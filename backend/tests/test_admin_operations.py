"""Admin screens that are not plain CRUD: catalogue, orders, returns, people."""
import io

from PIL import Image

from app.extensions import db
from app.models.catalogue import Product, ProductVariant
from app.models.enums import OrderStatus, ReturnStatus
from app.models.marketing import ContactMessage, NewsletterSubscriber, WholesaleInquiry
from app.models.order import Order, Return
from app.models.user import User
from app.services import shiprocket
from app.services.order_service import create_order_from_cart
from tests.factories import make_address, make_cart, make_product, make_user
from tests.helpers import admin_headers, customer_headers, make_admin


def _category(client, headers):
    return client.post(
        "/api/admin/categories", headers=headers,
        json={"name": "Kurtas", "slug": "kurtas"},
    ).get_json()["id"]


def _product_payload(category_id, **over):
    return {
        "category_id": category_id, "name": "Linen Kurta", "slug": "linen-kurta",
        "mrp": 2999, "selling_price": 1999, **over,
    }


def _order(user=None, quantity=2, stock=10):
    user = user or make_user()
    address = make_address(user)
    _, variant = make_product(price=500, stock=stock)
    make_cart(user, [(variant, quantity)])
    order, err = create_order_from_cart(user.id, address.id, "cod")
    assert err is None, err
    return order, variant


# ── Catalogue ─────────────────────────────────────────────────

def test_product_lifecycle(app, client):
    headers = admin_headers()
    category_id = _category(client, headers)

    created = client.post(
        "/api/admin/products", headers=headers, json=_product_payload(category_id)
    )
    assert created.status_code == 201, created.get_data(as_text=True)
    product_id = created.get_json()["id"]

    fetched = client.get(f"/api/admin/products/{product_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.get_json()["slug"] == "linen-kurta"

    updated = client.put(
        f"/api/admin/products/{product_id}", headers=headers,
        json=_product_payload(category_id, selling_price=1799),
    )
    assert updated.status_code == 200
    assert updated.get_json()["selling_price"] == 1799

    listed = client.get("/api/admin/products?q=linen", headers=headers)
    assert listed.status_code == 200
    assert listed.get_json()["total"] == 1

    # Deleting deactivates: past orders still reference the product.
    deleted = client.delete(f"/api/admin/products/{product_id}", headers=headers)
    assert deleted.status_code == 200
    assert db.session.get(Product, product_id).is_active is False
    assert client.get("/api/admin/products?active=true", headers=headers).get_json()["total"] == 0


def test_duplicate_product_slug_is_a_conflict(app, client):
    headers = admin_headers()
    category_id = _category(client, headers)
    client.post("/api/admin/products", headers=headers, json=_product_payload(category_id))

    resp = client.post(
        "/api/admin/products", headers=headers, json=_product_payload(category_id)
    )

    assert resp.status_code == 409


def test_product_needs_an_existing_category(app, client):
    resp = client.post(
        "/api/admin/products", headers=admin_headers(), json=_product_payload(424242)
    )

    assert resp.status_code == 404


def test_variant_lifecycle(app, client):
    headers = admin_headers()
    product_id = client.post(
        "/api/admin/products", headers=headers,
        json=_product_payload(_category(client, headers)),
    ).get_json()["id"]
    variant = {"size": "M", "color_name": "Indigo", "color_hex": "#1A237E", "stock_qty": 5}

    added = client.post(
        f"/api/admin/products/{product_id}/variants", headers=headers, json=variant
    )
    assert added.status_code == 201, added.get_data(as_text=True)
    variant_id = added.get_json()["variants"][0]["id"]

    duplicate = client.post(
        f"/api/admin/products/{product_id}/variants", headers=headers, json=variant
    )
    assert duplicate.status_code == 409

    restocked = client.put(
        f"/api/admin/products/{product_id}/variants/{variant_id}", headers=headers,
        json={**variant, "stock_qty": 40},
    )
    assert restocked.status_code == 200
    assert db.session.get(ProductVariant, variant_id).stock_qty == 40

    removed = client.delete(
        f"/api/admin/products/{product_id}/variants/{variant_id}", headers=headers
    )
    assert removed.status_code == 200
    assert removed.get_json()["variants"] == []


def test_first_image_becomes_primary_and_primary_moves_on_delete(app, client):
    headers = admin_headers()
    product_id = client.post(
        "/api/admin/products", headers=headers,
        json=_product_payload(_category(client, headers)),
    ).get_json()["id"]
    url = f"/api/admin/products/{product_id}/images"

    first = client.post(url, headers=headers, json={"image_url": "/static/uploads/1.webp"})
    assert first.status_code == 201
    second = client.post(
        url, headers=headers,
        json={"image_url": "/static/uploads/2.webp", "sort_order": 1},
    )
    images = second.get_json()["images"]
    assert [i["is_primary"] for i in images] == [True, False]

    after = client.delete(f"{url}/{images[0]['id']}", headers=headers)
    assert after.status_code == 200
    remaining = after.get_json()["images"]
    assert len(remaining) == 1 and remaining[0]["is_primary"] is True


def test_upload_stores_an_image_and_returns_its_url(app, client, tmp_path, monkeypatch):
    monkeypatch.setitem(app.config, "UPLOAD_FOLDER", str(tmp_path))
    monkeypatch.setitem(app.config, "SUPABASE_URL", "")
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), "#C8963E").save(buf, format="PNG")
    buf.seek(0)

    resp = client.post(
        "/api/admin/upload", headers=admin_headers(),
        data={"file": (buf, "swatch.png")}, content_type="multipart/form-data",
    )

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["url"]


