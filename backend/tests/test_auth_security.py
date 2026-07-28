"""Phase 2 security behaviour: token storage, refresh rotation, OTP leakage."""
import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db, limiter
from app.models.user import User
from app.models.cart import Cart

PASSWORD = "CorrectHorse1!"


def _make_login_user(email="login@example.com"):
    user = User(
        full_name="Login User",
        email=email,
        password_hash=generate_password_hash(PASSWORD),
    )
    db.session.add(user)
    db.session.flush()
    db.session.add(Cart(user_id=user.id))
    db.session.commit()
    return user


def _refresh_cookie_header(resp):
    for c in resp.headers.getlist("Set-Cookie"):
        if c.startswith("aanga_refresh="):
            return c
    return None


# ── Token storage ─────────────────────────────────────────────────────────
def test_login_returns_access_token_but_not_refresh_token_in_body(app, client):
    _make_login_user()

    resp = client.post("/api/auth/login", json={"email": "login@example.com", "password": PASSWORD})

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["access_token"]
    # The refresh token must never be readable by JavaScript.
    assert "refresh_token" not in body


def test_login_sets_httponly_refresh_cookie(app, client):
    _make_login_user()

    resp = client.post("/api/auth/login", json={"email": "login@example.com", "password": PASSWORD})

    cookie = _refresh_cookie_header(resp)
    assert cookie is not None, "refresh cookie was not set"
    assert "HttpOnly" in cookie
    assert "Path=/api/auth" in cookie


def test_register_also_uses_cookie(app, client):
    resp = client.post("/api/auth/register", json={
        "full_name": "New User",
        "email": "new@example.com",
        "password": PASSWORD,
    })

    assert resp.status_code == 201
    assert "refresh_token" not in resp.get_json()
    assert _refresh_cookie_header(resp) is not None


# ── Refresh rotation + logout ─────────────────────────────────────────────
def test_refresh_issues_new_access_token_and_rotates_cookie(app, client):
    _make_login_user()
    login = client.post("/api/auth/login", json={"email": "login@example.com", "password": PASSWORD})
    first_access = login.get_json()["access_token"]

    csrf = client.get_cookie("csrf_refresh_token")
    resp = client.post(
        "/api/auth/refresh",
        headers={"X-CSRF-TOKEN": csrf.value} if csrf else {},
    )

    assert resp.status_code == 200
    assert resp.get_json()["access_token"]
    # a fresh refresh cookie is issued on every use (rotation)
    assert _refresh_cookie_header(resp) is not None


def test_logout_clears_refresh_cookie(app, client):
    _make_login_user()
    client.post("/api/auth/login", json={"email": "login@example.com", "password": PASSWORD})

    resp = client.post("/api/auth/logout")

    assert resp.status_code == 200
    cookie = _refresh_cookie_header(resp)
    # cleared by setting an empty value / immediate expiry
    assert cookie is not None
    assert "aanga_refresh=;" in cookie or "Expires=Thu, 01 Jan 1970" in cookie


def test_refresh_without_cookie_is_rejected(app, client):
    resp = client.post("/api/auth/refresh")
    assert resp.status_code == 401


# ── OTP must not leak the code ────────────────────────────────────────────
def test_otp_response_never_leaks_code_outside_debug(app, client):
    """Regression: dev_otp used to be returned unconditionally (auth bypass)."""
    assert not app.config.get("DEBUG")

    resp = client.post("/api/auth/otp/send", json={"phone": "+919876543210"})

    assert resp.status_code == 200
    assert "dev_otp" not in resp.get_json()


# ── Rate limiting ─────────────────────────────────────────────────────────
def test_login_is_rate_limited(app, client):
    _make_login_user()
    codes = [
        client.post(
            "/api/auth/login",
            json={"email": "login@example.com", "password": "wrong"},
        ).status_code
        for _ in range(12)
    ]

    assert 429 in codes, f"expected a 429 among {codes}"
