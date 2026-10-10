"""Checks behind the admin System Health panel.

Each check reports one of three states and a short human-readable detail:

    ok              configured (and reachable, where that is tested)
    not_configured  the integration is switched off — a valid way to run
    error           configured but broken, or only half configured

A check never returns a configured *value* — no key, URL, email or password —
only whether one is present. The Razorpay check does report "test" or "live",
which it reads from the key's public prefix.

The database and rate-limit store are always pinged. External services are
contacted only when ``probe=True`` (the panel's "Test connections" button), so
simply opening the page costs no third-party calls.
"""
import os
import time

import requests
from flask import current_app
from sqlalchemy import text

from app.extensions import db, limiter

OK, NOT_CONFIGURED, ERROR = "ok", "not_configured", "error"
PROBE_TIMEOUT = 6


def _has(name, config=False):
    value = current_app.config.get(name) if config else os.environ.get(name)
    return bool(str(value or "").strip())


def _result(status, detail, **extra):
    return {"status": status, "detail": detail, **extra}


def check_database():
    started = time.perf_counter()
    try:
        db.session.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db.session.rollback()
        current_app.logger.exception("HEALTH_DB_FAILED")
        return _result(ERROR, "The database did not answer.")
    latency = round((time.perf_counter() - started) * 1000, 1)
    return _result(OK, "Connected.", latency_ms=latency)


def check_rate_limit_store():
    uri = str(current_app.config.get("RATELIMIT_STORAGE_URI") or "")
    if uri.startswith("memory://") or not uri:
        return _result(
            NOT_CONFIGURED,
            "Using in-process memory. Limits are per worker; set a Redis URL "
            "before running more than one worker or instance.",
        )
    try:
        healthy = limiter.storage.check()
    except Exception:  # noqa: BLE001
        healthy = False
    if not healthy:
        return _result(ERROR, "Redis is configured but did not answer.")
    return _result(OK, "Redis connected.")


def check_razorpay(probe=False):
    key, secret = _has("RAZORPAY_KEY_ID"), _has("RAZORPAY_KEY_SECRET")
    if not key and not secret:
        return _result(NOT_CONFIGURED, "Online payments are off; the store is COD-only.")
    if not (key and secret):
        return _result(ERROR, "Key ID and key secret must both be set.")

    mode = "test" if os.environ["RAZORPAY_KEY_ID"].startswith("rzp_test_") else "live"
    if not _has("RAZORPAY_WEBHOOK_SECRET"):
        return _result(
            ERROR, "Webhook secret is missing, so abandoned checkouts are not refunded.",
            mode=mode,
        )
    if not probe:
        return _result(OK, f"Configured ({mode} mode).", mode=mode)

    try:
        resp = requests.get(
            "https://api.razorpay.com/v1/payments",
            auth=(os.environ["RAZORPAY_KEY_ID"], os.environ["RAZORPAY_KEY_SECRET"]),
            params={"count": 1}, timeout=PROBE_TIMEOUT,
        )
    except requests.RequestException:
        return _result(ERROR, "Could not reach Razorpay.", mode=mode)
    if resp.status_code == 401:
        return _result(ERROR, "Razorpay rejected the credentials.", mode=mode)
    if resp.status_code != 200:
        return _result(ERROR, f"Razorpay answered {resp.status_code}.", mode=mode)
    return _result(OK, f"Connected ({mode} mode).", mode=mode)


def check_shiprocket(probe=False):
    email, password = _has("SHIPROCKET_EMAIL"), _has("SHIPROCKET_PASSWORD")
    if not email and not password:
        return _result(NOT_CONFIGURED, "Courier booking and delivery checks are off.")
    if not (email and password):
        return _result(ERROR, "API email and password must both be set.")
    if not _has("SHIPROCKET_PICKUP_PINCODE"):
        return _result(ERROR, "Pickup PIN code is missing, so delivery checks cannot run.")
    if not probe:
        return _result(OK, "Configured.")

    from app.services import shiprocket
    try:
        shiprocket._get_token(force=True)
    except shiprocket.ShiprocketError as exc:
        return _result(ERROR, str(exc))
    return _result(OK, "Signed in to Shiprocket.")


def check_storage(probe=False):
    url, key = _has("SUPABASE_URL", config=True), _has("SUPABASE_SERVICE_KEY", config=True)
    if not url and not key:
        return _result(
            NOT_CONFIGURED,
            "Images are saved to local disk. That is lost on every deploy — "
            "configure Supabase Storage before going live.",
        )
    if not (url and key):
        return _result(ERROR, "Project URL and service key must both be set.")
    if not probe:
        return _result(OK, "Configured.")

    cfg = current_app.config
    bucket = cfg.get("SUPABASE_STORAGE_BUCKET", "product-images")
    try:
        resp = requests.get(
            f"{cfg['SUPABASE_URL'].rstrip('/')}/storage/v1/bucket/{bucket}",
            headers={"Authorization": f"Bearer {cfg['SUPABASE_SERVICE_KEY']}",
                     "apikey": cfg["SUPABASE_SERVICE_KEY"]},
            timeout=PROBE_TIMEOUT,
        )
    except requests.RequestException:
        return _result(ERROR, "Could not reach Supabase Storage.")
    if resp.status_code in (401, 403):
        return _result(ERROR, "Supabase rejected the service key.")
    if resp.status_code == 404:
        return _result(ERROR, f'Bucket "{bucket}" does not exist.')
    if resp.status_code != 200:
        return _result(ERROR, f"Supabase answered {resp.status_code}.")
    if not resp.json().get("public"):
        return _result(ERROR, f'Bucket "{bucket}" is private; product images will not load.')
    return _result(OK, f'Connected (bucket "{bucket}").')


def check_email():
    from app.services.email import is_email_configured
    if not is_email_configured():
        return _result(NOT_CONFIGURED, "Emails are written to the log, not sent.")
    if not current_app.config.get("EMAIL_ENABLED", True):
        return _result(ERROR, "Configured, but EMAIL_ENABLED is off.")
    return _result(OK, "Configured.")


def check_sentry():
    if not _has("SENTRY_DSN", config=True):
        return _result(NOT_CONFIGURED, "Errors are logged but not reported to Sentry.")
    return _result(OK, "Configured.")


def check_google_login():
    if not _has("GOOGLE_CLIENT_ID"):
        return _result(NOT_CONFIGURED, '"Continue with Google" is off.')
    return _result(OK, "Configured.")


def run_all(probe=False):
    """Ordered so the panel lists what the store cannot run without first."""
    return [
        {"key": "database", "label": "Database", **check_database()},
        {"key": "rate_limit_store", "label": "Redis (rate limits)", **check_rate_limit_store()},
        {"key": "storage", "label": "Supabase Storage (images)", **check_storage(probe)},
        {"key": "razorpay", "label": "Razorpay (payments)", **check_razorpay(probe)},
        {"key": "shiprocket", "label": "Shiprocket (delivery)", **check_shiprocket(probe)},
        {"key": "email", "label": "Resend (email)", **check_email()},
        {"key": "sentry", "label": "Sentry (error reports)", **check_sentry()},
        {"key": "google_login", "label": "Google sign-in", **check_google_login()},
    ]
