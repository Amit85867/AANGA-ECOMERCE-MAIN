"""Razorpay online payments: create order + verify signature.

Uses the Razorpay REST API directly (via requests) and verifies the payment
signature with HMAC-SHA256, so no extra SDK dependency is required.

Configure with env vars RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET. When they are
absent the endpoints return 503 and the storefront keeps COD-only.
"""
import os
import hmac
import hashlib

import requests
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models.cart import Cart
from app.services.order_service import compute_totals, create_order_from_cart

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")

RAZORPAY_ORDERS_URL = "https://api.razorpay.com/v1/orders"

# Frontend payment ids → backend PaymentMethod enum values
METHOD_MAP = {
    "upi": "upi",
    "card": "credit_card",
    "netbanking": "net_banking",
    "wallet": "wallet",
}


def _keys():
    return os.environ.get("RAZORPAY_KEY_ID"), os.environ.get("RAZORPAY_KEY_SECRET")


@payments_bp.route("/create-order", methods=["POST"])
@jwt_required()
def create_payment_order():
    key_id, key_secret = _keys()
    if not key_id or not key_secret:
        return jsonify(error="Online payments are not configured"), 503

    cart = Cart.query.filter_by(user_id=get_jwt_identity()).first()
    if not cart or not cart.items:
        return jsonify(error="Cart is empty"), 422

    totals = compute_totals(cart)
    amount_paise = int(round(totals["total"] * 100))

    try:
        resp = requests.post(
            RAZORPAY_ORDERS_URL,
            auth=(key_id, key_secret),
            json={
                "amount": amount_paise,
                "currency": "INR",
                "receipt": f"cart_{cart.id}",
                "payment_capture": 1,
            },
            timeout=15,
        )
    except requests.RequestException:
        return jsonify(error="Payment gateway unreachable"), 502

    if resp.status_code not in (200, 201):
        return jsonify(error="Could not initiate payment"), 502

    rzp = resp.json()
    return jsonify(
        razorpay_order_id=rzp["id"],
        amount=amount_paise,
        currency="INR",
        key_id=key_id,
    ), 200


@payments_bp.route("/verify", methods=["POST"])
@jwt_required()
def verify_payment():
    _, key_secret = _keys()
    if not key_secret:
        return jsonify(error="Online payments are not configured"), 503

    data = request.get_json() or {}
    rzp_order = data.get("razorpay_order_id")
    rzp_payment = data.get("razorpay_payment_id")
    rzp_sig = data.get("razorpay_signature")
    address_id = data.get("address_id")
    frontend_method = data.get("payment_method", "upi")

    if not all([rzp_order, rzp_payment, rzp_sig, address_id]):
        return jsonify(error="Missing payment verification fields"), 422

    expected = hmac.new(
        key_secret.encode(),
        f"{rzp_order}|{rzp_payment}".encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, rzp_sig):
        return jsonify(error="Payment verification failed"), 400

    method_value = METHOD_MAP.get(frontend_method, "upi")
    order, err = create_order_from_cart(
        get_jwt_identity(),
        address_id,
        method_value,
        payment_ref=rzp_payment,
        paid=True,
    )
    if err:
        return jsonify(error=err[0]), err[1]

    return jsonify(order_number=order.order_number, order_id=order.id), 201
