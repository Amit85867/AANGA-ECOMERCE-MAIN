"""Image optimisation, and where the result is stored.

Local disk is fine for development, but on Render the filesystem is
**ephemeral** -- anything written to `static/uploads` is destroyed on the next
deploy, which would silently break every product image. So production uploads
go to S3-compatible object storage (Neon Object Storage; see
`app/services/objectstore.py`, which is not Neon-specific).

Every upload is also optimised before it is stored: resized to a sane maximum
dimension and re-encoded as WebP. The raw Stitch product shots were ~930 KB
each; after this they are typically 40-80 KB with no visible quality loss,
which is the difference between a fast storefront and a painful one on mobile.

The backend is chosen from configuration:
  * the S3_* settings are all present -> object storage
  * otherwise                         -> local disk (development only)
"""
import io
import os
import uuid

from flask import current_app
from PIL import Image, ImageOps

from app.services import objectstore

# Longest edge in pixels. Large enough for a detail-page zoom, small enough to
# keep files light.
MAX_DIMENSION = 1400
WEBP_QUALITY = 80

# Smaller copies stored next to every WebP upload as "<name>_<width>.webp".
# 480 suits a product card; 800 suits a full-width image on a phone. Sending
# either of those the 1400px original cost several times the bytes the screen
# could show. The storefront derives these URLs from the original's (see
# frontend/src/utils/image and the inline script in frontend/index.html), so
# the widths and the "_<width>" suffix are a contract across those three files.
VARIANT_WIDTHS = (480, 800)
THUMB_QUALITY = 78


def variant_name(filename, width):
    stem, ext = filename.rsplit(".", 1)
    return f"{stem}_{width}.{ext}"

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


# One exception type across both modules: callers do
# `except StorageError` around save_image(), and an S3 failure raised inside
# objectstore has to be caught by that same handler.
StorageError = objectstore.StorageError


class InvalidImage(StorageError):
    """The upload is not an image this store accepts (the caller answers 400)."""


# What the picture actually is, whatever its file name says.
ALLOWED_FORMATS = {"PNG", "JPEG", "WEBP", "GIF"}
# Far beyond any product photo; stops a tiny file that unpacks to gigabytes.
MAX_PIXELS = 50_000_000


def inspect_image(raw):
    """Check ``raw`` really is an acceptable image. Returns its format.

    A file is judged by its contents, never by its name: a page of HTML
    renamed photo.png, or an SVG with a script in it, is refused here.
    """
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            image_format = probe.format
            width, height = probe.size
            probe.verify()
    except Exception:  # noqa: BLE001 - anything Pillow cannot read is not an image
        raise InvalidImage("This file is not a valid image.") from None
    if image_format not in ALLOWED_FORMATS:
        raise InvalidImage("Use a JPG, PNG, WebP or GIF image.")
    if width * height > MAX_PIXELS:
        raise InvalidImage("This image is too large. Use one under 50 megapixels.")
    return image_format


def is_object_storage_configured(config=None):
    """True when uploads go to object storage rather than local disk."""
    return objectstore.is_configured(config)


def optimize_image(file_storage):
    """Return (bytes, ext, content_type) for an uploaded image.

    Static images are downscaled and re-encoded as WebP. Animated GIFs (and
    anything Pillow can't open) are returned unchanged so we never lose data.
    """
    original_ext = file_storage.filename.rsplit(".", 1)[1].lower()
    file_storage.stream.seek(0)
    raw = file_storage.stream.read()
    image_format = inspect_image(raw)
    # Stored under what it is, not what it was called.
    original_ext = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp", "GIF": "gif"}[image_format]

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


def make_variant(webp_bytes, width):
    """A `width`-wide WebP of an already-optimised image, or None when the
    original is no wider than that (the copy would only be a duplicate)."""
    img = Image.open(io.BytesIO(webp_bytes))
    if img.width <= width:
        return None
    height = round(img.height * width / img.width)
    small = img.resize((width, height), Image.LANCZOS)
    buf = io.BytesIO()
    small.save(buf, format="WEBP", quality=THUMB_QUALITY, method=6)
    return buf.getvalue()


def save_image(file_storage):
    """Optimise and persist an uploaded image; return its public URL.

    Smaller variants are stored alongside. They are best-effort: if one cannot
    be made or stored the upload still succeeds, and the storefront falls back
    to the full-size image.
    """
    data, ext, content_type = optimize_image(file_storage)
    filename = f"{uuid.uuid4().hex}.{ext}"
    remote = is_object_storage_configured()

    def put(name, payload):
        if remote:
            return objectstore.put_bytes(name, payload, content_type)
        return _save_bytes_to_disk(payload, name)

    url = put(filename, data)

    if ext == "webp":
        for width in VARIANT_WIDTHS:
            try:
                variant = make_variant(data, width)
                if variant:
                    put(variant_name(filename, width), variant)
            except Exception as exc:  # noqa: BLE001 - never fail an upload over a thumbnail
                current_app.logger.warning("Variant %s not stored for %s: %s", width, filename, exc)
    return url


def _save_bytes_to_disk(data, filename):
    upload_dir = os.path.join(current_app.root_path, "..", "static", "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    with open(os.path.join(upload_dir, filename), "wb") as fh:
        fh.write(data)
    return f"/static/uploads/{filename}"
