"""Customer returns: eligibility is enforced server-side, not trusted."""
from datetime import datetime, timezone, timedelta

from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models.order import Return, OrderTracking
from app.models.enums import OrderStatus, ReturnStatus, TrackingStatusType
from app.services.order_service import create_order_from_cart
from tests.factories import make_user, make_address, make_product, make_cart


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token(identity=str(user.id))}"}


def _delivered_order(user, delivered_days_ago=0):
    address = make_address(user)
    _, variant = make_product(price=500, stock=10)
    make_cart(user, [(variant, 2)])
    order, err = create_order_from_cart(user.id, address.id, "cod")
    assert err is None, err

    order.status = OrderStatus.delivered
    db.session.add(OrderTracking(
        order_id=order.id,
        status_label="Delivered",
        description="Handed to customer.",
        status_type=TrackingStatusType.delivered,
        event_time=datetime.now(timezone.utc) - timedelta(days=delivered_days_ago),
    ))
    db.session.commit()
    return order


def test_request_return_on_delivered_item(app, client):
    user = make_user()
    order = _delivered_order(user)

    resp = client.post("/api/returns", json={
        "order_item_id": order.items[0].id,
        "reason": "size_issue",
        "description": "Too tight across the shoulders.",
    }, headers=_headers(user))

    assert resp.status_code == 201
    body = resp.get_json()
    assert body["status"] == "requested"
    assert body["reason"] == "size_issue"
    assert body["order_number"] == order.order_number
    db.session.expire_all()
    assert db.session.get(type(order), order.id).status == OrderStatus.return_requested


def test_cannot_return_another_customers_item(app, client):
    owner = make_user()
    order = _delivered_order(owner)
    stranger = make_user()

    resp = client.post("/api/returns", json={
        "order_item_id": order.items[0].id, "reason": "damaged",
    }, headers=_headers(stranger))

    assert resp.status_code == 404
    assert Return.query.count() == 0


def test_cannot_return_undelivered_order(app, client):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=500, stock=10)
    make_cart(user, [(variant, 1)])
    order, _ = create_order_from_cart(user.id, address.id, "cod")  # pending

    resp = client.post("/api/returns", json={
        "order_item_id": order.items[0].id, "reason": "changed_mind",
    }, headers=_headers(user))

    assert resp.status_code == 422
    assert "delivered" in resp.get_json()["error"].lower()


def test_return_window_closes_after_seven_days(app, client):
    user = make_user()
    order = _delivered_order(user, delivered_days_ago=8)

    resp = client.post("/api/returns", json={
        "order_item_id": order.items[0].id, "reason": "quality_issue",
    }, headers=_headers(user))

    assert resp.status_code == 422
    assert "window" in resp.get_json()["error"].lower()


def test_return_allowed_on_final_day_of_window(app, client):
    user = make_user()
    order = _delivered_order(user, delivered_days_ago=6)

    resp = client.post("/api/returns", json={
        "order_item_id": order.items[0].id, "reason": "wrong_item",
    }, headers=_headers(user))

    assert resp.status_code == 201


def test_duplicate_open_return_is_rejected(app, client):
    user = make_user()
    order = _delivered_order(user)
    payload = {"order_item_id": order.items[0].id, "reason": "damaged"}

    assert client.post("/api/returns", json=payload, headers=_headers(user)).status_code == 201
    resp = client.post("/api/returns", json=payload, headers=_headers(user))

    assert resp.status_code == 409
    assert Return.query.count() == 1


def test_can_re_request_after_a_rejected_return(app, client):
    user = make_user()
    order = _delivered_order(user)
    payload = {"order_item_id": order.items[0].id, "reason": "damaged"}

    first = client.post("/api/returns", json=payload, headers=_headers(user))
    rejected = db.session.get(Return, first.get_json()["id"])
    rejected.status = ReturnStatus.rejected
    db.session.commit()

    resp = client.post("/api/returns", json=payload, headers=_headers(user))
    assert resp.status_code == 201


def test_returning_one_item_does_not_lock_out_the_others(app, client):
    """A multi-item order flips to return_requested on the first return; the
    remaining items must still be returnable."""
    user = make_user()
    address = make_address(user)
    _, variant_a = make_product(price=500, stock=10)
    _, variant_b = make_product(price=700, stock=10)
    make_cart(user, [(variant_a, 1), (variant_b, 1)])
    order, err = create_order_from_cart(user.id, address.id, "cod")
    assert err is None, err
    order.status = OrderStatus.delivered
    db.session.add(OrderTracking(
        order_id=order.id, status_label="Delivered",
        status_type=TrackingStatusType.delivered,
        event_time=datetime.now(timezone.utc),
    ))
    db.session.commit()

    first, second = order.items[0], order.items[1]
    r1 = client.post("/api/returns", json={
        "order_item_id": first.id, "reason": "damaged",
    }, headers=_headers(user))
    r2 = client.post("/api/returns", json={
        "order_item_id": second.id, "reason": "size_issue",
    }, headers=_headers(user))

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert Return.query.count() == 2


def test_list_only_returns_my_own(app, client):
    mine = make_user()
    my_order = _delivered_order(mine)
    client.post("/api/returns", json={
        "order_item_id": my_order.items[0].id, "reason": "other",
    }, headers=_headers(mine))

    other = make_user()
    other_order = _delivered_order(other)
    client.post("/api/returns", json={
        "order_item_id": other_order.items[0].id, "reason": "other",
    }, headers=_headers(other))

    resp = client.get("/api/returns", headers=_headers(mine))

    assert resp.status_code == 200
    returns = resp.get_json()["returns"]
    assert len(returns) == 1
    assert returns[0]["order_number"] == my_order.order_number


def test_eligibility_marks_items_returnable(app, client):
    user = make_user()
    order = _delivered_order(user)

    resp = client.get(f"/api/returns/eligibility/{order.id}", headers=_headers(user))

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["window_open"] is True
    assert body["window_days"] == 7
    assert all(i["returnable"] for i in body["items"])


def test_eligibility_flags_item_with_open_return(app, client):
    user = make_user()
    order = _delivered_order(user)
    client.post("/api/returns", json={
        "order_item_id": order.items[0].id, "reason": "damaged",
    }, headers=_headers(user))

    resp = client.get(f"/api/returns/eligibility/{order.id}", headers=_headers(user))

    item = resp.get_json()["items"][0]
    assert item["returnable"] is False
    assert "already in progress" in item["reason_unavailable"]


def test_eligibility_closed_outside_window(app, client):
    user = make_user()
    order = _delivered_order(user, delivered_days_ago=30)

    resp = client.get(f"/api/returns/eligibility/{order.id}", headers=_headers(user))

    body = resp.get_json()
    assert body["window_open"] is False
    assert all(not i["returnable"] for i in body["items"])


def test_invalid_reason_is_rejected(app, client):
    user = make_user()
    order = _delivered_order(user)

    resp = client.post("/api/returns", json={
        "order_item_id": order.items[0].id, "reason": "i_just_dont_like_it",
    }, headers=_headers(user))

    assert resp.status_code == 422


def test_returns_require_authentication(app, client):
    assert client.get("/api/returns").status_code == 401
    assert client.post("/api/returns", json={}).status_code == 401
