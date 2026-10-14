"""Admin review moderation: browse what customers wrote, remove what breaks the rules."""
from flask import jsonify, request
from sqlalchemy import or_

from app.extensions import db
from app.models.catalogue import Product
from app.models.engagement import ProductReview
from app.models.user import User
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.services import audit
from app.utils.pagination import apply_sort, page_meta, paginate

_SORTABLE = {
    "created_at": ProductReview.created_at,
    "rating": ProductReview.rating,
}


@admin_bp.route("/reviews", methods=["GET"])
@admin_required
def admin_list_reviews():
    q = (
        db.session.query(ProductReview, Product.name, Product.slug, User.full_name, User.email)
        .join(Product, ProductReview.product_id == Product.id)
        .outerjoin(User, ProductReview.user_id == User.id)
    )

    rating = request.args.get("rating", type=int)
    if rating:
        q = q.filter(ProductReview.rating == rating)

    verified = request.args.get("verified", "").lower()
    if verified in ("true", "false"):
        q = q.filter(ProductReview.is_verified.is_(verified == "true"))

    product_id = request.args.get("product_id", type=int)
    if product_id:
        q = q.filter(ProductReview.product_id == product_id)

    search = (request.args.get("q") or "").strip()
    if search:
        like = f"%{search}%"
        q = q.filter(or_(
            ProductReview.title.ilike(like),
            ProductReview.body.ilike(like),
            Product.name.ilike(like),
            User.full_name.ilike(like),
            User.email.ilike(like),
        ))

    page = paginate(apply_sort(q, _SORTABLE, "created_at"))

    return jsonify(
        reviews=[
            {
                "id": review.id,
                "product_id": review.product_id,
                "product_name": product_name,
                "product_slug": product_slug,
                "customer_name": customer_name or "Deleted user",
                "customer_email": customer_email,
                "rating": review.rating,
                "title": review.title,
                "body": review.body,
                "is_verified": review.is_verified,
                "created_at": review.created_at.isoformat(),
            }
            for review, product_name, product_slug, customer_name, customer_email in page.items
        ],
        **page_meta(page),
    ), 200


@admin_bp.route("/reviews/<int:review_id>", methods=["DELETE"])
@admin_required
def admin_delete_review(review_id):
    review = db.session.get(ProductReview, review_id)
    if not review:
        return jsonify(error="Review not found"), 404

    # Keep what was removed: once the row is gone the audit entry is the only
    # record of what the customer wrote and why it was taken down.
    audit.annotate(
        summary=f"Removed a {review.rating}-star review of product #{review.product_id}",
        changes={
            "product_id": review.product_id,
            "user_id": str(review.user_id),
            "rating": review.rating,
            "title": review.title,
            "body": review.body,
        },
    )

    db.session.delete(review)
    db.session.commit()
    return jsonify(message="Review removed"), 200
