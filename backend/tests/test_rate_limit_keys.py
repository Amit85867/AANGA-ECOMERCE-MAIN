"""Rate limits must land on the real visitor: the right address behind the
proxies, and the account rather than the address on signed-in routes."""
from flask import Flask, request
from werkzeug.security import generate_password_hash

from app import _apply_proxy_fix
from app.extensions import db
from app.models.user import User
from tests.factories import make_user
from tests.helpers import admin_headers, customer_headers


def _proxied_app(hops):
    app = Flask(__name__)
    app.config.update(DEBUG=False, TESTING=False, TRUSTED_PROXY_COUNT=hops)
    _apply_proxy_fix(app)

    @app.route("/ip")
    def ip():
        return request.remote_addr

    return app.test_client()


def _ip(client, forwarded):
    return client.get(
        "/ip",
        headers={"X-Forwarded-For": forwarded},
        environ_base={"REMOTE_ADDR": "10.0.0.9"},
    ).get_data(as_text=True)


# ── Client address behind proxies ─────────────────────────────

def test_one_proxy_uses_the_address_it_reported():
    assert _ip(_proxied_app(1), "203.0.113.7") == "203.0.113.7"


def test_two_proxies_use_the_second_entry_from_the_right():
    """Static-site rewrite, then the API's load balancer."""
    assert _ip(_proxied_app(2), "203.0.113.7, 172.16.0.1") == "203.0.113.7"


def test_a_forged_header_cannot_change_the_address():
    """Whatever the client sends ends up left of the entries the proxies add."""
    assert _ip(_proxied_app(2), "1.2.3.4, 203.0.113.7, 172.16.0.1") == "203.0.113.7"
    assert _ip(_proxied_app(1), "1.2.3.4, 203.0.113.7") == "203.0.113.7"


def test_too_few_trusted_proxies_resolves_to_a_proxy():
    """The failure System Health exists to catch: everyone shares one bucket."""
    assert _ip(_proxied_app(1), "203.0.113.7, 172.16.0.1") == "172.16.0.1"


def test_no_proxy_fix_in_development():
    app = Flask(__name__)
    app.config.update(DEBUG=True, TESTING=False, TRUSTED_PROXY_COUNT=2)
    wsgi = app.wsgi_app
    _apply_proxy_fix(app)
    assert app.wsgi_app == wsgi


def test_health_reports_proxy_hops(client):
    resp = client.get(
        "/api/admin/system/health",
        headers={**admin_headers(), "X-Forwarded-For": "203.0.113.7, 172.16.0.1"},
    )
    body = resp.get_json()["app"]
    assert body["proxy_hops_seen"] == 2
    assert "proxy_hops_trusted" in body


# ── Signed-in routes are limited per account ──────────────────

def _coupon(client, headers, ip):
    return client.post(
        "/api/cart/coupon",
        json={"code": "NOPE"},
        headers=headers,
        environ_base={"REMOTE_ADDR": ip},
    ).status_code


def test_one_account_is_limited_across_addresses(client):
    """Switching network does not reset the allowance (30 per hour)."""
    headers = customer_headers(make_user())
    codes = [_coupon(client, headers, f"198.51.100.{i}") for i in range(31)]
    assert 429 not in codes[:30]
    assert codes[30] == 429


def test_accounts_sharing_an_address_have_separate_limits(client):
    first = customer_headers(make_user())
    second = customer_headers(make_user())
    for _ in range(30):
        _coupon(client, first, "198.51.100.1")
    assert _coupon(client, first, "198.51.100.1") == 429
    assert _coupon(client, second, "198.51.100.1") != 429


def test_a_bad_token_is_limited_by_address(client):
    """An invalid token must not buy a fresh bucket per request."""
    codes = [
        _coupon(client, {"Authorization": f"Bearer junk{i}"}, "198.51.100.2")
        for i in range(31)
    ]
    assert codes[30] == 429


# ── Sign-in is limited per account as well as per address ─────

def test_login_guessing_from_many_addresses_is_limited(client):
    db.session.add(User(
        full_name="Target", email="target@example.com",
        password_hash=generate_password_hash("CorrectHorse1!"),
    ))
    db.session.commit()
    codes = [
        client.post(
            "/api/auth/login",
            json={"email": "Target@example.com", "password": "wrong"},
            environ_base={"REMOTE_ADDR": f"198.51.100.{i}"},
        ).status_code
        for i in range(21)
    ]
    assert 429 not in codes[:20]
    assert codes[20] == 429


def test_admin_login_guessing_from_many_addresses_is_limited(client):
    codes = [
        client.post(
            "/api/admin/auth/login",
            json={"email": "admin@example.com", "password": "wrong"},
            environ_base={"REMOTE_ADDR": f"198.51.100.{i}"},
        ).status_code
        for i in range(11)
    ]
    assert 429 not in codes[:10]
    assert codes[10] == 429


# ── Renewing an admin session is limited per admin, not per address ──

def _renew(client, admin, ip="198.51.100.9"):
    from flask_jwt_extended import create_refresh_token, decode_token
    from app.routes.admin.auth import ADMIN_COOKIE_PATH, ADMIN_REFRESH_COOKIE

    token = create_refresh_token(identity=str(admin.id), additional_claims={"actor": "admin", "role": admin.role})
    client.set_cookie(ADMIN_REFRESH_COOKIE, token, path=ADMIN_COOKIE_PATH)
    return client.post(
        "/api/admin/auth/refresh",
        headers={"X-CSRF-TOKEN": decode_token(token)["csrf"]},
        environ_base={"REMOTE_ADDR": ip},
    ).status_code


def test_a_team_on_one_connection_is_not_locked_out_of_the_dashboard(client):
    """Every page reload renews the session. Counted per address (60 an hour),
    three people at one shop were sent back to the sign-in page mid-morning."""
    from tests.helpers import make_admin

    team = [make_admin("master"), make_admin("manager"), make_admin("staff")]
    codes = [_renew(client, admin) for _ in range(61) for admin in team]
    assert set(codes) == {200}


def test_renewal_without_a_session_is_limited_by_address(client):
    codes = [
        client.post("/api/admin/auth/refresh", environ_base={"REMOTE_ADDR": "198.51.100.10"}).status_code
        for _ in range(301)
    ]
    assert set(codes[:300]) == {401}
    assert codes[300] == 429
