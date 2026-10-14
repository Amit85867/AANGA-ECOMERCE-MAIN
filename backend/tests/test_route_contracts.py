"""Contract checks applied to every route, driven by Flask's url_map.

Because the route list is read from the app rather than written out here, a
new endpoint is covered the moment it is registered — in particular an admin
route that forgets @admin_required fails these tests instead of shipping.

Each test walks all matching routes and reports every offender at once.
"""
import inspect
import uuid

import pytest
import requests
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.admin import Admin
from tests.factories import make_user

WRITE_METHODS = {"POST", "PUT", "PATCH"}

# Routes whose authentication is not a bearer token, checked by their own tests.
#   admin refresh/logout  — httpOnly refresh cookie (test_admin_auth_security)
#   payments webhook      — HMAC signature over the body (test_payment_webhook)
_NOT_BEARER_AUTH = {
    "/api/admin/auth/login",
    "/api/admin/auth/refresh",
    "/api/admin/auth/logout",
}


@pytest.fixture(autouse=True)
def _integrations_configured_but_offline(monkeypatch):
    """Give the payment routes credentials so they reach their own validation
    (unconfigured they stop at a 503, which test_payments covers), and make
    sure nothing here can reach a real gateway."""
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_contract")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "contract-secret")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "contract-webhook-secret")

    def _offline(*args, **kwargs):
        raise requests.ConnectionError("network disabled in contract tests")

    monkeypatch.setattr(requests.sessions.Session, "request", _offline)


def _routes(app):
    """Yield (method, rule, view) for every application route."""
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        view = inspect.unwrap(app.view_functions[rule.endpoint])
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            yield method, rule, view


def _decorators(view):
    return inspect.getsource(view).split("def ", 1)[0]


def _is_admin(rule):
    return rule.rule.startswith("/api/admin/") and rule.rule not in _NOT_BEARER_AUTH


def _is_customer(view):
    head = _decorators(view)
    return (
        "@jwt_required" in head
        and "optional=True" not in head
        and "refresh=True" not in head
    )


def _url(rule, missing=True):
    """Fill path parameters with ids that match nothing."""
    values = {}
    for arg in rule.arguments:
        converter = rule._converters[arg].__class__.__name__
        if converter == "IntegerConverter":
            values[arg] = 999999
        elif arg in ("user_id", "admin_id"):
            values[arg] = str(uuid.uuid4())
        else:
            values[arg] = "does-not-exist"
    return rule.build(values, append_unknown=False)[1]


def _call(client, method, url, **kw):
    """Status code of a request; an unhandled exception counts as a 500."""
    try:
        return client.open(url, method=method, **kw).status_code
    except Exception as exc:  # noqa: BLE001 - the point is to catch anything
        return f"500 ({type(exc).__name__}: {exc})"[:160]


def _report(offenders):
    """One offender per line, so pytest shows the whole list untruncated."""
    return "\n" + "\n".join(offenders)


def _customer_headers():
    user = make_user()
    return {"Authorization": f"Bearer {create_access_token(identity=str(user.id))}"}


def _admin_headers(role="master"):
    admin = Admin(
        email=f"{role}-{uuid.uuid4().hex[:6]}@example.com",
        password_hash=generate_password_hash("AdminPass123!"),
        full_name="Contract Admin",
        role=role,
    )
    db.session.add(admin)
    db.session.commit()
    token = create_access_token(
        identity=str(admin.id),
        additional_claims={"actor": "admin", "role": role},
    )
    return {"Authorization": f"Bearer {token}"}


def test_every_admin_route_declares_an_admin_decorator(app):
    """The path prefix is not the protection — the decorator is."""
    unprotected = [
        f"{method} {rule.rule}"
        for method, rule, view in _routes(app)
        if _is_admin(rule)
        and "@admin_required" not in _decorators(view)
        and "@master_required" not in _decorators(view)
    ]
    assert not unprotected, _report(unprotected)


def test_admin_routes_reject_anonymous_callers(app, client):
    bad = []
    for method, rule, _ in _routes(app):
        if not _is_admin(rule):
            continue
        status = _call(client, method, _url(rule), json={})
        if status != 401:
            bad.append(f"{method} {rule.rule} -> {status}")
    assert not bad, _report(bad)


def test_admin_routes_reject_customer_tokens(app, client):
    headers = _customer_headers()
    bad = []
    for method, rule, _ in _routes(app):
        if not _is_admin(rule):
            continue
        status = _call(client, method, _url(rule), json={}, headers=headers)
        if status != 403:
            bad.append(f"{method} {rule.rule} -> {status}")
    assert not bad, _report(bad)


def test_master_routes_reject_ordinary_admins(app, client):
    headers = _admin_headers(role="staff")
    bad = []
    for method, rule, view in _routes(app):
        if "@master_required" not in _decorators(view):
            continue
        status = _call(client, method, _url(rule), json={}, headers=headers)
        if status != 403:
            bad.append(f"{method} {rule.rule} -> {status}")
    assert not bad, _report(bad)


def test_customer_routes_reject_anonymous_callers(app, client):
    bad = []
    for method, rule, view in _routes(app):
        if not _is_customer(view):
            continue
        status = _call(client, method, _url(rule), json={})
        if status != 401:
            bad.append(f"{method} {rule.rule} -> {status}")
    assert not bad, _report(bad)


def test_customer_routes_reject_admin_tokens(app, client):
    """An admin token is not a customer identity and must not act as one."""
    headers = _admin_headers()
    bad = []
    for method, rule, view in _routes(app):
        if not _is_customer(view):
            continue
        status = _call(client, method, _url(rule), json={}, headers=headers)
        if status not in (401, 403):
            bad.append(f"{method} {rule.rule} -> {status}")
    assert not bad, _report(bad)


def test_unknown_ids_are_not_found(app, client):
    """A well-authenticated request for a missing record is a 404 (or is
    refused by validation first) — never a 2xx and never a 500."""
    customer, admin = _customer_headers(), _admin_headers()
    bad = []
    for method, rule, view in _routes(app):
        if not rule.arguments:
            continue
        headers = admin if _is_admin(rule) else customer
        status = _call(client, method, _url(rule), json={}, headers=headers)
        allowed = (404, 400, 422) if method in WRITE_METHODS else (404,)
        if status not in allowed:
            bad.append(f"{method} {rule.rule} -> {status}")
    assert not bad, _report(bad)


def test_write_routes_survive_empty_and_malformed_bodies(app, client):
    """Bad input is the client's error: a 4xx, not an unhandled exception."""
    customer, admin = _customer_headers(), _admin_headers()
    bad = []
    for method, rule, view in _routes(app):
        if method not in WRITE_METHODS:
            continue
        headers = admin if _is_admin(rule) else customer
        url = _url(rule)
        for label, kw in (
            ("empty", {"json": {}}),
            ("not-json", {"data": "not json", "content_type": "application/json"}),
            ("json-list", {"json": []}),
            ("no-body", {}),
        ):
            status = _call(client, method, url, headers=headers, **kw)
            if not isinstance(status, int) or status >= 500:
                bad.append(f"{method} {rule.rule} [{label}] -> {status}")
    assert not bad, _report(bad)
