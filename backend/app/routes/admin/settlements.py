"""Admin: read-only Razorpay settlements (payouts to the company bank account).

A *settlement* is money Razorpay has transferred to the bank account registered
on the Razorpay account during KYC. This endpoint only ever *reads* settlements
so an admin can see payouts without leaving the app.

The destination bank account itself is managed in the Razorpay Dashboard and is
never stored here: Razorpay settles to the KYC-verified account regardless of
anything in our database, so keeping full bank details app-side would add risk
without changing where the money lands.
"""
import os

import requests
from flask import jsonify, request

from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required

RAZORPAY_API = "https://api.razorpay.com/v1"


def _keys():
    return os.environ.get("RAZORPAY_KEY_ID"), os.environ.get("RAZORPAY_KEY_SECRET")


@admin_bp.route("/settlements", methods=["GET"])
@admin_required
def list_settlements():
    """Recent Razorpay settlements. Returns ``configured=False`` (not an error)
    when online payments are not set up, so the admin UI can show guidance."""
    key_id, key_secret = _keys()
    if not key_id or not key_secret:
        return jsonify(configured=False, settlements=[]), 200

    try:
        count = min(max(int(request.args.get("count", 20)), 1), 100)
    except (TypeError, ValueError):
        count = 20

    try:
        resp = requests.get(
            f"{RAZORPAY_API}/settlements",
            auth=(key_id, key_secret),
            params={"count": count},
            timeout=15,
        )
    except requests.RequestException:
        return jsonify(error="Could not reach the payment gateway"), 502

    if resp.status_code != 200:
        return jsonify(error="Could not fetch settlements from Razorpay"), 502

    data = resp.json()
    settlements = [
        {
            "id": s.get("id"),
            "amount": (s.get("amount") or 0) / 100.0,   # paise → rupees
            "fees": (s.get("fees") or 0) / 100.0,
            "tax": (s.get("tax") or 0) / 100.0,
            "status": s.get("status"),
            "utr": s.get("utr"),
            "created_at": s.get("created_at"),          # unix seconds
        }
        for s in data.get("items", [])
    ]
    return jsonify(configured=True, settlements=settlements), 200
