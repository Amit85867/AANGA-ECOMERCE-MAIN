"""The app factory must refuse to start a production app with weak config."""
import pytest

from app import _validate_config
from config import UNSET_DATABASE_URL


class _FakeApp:
    def __init__(self, **config):
        self.config = config


def test_production_rejects_default_secrets():
    app = _FakeApp(
        DEBUG=False,
        TESTING=False,
        SECRET_KEY="dev-secret-change-me",
        JWT_SECRET_KEY="dev-jwt-change-me",
        SQLALCHEMY_DATABASE_URI="sqlite:///dev.db",
    )
    with pytest.raises(RuntimeError) as exc:
        _validate_config(app)
    msg = str(exc.value)
    assert "SECRET_KEY" in msg
    assert "JWT_SECRET_KEY" in msg
    assert "SQLite" in msg


def test_production_rejects_short_secrets():
    app = _FakeApp(
        DEBUG=False,
        TESTING=False,
        SECRET_KEY="short",
        JWT_SECRET_KEY="short",
        SQLALCHEMY_DATABASE_URI="postgresql://u:p@host/db",
    )
    with pytest.raises(RuntimeError) as exc:
        _validate_config(app)
    assert "too short" in str(exc.value)


def test_production_accepts_strong_config():
    app = _FakeApp(
        DEBUG=False,
        TESTING=False,
        SECRET_KEY="x" * 40,
        JWT_SECRET_KEY="y" * 40,
        SQLALCHEMY_DATABASE_URI="postgresql://u:p@host/db",
        # Object storage is mandatory in production — see test_storage.py.
        S3_ENDPOINT_URL="https://s3.example",
        S3_BUCKET="product-images",
        S3_ACCESS_KEY_ID="key",
        S3_SECRET_ACCESS_KEY="secret",
    )
    _validate_config(app)  # must not raise


def test_production_rejects_an_unset_database_url():
    """The fallback is a syntactically valid Postgres URI pointing nowhere, so
    it has to be caught by name rather than by scheme."""
    app = _FakeApp(
        DEBUG=False,
        TESTING=False,
        SECRET_KEY="x" * 40,
        JWT_SECRET_KEY="y" * 40,
        SQLALCHEMY_DATABASE_URI=UNSET_DATABASE_URL,
        S3_ENDPOINT_URL="https://s3.example",
        S3_BUCKET="product-images",
        S3_ACCESS_KEY_ID="key",
        S3_SECRET_ACCESS_KEY="secret",
    )
    with pytest.raises(RuntimeError) as exc:
        _validate_config(app)
    assert "DATABASE_URL is unset" in str(exc.value)


def test_development_is_exempt():
    app = _FakeApp(DEBUG=True, TESTING=False, SECRET_KEY="dev-secret-change-me")
    _validate_config(app)  # must not raise


# ── Optional integrations are all-or-nothing ──────────────────

INTEGRATION_VARS = (
    "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET",
    "SHIPROCKET_EMAIL", "SHIPROCKET_PASSWORD", "SHIPROCKET_PICKUP_PINCODE",
)


@pytest.fixture(autouse=True)
def _no_integrations_in_env(monkeypatch):
    """Whatever is in the developer's own environment must not decide these tests."""
    for key in INTEGRATION_VARS:
        monkeypatch.delenv(key, raising=False)


def _production_app():
    return _FakeApp(
        DEBUG=False, TESTING=False,
        SECRET_KEY="x" * 40, JWT_SECRET_KEY="y" * 40,
        SQLALCHEMY_DATABASE_URI="postgresql://u:p@host/db",
        S3_ENDPOINT_URL="https://s3.example", S3_BUCKET="product-images",
        S3_ACCESS_KEY_ID="key", S3_SECRET_ACCESS_KEY="secret",
    )


def test_production_starts_with_no_optional_integrations():
    _validate_config(_production_app())  # COD-only, no courier: must not raise


def test_razorpay_without_a_webhook_secret_refuses_to_start(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_live_x")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "secret")

    with pytest.raises(RuntimeError) as exc:
        _validate_config(_production_app())

    assert "RAZORPAY_WEBHOOK_SECRET" in str(exc.value)


def test_razorpay_key_without_its_secret_refuses_to_start(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_live_x")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "whsec")

    with pytest.raises(RuntimeError) as exc:
        _validate_config(_production_app())

    assert "RAZORPAY_KEY_SECRET" in str(exc.value)


def test_fully_configured_integrations_start(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_live_x")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "secret")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "whsec")
    monkeypatch.setenv("SHIPROCKET_EMAIL", "api@example.com")
    monkeypatch.setenv("SHIPROCKET_PASSWORD", "pw")
    monkeypatch.setenv("SHIPROCKET_PICKUP_PINCODE", "800001")

    _validate_config(_production_app())  # must not raise


@pytest.mark.parametrize("pincode", ["", "80001", "abcdef", "012345"])
def test_shiprocket_needs_a_real_pickup_pincode(monkeypatch, pincode):
    monkeypatch.setenv("SHIPROCKET_EMAIL", "api@example.com")
    monkeypatch.setenv("SHIPROCKET_PASSWORD", "pw")
    monkeypatch.setenv("SHIPROCKET_PICKUP_PINCODE", pincode)

    with pytest.raises(RuntimeError) as exc:
        _validate_config(_production_app())

    assert "SHIPROCKET_PICKUP_PINCODE" in str(exc.value)


def test_error_message_never_contains_a_secret_value(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_live_SENSITIVE")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "TOP-SECRET-VALUE")

    with pytest.raises(RuntimeError) as exc:
        _validate_config(_production_app())

    assert "SENSITIVE" not in str(exc.value)
    assert "TOP-SECRET-VALUE" not in str(exc.value)
