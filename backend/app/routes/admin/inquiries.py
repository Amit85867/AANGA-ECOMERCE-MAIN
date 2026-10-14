"""Admin: wholesale inquiries & contact messages management."""
from flask import request, jsonify
from sqlalchemy import or_
from marshmallow import ValidationError

from app.extensions import db
from app.models.marketing import WholesaleInquiry, ContactMessage
from app.models.enums import InquiryStatus, ContactSubject, MessageStatus
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.utils.pagination import apply_sort, paginate
from app.schemas.admin import AdminInquiryStatusIn, AdminMessageStatusIn

_inquiry_status_in = AdminInquiryStatusIn()
_message_status_in = AdminMessageStatusIn()


# ── Wholesale Inquiries ───────────────────────────────────────

@admin_bp.route("/wholesale-inquiries", methods=["GET"])
@admin_required
def list_inquiries():
    status = request.args.get("status")

    q = WholesaleInquiry.query
    if status:
        try:
            q = q.filter_by(status=InquiryStatus(status))
        except ValueError:
            pass

    search = (request.args.get("q") or "").strip()
    if search:
        like = f"%{search}%"
        q = q.filter(or_(
            WholesaleInquiry.shop_name.ilike(like),
            WholesaleInquiry.owner_name.ilike(like),
            WholesaleInquiry.email.ilike(like),
            WholesaleInquiry.phone.ilike(like),
            WholesaleInquiry.city.ilike(like),
        ))

    paginated = paginate(apply_sort(
        q, {"submitted_at": WholesaleInquiry.submitted_at}, "submitted_at"
    ))

    items = [
        {
            "id": i.id,
            "shop_name": i.shop_name,
            "owner_name": i.owner_name,
            "phone": i.phone,
            "email": i.email,
            "city": i.city,
            "state": i.state,
            "gst_number": i.gst_number,
            "categories_interest": i.categories_interest,
            "monthly_volume_range": i.monthly_volume_range.value,
            "status": i.status.value,
            "notes": i.notes,
            "submitted_at": i.submitted_at.isoformat(),
        }
        for i in paginated.items
    ]

    return jsonify(
        inquiries=items,
        page=paginated.page,
        pages=paginated.pages,
        total=paginated.total,
    ), 200


@admin_bp.route("/wholesale-inquiries/<int:inquiry_id>", methods=["PATCH"])
@admin_required
def update_inquiry(inquiry_id):
    try:
        data = _inquiry_status_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    inquiry = db.session.get(WholesaleInquiry, inquiry_id)
    if not inquiry:
        return jsonify(error="Inquiry not found"), 404

    inquiry.status = InquiryStatus(data["status"])
    if data.get("notes") is not None:
        inquiry.notes = data["notes"]

    db.session.commit()

    return jsonify(message="Inquiry updated"), 200


# ── Contact Messages ─────────────────────────────────────────

@admin_bp.route("/contact-messages", methods=["GET"])
@admin_required
def list_messages():
    status = request.args.get("status")

    q = ContactMessage.query
    if status:
        try:
            q = q.filter_by(status=MessageStatus(status))
        except ValueError:
            pass

    search = (request.args.get("q") or "").strip()
    if search:
        like = f"%{search}%"
        q = q.filter(or_(
            ContactMessage.name.ilike(like),
            ContactMessage.email.ilike(like),
            ContactMessage.message.ilike(like),
        ))

    paginated = paginate(apply_sort(q, {"sent_at": ContactMessage.sent_at}, "sent_at"))

    items = [
        {
            "id": m.id,
            "name": m.name,
            "email": m.email,
            "phone": m.phone,
            "subject": m.subject.value,
            "message": m.message,
            "status": m.status.value,
            "sent_at": m.sent_at.isoformat(),
            "replied_at": m.replied_at.isoformat() if m.replied_at else None,
        }
        for m in paginated.items
    ]

    return jsonify(
        messages=items,
        page=paginated.page,
        pages=paginated.pages,
        total=paginated.total,
    ), 200


@admin_bp.route("/contact-messages/<int:message_id>", methods=["PATCH"])
@admin_required
def update_message(message_id):
    try:
        data = _message_status_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    msg = db.session.get(ContactMessage, message_id)
    if not msg:
        return jsonify(error="Message not found"), 404

    msg.status = MessageStatus(data["status"])
    if data["status"] == "replied":
        from datetime import datetime, timezone
        msg.replied_at = datetime.now(timezone.utc)

    db.session.commit()

    return jsonify(message="Message status updated"), 200
