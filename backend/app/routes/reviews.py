"""Product reviews: list by product, submit."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from sqlalchemy import func

from app.extensions import db
from app.models.engagement import ProductReview
from app.models.catalogue import Product, ProductVariant
from app.models.order import Order, OrderItem
from app.models.enums import OrderStatus
from app.models.user import User
from app.schemas.product import ReviewIn, ReviewOut

reviews_bp = Blueprint("reviews", __name__, url_prefix="/api/reviews")

_review_in = ReviewIn()
_review_out = ReviewOut(many=True)


@reviews_bp.route("/product/<int:product_id>", methods=["GET"])
def product_reviews(product_id):
    page = request.args.get("page", 1, type=int)
    per_page = min(max(request.args.get("per_page", 10, type=int), 1), 50)

    product = db.session.get(Product, product_id)
    if not product or not product.is_active:
        return jsonify(error="Product not found"), 404

    paginated = (
        ProductReview.query
        .filter_by(product_id=product_id)
        .order_by(ProductReview.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    items = []
    for r in paginated.items:
        user = db.session.get(User, r.user_id)
        items.append({
            "id": r.id,
            "rating": r.rating,
            "title": r.title,
            "body": r.body,
            "is_verified": r.is_verified,
            "user_name": user.full_name if user else "Anonymous",
            "created_at": r.created_at.isoformat(),
        })

    stats = (
        db.session.query(
            func.avg(ProductReview.rating),
            func.count(ProductReview.id),
        )
        .filter_by(product_id=product_id)
        .first()
    )

    return jsonify(
        reviews=items,
        avg_rating=round(stats[0], 1) if stats[0] else None,
        total=paginated.total,
        page=paginated.page,
        pages=paginated.pages,
    ), 200


@reviews_bp.route("", methods=["POST"])
@jwt_required()
def submit_review():
    try:
        data = _review_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    user_id = get_jwt_identity()
    product = db.session.get(Product, data["product_id"])
    if not product:
        return jsonify(error="Product not found"), 404

    existing = ProductReview.query.filter_by(
        user_id=user_id, product_id=data["product_id"]
    ).first()
    if existing:
        return jsonify(error="You have already reviewed this product"), 409

    # "Verified purchase" is resolved from this user's own delivered orders —
    # never from a client-supplied order_item_id, which any logged-in user
    # could point at someone else's order (or an unrelated product) to forge
    # the badge.
    purchased_item = _find_delivered_order_item(user_id, data["product_id"])

    review = ProductReview(
        product_id=data["product_id"],
        user_id=user_id,
        order_item_id=purchased_item.id if purchased_item else None,
        rating=data["rating"],
        title=data.get("title"),
        body=data.get("body"),
        is_verified=purchased_item is not None,
    )
    db.session.add(review)
    db.session.commit()

    return jsonify(
        message="Review submitted",
        id=review.id,
        is_verified=review.is_verified,
    ), 201


def _find_delivered_order_item(user_id, product_id):
    """The user's most recent delivered order item for this product, or None.

    Delivery — not merely placing an order — is what a "verified purchase"
    claims, so pending/cancelled orders do not qualify.
    """
    return (
        db.session.query(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .join(ProductVariant, OrderItem.variant_id == ProductVariant.id)
        .filter(
            Order.user_id == user_id,
            Order.status == OrderStatus.delivered,
            ProductVariant.product_id == product_id,
        )
        .order_by(OrderItem.id.desc())
        .first()
    )
