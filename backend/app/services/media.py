"""Media library: every uploaded image, recorded once and reusable anywhere.

The picture itself goes through app/services/storage.py (Supabase Storage in
production, local disk in development) and is resized to the widths the
storefront's ``srcset`` asks for. This module adds the catalogue of what has
been uploaded and answers "where is this image used?" before one is deleted.
"""
import io
import os

import requests
from flask import current_app
from PIL import Image

from app.extensions import db
from app.models.owner import MediaAsset
from app.services import storage


def record(url, file_storage, uploaded_by=None, alt_text=None, source_note=None):
    """Add an uploaded file to the library. Never fails the upload."""
    width = height = size = None
    try:
        file_storage.stream.seek(0)
        raw = file_storage.stream.read()
        size = len(raw)
        with Image.open(io.BytesIO(raw)) as img:
            width, height = img.size
            if max(width, height) > storage.MAX_DIMENSION:      # stored copy is scaled down
                scale = storage.MAX_DIMENSION / max(width, height)
                width, height = round(width * scale), round(height * scale)
    except Exception:  # noqa: BLE001 - dimensions are a nicety
        pass
    asset = MediaAsset(
        url=url, filename=(file_storage.filename or "")[:200], width=width, height=height,
        size_bytes=size, uploaded_by=uploaded_by,
        alt_text=(alt_text or None), source_note=(source_note or None),
    )
    db.session.add(asset)
    return asset


def _columns():
    """Every column that can hold an image address: (label, model, column, name column, admin link)."""
    from app.models.catalogue import Category, Product, ProductImage
    from app.models.cms import Feature, HeroBanner, PromoBanner, SiteSetting, Testimonial
    from app.models.marketing import Offer
    from app.models.owner import CmsPage, Collection

    return [
        ("Product image", ProductImage, "image_url", None),
        ("Product share image", Product, "share_image_url", "name"),
        ("Category", Category, "image_url", "name"),
        ("Collection", Collection, "image_url", "name"),
        ("Collection share image", Collection, "share_image_url", "name"),
        ("Hero slide", HeroBanner, "image_url", "title"),
        ("Hero slide (mobile)", HeroBanner, "mobile_image_url", "title"),
        ("Promo banner", PromoBanner, "image_url", "title"),
        ("Testimonial photo", Testimonial, "avatar_url", "name"),
        ("Feature card", Feature, "image_url", "title"),
        ("Offer", Offer, "image_url", "title"),
        ("Page share image", CmsPage, "share_image_url", "title"),
        ("Store setting", SiteSetting, "value", "label"),
    ]


def usage(url):
    """Where an image is used: ``[{"where": "Hero slide", "name": "Diwali lights"}]``."""
    from app.models.catalogue import Product, ProductImage

    found = []
    for label, model, column, name_column in _columns():
        for row in model.query.filter(getattr(model, column) == url).limit(20).all():
            if model is ProductImage:
                product = db.session.get(Product, row.product_id)
                name = product.name if product else f"product #{row.product_id}"
            else:
                name = getattr(row, name_column, None) or f"#{row.id}"
            found.append({"where": label, "name": name})
    return found


def usage_counts(urls):
    """``{url: number of places it is used}`` for a page of the library."""
    counts = dict.fromkeys(urls, 0)
    if not urls:
        return counts
    for _label, model, column, _name in _columns():
        col = getattr(model, column)
        for (value,) in db.session.query(col).filter(col.in_(urls)).all():
            counts[value] += 1
    return counts


def delete_files(url):
    """Remove a stored image and its resized copies. Best effort."""
    filename = url.rsplit("/", 1)[-1]
    names = [filename] + [storage.variant_name(filename, w) for w in storage.VARIANT_WIDTHS]
    if url.startswith("/static/uploads/"):
        folder = os.path.join(current_app.root_path, "..", "static", "uploads")
        for name in names:
            try:
                os.remove(os.path.join(folder, name))
            except OSError:
                pass
        return
    if storage.is_object_storage_configured():
        base = current_app.config["SUPABASE_URL"].rstrip("/")
        key = current_app.config["SUPABASE_SERVICE_KEY"]
        bucket = current_app.config.get("SUPABASE_STORAGE_BUCKET", "product-images")
        if f"/object/public/{bucket}/" not in url:
            return
        try:
            requests.delete(
                f"{base}/storage/v1/object/{bucket}",
                json={"prefixes": names},
                headers={"Authorization": f"Bearer {key}", "apikey": key},
                timeout=30,
            )
        except requests.RequestException as exc:
            current_app.logger.warning("MEDIA_DELETE_FAILED url=%s err=%s", url, exc)
