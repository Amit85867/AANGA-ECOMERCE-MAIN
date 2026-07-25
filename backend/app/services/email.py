"""Transactional email via Resend.

Uses the Resend REST API directly (like the Razorpay and Supabase Storage
integrations) so no SDK dependency is needed. Sending is **best-effort**: a
failure never raises into the caller, because a customer's order must not fail
just because a confirmation email bounced. When email is not configured (no API
key) the message is logged instead, so local development is unchanged.

Configure with RESEND_API_KEY + EMAIL_FROM. EMAIL_ENABLED is a manual kill
switch (default on).
"""
from flask import current_app

import requests

RESEND_API_URL = "https://api.resend.com/emails"

# Phone-only accounts get a synthetic email (see auth.verify_otp); never try to
# deliver to those.
_SYNTHETIC_EMAIL_SUFFIX = "@phone.aanga.in"


def is_email_configured(config=None):
    cfg = config or current_app.config
    return bool(cfg.get("RESEND_API_KEY") and cfg.get("EMAIL_FROM"))


def _deliverable(email):
    return bool(email) and not email.endswith(_SYNTHETIC_EMAIL_SUFFIX)


def send_email(to, subject, html, text=None):
    """Send one transactional email. Returns True on success. Never raises."""
    if not current_app.config.get("EMAIL_ENABLED", True) or not is_email_configured():
        current_app.logger.info("[email disabled] to=%s subject=%r", to, subject)
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

    try:
        resp = requests.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {current_app.config['RESEND_API_KEY']}"},
            json=payload,
            timeout=15,
        )
    except requests.RequestException:
        current_app.logger.exception("Email send failed to=%s", to)
        return False

    if resp.status_code >= 300:
        current_app.logger.error(
            "Email rejected status=%s to=%s body=%s", resp.status_code, to, resp.text[:300]
        )
        return False
    return True


# ── Templates ──────────────────────────────────────────────────────────────

def _wrap(inner):
    return (
        '<div style="font-family:Inter,Arial,sans-serif;max-width:560px;margin:0 auto;'
        'color:#1a1a1a">'
        '<h1 style="font-size:20px;letter-spacing:2px">AANGA</h1>'
        f"{inner}"
        '<hr style="border:none;border-top:1px solid #eee;margin:24px 0">'
        '<p style="font-size:12px;color:#888">You are receiving this because you have '
        "an account at AANGA.</p></div>"
    )


def send_password_reset(email, reset_link):
    html = _wrap(
        "<p>We received a request to reset your password. This link expires in "
        "one hour:</p>"
        f'<p><a href="{reset_link}" style="background:#1a1a1a;color:#fff;'
        'padding:12px 20px;text-decoration:none;display:inline-block">Reset '
        "password</a></p>"
        "<p>If you didn't ask for this, you can safely ignore this email.</p>"
    )
    return send_email(
        email,
        "Reset your AANGA password",
        html,
        text=f"Reset your AANGA password (expires in 1 hour): {reset_link}",
    )


def send_order_confirmation(order):
    """Confirm a placed order. Safe to call for any order; no-ops if undeliverable."""
    user = getattr(order, "user", None)
    email = getattr(user, "email", None)
    if not _deliverable(email):
        return False

    rows = ""
    for item in order.items:
        variant = item.variant
        name = variant.product.name
        rows += (
            f'<tr><td style="padding:6px 0">{name} '
            f"({variant.size}/{variant.color_name}) &times; {item.quantity}</td>"
            f'<td style="padding:6px 0;text-align:right">'
            f"&#8377;{float(item.unit_price) * item.quantity:.2f}</td></tr>"
        )

    html = _wrap(
        f"<p>Thanks for your order, {user.full_name}! We&rsquo;ve received it and "
        "will let you know when it ships.</p>"
        f"<p><strong>Order {order.order_number}</strong></p>"
        f'<table style="width:100%;border-collapse:collapse;font-size:14px">{rows}'
        f'<tr><td style="padding-top:10px;font-weight:600">Total</td>'
        f'<td style="padding-top:10px;text-align:right;font-weight:600">'
        f"&#8377;{float(order.total_amount):.2f}</td></tr></table>"
    )
    return send_email(
        email,
        f"Your AANGA order {order.order_number} is confirmed",
        html,
        text=f"Order {order.order_number} confirmed. Total: Rs.{float(order.total_amount):.2f}",
    )
