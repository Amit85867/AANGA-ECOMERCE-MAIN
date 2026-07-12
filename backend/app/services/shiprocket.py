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
    resp = requests.request(method, url, headers=_headers(), **kwargs)
    # Token may have expired early — retry once with a fresh token.
    if resp.status_code in (401, 403):
        _get_token(force=True)
        resp = requests.request(method, url, headers=_headers(), **kwargs)
    return resp


def create_order(order):
    """Create an adhoc Shiprocket order from an AANGA Order.

    Returns {"sr_order_id", "shipment_id", "status"}.
    """
    addr = order.address
    name_parts = (addr.full_name or "Customer").split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else "."

    email = order.user.email if order.user else os.environ.get("ADMIN_EMAIL", "orders@aanga.in")

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
