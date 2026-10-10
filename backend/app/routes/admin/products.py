"""Admin product management: CRUD products, variants, images."""
from flask import request, jsonify
from marshmallow import ValidationError
from sqlalchemy import and_, or_
from sqlalchemy.orm import joinedload, selectinload

from app.extensions import db
from app.models.catalogue import Product, ProductVariant, ProductImage, Category
from app.models.order import OrderItem
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.utils.pagination import apply_sort, page_meta, paginate
from app.schemas.admin import AdminProductIn, AdminVariantIn, AdminImageIn

_product_in = AdminProductIn()
_variant_in = AdminVariantIn()
_image_in = AdminImageIn()


def _serialize_product(p):
    return {
        "id": p.id,
        "category_id": p.category_id,
        "category_name": p.category.name if p.category else None,
        "name": p.name,
        "slug": p.slug,
        "description": p.description,
        "mrp": float(p.mrp),
        "selling_price": float(p.selling_price),
        "discount_percent": p.discount_percent,
        "badge_label": p.badge_label,
        "badge_class": p.badge_class,
        "is_active": p.is_active,
        "is_featured": p.is_featured,
        "created_at": p.created_at.isoformat(),
        "total_stock": sum(v.stock_qty for v in p.variants),
        "variant_count": len(p.variants),
        "image_count": len(p.images),
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
    }


_PRODUCT_SORTS = {
    "created_at": Product.created_at,
    "name": Product.name,
    "selling_price": Product.selling_price,
}


@admin_bp.route("/products", methods=["GET"])
@admin_required
def list_products():
    # selectinload, not joinedload: joining two collections multiplies rows
    # (variants x images) before the page limit is applied.
    q = Product.query.options(
        joinedload(Product.category),
        selectinload(Product.variants),
        selectinload(Product.images),
    )

    search = (request.args.get("q") or "").strip()
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Product.name.ilike(like), Product.slug.ilike(like)))

    category_id = request.args.get("category_id", type=int)
    if category_id:
        q = q.filter(Product.category_id == category_id)

    active = request.args.get("active", "").lower()
    if active in ("true", "false"):
        q = q.filter(Product.is_active.is_(active == "true"))

    if request.args.get("featured", "").lower() == "true":
        q = q.filter(Product.is_featured.is_(True))

    # "out" = at least one variant with nothing left; "low" = at or under 5.
    stock = request.args.get("stock", "").lower()
    if stock in ("out", "low"):
        level = ProductVariant.stock_qty <= 0 if stock == "out" else and_(
            ProductVariant.stock_qty > 0, ProductVariant.stock_qty <= 5
        )
        q = q.filter(Product.variants.any(level))

    page = paginate(apply_sort(q, _PRODUCT_SORTS, "created_at"))

    return jsonify(
        products=[_serialize_product(p) for p in page.items],
        **page_meta(page),
    ), 200


@admin_bp.route("/products/<int:product_id>", methods=["GET"])
@admin_required
def get_product(product_id):
    p = db.session.get(Product, product_id)
    if not p:
        return jsonify(error="Product not found"), 404
    return jsonify(_serialize_product(p)), 200


@admin_bp.route("/products", methods=["POST"])
@admin_required
def create_product():
    try:
        data = _product_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    if not db.session.get(Category, data["category_id"]):
        return jsonify(error="Category not found"), 404

    if Product.query.filter_by(slug=data["slug"]).first():
        return jsonify(error="Slug already exists"), 409

    p = Product(**data)
    db.session.add(p)
    db.session.commit()

    return jsonify(_serialize_product(p)), 201


@admin_bp.route("/products/<int:product_id>", methods=["PUT"])
@admin_required
def update_product(product_id):
    try:
        data = _product_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    p = db.session.get(Product, product_id)
    if not p:
        return jsonify(error="Product not found"), 404

    dup = Product.query.filter(Product.slug == data["slug"], Product.id != product_id).first()
    if dup:
        return jsonify(error="Slug already exists"), 409

    for key, val in data.items():
        setattr(p, key, val)
    db.session.commit()

    return jsonify(_serialize_product(p)), 200


