"""Image storage backend selection and the production guard.

Production must never fall back to local disk: Render/Railway filesystems are
ephemeral, so product images would disappear on the next deploy.
"""
import io

import pytest
import requests
from werkzeug.datastructures import FileStorage

from app import _validate_config
from app.services import storage
from app.services.storage import (
    StorageError,
    is_object_storage_configured,
    save_image,
)


class _FakeApp:
    def __init__(self, **config):
        self.config = config


def _upload_file(name="photo.png", data=b"fake-png-bytes"):
    return FileStorage(stream=io.BytesIO(data), filename=name, content_type="image/png")


# ── Backend selection ─────────────────────────────────────────────────────
def test_object_storage_not_configured_by_default(app):
    assert is_object_storage_configured(app.config) is False


def test_object_storage_detected_when_keys_present():
    cfg = {"SUPABASE_URL": "https://x.supabase.co", "SUPABASE_SERVICE_KEY": "k"}
    assert is_object_storage_configured(cfg) is True


def test_partial_config_does_not_count_as_configured():
    assert is_object_storage_configured({"SUPABASE_URL": "https://x.supabase.co"}) is False
    assert is_object_storage_configured({"SUPABASE_SERVICE_KEY": "k"}) is False


def test_local_backend_returns_static_url(app, tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "_save_to_disk", lambda f, name: f"/static/uploads/{name}")

    url = save_image(_upload_file())

    assert url.startswith("/static/uploads/")
    assert url.endswith(".png")


# ── Supabase backend ──────────────────────────────────────────────────────
def test_supabase_backend_posts_and_returns_public_url(app, monkeypatch):
    app.config["SUPABASE_URL"] = "https://proj.supabase.co"
    app.config["SUPABASE_SERVICE_KEY"] = "service-key"
    app.config["SUPABASE_STORAGE_BUCKET"] = "product-images"
    captured = {}

    class _Resp:
        status_code = 200
        text = ""

    def fake_post(url, data=None, headers=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        return _Resp()

    monkeypatch.setattr(requests, "post", fake_post)
    try:
        url = save_image(_upload_file())
    finally:
        app.config["SUPABASE_URL"] = ""
        app.config["SUPABASE_SERVICE_KEY"] = ""

    assert "/storage/v1/object/product-images/" in captured["url"]
    assert captured["headers"]["Authorization"] == "Bearer service-key"
    assert url.startswith("https://proj.supabase.co/storage/v1/object/public/product-images/")


def test_supabase_failure_raises_storage_error(app, monkeypatch):
    app.config["SUPABASE_URL"] = "https://proj.supabase.co"
    app.config["SUPABASE_SERVICE_KEY"] = "service-key"

    class _Resp:
        status_code = 403
        text = "denied"

    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp())
    try:
        with pytest.raises(StorageError):
            save_image(_upload_file())
    finally:
        app.config["SUPABASE_URL"] = ""
        app.config["SUPABASE_SERVICE_KEY"] = ""


# ── Production guard ──────────────────────────────────────────────────────
def test_production_refuses_ephemeral_image_storage():
    bad = _FakeApp(
        DEBUG=False,
        TESTING=False,
        SECRET_KEY="x" * 40,
        JWT_SECRET_KEY="y" * 40,
        SQLALCHEMY_DATABASE_URI="postgresql://u:p@host/db",
    )
    with pytest.raises(RuntimeError) as exc:
        _validate_config(bad)
    assert "SUPABASE_URL" in str(exc.value)


def test_production_accepts_configured_object_storage():
    ok = _FakeApp(
        DEBUG=False,
        TESTING=False,
        SECRET_KEY="x" * 40,
        JWT_SECRET_KEY="y" * 40,
        SQLALCHEMY_DATABASE_URI="postgresql://u:p@host/db",
        SUPABASE_URL="https://proj.supabase.co",
        SUPABASE_SERVICE_KEY="service-key",
    )
    _validate_config(ok)  # must not raise
