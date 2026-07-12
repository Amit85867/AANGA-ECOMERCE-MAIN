"""Admin feature ("Why Choose") management: CRUD."""
from flask import request, jsonify
from marshmallow import ValidationError

from app.extensions import db
from app.models.cms import Feature
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.schemas.admin import AdminFeatureIn

_in = AdminFeatureIn()


def _serialize(f):
    return {
        "id": f.id,
        "icon": f.icon,
        "title": f.title,
        "description": f.description,
        "image_url": f.image_url,
        "sort_order": f.sort_order,
        "is_active": f.is_active,
        "created_at": f.created_at.isoformat(),
    }


@admin_bp.route("/features", methods=["GET"])
@admin_required
def admin_list_features():
    items = Feature.query.order_by(Feature.sort_order, Feature.created_at.desc()).all()
    return jsonify(features=[_serialize(f) for f in items]), 200


@admin_bp.route("/features", methods=["POST"])
@admin_required
def create_feature():
    try:
        data = _in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    f = Feature(**data)
    db.session.add(f)
    db.session.commit()
    return jsonify(_serialize(f)), 201


@admin_bp.route("/features/<int:fid>", methods=["PUT"])
@admin_required
def update_feature(fid):
    try:
        data = _in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    f = db.session.get(Feature, fid)
    if not f:
        return jsonify(error="Feature not found"), 404

    for k, v in data.items():
        setattr(f, k, v)
    db.session.commit()
    return jsonify(_serialize(f)), 200


@admin_bp.route("/features/<int:fid>", methods=["DELETE"])
@admin_required
def delete_feature(fid):
    f = db.session.get(Feature, fid)
    if not f:
        return jsonify(error="Feature not found"), 404
    db.session.delete(f)
    db.session.commit()
    return jsonify(message="Feature deleted"), 200
