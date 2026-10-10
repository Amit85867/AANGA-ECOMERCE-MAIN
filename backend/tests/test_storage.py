"""Image storage: optimisation, backend selection, and the production guard.

Production must never fall back to local disk (Render/Railway filesystems are
ephemeral) and every upload must be optimised before it is stored.
"""
import io

import pytest
import requests
from PIL import Image
from werkzeug.datastructures import FileStorage

from app import _validate_config
from app.services import storage
from app.services.storage import (
    StorageError,
    is_object_storage_configured,
    optimize_image,
    save_image,
)


class _FakeApp:
    def __init__(self, **config):
        self.config = config


def _png_upload(name="photo.png", size=(2000, 2500), colour=(120, 30, 60)):
    """A large solid PNG, deliberately bigger than MAX_DIMENSION."""
    img = Image.new("RGB", size, colour)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return FileStorage(stream=buf, filename=name, content_type="image/png")


# ── Optimisation ──────────────────────────────────────────────────────────
def test_optimize_converts_png_to_webp(app):
    data, ext, content_type = optimize_image(_png_upload())

    assert ext == "webp"
    assert content_type == "image/webp"
    # bytes really are WebP
    assert Image.open(io.BytesIO(data)).format == "WEBP"


def test_optimize_downscales_to_max_dimension(app):
    data, _, _ = optimize_image(_png_upload(size=(3000, 3000)))

    out = Image.open(io.BytesIO(data))
    assert max(out.size) == storage.MAX_DIMENSION


def test_optimize_shrinks_file_size(app):
    upload = _png_upload(size=(2000, 2500))
    upload.stream.seek(0, io.SEEK_END)
    original = upload.stream.tell()
    upload.stream.seek(0)

    data, _, _ = optimize_image(upload)

    assert len(data) < original


def test_optimize_passes_gif_through_untouched(app):
    gif = Image.new("RGB", (10, 10), (0, 0, 0))
    buf = io.BytesIO()
    gif.save(buf, format="GIF")
    raw = buf.getvalue()
    fs = FileStorage(stream=io.BytesIO(raw), filename="a.gif", content_type="image/gif")

    data, ext, content_type = optimize_image(fs)

    assert ext == "gif"
    assert data == raw


# ── Backend selection ─────────────────────────────────────────────────────
def test_object_storage_not_configured_without_keys():
    # Explicit config so the result never depends on the developer's ambient
    # .env (which may legitimately have Supabase configured).
    assert is_object_storage_configured({}) is False
    assert is_object_storage_configured({"SUPABASE_URL": "", "SUPABASE_SERVICE_KEY": ""}) is False


def test_object_storage_detected_when_keys_present():
    cfg = {"SUPABASE_URL": "https://x.supabase.co", "SUPABASE_SERVICE_KEY": "k"}
    assert is_object_storage_configured(cfg) is True


def test_partial_config_does_not_count_as_configured():
    assert is_object_storage_configured({"SUPABASE_URL": "https://x.supabase.co"}) is False
    assert is_object_storage_configured({"SUPABASE_SERVICE_KEY": "k"}) is False


def test_local_backend_writes_webp_and_returns_static_url(app, monkeypatch):
    # Force the local-disk branch regardless of any Supabase keys in the
    # ambient .env, so this test is deterministic and offline.
    monkeypatch.setitem(app.config, "SUPABASE_URL", "")
    monkeypatch.setitem(app.config, "SUPABASE_SERVICE_KEY", "")

    url = save_image(_png_upload())

    assert url.startswith("/static/uploads/")
    assert url.endswith(".webp")


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
        captured["content_type"] = headers["Content-Type"]
        return _Resp()

    monkeypatch.setattr(requests, "post", fake_post)
    try:
        url = save_image(_png_upload())
    finally:
        app.config["SUPABASE_URL"] = ""
        app.config["SUPABASE_SERVICE_KEY"] = ""

    assert "/storage/v1/object/product-images/" in captured["url"]
    assert captured["headers"]["Authorization"] == "Bearer service-key"
    assert captured["content_type"] == "image/webp"
    assert url.startswith("https://proj.supabase.co/storage/v1/object/public/product-images/")
    assert url.endswith(".webp")


def test_supabase_failure_raises_storage_error(app, monkeypatch):
    app.config["SUPABASE_URL"] = "https://proj.supabase.co"
    app.config["SUPABASE_SERVICE_KEY"] = "service-key"

    class _Resp:
        status_code = 403
        text = "denied"

    monkeypatch.setattr(requests, "post", lambda *a, **k: _Resp())
    try:
        with pytest.raises(StorageError):
            save_image(_png_upload())
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


# ── Thumbnails ────────────────────────────────────────────────

def _png(width, height):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "#336699").save(buf, format="PNG")
    buf.seek(0)
    return FileStorage(stream=buf, filename="photo.png", content_type="image/png")


def test_upload_stores_a_480px_thumbnail_next_to_the_original(app, tmp_path, monkeypatch):
    monkeypatch.setitem(app.config, "SUPABASE_URL", "")
    saved = {}
    monkeypatch.setattr(storage, "_save_bytes_to_disk",
                        lambda data, name: saved.setdefault(name, data) and f"/static/uploads/{name}")

    url = storage.save_image(_png(1200, 1600))

    original, thumb = sorted(saved, key=len)
    assert url == f"/static/uploads/{original}"
    assert thumb == original.replace(".webp", "_480.webp")
    small = Image.open(io.BytesIO(saved[thumb]))
    assert small.size == (480, 640)                       # same shape, 480 wide
    assert len(saved[thumb]) < len(saved[original])


def test_small_images_get_no_thumbnail(app, monkeypatch):
    monkeypatch.setitem(app.config, "SUPABASE_URL", "")
    saved = {}
    monkeypatch.setattr(storage, "_save_bytes_to_disk",
                        lambda data, name: saved.setdefault(name, data) and f"/static/uploads/{name}")

    storage.save_image(_png(300, 400))

    assert len(saved) == 1


def test_a_failed_thumbnail_does_not_fail_the_upload(app, monkeypatch):
    monkeypatch.setitem(app.config, "SUPABASE_URL", "")
    monkeypatch.setattr(storage, "_save_bytes_to_disk", lambda data, name: f"/static/uploads/{name}")

    def _boom(_bytes):
        raise OSError("disk full")

    monkeypatch.setattr(storage, "make_thumbnail", _boom)

    assert storage.save_image(_png(1200, 1600)).endswith(".webp")
