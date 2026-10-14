"""S3-compatible object storage: the driver, and the media operations on it.

Everything here runs against an in-memory fake S3 rather than the network, so
the suite stays offline and deterministic. The real round trip is proved
separately by `scripts/migrate_images_to_objectstore.py` and by the storage
probe on the admin System Health page.

Covered, in the order the user meets them:
  upload -> replace -> delete when unused -> media library listing
plus the thing that has to be true for any of it: the app refuses to start in
production without storage, and no longer wants the old Supabase settings.
"""
import io

import pytest
from PIL import Image
from werkzeug.datastructures import FileStorage

from app import _validate_config
from app.services import media, objectstore, storage

S3_SETTINGS = {
    "S3_ENDPOINT_URL": "https://s3.example",
    "S3_BUCKET": "test-bucket",
    "S3_ACCESS_KEY_ID": "key",
    "S3_SECRET_ACCESS_KEY": "secret",
    "S3_REGION": "ap-southeast-1",
    "S3_PUBLIC_BASE_URL": "",
    "S3_FORCE_PATH_STYLE": True,
}


def _admin(client):
    from werkzeug.security import generate_password_hash

    from app.extensions import db as _db
    from app.models.admin import Admin

    password = "Storage-Admin-Pw1!"
    _db.session.add(Admin(
        email="storage-admin@example.com",
        password_hash=generate_password_hash(password),
        full_name="Storage Admin",
        role="master",
    ))
    _db.session.commit()
    resp = client.post("/api/admin/auth/login",
                       json={"email": "storage-admin@example.com", "password": password})
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


def _png(name="photo.png", size=(1600, 1200), colour=(90, 140, 200)):
    img = Image.new("RGB", size, colour)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return FileStorage(stream=buf, filename=name, content_type="image/png")


# ── Driver ────────────────────────────────────────────────────────────────
def test_public_url_is_path_style_endpoint_bucket_key(app, fake_s3):
    assert objectstore.public_base_url() == "https://s3.example/test-bucket"
    assert objectstore.public_url("abc.webp") == "https://s3.example/test-bucket/abc.webp"


def test_public_base_url_can_be_overridden_for_a_cdn(app, fake_s3, monkeypatch):
    monkeypatch.setitem(app.config, "S3_PUBLIC_BASE_URL", "https://cdn.example/img/")
    assert objectstore.public_url("abc.webp") == "https://cdn.example/img/abc.webp"


def test_key_for_url_only_claims_our_own_objects(app, fake_s3):
    assert objectstore.key_for_url("https://s3.example/test-bucket/a.webp") == "a.webp"
    # Another branch's bucket, or anywhere else, is not ours to touch. This is
    # what stops a dev environment deleting production's images after a branch
    # reset copies production's rows.
    assert objectstore.key_for_url("https://other.example/test-bucket/a.webp") is None
    assert objectstore.key_for_url("/static/uploads/a.webp") is None
    assert objectstore.key_for_url(None) is None


def test_put_sets_content_type_and_a_long_cache(app, fake_s3):
    objectstore.put_bytes("x.webp", b"bytes", "image/webp")

    assert fake_s3.content_type("x.webp") == "image/webp"
    # Names are content-addressed, so an immutable year is safe -- and without
    # an explicit Content-Type the browser downloads the file instead of
    # rendering it.
    assert "immutable" in fake_s3.cache_control("x.webp")


