"""Round 4 pre-launch audit: checks that did not belong to an existing file.

* the integration check and the verify script never print a secret, and say
  the right thing with no keys, test keys, live keys and half-set keys;
* every list in the dashboard answers on a database with nothing in it;
* log lines carry no personal data.
"""
import logging
import re

import pytest

from app.services import integrations_check, integrations_verify
from tests.helpers import admin_headers

SECRETS = {
    "RAZORPAY_KEY_SECRET": "s3cr3t-razorpay-value-do-not-print",
    "RAZORPAY_WEBHOOK_SECRET": "whsec-value-do-not-print",
    "SHIPROCKET_PASSWORD": "shiprocket-pass-do-not-print",
    "S3_SECRET_ACCESS_KEY": "s3-secret-access-key-do-not-print",
    "RESEND_API_KEY": "re_do_not_print_this_value",
}
ALL_KEYS = ["RAZORPAY_KEY_ID", "SHIPROCKET_EMAIL", "SHIPROCKET_PICKUP_PINCODE",
            "S3_ENDPOINT_URL", "S3_BUCKET", "S3_ACCESS_KEY_ID", *SECRETS]


@pytest.fixture
def no_keys(monkeypatch):
    for name in ALL_KEYS:
        monkeypatch.delenv(name, raising=False)


def _report(probe=False):
    lines, code = integrations_check.run(probe=probe)
    return "\n".join(lines), code


def test_check_integrations_with_no_keys_says_not_configured_and_passes(app, no_keys):
    text, code = _report()
    assert code == 0
    assert text.count("NOT CONFIGURED") >= 2            # Razorpay and Shiprocket at least
    assert "PROBLEM" not in text


def test_check_integrations_never_prints_a_value(app, no_keys, monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_abcdefghijklmn")
    monkeypatch.setenv("SHIPROCKET_EMAIL", "api-user@example.com")
    monkeypatch.setenv("SHIPROCKET_PICKUP_PINCODE", "800001")
    for name, value in SECRETS.items():
        monkeypatch.setenv(name, value)
    text, _code = _report()
    for value in SECRETS.values():
        assert value not in text
    assert "rzp_test_abcdefghijklmn" not in text         # not even the public key id
    assert "TEST" in text                                # but it does say which mode


def test_check_integrations_names_live_mode(app, no_keys, monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_live_abcdefghijklmn")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", SECRETS["RAZORPAY_KEY_SECRET"])
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", SECRETS["RAZORPAY_WEBHOOK_SECRET"])
    text, _code = _report()
    assert "LIVE" in text


@pytest.mark.parametrize("env", [
    {"RAZORPAY_KEY_ID": "rzp_test_abcdefghijklmn"},                       # id without its secret
    {"SHIPROCKET_EMAIL": "api-user@example.com"},                         # email without its password
])
def test_check_integrations_reports_half_set_keys_as_a_problem(app, no_keys, monkeypatch, env):
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    text, code = _report()
    assert code == 1
    assert "PROBLEM" in text


def test_verify_integrations_refuses_without_keys_and_with_live_keys(app, no_keys, monkeypatch):
    lines, code = integrations_verify.run(app)
    assert code == 2 and "not set" in lines[0]

    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_live_abcdefghijklmn")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", SECRETS["RAZORPAY_KEY_SECRET"])
    lines, code = integrations_verify.run(app)
    assert code == 2 and "not a test key" in lines[0]
    assert SECRETS["RAZORPAY_KEY_SECRET"] not in "\n".join(lines)


def test_verify_integrations_reports_each_step_and_prints_no_secret(app, no_keys, monkeypatch):
    """With test keys but no network and no paid order: six lines, none a crash."""
    import requests

    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_abcdefghijklmn")
    for name, value in SECRETS.items():
        monkeypatch.setenv(name, value)

    def offline(*_args, **_kwargs):
        raise requests.ConnectionError("no network in tests")
    for verb in ("get", "post", "request"):
        monkeypatch.setattr(requests, verb, offline)

    lines, code = integrations_verify.run(app)
    text = "\n".join(lines)
    assert code == 1
    assert len([line for line in lines if re.match(r"^(PASS|FAIL|SKIP)", line)]) == 6
    assert re.search(r"^PASS\s+4\. Signed webhook", text, re.M)           # needs no network
    assert re.search(r"^FAIL\s+1\. Test checkout", text, re.M)
    assert "unexpected error" not in text
    for value in SECRETS.values():
        assert value not in text


# ── Every dashboard list on an empty database ─────────────────

def test_every_list_answers_when_it_is_empty(app, client):
    """A new store has no orders, customers, coupons... Every screen's first
    request must answer, not fall over on an empty table."""
    headers = admin_headers()
    checked = 0
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api/admin/") or "GET" not in rule.methods or rule.arguments:
            continue
        if rule.rule.endswith(("/export", "/export.csv")):
            continue
        resp = client.get(rule.rule, headers=headers)
        assert resp.status_code == 200, f"{rule.rule} answered {resp.status_code} on an empty database"
        checked += 1
    assert checked > 30


def test_the_storefront_answers_on_an_empty_database(client):
    for url in ("/api/products", "/api/categories", "/api/content/layout", "/api/cms/settings", "/api/content/faq",
                "/api/cms/features-available", "/api/health", "/sitemap.xml", "/robots.txt"):
        assert client.get(url).status_code == 200, url


# ── Logs ──────────────────────────────────────────────────────

def test_placing_an_order_and_resetting_a_password_log_no_personal_data(app, client, caplog, monkeypatch):
    from app.extensions import db
    from app.models.user import User
    from tests.factories import make_address, make_cart, make_product, make_user
    from tests.helpers import customer_headers
    from werkzeug.security import generate_password_hash

    user = make_user(email="private.person@example.com")
    user.full_name, user.phone = "Private Person", "+919812345678"
    user.password_hash = generate_password_hash("OldPassword1!")
    db.session.commit()
    address = make_address(user)
    _, variant = make_product(price=500, stock=5)
    make_cart(user, [(variant, 1)])
    app.config["RATELIMIT_ENABLED"] = False
    try:
        with caplog.at_level(logging.DEBUG):
            placed = client.post("/api/orders", headers=customer_headers(user), json={"address_id": address.id, "payment_method": "cod"})
            assert placed.status_code in (200, 201)
            assert client.post("/api/auth/login", json={"email": "private.person@example.com", "password": "wrong-guess"}).status_code == 401
            assert client.post("/api/auth/forgot-password", json={"email": "private.person@example.com"}).status_code == 200
    finally:
        app.config["RATELIMIT_ENABLED"] = True

    text = "\n".join(record.getMessage() for record in caplog.records if record.name.startswith(("app", "aanga", "flask")))
    assert "private.person@example.com" not in text
    assert "+919812345678" not in text and "9812345678" not in text
    assert "OldPassword1!" not in text and "wrong-guess" not in text
    assert "reset-password?token=" not in text
    assert db.session.get(User, user.id) is not None
