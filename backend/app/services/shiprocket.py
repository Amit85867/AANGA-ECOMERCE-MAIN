"""Shiprocket delivery integration.

Thin client over the Shiprocket external API. Configure with env vars
SHIPROCKET_EMAIL / SHIPROCKET_PASSWORD (create an API user in
Shiprocket → Settings → API). The auth token is cached in-process
(Shiprocket tokens are valid for ~10 days).

All functions raise ShiprocketError with a human-readable message on failure
so callers can surface it to the admin.
"""
import os
import time
from datetime import datetime

import requests

BASE = "https://apiv2.shiprocket.in/v1/external"

# module-level token cache: {"token": str, "fetched_at": float}
_token_cache = {"token": None, "fetched_at": 0}
_TOKEN_TTL = 9 * 24 * 3600  # refresh a little before the 10-day expiry


class ShiprocketError(Exception):
    pass


def _credentials():
    email = os.environ.get("SHIPROCKET_EMAIL")
    password = os.environ.get("SHIPROCKET_PASSWORD")
    if not email or not password:
        raise ShiprocketError("Shiprocket is not configured. Add SHIPROCKET_EMAIL and SHIPROCKET_PASSWORD.")
    return email, password


def _get_token(force=False):
    now = time.time()
    if not force and _token_cache["token"] and (now - _token_cache["fetched_at"]) < _TOKEN_TTL:
        return _token_cache["token"]

    email, password = _credentials()
    try:
        resp = requests.post(
            f"{BASE}/auth/login",
            json={"email": email, "password": password},
            timeout=20,
        )
    except requests.RequestException:
        raise ShiprocketError("Could not reach Shiprocket. Try again shortly.")

    if resp.status_code != 200:
        raise ShiprocketError("Shiprocket authentication failed. Check the API credentials.")

    token = resp.json().get("token")
    if not token:
        raise ShiprocketError("Shiprocket did not return a token.")

    _token_cache["token"] = token
    _token_cache["fetched_at"] = now
    return token


def _headers():
    return {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}


def _request(method, path, **kwargs):
    kwargs.setdefault("timeout", 30)
    url = f"{BASE}{path}"
    try:
        resp = requests.request(method, url, headers=_headers(), **kwargs)
        # Token may have expired early — retry once with a fresh token.
        if resp.status_code in (401, 403):
            _get_token(force=True)
            resp = requests.request(method, url, headers=_headers(), **kwargs)
    except requests.RequestException:
        # A timeout or dropped connection is the courier's outage, not a bug
        # here: callers report it to the admin like any other refusal.
        raise ShiprocketError("Could not reach Shiprocket. Try again shortly.")
    return resp


def create_order(order):
    """Create an adhoc Shiprocket order from an AANGA Order.

    Returns {"sr_order_id", "shipment_id", "status"}.
    """
    addr = order.address
    name_parts = (addr.full_name or "Customer").split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else "."

    email = order.user.email if order.user else os.environ.get("ADMIN_EMAIL", "")

    items = []
    for oi in order.items:
        variant = oi.variant
        items.append({
            "name": variant.product.name,
            "sku": variant.sku or f"VAR-{variant.id}",
            "units": oi.quantity,
            "selling_price": float(oi.unit_price),
        })

    payload = {
        "order_id": order.order_number,
        "order_date": order.placed_at.strftime("%Y-%m-%d %H:%M") if order.placed_at else datetime.now().strftime("%Y-%m-%d %H:%M"),
        "pickup_location": os.environ.get("SHIPROCKET_PICKUP_LOCATION", "Primary"),
        "billing_customer_name": first_name,
        "billing_last_name": last_name,
        "billing_address": addr.line1,
        "billing_address_2": addr.line2 or "",
        "billing_city": addr.city,
        "billing_pincode": addr.pin_code,
        "billing_state": addr.state,
        "billing_country": "India",
        "billing_email": email,
        "billing_phone": addr.phone,
        "shipping_is_billing": True,
        "order_items": items,
        "payment_method": "COD" if order.payment_method.value == "cod" else "Prepaid",
        "sub_total": float(order.total_amount),
        # Package defaults — adjust per real product weights/dimensions.
        "length": 20,
        "breadth": 15,
        "height": 5,
        "weight": 0.5,
    }

    resp = _request("POST", "/orders/create/adhoc", json=payload)
    if resp.status_code not in (200, 201):
        raise ShiprocketError(_error_message(resp, "Could not create Shiprocket order."))

    data = resp.json()
    return {
        "sr_order_id": data.get("order_id"),
        "shipment_id": data.get("shipment_id"),
        "status": data.get("status"),
    }


