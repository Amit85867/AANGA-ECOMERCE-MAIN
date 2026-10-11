"""Product listing, detail, and search."""
from flask import Blueprint, request, jsonify
from sqlalchemy import and_, func

from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.services.catalogue import card_extras
from app.services import campaigns
from app.services.cache import cached_view
from app.models.catalogue import Product, ProductImage, ProductVariant, Category
from app.models.engagement import ProductReview
from app.schemas.product import ProductListOut, ProductDetailOut

products_bp = Blueprint("products", __name__, url_prefix="/api/products")

_list_out = ProductListOut(many=True)
_detail_out = ProductDetailOut()


def _csv(value):
    """"M,L" -> ["M", "L"]; bounded so a query string cannot build a huge IN list."""
    return [part.strip() for part in (value or "").split(",") if part.strip()][:20]


# Clothing sizes sort by convention, not alphabet: S before M before L.
_SIZE_ORDER = {s: i for i, s in enumerate(
    ["XXS", "XS", "S", "M", "L", "XL", "XXL", "2XL", "3XL", "4XL", "ONE SIZE", "FREE SIZE"]
)}


def _size_key(size):
    upper = size.upper()
    if upper in _SIZE_ORDER:
        return (0, _SIZE_ORDER[upper], "")
    if upper.replace(".", "", 1).isdigit():
        return (1, float(upper), "")      # waist / shoe sizes, numerically
    return (2, 0, upper)


@products_bp.route("/facets", methods=["GET"])
@cached_view(120)
def product_facets():
    """The sizes, colours and price range that exist among active products
    (optionally within one category), so the shop only offers filters that can
    return something."""
    variants = (
        db.session.query(ProductVariant.size, ProductVariant.color_name, ProductVariant.color_hex)
        .join(Product, ProductVariant.product_id == Product.id)
        .filter(Product.is_active.is_(True), ProductVariant.stock_qty > 0)
    )
    prices = db.session.query(
        func.min(Product.selling_price), func.max(Product.selling_price)
    ).filter(Product.is_active.is_(True))

    category_slug = request.args.get("category")
    if category_slug:
        variants = variants.join(Category, Product.category_id == Category.id).filter(
            Category.slug == category_slug)
        prices = prices.join(Category, Product.category_id == Category.id).filter(
            Category.slug == category_slug)

    sizes, colours = set(), {}
    for size, colour_name, colour_hex in variants.distinct().all():
        sizes.add(size)
        colours.setdefault(colour_name, colour_hex)

    low, high = prices.one()
    # During a campaign sale the range has to be of the prices on show, or
    # the slider's ends would not match any card.
    live = campaigns.live()
    if live and live.get("sale_percent") and live["sale_product_ids"]:
        price = campaigns.effective_price_sql(live)
        ranged = db.session.query(func.min(price), func.max(price)).select_from(Product).filter(Product.is_active.is_(True))
        if category_slug:
            ranged = ranged.join(Category, Product.category_id == Category.id).filter(Category.slug == category_slug)
        low, high = ranged.one()
    return jsonify(
        sizes=sorted(sizes, key=_size_key),
        colors=[{"name": name, "hex": colours[name]} for name in sorted(colours)],
        price={"min": float(low or 0), "max": float(high or 0)},
    ), 200


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
@cached_view(60)
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

    # A hand-picked collection, in the order the owner arranged it.
    collection_slug = request.args.get("collection")
    if collection_slug:
        from app.models.owner import Collection, CollectionProduct
        q = (
            q.join(CollectionProduct, CollectionProduct.product_id == Product.id)
            .join(Collection, Collection.id == CollectionProduct.collection_id)
            .filter(Collection.slug == collection_slug, Collection.is_active.is_(True))
        )

    if search:
        q = q.filter(Product.name.ilike(f"%{search}%"))

    # The price a customer sees: the campaign sale price where one applies.
    live = campaigns.live()
    price = campaigns.effective_price_sql(live)
    if min_price is not None:
        q = q.filter(price >= min_price)
    if max_price is not None:
        q = q.filter(price <= max_price)

    if badge:
        q = q.filter(Product.badge_label.ilike(badge))

    if featured_only:
        q = q.filter(Product.is_featured.is_(True))

    # Size and colour live on variants. A product matches when ONE variant has
    # both the size and the colour asked for and is in stock — "M" and "Blue"
    # should not match a product that only has M in red and L in blue, nor one
    # whose blue M sold out.
    sizes = _csv(request.args.get("size"))
    colours = _csv(request.args.get("color"))
    if sizes or colours or request.args.get("in_stock", "").lower() == "true":
        wanted = [ProductVariant.stock_qty > 0]
        if sizes:
            wanted.append(func.lower(ProductVariant.size).in_([s.lower() for s in sizes]))
        if colours:
            wanted.append(func.lower(ProductVariant.color_name).in_([c.lower() for c in colours]))
        q = q.filter(Product.variants.any(and_(*wanted)))

    sort_map = {
        "newest": Product.created_at.desc(),
        "price_asc": price.asc(),
        "price_desc": price.desc(),
        "popular": Product.id.desc(),
    }
    if collection_slug and "sort" not in request.args:
        q = q.order_by(CollectionProduct.sort_order, Product.id)
    else:
        q = q.order_by(sort_map.get(sort, Product.created_at.desc()))

    paginated = q.options(joinedload(Product.category)).paginate(
        page=max(page, 1), per_page=max(per_page, 1), error_out=False
    )

    # Images, colours and ratings for the whole page in three queries, rather
    # than three per product.
    extras = card_extras(paginated.items)
    items = [
        campaigns.apply_to_product(_build_product_list_item(
            p,
            extras[p.id]["primary_image"],
            extras[p.id]["colors"],
            extras[p.id]["avg_rating"] or 0,
            extras[p.id]["review_count"],
        ), p.id, live)
        for p in paginated.items
    ]

    return jsonify(
        products=_list_out.dump(items),
        page=paginated.page,
        pages=paginated.pages,
        total=paginated.total,
    ), 200


@products_bp.route("/<slug>", methods=["GET"])
@cached_view(30)
def product_detail(slug):
    p = (
        Product.query
        .options(
            joinedload(Product.category),
            selectinload(Product.variants),
            selectinload(Product.images),
        )
        .filter_by(slug=slug, is_active=True)
        .first()
    )
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
        "care_details": p.care_details,
        "meta_title": p.meta_title,
        "meta_description": p.meta_description,
        "share_image_url": p.share_image_url,
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

    campaigns.apply_to_product(data, p.id, campaigns.live())
    return jsonify(_detail_out.dump(data)), 200
