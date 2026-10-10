"""Admin order management: list, detail, update status, add tracking, manage returns."""
from flask import request, jsonify, current_app
from marshmallow import ValidationError

from app.extensions import db
from app.models.order import Order, OrderItem, OrderTracking, Return
from app.models.catalogue import ProductImage
from app.models.user import User
from app.models.enums import (
    OrderStatus,
    PaymentStatus,
    TrackingStatusType,
    ReturnStatus,
    ResolutionType,
)
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.schemas.admin import AdminOrderStatusIn, AdminTrackingIn, AdminReturnUpdateIn
from app.services.order_service import refund_order_if_prepaid

_status_in = AdminOrderStatusIn()
_tracking_in = AdminTrackingIn()
_return_in = AdminReturnUpdateIn()


def _serialize_order_list(o):
    user = db.session.get(User, o.user_id)
    return {
        "id": o.id,
        "order_number": o.order_number,
        "status": o.status.value,
        "total_amount": float(o.total_amount),
        "payment_method": o.payment_method.value,
        "payment_status": o.payment_status.value,
        "item_count": sum(i.quantity for i in o.items),
        "customer_name": user.full_name if user else "Unknown",
        "customer_email": user.email if user else None,
        "placed_at": o.placed_at.isoformat(),
        "expected_delivery": o.expected_delivery.isoformat() if o.expected_delivery else None,
    }


