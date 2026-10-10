"""Cancellation side effects: restock exactly once, and refund prepaid orders.

Inventory restoration on cancel belongs to the trg_restore_inventory trigger.
Any app-side `stock_qty += quantity` on the same status flip silently doubles
it, so these tests assert the post-cancel stock is exactly the pre-order level.
"""
from unittest.mock import patch

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.admin import Admin
from app.models.order import Order
from app.models.enums import OrderStatus, PaymentStatus
from app.services.order_service import create_order_from_cart
from tests.factories import make_user, make_address, make_product, make_cart

PASSWORD = "AdminPass123!"
STARTING_STOCK = 10
ORDER_QTY = 3


def _admin_headers(client):
    db.session.add(Admin(
        email="cancel-admin@example.com",
        password_hash=generate_password_hash(PASSWORD),
        full_name="Cancel Admin",
        role="master",
    ))
    db.session.commit()
    resp = client.post(
        "/api/admin/auth/login",
        json={"email": "cancel-admin@example.com", "password": PASSWORD},
    )
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


def _placed_order(paid=False, payment_ref=None):
    """A COD (or prepaid) order for ORDER_QTY units of a STARTING_STOCK variant."""
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=500, stock=STARTING_STOCK)
    make_cart(user, [(variant, ORDER_QTY)])

    order, err = create_order_from_cart(
        user.id, address.id, "cod" if not paid else "upi",
        paid=paid, payment_ref=payment_ref,
    )
    assert err is None, err
    db.session.refresh(variant)
    # The trigger deducted at insert time.
    assert variant.stock_qty == STARTING_STOCK - ORDER_QTY
    return order, variant


def test_admin_cancel_restocks_exactly_once(app, client):
    """Regression: the route also did `stock_qty += quantity`, doubling the
    trigger's restock and inflating inventory on every cancellation."""
    headers = _admin_headers(client)
    order, variant = _placed_order()

    resp = client.patch(
        f"/api/admin/orders/{order.id}/status",
        json={"status": "cancelled"},
        headers=headers,
    )

    assert resp.status_code == 200
    db.session.expire_all()
    db.session.refresh(variant)
    assert variant.stock_qty == STARTING_STOCK


def test_repeated_admin_cancel_does_not_restock_again(app, client):
    headers = _admin_headers(client)
    order, variant = _placed_order()

    for _ in range(3):
        client.patch(
            f"/api/admin/orders/{order.id}/status",
            json={"status": "cancelled"},
            headers=headers,
        )

    db.session.expire_all()
    db.session.refresh(variant)
    assert variant.stock_qty == STARTING_STOCK


def test_cancelled_order_cannot_move_to_another_status(app, client):
    headers = _admin_headers(client)
    order, _ = _placed_order()

    client.patch(
        f"/api/admin/orders/{order.id}/status",
        json={"status": "cancelled"}, headers=headers,
    )
    resp = client.patch(
        f"/api/admin/orders/{order.id}/status",
        json={"status": "shipped"}, headers=headers,
    )

    assert resp.status_code == 409
    db.session.expire_all()
    assert db.session.get(Order, order.id).status == OrderStatus.cancelled


def test_customer_cancel_restocks_exactly_once(app, client):
    order, variant = _placed_order()
    token = create_access_token(identity=str(order.user_id))

    resp = client.post(
        f"/api/orders/{order.id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200
    db.session.expire_all()
    db.session.refresh(variant)
    assert variant.stock_qty == STARTING_STOCK


def test_cancelling_prepaid_order_refunds_the_customer(app, client):
    """A captured payment must be returned when the order is cancelled."""
    headers = _admin_headers(client)
    order, _ = _placed_order(paid=True, payment_ref="pay_TESTCANCEL1")
    expected_paise = int(round(float(order.total_amount) * 100))

    with patch("app.routes.payments.refund_payment", return_value=True) as refund:
        resp = client.patch(
            f"/api/admin/orders/{order.id}/status",
            json={"status": "cancelled"},
            headers=headers,
        )

    assert resp.status_code == 200
    assert resp.get_json()["refunded"] is True
    refund.assert_called_once_with("pay_TESTCANCEL1", expected_paise)
    db.session.expire_all()
    assert db.session.get(Order, order.id).payment_status == PaymentStatus.refunded


def test_cancelling_cod_order_attempts_no_refund(app, client):
    headers = _admin_headers(client)
    order, _ = _placed_order()

    with patch("app.routes.payments.refund_payment") as refund:
        resp = client.patch(
            f"/api/admin/orders/{order.id}/status",
            json={"status": "cancelled"},
            headers=headers,
        )

    assert resp.status_code == 200
    refund.assert_not_called()
    assert "refunded" not in resp.get_json()


def test_failed_refund_still_cancels_and_reports(app, client):
    """The order must not stay live just because the gateway refund failed —
    it is logged CRITICAL for manual follow-up instead."""
    headers = _admin_headers(client)
    order, _ = _placed_order(paid=True, payment_ref="pay_TESTCANCEL2")

    with patch("app.routes.payments.refund_payment", return_value=False):
        resp = client.patch(
            f"/api/admin/orders/{order.id}/status",
            json={"status": "cancelled"},
            headers=headers,
        )

    assert resp.status_code == 200
    assert resp.get_json()["refunded"] is False
    db.session.expire_all()
    updated = db.session.get(Order, order.id)
    assert updated.status == OrderStatus.cancelled
    assert updated.payment_status == PaymentStatus.paid  # unchanged, needs follow-up


def test_admin_status_change_leaves_a_tracking_event(app, client):
    """The customer's order page and the return window both read tracking
    events, so marking an order delivered must record one."""
    headers = _admin_headers(client)
    order, _ = _placed_order()

    for status in ("shipped", "delivered"):
        resp = client.patch(
            f"/api/admin/orders/{order.id}/status", json={"status": status}, headers=headers,
        )
        assert resp.status_code == 200

    db.session.expire_all()
    order = db.session.get(Order, order.id)
    types = [t.status_type.value for t in order.tracking]
    assert "dispatched" in types
    assert types.count("delivered") == 1


def test_delivered_cod_order_is_marked_paid(app, client):
    headers = _admin_headers(client)
    order, _ = _placed_order()
    assert order.payment_status == PaymentStatus.pending

    client.patch(f"/api/admin/orders/{order.id}/status", json={"status": "delivered"}, headers=headers)

    db.session.expire_all()
    assert db.session.get(Order, order.id).payment_status == PaymentStatus.paid