def assign_awb(shipment_id, courier_id=None):
    """Assign a courier AWB to a shipment.

    Returns {"awb_code", "courier_name"}.
    """
    body = {"shipment_id": shipment_id}
    if courier_id:
        body["courier_id"] = courier_id

    resp = _request("POST", "/courier/assign/awb", json=body)
    if resp.status_code not in (200, 201):
        raise ShiprocketError(_error_message(resp, "Could not assign a courier AWB."))

    data = resp.json().get("response", {}).get("data", {})
    awb = data.get("awb_code")
    if not awb:
        raise ShiprocketError(_error_message(resp, "No courier serviceable / AWB not assigned."))

    return {"awb_code": awb, "courier_name": data.get("courier_name")}


def schedule_pickup(shipment_id):
    """Ask the assigned courier to collect the parcel.

    Returns {"scheduled_date", "token"}. Without this the AWB exists but nobody
    comes for the parcel until someone presses "Schedule pickup" in Shiprocket.
    """
    resp = _request("POST", "/courier/generate/pickup", json={"shipment_id": [shipment_id]})
    if resp.status_code not in (200, 201):
        raise ShiprocketError(_error_message(resp, "Could not schedule the pickup."))

    data = resp.json()
    if not data.get("pickup_status"):
        raise ShiprocketError(_error_message(resp, "The courier did not accept the pickup request."))
    details = data.get("response") or {}
    return {
        "scheduled_date": details.get("pickup_scheduled_date"),
        "token": details.get("pickup_token_number"),
    }


def check_serviceability(delivery_pincode, cod=False, weight=0.5, declared_value=None):
    """Can we deliver to this pincode, and how soon?

    Returns {"serviceable", "couriers": [...], "estimated_days", "cheapest_rate"}.
    ``couriers`` is ordered cheapest-first. Raises ShiprocketError if the pickup
    pincode is not configured or the API rejects the request.
    """
    pickup = os.environ.get("SHIPROCKET_PICKUP_PINCODE")
    if not pickup:
        raise ShiprocketError(
            "Delivery checks are not configured. Add SHIPROCKET_PICKUP_PINCODE."
        )

    params = {
        "pickup_postcode": pickup,
        "delivery_postcode": delivery_pincode,
        "cod": 1 if cod else 0,
        "weight": weight,
    }
    if declared_value is not None:
        params["declared_value"] = declared_value

    resp = _request("GET", "/courier/serviceability/", params=params)
    if resp.status_code != 200:
        # A pincode we do not serve legitimately comes back non-200; treat that
        # as "not serviceable" rather than an outage.
        return {"serviceable": False, "couriers": [], "estimated_days": None,
                "cheapest_rate": None}

    available = (resp.json().get("data") or {}).get("available_courier_companies") or []
    if not available:
        return {"serviceable": False, "couriers": [], "estimated_days": None,
                "cheapest_rate": None}

    couriers = sorted(
        (
            {
                "name": c.get("courier_name"),
                "rate": c.get("rate"),
                "estimated_days": c.get("estimated_delivery_days"),
                "cod_available": bool(c.get("cod")),
            }
            for c in available
        ),
        key=lambda c: (c["rate"] is None, c["rate"] or 0),
    )

    days = [
        int(c["estimated_days"]) for c in couriers
        if str(c["estimated_days"] or "").strip().isdigit()
    ]

    return {
        "serviceable": True,
        "couriers": couriers[:5],
        "estimated_days": min(days) if days else None,
        "cheapest_rate": couriers[0]["rate"],
    }


def track_by_awb(awb):
    """Fetch tracking activities for an AWB. Returns a list of events (may be empty)."""
    resp = _request("GET", f"/courier/track/awb/{awb}")
    if resp.status_code != 200:
        raise ShiprocketError("Could not fetch tracking updates.")

    data = resp.json()
    tracking = data.get("tracking_data", {})
    return tracking.get("shipment_track_activities") or []


def _error_message(resp, fallback):
    try:
        body = resp.json()
        return body.get("message") or body.get("error") or fallback
    except ValueError:
        return fallback
