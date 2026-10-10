"""Admin order management: list, detail, update status, add tracking, manage returns."""
from datetime import datetime, timezone

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
from app.services import audit
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
    audit.annotate(
        by_admin=True,
        summary=f"Order {order.order_number}: {previous_status.value} → {new_status.value}",
        changes={"from": previous_status.value, "to": new_status.value},
    )

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


# A return that has been resolved or rejected is closed: money may already
# have moved, so it cannot be reopened or resolved a second time.
_CLOSED_RETURN_STATUSES = {ReturnStatus.resolved, ReturnStatus.rejected}


@admin_bp.route("/returns/<int:return_id>", methods=["PATCH"])
@admin_required
def update_return(return_id):
    """Move a return along, and settle it.

    Resolving as a refund is where money moves: a prepaid order is refunded
    through Razorpay for the approved amount, and only if that succeeds is the
    return marked resolved. A COD order has nothing to reverse online, so the
    response says the refund must be paid out manually.
    """
    try:
        data = _return_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    ret = db.session.get(Return, return_id)
    if not ret:
        return jsonify(error="Return not found"), 404

    if ret.status in _CLOSED_RETURN_STATUSES:
        return jsonify(error=f"This return is already {ret.status.value} and cannot be changed."), 409

    item = ret.order_item
    order = item.order
    paid_for_item = float(item.total_price or float(item.unit_price) * item.quantity)

    # A refund can be for less than the item cost (partial), never more.
    refund_amount = data.get("refund_amount")
    if refund_amount is not None and refund_amount > paid_for_item:
        return jsonify(errors={"refund_amount": [
            f"Cannot exceed the {paid_for_item:.2f} paid for this item."
        ]}), 422

    new_status = ReturnStatus(data["status"])
    previous_status = ret.status
    resolution = (
        ResolutionType(data["resolution_type"]) if data.get("resolution_type")
        else ret.resolution_type
    )

    refund_method = None
    if new_status == ReturnStatus.resolved:
        if resolution is None:
            return jsonify(errors={"resolution_type": [
                "Choose how this return is being resolved."
            ]}), 422

        if resolution == ResolutionType.refund:
            if refund_amount is None:
                refund_amount = float(ret.refund_amount) if ret.refund_amount else paid_for_item

            if order.payment_status == PaymentStatus.paid and order.payment_ref:
                from app.routes.payments import refund_payment
                ok = refund_payment(
                    order.payment_ref, int(round(refund_amount * 100)),
                    reason=f"return_{ret.id}",
                )
                if not ok:
                    current_app.logger.critical(
                        "REFUND_FAILED_ON_RETURN return=%s order=%s amount=%s",
                        ret.id, order.order_number, refund_amount,
                    )
                    return jsonify(
                        error="The payment gateway did not accept the refund. "
                              "The return has not been resolved — try again, or "
                              "refund it in the Razorpay Dashboard."
                    ), 502
                refund_method = "gateway"
            else:
                # COD (or never captured): nothing to reverse online.
                refund_method = "manual"

        if data.get("restock"):
            item.variant.stock_qty += item.quantity

        ret.resolved_at = datetime.now(timezone.utc)

    ret.status = new_status
    ret.resolution_type = resolution
    if refund_amount is not None:
        ret.refund_amount = refund_amount

    if new_status == ReturnStatus.rejected:
        ret.resolved_at = datetime.now(timezone.utc)

    db.session.flush()
    _sync_order_after_return(order)

    restocked = bool(new_status == ReturnStatus.resolved and data.get("restock"))
    audit.annotate(
        entity="refunds" if refund_method else "returns",
        summary=(
            f"Return #{ret.id} on order {order.order_number}: "
            f"{previous_status.value} → {new_status.value}"
            + (f", refunded ₹{refund_amount:.2f} ({refund_method})" if refund_method else "")
            + (", item restocked" if restocked else "")
        ),
        changes={
            "order_number": order.order_number,
            "from": previous_status.value, "to": new_status.value,
            "resolution_type": resolution.value if resolution else None,
            "refund_amount": refund_amount, "refund_method": refund_method,
            "restocked": restocked,
        },
    )

    db.session.commit()

    return jsonify(
        message="Return updated",
        status=ret.status.value,
        refund_method=refund_method,
        refund_amount=float(ret.refund_amount) if ret.refund_amount else None,
    ), 200


def _sync_order_after_return(order):
    """Reflect the state of an order's returns on the order itself.

    Every item returned and refunded -> the order is "returned". Otherwise, once
    no return is still in progress, it goes back to "delivered".
    """
    returns = Return.query.join(OrderItem, Return.order_item_id == OrderItem.id).filter(
        OrderItem.order_id == order.id
    ).all()
    open_returns = [r for r in returns if r.status not in _CLOSED_RETURN_STATUSES]
    resolved_items = {
        r.order_item_id for r in returns
        if r.status == ReturnStatus.resolved and r.resolution_type == ResolutionType.refund
    }

    if open_returns:
        return
    if resolved_items and resolved_items == {i.id for i in order.items}:
        order.status = OrderStatus.returned
    elif order.status == OrderStatus.return_requested:
        order.status = OrderStatus.delivered
