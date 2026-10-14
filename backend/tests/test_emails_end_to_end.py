"""Every email the store sends: it is sent, it reads correctly, its link works.

There are two: the order confirmation and the password reset. The mail
provider's HTTP call is captured, so these check the real message.
"""
import re

import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.user import User
from app.services import email as email_svc
from tests.factories import make_address, make_cart, make_coupon, make_product, make_user
from tests.helpers import customer_headers


class _Accepted:
    status_code, text = 200, "ok"


@pytest.fixture
def outbox(app, monkeypatch):
    """Messages handed to the mail provider, as the JSON it would receive."""
    sent = []
    monkeypatch.setitem(app.config, "RESEND_API_KEY", "re_test")
    monkeypatch.setitem(app.config, "EMAIL_FROM", "Store <orders@example.com>")
    monkeypatch.setitem(app.config, "EMAIL_ENABLED", True)
    monkeypatch.setitem(app.config, "EMAIL_ASYNC", False)
    monkeypatch.setitem(app.config, "FRONTEND_ORIGIN", "https://shop.example.com")
    monkeypatch.setitem(app.config, "SITE_URL", "https://shop.example.com")
    monkeypatch.setattr(email_svc.requests, "post", lambda url, headers=None, json=None, timeout=None: sent.append(json) or _Accepted())
    app.config["RATELIMIT_ENABLED"] = False
    yield sent
    app.config["RATELIMIT_ENABLED"] = True


def _links(message):
    return re.findall(r'href="([^"]+)"', message["html"])


def _customer(email="reader@example.com", password="OldPassword1!"):
    user = User(full_name="Asha Reader", email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return user


# ── Password reset ────────────────────────────────────────────

def test_the_reset_email_link_opens_the_reset_page_and_the_token_works_once(client, outbox):
    _customer()

    asked = client.post("/api/auth/forgot-password", json={"email": "reader@example.com"})
    assert asked.status_code == 200

    assert len(outbox) == 1
    message = outbox[0]
    assert message["to"] == ["reader@example.com"]
    assert message["from"] == "Store <orders@example.com>"
    assert message["subject"].startswith("Reset your ")
    link = next(h for h in _links(message) if "reset-password" in h)
    assert link.startswith("https://shop.example.com/reset-password?token=")
    assert link in message["text"]                               # the plain-text part carries the same link
    token = link.split("token=")[1]
    assert len(token) >= 40

    changed = client.post("/api/auth/reset-password", json={"token": token, "new_password": "BrandNewPass9!"})
    assert changed.status_code == 200
    assert client.post("/api/auth/login", json={"email": "reader@example.com", "password": "BrandNewPass9!"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "reader@example.com", "password": "OldPassword1!"}).status_code == 401

    again = client.post("/api/auth/reset-password", json={"token": token, "new_password": "AnotherPass10!"})
    assert again.status_code == 400                              # a link is good for one use


def test_asking_twice_cancels_the_first_link(client, outbox):
    _customer()
    client.post("/api/auth/forgot-password", json={"email": "reader@example.com"})
    client.post("/api/auth/forgot-password", json={"email": "reader@example.com"})
    first, second = (next(h for h in _links(m) if "reset-password" in h).split("token=")[1] for m in outbox)
    assert first != second
    assert client.post("/api/auth/reset-password", json={"token": first, "new_password": "BrandNewPass9!"}).status_code == 400
    assert client.post("/api/auth/reset-password", json={"token": second, "new_password": "BrandNewPass9!"}).status_code == 200


def test_an_unknown_address_gets_the_same_answer_and_no_email(client, outbox):
    _customer()
    known = client.post("/api/auth/forgot-password", json={"email": "reader@example.com"})
    unknown = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert unknown.status_code == known.status_code == 200
    assert unknown.get_json()["message"] == known.get_json()["message"]
    assert [m["to"] for m in outbox] == [["reader@example.com"]]


def test_production_never_returns_the_reset_token_in_the_response(client, outbox, app):
    _customer()
    assert not app.config.get("DEBUG")
    body = client.post("/api/auth/forgot-password", json={"email": "reader@example.com"}).get_json()
    assert set(body) == {"message"}


# ── Order confirmation ────────────────────────────────────────

def test_the_order_email_has_every_line_every_total_and_a_working_link(client, outbox):
    user = make_user(email="buyer@example.com")
    address = make_address(user)
    product, variant = make_product(price=1250, stock=5)
    coupon = make_coupon(code="TEN", discount_value=10)
    make_cart(user, [(variant, 2)], coupon=coupon)
    headers = customer_headers(user)

    placed = client.post("/api/orders", headers=headers, json={"address_id": address.id, "payment_method": "cod"})
    assert placed.status_code in (200, 201)
    order = client.get(f"/api/orders/{placed.get_json()['order_id']}", headers=headers).get_json()

    assert len(outbox) == 1
    message = outbox[0]
    assert message["to"] == ["buyer@example.com"]
    assert order["order_number"] in message["subject"]
    html = message["html"]
    assert product.name in html
    for amount in (2500, 250, 112.5, 2362.5):                    # subtotal, discount, GST, total
        assert f"{amount:,.2f}" in html, amount
    assert "TEN" in html or "Discount" in html
    link = next(h for h in _links(message) if "/account/orders/" in h)
    assert link == f"https://shop.example.com/account/orders/{order['id']}"
    # the page that link opens loads this order for this customer
    assert client.get(f"/api/orders/{link.rsplit('/', 1)[1]}", headers=headers).status_code == 200
    assert link in message["text"] and "2,362.50" in message["text"]


def test_a_mail_provider_outage_does_not_stop_the_order(client, app, monkeypatch, outbox):
    def down(*_a, **_k):
        raise email_svc.requests.ConnectionError("mail provider is down")
    monkeypatch.setattr(email_svc.requests, "post", down)
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=500, stock=5)
    make_cart(user, [(variant, 1)])
    placed = client.post("/api/orders", headers=customer_headers(user), json={"address_id": address.id, "payment_method": "cod"})
    assert placed.status_code in (200, 201)


def test_no_email_is_attempted_when_no_mail_key_is_set(client, app, monkeypatch):
    calls = []
    monkeypatch.setitem(app.config, "EMAIL_ENABLED", False)
    monkeypatch.setattr(email_svc.requests, "post", lambda *a, **k: calls.append(1))
    _customer()
    app.config["RATELIMIT_ENABLED"] = False
    try:
        assert client.post("/api/auth/forgot-password", json={"email": "reader@example.com"}).status_code == 200
    finally:
        app.config["RATELIMIT_ENABLED"] = True
    assert calls == []
