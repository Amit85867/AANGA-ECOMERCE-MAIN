"""Admin category management: CRUD."""
from flask import request, jsonify
from marshmallow import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import subqueryload

from app.extensions import db
from app.models.catalogue import Category, Product
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.schemas.admin import AdminCategoryIn

_cat_in = AdminCategoryIn()


def _serialize_category(cat):
    """Flat representation, used by the create/update responses."""
    return {
        "id": cat.id,
        "name": cat.name,
        "slug": cat.slug,
        "description": cat.description,
        "image_url": cat.image_url,
        "parent_id": cat.parent_id,
        "sort_order": cat.sort_order,
        "is_active": cat.is_active,
    }


def _serialize_tree(cat, counts):
    return {
        **_serialize_category(cat),
        "product_count": counts.get(cat.id, 0),
        "children": [_serialize_tree(ch, counts) for ch in cat.children],
    }


@admin_bp.route("/categories", methods=["GET"])
@admin_required
def list_all_categories():
    cats = (
        Category.query
        .options(subqueryload(Category.children))
        .order_by(Category.sort_order)
        .all()
    )
    counts = dict(
        db.session.query(Product.category_id, func.count(Product.id))
        .group_by(Product.category_id)
        .all()
    )
    roots = [c for c in cats if c.parent_id is None]
    return jsonify(categories=[_serialize_tree(r, counts) for r in roots]), 200


@admin_bp.route("/categories", methods=["POST"])
@admin_required
def create_category():
    try:
        data = _cat_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    if Category.query.filter_by(slug=data["slug"]).first():
        return jsonify(error="Slug already exists"), 409

    cat = Category(**data)
    db.session.add(cat)
    db.session.commit()

    return jsonify(_serialize_category(cat)), 201


@admin_bp.route("/categories/<int:cat_id>", methods=["PUT"])
@admin_required
def update_category(cat_id):
    try:
        data = _cat_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    cat = db.session.get(Category, cat_id)
    if not cat:
        return jsonify(error="Category not found"), 404

    dup = Category.query.filter(Category.slug == data["slug"], Category.id != cat_id).first()
    if dup:
        return jsonify(error="Slug already exists"), 409

    for key, val in data.items():
        setattr(cat, key, val)
    db.session.commit()

    return jsonify(_serialize_category(cat)), 200


@admin_bp.route("/categories/<int:cat_id>", methods=["DELETE"])
@admin_required
def delete_category(cat_id):
    cat = db.session.get(Category, cat_id)
    if not cat:
        return jsonify(error="Category not found"), 404

    if cat.products:
        return jsonify(error="Cannot delete category with products — reassign them first"), 422

    cat.is_active = False
    db.session.commit()

    return jsonify(message="Category deactivated"), 200
