"""Order status rules (app/services/order_status.py) and their enforcement.

Refunds and restocks hang off status changes, so each rejected change is also
checked to have moved no money and no stock.
"""
from unittest.mock import patch

import pytest

from app.extensions import db
from app.models.enums import OrderStatus as S, PaymentStatus, ReturnStatus
from app.models.order import Order, Return
from app.models.catalogue import ProductVariant
from app.services import order_status
from app.services.order_service import create_order_from_cart
from tests.factories import make_address, make_cart, make_product, make_user
from tests.helpers import admin_headers, customer_headers

ACTORS = (order_status.ADMIN, order_status.CUSTOMER, order_status.SHIPMENT, order_status.RETURNS)


def _order(status=S.pending, paid=False, qty=2):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=500, stock=10)
    make_cart(user, [(variant, qty)])
    order, _ = create_order_from_cart(
        user.id, address.id, "upi" if paid else "cod",
        payment_ref="pay_test_1" if paid else None, paid=paid,
    )
    if status != S.pending:
        # Straight to the state under test; the rules are what is being tested.
        Order.query.filter_by(id=order.id).update({"status": status})
        db.session.commit()
    return user, order, variant


def _stock(variant):
    db.session.expire_all()
    return db.session.get(ProductVariant, variant.id).stock_qty


def _status(order):
    db.session.expire_all()
    return db.session.get(Order, order.id).status


def _admin_set(client, order, status, headers=None):
    return client.patch(
        f"/api/admin/orders/{order.id}/status",
        json={"status": status.value}, headers=headers or admin_headers(),
    )


# ── The table itself ──────────────────────────────────────────

@pytest.mark.parametrize("final", [S.cancelled, S.returned])
def test_final_statuses_allow_nothing(final):
    for actor in ACTORS:
        assert order_status.allowed_next(final, actor) == []


def test_admin_moves_fulfilment_forward_only():
    chain = [S.pending, S.confirmed, S.packed, S.shipped, S.out_for_delivery, S.delivered]
    for i, current in enumerate(chain):
        for j, new in enumerate(chain):
            assert order_status.can_transition(current, new, order_status.ADMIN) == (j > i)


def test_admin_can_cancel_until_delivery():
    for current in (S.pending, S.confirmed, S.packed, S.shipped, S.out_for_delivery):
        assert order_status.can_transition(current, S.cancelled, order_status.ADMIN)
    assert not order_status.can_transition(S.delivered, S.cancelled, order_status.ADMIN)


def test_admin_cannot_set_return_statuses_by_hand():
    for current in S:
        for new in (S.return_requested, S.returned):
            assert not order_status.can_transition(current, new, order_status.ADMIN)
    assert order_status.allowed_next(S.return_requested, order_status.ADMIN) == []


def test_customer_rules():
    allowed = {
        (S.pending, S.cancelled), (S.confirmed, S.cancelled), (S.delivered, S.return_requested),
    }
    for current in S:
        for new in S:
            assert order_status.can_transition(current, new, order_status.CUSTOMER) == ((current, new) in allowed)


def test_same_status_is_not_a_transition():
    for actor in ACTORS:
        for status in S:
            assert not order_status.can_transition(status, status, actor)


# ── Admin path ────────────────────────────────────────────────

@pytest.mark.parametrize("current,new", [
    (S.shipped, S.packed),
    (S.delivered, S.pending),
    (S.delivered, S.cancelled),
    (S.delivered, S.returned),
    (S.pending, S.return_requested),
    (S.return_requested, S.delivered),
    (S.returned, S.delivered),
    (S.cancelled, S.confirmed),
])
def test_admin_invalid_change_is_a_409_and_changes_nothing(app, client, current, new):
    _, order, variant = _order(current, paid=True)
    stock_before = _stock(variant)

    with patch("app.routes.payments.refund_payment", return_value=True) as refund:
        resp = _admin_set(client, order, new)

    assert resp.status_code == 409
    body = resp.get_json()
    assert body["error"]
    assert body["status"] == current.value
    assert body["allowed"] == [s.value for s in order_status.allowed_next(current, order_status.ADMIN)]
    refund.assert_not_called()
    assert _status(order) == current
    assert _stock(variant) == stock_before
    assert db.session.get(Order, order.id).payment_status == PaymentStatus.paid


def test_admin_cancel_of_shipped_order_refunds_and_restocks_once(app, client):
    _, order, variant = _order(S.shipped, paid=True)
    stock_before = _stock(variant)

    with patch("app.routes.payments.refund_payment", return_value=True) as refund:
        assert _admin_set(client, order, S.cancelled).status_code == 200
        # a second attempt is "unchanged", a move elsewhere is refused
        assert _admin_set(client, order, S.cancelled).status_code == 200
        assert _admin_set(client, order, S.delivered).status_code == 409

    refund.assert_called_once()
    assert _stock(variant) == stock_before + 2


