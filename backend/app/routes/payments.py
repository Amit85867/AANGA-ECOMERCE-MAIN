"""Razorpay online payments: create order + verify signature + reconcile.

Uses the Razorpay REST API directly (via requests) and verifies the payment
signature with HMAC-SHA256, so no extra SDK dependency is required.

The signature only proves the ``{order_id}|{payment_id}`` pair came from
Razorpay — it does NOT bind an amount or a status. So on /verify we also fetch
the payment from Razorpay and confirm it was actually captured, belongs to the
order we created, and its amount matches the order total computed server-side.
Only then is the order created. If the money was captured but the order cannot
be placed (e.g. a stock race), we auto-refund so the customer is never charged
for nothing.

Configure with env vars RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET. When they are
absent the endpoints return 503 and the storefront keeps COD-only.
"""
import os
import hmac
import hashlib

import requests
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models.cart import Cart
from app.models.order import Order
from app.services.order_service import compute_totals, create_order_from_cart

payments_bp = Blueprint("payments", __name__, url_prefix="/api/payments")

RAZORPAY_API = "https://api.razorpay.com/v1"
RAZORPAY_ORDERS_URL = f"{RAZORPAY_API}/orders"

# Frontend payment ids → backend PaymentMethod enum values
METHOD_MAP = {
    "upi": "upi",
    "card": "credit_card",
    "netbanking": "net_banking",
    "wallet": "wallet",
}


def _keys():
    return os.environ.get("RAZORPAY_KEY_ID"), os.environ.get("RAZORPAY_KEY_SECRET")


def fetch_payment(payment_id):
    """Fetch a payment from Razorpay. Returns the JSON dict or None on failure.

    Kept as a module-level function so it can be mocked in tests without hitting
    the network.
    """
    key_id, key_secret = _keys()
    try:
        resp = requests.get(
            f"{RAZORPAY_API}/payments/{payment_id}",
            auth=(key_id, key_secret),
            timeout=15,
        )
    except requests.RequestException:
        return None
    if resp.status_code != 200:
        return None
    return resp.json()


def refund_payment(payment_id, amount_paise=None):
    """Refund a captured payment. Returns True on success, False otherwise.

    Idempotent: Razorpay dedupes refunds sharing an ``Idempotency-Key`` header,
    so a retried paid-but-no-stock path never double-refunds.
    """
    key_id, key_secret = _keys()
    body = {}
    if amount_paise is not None:
        body["amount"] = int(amount_paise)
    try:
        resp = requests.post(
            f"{RAZORPAY_API}/payments/{payment_id}/refund",
            auth=(key_id, key_secret),
            json=body,
            headers={"Idempotency-Key": f"refund_{payment_id}"},
            timeout=15,
        )
    except requests.RequestException:
        return False
    return resp.status_code in (200, 201)


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
    key_id, key_secret = _keys()
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

    # 1. The signature proves Razorpay generated this order/payment pair.
    expected_sig = hmac.new(
        key_secret.encode(),
        f"{rzp_order}|{rzp_payment}".encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected_sig, rzp_sig):
        return jsonify(error="Payment verification failed"), 400

    user_id = get_jwt_identity()

    # 2. Idempotent replay: if this payment already produced an order, return it
    #    (the cart is gone by now, so this must short-circuit before the cart
    #    check below).
    existing = Order.query.filter_by(payment_ref=rzp_payment).first()
    if existing:
        return jsonify(order_number=existing.order_number, order_id=existing.id), 200

    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart or not cart.items:
        return jsonify(error="Cart is empty"), 422

    # 3. Reconcile against the gateway. The signature does not bind an amount or
    #    a status, so confirm the payment was actually captured, belongs to this
    #    order, and its amount matches the total we compute server-side. This
    #    stops a client paying for a cheap cart and then swapping in an
    #    expensive one before verify (or vice-versa).
    expected_paise = int(round(compute_totals(cart)["total"] * 100))
    payment = fetch_payment(rzp_payment)
    if payment is None:
        return jsonify(error="Could not verify the payment with the gateway"), 502
    if payment.get("status") != "captured":
        return jsonify(error="Payment has not been captured"), 400
    if payment.get("order_id") != rzp_order:
        return jsonify(error="Payment does not belong to this order"), 400
    if int(payment.get("amount", -1)) != expected_paise:
        current_app.logger.warning(
            "PAYMENT_AMOUNT_MISMATCH payment=%s user=%s gateway=%s expected=%s",
            rzp_payment, user_id, payment.get("amount"), expected_paise,
        )
        return jsonify(error="Payment amount does not match the order total"), 400

    # 4. Everything checks out — create the paid order.
    method_value = METHOD_MAP.get(frontend_method, "upi")
    order, err = create_order_from_cart(
        user_id, address_id, method_value, payment_ref=rzp_payment, paid=True,
    )
    if err:
        # Money was captured but the order could not be created (e.g. a stock
        # race). Never keep the customer's money with no order: auto-refund,
        # and log loudly as a fallback in case the refund call itself fails.
        refunded = refund_payment(rzp_payment, expected_paise)
        current_app.logger.critical(
            "PAID_BUT_NO_ORDER razorpay_payment_id=%s user=%s reason=%s refunded=%s",
            rzp_payment, user_id, err[0], refunded,
        )
        if refunded:
            message = (
                "Your payment was received but the order could not be placed, "
                "so it has been refunded. Please try again."
            )
        else:
            message = (
                "Your payment was received but the order could not be placed. "
                "Our team has been notified and will refund you shortly."
            )
        return jsonify(error=message, payment_ref=rzp_payment, refunded=refunded), 409

    return jsonify(order_number=order.order_number, order_id=order.id), 201
