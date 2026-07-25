"""Route-level tests for POST /api/orders (COD checkout).

Guards the two holes closed in Phase 1:
  * a client must never be able to declare its own order paid, and
  * a double-submitted checkout must resolve to a single order.
"""
from flask_jwt_extended import create_access_token

from app.models.order import Order
from app.models.enums import PaymentStatus
from tests.factories import make_user, make_address, make_product, make_cart


def _auth_headers(app, user):
    with app.app_context():
        token = create_access_token(identity=str(user.id))
    return {"Authorization": f"Bearer {token}"}


def test_cod_order_is_never_paid_even_with_injected_payment_ref(app, client):
    """A forged payment_ref in the body must not mark the order paid."""
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=5)
    make_cart(user, [(variant, 1)])

    resp = client.post(
        "/api/orders",
        json={
            "address_id": address.id,
            "payment_method": "cod",
            "payment_ref": "totally_forged",  # attacker-supplied
        },
        headers=_auth_headers(app, user),
    )

    assert resp.status_code == 201
    order = Order.query.one()
    assert order.payment_status == PaymentStatus.pending
    assert order.payment_ref is None


def test_cod_double_submit_with_idempotency_key_places_one_order(app, client):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=5)
    make_cart(user, [(variant, 2)])

    headers = _auth_headers(app, user)
    headers["Idempotency-Key"] = "checkout-abc-123"
    payload = {"address_id": address.id, "payment_method": "cod"}

    r1 = client.post("/api/orders", json=payload, headers=headers)
    r2 = client.post("/api/orders", json=payload, headers=headers)

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.get_json()["order_id"] == r2.get_json()["order_id"]
    assert Order.query.count() == 1
    # Stock deducted once, not twice.
    from app.extensions import db
    db.session.refresh(variant)
    assert variant.stock_qty == 3