def test_admin_order_detail_lists_allowed_statuses(app, client):
    _, order, _ = _order(S.packed)
    body = client.get(f"/api/admin/orders/{order.id}", headers=admin_headers()).get_json()
    assert body["allowed_statuses"] == ["shipped", "out_for_delivery", "delivered", "cancelled"]


# ── Customer path ─────────────────────────────────────────────

@pytest.mark.parametrize("current", [
    S.packed, S.shipped, S.out_for_delivery, S.delivered, S.cancelled, S.return_requested, S.returned,
])
def test_customer_cannot_cancel_after_confirmation(app, client, current):
    user, order, variant = _order(current, paid=True)
    stock_before = _stock(variant)

    with patch("app.routes.payments.refund_payment", return_value=True) as refund:
        resp = client.post(f"/api/orders/{order.id}/cancel", headers=customer_headers(user))

    assert resp.status_code == 409
    assert resp.get_json()["error"]
    refund.assert_not_called()
    assert _status(order) == current
    assert _stock(variant) == stock_before


def test_customer_cancel_twice_refunds_once(app, client):
    user, order, variant = _order(S.confirmed, paid=True)
    stock_before = _stock(variant)

    with patch("app.routes.payments.refund_payment", return_value=True) as refund:
        first = client.post(f"/api/orders/{order.id}/cancel", headers=customer_headers(user))
        second = client.post(f"/api/orders/{order.id}/cancel", headers=customer_headers(user))

    assert (first.status_code, second.status_code) == (200, 409)
    refund.assert_called_once()
    assert _stock(variant) == stock_before + 2


@pytest.mark.parametrize("current", [S.pending, S.shipped, S.cancelled, S.returned])
def test_customer_cannot_return_what_is_not_delivered(app, client, current):
    user, order, _ = _order(current)
    resp = client.post(
        "/api/returns",
        json={"order_item_id": order.items[0].id, "reason": "changed_mind"},
        headers=customer_headers(user),
    )
    assert resp.status_code == 409
    assert Return.query.count() == 0
    assert _status(order) == current


# ── Courier booking ───────────────────────────────────────────

@pytest.mark.parametrize("current", [S.cancelled, S.delivered, S.shipped, S.returned])
def test_cannot_book_a_courier_for_an_order_that_cannot_ship(app, client, current):
    _, order, _ = _order(current)
    with patch("app.routes.admin.shipping.shiprocket") as courier:
        resp = client.post(f"/api/admin/orders/{order.id}/ship", headers=admin_headers())
    assert resp.status_code == 409
    courier.create_order.assert_not_called()
    assert _status(order) == current


# ── Returns desk ──────────────────────────────────────────────

def _open_return(client, user, order):
    resp = client.post(
        "/api/returns",
        json={"order_item_id": order.items[0].id, "reason": "changed_mind"},
        headers=customer_headers(user),
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["id"]


def test_return_cannot_be_refunded_once_the_order_is_settled_another_way(app, client):
    """Belt and braces: the rules stop an order with an open return being
    cancelled, but if it ever is, the return must not refund or restock again."""
    user, order, variant = _order(S.delivered, paid=True)
    return_id = _open_return(client, user, order)
    Order.query.filter_by(id=order.id).update({"status": S.cancelled})  # also restocks, via the trigger
    db.session.commit()
    stock_before = _stock(variant)

    with patch("app.routes.payments.refund_payment", return_value=True) as refund:
        resp = client.patch(
            f"/api/admin/returns/{return_id}",
            json={"status": "resolved", "resolution_type": "refund", "restock": True},
            headers=admin_headers(),
        )

    assert resp.status_code == 409
    refund.assert_not_called()
    assert _stock(variant) == stock_before
    assert db.session.get(Return, return_id).status == ReturnStatus.requested


def test_return_outcomes_move_the_order_by_the_rules(app, client):
    user, order, _ = _order(S.delivered)
    return_id = _open_return(client, user, order)
    assert _status(order) == S.return_requested

    # no admin shortcut while the return is open
    assert _admin_set(client, order, S.cancelled).status_code == 409

    resp = client.patch(
        f"/api/admin/returns/{return_id}",
        json={"status": "resolved", "resolution_type": "refund"},
        headers=admin_headers(),
    )
    assert resp.status_code == 200, resp.get_json()
    assert _status(order) == S.returned
    assert _admin_set(client, order, S.delivered).status_code == 409
