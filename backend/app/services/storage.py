"""Image storage backends + optimisation.

Local disk is fine for development, but on Render/Railway the filesystem is
**ephemeral** — anything written to `static/uploads` is destroyed on the next
deploy, which would silently break every product image. So production uploads
go to Supabase Storage (an S3-compatible object store on the project you
already have).

Every upload is also optimised before it is stored: resized to a sane maximum
dimension and re-encoded as WebP. The raw Stitch product shots were ~930 KB
each; after this they are typically 40-80 KB with no visible quality loss,
which is the difference between a fast storefront and a painful one on mobile.

The storage backend is chosen from configuration:
  * SUPABASE_URL + SUPABASE_SERVICE_KEY set -> Supabase Storage
  * otherwise                               -> local disk

Uses the Storage REST API directly (like the Razorpay integration) so no extra
SDK dependency is needed.
"""
import io
import os
import uuid

import requests
from flask import current_app
from PIL import Image, ImageOps

# Longest edge in pixels. Large enough for a detail-page zoom, small enough to
# keep files light.
MAX_DIMENSION = 1400
WEBP_QUALITY = 80

# Animated GIFs are passed through untouched (re-encoding them to static WebP
# would drop the animation); everything else becomes WebP.
PASSTHROUGH_EXTS = {"gif"}

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


def optimize_image(file_storage):
    """Return (bytes, ext, content_type) for an uploaded image.

    Static images are downscaled and re-encoded as WebP. Animated GIFs (and
    anything Pillow can't open) are returned unchanged so we never lose data.
    """
    original_ext = file_storage.filename.rsplit(".", 1)[1].lower()
    file_storage.stream.seek(0)
    raw = file_storage.stream.read()

    if original_ext in PASSTHROUGH_EXTS:
        return raw, original_ext, CONTENT_TYPES.get(original_ext, "application/octet-stream")

    try:
        img = Image.open(io.BytesIO(raw))
        # Multi-frame (animated) images: leave them alone.
        if getattr(img, "n_frames", 1) > 1:
            return raw, original_ext, CONTENT_TYPES.get(original_ext, "application/octet-stream")

        img = ImageOps.exif_transpose(img)  # honour camera orientation

        # WebP supports alpha; flatten exotic modes to something it can encode.
        if img.mode in ("P", "LA"):
            img = img.convert("RGBA")
        elif img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")

        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=WEBP_QUALITY, method=6)
        return buf.getvalue(), "webp", "image/webp"
    except Exception as exc:  # pragma: no cover - defensive
        current_app.logger.warning("Image optimisation failed, storing original: %s", exc)
        return raw, original_ext, CONTENT_TYPES.get(original_ext, "application/octet-stream")


def save_image(file_storage):
    """Optimise and persist an uploaded image; return its public URL."""
    data, ext, content_type = optimize_image(file_storage)
    filename = f"{uuid.uuid4().hex}.{ext}"

    if is_object_storage_configured():
        return _save_bytes_to_supabase(data, filename, content_type)
    return _save_bytes_to_disk(data, filename)


def _save_bytes_to_disk(data, filename):
    upload_dir = os.path.join(current_app.root_path, "..", "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    with open(os.path.join(upload_dir, filename), "wb") as fh:
        fh.write(data)
    return f"/static/uploads/{filename}"


def _save_bytes_to_supabase(data, filename, content_type):
    base = current_app.config["SUPABASE_URL"].rstrip("/")
    key = current_app.config["SUPABASE_SERVICE_KEY"]
    bucket = current_app.config.get("SUPABASE_STORAGE_BUCKET", "product-images")

    try:
        resp = requests.post(
            f"{base}/storage/v1/object/{bucket}/{filename}",
            data=data,
            headers={
                "Authorization": f"Bearer {key}",
                "apikey": key,
                "Content-Type": content_type,
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
