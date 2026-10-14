"""The six checks that need real TEST keys, run in one go.

    flask verify-integrations          (or scripts/verify_integrations.sh)

Everything else about Razorpay and Shiprocket is proven without keys by
tests/test_integration_contracts.py. These six steps are what only the
providers' own sandboxes can confirm:

  1. test checkout      Razorpay accepts our keys and opens a payment order
  2. verification       a payment made in the storefront is captured, for the
                        amount of the order it produced
  3. refund on cancel   cancelling that order returns the money
  4. signed webhook     the webhook accepts our secret and refuses a forgery
  5. reconcile          the reconcile-payments sweep runs cleanly
  6. pincode check      Shiprocket answers a live delivery check

Refuses to run unless RAZORPAY_KEY_ID is a test key: step 3 moves money.
Step 2 needs one order paid by hand in the storefront first (the payment window
is Razorpay's own page, which only a person can complete).

Prints PASS / FAIL per step and never a key, secret or password.
"""
import hashlib
import hmac
import json
import os
import time

import requests

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
PAY_FIRST = (
    "place one order in the storefront with \"Pay online\" "
    "(test card 4111 1111 1111 1111, any future date, any CVV; or UPI success@razorpay), then run this again"
)


def _env(name):
    return (os.environ.get(name) or "").strip()


def _paid_test_order():
    """The newest order paid online that can still be cancelled."""
    from app.models.enums import OrderStatus, PaymentStatus
    from app.models.order import Order

    return (
        Order.query
        .filter(Order.payment_ref.isnot(None), Order.payment_status == PaymentStatus.paid,
                Order.status.in_([OrderStatus.pending, OrderStatus.confirmed]))
        .order_by(Order.placed_at.desc())
        .first()
    )


def _admin_headers():
    from flask_jwt_extended import create_access_token
    from app.models.admin import Admin

    admin = Admin.query.filter_by(role="master", is_active=True).first()
    if not admin:
        return None
    token = create_access_token(identity=str(admin.id), additional_claims={"actor": "admin", "role": admin.role})
    return {"Authorization": f"Bearer {token}"}


def _step_checkout():
    from app.routes.payments import RAZORPAY_ORDERS_URL

    try:
        resp = requests.post(
            RAZORPAY_ORDERS_URL, auth=(_env("RAZORPAY_KEY_ID"), _env("RAZORPAY_KEY_SECRET")),
            json={"amount": 100, "currency": "INR", "receipt": f"verify_{int(time.time())}", "payment_capture": 1},
            timeout=20,
        )
    except requests.RequestException:
        return FAIL, "Razorpay could not be reached"
    if resp.status_code == 401:
        return FAIL, "Razorpay refused the keys (check RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET belong together)"
    if resp.status_code not in (200, 201) or not str(resp.json().get("id", "")).startswith("order_"):
        return FAIL, f"Razorpay answered {resp.status_code} when opening a payment order"
    return PASS, "Razorpay opened a ₹1 test payment order (nothing is charged until someone pays it)"


def _step_verification(order):
    from app.routes.payments import fetch_payment

    if order is None:
        return FAIL, f"no order paid online was found — {PAY_FIRST}"
    payment = fetch_payment(order.payment_ref)
    if payment is None:
        return FAIL, f"Razorpay has no record of the payment on order {order.order_number}"
    if payment.get("status") != "captured":
        return FAIL, f"the payment on order {order.order_number} is \"{payment.get('status')}\", not captured"
    expected = int(round(float(order.total_amount) * 100))
    if int(payment.get("amount", -1)) != expected:
        return FAIL, f"order {order.order_number} is for {expected} paise but Razorpay captured {payment.get('amount')}"
    return PASS, f"order {order.order_number}: captured, and the amount matches the order total"


def _step_refund(app, order):
    from app.extensions import db
    from app.models.enums import PaymentStatus
    from app.models.order import Order

    if order is None:
        return SKIP, "needs the paid order from step 2"
    headers = _admin_headers()
    if headers is None:
        return FAIL, "no owner account exists to cancel the order with"
    resp = app.test_client().patch(f"/api/admin/orders/{order.id}/status", json={"status": "cancelled"}, headers=headers)
    body = resp.get_json(silent=True) or {}
    db.session.expire_all()
    fresh = db.session.get(Order, order.id)
    if resp.status_code != 200:
        return FAIL, f"cancelling order {order.order_number} answered {resp.status_code}: {body.get('error', '')}"
    if not body.get("refunded") or fresh.payment_status != PaymentStatus.refunded:
        return FAIL, f"order {order.order_number} was cancelled but Razorpay did not accept the refund"
    return PASS, f"order {order.order_number} cancelled and refunded in full (test money)"


