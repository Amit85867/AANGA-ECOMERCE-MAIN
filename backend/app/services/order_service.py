"""Shared order-creation logic used by COD checkout and online payment verify."""
from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.models.order import Order, OrderItem, OrderTracking
from app.models.cart import Cart, CartItem
from app.models.user import Address
from app.models.enums import (
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    TrackingStatusType,
)

GST_RATE = 0.05
FREE_SHIPPING_THRESHOLD = 999
DELIVERY_CHARGE = 49


def compute_totals(cart):
    """Compute subtotal, discount, gst, delivery, and total for a cart."""
    subtotal = sum(float(ci.unit_price) * ci.quantity for ci in cart.items)
    discount = 0
    if cart.coupon:
        if cart.coupon.discount_type.value == "percentage":
            discount = subtotal * float(cart.coupon.discount_value) / 100
            if cart.coupon.max_discount:
                discount = min(discount, float(cart.coupon.max_discount))
        else:
            discount = float(cart.coupon.discount_value)

    after_discount = subtotal - discount
    gst = round(after_discount * GST_RATE, 2)
    delivery = 0 if subtotal >= FREE_SHIPPING_THRESHOLD else DELIVERY_CHARGE
    total = round(after_discount + gst + delivery, 2)
    return {
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "gst": gst,
        "delivery": delivery,
        "total": total,
    }


def create_order_from_cart(user_id, address_id, payment_method_value, payment_ref=None, paid=False):
    """Turn a user's cart into an Order.

    Returns (order, None) on success or (None, (error_message, status_code)).
    Deducts stock, records the initial tracking event, consumes the coupon,
    and clears the cart — all in one transaction.
    """
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart or not cart.items:
        return None, ("Cart is empty", 422)

    address = Address.query.filter_by(id=address_id, user_id=user_id).first()
    if not address:
        return None, ("Address not found", 404)

    totals = compute_totals(cart)

    payment_method = PaymentMethod(payment_method_value)
    payment_status = PaymentStatus.paid if paid else PaymentStatus.pending

    order = Order(
        user_id=user_id,
        address_id=address_id,
        coupon_id=cart.coupon_id,
        order_number="",
        status=OrderStatus.pending,
        subtotal=totals["subtotal"],
        discount_amount=totals["discount"],
        gst_amount=totals["gst"],
        delivery_charge=totals["delivery"],
        total_amount=totals["total"],
        payment_method=payment_method,
        payment_status=payment_status,
        payment_ref=payment_ref,
        expected_delivery=datetime.now(timezone.utc).date() + timedelta(days=7),
    )
    db.session.add(order)
    db.session.flush()

    order.order_number = f"ANG-{datetime.now().year}-{order.id}"

    for ci in cart.items:
        variant = ci.variant
        if variant.stock_qty < ci.quantity:
            db.session.rollback()
            return None, (
                f"Insufficient stock for {variant.product.name} ({variant.size}/{variant.color_name})",
                409,
            )
        variant.stock_qty -= ci.quantity
        db.session.add(OrderItem(
            order_id=order.id,
            variant_id=ci.variant_id,
            quantity=ci.quantity,
            unit_price=ci.unit_price,
        ))

    db.session.add(OrderTracking(
        order_id=order.id,
        status_label="Order Placed",
        description="Your order has been placed successfully.",
        status_type=TrackingStatusType.placed,
    ))

    if cart.coupon:
        cart.coupon.used_count += 1

    CartItem.query.filter_by(cart_id=cart.id).delete()
    cart.coupon_id = None

    db.session.commit()
    return order, None
