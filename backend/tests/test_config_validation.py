"""The app factory must refuse to start a production app with weak config."""
import pytest

from app import _validate_config


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
        SUPABASE_URL="https://proj.supabase.co",
        SUPABASE_SERVICE_KEY="service-key",
    )
    _validate_config(app)  # must not raise


def test_development_is_exempt():
    app = _FakeApp(DEBUG=True, TESTING=False, SECRET_KEY="dev-secret-change-me")
    _validate_config(app)  # must not raise
