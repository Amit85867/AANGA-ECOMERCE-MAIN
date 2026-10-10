"""Admin promo banner management: CRUD."""
from flask import request, jsonify
from marshmallow import ValidationError

from app.extensions import db
from app.models.cms import PromoBanner
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.utils.pagination import page_meta, paginate
from app.schemas.admin import AdminPromoBannerIn

_promo_in = AdminPromoBannerIn()


def _serialize_promo(p):
    return {
        "id": p.id,
        "title": p.title,
        "subtitle": p.subtitle,
        "description": p.description,
        "badge_text": p.badge_text,
        "image_url": p.image_url,
        "link_url": p.link_url,
        "link_text": p.link_text,
        "items": p.items,
        "sort_order": p.sort_order,
        "is_active": p.is_active,
        "starts_at": p.starts_at.isoformat() if p.starts_at else None,
        "ends_at": p.ends_at.isoformat() if p.ends_at else None,
        "created_at": p.created_at.isoformat(),
    }


@admin_bp.route("/promo-banners", methods=["GET"])
@admin_required
def admin_list_promos():
    q = PromoBanner.query
    search = (request.args.get("q") or "").strip()
    if search:
        q = q.filter(PromoBanner.title.ilike(f"%{search}%"))

    # Capped rather than unbounded: these lists are short today, and this
    # is what keeps them cheap when they are not.
    page = paginate(q.order_by(PromoBanner.sort_order, PromoBanner.created_at.desc()), default=50)
    return jsonify(
        promo_banners=[_serialize_promo(row) for row in page.items], **page_meta(page)
    ), 200


@admin_bp.route("/promo-banners", methods=["POST"])
@admin_required
def create_promo():
    try:
        data = _promo_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    promo = PromoBanner(
        title=data["title"],
        subtitle=data.get("subtitle"),
        description=data.get("description"),
        badge_text=data.get("badge_text"),
        image_url=data.get("image_url"),
        link_url=data.get("link_url"),
        link_text=data.get("link_text"),
        items=data.get("items"),
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", True),
        starts_at=data.get("starts_at"),
        ends_at=data.get("ends_at"),
    )
    db.session.add(promo)
    db.session.commit()
    return jsonify(_serialize_promo(promo)), 201


@admin_bp.route("/promo-banners/<int:promo_id>", methods=["PUT"])
@admin_required
def update_promo(promo_id):
    try:
        data = _promo_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    promo = db.session.get(PromoBanner, promo_id)
    if not promo:
        return jsonify(error="Promo banner not found"), 404

    promo.title = data["title"]
    promo.subtitle = data.get("subtitle")
    promo.description = data.get("description")
    promo.badge_text = data.get("badge_text")
    promo.image_url = data.get("image_url")
    promo.link_url = data.get("link_url")
    promo.link_text = data.get("link_text")
    promo.items = data.get("items")
    promo.sort_order = data.get("sort_order", 0)
    promo.is_active = data.get("is_active", True)
    promo.starts_at = data.get("starts_at")
    promo.ends_at = data.get("ends_at")

    db.session.commit()
    return jsonify(_serialize_promo(promo)), 200


@admin_bp.route("/promo-banners/<int:promo_id>", methods=["DELETE"])
@admin_required
def delete_promo(promo_id):
    promo = db.session.get(PromoBanner, promo_id)
    if not promo:
        return jsonify(error="Promo banner not found"), 404

    db.session.delete(promo)
    db.session.commit()
    return jsonify(message="Promo banner deleted"), 200
