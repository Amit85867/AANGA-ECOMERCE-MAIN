"""Tests for the Resend email service (best-effort, network mocked)."""
import pytest

from app.services import email as email_svc
from tests.factories import make_user, make_address, make_product, make_cart
from app.services.order_service import create_order_from_cart


class FakeResp:
    def __init__(self, status_code=200, text="ok"):
        self.status_code = status_code
        self.text = text


@pytest.fixture
def enable_email(app, monkeypatch):
    monkeypatch.setitem(app.config, "RESEND_API_KEY", "re_test")
    monkeypatch.setitem(app.config, "EMAIL_FROM", "AANGA <orders@aanga.in>")
    monkeypatch.setitem(app.config, "EMAIL_ENABLED", True)


def test_send_email_noop_when_not_configured(app, monkeypatch):
    calls = []
    monkeypatch.setattr(email_svc.requests, "post", lambda *a, **k: calls.append(1))
    # No RESEND_API_KEY in test config → must not hit the network.
    assert email_svc.send_email("a@b.com", "Hi", "<p>x</p>") is False
    assert calls == []


def test_send_email_posts_to_resend_when_configured(app, enable_email, monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return FakeResp(200)

    monkeypatch.setattr(email_svc.requests, "post", fake_post)

    ok = email_svc.send_email("a@b.com", "Hi", "<p>x</p>", text="x")
    assert ok is True
    assert captured["url"] == email_svc.RESEND_API_URL
    assert captured["headers"]["Authorization"] == "Bearer re_test"
    assert captured["json"]["to"] == ["a@b.com"]
    assert captured["json"]["subject"] == "Hi"


def test_send_email_skips_synthetic_phone_addresses(app, enable_email, monkeypatch):
    calls = []
    monkeypatch.setattr(email_svc.requests, "post", lambda *a, **k: calls.append(1))
    assert email_svc.send_email("919000000000@phone.aanga.in", "Hi", "<p>x</p>") is False
    assert calls == []


def test_send_email_returns_false_on_rejection(app, enable_email, monkeypatch):
    monkeypatch.setattr(email_svc.requests, "post", lambda *a, **k: FakeResp(422, "bad"))
    assert email_svc.send_email("a@b.com", "Hi", "<p>x</p>") is False


def test_order_confirmation_sent_on_order_creation(app, enable_email, monkeypatch):
    sent = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        sent["json"] = json
        return FakeResp(200)

    monkeypatch.setattr(email_svc.requests, "post", fake_post)

    user = make_user(email="buyer@example.com")
    address = make_address(user)
    _, variant = make_product(price=300, stock=5)
    make_cart(user, [(variant, 2)])

    order, err = create_order_from_cart(user.id, address.id, "cod")

    assert err is None
    assert sent["json"]["to"] == ["buyer@example.com"]
    assert order.order_number in sent["json"]["subject"]
