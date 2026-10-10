"""Category listing."""
from flask import Blueprint, jsonify

from app.models.catalogue import Category
from app.services.cache import cached_view

categories_bp = Blueprint("categories", __name__, url_prefix="/api/categories")


@categories_bp.route("", methods=["GET"])
@cached_view(300)
def list_categories():
    cats = (
        Category.query
        .filter_by(is_active=True)
        .order_by(Category.sort_order)
        .all()
    )

    def _serialize(cat):
        return {
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "description": cat.description,
            "image_url": cat.image_url,
            "parent_id": cat.parent_id,
            "children": [_serialize(c) for c in cat.children if c.is_active],
        }

    roots = [c for c in cats if c.parent_id is None]
    return jsonify(categories=[_serialize(r) for r in roots]), 200
