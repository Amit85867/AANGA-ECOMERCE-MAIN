"""Admin coupon management: CRUD."""
from flask import request, jsonify
from marshmallow import ValidationError

from app.extensions import db
from app.models.engagement import Coupon
from app.models.enums import DiscountType
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.utils.pagination import page_meta, paginate
from app.schemas.admin import AdminCouponIn

_coupon_in = AdminCouponIn()


def _serialize_coupon(c):
    return {
        "id": c.id,
        "code": c.code,
        "description": c.description,
        "discount_type": c.discount_type.value,
        "discount_value": float(c.discount_value),
        "min_order_value": float(c.min_order_value),
        "max_discount": float(c.max_discount) if c.max_discount else None,
        "usage_limit": c.usage_limit,
        "used_count": c.used_count,
        "is_active": c.is_active,
        "campaign_id": c.campaign_id,
        "is_demo": c.is_demo,
        "expires_at": c.expires_at.isoformat() if c.expires_at else None,
        "created_at": c.created_at.isoformat(),
    }


@admin_bp.route("/coupons", methods=["GET"])
@admin_required
def list_coupons():
    q = Coupon.query
    search = (request.args.get("q") or "").strip()
    if search:
        q = q.filter(Coupon.code.ilike(f"%{search}%"))

    # Capped rather than unbounded: these lists are short today, and this
    # is what keeps them cheap when they are not.
    page = paginate(q.order_by(Coupon.created_at.desc()), default=50)
    return jsonify(
        coupons=[_serialize_coupon(row) for row in page.items], **page_meta(page)
    ), 200


@admin_bp.route("/coupons", methods=["POST"])
@admin_required
def create_coupon():
    try:
        data = _coupon_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    code = data["code"].upper()
    if Coupon.query.filter_by(code=code).first():
        return jsonify(error="Coupon code already exists"), 409

    coupon = Coupon(
        code=code,
        description=data.get("description"),
        discount_type=DiscountType(data["discount_type"]),
        discount_value=data["discount_value"],
        min_order_value=data.get("min_order_value", 0),
        max_discount=data.get("max_discount"),
        usage_limit=data.get("usage_limit"),
        is_active=data.get("is_active", True),
        expires_at=data.get("expires_at"),
    )
    db.session.add(coupon)
    db.session.commit()

    return jsonify(_serialize_coupon(coupon)), 201


@admin_bp.route("/coupons/<int:coupon_id>", methods=["PUT"])
@admin_required
def update_coupon(coupon_id):
    try:
        data = _coupon_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    coupon = db.session.get(Coupon, coupon_id)
    if not coupon:
        return jsonify(error="Coupon not found"), 404

    code = data["code"].upper()
    dup = Coupon.query.filter(Coupon.code == code, Coupon.id != coupon_id).first()
    if dup:
        return jsonify(error="Coupon code already exists"), 409

    coupon.code = code
    coupon.description = data.get("description")
    coupon.discount_type = DiscountType(data["discount_type"])
    coupon.discount_value = data["discount_value"]
    coupon.min_order_value = data.get("min_order_value", 0)
    coupon.max_discount = data.get("max_discount")
    coupon.usage_limit = data.get("usage_limit")
    coupon.is_active = data.get("is_active", True)
    coupon.expires_at = data.get("expires_at")

    db.session.commit()

    return jsonify(_serialize_coupon(coupon)), 200


@admin_bp.route("/coupons/<int:coupon_id>", methods=["DELETE"])
@admin_required
def delete_coupon(coupon_id):
    coupon = db.session.get(Coupon, coupon_id)
    if not coupon:
        return jsonify(error="Coupon not found"), 404

    db.session.delete(coupon)
    db.session.commit()

    return jsonify(message="Coupon deleted"), 200
