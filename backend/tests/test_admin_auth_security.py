"""Admin session security: cookie-based refresh, CSRF, and claim separation."""
import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.admin import Admin
from app.routes.admin.auth import (
    ADMIN_REFRESH_COOKIE,
    ADMIN_CSRF_COOKIE,
    ADMIN_COOKIE_PATH,
)

PASSWORD = "AdminPass123!"


def _make_admin(email="admin@example.com", role="master"):
    admin = Admin(
        email=email,
        password_hash=generate_password_hash(PASSWORD),
        full_name="Test Admin",
        role=role,
    )
    db.session.add(admin)
    db.session.commit()
    return admin


def _login(client, email="admin@example.com"):
    return client.post(
        "/api/admin/auth/login", json={"email": email, "password": PASSWORD}
    )


def _cookie_header(resp, name):
    for c in resp.headers.getlist("Set-Cookie"):
        if c.startswith(f"{name}="):
            return c
    return None


# ── Token storage ─────────────────────────────────────────────────────────
def test_admin_login_keeps_refresh_token_out_of_the_body(app, client):
    _make_admin()

    resp = _login(client)

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["access_token"]
    assert "refresh_token" not in body


def test_admin_login_sets_httponly_scoped_cookie(app, client):
    _make_admin()

    resp = _login(client)

    cookie = _cookie_header(resp, ADMIN_REFRESH_COOKIE)
    assert cookie is not None
    assert "HttpOnly" in cookie
    # Scoped to the admin auth routes so it never rides along with storefront
    # requests (and never collides with the customer refresh cookie).
    assert "Path=/api/admin/auth" in cookie

    csrf_cookie = _cookie_header(resp, ADMIN_CSRF_COOKIE)
    assert csrf_cookie is not None
    assert "HttpOnly" not in csrf_cookie  # must be readable for double-submit


def test_admin_and_customer_cookies_are_independent(app, client):
    """Signing into the admin panel must not clobber a customer session."""
    _make_admin()
    resp = _login(client)

    names = [c.split("=")[0] for c in resp.headers.getlist("Set-Cookie")]
    assert "aanga_refresh" not in names  # the customer cookie is untouched
    assert ADMIN_REFRESH_COOKIE in names


# ── Claim separation (regression) ─────────────────────────────────────────
def test_admin_refresh_token_cannot_be_used_as_an_access_token(app, client):
    """Regression: additional_claims used to overwrite the reserved `type`
    claim, so a 30-day refresh token passed as an access token."""
    _make_admin()
    login = _login(client)
    refresh_cookie_value = client.get_cookie(ADMIN_REFRESH_COOKIE, path=ADMIN_COOKIE_PATH).value

    # Present the refresh token as a bearer token against a protected route.
    resp = client.get(
        "/api/admin/auth/me",
        headers={"Authorization": f"Bearer {refresh_cookie_value}"},
    )

    assert resp.status_code in (401, 422), (
        "a refresh token must never authenticate an admin API call"
    )
    # the genuine access token still works
    ok = client.get(
        "/api/admin/auth/me",
        headers={"Authorization": f"Bearer {login.get_json()['access_token']}"},
    )
    assert ok.status_code == 200


