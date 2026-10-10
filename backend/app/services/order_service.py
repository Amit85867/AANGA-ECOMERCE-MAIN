"""Shared order-creation logic used by COD checkout and online payment verify.

Inventory deduction, coupon-usage counting and order-number assignment are all
handled by database triggers (see schema.sql: trg_deduct_inventory,
trg_coupon_usage, trg_order_number). This module must NOT repeat that work or
the effect is applied twice. It is responsible only for building the order,
its items and the initial tracking event, and for turning the trigger's
atomic stock guard into a clean API error.
"""
from datetime import datetime, timezone, timedelta

from sqlalchemy.exc import SQLAlchemyError, IntegrityError

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
    if not cart.items:
        # Nothing to ship: an empty cart must not quote the delivery charge it
        # would otherwise pick up from being under the free-shipping threshold.
        return {"subtotal": 0, "discount": 0, "gst": 0, "delivery": 0, "total": 0}

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


def refund_order_if_prepaid(order):
    """Refund a captured payment when an order is cancelled.

    Returns None when there was nothing to refund (COD, or never captured),
    otherwise True/False for the refund outcome. Does not commit — the caller
    owns the transaction that also flips the order status.

    Cancelling a prepaid order used to leave the customer's money with us: the
    only refund path was the paid-but-no-order branch of /api/payments/verify.
    """
    from flask import current_app

    if order.payment_status != PaymentStatus.paid or not order.payment_ref:
        return None

    # Imported lazily: app.routes.payments imports this module.
    from app.routes.payments import refund_payment

    amount_paise = int(round(float(order.total_amount) * 100))
    ok = refund_payment(order.payment_ref, amount_paise)
    if ok:
        order.payment_status = PaymentStatus.refunded
    else:
        current_app.logger.critical(
            "REFUND_FAILED_ON_CANCEL order=%s payment_ref=%s amount_paise=%s",
            order.order_number, order.payment_ref, amount_paise,
        )

    # Money moving is always on the trail, whoever cancelled. Not committed
    # here: it rides in the caller's transaction with the status change.
    from app.services import audit
    by_admin = audit.notes().get("by_admin", False)
    audit.record(
        "refund_on_cancel", "refunds", order.id,
        summary=(
            f"Refunded ₹{float(order.total_amount):.2f} for cancelled order "
            f"{order.order_number}" if ok else
            f"REFUND FAILED for cancelled order {order.order_number} — "
            f"₹{float(order.total_amount):.2f} must be refunded manually"
        ),
        changes={"order_number": order.order_number, "amount": float(order.total_amount),
                 "succeeded": ok},
        actor_type=None if by_admin else "customer",
        commit=False,
    )
    return ok


def create_order_from_cart(user_id, address_id, payment_method_value,
                           payment_ref=None, paid=False, idempotency_key=None):
    """Turn a user's cart into an Order.

    Returns (order, None) on success or (None, (error_message, status_code)).

    Idempotent on both ``payment_ref`` (prepaid: a payment can be verified more
    than once via gateway retries, duplicate callbacks, or an impatient user)
    and ``idempotency_key`` (COD: a double-submitted checkout). If an order
    already exists for either, we return it rather than creating a duplicate or
    charging the customer for nothing. The application-level pre-checks below
    cover the common sequential case; the DB unique indexes on those columns are
    the race-proof authority and are recovered from in the commit handler.

    Records the initial tracking event and clears the cart in one transaction.
    Stock deduction, coupon usage and the order number are applied by database
    triggers — not here.
    """
    # Idempotency guards (fast path for the common, non-racy case).
    if payment_ref:
        existing = Order.query.filter_by(payment_ref=payment_ref).first()
        if existing:
            return existing, None
    if idempotency_key:
        existing = Order.query.filter_by(idempotency_key=idempotency_key).first()
        if existing:
            return existing, None

    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart or not cart.items:
        return None, ("Cart is empty", 422)

    address = Address.query.filter_by(
        id=address_id, user_id=user_id, archived_at=None
    ).first()
    if not address:
        return None, ("Address not found", 404)

    # Friendly, early stock check. The trg_deduct_inventory trigger is the
    # atomic authority (it raises if stock would go negative under a race);
    # this just returns a clean message for the common, non-racy case.
    for ci in cart.items:
        variant = ci.variant
        if variant.stock_qty < ci.quantity:
            return None, (
                f"Insufficient stock for {variant.product.name} ({variant.size}/{variant.color_name})",
                409,
            )

    totals = compute_totals(cart)

    payment_method = PaymentMethod(payment_method_value)
    payment_status = PaymentStatus.paid if paid else PaymentStatus.pending

    order = Order(
        user_id=user_id,
        address_id=address_id,
        coupon_id=cart.coupon_id,
        order_number=None,  # assigned by trg_order_number (fires only when NULL)
        status=OrderStatus.pending,
        subtotal=totals["subtotal"],
        discount_amount=totals["discount"],
        gst_amount=totals["gst"],
        delivery_charge=totals["delivery"],
        total_amount=totals["total"],
        payment_method=payment_method,
        payment_status=payment_status,
        payment_ref=payment_ref,
        idempotency_key=idempotency_key,
        expected_delivery=datetime.now(timezone.utc).date() + timedelta(days=7),
    )
    db.session.add(order)
    db.session.flush()  # trg_order_number + trg_coupon_usage fire here

    for ci in cart.items:
        db.session.add(OrderItem(
            order_id=order.id,
            variant_id=ci.variant_id,
            quantity=ci.quantity,
            unit_price=ci.unit_price,
        ))  # trg_deduct_inventory fires per row

    db.session.add(OrderTracking(
        order_id=order.id,
        status_label="Order Placed",
        description="Your order has been placed successfully.",
        status_type=TrackingStatusType.placed,
    ))

    CartItem.query.filter_by(cart_id=cart.id).delete()
    cart.coupon_id = None

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        # A concurrent request inserted the same payment_ref / idempotency_key
        # first — the DB unique indexes are the race-proof authority. Resolve to
        # the order that won the race instead of surfacing an error.
        if payment_ref:
            existing = Order.query.filter_by(payment_ref=payment_ref).first()
            if existing:
                return existing, None
        if idempotency_key:
            existing = Order.query.filter_by(idempotency_key=idempotency_key).first()
            if existing:
                return existing, None
        raise
    except SQLAlchemyError as exc:
        db.session.rollback()
        # trg_deduct_inventory raises on a concurrent oversell.
        if "stock" in str(getattr(exc, "orig", exc)).lower():
            return None, ("Insufficient stock for one or more items", 409)
        raise

    db.session.refresh(order)  # pull the trigger-assigned order_number

    # Best-effort confirmation email — never let a mail hiccup fail the order.
    from app.services.email import send_order_confirmation
    send_order_confirmation(order)

    return order, None
