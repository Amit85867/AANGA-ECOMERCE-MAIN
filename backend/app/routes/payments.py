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
import json
import time
import hashlib

import requests
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db, limiter
from app.models.cart import Cart
from app.models.order import Order
from app.models.enums import PaymentStatus
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


# A webhook for payment.captured routinely beats the browser's /verify call to
# the server, so "captured but no order" is the NORMAL state for a few seconds.
# Only a payment older than this window is treated as genuinely abandoned.
ORPHAN_GRACE_SECONDS = int(os.environ.get("RAZORPAY_ORPHAN_GRACE_SECONDS", 900))


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


@payments_bp.route("/webhook", methods=["POST"])
@limiter.exempt
def razorpay_webhook():
    """Razorpay server-to-server events.

    Configure in the Razorpay Dashboard → Settings → Webhooks, subscribing to
    ``payment.captured``, ``payment.failed`` and ``refund.processed``, with the
    same secret as RAZORPAY_WEBHOOK_SECRET.

    This closes the hole where a customer's browser dies between capture and
    /verify: the money is captured, no order exists, and nothing would ever
    notice. Here an orphaned capture past ORPHAN_GRACE_SECONDS is refunded
    automatically.

    Unauthenticated by design — the shared-secret signature over the raw body
    is the authentication, so the body must be read verbatim (not re-serialised)
    before it is parsed.
    """
    secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET")
    if not secret:
        return jsonify(error="Webhooks are not configured"), 503

    raw = request.get_data()
    sent_sig = request.headers.get("X-Razorpay-Signature", "")
    expected_sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, sent_sig):
        current_app.logger.warning("RAZORPAY_WEBHOOK_BAD_SIGNATURE")
        return jsonify(error="Invalid signature"), 400

    try:
        event = json.loads(raw)
    except ValueError:
        return jsonify(error="Malformed payload"), 400

    kind = event.get("event")
    entities = event.get("payload") or {}

    if kind == "payment.captured":
        payment = (entities.get("payment") or {}).get("entity") or {}
        _handle_captured(payment)
    elif kind == "payment.failed":
        payment = (entities.get("payment") or {}).get("entity") or {}
        _mark_payment_status(payment.get("id"), PaymentStatus.failed)
    elif kind == "refund.processed":
        refund = (entities.get("refund") or {}).get("entity") or {}
        _mark_payment_status(refund.get("payment_id"), PaymentStatus.refunded)

    # Always 200 for a correctly signed event: a non-2xx makes Razorpay retry,
    # and retrying will not fix anything we failed to interpret.
    return jsonify(status="ok"), 200


def _handle_captured(payment):
    """Refund a capture that never became an order, once past the grace window."""
    payment_id = payment.get("id")
    if not payment_id:
        return

    if Order.query.filter_by(payment_ref=payment_id).first():
        return  # the normal path — /verify already created the order

    created_at = payment.get("created_at")
    age = time.time() - created_at if created_at else 0
    if age < ORPHAN_GRACE_SECONDS:
        # Almost certainly an in-flight checkout; the reconcile sweep will pick
        # it up later if /verify never lands.
        current_app.logger.info(
            "RAZORPAY_CAPTURE_PENDING_ORDER payment=%s age=%.0fs", payment_id, age
        )
        return

    refunded = refund_payment(payment_id, payment.get("amount"))
    current_app.logger.critical(
        "ORPHANED_CAPTURE_REFUNDED payment=%s amount=%s age=%.0fs refunded=%s",
        payment_id, payment.get("amount"), age, refunded,
    )


def reconcile_orphaned_captures(window_seconds=86400, dry_run=False):
    """Find captured payments with no order and refund the abandoned ones.

    The safety net behind the webhook: a webhook that was never delivered (or
    arrived while the app was down) would otherwise leave a customer charged
    with nothing to show for it. Run periodically — see the ``reconcile-payments``
    CLI command.

    Returns a summary dict; never raises on a single bad payment.
    """
    key_id, key_secret = _keys()
    if not key_id or not key_secret:
        return {"configured": False, "checked": 0, "refunded": 0, "orphans": []}

    now = int(time.time())
    try:
        resp = requests.get(
            f"{RAZORPAY_API}/payments",
            auth=(key_id, key_secret),
            params={"from": now - window_seconds, "to": now, "count": 100},
            timeout=30,
        )
    except requests.RequestException:
        return {"configured": True, "error": "gateway unreachable",
                "checked": 0, "refunded": 0, "orphans": []}

    if resp.status_code != 200:
        return {"configured": True, "error": f"gateway returned {resp.status_code}",
                "checked": 0, "refunded": 0, "orphans": []}

    payments = resp.json().get("items", [])
    orphans, refunded_count = [], 0

    for payment in payments:
        if payment.get("status") != "captured":
            continue
        payment_id = payment.get("id")
        if Order.query.filter_by(payment_ref=payment_id).first():
            continue
        age = now - (payment.get("created_at") or now)
        if age < ORPHAN_GRACE_SECONDS:
            continue

        orphans.append({"id": payment_id, "amount": payment.get("amount"), "age": age})
        if dry_run:
            continue
        if refund_payment(payment_id, payment.get("amount")):
            refunded_count += 1
            current_app.logger.critical(
                "ORPHANED_CAPTURE_REFUNDED_BY_SWEEP payment=%s amount=%s age=%ss",
                payment_id, payment.get("amount"), age,
            )
        else:
            current_app.logger.critical(
                "ORPHANED_CAPTURE_REFUND_FAILED payment=%s amount=%s age=%ss",
                payment_id, payment.get("amount"), age,
            )

    return {
        "configured": True,
        "checked": len(payments),
        "orphans": orphans,
        "refunded": refunded_count,
    }


def _mark_payment_status(payment_id, status):
    if not payment_id:
        return
    order = Order.query.filter_by(payment_ref=payment_id).first()
    if not order:
        return
    order.payment_status = status
    db.session.commit()


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
