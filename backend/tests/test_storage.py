"""Image storage: optimisation, backend selection, and the production guard.

Production must never fall back to local disk (Render/Railway filesystems are
ephemeral) and every upload must be optimised before it is stored.
"""
import io

import pytest
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
    assert is_object_storage_configured(
        {"S3_ENDPOINT_URL": "", "S3_BUCKET": "", "S3_ACCESS_KEY_ID": "", "S3_SECRET_ACCESS_KEY": ""}
    ) is False


def test_object_storage_detected_when_keys_present():
    cfg = {"S3_ENDPOINT_URL": "https://s3.example", "S3_BUCKET": "b",
           "S3_ACCESS_KEY_ID": "k", "S3_SECRET_ACCESS_KEY": "s"}
    assert is_object_storage_configured(cfg) is True


def test_partial_config_does_not_count_as_configured():
    assert is_object_storage_configured({"S3_ENDPOINT_URL": "https://s3.example"}) is False
    assert is_object_storage_configured({"S3_BUCKET": "b", "S3_ACCESS_KEY_ID": "k"}) is False


def test_local_backend_writes_webp_and_returns_static_url(app, monkeypatch):
    # Force the local-disk branch regardless of any S3 settings in the
    # ambient .env, so this test is deterministic and offline.
    for name in ("S3_ENDPOINT_URL", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.setitem(app.config, name, "")

    url = save_image(_png_upload())

    assert url.startswith("/static/uploads/")
    assert url.endswith(".webp")


# ── Object-storage backend ────────────────────────────────────────────────
# The driver itself (put/delete/list, path style, public URLs) is covered in
# test_objectstore.py against a fake S3; here we only check that save_image
# routes through it and returns what it returns.
def test_object_storage_backend_returns_the_public_url(app, monkeypatch, fake_s3):
    url = save_image(_png_upload())

    assert url.startswith("https://s3.example/test-bucket/")
    assert url.endswith(".webp")
    key = url.rsplit("/", 1)[-1]
    assert fake_s3.content_type(key) == "image/webp"


def test_object_storage_failure_raises_storage_error(app, monkeypatch, fake_s3):
    fake_s3.fail_on_put = True

    with pytest.raises(StorageError):
        save_image(_png_upload())


# ── Production guard ──────────────────────────────────────────────────────
def _no_integration_env(monkeypatch):
    """_validate_config reads os.environ for the all-or-nothing integration
    rules, so a developer's .env must not decide whether these tests pass."""
    for name in ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET",
                 "SHIPROCKET_EMAIL", "SHIPROCKET_PASSWORD", "SHIPROCKET_PICKUP_PINCODE"):
        monkeypatch.delenv(name, raising=False)


def test_production_refuses_ephemeral_image_storage(monkeypatch):
    _no_integration_env(monkeypatch)
    bad = _FakeApp(
        DEBUG=False,
        TESTING=False,
        SECRET_KEY="x" * 40,
        JWT_SECRET_KEY="y" * 40,
        SQLALCHEMY_DATABASE_URI="postgresql://u:p@host/db",
    )
    with pytest.raises(RuntimeError) as exc:
        _validate_config(bad)
    message = str(exc.value)
    assert "object storage is not configured" in message
    # It must name what is missing, not just complain.
    assert "S3_ENDPOINT_URL" in message
    # The old Supabase settings must not come back as a requirement.
    assert "SUPABASE" not in message


def test_production_accepts_configured_object_storage(monkeypatch):
    _no_integration_env(monkeypatch)
    ok = _FakeApp(
        DEBUG=False,
        TESTING=False,
        SECRET_KEY="x" * 40,
        JWT_SECRET_KEY="y" * 40,
        SQLALCHEMY_DATABASE_URI="postgresql://u:p@host/db",
        S3_ENDPOINT_URL="https://s3.example",
        S3_BUCKET="product-images",
        S3_ACCESS_KEY_ID="key",
        S3_SECRET_ACCESS_KEY="secret",
    )
    _validate_config(ok)  # must not raise


# ── Thumbnails ────────────────────────────────────────────────

def _png(width, height):
    buf = io.BytesIO()
    Image.new("RGB", (width, height), "#336699").save(buf, format="PNG")
    buf.seek(0)
    return FileStorage(stream=buf, filename="photo.png", content_type="image/png")


def test_upload_stores_smaller_variants_next_to_the_original(app, tmp_path, monkeypatch):
    for name in ("S3_ENDPOINT_URL", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.setitem(app.config, name, "")
    saved = {}
    monkeypatch.setattr(storage, "_save_bytes_to_disk",
                        lambda data, name: saved.setdefault(name, data) and f"/static/uploads/{name}")

    url = storage.save_image(_png(1200, 1600))

    original = min(saved, key=len)
    assert url == f"/static/uploads/{original}"
    assert set(saved) == {
        original, original.replace(".webp", "_480.webp"), original.replace(".webp", "_800.webp"),
    }
    # Same shape as the original, at the promised widths.
    assert Image.open(io.BytesIO(saved[original.replace(".webp", "_480.webp")])).size == (480, 640)
    assert Image.open(io.BytesIO(saved[original.replace(".webp", "_800.webp")])).size == (800, 1067)


def test_small_images_get_no_thumbnail(app, monkeypatch):
    for _name in ("S3_ENDPOINT_URL", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.setitem(app.config, _name, "")
    saved = {}
    monkeypatch.setattr(storage, "_save_bytes_to_disk",
                        lambda data, name: saved.setdefault(name, data) and f"/static/uploads/{name}")

    storage.save_image(_png(300, 400))

    assert len(saved) == 1


def test_a_failed_thumbnail_does_not_fail_the_upload(app, monkeypatch):
    for _name in ("S3_ENDPOINT_URL", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.setitem(app.config, _name, "")
    monkeypatch.setattr(storage, "_save_bytes_to_disk", lambda data, name: f"/static/uploads/{name}")

    def _boom(_bytes, _width):
        raise OSError("disk full")

    monkeypatch.setattr(storage, "make_variant", _boom)

    assert storage.save_image(_png(1200, 1600)).endswith(".webp")
