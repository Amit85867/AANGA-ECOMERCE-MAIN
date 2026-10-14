"""Razorpay webhook: signature enforcement and orphaned-capture handling.

The hole this closes: a customer whose browser dies between capture and
/api/payments/verify is charged with no order and nothing to notice it.
"""
import hmac
import json
import time
import hashlib
from unittest.mock import patch

import pytest

from app.extensions import db
from app.models.order import Order
from app.models.enums import PaymentStatus
from app.services.order_service import create_order_from_cart
from tests.factories import make_user, make_address, make_product, make_cart

SECRET = "whsec_test_secret"


@pytest.fixture(autouse=True)
def _webhook_secret(monkeypatch):
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", SECRET)


def _post(client, event, secret=SECRET):
    raw = json.dumps(event).encode()
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return client.post(
        "/api/payments/webhook",
        data=raw,
        content_type="application/json",
        headers={"X-Razorpay-Signature": sig},
    )


def _captured_event(payment_id, amount=52500, age_seconds=0):
    return {
        "event": "payment.captured",
        "payload": {"payment": {"entity": {
            "id": payment_id,
            "amount": amount,
            "status": "captured",
            "created_at": int(time.time()) - age_seconds,
        }}},
    }


def _paid_order(payment_ref):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=500, stock=10)
    make_cart(user, [(variant, 1)])
    order, err = create_order_from_cart(
        user.id, address.id, "upi", payment_ref=payment_ref, paid=True
    )
    assert err is None, err
    return order


def test_bad_signature_is_rejected(app, client):
    raw = json.dumps(_captured_event("pay_X")).encode()
    resp = client.post(
        "/api/payments/webhook",
        data=raw,
        content_type="application/json",
        headers={"X-Razorpay-Signature": "deadbeef"},
    )
    assert resp.status_code == 400


def test_missing_signature_is_rejected(app, client):
    resp = client.post(
        "/api/payments/webhook",
        data=json.dumps(_captured_event("pay_X")).encode(),
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_signature_from_wrong_secret_is_rejected(app, client):
    resp = _post(client, _captured_event("pay_X"), secret="the_wrong_secret")
    assert resp.status_code == 400


def test_capture_with_existing_order_is_a_no_op(app, client):
    """The normal path: /verify already created the order, nothing to refund."""
    _paid_order("pay_HASORDER")

    with patch("app.routes.payments.refund_payment") as refund:
        resp = _post(client, _captured_event("pay_HASORDER", age_seconds=99999))

    assert resp.status_code == 200
    refund.assert_not_called()


def test_recent_orphan_is_left_alone(app, client):
    """A capture seconds old is an in-flight checkout, not an abandoned one —
    refunding it would cancel a legitimate order mid-flight."""
    with patch("app.routes.payments.refund_payment") as refund:
        resp = _post(client, _captured_event("pay_INFLIGHT", age_seconds=5))

    assert resp.status_code == 200
    refund.assert_not_called()


def test_stale_orphan_is_refunded(app, client):
    """Past the grace window with no order, the money goes back."""
    with patch("app.routes.payments.refund_payment", return_value=True) as refund:
        resp = _post(client, _captured_event("pay_ORPHAN", amount=52500, age_seconds=7200))

    assert resp.status_code == 200
    refund.assert_called_once_with("pay_ORPHAN", 52500)


def test_failed_payment_marks_the_order(app, client):
    order = _paid_order("pay_WILLFAIL")

    resp = _post(client, {
        "event": "payment.failed",
        "payload": {"payment": {"entity": {"id": "pay_WILLFAIL"}}},
    })

    assert resp.status_code == 200
    db.session.expire_all()
    assert db.session.get(Order, order.id).payment_status == PaymentStatus.failed


def test_refund_processed_marks_the_order_refunded(app, client):
    order = _paid_order("pay_REFUNDED")

    resp = _post(client, {
        "event": "refund.processed",
        "payload": {"refund": {"entity": {
            "id": "rfnd_1", "payment_id": "pay_REFUNDED",
        }}},
    })

    assert resp.status_code == 200
    db.session.expire_all()
    assert db.session.get(Order, order.id).payment_status == PaymentStatus.refunded


def test_unknown_event_is_acknowledged(app, client):
    """Razorpay retries non-2xx; an event we do not model is not an error."""
    resp = _post(client, {"event": "payment.authorized", "payload": {}})
    assert resp.status_code == 200


def test_malformed_body_is_rejected(app, client):
    raw = b"{not json"
    sig = hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()
    resp = client.post(
        "/api/payments/webhook", data=raw,
        content_type="application/json",
        headers={"X-Razorpay-Signature": sig},
    )
    assert resp.status_code == 400


def test_webhook_disabled_without_a_secret(app, client, monkeypatch):
    monkeypatch.delenv("RAZORPAY_WEBHOOK_SECRET", raising=False)
    resp = _post(client, _captured_event("pay_X"))
    assert resp.status_code == 503
