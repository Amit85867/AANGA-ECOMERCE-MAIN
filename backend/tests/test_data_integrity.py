"""Things that must hold when several people act at once, or act twice.

These run real concurrent transactions against Postgres (threads, each with
its own connection): the guarantees come from row locks, unique indexes and
triggers, and only a real race shows whether they hold.
"""
import threading
from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.models.engagement import Coupon
from app.models.enums import DiscountType
from app.models.order import Order
from app.models.catalogue import ProductVariant
from app.models.user import User
from app.services.email import order_confirmation_content
from app.services.order_service import compute_totals, create_order_from_cart
from tests.factories import make_address, make_cart, make_coupon, make_product, make_user
from tests.helpers import admin_headers, customer_headers


def _together(app, jobs):
    """Run each job in its own thread and app context, released at the same
    instant. Returns their results in order."""
    gate = threading.Barrier(len(jobs))
    results = [None] * len(jobs)

    def run(index, job):
        with app.app_context():
            try:
                gate.wait(timeout=10)
                results[index] = job()
            except Exception as exc:  # noqa: BLE001 - a crash is a result worth asserting on
                results[index] = exc
            finally:
                db.session.remove()

    threads = [threading.Thread(target=run, args=(i, job)) for i, job in enumerate(jobs)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    return results


def _buyers(count, variant, coupon=None):
    out = []
    for _ in range(count):
        user = make_user()
        address = make_address(user)
        make_cart(user, [(variant, 1)], coupon=coupon)
        out.append((user.id, address.id))
    return out


def _place(user_id, address_id, **kw):
    order, err = create_order_from_cart(user_id, address_id, "cod", **kw)
    return ("ok", order.id) if order else ("refused", err)


# ── Stock ─────────────────────────────────────────────────────

@pytest.mark.parametrize("buyers", [2, 6])
def test_the_last_unit_is_sold_exactly_once(app, buyers):
    _, variant = make_product(price=500, stock=1)
    people = _buyers(buyers, variant)

    results = _together(app, [lambda p=p: _place(*p) for p in people])

    assert [r[0] for r in results].count("ok") == 1, results
    assert all(r[0] == "refused" and r[1][1] == 409 for r in results if r[0] != "ok"), results
    db.session.expire_all()
    assert db.session.get(ProductVariant, variant.id).stock_qty == 0
    assert Order.query.count() == 1


def test_stock_never_goes_below_zero_when_many_buy_at_once(app):
    _, variant = make_product(price=500, stock=3)
    people = _buyers(8, variant)
    results = _together(app, [lambda p=p: _place(*p) for p in people])
    assert [r[0] for r in results].count("ok") == 3, results
    db.session.expire_all()
    assert db.session.get(ProductVariant, variant.id).stock_qty == 0


def test_stock_comes_back_exactly_once_when_an_order_is_cancelled(app, client):
    _, variant = make_product(price=500, stock=5)
    (user_id, address_id), = _buyers(1, variant)
    order, _ = create_order_from_cart(user_id, address_id, "cod")
    headers = customer_headers(db.session.get(User, user_id))

    assert client.post(f"/api/orders/{order.id}/cancel", headers=headers).status_code == 200
    assert client.post(f"/api/orders/{order.id}/cancel", headers=headers).status_code == 409
    db.session.expire_all()
    assert db.session.get(ProductVariant, variant.id).stock_qty == 5


# ── Coupons ───────────────────────────────────────────────────

@pytest.mark.parametrize("limit, buyers", [(1, 2), (2, 6)])
def test_a_coupon_is_never_used_more_times_than_its_limit(app, limit, buyers):
    _, variant = make_product(price=2000, stock=50)
    coupon = make_coupon(code="LIMITED", discount_value=10)
    coupon.usage_limit = limit
    db.session.commit()
    people = _buyers(buyers, variant, coupon=coupon)

    results = _together(app, [lambda p=p: _place(*p) for p in people])

    assert [r[0] for r in results].count("ok") == limit, results
    refused = [r for r in results if r[0] == "refused"]
    assert all(r[1][1] == 409 and "LIMITED" in r[1][0] and "used up" in r[1][0] for r in refused), refused
    db.session.expire_all()
    assert db.session.get(Coupon, coupon.id).used_count == limit
    assert Order.query.filter(Order.coupon_id == coupon.id).count() == limit

    # whoever was turned away still has their bag, without the coupon, and can order at full price
    user_id, address_id = next(p for p, r in zip(people, results) if r[0] == "refused")
    outcome, order_id = _place(user_id, address_id)
    assert outcome == "ok"
    assert float(db.session.get(Order, order_id).discount_amount) == 0


def _bag_with(coupon_changes, price=2000, quantity=1):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=price, stock=20)
    coupon = make_coupon(code="LATER", discount_type=DiscountType.flat, discount_value=500)
    cart = make_cart(user, [(variant, quantity)], coupon=coupon)
    for field, value in coupon_changes.items():
        setattr(coupon, field, value)
    db.session.commit()
    return user, address, cart, coupon