def test_upload_rejects_a_non_image(app, client):
    resp = client.post(
        "/api/admin/upload", headers=admin_headers(),
        data={"file": (io.BytesIO(b"#!/bin/sh"), "run.sh")},
        content_type="multipart/form-data",
    )

    assert resp.status_code == 400


# ── Orders ────────────────────────────────────────────────────

def test_order_list_filters_and_detail(app, client):
    order, _ = _order()
    headers = admin_headers()

    listed = client.get("/api/admin/orders?status=pending", headers=headers)
    assert listed.status_code == 200
    assert [o["id"] for o in listed.get_json()["orders"]] == [order.id]
    assert client.get(
        "/api/admin/orders?status=delivered", headers=headers
    ).get_json()["total"] == 0

    detail = client.get(f"/api/admin/orders/{order.id}", headers=headers)
    assert detail.status_code == 200
    body = detail.get_json()
    assert body["order_number"] == order.order_number
    assert body["items"][0]["quantity"] == 2
    assert body["address"]["pin_code"] == "700001"


def test_manual_tracking_event_updates_the_order(app, client):
    order, _ = _order()

    resp = client.post(
        f"/api/admin/orders/{order.id}/tracking", headers=admin_headers(),
        json={
            "status_label": "Packed", "status_type": "packed",
            "courier_name": "BlueDart", "tracking_number": "BD123",
        },
    )

    assert resp.status_code == 201, resp.get_data(as_text=True)
    db.session.refresh(order)
    assert order.tracking_number == "BD123"
    assert any(t.status_label == "Packed" for t in order.tracking)


def test_ship_creates_a_shipment_and_marks_the_order_shipped(app, client, monkeypatch):
    order, _ = _order()
    monkeypatch.setattr(shiprocket, "create_order", lambda o: {"shipment_id": 77})
    monkeypatch.setattr(
        shiprocket, "assign_awb",
        lambda shipment_id: {"awb_code": "AWB001", "courier_name": "Delhivery"},
    )
    headers = admin_headers()

    resp = client.post(f"/api/admin/orders/{order.id}/ship", headers=headers)

    assert resp.status_code == 201, resp.get_data(as_text=True)
    db.session.refresh(order)
    assert order.status == OrderStatus.shipped
    assert order.tracking_number == "AWB001"
    # A second click must not book a second shipment.
    assert client.post(f"/api/admin/orders/{order.id}/ship", headers=headers).status_code == 409


def test_ship_reports_a_courier_failure_without_changing_the_order(app, client, monkeypatch):
    order, _ = _order()

    def _fail(_order):
        raise shiprocket.ShiprocketError("Shipping is not configured.")

    monkeypatch.setattr(shiprocket, "create_order", _fail)

    resp = client.post(f"/api/admin/orders/{order.id}/ship", headers=admin_headers())

    assert resp.status_code == 502
    db.session.refresh(order)
    assert order.status == OrderStatus.pending
    assert order.tracking_number is None


def test_sync_tracking_adds_each_courier_update_once(app, client, monkeypatch):
    order, _ = _order()
    order.tracking_number = "AWB001"
    db.session.commit()
    monkeypatch.setattr(shiprocket, "track_by_awb", lambda awb: [
        {"activity": "Picked up", "location": "Kolkata"},
        {"activity": "In transit", "location": "Delhi"},
    ])
    headers = admin_headers()

    first = client.post(f"/api/admin/orders/{order.id}/sync-tracking", headers=headers)
    second = client.post(f"/api/admin/orders/{order.id}/sync-tracking", headers=headers)

    assert first.status_code == 200 and first.get_json()["added"] == 2
    assert second.get_json()["added"] == 0


