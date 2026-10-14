"""Admin offer management: CRUD."""
from flask import request, jsonify
from marshmallow import ValidationError

from app.extensions import db
from app.models.marketing import Offer
from app.models.enums import OfferType
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.utils.pagination import page_meta, paginate
from app.schemas.admin import AdminOfferIn

_offer_in = AdminOfferIn()


def _serialize_offer(o):
    return {
        "id": o.id,
        "title": o.title,
        "description": o.description,
        "category_id": o.category_id,
        "offer_type": o.offer_type.value,
        "discount_percent": float(o.discount_percent) if o.discount_percent else None,
        "image_url": o.image_url,
        "is_active": o.is_active,
        "starts_at": o.starts_at.isoformat() if o.starts_at else None,
        "ends_at": o.ends_at.isoformat() if o.ends_at else None,
        "created_at": o.created_at.isoformat(),
    }


@admin_bp.route("/offers", methods=["GET"])
@admin_required
def admin_list_offers():
    q = Offer.query
    search = (request.args.get("q") or "").strip()
    if search:
        q = q.filter(Offer.title.ilike(f"%{search}%"))

    # Capped rather than unbounded: these lists are short today, and this
    # is what keeps them cheap when they are not.
    page = paginate(q.order_by(Offer.created_at.desc()), default=50)
    return jsonify(
        offers=[_serialize_offer(row) for row in page.items], **page_meta(page)
    ), 200


@admin_bp.route("/offers", methods=["POST"])
@admin_required
def create_offer():
    try:
        data = _offer_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    offer = Offer(
        title=data["title"],
        description=data.get("description"),
        category_id=data.get("category_id"),
        offer_type=OfferType(data["offer_type"]),
        discount_percent=data.get("discount_percent"),
        image_url=data.get("image_url"),
        is_active=data.get("is_active", True),
        starts_at=data.get("starts_at"),
        ends_at=data.get("ends_at"),
    )
    db.session.add(offer)
    db.session.commit()

    return jsonify(_serialize_offer(offer)), 201


@admin_bp.route("/offers/<int:offer_id>", methods=["PUT"])
@admin_required
def update_offer(offer_id):
    try:
        data = _offer_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    offer = db.session.get(Offer, offer_id)
    if not offer:
        return jsonify(error="Offer not found"), 404

    offer.title = data["title"]
    offer.description = data.get("description")
    offer.category_id = data.get("category_id")
    offer.offer_type = OfferType(data["offer_type"])
    offer.discount_percent = data.get("discount_percent")
    offer.image_url = data.get("image_url")
    offer.is_active = data.get("is_active", True)
    offer.starts_at = data.get("starts_at")
    offer.ends_at = data.get("ends_at")

    db.session.commit()

    return jsonify(_serialize_offer(offer)), 200


@admin_bp.route("/offers/<int:offer_id>", methods=["DELETE"])
@admin_required
def delete_offer(offer_id):
    offer = db.session.get(Offer, offer_id)
    if not offer:
        return jsonify(error="Offer not found"), 404

    db.session.delete(offer)
    db.session.commit()

    return jsonify(message="Offer deleted"), 200
