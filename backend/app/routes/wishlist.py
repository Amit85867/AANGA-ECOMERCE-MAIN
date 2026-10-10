"""Wishlist: list, add, remove."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import func

from sqlalchemy.orm import joinedload

from app.extensions import db
from app.services.catalogue import card_extras
from app.models.engagement import Wishlist, ProductReview
from app.models.catalogue import Product, ProductImage, ProductVariant

wishlist_bp = Blueprint("wishlist", __name__, url_prefix="/api/wishlist")

# A wishlist is a shortlist, not an archive; this also bounds the response.
MAX_WISHLIST_ITEMS = 200


def _serialize_item(w, product, extras):
    return {
        "wishlist_id": w.id,
        "product_id": product.id,
        "slug": product.slug,
        "name": product.name,
        "category_name": product.category.name if product.category else None,
        "mrp": float(product.mrp),
        "selling_price": float(product.selling_price),
        "discount_percent": product.discount_percent,
        "badge_label": product.badge_label,
        **extras,
        "added_at": w.added_at.isoformat(),
    }


@wishlist_bp.route("", methods=["GET"])
@jwt_required()
def get_wishlist():
    # One query for the saved products, three for their card details —
    # previously four queries per saved item.
    rows = (
        db.session.query(Wishlist, Product)
        .join(Product, Wishlist.product_id == Product.id)
        .options(joinedload(Product.category))
        .filter(Wishlist.user_id == get_jwt_identity(), Product.is_active.is_(True))
        .order_by(Wishlist.added_at.desc())
        .limit(MAX_WISHLIST_ITEMS)
        .all()
    )
    extras = card_extras([product for _, product in rows])
    result = [_serialize_item(w, product, extras[product.id]) for w, product in rows]

    return jsonify(items=result, count=len(result)), 200


@wishlist_bp.route("", methods=["POST"])
@jwt_required()
def add_to_wishlist():
    data = request.get_json(silent=True)
    product_id = data.get("product_id") if isinstance(data, dict) else None
    if not isinstance(product_id, int) or isinstance(product_id, bool):
        return jsonify(error="product_id is required"), 422

    product = db.session.get(Product, product_id)
    if not product or not product.is_active:
        return jsonify(error="Product not found"), 404

    existing = Wishlist.query.filter_by(
        user_id=get_jwt_identity(), product_id=product_id
    ).first()
    if existing:
        return jsonify(message="Already in wishlist"), 200

    w = Wishlist(
        user_id=get_jwt_identity(),
        product_id=product_id,
        variant_id=data.get("variant_id"),
    )
    db.session.add(w)
    db.session.commit()
    return jsonify(message="Added to wishlist"), 201


@wishlist_bp.route("/<int:product_id>", methods=["DELETE"])
@jwt_required()
def remove_from_wishlist(product_id):
    w = Wishlist.query.filter_by(
        user_id=get_jwt_identity(), product_id=product_id
    ).first()
    if not w:
        return jsonify(error="Item not in wishlist"), 404

    db.session.delete(w)
    db.session.commit()
    return jsonify(message="Removed from wishlist"), 200
