"""Route-level tests for the Razorpay verify endpoint.

The gateway is not called on /verify — it only checks the HMAC signature and
then creates the order — so we can exercise the whole endpoint by computing a
valid signature with a known secret.
"""
import hmac
import hashlib

import pytest
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models.order import Order
from tests.factories import make_user, make_address, make_product, make_cart

SECRET = "test_secret_key"


@pytest.fixture(autouse=True)
def _razorpay_keys(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_x")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", SECRET)


def _sign(order_id, payment_id):
    return hmac.new(
        SECRET.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256
    ).hexdigest()


def _auth_headers(app, user):
    with app.app_context():
        token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def _verify_payload(address, payment_id="pay_1", order_id="order_1"):
    return {
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": _sign(order_id, payment_id),
        "address_id": address.id,
        "payment_method": "upi",
    }


def test_verify_creates_paid_order(app, client):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=5)
    make_cart(user, [(variant, 2)])

    resp = client.post(
        "/api/payments/verify",
        json=_verify_payload(address),
        headers=_auth_headers(app, user),
    )

    assert resp.status_code == 201
    assert resp.get_json()["order_number"].startswith("ANG-")
    assert Order.query.count() == 1


def test_verify_rejects_bad_signature(app, client):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=5)
    make_cart(user, [(variant, 1)])

    payload = _verify_payload(address)
    payload["razorpay_signature"] = "deadbeef"
    resp = client.post(
        "/api/payments/verify", json=payload, headers=_auth_headers(app, user)
    )

    assert resp.status_code == 400
    assert Order.query.count() == 0


def test_verify_is_idempotent(app, client):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=5)
    make_cart(user, [(variant, 2)])

    headers = _auth_headers(app, user)
    payload = _verify_payload(address, payment_id="pay_same")

    r1 = client.post("/api/payments/verify", json=payload, headers=headers)
    r2 = client.post("/api/payments/verify", json=payload, headers=headers)

    assert r1.status_code == 201
    # Second call must not create a duplicate order.
    assert Order.query.count() == 1
    assert r2.get_json().get("order_id") == r1.get_json().get("order_id") or \
        r2.status_code in (201, 409)


def test_verify_paid_but_no_stock_does_not_lose_payment(app, client):
    """Payment captured but stock gone → 409 that echoes the payment ref."""
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=1)
    make_cart(user, [(variant, 5)])  # cart wants more than is in stock

    resp = client.post(
        "/api/payments/verify",
        json=_verify_payload(address, payment_id="pay_orphan"),
        headers=_auth_headers(app, user),
    )

    assert resp.status_code == 409
    body = resp.get_json()
    assert body["payment_ref"] == "pay_orphan"
    assert Order.query.count() == 0
