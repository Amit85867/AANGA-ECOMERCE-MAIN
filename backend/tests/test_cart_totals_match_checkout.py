"""The price shown in the cart must be the price the order charges.

The cart used to re-implement the GST / free-shipping / coupon maths that
order_service.compute_totals already owned. Two copies of pricing logic drift,
and the failure mode is the worst kind: the customer is quoted one number and
charged another.
"""
from flask_jwt_extended import create_access_token

from app.services.order_service import compute_totals, create_order_from_cart
from app.models.cart import Cart
from app.models.enums import DiscountType
from tests.factories import (
    make_user, make_address, make_product, make_cart, make_coupon,
)


def _headers(user):
    return {"Authorization": f"Bearer {create_access_token(identity=str(user.id))}"}


def _cart_body(client, user):
    resp = client.get("/api/cart", headers=_headers(user))
    assert resp.status_code == 200
    return resp.get_json()


def test_cart_totals_match_compute_totals_below_free_shipping(app, client):
    user = make_user()
    _, variant = make_product(price=200, stock=10)
    cart = make_cart(user, [(variant, 2)])   # 400, under the threshold

    body = _cart_body(client, user)
    expected = compute_totals(cart)

    assert body["subtotal"] == expected["subtotal"]
    assert body["gst"] == expected["gst"]
    assert body["delivery_charge"] == expected["delivery"]
    assert body["total"] == expected["total"]


def test_cart_totals_match_compute_totals_with_free_shipping(app, client):
    user = make_user()
    _, variant = make_product(price=1200, stock=10)
    cart = make_cart(user, [(variant, 1)])

    body = _cart_body(client, user)
    expected = compute_totals(cart)

    assert body["delivery_charge"] == 0 == expected["delivery"]
    assert body["total"] == expected["total"]


def test_cart_totals_match_compute_totals_with_capped_percentage_coupon(app, client):
    user = make_user()
    _, variant = make_product(price=1000, stock=10)
    coupon = make_coupon(
        code="HALF", discount_type=DiscountType.percentage,
        discount_value=50, max_discount=200,
    )
    cart = make_cart(user, [(variant, 2)], coupon=coupon)

    body = _cart_body(client, user)
    expected = compute_totals(cart)

    assert body["discount"] == expected["discount"] == 200  # capped, not 1000
    assert body["gst"] == expected["gst"]
    assert body["total"] == expected["total"]


def test_cart_total_equals_the_amount_the_order_charges(app, client):
    """End to end: whatever the cart quoted is what the order records."""
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=700, stock=10)
    coupon = make_coupon(code="TENOFF", discount_type=DiscountType.flat, discount_value=100)
    make_cart(user, [(variant, 2)], coupon=coupon)

    quoted = _cart_body(client, user)["total"]

    order, err = create_order_from_cart(user.id, address.id, "cod")
    assert err is None, err

    assert float(order.total_amount) == quoted


def test_empty_cart_totals_are_zero_not_a_delivery_charge(app, client):
    """An empty cart is under the free-shipping threshold, so the naive rule
    would quote a delivery charge on a cart with nothing to deliver."""
    user = make_user()

    body = _cart_body(client, user)

    assert body["subtotal"] == 0
    assert body["item_count"] == 0
    assert body["delivery_charge"] == 0
    assert body["total"] == 0
    assert compute_totals(Cart.query.filter_by(user_id=user.id).first())["total"] == 0