def _step_webhook(app, order):
    secret = _env("RAZORPAY_WEBHOOK_SECRET")
    if not secret:
        return FAIL, "RAZORPAY_WEBHOOK_SECRET is not set (Razorpay Dashboard → Settings → Webhooks → Secret)"
    # An event this store does nothing with, so the check changes no order.
    raw = json.dumps({"entity": "event", "event": "order.paid", "payload": {}, "created_at": int(time.time())}).encode()

    def post(signature):
        return app.test_client().post("/api/payments/webhook", data=raw, content_type="application/json",
                                      headers={"X-Razorpay-Signature": signature}).status_code

    good = post(hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest())
    forged = post(hmac.new(b"not-the-secret", raw, hashlib.sha256).hexdigest())
    if good != 200:
        return FAIL, f"a correctly signed event was answered {good}"
    if forged == 200:
        return FAIL, "a forged signature was accepted"
    return PASS, "a signed event is accepted and a forged one refused"


def _step_reconcile():
    from app.routes.payments import reconcile_orphaned_captures

    result = reconcile_orphaned_captures(dry_run=True)
    if result.get("error"):
        return FAIL, f"the sweep stopped: {result['error']}"
    return PASS, f"checked {result.get('checked', 0)} payment(s) from the last day; {len(result.get('orphans', []))} without an order"


def _step_pincode():
    from app.services import shiprocket

    if not (_env("SHIPROCKET_EMAIL") and _env("SHIPROCKET_PASSWORD")):
        return FAIL, "SHIPROCKET_EMAIL and SHIPROCKET_PASSWORD are not set"
    try:
        result = shiprocket.check_serviceability("400001")       # Mumbai GPO: every courier serves it
    except shiprocket.ShiprocketError as err:
        return FAIL, str(err)
    if not result["serviceable"]:
        return FAIL, ("Shiprocket says nobody delivers from your pickup pincode to Mumbai 400001 — "
                      "check SHIPROCKET_PICKUP_PINCODE and that a pickup address is verified in Shiprocket")
    return PASS, f"delivery to 400001 in about {result['estimated_days']} day(s), from ₹{result['cheapest_rate']}"


def run(app):
    """Returns (lines, exit_code)."""
    key_id = _env("RAZORPAY_KEY_ID")
    if not key_id or not _env("RAZORPAY_KEY_SECRET"):
        return ["Razorpay keys are not set. Add the TEST keys to backend/.env first (docs/GO_LIVE.md, step 1)."], 2
    if not key_id.startswith("rzp_test_"):
        return ["RAZORPAY_KEY_ID is not a test key. This script cancels and refunds an order, so it only runs "
                "with test keys (they start with rzp_test_)."], 2

    order = _paid_test_order()
    steps = [
        ("1. Test checkout", _step_checkout),
        ("2. Payment verification", lambda: _step_verification(order)),
        ("3. Refund on cancel", lambda: _step_refund(app, order)),
        ("4. Signed webhook", lambda: _step_webhook(app, order)),
        ("5. Reconcile payments", _step_reconcile),
        ("6. Live pincode check", _step_pincode),
    ]
    lines, failed = [], 0
    verified = True
    for name, step in steps:
        if name.startswith("3.") and not verified:
            outcome, detail = SKIP, "step 2 did not pass, so nothing is cancelled"
        else:
            try:
                outcome, detail = step()
            except Exception as exc:  # noqa: BLE001 - one broken step must not hide the others
                outcome, detail = FAIL, f"unexpected error: {type(exc).__name__}"
        if name.startswith("2."):
            verified = outcome == PASS
        failed += outcome != PASS
        lines.append(f"{outcome:<4}  {name:<24} {detail}")
    lines.append("")
    lines.append("All six steps passed." if not failed else f"{failed} of 6 steps did not pass.")
    return lines, 0 if not failed else 1
