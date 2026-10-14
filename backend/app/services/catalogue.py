"""Batched lookups for product listings.

A product card needs its primary image, the colours it comes in and its rating.
Fetching those per product is three queries a card — 36 for one shop page.
These helpers fetch them for a whole page of products in one query each.
"""
from sqlalchemy import func

from app.extensions import db
from app.models.catalogue import ProductImage, ProductVariant
from app.models.engagement import ProductReview


def primary_images(product_ids):
    """{product_id: image_url} for the products that have a primary image."""
    ids = list({pid for pid in product_ids if pid is not None})
    if not ids:
        return {}
    rows = (
        db.session.query(ProductImage.product_id, ProductImage.image_url)
        .filter(ProductImage.product_id.in_(ids), ProductImage.is_primary.is_(True))
        .all()
    )
    return dict(rows)


def colours(product_ids):
    """{product_id: [hex, ...]} — each distinct colour once, in a stable order."""
    ids = list(set(product_ids))
    if not ids:
        return {}
    rows = (
        db.session.query(ProductVariant.product_id, ProductVariant.color_hex)
        .filter(ProductVariant.product_id.in_(ids))
        .group_by(ProductVariant.product_id, ProductVariant.color_hex)
        .order_by(ProductVariant.product_id, func.min(ProductVariant.id))
        .all()
    )
    out = {}
    for product_id, colour in rows:
        out.setdefault(product_id, []).append(colour)
    return out


def ratings(product_ids):
    """{product_id: (average or None, count)}; products with no reviews are absent."""
    ids = list(set(product_ids))
    if not ids:
        return {}
    rows = (
        db.session.query(
            ProductReview.product_id,
            func.avg(ProductReview.rating),
            func.count(ProductReview.id),
        )
        .filter(ProductReview.product_id.in_(ids))
        .group_by(ProductReview.product_id)
        .all()
    )
    return {pid: (float(avg) if avg is not None else None, count) for pid, avg, count in rows}


def card_extras(products):
    """Everything a list of product cards needs beyond the product row itself.

    Returns ``{product_id: {"primary_image", "colors", "avg_rating",
    "review_count"}}`` using three queries regardless of how many products.
    """
    ids = [p.id for p in products]
    images, colour_map, rating_map = primary_images(ids), colours(ids), ratings(ids)
    extras = {}
    for pid in ids:
        average, count = rating_map.get(pid, (None, 0))
        extras[pid] = {
            "primary_image": images.get(pid),
            "colors": colour_map.get(pid, []),
            "avg_rating": round(average, 1) if average else None,
            "review_count": count,
        }
    return extras