@admin_bp.route("/products/<int:product_id>", methods=["DELETE"])
@admin_required
def delete_product(product_id):
    p = db.session.get(Product, product_id)
    if not p:
        return jsonify(error="Product not found"), 404

    p.is_active = False
    db.session.commit()

    return jsonify(message="Product deactivated"), 200


# ── Variants ──────────────────────────────────────────────────

@admin_bp.route("/products/<int:product_id>/variants", methods=["POST"])
@admin_required
def add_variant(product_id):
    try:
        data = _variant_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    p = db.session.get(Product, product_id)
    if not p:
        return jsonify(error="Product not found"), 404

    existing = ProductVariant.query.filter_by(
        product_id=product_id, size=data["size"], color_name=data["color_name"]
    ).first()
    if existing:
        return jsonify(error="Variant with this size and color already exists"), 409

    v = ProductVariant(product_id=product_id, **data)
    db.session.add(v)
    db.session.commit()

    return jsonify(_serialize_product(p)), 201


@admin_bp.route("/products/<int:product_id>/variants/<int:variant_id>", methods=["PUT"])
@admin_required
def update_variant(product_id, variant_id):
    try:
        data = _variant_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    v = ProductVariant.query.filter_by(id=variant_id, product_id=product_id).first()
    if not v:
        return jsonify(error="Variant not found"), 404

    for key, val in data.items():
        setattr(v, key, val)
    db.session.commit()

    return jsonify(_serialize_product(v.product)), 200


@admin_bp.route("/products/<int:product_id>/variants/<int:variant_id>", methods=["DELETE"])
@admin_required
def delete_variant(product_id, variant_id):
    v = ProductVariant.query.filter_by(id=variant_id, product_id=product_id).first()
    if not v:
        return jsonify(error="Variant not found"), 404

    # order_items keeps a RESTRICT foreign key to the variant: past orders must
    # go on showing what was bought. Refuse cleanly instead of letting the
    # database raise.
    if db.session.query(OrderItem.id).filter_by(variant_id=v.id).first():
        return jsonify(
            error="This variant has been ordered, so it cannot be deleted. "
                  "Set its stock to 0 to stop selling it."
        ), 409

    p = v.product
    db.session.delete(v)
    db.session.commit()

    return jsonify(_serialize_product(p)), 200


# ── Images ────────────────────────────────────────────────────

@admin_bp.route("/products/<int:product_id>/images", methods=["POST"])
@admin_required
def add_image(product_id):
    try:
        data = _image_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    p = db.session.get(Product, product_id)
    if not p:
        return jsonify(error="Product not found"), 404

    if data.get("is_primary"):
        ProductImage.query.filter_by(product_id=product_id, is_primary=True).update(
            {"is_primary": False}
        )

    if not p.images:
        data["is_primary"] = True

    img = ProductImage(product_id=product_id, **data)
    db.session.add(img)
    db.session.commit()

    return jsonify(_serialize_product(p)), 201


@admin_bp.route("/products/<int:product_id>/images/<int:image_id>", methods=["DELETE"])
@admin_required
def delete_image(product_id, image_id):
    img = ProductImage.query.filter_by(id=image_id, product_id=product_id).first()
    if not img:
        return jsonify(error="Image not found"), 404

    was_primary = img.is_primary
    p = img.product
    db.session.delete(img)
    db.session.flush()

    if was_primary:
        next_img = (
            ProductImage.query
            .filter_by(product_id=product_id)
            .order_by(ProductImage.sort_order)
            .first()
        )
        if next_img:
            next_img.is_primary = True

    db.session.commit()

    return jsonify(_serialize_product(p)), 200
