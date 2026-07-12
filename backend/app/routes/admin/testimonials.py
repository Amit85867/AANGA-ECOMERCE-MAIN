"""Admin testimonial management: CRUD."""
from flask import request, jsonify
from marshmallow import ValidationError

from app.extensions import db
from app.models.cms import Testimonial
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.schemas.admin import AdminTestimonialIn

_in = AdminTestimonialIn()


def _serialize(t):
    return {
        "id": t.id,
        "name": t.name,
        "location": t.location,
        "rating": t.rating,
        "quote": t.quote,
        "avatar_url": t.avatar_url,
        "sort_order": t.sort_order,
        "is_active": t.is_active,
        "created_at": t.created_at.isoformat(),
    }


@admin_bp.route("/testimonials", methods=["GET"])
@admin_required
def admin_list_testimonials():
    items = Testimonial.query.order_by(Testimonial.sort_order, Testimonial.created_at.desc()).all()
    return jsonify(testimonials=[_serialize(t) for t in items]), 200


@admin_bp.route("/testimonials", methods=["POST"])
@admin_required
def create_testimonial():
    try:
        data = _in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    t = Testimonial(**data)
    db.session.add(t)
    db.session.commit()
    return jsonify(_serialize(t)), 201


@admin_bp.route("/testimonials/<int:tid>", methods=["PUT"])
@admin_required
def update_testimonial(tid):
    try:
        data = _in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    t = db.session.get(Testimonial, tid)
    if not t:
        return jsonify(error="Testimonial not found"), 404

    for k, v in data.items():
        setattr(t, k, v)
    db.session.commit()
    return jsonify(_serialize(t)), 200


@admin_bp.route("/testimonials/<int:tid>", methods=["DELETE"])
@admin_required
def delete_testimonial(tid):
    t = db.session.get(Testimonial, tid)
    if not t:
        return jsonify(error="Testimonial not found"), 404
    db.session.delete(t)
    db.session.commit()
    return jsonify(message="Testimonial deleted"), 200
