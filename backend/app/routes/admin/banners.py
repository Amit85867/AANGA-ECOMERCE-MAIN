"""Admin hero banner management: CRUD."""
from flask import request, jsonify
from marshmallow import ValidationError

from app.extensions import db
from app.models.cms import HeroBanner
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.schemas.admin import AdminHeroBannerIn

_banner_in = AdminHeroBannerIn()


def _serialize_banner(b):
    return {
        "id": b.id,
        "title": b.title,
        "subtitle": b.subtitle,
        "description": b.description,
        "image_url": b.image_url,
        "mobile_image_url": b.mobile_image_url,
        "link_url": b.link_url,
        "link_text": b.link_text,
        "secondary_link_url": b.secondary_link_url,
        "secondary_link_text": b.secondary_link_text,
        "sort_order": b.sort_order,
        "is_active": b.is_active,
        "starts_at": b.starts_at.isoformat() if b.starts_at else None,
        "ends_at": b.ends_at.isoformat() if b.ends_at else None,
        "created_at": b.created_at.isoformat(),
        "updated_at": b.updated_at.isoformat() if b.updated_at else None,
    }


@admin_bp.route("/banners", methods=["GET"])
@admin_required
def admin_list_banners():
    banners = HeroBanner.query.order_by(HeroBanner.sort_order, HeroBanner.created_at.desc()).all()
    return jsonify(banners=[_serialize_banner(b) for b in banners]), 200


@admin_bp.route("/banners", methods=["POST"])
@admin_required
def create_banner():
    try:
        data = _banner_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    banner = HeroBanner(
        title=data["title"],
        subtitle=data.get("subtitle"),
        description=data.get("description"),
        image_url=data["image_url"],
        mobile_image_url=data.get("mobile_image_url"),
        link_url=data.get("link_url"),
        link_text=data.get("link_text"),
        secondary_link_url=data.get("secondary_link_url"),
        secondary_link_text=data.get("secondary_link_text"),
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", True),
        starts_at=data.get("starts_at"),
        ends_at=data.get("ends_at"),
    )
    db.session.add(banner)
    db.session.commit()
    return jsonify(_serialize_banner(banner)), 201


@admin_bp.route("/banners/<int:banner_id>", methods=["PUT"])
@admin_required
def update_banner(banner_id):
    try:
        data = _banner_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    banner = db.session.get(HeroBanner, banner_id)
    if not banner:
        return jsonify(error="Banner not found"), 404

    banner.title = data["title"]
    banner.subtitle = data.get("subtitle")
    banner.description = data.get("description")
    banner.image_url = data["image_url"]
    banner.mobile_image_url = data.get("mobile_image_url")
    banner.link_url = data.get("link_url")
    banner.link_text = data.get("link_text")
    banner.secondary_link_url = data.get("secondary_link_url")
    banner.secondary_link_text = data.get("secondary_link_text")
    banner.sort_order = data.get("sort_order", 0)
    banner.is_active = data.get("is_active", True)
    banner.starts_at = data.get("starts_at")
    banner.ends_at = data.get("ends_at")

    db.session.commit()
    return jsonify(_serialize_banner(banner)), 200


@admin_bp.route("/banners/<int:banner_id>", methods=["DELETE"])
@admin_required
def delete_banner(banner_id):
    banner = db.session.get(HeroBanner, banner_id)
    if not banner:
        return jsonify(error="Banner not found"), 404

    db.session.delete(banner)
    db.session.commit()
    return jsonify(message="Banner deleted"), 200
