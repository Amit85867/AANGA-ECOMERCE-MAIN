"""Admin announcement management: CRUD."""
from flask import request, jsonify
from marshmallow import ValidationError

from app.extensions import db
from app.models.cms import Announcement
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.schemas.admin import AdminAnnouncementIn

_ann_in = AdminAnnouncementIn()


def _serialize_announcement(a):
    return {
        "id": a.id,
        "text": a.text,
        "highlight_text": a.highlight_text,
        "link_url": a.link_url,
        "link_text": a.link_text,
        "bg_color": a.bg_color,
        "text_color": a.text_color,
        "highlight_color": a.highlight_color,
        "sort_order": a.sort_order,
        "is_active": a.is_active,
        "starts_at": a.starts_at.isoformat() if a.starts_at else None,
        "ends_at": a.ends_at.isoformat() if a.ends_at else None,
        "created_at": a.created_at.isoformat(),
    }


@admin_bp.route("/announcements", methods=["GET"])
@admin_required
def admin_list_announcements():
    items = Announcement.query.order_by(Announcement.sort_order, Announcement.created_at.desc()).all()
    return jsonify(announcements=[_serialize_announcement(a) for a in items]), 200


@admin_bp.route("/announcements", methods=["POST"])
@admin_required
def create_announcement():
    try:
        data = _ann_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    ann = Announcement(
        text=data["text"],
        highlight_text=data.get("highlight_text"),
        link_url=data.get("link_url"),
        link_text=data.get("link_text"),
        bg_color=data.get("bg_color", "#0A0A0A"),
        text_color=data.get("text_color", "#ffffff"),
        highlight_color=data.get("highlight_color", "#D4AF37"),
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", True),
        starts_at=data.get("starts_at"),
        ends_at=data.get("ends_at"),
    )
    db.session.add(ann)
    db.session.commit()
    return jsonify(_serialize_announcement(ann)), 201


@admin_bp.route("/announcements/<int:ann_id>", methods=["PUT"])
@admin_required
def update_announcement(ann_id):
    try:
        data = _ann_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    ann = db.session.get(Announcement, ann_id)
    if not ann:
        return jsonify(error="Announcement not found"), 404

    ann.text = data["text"]
    ann.highlight_text = data.get("highlight_text")
    ann.link_url = data.get("link_url")
    ann.link_text = data.get("link_text")
    ann.bg_color = data.get("bg_color", "#0A0A0A")
    ann.text_color = data.get("text_color", "#ffffff")
    ann.highlight_color = data.get("highlight_color", "#D4AF37")
    ann.sort_order = data.get("sort_order", 0)
    ann.is_active = data.get("is_active", True)
    ann.starts_at = data.get("starts_at")
    ann.ends_at = data.get("ends_at")

    db.session.commit()
    return jsonify(_serialize_announcement(ann)), 200


@admin_bp.route("/announcements/<int:ann_id>", methods=["DELETE"])
@admin_required
def delete_announcement(ann_id):
    ann = db.session.get(Announcement, ann_id)
    if not ann:
        return jsonify(error="Announcement not found"), 404

    db.session.delete(ann)
    db.session.commit()
    return jsonify(message="Announcement deleted"), 200
