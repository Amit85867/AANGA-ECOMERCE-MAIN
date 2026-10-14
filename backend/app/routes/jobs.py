"""Scheduled jobs, triggered over HTTP.

Render's free plan has no cron, so GitHub Actions calls these on a schedule
(.github/workflows/scheduled-jobs.yml). The work itself is the same code the
`flask reconcile-payments` CLI command runs.

Authentication is a single shared secret in `JOBS_TOKEN`, compared in constant
time. It is deliberately not a JWT and not an admin session: this is called by
a machine with no browser, and a long random string in one environment
variable on each side is the smallest thing that is actually safe.

With JOBS_TOKEN unset every route here answers 404, so an instance that was
never meant to run jobs does not advertise them.
"""
import hmac
import os
from functools import wraps

from flask import Blueprint, current_app, jsonify, request

from app.extensions import limiter

jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")


def _token():
    return os.environ.get("JOBS_TOKEN") or current_app.config.get("JOBS_TOKEN") or ""


def jobs_token_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        expected = _token()
        if not expected:
            # Not configured: behave as if the route does not exist rather
            # than inviting attempts at a secret that is not there.
            return jsonify(error="Not found"), 404

        header = request.headers.get("Authorization", "")
        presented = header[7:] if header.lower().startswith("bearer ") else ""
        # compare_digest, not ==, so a wrong token cannot be found a character
        # at a time by timing the response.
        if not presented or not hmac.compare_digest(presented, expected):
            current_app.logger.warning(
                "JOBS_AUTH_FAILED path=%s ip=%s", request.path, request.remote_addr
            )
            return jsonify(error="Unauthorized"), 401
        return view(*args, **kwargs)

    return wrapper


@jobs_bp.route("/reconcile-payments", methods=["POST"])
@limiter.limit("10 per hour")
@jobs_token_required
def reconcile_payments():
    """Refund captured payments that never became an order.

    Safety net for a webhook that was never delivered. Idempotent: a refunded
    payment stops reporting as captured, and each refund call carries an
    idempotency key, so running it twice costs nothing.
    """
    from app.routes.payments import reconcile_orphaned_captures

    payload = request.get_json(silent=True) or {}
    try:
        hours = int(payload.get("hours", 24))
    except (TypeError, ValueError):
        return jsonify(error="hours must be a number"), 400
    hours = max(1, min(hours, 24 * 7))

    result = reconcile_orphaned_captures(window_seconds=hours * 3600, dry_run=False)

    if not result.get("configured"):
        # Not an error: before Razorpay is switched on there is nothing to do,
        # and the schedule should not start failing because of it.
        return jsonify(status="skipped", reason="Razorpay is not configured"), 200
    if result.get("error"):
        current_app.logger.error("RECONCILE_FAILED err=%s", result["error"])
        return jsonify(status="error", error=result["error"]), 502

    orphans = result.get("orphans", [])
    if orphans:
        current_app.logger.warning(
            "RECONCILE_REFUNDED count=%s of=%s", result.get("refunded"), len(orphans)
        )
    return jsonify(
        status="ok",
        checked=result.get("checked", 0),
        orphans=len(orphans),
        refunded=result.get("refunded", 0),
        hours=hours,
    ), 200