def test_sync_tracking_needs_an_awb(app, client):
    order, _ = _order()

    resp = client.post(f"/api/admin/orders/{order.id}/sync-tracking", headers=admin_headers())

    assert resp.status_code == 422


# ── Returns ───────────────────────────────────────────────────

def test_returns_list_and_resolution(app, client):
    user = make_user()
    order, _ = _order(user=user)
    order.status = OrderStatus.delivered
    db.session.commit()
    requested = client.post(
        "/api/returns", headers=customer_headers(user),
        json={"order_item_id": order.items[0].id, "reason": "size_issue"},
    )
    assert requested.status_code == 201, requested.get_data(as_text=True)
    headers = admin_headers()

    listed = client.get("/api/admin/returns?status=requested", headers=headers)
    assert listed.status_code == 200
    rows = listed.get_json()["returns"]
    assert len(rows) == 1 and rows[0]["customer_name"] == user.full_name

    resolved = client.patch(
        f"/api/admin/returns/{rows[0]['id']}", headers=headers,
        json={"status": "resolved", "resolution_type": "refund", "refund_amount": 500},
    )
    assert resolved.status_code == 200, resolved.get_data(as_text=True)
    ret = db.session.get(Return, rows[0]["id"])
    assert ret.status == ReturnStatus.resolved
    assert ret.resolved_at is not None


# ── People ────────────────────────────────────────────────────

def test_user_list_search_detail_and_deactivation(app, client):
    user = make_user(email="asha@example.com", full_name="Asha Rao")
    make_user(email="other@example.com", full_name="Someone Else")
    headers = admin_headers()

    found = client.get("/api/admin/users?q=asha", headers=headers)
    assert found.status_code == 200
    assert found.get_json()["total"] == 1

    detail = client.get(f"/api/admin/users/{user.id}", headers=headers)
    assert detail.status_code == 200
    assert "asha@example.com" in detail.get_data(as_text=True)

    blocked = client.patch(
        f"/api/admin/users/{user.id}", headers=headers, json={"is_active": False}
    )
    assert blocked.status_code == 200
    assert db.session.get(User, user.id).is_active is False


def test_master_can_remove_another_admin_but_not_themselves(app, client):
    master = make_admin(role="master")
    staff = make_admin(role="staff")
    headers = admin_headers(master)

    assert client.delete(
        f"/api/admin/auth/admins/{master.id}", headers=headers
    ).status_code == 422

    resp = client.delete(f"/api/admin/auth/admins/{staff.id}", headers=headers)
    assert resp.status_code == 200
    emails = [a["email"] for a in client.get(
        "/api/admin/auth/admins", headers=headers
    ).get_json()["admins"]]
    assert staff.email not in emails


def test_wholesale_inquiry_inbox(app, client):
    submitted = client.post("/api/wholesale", json={
        "shop_name": "Rao Textiles", "owner_name": "Asha Rao",
        "email": "asha@example.com", "phone": "9000000000",
        "city": "Kolkata", "state": "West Bengal", "gst_number": "",
        "monthly_volume_range": "10k_50k",
    })
    assert submitted.status_code == 201, submitted.get_data(as_text=True)
    inquiry = WholesaleInquiry.query.one()
    headers = admin_headers()

    listed = client.get("/api/admin/wholesale-inquiries?status=new", headers=headers)
    assert listed.status_code == 200
    assert listed.get_json()["total"] == 1

    updated = client.patch(
        f"/api/admin/wholesale-inquiries/{inquiry.id}", headers=headers,
        json={"status": "contacted", "notes": "Called on Monday."},
    )
    assert updated.status_code == 200
    db.session.refresh(inquiry)
    assert inquiry.status.value == "contacted" and inquiry.notes == "Called on Monday."


def test_contact_message_inbox(app, client):
    submitted = client.post("/api/contact", json={
        "name": "Asha Rao", "email": "asha@example.com",
        "subject": "order_support", "message": "Where is my order?",
    })
    assert submitted.status_code == 201, submitted.get_data(as_text=True)
    message = ContactMessage.query.one()
    headers = admin_headers()

    listed = client.get("/api/admin/contact-messages?status=unread", headers=headers)
    assert listed.status_code == 200
    assert listed.get_json()["total"] == 1

    read = client.patch(
        f"/api/admin/contact-messages/{message.id}", headers=headers,
        json={"status": "read"},
    )
    assert read.status_code == 200
    db.session.refresh(message)
    assert message.status.value == "read"


