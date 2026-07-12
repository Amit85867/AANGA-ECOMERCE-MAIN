"""Public CMS endpoints — serve active banners, announcements, and settings."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify
from sqlalchemy import or_, and_

from app.models.cms import HeroBanner, Announcement, PromoBanner, SiteSetting, Testimonial, Feature

cms_bp = Blueprint("cms", __name__, url_prefix="/api/cms")


def _is_scheduled_active():
    now = datetime.now(timezone.utc)
    return and_(
        or_(HeroBanner.starts_at.is_(None), HeroBanner.starts_at <= now),
        or_(HeroBanner.ends_at.is_(None), HeroBanner.ends_at >= now),
    )


@cms_bp.route("/banners", methods=["GET"])
def public_banners():
    now = datetime.now(timezone.utc)
    banners = HeroBanner.query.filter(
        HeroBanner.is_active.is_(True),
        or_(HeroBanner.starts_at.is_(None), HeroBanner.starts_at <= now),
        or_(HeroBanner.ends_at.is_(None), HeroBanner.ends_at >= now),
    ).order_by(HeroBanner.sort_order).all()

    return jsonify(banners=[
        {
            "id": b.id,
            "title": b.title,
            "subtitle": b.subtitle,
            "description": b.description,
            "image_url": b.image_url,
            "mobile_image_url": b.mobile_image_url,
            "link_url": b.link_url,
            "link_text": b.link_text,
            "secondary_link_url": b.secondary_link_url,
            "secondary_link_text": b.secondary_link_text,
        }
        for b in banners
    ]), 200


@cms_bp.route("/announcements", methods=["GET"])
def public_announcements():
    now = datetime.now(timezone.utc)
    items = Announcement.query.filter(
        Announcement.is_active.is_(True),
        or_(Announcement.starts_at.is_(None), Announcement.starts_at <= now),
        or_(Announcement.ends_at.is_(None), Announcement.ends_at >= now),
    ).order_by(Announcement.sort_order).all()

    return jsonify(announcements=[
        {
            "id": a.id,
            "text": a.text,
            "highlight_text": a.highlight_text,
            "link_url": a.link_url,
            "link_text": a.link_text,
            "bg_color": a.bg_color,
            "text_color": a.text_color,
            "highlight_color": a.highlight_color,
        }
        for a in items
    ]), 200


@cms_bp.route("/promo-banners", methods=["GET"])
def public_promos():
    now = datetime.now(timezone.utc)
    promos = PromoBanner.query.filter(
        PromoBanner.is_active.is_(True),
        or_(PromoBanner.starts_at.is_(None), PromoBanner.starts_at <= now),
        or_(PromoBanner.ends_at.is_(None), PromoBanner.ends_at >= now),
    ).order_by(PromoBanner.sort_order).all()

    return jsonify(promo_banners=[
        {
            "id": p.id,
            "title": p.title,
            "subtitle": p.subtitle,
            "description": p.description,
            "badge_text": p.badge_text,
            "image_url": p.image_url,
            "link_url": p.link_url,
            "link_text": p.link_text,
            "items": p.items,
        }
        for p in promos
    ]), 200


@cms_bp.route("/testimonials", methods=["GET"])
def public_testimonials():
    items = Testimonial.query.filter(
        Testimonial.is_active.is_(True),
    ).order_by(Testimonial.sort_order, Testimonial.created_at.desc()).all()

    return jsonify(testimonials=[
        {
            "id": t.id,
            "name": t.name,
            "location": t.location,
            "rating": t.rating,
            "quote": t.quote,
            "avatar_url": t.avatar_url,
        }
        for t in items
    ]), 200


@cms_bp.route("/features", methods=["GET"])
def public_features():
    items = Feature.query.filter(
        Feature.is_active.is_(True),
    ).order_by(Feature.sort_order, Feature.created_at.desc()).all()

    return jsonify(features=[
        {
            "id": f.id,
            "icon": f.icon,
            "title": f.title,
            "description": f.description,
            "image_url": f.image_url,
        }
        for f in items
    ]), 200


@cms_bp.route("/settings", methods=["GET"])
def public_settings():
    settings = SiteSetting.query.all()
    return jsonify(
        settings={s.key: s.value for s in settings}
    ), 200