@pytest.mark.parametrize("changes, reason", [
    ({"expires_at": datetime.now(timezone.utc) - timedelta(minutes=1)}, "has expired"),
    ({"is_active": False}, "is no longer available"),
    ({"usage_limit": 3, "used_count": 3}, "has been used up"),
    ({"min_order_value": 4999}, "needs a bag of at least ₹4999"),
])
def test_a_coupon_that_stopped_being_valid_after_it_was_applied_is_not_honoured(app, client, changes, reason):
    user, address, _cart, coupon = _bag_with(changes)
    headers = customer_headers(user)

    placed = client.post("/api/orders", headers=headers, json={"address_id": address.id, "payment_method": "cod"})
    assert placed.status_code == 409
    assert reason in placed.get_json()["error"]
    assert Order.query.count() == 0

    bag = client.get("/api/cart", headers=headers).get_json()
    assert bag["coupon_code"] is None and bag["discount"] == 0
    assert bag["total"] == round(2000 * 1.05, 2)

    again = client.post("/api/orders", headers=headers, json={"address_id": address.id, "payment_method": "cod"})
    assert again.status_code in (200, 201)
    db.session.expire_all()
    assert db.session.get(Coupon, coupon.id).used_count == changes.get("used_count", 0)


def test_the_bag_says_once_why_a_coupon_was_taken_off(app, client):
    user, _address, _cart, _coupon = _bag_with({"expires_at": datetime.now(timezone.utc) - timedelta(days=1)})
    headers = customer_headers(user)
    first = client.get("/api/cart", headers=headers).get_json()
    assert first["coupon_notice"] == "Coupon LATER has expired, so it was taken off your bag."
    assert client.get("/api/cart", headers=headers).get_json()["coupon_notice"] is None


def test_shrinking_the_bag_below_the_minimum_drops_the_coupon(app, client):
    user = make_user()
    _, variant = make_product(price=1000, stock=20)
    coupon = make_coupon(code="BIG500", discount_type=DiscountType.flat, discount_value=500)
    coupon.min_order_value = 4999
    db.session.commit()
    make_cart(user, [(variant, 5)])
    headers = customer_headers(user)
    assert client.post("/api/cart/coupon", headers=headers, json={"code": "BIG500"}).status_code == 200
    line = client.get("/api/cart", headers=headers).get_json()["items"][0]

    bag = client.patch(f"/api/cart/items/{line['id']}", headers=headers, json={"quantity": 1}).get_json()

    assert bag["coupon_code"] is None and bag["discount"] == 0
    assert bag["total"] > 1000


def test_a_flat_coupon_larger_than_the_bag_cannot_make_the_total_negative(app):
    user = make_user()
    _, variant = make_product(price=300, stock=5)
    coupon = make_coupon(code="HUGE", discount_type=DiscountType.flat, discount_value=5000)
    cart = make_cart(user, [(variant, 1)], coupon=coupon)
    totals = compute_totals(cart)
    assert totals["discount"] == 300
    assert totals["total"] >= 0 and totals["gst"] == 0