@admin_bp.route("/orders", methods=["GET"])
@admin_required
def admin_list_orders():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    status = request.args.get("status")
    search = request.args.get("q")

    q = Order.query

    if status:
        try:
            q = q.filter_by(status=OrderStatus(status))
        except ValueError:
            pass

    if search:
        q = q.filter(Order.order_number.ilike(f"%{search}%"))

    paginated = q.order_by(Order.placed_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify(
        orders=[_serialize_order_list(o) for o in paginated.items],
        page=paginated.page,
        pages=paginated.pages,
        total=paginated.total,
    ), 200


@admin_bp.route("/orders/<int:order_id>", methods=["GET"])
@admin_required
def admin_order_detail(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify(error="Order not found"), 404

    user = db.session.get(User, order.user_id)
    addr = order.address

    items = []
    for oi in order.items:
        variant = oi.variant
        product = variant.product
        primary = (
            ProductImage.query
            .filter_by(product_id=product.id, is_primary=True)
            .first()
        )
        items.append({
            "id": oi.id,
            "product_name": product.name,
            "product_slug": product.slug,
            "size": variant.size,
            "color_name": variant.color_name,
            "color_hex": variant.color_hex,
            "image_url": primary.image_url if primary else None,
            "quantity": oi.quantity,
            "unit_price": float(oi.unit_price),
            "total_price": float(oi.total_price) if oi.total_price else float(oi.unit_price) * oi.quantity,
            "sku": variant.sku,
        })

    tracking_events = [
        {
            "id": t.id,
            "status_label": t.status_label,
            "description": t.description,
            "status_type": t.status_type.value,
            "event_time": t.event_time.isoformat(),
        }
        for t in sorted(order.tracking, key=lambda t: t.event_time)
    ]

    return jsonify(
        id=order.id,
        order_number=order.order_number,
        status=order.status.value,
        subtotal=float(order.subtotal),
        discount_amount=float(order.discount_amount),
        gst_amount=float(order.gst_amount),
        delivery_charge=float(order.delivery_charge),
        total_amount=float(order.total_amount),
        payment_method=order.payment_method.value,
        payment_status=order.payment_status.value,
        payment_ref=order.payment_ref,
        courier_name=order.courier_name,
        tracking_number=order.tracking_number,
        expected_delivery=order.expected_delivery.isoformat() if order.expected_delivery else None,
        placed_at=order.placed_at.isoformat(),
        customer={
            "id": str(user.id) if user else None,
            "full_name": user.full_name if user else "Unknown",
            "email": user.email if user else None,
            "phone": user.phone if user else None,
        },
        address={
            "full_name": addr.full_name,
            "phone": addr.phone,
            "line1": addr.line1,
            "line2": addr.line2,
            "city": addr.city,
            "state": addr.state,
            "pin_code": addr.pin_code,
        } if addr else None,
        items=items,
        tracking=tracking_events,
    ), 200


@admin_bp.route("/orders/<int:order_id>/status", methods=["PATCH"])
@admin_required
def update_order_status(order_id):
    try:
        data = _status_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    order = db.session.get(Order, order_id)
    if not order:
        return jsonify(error="Order not found"), 404

    new_status = OrderStatus(data["status"])
    previous_status = order.status

    if new_status == previous_status:
        return jsonify(message="Status unchanged", status=new_status.value), 200

    # Cancelling a cancelled order must not run the side effects twice. The
    # status guard above already covers the common repeat-PATCH case; this is
    # the explicit invariant for anything that reaches here.
    if previous_status == OrderStatus.cancelled:
        return jsonify(error="A cancelled order cannot change status"), 409

    order.status = new_status

    refunded = None
    if new_status == OrderStatus.cancelled:
        # Stock is restored by the trg_restore_inventory trigger the moment this
        # UPDATE flips status to 'cancelled' — adding it back here as well would
        # double the restock and silently inflate inventory.
        refunded = refund_order_if_prepaid(order)

    db.session.commit()

    payload = {"message": "Status updated", "status": new_status.value}
    if refunded is not None:
        payload["refunded"] = refunded
    return jsonify(payload), 200


@admin_bp.route("/orders/<int:order_id>/tracking", methods=["POST"])
@admin_required
def add_tracking_event(order_id):
    try:
        data = _tracking_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    order = db.session.get(Order, order_id)
    if not order:
        return jsonify(error="Order not found"), 404

    event = OrderTracking(
        order_id=order_id,
        status_label=data["status_label"],
        description=data.get("description"),
        status_type=TrackingStatusType(data["status_type"]),
    )
    db.session.add(event)

    if data.get("courier_name"):
        order.courier_name = data["courier_name"]
    if data.get("tracking_number"):
        order.tracking_number = data["tracking_number"]
    if data.get("expected_delivery"):
        order.expected_delivery = data["expected_delivery"]

    db.session.commit()

    return jsonify(message="Tracking event added"), 201


# ── Returns ───────────────────────────────────────────────────

@admin_bp.route("/returns", methods=["GET"])
@admin_required
def list_returns():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    status = request.args.get("status")

    q = Return.query
    if status:
        try:
            q = q.filter_by(status=ReturnStatus(status))
        except ValueError:
            pass

    paginated = q.order_by(Return.requested_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    items = []
    for r in paginated.items:
        oi = r.order_item
        user = db.session.get(User, r.user_id)
        items.append({
            "id": r.id,
            "order_item_id": r.order_item_id,
            "product_name": oi.variant.product.name if oi else "Unknown",
            "customer_name": user.full_name if user else "Unknown",
            "reason": r.reason.value,
            "description": r.description,
            "status": r.status.value,
            "resolution_type": r.resolution_type.value if r.resolution_type else None,
            "refund_amount": float(r.refund_amount) if r.refund_amount else None,
            "requested_at": r.requested_at.isoformat(),
            "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
        })

    return jsonify(
        returns=items,
        page=paginated.page,
        pages=paginated.pages,
        total=paginated.total,
    ), 200


@admin_bp.route("/returns/<int:return_id>", methods=["PATCH"])
@admin_required
def update_return(return_id):
    try:
        data = _return_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    ret = db.session.get(Return, return_id)
    if not ret:
        return jsonify(error="Return not found"), 404

    ret.status = ReturnStatus(data["status"])
    if data.get("resolution_type"):
        ret.resolution_type = ResolutionType(data["resolution_type"])
    if data.get("refund_amount") is not None:
        ret.refund_amount = data["refund_amount"]

    from datetime import datetime, timezone
    if ret.status == ReturnStatus.resolved:
        ret.resolved_at = datetime.now(timezone.utc)

    db.session.commit()

    return jsonify(message="Return updated"), 200