def test_missing_settings_are_reported_by_name(app, monkeypatch):
    for name in ("S3_BUCKET", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.setitem(app.config, name, "")
    monkeypatch.setitem(app.config, "S3_ENDPOINT_URL", "https://s3.example")
    monkeypatch.setitem(app.config, "S3_ACCESS_KEY_ID", "k")

    assert objectstore.is_configured() is False
    assert objectstore.missing_settings() == ["S3_BUCKET", "S3_SECRET_ACCESS_KEY"]


def test_delete_ignores_an_object_that_is_already_gone(app, fake_s3):
    objectstore.put_bytes("here.webp", b"x", "image/webp")

    # Deleting both the present and the absent key must not raise: deletion is
    # best effort and runs while a row is being removed.
    objectstore.delete_keys(["here.webp", "never-existed.webp"])

    assert objectstore.exists("here.webp") is False


# ── Upload ────────────────────────────────────────────────────────────────
def test_upload_stores_the_original_and_both_srcset_widths(app, fake_s3):
    url = storage.save_image(_png())
    name = url.rsplit("/", 1)[-1]

    assert url.startswith("https://s3.example/test-bucket/")
    stored = sorted(fake_s3.keys())
    assert name in stored
    for width in storage.VARIANT_WIDTHS:
        assert storage.variant_name(name, width) in stored
    assert len(stored) == 1 + len(storage.VARIANT_WIDTHS)


def test_upload_keeps_the_existing_resize_rules(app, fake_s3):
    """The move to Neon must not change how images are sized."""
    url = storage.save_image(_png(size=(2400, 1800)))
    name = url.rsplit("/", 1)[-1]

    original = Image.open(io.BytesIO(fake_s3.body(name)))
    assert max(original.size) == storage.MAX_DIMENSION

    for width in storage.VARIANT_WIDTHS:
        variant = Image.open(io.BytesIO(fake_s3.body(storage.variant_name(name, width))))
        assert variant.width == width


# ── Replace ───────────────────────────────────────────────────────────────
def test_replacing_an_image_writes_a_new_object_and_leaves_the_old(app, fake_s3):
    """Uploads are content-addressed, so a replacement never overwrites.

    The old object is removed by the delete-when-unused path, not by the
    upload -- otherwise a second row still using it would break.
    """
    first = storage.save_image(_png(colour=(10, 10, 10)))
    second = storage.save_image(_png(colour=(240, 240, 240)))

    assert first != second
    assert objectstore.key_for_url(first) in fake_s3.keys()
    assert objectstore.key_for_url(second) in fake_s3.keys()


# ── Delete when unused ────────────────────────────────────────────────────
def test_delete_files_removes_the_original_and_its_variants(app, fake_s3):
    url = storage.save_image(_png())
    assert len(fake_s3.keys()) == 1 + len(storage.VARIANT_WIDTHS)

    media.delete_files(url)

    assert fake_s3.keys() == []


def test_delete_files_leaves_another_bucket_alone(app, fake_s3):
    """A dev branch holds production's URLs after a reset; it must not delete them."""
    objectstore.put_bytes("mine.webp", b"x", "image/webp")

    media.delete_files("https://other.example/test-bucket/mine.webp")

    assert "mine.webp" in fake_s3.keys()


def test_delete_files_is_quiet_when_storage_is_not_configured(app, monkeypatch):
    for name in ("S3_ENDPOINT_URL", "S3_BUCKET", "S3_ACCESS_KEY_ID", "S3_SECRET_ACCESS_KEY"):
        monkeypatch.setitem(app.config, name, "")

    media.delete_files("https://s3.example/test-bucket/whatever.webp")  # must not raise


# ── Media library listing ─────────────────────────────────────────────────
def test_media_library_lists_an_upload_with_its_dimensions(app, client, fake_s3):
    headers = _admin(client)
    upload = _png(size=(1600, 1200))
    url = storage.save_image(upload)
    upload.stream.seek(0)
    media.record(url, upload)

    response = client.get("/api/admin/media", headers=headers)

    assert response.status_code == 200
    assets = response.get_json()["assets"]
    entry = next(a for a in assets if a["url"] == url)
    # Recorded against the stored copy, which is capped at MAX_DIMENSION.
    assert entry["width"] == storage.MAX_DIMENSION
    assert entry["height"] == round(storage.MAX_DIMENSION * 1200 / 1600)
    assert entry["url"].startswith("https://s3.example/test-bucket/")


def test_media_listing_reports_where_an_image_is_used(app, fake_s3):
    from app.extensions import db as _db
    from app.models.catalogue import Category

    url = storage.save_image(_png())
    _db.session.add(Category(name="Shirts", slug="shirts", image_url=url))
    _db.session.commit()

    assert media.usage_counts([url])[url] == 1
    assert any(u["where"] == "Category" for u in media.usage(url))


# ── Starting without the old Supabase settings ────────────────────────────
def _no_integration_env(monkeypatch):
    for name in ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET",
                 "SHIPROCKET_EMAIL", "SHIPROCKET_PASSWORD", "SHIPROCKET_PICKUP_PINCODE"):
        monkeypatch.delenv(name, raising=False)


def test_production_starts_with_s3_and_no_supabase_variables(monkeypatch):
    """The whole point of the move: Supabase settings are no longer required."""
    _no_integration_env(monkeypatch)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)

    class _App:
        config = dict(
            DEBUG=False, TESTING=False,
            SECRET_KEY="x" * 40, JWT_SECRET_KEY="y" * 40,
            SQLALCHEMY_DATABASE_URI="postgresql://u:p@host/db",
            RATELIMIT_ENABLED=True,
            **{k: v for k, v in S3_SETTINGS.items() if v != ""},
        )

    _validate_config(_App())  # must not raise


def test_production_still_refuses_when_storage_is_half_configured(monkeypatch):
    _no_integration_env(monkeypatch)
    class _App:
        config = dict(
            DEBUG=False, TESTING=False,
            SECRET_KEY="x" * 40, JWT_SECRET_KEY="y" * 40,
            SQLALCHEMY_DATABASE_URI="postgresql://u:p@host/db",
            RATELIMIT_ENABLED=True,
            S3_ENDPOINT_URL="https://s3.example",
            S3_BUCKET="b",
        )

    with pytest.raises(RuntimeError) as exc:
        _validate_config(_App())
    message = str(exc.value)
    assert "S3_ACCESS_KEY_ID" in message and "S3_SECRET_ACCESS_KEY" in message
