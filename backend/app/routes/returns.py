"""Customer-facing returns: request one, and list your own.

The Returns policy page tells customers to open My Orders and hit "Return" on a
delivered item within the return window — this is the API behind that. Admins
review the request through /api/admin/returns.

Eligibility is enforced here rather than trusted from the client: the item must
belong to the caller, its order must be delivered, the delivery must be inside
RETURN_WINDOW_DAYS, and the item must not already have an open return.
"""
from datetime import datetime, timezone, timedelta

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.extensions import db
from app.models.order import Order, OrderItem, Return
from app.models.enums import OrderStatus, ReturnReason, ReturnStatus
from app.schemas.order import ReturnRequestIn

returns_bp = Blueprint("returns", __name__, url_prefix="/api/returns")

_return_in = ReturnRequestIn()

# Must match the promise on the Returns policy page.
RETURN_WINDOW_DAYS = 7

# Once a return has been resolved or rejected the item is settled; anything
# earlier still counts as an open request and blocks a duplicate.
_CLOSED_STATUSES = {ReturnStatus.resolved, ReturnStatus.rejected}

# An order carrying an in-flight return still accepts returns for its *other*
# items, so return_requested has to qualify alongside delivered — otherwise the
# first return on a multi-item order would lock out the rest.
_RETURNABLE_ORDER_STATUSES = {OrderStatus.delivered, OrderStatus.return_requested}


def _delivered_at(order):
    """When the order reached the customer, for the return-window check.

    Prefers the real delivery tracking event; falls back to expected_delivery,
    then to placed_at, so a missing event can never make an item permanently
    non-returnable.
    """
    delivery_events = [
        t.event_time for t in order.tracking
        if t.status_type.value == "delivered"
    ]
    if delivery_events:
        return max(delivery_events)
    if order.expected_delivery:
        return datetime.combine(
            order.expected_delivery, datetime.min.time(), tzinfo=timezone.utc
        )
    return order.placed_at


def _serialize(ret):
    item = ret.order_item
    variant = item.variant if item else None
    order = item.order if item else None
    return {
        "id": ret.id,
        "order_item_id": ret.order_item_id,
        "order_id": order.id if order else None,
        "order_number": order.order_number if order else None,
        "product_name": variant.product.name if variant else None,
        "size": variant.size if variant else None,
        "color_name": variant.color_name if variant else None,
        "quantity": item.quantity if item else None,
        "reason": ret.reason.value,
        "description": ret.description,
        "status": ret.status.value,
        "resolution_type": ret.resolution_type.value if ret.resolution_type else None,
        "refund_amount": float(ret.refund_amount) if ret.refund_amount is not None else None,
        "requested_at": ret.requested_at.isoformat(),
        "resolved_at": ret.resolved_at.isoformat() if ret.resolved_at else None,
    }


@returns_bp.route("", methods=["POST"])
@jwt_required()
def request_return():
    try:
        data = _return_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    user_id = get_jwt_identity()

    # Ownership: join through the order so another customer's item is a 404,
    # not a leak that it exists.
    item = (
        db.session.query(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(OrderItem.id == data["order_item_id"], Order.user_id == user_id)
        .first()
    )
    if not item:
        return jsonify(error="Order item not found"), 404

    order = item.order
    if order.status not in _RETURNABLE_ORDER_STATUSES:
        return jsonify(
            error="Only delivered items can be returned."
        ), 422

    deadline = _delivered_at(order) + timedelta(days=RETURN_WINDOW_DAYS)
    if datetime.now(timezone.utc) > deadline:
        return jsonify(
            error=f"The {RETURN_WINDOW_DAYS}-day return window for this item has closed."
        ), 422

    open_return = (
        Return.query
        .filter(Return.order_item_id == item.id)
        .filter(Return.status.notin_(list(_CLOSED_STATUSES)))
        .first()
    )
    if open_return:
        return jsonify(
            error="A return request for this item is already in progress.",
            return_id=open_return.id,
        ), 409

    ret = Return(
        order_item_id=item.id,
        user_id=user_id,
        reason=ReturnReason(data["reason"]),
        description=data.get("description"),
        status=ReturnStatus.requested,
    )
    db.session.add(ret)

    # Surface it on the order timeline so the customer sees it in tracking.
    order.status = OrderStatus.return_requested

    db.session.commit()

    return jsonify(_serialize(ret)), 201


@returns_bp.route("", methods=["GET"])
@jwt_required()
def list_my_returns():
    returns = (
        Return.query
        .filter_by(user_id=get_jwt_identity())
        .order_by(Return.requested_at.desc())
        .all()
    )
    return jsonify(returns=[_serialize(r) for r in returns]), 200


@returns_bp.route("/<int:return_id>", methods=["GET"])
@jwt_required()
def return_detail(return_id):
    ret = Return.query.filter_by(id=return_id, user_id=get_jwt_identity()).first()
    if not ret:
        return jsonify(error="Return not found"), 404
    return jsonify(_serialize(ret)), 200


@returns_bp.route("/eligibility/<int:order_id>", methods=["GET"])
@jwt_required()
def order_return_eligibility(order_id):
    """Which items of an order can still be returned — drives the "Return"
    button in My Orders so the UI never offers an action that would 422."""
    order = Order.query.filter_by(id=order_id, user_id=get_jwt_identity()).first()
    if not order:
        return jsonify(error="Order not found"), 404

    window_open = (
        order.status in _RETURNABLE_ORDER_STATUSES
        and datetime.now(timezone.utc) <= _delivered_at(order) + timedelta(days=RETURN_WINDOW_DAYS)
    )

    open_ids = {
        r.order_item_id for r in
        Return.query
        .filter(Return.order_item_id.in_([i.id for i in order.items] or [0]))
        .filter(Return.status.notin_(list(_CLOSED_STATUSES)))
        .all()
    }

    items = []
    for oi in order.items:
        already = oi.id in open_ids
        items.append({
            "order_item_id": oi.id,
            "product_name": oi.variant.product.name,
            "size": oi.variant.size,
            "color_name": oi.variant.color_name,
            "quantity": oi.quantity,
            "returnable": bool(window_open and not already),
            "reason_unavailable": (
                "A return is already in progress for this item." if already
                else None if window_open
                else "This item is outside the return window."
            ),
        })

    return jsonify(
        order_id=order.id,
        order_number=order.order_number,
        window_days=RETURN_WINDOW_DAYS,
        window_open=window_open,
        items=items,
    ), 200
