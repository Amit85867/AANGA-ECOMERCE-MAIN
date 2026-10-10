"""Maintenance mode: close the storefront, keep the admin panel open.

The switch is two rows in site_settings, so it survives restarts and is shared
by every worker and instance. Because the storefront already loads
/api/cms/settings on start-up, the same rows tell the browser to show the
maintenance page.

While it is on, customer-facing API calls answer 503. What stays open:

* /api/admin/*            — admins must be able to sign in and switch it off
* /api/payments/webhook   — Razorpay must still be able to report a payment
                            that was captured just before the switch
* /api/cms/*              — the maintenance page reads its message from here
* /api/health, sitemap, robots, static files
"""
import time

from flask import jsonify, request

from app.extensions import db
from app.models.cms import SiteSetting

FLAG_KEY = "maintenance_mode"
MESSAGE_KEY = "maintenance_message"
DEFAULT_MESSAGE = (
    "We are making a few improvements and will be back shortly. "
    "Thank you for your patience."
)

_OPEN_PREFIXES = ("/api/admin/", "/api/cms/", "/api/health", "/api/payments/webhook")

# Reading the flag costs a query, and it is checked on every storefront request.
# Each process remembers it briefly; turning the mode on or off therefore takes
# up to this long to reach other workers (the worker that handled the toggle
# updates at once).
_CACHE_SECONDS = 5
_cache = {"at": 0.0, "state": None}


def _truthy(value):
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")


def get_state(fresh=False):
    """{"enabled": bool, "message": str}."""
    now = time.monotonic()
    if not fresh and _cache["state"] is not None and now - _cache["at"] < _CACHE_SECONDS:
        return _cache["state"]

    rows = {
        s.key: s.value
        for s in SiteSetting.query.filter(SiteSetting.key.in_([FLAG_KEY, MESSAGE_KEY]))
    }
    state = {
        "enabled": _truthy(rows.get(FLAG_KEY)),
        "message": (rows.get(MESSAGE_KEY) or "").strip() or DEFAULT_MESSAGE,
    }
    _cache.update(at=now, state=state)
    return state


def set_state(enabled, message=None):
    values = {FLAG_KEY: "true" if enabled else "false"}
    if message is not None:
        values[MESSAGE_KEY] = message.strip()

    for key, value in values.items():
        row = SiteSetting.query.filter_by(key=key).first()
        if row:
            row.value = value
        else:
            db.session.add(SiteSetting(
                key=key, value=value, group_name="system",
                label="Maintenance mode" if key == FLAG_KEY else "Maintenance message",
            ))
    db.session.commit()
    return get_state(fresh=True)


def reset_cache():
    _cache.update(at=0.0, state=None)


def init_app(app):
    @app.before_request
    def _closed_for_maintenance():
        path = request.path
        if not path.startswith("/api/") or path.startswith(_OPEN_PREFIXES):
            return None
        if request.method == "OPTIONS":
            return None   # CORS preflight must pass or the browser hides the 503

        state = get_state()
        if not state["enabled"]:
            return None

        resp = jsonify(error=state["message"], maintenance=True)
        resp.status_code = 503
        resp.headers["Retry-After"] = "600"
        return resp
