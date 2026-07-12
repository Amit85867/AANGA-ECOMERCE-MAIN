"""Admin Shiprocket actions: create shipment + sync tracking."""
from datetime import datetime, timezone

from flask import jsonify

from app.extensions import db
from app.models.order import Order, OrderTracking
from app.models.enums import OrderStatus, TrackingStatusType
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.services import shiprocket
from app.services.shiprocket import ShiprocketError


@admin_bp.route("/orders/<int:order_id>/ship", methods=["POST"])
@admin_required
def ship_order(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify(error="Order not found"), 404

    if order.tracking_number:
        return jsonify(error="This order already has an AWB assigned"), 409

    try:
        created = shiprocket.create_order(order)
        shipment_id = created.get("shipment_id")
        if not shipment_id:
            return jsonify(error="Shiprocket did not return a shipment id"), 502

        awb = shiprocket.assign_awb(shipment_id)
    except ShiprocketError as err:
        return jsonify(error=str(err)), 502

    order.courier_name = awb.get("courier_name")
    order.tracking_number = awb.get("awb_code")
    order.status = OrderStatus.shipped

    db.session.add(OrderTracking(
        order_id=order.id,
        status_label="Shipped",
        description=f"Dispatched via {order.courier_name or 'courier'} (AWB {order.tracking_number}).",
        status_type=TrackingStatusType.dispatched,
    ))
    db.session.commit()

    return jsonify(
        message="Shipment created",
        courier_name=order.courier_name,
        tracking_number=order.tracking_number,
        status=order.status.value,
    ), 201


@admin_bp.route("/orders/<int:order_id>/sync-tracking", methods=["POST"])
@admin_required
def sync_tracking(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify(error="Order not found"), 404
    if not order.tracking_number:
        return jsonify(error="No AWB assigned to this order yet"), 422

    try:
        activities = shiprocket.track_by_awb(order.tracking_number)
    except ShiprocketError as err:
        return jsonify(error=str(err)), 502

    existing = {(t.status_label, t.description) for t in order.tracking}
    added = 0
    for act in activities:
        label = act.get("activity") or act.get("status") or "Update"
        desc = act.get("location") or act.get("date")
        if (label, desc) in existing:
            continue
        db.session.add(OrderTracking(
            order_id=order.id,
            status_label=label,
            description=desc,
            status_type=TrackingStatusType.in_transit,
        ))
        existing.add((label, desc))
        added += 1

    db.session.commit()
    return jsonify(message=f"Synced {added} new tracking update(s)", added=added), 200
