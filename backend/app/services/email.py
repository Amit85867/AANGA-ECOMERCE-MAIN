"""Transactional email via Resend.

Uses the Resend REST API directly (like the Razorpay and Supabase Storage
integrations) so no SDK dependency is needed. Sending is **best-effort**: a
failure never raises into the caller, because a customer's order must not fail
just because a confirmation email bounced. When email is not configured (no API
key) the message is logged instead, so local development is unchanged.

Configure with RESEND_API_KEY + EMAIL_FROM. EMAIL_ENABLED is a manual kill
switch (default on).
"""
from html import escape
import atexit
from concurrent.futures import ThreadPoolExecutor

from flask import current_app

import requests

RESEND_API_URL = "https://api.resend.com/emails"

# Two threads are plenty: sending is one short HTTPS call, and a burst simply
# queues. Threads are joined at interpreter exit, so a graceful worker shutdown
# still delivers what was queued.
_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="email")
atexit.register(_executor.shutdown, wait=True)

# Phone-only accounts get a synthetic email (see auth.verify_otp); never try to
# deliver to those.
_SYNTHETIC_EMAIL_SUFFIX = "@phone.aanga.in"


def is_email_configured(config=None):
    cfg = config or current_app.config
    return bool(cfg.get("RESEND_API_KEY") and cfg.get("EMAIL_FROM"))


def _deliverable(email):
    return bool(email) and not email.endswith(_SYNTHETIC_EMAIL_SUFFIX)


def mask(address):
    """``priya.nair@example.com`` -> ``p***@example.com``. Logs say that an
    email went to someone, not who: a log line is not the place for a
    customer's address."""
    if isinstance(address, (list, tuple)):
        address = address[0] if address else ""
    name, _, domain = str(address or "").partition("@")
    return f"{name[:1]}***@{domain}" if domain else "***"


def send_email(to, subject, html, text=None):
    """Send one transactional email. Returns True on success. Never raises."""
    if not current_app.config.get("EMAIL_ENABLED", True) or not is_email_configured():
        current_app.logger.info("[email disabled] to=%s subject=%r", mask(to), subject)
        return False
    if not _deliverable(to):
        return False

    payload = {
        "from": current_app.config["EMAIL_FROM"],
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text

    api_key = current_app.config["RESEND_API_KEY"]
    if current_app.config.get("EMAIL_ASYNC"):
        # The request is done as far as the customer is concerned; delivery
        # happens behind it. The app object is passed so the worker thread can
        # log through it.
        app = current_app._get_current_object()
        _executor.submit(_deliver_in_app, app, api_key, payload)
        return True
    return _deliver(api_key, payload, current_app.logger)


def _deliver_in_app(app, api_key, payload):
    with app.app_context():
        try:
            _deliver(api_key, payload, app.logger)
        except Exception:  # noqa: BLE001 - nothing can catch this for us
            app.logger.exception("Email delivery crashed to=%s", mask(payload.get("to")))


def _deliver(api_key, payload, logger):
    to = payload["to"][0]
    try:
        resp = requests.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=15,
        )
    except requests.RequestException:
        logger.exception("Email send failed to=%s", mask(to))
        return False

    if resp.status_code >= 300:
        logger.error(
            "Email rejected status=%s to=%s body=%s", resp.status_code, mask(to), resp.text[:300]
        )
        return False
    return True


# ── Templates ──────────────────────────────────────────────────────────────

def _store_name():
    """The owner's store name (Admin -> Store settings), for subjects and headers."""
    try:
        from app.services import store_settings
        return store_settings.get("store_name") or "AANGA"
    except Exception:  # noqa: BLE001 - an email must not fail over a settings lookup
        return "AANGA"


def _wrap(inner):
    name = escape(_store_name())
    return (
        '<div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;'
        'color:#1a1a1a">'
        f'<h1 style="font-size:20px;letter-spacing:2px">{name}</h1>'
        f"{inner}"
        '<hr style="border:none;border-top:1px solid #eee;margin:24px 0">'
        '<p style="font-size:12px;color:#888">You are receiving this because you have '
        f"an account at {name}.</p></div>"
    )


