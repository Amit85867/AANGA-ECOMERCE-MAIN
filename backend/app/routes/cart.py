"""Shopping cart: get, add item, update qty, remove, apply/remove coupon."""
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.extensions import db
from app.models.cart import Cart, CartItem
from app.models.catalogue import Product, ProductVariant, ProductImage
from app.models.engagement import Coupon
from app.schemas.cart import CartItemIn, CartItemUpdateIn, ApplyCouponIn, CartOut
from app.services.order_service import compute_totals

cart_bp = Blueprint("cart", __name__, url_prefix="/api/cart")

_item_in = CartItemIn()
_item_update = CartItemUpdateIn()
_coupon_in = ApplyCouponIn()
_cart_out = CartOut()


def _get_or_create_cart(user_id):
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.flush()
    return cart


def _serialize_cart(cart):
    items = []
    subtotal = 0
    mrp_total = 0

    for ci in cart.items:
        variant = ci.variant
        product = variant.product
        primary_img = (
            ProductImage.query
            .filter_by(product_id=product.id, is_primary=True)
            .first()
        )
        line_total = float(ci.unit_price) * ci.quantity
        mrp_line = float(product.mrp) * ci.quantity
        subtotal += line_total
        mrp_total += mrp_line

        items.append({
            "id": ci.id,
            "variant_id": variant.id,
            "product_name": product.name,
            "product_slug": product.slug,
            "size": variant.size,
            "color_name": variant.color_name,
            "color_hex": variant.color_hex,
            "image_url": primary_img.image_url if primary_img else None,
            "quantity": ci.quantity,
            "unit_price": float(ci.unit_price),
            "mrp": float(product.mrp),
            "line_total": line_total,
        })

    # Single source of truth, shared with checkout. Computing GST/shipping/
    # discount separately here once meant the cart could quote one price while
    # the order charged another.
    totals = compute_totals(cart)
    savings = round(mrp_total - subtotal + totals["discount"], 2)

    return _cart_out.dump({
        "id": cart.id,
        "items": items,
        "coupon_code": cart.coupon.code if cart.coupon else None,
        "subtotal": totals["subtotal"],
        "discount": totals["discount"],
        "gst": totals["gst"],
        "delivery_charge": totals["delivery"],
        "total": totals["total"],
        "savings": savings,
        "item_count": sum(ci.quantity for ci in cart.items),
    })


@cart_bp.route("", methods=["GET"])
@jwt_required()
def get_cart():
    cart = _get_or_create_cart(get_jwt_identity())
    return jsonify(_serialize_cart(cart)), 200


@cart_bp.route("/items", methods=["POST"])
@jwt_required()
def add_item():
    try:
        data = _item_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    variant = db.session.get(ProductVariant, data["variant_id"])
    if not variant or not variant.product.is_active:
        return jsonify(error="Variant not found"), 404

    cart = _get_or_create_cart(get_jwt_identity())

    existing = CartItem.query.filter_by(cart_id=cart.id, variant_id=variant.id).first()
    # Stock is checked against what the line would hold afterwards, not just
    # this request, or adding the same item twice walks past the limit.
    wanted = data["quantity"] + (existing.quantity if existing else 0)
    if variant.stock_qty < wanted:
        return jsonify(error="Insufficient stock"), 409

    if existing:
        existing.quantity += data["quantity"]
        existing.updated_at = datetime.now(timezone.utc)
    else:
        price = float(variant.price_override or variant.product.selling_price)
        ci = CartItem(
            cart_id=cart.id,
            variant_id=variant.id,
            quantity=data["quantity"],
            unit_price=price,
        )
        db.session.add(ci)

    db.session.commit()
    return jsonify(_serialize_cart(cart)), 200


@cart_bp.route("/items/<int:item_id>", methods=["PATCH"])
@jwt_required()
def update_item(item_id):
    try:
        data = _item_update.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    cart = _get_or_create_cart(get_jwt_identity())
    ci = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()
    if not ci:
        return jsonify(error="Cart item not found"), 404

    if data["quantity"] <= 0:
        db.session.delete(ci)
    else:
        if ci.variant.stock_qty < data["quantity"]:
            return jsonify(error="Insufficient stock"), 409
        ci.quantity = data["quantity"]
        ci.updated_at = datetime.now(timezone.utc)

    db.session.commit()
    return jsonify(_serialize_cart(cart)), 200


@cart_bp.route("/items/<int:item_id>", methods=["DELETE"])
@jwt_required()
def remove_item(item_id):
    cart = _get_or_create_cart(get_jwt_identity())
    ci = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first()
    if not ci:
        return jsonify(error="Cart item not found"), 404

    db.session.delete(ci)
    db.session.commit()
    return jsonify(_serialize_cart(cart)), 200


@cart_bp.route("/coupon", methods=["POST"])
@jwt_required()
def apply_coupon():
    try:
        data = _coupon_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    coupon = Coupon.query.filter_by(code=data["code"].upper(), is_active=True).first()
    if not coupon:
        return jsonify(error="Invalid coupon code"), 404

    now = datetime.now(timezone.utc)
    if coupon.expires_at and coupon.expires_at < now:
        return jsonify(error="Coupon has expired"), 410

    if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
        return jsonify(error="Coupon usage limit reached"), 410

    cart = _get_or_create_cart(get_jwt_identity())

    subtotal = sum(float(ci.unit_price) * ci.quantity for ci in cart.items)
    if subtotal < float(coupon.min_order_value):
        return jsonify(error=f"Minimum order value is ₹{coupon.min_order_value}"), 422

    cart.coupon_id = coupon.id
    db.session.commit()
    return jsonify(_serialize_cart(cart)), 200


@cart_bp.route("/coupon", methods=["DELETE"])
@jwt_required()
def remove_coupon():
    cart = _get_or_create_cart(get_jwt_identity())
    cart.coupon_id = None
    db.session.commit()
    return jsonify(_serialize_cart(cart)), 200