def test_customer_token_cannot_access_admin_routes(app, client):
    from flask_jwt_extended import create_access_token

    with app.app_context():
        token = create_access_token(identity="00000000-0000-0000-0000-000000000001")

    resp = client.get("/api/admin/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


# ── Refresh / CSRF / logout ───────────────────────────────────────────────
def test_admin_refresh_requires_csrf_header(app, client):
    _make_admin()
    _login(client)

    resp = client.post("/api/admin/auth/refresh")
    assert resp.status_code == 401


def test_admin_refresh_with_csrf_returns_new_token_and_rotates(app, client):
    _make_admin()
    _login(client)
    csrf = client.get_cookie(ADMIN_CSRF_COOKIE).value
    before = client.get_cookie(ADMIN_REFRESH_COOKIE, path=ADMIN_COOKIE_PATH).value

    resp = client.post("/api/admin/auth/refresh", headers={"X-CSRF-TOKEN": csrf})

    assert resp.status_code == 200
    assert resp.get_json()["access_token"]
    assert _cookie_header(resp, ADMIN_REFRESH_COOKIE) is not None
    assert client.get_cookie(ADMIN_REFRESH_COOKIE, path=ADMIN_COOKIE_PATH).value != before  # rotated


def test_admin_refresh_rejects_deactivated_admin(app, client):
    admin = _make_admin()
    _login(client)
    csrf = client.get_cookie(ADMIN_CSRF_COOKIE).value

    admin.is_active = False
    db.session.commit()

    resp = client.post("/api/admin/auth/refresh", headers={"X-CSRF-TOKEN": csrf})
    assert resp.status_code == 401


def test_admin_logout_clears_cookies(app, client):
    _make_admin()
    _login(client)

    resp = client.post("/api/admin/auth/logout")

    assert resp.status_code == 200
    assert _cookie_header(resp, ADMIN_REFRESH_COOKIE) is not None
    # after logout the refresh cookie no longer authenticates
    follow_up = client.post("/api/admin/auth/refresh")
    assert follow_up.status_code == 401


def test_admin_refresh_without_cookie_is_rejected(app, client):
    resp = client.post("/api/admin/auth/refresh")
    assert resp.status_code == 401


# ── Rotating an admin password from the CLI ───────────────────

def test_set_admin_password_replaces_the_hash(app, client, monkeypatch):
    from tests.helpers import ADMIN_PASSWORD, make_admin

    admin = make_admin(email="rotate@example.com")
    monkeypatch.setenv("ADMIN_EMAIL", admin.email)
    monkeypatch.setenv("ADMIN_PASSWORD", "A-Brand-New-Passphrase-42")

    result = app.test_cli_runner().invoke(args=["set-admin-password"])

    assert result.exit_code == 0, result.output
    # The new password is never echoed back.
    assert "A-Brand-New-Passphrase-42" not in result.output
    login = lambda pw: client.post(  # noqa: E731
        "/api/admin/auth/login", json={"email": admin.email, "password": pw}
    ).status_code
    assert login(ADMIN_PASSWORD) == 401
    assert login("A-Brand-New-Passphrase-42") == 200


def test_set_admin_password_refuses_a_short_password(app, monkeypatch):
    from tests.helpers import make_admin

    admin = make_admin(email="short@example.com")
    monkeypatch.setenv("ADMIN_EMAIL", admin.email)
    monkeypatch.setenv("ADMIN_PASSWORD", "short")

    result = app.test_cli_runner().invoke(args=["set-admin-password"])

    assert result.exit_code != 0


def test_set_admin_password_reports_an_unknown_admin(app, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "nobody@example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "A-Brand-New-Passphrase-42")

    result = app.test_cli_runner().invoke(args=["set-admin-password"])

    assert result.exit_code != 0
    assert "No admin" in result.output


# ── Sign-ins are on the audit trail ───────────────────────────

def _sign_in_entries():
    from app.models.ops import AuditLog
    return AuditLog.query.filter_by(entity_type="sign_ins").order_by(AuditLog.id).all()


def test_successful_admin_sign_in_is_audited(app, client):
    from tests.helpers import ADMIN_PASSWORD, make_admin
    admin = make_admin(email="audited@example.com")

    resp = client.post(
        "/api/admin/auth/login",
        json={"email": admin.email, "password": ADMIN_PASSWORD},
        headers={"User-Agent": "pytest-browser"},
    )
    assert resp.status_code == 200

    [entry] = _sign_in_entries()
    assert entry.action == "admin_sign_in"
    assert entry.actor_type == "admin"
    assert str(entry.admin_id) == str(admin.id)
    assert entry.actor_label == "audited@example.com"
    assert entry.ip
    assert entry.changes == {"user_agent": "pytest-browser"}


def test_failed_admin_sign_ins_are_audited_without_the_password(app, client):
    from tests.helpers import make_admin
    admin = make_admin(email="audited@example.com")
    inactive = make_admin(email="gone@example.com")
    inactive.is_active = False
    db.session.commit()

    attempts = [
        ("audited@example.com", "WrongPass999!", 401, "wrong password"),
        ("nobody@example.com", "WrongPass999!", 401, "no admin with this email"),
        ("gone@example.com", "AdminPass123!", 403, "account is deactivated"),
    ]
    for email, password, status, _ in attempts:
        resp = client.post("/api/admin/auth/login", json={"email": email, "password": password})
        assert resp.status_code == status
        # the browser is never told which of the two it was
        if status == 401:
            assert resp.get_json() == {"error": "Invalid email or password"}

    entries = _sign_in_entries()
    assert [e.action for e in entries] == ["admin_sign_in_failed"] * 3
    assert [e.changes["reason"] for e in entries] == [a[3] for a in attempts]
    assert [e.actor_label for e in entries] == [a[0] for a in attempts]
    assert all(e.actor_type == "anonymous" and e.admin_id is None for e in entries)
    assert entries[0].entity_id == str(admin.id)
    assert entries[1].entity_id is None
    assert "WrongPass999!" not in str([(e.summary, e.changes) for e in entries])


def test_sign_ins_show_in_the_audit_log_endpoint(app, client):
    from tests.helpers import admin_headers
    client.post("/api/admin/auth/login", json={"email": "nobody@example.com", "password": "WrongPass999!"})
    body = client.get(
        "/api/admin/audit-log?actor_type=anonymous", headers=admin_headers()
    ).get_json()
    assert body["entries"][0]["action"] == "admin_sign_in_failed"
    assert body["entries"][0]["actor"] == "nobody@example.com"
    assert "sign_ins" in body["entity_types"]