def send_password_reset(email, reset_link):
    store = _store_name()
    html = _wrap(
        "<p>We received a request to reset your password. This link expires in "
        "one hour:</p>"
        f'<p><a href="{escape(reset_link, quote=True)}" style="background:#1a1a1a;color:#fff;'
        'padding:12px 20px;text-decoration:none;display:inline-block">Reset '
        "password</a></p>"
        "<p>If you didn't ask for this, you can safely ignore this email.</p>"
    )
    return send_email(
        email,
        f"Reset your {store} password",
        html,
        text=f"Reset your {store} password (expires in 1 hour): {reset_link}",
    )


def _rupees(value):
    """12,34,567.50 — grouped the Indian way, as the storefront shows prices."""
    whole, paise = f"{abs(float(value)):.2f}".split(".")
    head, tail = whole[:-3], whole[-3:]
    groups = []
    while head:
        groups.insert(0, head[-2:])
        head = head[:-2]
    return ("-" if float(value) < 0 else "") + ",".join(groups + [tail]) + "." + paise


def _money(value):
    return f"&#8377;{_rupees(value)}"


def order_confirmation_content(order):
    """``(subject, html, text)`` for an order. Separate from sending so the
    figures can be checked against the order itself."""
    user = order.user
    store = _store_name()
    cell = 'style="padding:6px 0"'
    right = 'style="padding:6px 0;text-align:right"'

    rows = ""
    for item in order.items:
        variant = item.variant
        # Everything a person typed is escaped: a product or customer name is
        # text, never markup.
        label = escape(f"{variant.product.name} ({variant.size}/{variant.color_name})")
        rows += (
            f"<tr><td {cell}>{label} &times; {item.quantity}</td>"
            f"<td {right}>{_money(float(item.unit_price) * item.quantity)}</td></tr>"
        )

    summary = f"<tr><td {cell}>Subtotal</td><td {right}>{_money(order.subtotal)}</td></tr>"
    if float(order.discount_amount or 0) > 0:
        summary += f"<tr><td {cell}>Discount</td><td {right}>&minus;{_money(order.discount_amount)}</td></tr>"
    summary += f"<tr><td {cell}>GST</td><td {right}>{_money(order.gst_amount)}</td></tr>"
    delivery = "Free" if float(order.delivery_charge or 0) == 0 else _money(order.delivery_charge)
    summary += f"<tr><td {cell}>Delivery</td><td {right}>{delivery}</td></tr>"

    payment = "Cash on delivery" if order.payment_method.value == "cod" else "Paid online"
    site = (current_app.config.get("SITE_URL") or current_app.config.get("FRONTEND_ORIGIN") or "").rstrip("/")
    link = f"{site}/account/orders/{order.id}"

    html = _wrap(
        f"<p>Thanks for your order, {escape(user.full_name or '')}! We&rsquo;ve received it and "
        "will let you know when it ships.</p>"
        f"<p><strong>Order {escape(order.order_number)}</strong> &middot; {payment}</p>"
        f'<table style="width:100%;border-collapse:collapse;font-size:14px">{rows}'
        f'<tr><td colspan="2" style="border-top:1px solid #eee;padding:0"></td></tr>{summary}'
        f'<tr><td style="padding-top:10px;font-weight:600">Total</td>'
        f'<td style="padding-top:10px;text-align:right;font-weight:600">'
        f"{_money(order.total_amount)}</td></tr></table>"
        f'<p><a href="{escape(link, quote=True)}">View your order</a></p>'
    )
    text = (
        f"Order {order.order_number} confirmed ({payment}). "
        f"Total: Rs.{_rupees(order.total_amount)}. View it: {link}"
    )
    return f"Your {store} order {order.order_number} is confirmed", html, text


def send_order_confirmation(order):
    """Confirm a placed order. Safe to call for any order; no-ops if undeliverable."""
    user = getattr(order, "user", None)
    email = getattr(user, "email", None)
    if not _deliverable(email):
        return False
    subject, html, text = order_confirmation_content(order)
    return send_email(email, subject, html, text=text)
