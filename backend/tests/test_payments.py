"""Route-level tests for the Razorpay verify endpoint.

/verify checks the HMAC signature AND reconciles the payment against the
gateway (captured status, matching order, matching amount) before creating the
order. The gateway fetch/refund calls are mocked here so no network is touched;
a valid signature is computed with a known secret.
"""
import hmac
import hashlib

import pytest
from flask_jwt_extended import create_access_token

from app.models.order import Order
from app.services.order_service import compute_totals
from tests.factories import make_user, make_address, make_product, make_cart

SECRET = "test_secret_key"


@pytest.fixture(autouse=True)
def _razorpay_keys(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_x")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", SECRET)


class FakeGateway:
    """Stand-in for Razorpay's payment fetch + refund."""

    def __init__(self):
        self.status = "captured"
        self.amount = None        # set per test to the expected paise
        self.order_id = "order_1"
        self.refund_ok = True
        self.refunds = []         # records (payment_id, amount) calls

    def payment(self, _payment_id):
        return {"status": self.status, "order_id": self.order_id, "amount": self.amount}

    def refund(self, payment_id, amount_paise=None):
        self.refunds.append((payment_id, amount_paise))
        return self.refund_ok


@pytest.fixture
def gateway(monkeypatch):
    gw = FakeGateway()
    monkeypatch.setattr("app.routes.payments.fetch_payment", gw.payment)
    monkeypatch.setattr("app.routes.payments.refund_payment", gw.refund)
    return gw


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


def _paise(cart):
    return int(round(compute_totals(cart)["total"] * 100))


def test_verify_creates_paid_order(app, client, gateway):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=5)
    cart = make_cart(user, [(variant, 2)])
    gateway.amount = _paise(cart)

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


def test_verify_is_idempotent(app, client, gateway):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=5)
    cart = make_cart(user, [(variant, 2)])
    gateway.amount = _paise(cart)

    headers = _auth_headers(app, user)
    payload = _verify_payload(address, payment_id="pay_same")

    r1 = client.post("/api/payments/verify", json=payload, headers=headers)
    r2 = client.post("/api/payments/verify", json=payload, headers=headers)

    assert r1.status_code == 201
    # Second call must not create a duplicate order; it returns the same one.
    assert r2.status_code == 200
    assert Order.query.count() == 1
    assert r2.get_json()["order_id"] == r1.get_json()["order_id"]


def test_verify_rejects_amount_mismatch(app, client, gateway):
    """The gateway amount must equal the server-computed order total."""
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=5)
    cart = make_cart(user, [(variant, 2)])
    gateway.amount = _paise(cart) - 1  # underpaid by one paisa

    resp = client.post(
        "/api/payments/verify",
        json=_verify_payload(address),
        headers=_auth_headers(app, user),
    )

    assert resp.status_code == 400
    assert Order.query.count() == 0


def test_verify_rejects_uncaptured_payment(app, client, gateway):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=5)
    cart = make_cart(user, [(variant, 2)])
    gateway.amount = _paise(cart)
    gateway.status = "authorized"  # not yet captured

    resp = client.post(
        "/api/payments/verify",
        json=_verify_payload(address),
        headers=_auth_headers(app, user),
    )

    assert resp.status_code == 400
    assert Order.query.count() == 0


def test_verify_rejects_mismatched_order(app, client, gateway):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=5)
    cart = make_cart(user, [(variant, 2)])
    gateway.amount = _paise(cart)
    gateway.order_id = "order_someone_else"  # payment belongs to another order

    resp = client.post(
        "/api/payments/verify",
        json=_verify_payload(address),  # payload says order_1
        headers=_auth_headers(app, user),
    )

    assert resp.status_code == 400
    assert Order.query.count() == 0


def test_verify_paid_but_no_stock_auto_refunds(app, client, gateway):
    """Payment captured but stock gone → auto-refund, no order, 409."""
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=1)
    cart = make_cart(user, [(variant, 5)])  # cart wants more than is in stock
    expected = _paise(cart)
    gateway.amount = expected

    resp = client.post(
        "/api/payments/verify",
        json=_verify_payload(address, payment_id="pay_orphan"),
        headers=_auth_headers(app, user),
    )

    assert resp.status_code == 409
    body = resp.get_json()
    assert body["payment_ref"] == "pay_orphan"
    assert body["refunded"] is True
    assert gateway.refunds == [("pay_orphan", expected)]
    assert Order.query.count() == 0
