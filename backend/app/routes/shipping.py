"""Public delivery checks: is a pincode serviceable, and how soon.

Backed by Shiprocket's courier serviceability API. Unauthenticated so a shopper
can check before creating an account, and therefore rate limited — every call
costs an upstream request.

Never fails the page: when Shiprocket is unconfigured or unreachable the
response says so with ``configured``/``available`` flags rather than an error
status, so the storefront can quietly hide the widget.
"""
import re

from flask import Blueprint, request, jsonify, current_app

from app.extensions import limiter
from app.services import cache, shiprocket
from app.services.shiprocket import ShiprocketError

shipping_bp = Blueprint("shipping", __name__, url_prefix="/api/shipping")

# Indian PIN codes: six digits, never starting with 0.
_PIN_RE = re.compile(r"^[1-9]\d{5}$")


@shipping_bp.route("/serviceability", methods=["GET"])
@limiter.limit("30 per minute; 300 per hour")
def serviceability():
    pincode = (request.args.get("pincode") or "").strip()
    if not _PIN_RE.match(pincode):
        return jsonify(error="Enter a valid 6-digit PIN code"), 422

    cod = request.args.get("cod", "").lower() in ("1", "true", "yes")

    try:
        weight = float(request.args.get("weight", 0.5))
    except (TypeError, ValueError):
        weight = 0.5
    weight = min(max(weight, 0.1), 50)

    try:
        # A PIN code's couriers do not change minute to minute, and every lookup
        # is a paid-for upstream call: remember each answer for ten minutes.
        # A failure raises through and is not remembered.
        result = cache.get_or_set(
            f"serviceability:{pincode}:{int(cod)}:{weight}", 600,
            lambda: shiprocket.check_serviceability(pincode, cod=cod, weight=weight),
        )
    except ShiprocketError as err:
        # Configuration or upstream problem — not the shopper's fault, and not
        # a reason to break the product page.
        current_app.logger.warning("SERVICEABILITY_UNAVAILABLE pincode=%s err=%s", pincode, err)
        return jsonify(
            pincode=pincode, available=False, configured=False, message=str(err),
        ), 200

    return jsonify(
        pincode=pincode,
        available=True,
        configured=True,
        serviceable=result["serviceable"],
        estimated_days=result["estimated_days"],
        cheapest_rate=result["cheapest_rate"],
        couriers=result["couriers"],
        cod_available=any(c["cod_available"] for c in result["couriers"]),
    ), 200