def test_newsletter_subscribe_unsubscribe_and_admin_removal(app, client):
    assert client.post(
        "/api/newsletter/subscribe", json={"email": "asha@example.com"}
    ).status_code in (200, 201)
    subscriber = NewsletterSubscriber.query.one()
    headers = admin_headers()

    listed = client.get("/api/admin/newsletter", headers=headers)
    assert listed.status_code == 200
    assert listed.get_json()["total"] == 1

    assert client.post(
        "/api/newsletter/unsubscribe", json={"email": "asha@example.com"}
    ).status_code == 200
    assert client.get("/api/admin/newsletter", headers=headers).get_json()["total"] == 0

    removed = client.delete(f"/api/admin/newsletter/{subscriber.id}", headers=headers)
    assert removed.status_code == 200
    assert NewsletterSubscriber.query.count() == 0


# ── Dashboard and settlements ─────────────────────────────────

def test_dashboard_counts_match_the_database(app, client):
    _order(quantity=2)
    make_product(stock=0)   # one variant out of stock

    resp = client.get("/api/admin/dashboard/stats", headers=admin_headers())

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["orders"]["total"] == Order.query.count() == 1
    assert body["products"]["total"] == 2
    assert body["products"]["out_of_stock"] == 1
    assert body["pending_returns"] == 0
    assert len(body["recent_orders"]) == 1


def test_settlements_report_unconfigured_instead_of_failing(app, client, monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)

    resp = client.get("/api/admin/settlements", headers=admin_headers())

    assert resp.status_code == 200
    assert resp.get_json() == {"configured": False, "settlements": []}


def test_settlements_convert_paise_to_rupees(app, client, monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_x")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "secret")

    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {"items": [{
                "id": "setl_1", "amount": 123450, "fees": 2360, "tax": 360,
                "status": "processed", "utr": "UTR1", "created_at": 1700000000,
            }]}

    monkeypatch.setattr(
        "app.routes.admin.settlements.requests.get", lambda *a, **kw: _Resp()
    )

    resp = client.get("/api/admin/settlements", headers=admin_headers())

    assert resp.status_code == 200
    row = resp.get_json()["settlements"][0]
    assert row["amount"] == 1234.5 and row["fees"] == 23.6


# ── Values the database refuses must be a 422, not a 500 ──────

def test_product_prices_must_be_positive_and_not_above_mrp(app, client):
    headers = admin_headers()
    category_id = _category(client, headers)

    for bad in (
        {"mrp": 0}, {"selling_price": 0}, {"selling_price": -5},
        {"mrp": 1000, "selling_price": 1500},
    ):
        resp = client.post(
            "/api/admin/products", headers=headers,
            json=_product_payload(category_id, **bad),
        )
        assert resp.status_code == 422, (bad, resp.get_data(as_text=True))


def test_variant_stock_cannot_be_negative(app, client):
    headers = admin_headers()
    product_id = client.post(
        "/api/admin/products", headers=headers,
        json=_product_payload(_category(client, headers)),
    ).get_json()["id"]

    resp = client.post(
        f"/api/admin/products/{product_id}/variants", headers=headers,
        json={"size": "M", "color_name": "Indigo", "color_hex": "#1A237E", "stock_qty": -1},
    )

    assert resp.status_code == 422


def test_coupon_values_are_bounded(app, client):
    headers = admin_headers()

    for bad in (
        {"discount_type": "percentage", "discount_value": -10},
        {"discount_type": "percentage", "discount_value": 150},
        {"discount_type": "flat", "discount_value": 100, "usage_limit": -1},
    ):
        resp = client.post(
            "/api/admin/coupons", headers=headers, json={"code": "BADONE", **bad}
        )
        assert resp.status_code == 422, (bad, resp.get_data(as_text=True))


def test_return_refund_cannot_exceed_what_the_item_cost(app, client):
    user = make_user()
    order, _ = _order(user=user, quantity=2)   # 2 x 500
    order.status = OrderStatus.delivered
    db.session.commit()
    return_id = client.post(
        "/api/returns", headers=customer_headers(user),
        json={"order_item_id": order.items[0].id, "reason": "damaged"},
    ).get_json()["id"]

    resp = client.patch(
        f"/api/admin/returns/{return_id}", headers=admin_headers(),
        json={"status": "resolved", "resolution_type": "refund", "refund_amount": 5000},
    )

    assert resp.status_code == 422
    assert db.session.get(Return, return_id).status == ReturnStatus.requested
