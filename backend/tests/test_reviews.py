"""Review submission: the "verified purchase" badge must be unforgeable.

The badge used to be set from a client-supplied ``order_item_id`` with no
ownership or product check, so any logged-in user could claim it by sending an
arbitrary integer. It is now resolved server-side from the reviewer's own
delivered orders.
"""
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.models.engagement import ProductReview
from app.models.enums import OrderStatus
from app.services.order_service import create_order_from_cart
from tests.factories import make_user, make_address, make_product, make_cart


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token(identity=str(user.id))}"}


def _deliver_an_order(user, variant):
    address = make_address(user)
    make_cart(user, [(variant, 1)])
    order, err = create_order_from_cart(user.id, address.id, "cod")
    assert err is None, err
    order.status = OrderStatus.delivered
    db.session.commit()
    return order


def test_review_from_non_buyer_is_not_verified(app, client):
    buyer = make_user()
    product, variant = make_product(price=500, stock=10)
    _deliver_an_order(buyer, variant)

    # A different user who never bought the product.
    stranger = make_user()
    resp = client.post("/api/reviews", json={
        "product_id": product.id, "rating": 5, "body": "Great!",
    }, headers=_headers(stranger))

    assert resp.status_code == 201
    assert resp.get_json()["is_verified"] is False
    review = db.session.get(ProductReview, resp.get_json()["id"])
    assert review.is_verified is False
    assert review.order_item_id is None


def test_client_supplied_order_item_id_cannot_forge_the_badge(app, client):
    """Regression: passing someone else's order_item_id used to set is_verified.

    The field is no longer part of the input schema at all, so an attempt to
    supply it is rejected outright rather than silently ignored — which makes
    the change visible to any caller still sending it.
    """
    buyer = make_user()
    product, variant = make_product(price=500, stock=10)
    order = _deliver_an_order(buyer, variant)
    victim_item_id = order.items[0].id

    stranger = make_user()
    resp = client.post("/api/reviews", json={
        "product_id": product.id,
        "order_item_id": victim_item_id,   # not this user's order item
        "rating": 5,
    }, headers=_headers(stranger))

    assert resp.status_code == 422
    assert "order_item_id" in resp.get_json()["errors"]
    assert ProductReview.query.filter_by(user_id=stranger.id).count() == 0


def test_real_buyer_gets_the_verified_badge(app, client):
    buyer = make_user()
    product, variant = make_product(price=500, stock=10)
    order = _deliver_an_order(buyer, variant)

    resp = client.post("/api/reviews", json={
        "product_id": product.id, "rating": 4, "body": "Good fabric.",
    }, headers=_headers(buyer))

    assert resp.status_code == 201
    assert resp.get_json()["is_verified"] is True
    assert db.session.get(ProductReview, resp.get_json()["id"]).order_item_id == order.items[0].id


def test_undelivered_order_does_not_verify(app, client):
    """A placed-but-not-delivered order is not yet a verified purchase."""
    buyer = make_user()
    product, variant = make_product(price=500, stock=10)
    address = make_address(buyer)
    make_cart(buyer, [(variant, 1)])
    create_order_from_cart(buyer.id, address.id, "cod")  # stays pending

    resp = client.post("/api/reviews", json={
        "product_id": product.id, "rating": 5,
    }, headers=_headers(buyer))

    assert resp.status_code == 201
    assert resp.get_json()["is_verified"] is False


def test_out_of_range_rating_is_rejected_cleanly(app, client):
    """Regression: an unbounded rating hit ck_review_rating and 500'd."""
    user = make_user()
    product, _ = make_product(price=500, stock=10)

    for bad in (0, 6, 99, -1):
        resp = client.post("/api/reviews", json={
            "product_id": product.id, "rating": bad,
        }, headers=_headers(user))
        assert resp.status_code == 422, f"rating={bad} returned {resp.status_code}"


def test_duplicate_review_is_rejected(app, client):
    user = make_user()
    product, _ = make_product(price=500, stock=10)
    payload = {"product_id": product.id, "rating": 5}

    assert client.post("/api/reviews", json=payload, headers=_headers(user)).status_code == 201
    assert client.post("/api/reviews", json=payload, headers=_headers(user)).status_code == 409


def test_review_requires_authentication(app, client):
    product, _ = make_product(price=500, stock=10)
    resp = client.post("/api/reviews", json={"product_id": product.id, "rating": 5})
    assert resp.status_code == 401
