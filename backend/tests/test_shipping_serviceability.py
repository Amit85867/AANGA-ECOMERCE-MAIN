"""Public pincode serviceability check.

This endpoint is unauthenticated and proxies a paid upstream API, so input
validation and rate limiting matter more than usual. It must also degrade
quietly: an unconfigured or unreachable Shiprocket cannot be allowed to break
the product page.
"""
from unittest.mock import patch

import pytest

from app.services.shiprocket import ShiprocketError

SERVICEABLE = {
    "serviceable": True,
    "couriers": [
        {"name": "Delhivery", "rate": 42.0, "estimated_days": "3", "cod_available": True},
        {"name": "Bluedart", "rate": 66.0, "estimated_days": "2", "cod_available": False},
    ],
    "estimated_days": 2,
    "cheapest_rate": 42.0,
}


@pytest.fixture(autouse=True)
def _no_rate_limit(app):
    """These tests hammer one endpoint; the limiter is exercised separately."""
    app.config["RATELIMIT_ENABLED"] = False
    yield
    app.config["RATELIMIT_ENABLED"] = True


def test_serviceable_pincode_returns_eta_and_rate(app, client):
    with patch("app.services.shiprocket.check_serviceability", return_value=SERVICEABLE):
        resp = client.get("/api/shipping/serviceability?pincode=700001")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["serviceable"] is True
    assert body["estimated_days"] == 2
    assert body["cheapest_rate"] == 42.0
    assert body["cod_available"] is True
    assert len(body["couriers"]) == 2


def test_unserviceable_pincode_is_reported_not_errored(app, client):
    empty = {"serviceable": False, "couriers": [], "estimated_days": None, "cheapest_rate": None}
    with patch("app.services.shiprocket.check_serviceability", return_value=empty):
        resp = client.get("/api/shipping/serviceability?pincode=999999")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["serviceable"] is False
    assert body["cod_available"] is False


@pytest.mark.parametrize("pincode", ["", "12345", "1234567", "abcdef", "012345", "70 0001"])
def test_invalid_pincodes_are_rejected(app, client, pincode):
    with patch("app.services.shiprocket.check_serviceability") as check:
        resp = client.get(f"/api/shipping/serviceability?pincode={pincode}")

    assert resp.status_code == 422
    check.assert_not_called()  # never spend an upstream call on bad input


def test_missing_pincode_is_rejected(app, client):
    assert client.get("/api/shipping/serviceability").status_code == 422


def test_unconfigured_shiprocket_degrades_quietly(app, client):
    """A missing pickup pincode must not 500 the product page."""
    with patch(
        "app.services.shiprocket.check_serviceability",
        side_effect=ShiprocketError("Delivery checks are not configured."),
    ):
        resp = client.get("/api/shipping/serviceability?pincode=700001")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["available"] is False
    assert body["configured"] is False


def test_upstream_outage_degrades_quietly(app, client):
    with patch(
        "app.services.shiprocket.check_serviceability",
        side_effect=ShiprocketError("Could not reach Shiprocket."),
    ):
        resp = client.get("/api/shipping/serviceability?pincode=700001")

    assert resp.status_code == 200
    assert resp.get_json()["available"] is False


def test_cod_flag_is_passed_through(app, client):
    with patch("app.services.shiprocket.check_serviceability", return_value=SERVICEABLE) as check:
        client.get("/api/shipping/serviceability?pincode=700001&cod=true")

    assert check.call_args.kwargs["cod"] is True


def test_absurd_weight_is_clamped(app, client):
    with patch("app.services.shiprocket.check_serviceability", return_value=SERVICEABLE) as check:
        client.get("/api/shipping/serviceability?pincode=700001&weight=99999")

    assert check.call_args.kwargs["weight"] == 50


def test_garbage_weight_falls_back_to_default(app, client):
    with patch("app.services.shiprocket.check_serviceability", return_value=SERVICEABLE) as check:
        client.get("/api/shipping/serviceability?pincode=700001&weight=heavy")

    assert check.call_args.kwargs["weight"] == 0.5


def test_endpoint_needs_no_authentication(app, client):
    """A shopper must be able to check delivery before signing up."""
    with patch("app.services.shiprocket.check_serviceability", return_value=SERVICEABLE):
        resp = client.get("/api/shipping/serviceability?pincode=700001")
    assert resp.status_code == 200
