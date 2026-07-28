"""Tests for the shared order-creation logic (COD + online payment paths)."""
from app.extensions import db
from app.models.order import Order
from app.models.enums import PaymentStatus, OrderStatus
from app.services.order_service import (
    compute_totals,
    create_order_from_cart,
    DELIVERY_CHARGE,
    FREE_SHIPPING_THRESHOLD,
)
from tests.factories import (
    make_user,
    make_address,
    make_product,
    make_cart,
    make_coupon,
)
from app.models.enums import DiscountType


# ── compute_totals ────────────────────────────────────────────────────────
def test_totals_add_gst_and_delivery_below_threshold(app):
    user = make_user()
    _, variant = make_product(price=200, stock=5)
    cart = make_cart(user, [(variant, 2)])  # subtotal 400 < free-shipping

    totals = compute_totals(cart)

    assert totals["subtotal"] == 400
    assert totals["delivery"] == DELIVERY_CHARGE
    assert totals["gst"] == round(400 * 0.05, 2)
    assert totals["total"] == round(400 + totals["gst"] + DELIVERY_CHARGE, 2)


def test_totals_free_shipping_at_or_above_threshold(app):
    user = make_user()
    _, variant = make_product(price=FREE_SHIPPING_THRESHOLD, stock=5)
    cart = make_cart(user, [(variant, 1)])

    totals = compute_totals(cart)

    assert totals["delivery"] == 0


def test_totals_percentage_coupon_respects_max_discount(app):
    user = make_user()
    _, variant = make_product(price=1000, stock=5)
    coupon = make_coupon(
        code="HALF", discount_type=DiscountType.percentage,
        discount_value=50, max_discount=100,
    )
    cart = make_cart(user, [(variant, 1)], coupon=coupon)

    totals = compute_totals(cart)

    # 50% of 1000 = 500, capped at 100
    assert totals["discount"] == 100


# ── create_order_from_cart ────────────────────────────────────────────────
def test_create_order_success_deducts_stock_and_clears_cart(app):
    user = make_user()
    make_address(user)
    address = user.addresses[0]
    _, variant = make_product(price=300, stock=10)
    make_cart(user, [(variant, 3)])

    order, err = create_order_from_cart(user.id, address.id, "cod")

    assert err is None
    assert order.id is not None
    assert order.order_number.startswith("ANG-")
    assert order.status == OrderStatus.pending
    assert order.payment_status == PaymentStatus.pending
    # stock deducted
    assert variant.stock_qty == 7
    # cart emptied
    assert user.cart.items == []
    # one order item + a tracking event recorded
    assert len(order.items) == 1
    assert len(order.tracking) == 1


def test_create_order_marks_paid_when_paid_true(app):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=10)
    make_cart(user, [(variant, 1)])

    order, err = create_order_from_cart(
        user.id, address.id, "upi", payment_ref="pay_abc", paid=True
    )

    assert err is None
    assert order.payment_status == PaymentStatus.paid
    assert order.payment_ref == "pay_abc"


def test_create_order_empty_cart_returns_422(app):
    user = make_user()
    address = make_address(user)

    order, err = create_order_from_cart(user.id, address.id, "cod")

    assert order is None
    assert err == ("Cart is empty", 422)


def test_create_order_insufficient_stock_rolls_back(app):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=2)
    make_cart(user, [(variant, 5)])  # want 5, only 2 available

    order, err = create_order_from_cart(user.id, address.id, "cod")

    assert order is None
    assert err[1] == 409
    # stock untouched, cart intact, no order persisted
    db.session.refresh(variant)
    assert variant.stock_qty == 2
    assert Order.query.count() == 0
    assert len(user.cart.items) == 1


# ── Regression: DB triggers own inventory/coupons, app must not repeat them ──
def test_stock_deducted_exactly_once(app):
    """trg_deduct_inventory is the only place stock is reduced."""
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=10)
    make_cart(user, [(variant, 3)])

    create_order_from_cart(user.id, address.id, "cod")

    db.session.refresh(variant)
    assert variant.stock_qty == 7  # 10 - 3, not 10 - 6


def test_coupon_usage_incremented_exactly_once(app):
    """trg_coupon_usage bumps used_count once; the app must not also do it."""
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=1000, stock=5)
    coupon = make_coupon(code="ONCE", discount_type=DiscountType.flat, discount_value=100)
    make_cart(user, [(variant, 1)], coupon=coupon)

    order, err = create_order_from_cart(user.id, address.id, "cod")

    assert err is None
    db.session.refresh(coupon)
    assert coupon.used_count == 1


def test_order_number_assigned_by_trigger(app):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=10)
    make_cart(user, [(variant, 1)])

    order, err = create_order_from_cart(user.id, address.id, "cod")

    assert err is None
    # Format from generate_order_number(): ANG-<year>-<order_seq>
    assert order.order_number.startswith("ANG-")
    assert order.order_number.count("-") == 2


def test_cancel_restores_stock_exactly_once(app):
    """trg_restore_inventory restores on cancel; the app must not also do it."""
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=10)
    make_cart(user, [(variant, 4)])
    order, _ = create_order_from_cart(user.id, address.id, "cod")
    db.session.refresh(variant)
    assert variant.stock_qty == 6

    # Flip to cancelled — mirrors what the cancel route does (trigger fires).
    order.status = OrderStatus.cancelled
    db.session.commit()

    db.session.refresh(variant)
    assert variant.stock_qty == 10  # restored once, not 14


def test_prepaid_verify_is_idempotent(app):
    """Verifying the same payment twice returns the same order, not a duplicate."""
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=300, stock=10)
    make_cart(user, [(variant, 2)])

    order1, err1 = create_order_from_cart(
        user.id, address.id, "upi", payment_ref="pay_dup", paid=True
    )
    order2, err2 = create_order_from_cart(
        user.id, address.id, "upi", payment_ref="pay_dup", paid=True
    )

    assert err1 is None and err2 is None
    assert order1.id == order2.id
    assert Order.query.count() == 1
    # stock only deducted for the first creation
    db.session.refresh(variant)
    assert variant.stock_qty == 8
