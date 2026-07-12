"""Product listing, detail, and search."""
from flask import Blueprint, request, jsonify
from sqlalchemy import func

from app.extensions import db
from app.models.catalogue import Product, ProductImage, ProductVariant, Category
from app.models.engagement import ProductReview
from app.schemas.product import ProductListOut, ProductDetailOut

products_bp = Blueprint("products", __name__, url_prefix="/api/products")

_list_out = ProductListOut(many=True)
_detail_out = ProductDetailOut()


def _build_product_list_item(p, primary_image, colors, avg_rating, review_count):
    return {
        "id": p.id,
        "slug": p.slug,
        "name": p.name,
        "category_name": p.category.name if p.category else None,
        "mrp": float(p.mrp),
        "selling_price": float(p.selling_price),
        "discount_percent": p.discount_percent,
        "badge_label": p.badge_label,
        "badge_class": p.badge_class,
        "primary_image": primary_image,
        "colors": colors,
        "avg_rating": round(avg_rating, 1) if avg_rating else None,
        "review_count": review_count,
    }


@products_bp.route("", methods=["GET"])
def list_products():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 12, type=int), 48)
    category_slug = request.args.get("category")
    search = request.args.get("q")
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    sort = request.args.get("sort", "newest")
    badge = request.args.get("badge")
    featured_only = request.args.get("featured", "").lower() == "true"

    q = Product.query.filter(Product.is_active.is_(True))

    if category_slug:
        q = q.join(Category).filter(Category.slug == category_slug)

    if search:
        q = q.filter(Product.name.ilike(f"%{search}%"))

    if min_price is not None:
        q = q.filter(Product.selling_price >= min_price)
    if max_price is not None:
        q = q.filter(Product.selling_price <= max_price)

    if badge:
        q = q.filter(Product.badge_label.ilike(badge))

    if featured_only:
        q = q.filter(Product.is_featured.is_(True))

    sort_map = {
        "newest": Product.created_at.desc(),
        "price_asc": Product.selling_price.asc(),
        "price_desc": Product.selling_price.desc(),
        "popular": Product.id.desc(),
    }
    q = q.order_by(sort_map.get(sort, Product.created_at.desc()))

    paginated = q.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for p in paginated.items:
        primary = (
            ProductImage.query
            .filter_by(product_id=p.id, is_primary=True)
            .first()
        )
        colors = (
            db.session.query(ProductVariant.color_hex)
            .filter_by(product_id=p.id)
            .distinct()
            .all()
        )
        stats = (
            db.session.query(
                func.avg(ProductReview.rating),
                func.count(ProductReview.id),
            )
            .filter_by(product_id=p.id)
            .first()
        )
        items.append(_build_product_list_item(
            p,
            primary.image_url if primary else None,
            [c[0] for c in colors],
            stats[0] or 0,
            stats[1],
        ))

    return jsonify(
        products=_list_out.dump(items),
        page=paginated.page,
        pages=paginated.pages,
        total=paginated.total,
    ), 200


@products_bp.route("/<slug>", methods=["GET"])
def product_detail(slug):
    p = Product.query.filter_by(slug=slug, is_active=True).first()
    if not p:
        return jsonify(error="Product not found"), 404

    stats = (
        db.session.query(
            func.avg(ProductReview.rating),
            func.count(ProductReview.id),
        )
        .filter_by(product_id=p.id)
        .first()
    )

    data = {
        "id": p.id,
        "slug": p.slug,
        "name": p.name,
        "description": p.description,
        "category_name": p.category.name if p.category else None,
        "category_slug": p.category.slug if p.category else None,
        "mrp": float(p.mrp),
        "selling_price": float(p.selling_price),
        "discount_percent": p.discount_percent,
        "badge_label": p.badge_label,
        "badge_class": p.badge_class,
        "is_featured": p.is_featured,
        "variants": [
            {
                "id": v.id,
                "size": v.size,
                "color_name": v.color_name,
                "color_hex": v.color_hex,
                "stock_qty": v.stock_qty,
                "price_override": float(v.price_override) if v.price_override else None,
                "sku": v.sku,
            }
            for v in sorted(p.variants, key=lambda v: v.id)
        ],
        "images": [
            {
                "id": img.id,
                "image_url": img.image_url,
                "sort_order": img.sort_order,
                "is_primary": img.is_primary,
            }
            for img in sorted(p.images, key=lambda i: i.sort_order)
        ],
        "avg_rating": round(stats[0], 1) if stats[0] else None,
        "review_count": stats[1],
        "rating_count": stats[1],
    }

    return jsonify(_detail_out.dump(data)), 200
