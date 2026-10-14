"""Auth across two hosts: storefront on example.com, API on api.example.com.

Different origins (so CORS applies) but the same registrable domain, so the
refresh cookie is scoped to ".example.com" and SameSite=Lax is enough.

The failure these guard against is subtle and total: get the cookie Domain or
the CORS allow-list wrong and sign-in *appears* to work — the login response
comes back 200 — but the refresh cookie is never stored, so the customer is
signed out the moment they reload.
"""
import re

import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.user import User

PASSWORD = "Cross-Domain-Pw1!"
STOREFRONT = "https://example.com"
WWW = "https://www.example.com"
OTHER = "https://evil.example.net"


@pytest.fixture()
def cross_domain(app, monkeypatch):
    """Configure the app the way production will be configured."""
    monkeypatch.setitem(app.config, "COOKIE_DOMAIN", ".example.com")
    monkeypatch.setitem(app.config, "JWT_COOKIE_DOMAIN", ".example.com")
    monkeypatch.setitem(app.config, "JWT_COOKIE_SAMESITE", "Lax")
    monkeypatch.setitem(app.config, "JWT_COOKIE_SECURE", True)
    return app


@pytest.fixture()
def customer(app):
    user = User(
        email="cross@example.com",
        password_hash=generate_password_hash(PASSWORD),
        full_name="Cross Domain",
    )
    db.session.add(user)
    db.session.commit()
    return user


# Requests are made AT the API host, the way the browser makes them, so a
# cookie scoped to ".example.com" is actually stored by the test client. With
# the default "localhost" host it would be silently dropped and every cookie
# assertion would pass for the wrong reason.
API_BASE = "https://api.example.com"


def _login(client, origin=STOREFRONT):
    return client.post(
        "/api/auth/login",
        json={"email": "cross@example.com", "password": PASSWORD},
        headers={"Origin": origin},
        base_url=API_BASE,
    )


def _cookies(response):
    """{name: full Set-Cookie line} for everything the response sets."""
    out = {}
    for header in response.headers.getlist("Set-Cookie"):
        name = header.split("=", 1)[0]
        out[name] = header
    return out


# ── Cookies ───────────────────────────────────────────────────────────────
def test_login_scopes_the_refresh_cookie_to_the_parent_domain(cross_domain, client, customer):
    response = _login(client)
    assert response.status_code == 200

    cookies = _cookies(response)
    refresh = cookies.get("aanga_refresh")
    assert refresh, f"no refresh cookie set; got {list(cookies)}"

    # Domain must be the parent, or api.example.com's cookie never reaches
    # example.com and the customer is signed out on reload.
    assert re.search(r"Domain=\.?example\.com", refresh, re.I), refresh
    assert "HttpOnly" in refresh                      # JavaScript must not read it
    assert "Secure" in refresh
    assert re.search(r"SameSite=Lax", refresh, re.I), refresh


def test_csrf_cookie_is_readable_by_the_storefront(cross_domain, client, customer):
    """The double-submit token has to be readable, or the frontend cannot echo it."""
    cookies = _cookies(_login(client))
    csrf = cookies.get("csrf_refresh_token")
    assert csrf, f"no CSRF cookie set; got {list(cookies)}"

    assert "HttpOnly" not in csrf, "the CSRF cookie must be readable by JavaScript"
    assert re.search(r"Domain=\.?example\.com", csrf, re.I), csrf
    assert "Secure" in csrf


def test_refresh_after_a_reload_keeps_the_customer_signed_in(cross_domain, client, customer):
    """A reload loses the in-memory access token; only the cookie survives."""
    login = _login(client)
    access = login.get_json()["access_token"]
    csrf = client.get_cookie("csrf_refresh_token", domain="example.com")
    assert csrf is not None, "the CSRF cookie was not stored for example.com"

    # No Authorization header: exactly what the app does on a cold page load.
    refreshed = client.post(
        "/api/auth/refresh",
        headers={"Origin": STOREFRONT, "X-CSRF-TOKEN": csrf.value},
        base_url=API_BASE,
    )

    assert refreshed.status_code == 200
    new_access = refreshed.get_json()["access_token"]
    assert new_access and new_access != access


def test_refresh_without_the_csrf_header_is_refused(cross_domain, client, customer):
    _login(client)

    refused = client.post("/api/auth/refresh", headers={"Origin": STOREFRONT},
                          base_url=API_BASE)

    assert refused.status_code in (401, 422)


def test_logout_clears_the_cookie_on_the_same_domain(cross_domain, client, customer):
    _login(client)
    csrf = client.get_cookie("csrf_refresh_token", domain="example.com")
    assert csrf is not None

    out = client.post(
        "/api/auth/logout",
        headers={"Origin": STOREFRONT, "X-CSRF-TOKEN": csrf.value},
        base_url=API_BASE,
    )
    assert out.status_code == 200

    # Cleared with the same Domain, or the browser keeps the original cookie.
    cleared = _cookies(out).get("aanga_refresh", "")
    assert cleared, "logout did not clear the refresh cookie"
    assert re.search(r"Domain=\.?example\.com", cleared, re.I), cleared

    after = client.post("/api/auth/refresh", headers={"Origin": STOREFRONT},
                        base_url=API_BASE)
    assert after.status_code in (401, 422)


# ── CORS ──────────────────────────────────────────────────────────────────
# CORS is wired once, in create_app, from CORS_ORIGINS. Flask refuses to accept
# new after_request handlers on an app that has already served a request, so
# these build their own app with the environment production will have.
@pytest.fixture(scope="module")
def cross_origin_client():
    import os

    from app import create_app

    previous = os.environ.get("CORS_ORIGINS")
    os.environ["CORS_ORIGINS"] = f"{STOREFRONT},{WWW}"
    try:
        application = create_app()
        application.config.update(TESTING=True)
        with application.test_client() as c:
            yield application, c
    finally:
        if previous is None:
            os.environ.pop("CORS_ORIGINS", None)
        else:
            os.environ["CORS_ORIGINS"] = previous


@pytest.mark.parametrize("origin", [STOREFRONT, WWW])
def test_storefront_origins_are_allowed_with_credentials(cross_origin_client, origin):
    _app, client = cross_origin_client

    response = client.options(
        "/api/products",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.headers.get("Access-Control-Allow-Origin") == origin
    assert response.headers.get("Access-Control-Allow-Credentials") == "true"


def test_another_origin_is_not_granted_access(cross_origin_client):
    _app, client = cross_origin_client

    response = client.options(
        "/api/products",
        headers={"Origin": OTHER, "Access-Control-Request-Method": "GET"},
    )

    # Either no header, or one naming someone else: both make the browser
    # refuse. What must never appear is OTHER or "*".
    allowed = response.headers.get("Access-Control-Allow-Origin")
    assert allowed != OTHER
    assert allowed != "*"


def test_the_allow_list_is_exact_and_has_no_wildcard(cross_origin_client):
    """A wildcard with credentials is illegal, and would be a serious hole."""
    application, _client = cross_origin_client
    resolved = application.config["RESOLVED_CORS_ORIGINS"]

    assert "*" not in resolved
    assert STOREFRONT in resolved and WWW in resolved


# ── The API must not be indexed ───────────────────────────────────────────
def test_api_responses_say_noindex(client):
    assert "noindex" in client.get("/api/ping").headers.get("X-Robots-Tag", "")
    assert "noindex" in client.get("/api/products").headers.get("X-Robots-Tag", "")
