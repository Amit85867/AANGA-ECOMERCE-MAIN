"""Orders: place, list, detail, cancel."""
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy.orm import selectinload
from marshmallow import ValidationError

from app.extensions import db, limiter
from app.models.order import Order, OrderItem, OrderTracking
from app.models.cart import Cart, CartItem
from app.models.catalogue import ProductVariant
from app.models.enums import OrderStatus, TrackingStatusType
from app.schemas.order import PlaceOrderIn, OrderListOut, OrderDetailOut
from app.services.catalogue import primary_images
from app.services.order_service import create_order_from_cart, refund_order_if_prepaid
from app.utils.pagination import page_meta, paginate

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")

_place_in = PlaceOrderIn()
_list_out = OrderListOut(many=True)
_detail_out = OrderDetailOut()


@orders_bp.route("", methods=["POST"])
@limiter.limit("30 per hour")
@jwt_required()
def place_order():
    try:
        data = _place_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    # This route always creates an UNPAID (pending) order — typically COD.
    # Payment is never asserted by the client here; prepaid orders are created
    # only by /api/payments/verify, which validates the gateway signature and
    # the amount. So `paid` is hard-coded False and no client `payment_ref` is
    # accepted (see PlaceOrderIn).
    #
    # An optional Idempotency-Key header lets a retried/double-submitted COD
    # checkout resolve to the same order instead of placing two.
    idempotency_key = request.headers.get("Idempotency-Key") or None

    order, err = create_order_from_cart(
        get_jwt_identity(),
        data["address_id"],
        data["payment_method"],
        paid=False,
        idempotency_key=idempotency_key,
    )
    if err:
        return jsonify(error=err[0]), err[1]

    return jsonify(order_number=order.order_number, order_id=order.id), 201


@orders_bp.route("", methods=["GET"])
@jwt_required()
def list_orders():
    page = paginate(
        Order.query
        .options(selectinload(Order.items).joinedload(OrderItem.variant).joinedload(ProductVariant.product))
        .filter_by(user_id=get_jwt_identity())
        .order_by(Order.placed_at.desc()),
        default=20, cap=50,
    )
    orders = page.items

    result = []
    for o in orders:
        first_item = o.items[0] if o.items else None
        summary = ""
        if first_item:
            summary = first_item.variant.product.name
            if len(o.items) > 1:
                summary += f" + {len(o.items) - 1} more"

        result.append({
            "id": o.id,
            "order_number": o.order_number,
            "status": o.status.value,
            "total_amount": float(o.total_amount),
            "item_summary": summary,
            "item_count": sum(i.quantity for i in o.items),
            "placed_at": o.placed_at,
            "expected_delivery": o.expected_delivery,
        })

    return jsonify(orders=_list_out.dump(result), **page_meta(page)), 200


@orders_bp.route("/<int:order_id>", methods=["GET"])
@jwt_required()
def order_detail(order_id):
    order = Order.query.filter_by(id=order_id, user_id=get_jwt_identity()).first()
    if not order:
        return jsonify(error="Order not found"), 404

    images = primary_images(oi.variant.product_id for oi in order.items)

    items = []
    for oi in order.items:
        variant = oi.variant
        product = variant.product
        items.append({
            "id": oi.id,
            "product_name": product.name,
            "product_slug": product.slug,
            "size": variant.size,
            "color_name": variant.color_name,
            "image_url": images.get(product.id),
            "quantity": oi.quantity,
            "unit_price": float(oi.unit_price),
            "total_price": float(oi.total_price) if oi.total_price else float(oi.unit_price) * oi.quantity,
        })

    tracking_events = [
        {
            "id": t.id,
            "status_label": t.status_label,
            "description": t.description,
            "status_type": t.status_type.value,
            "event_time": t.event_time,
        }
        for t in sorted(order.tracking, key=lambda t: t.event_time)
    ]

    addr = order.address
    address_data = {
        "full_name": addr.full_name,
        "phone": addr.phone,
        "line1": addr.line1,
        "line2": addr.line2,
        "city": addr.city,
        "state": addr.state,
        "pin_code": addr.pin_code,
    }

    data = {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status.value,
        "subtotal": float(order.subtotal),
        "discount_amount": float(order.discount_amount),
        "gst_amount": float(order.gst_amount),
        "delivery_charge": float(order.delivery_charge),
        "total_amount": float(order.total_amount),
        "payment_method": order.payment_method.value,
        "payment_status": order.payment_status.value,
        "courier_name": order.courier_name,
        "tracking_number": order.tracking_number,
        "expected_delivery": order.expected_delivery,
        "placed_at": order.placed_at,
        "items": items,
        "tracking": tracking_events,
        "address": address_data,
    }

    return jsonify(_detail_out.dump(data)), 200


@orders_bp.route("/<int:order_id>/cancel", methods=["POST"])
@limiter.limit("30 per hour")
@jwt_required()
def cancel_order(order_id):
    order = Order.query.filter_by(id=order_id, user_id=get_jwt_identity()).first()
    if not order:
        return jsonify(error="Order not found"), 404

    cancellable = {OrderStatus.pending, OrderStatus.confirmed}
    if order.status not in cancellable:
        return jsonify(error="Order cannot be cancelled at this stage"), 422

    # Stock is restored by the trg_restore_inventory trigger when the status
    # flips to 'cancelled' — do not add it back here as well.
    order.status = OrderStatus.cancelled

    # A prepaid order cancelled by the customer must return their money.
    refunded = refund_order_if_prepaid(order)

    tracking = OrderTracking(
        order_id=order.id,
        status_label="Order Cancelled",
        description="Order cancelled by customer.",
        status_type=TrackingStatusType.returned,
    )
    db.session.add(tracking)
    db.session.commit()

    if refunded is False:
        return jsonify(
            message="Order cancelled. Your refund could not be processed "
                    "automatically — our team has been notified and will "
                    "complete it shortly.",
            refunded=False,
        ), 200

    payload = {"message": "Order cancelled"}
    if refunded is True:
        payload["message"] = "Order cancelled and your payment has been refunded."
        payload["refunded"] = True
    return jsonify(payload), 200