@pytest.mark.parametrize("code, changes, status, message", [
    ("NOTREAL", {}, 404, "Invalid coupon code"),
    ("TRYME", {"is_active": False}, 404, "Invalid coupon code"),
    ("TRYME", {"expires_at": datetime.now(timezone.utc) - timedelta(days=1)}, 410, "expired"),
    ("TRYME", {"usage_limit": 1, "used_count": 1}, 410, "usage limit"),
    ("TRYME", {"min_order_value": 99999}, 422, "Minimum order value"),
])
def test_applying_a_coupon_that_cannot_be_used_is_refused_with_the_reason(app, client, code, changes, status, message):
    user = make_user()
    _, variant = make_product(price=500, stock=5)
    make_cart(user, [(variant, 1)])
    coupon = make_coupon(code="TRYME")
    for field, value in changes.items():
        setattr(coupon, field, value)
    db.session.commit()
    resp = client.post("/api/cart/coupon", headers=customer_headers(user), json={"code": code})
    assert resp.status_code == status
    assert message.lower() in resp.get_json()["error"].lower()


def test_a_second_coupon_replaces_the_first(app, client):
    user = make_user()
    _, variant = make_product(price=2000, stock=5)
    make_cart(user, [(variant, 1)])
    make_coupon(code="TEN", discount_value=10)
    make_coupon(code="TWENTY", discount_value=20)
    headers = customer_headers(user)
    client.post("/api/cart/coupon", headers=headers, json={"code": "TEN"})
    bag = client.post("/api/cart/coupon", headers=headers, json={"code": "TWENTY"}).get_json()
    assert bag["coupon_code"] == "TWENTY"
    assert bag["discount"] == 400                       # 20% only: never both


# ── Placing the order twice ───────────────────────────────────

def test_the_same_checkout_sent_twice_at_once_makes_one_order(app):
    _, variant = make_product(price=500, stock=10)
    (user_id, address_id), = _buyers(1, variant)

    results = _together(app, [lambda: _place(user_id, address_id, idempotency_key="checkout-abc")] * 2)

    assert Order.query.count() == 1, results
    assert len({r[1] for r in results if r[0] == "ok"}) == 1
    db.session.expire_all()
    assert db.session.get(ProductVariant, variant.id).stock_qty == 9


def test_two_requests_without_a_key_cannot_order_the_same_bag_twice(app):
    """A double click from a browser that sends no key."""
    _, variant = make_product(price=500, stock=10)
    (user_id, address_id), = _buyers(1, variant)
    results = _together(app, [lambda: _place(user_id, address_id)] * 2)
    assert Order.query.count() == 1, results
    db.session.expire_all()
    assert db.session.get(ProductVariant, variant.id).stock_qty == 9


# ── One total, everywhere ─────────────────────────────────────

def test_the_total_is_the_same_in_the_bag_the_order_the_email_and_the_dashboard(app, client):
    user = make_user()
    address = make_address(user)
    _, shirt = make_product(price=1799, stock=10)
    _, belt = make_product(price=349.50, stock=10)
    coupon = make_coupon(code="TEN", discount_value=10)
    make_cart(user, [(shirt, 2), (belt, 1)], coupon=coupon)
    headers = customer_headers(user)

    bag = client.get("/api/cart", headers=headers).get_json()
    placed = client.post("/api/orders", headers=headers, json={"address_id": address.id, "payment_method": "cod"})
    assert placed.status_code in (200, 201), placed.get_json()
    order_id = placed.get_json()["order_id"]

    mine = client.get(f"/api/orders/{order_id}", headers=headers).get_json()
    listed = next(o for o in client.get("/api/orders", headers=headers).get_json()["orders"] if o["id"] == order_id)
    admin = client.get(f"/api/admin/orders/{order_id}", headers=admin_headers()).get_json()
    order = db.session.get(Order, order_id)
    _subject, html, text = order_confirmation_content(order)

    expected = round((1799 * 2 + 349.50) * 0.9 * 1.05, 2)            # 10% off, 5% GST, free delivery
    assert bag["total"] == expected
    for name, seen in [("order", mine["total_amount"]), ("order list", listed["total_amount"]),
                       ("dashboard", admin["total_amount"]), ("database", float(order.total_amount))]:
        assert seen == expected, name
    for part in ("subtotal", "discount_amount", "gst_amount", "delivery_charge"):
        assert mine[part] == admin[part], part
    assert mine["subtotal"] == bag["subtotal"] and mine["discount_amount"] == bag["discount"]
    assert round(mine["subtotal"] - mine["discount_amount"] + mine["gst_amount"] + mine["delivery_charge"], 2) == expected
    shown = f"{expected:,.2f}"
    assert shown in html and shown in text
