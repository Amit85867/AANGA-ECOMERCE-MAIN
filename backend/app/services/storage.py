"""Image storage backends.

Local disk is fine for development, but on Render/Railway the filesystem is
**ephemeral** — anything written to `static/uploads` is destroyed on the next
deploy, which would silently break every product image. So production uploads
go to Supabase Storage (an S3-compatible object store on the project you
already have).

The backend is chosen from configuration:
  * SUPABASE_URL + SUPABASE_SERVICE_KEY set -> Supabase Storage
  * otherwise                               -> local disk

Uses the Storage REST API directly (like the Razorpay integration) so no extra
SDK dependency is needed.
"""
import os
import uuid

import requests
from flask import current_app

CONTENT_TYPES = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}


class StorageError(Exception):
    """Raised when a file could not be persisted."""


def is_object_storage_configured(config=None):
    cfg = config if config is not None else current_app.config
    return bool(cfg.get("SUPABASE_URL") and cfg.get("SUPABASE_SERVICE_KEY"))


def generate_filename(original_name):
    ext = original_name.rsplit(".", 1)[1].lower()
    return f"{uuid.uuid4().hex}.{ext}", ext


def save_image(file_storage):
    """Persist an uploaded image and return its public URL."""
    filename, ext = generate_filename(file_storage.filename)

    if is_object_storage_configured():
        return _save_to_supabase(file_storage, filename, ext)
    return _save_to_disk(file_storage, filename)


def _save_to_disk(file_storage, filename):
    upload_dir = os.path.join(current_app.root_path, "..", "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_storage.save(os.path.join(upload_dir, filename))
    return f"/static/uploads/{filename}"


def _save_to_supabase(file_storage, filename, ext):
    base = current_app.config["SUPABASE_URL"].rstrip("/")
    key = current_app.config["SUPABASE_SERVICE_KEY"]
    bucket = current_app.config.get("SUPABASE_STORAGE_BUCKET", "product-images")

    file_storage.stream.seek(0)
    try:
        resp = requests.post(
            f"{base}/storage/v1/object/{bucket}/{filename}",
            data=file_storage.stream.read(),
            headers={
                "Authorization": f"Bearer {key}",
                "apikey": key,
                "Content-Type": CONTENT_TYPES.get(ext, "application/octet-stream"),
                "x-upsert": "true",
            },
            timeout=60,
        )
    except requests.RequestException as exc:
        raise StorageError(f"Could not reach object storage: {exc}") from exc

    if resp.status_code not in (200, 201):
        raise StorageError(
            f"Object storage rejected the upload ({resp.status_code}): {resp.text[:200]}"
        )

    # Bucket must be public for these URLs to resolve.
    return f"{base}/storage/v1/object/public/{bucket}/{filename}"
