"""Public CMS endpoints — serve active banners, announcements, and settings."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify
from sqlalchemy import or_, and_

from app.models.cms import HeroBanner, Announcement, PromoBanner, SiteSetting, Testimonial, Feature
from app.services import campaigns, store_settings
from app.services.cache import cached_view

cms_bp = Blueprint("cms", __name__, url_prefix="/api/cms")


def _is_scheduled_active():
    now = datetime.now(timezone.utc)
    return and_(
        or_(HeroBanner.starts_at.is_(None), HeroBanner.starts_at <= now),
        or_(HeroBanner.ends_at.is_(None), HeroBanner.ends_at >= now),
    )


@cms_bp.route("/banners", methods=["GET"])
@cached_view(60)
def public_banners():
    now = datetime.now(timezone.utc)
    # While a campaign is live its own slides replace the usual ones (if it
    # has any); the rest of the time campaign slides are never shown.
    live = campaigns.live()
    owner = None
    if live and HeroBanner.query.filter_by(campaign_id=live["id"], is_active=True).first():
        owner = live["id"]
    banners = HeroBanner.query.filter(
        HeroBanner.campaign_id == owner if owner else HeroBanner.campaign_id.is_(None),
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
            "pill_label": b.pill_label,
            "pill_value": b.pill_value,
            "chip_value": b.chip_value,
            "chip_label": b.chip_label,
        }
        for b in banners
    ]), 200


@cms_bp.route("/announcements", methods=["GET"])
@cached_view(60)
def public_announcements():
    live = campaigns.live()
    if live and live["announcement"]:
        # One festive line for the length of the campaign, in the campaign's
        # accent, instead of the everyday announcements.
        accent = live["decoration"]
        return jsonify(announcements=[{
            "id": f"campaign-{live['id']}",
            **live["announcement"],
            "bg_color": "#0A0A0A",
            "text_color": "#ffffff",
            "highlight_color": accent["accent"],
        }]), 200

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
@cached_view(60)
def public_promos():
    now = datetime.now(timezone.utc)
    live = campaigns.live()
    owner = None
    if live and PromoBanner.query.filter_by(campaign_id=live["id"], is_active=True).first():
        owner = live["id"]
    promos = PromoBanner.query.filter(
        PromoBanner.campaign_id == owner if owner else PromoBanner.campaign_id.is_(None),
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
@cached_view(60)
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
@cached_view(60)
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
@cached_view(60)
def public_settings():
    settings = {s.key: s.value for s in SiteSetting.query.all()}
    # The store's own fields always have a value, even before anyone saves them.
    settings.update(store_settings.all_values())
    return jsonify(settings=settings), 200


@cms_bp.route("/features-available", methods=["GET"])
@cached_view(60)
def available_features():
    """Which optional parts of the store are switched on.

    The storefront hides what is not configured — a "Pay online" option that
    can only fail, a "Continue with Google" button with no client id — instead
    of offering it and showing an error. Booleans only: nothing here reveals a
    key, only that one is present.
    """
    import os

    from flask import current_app

    from app.routes.auth import phone_login_available

    def has(name):
        return bool((os.environ.get(name) or "").strip())

    return jsonify(
        online_payments=has("RAZORPAY_KEY_ID") and has("RAZORPAY_KEY_SECRET"),
        delivery_check=(
            has("SHIPROCKET_EMAIL") and has("SHIPROCKET_PASSWORD")
            and has("SHIPROCKET_PICKUP_PINCODE")
        ),
        google_login=has("GOOGLE_CLIENT_ID"),
        cash_on_delivery=store_settings.flag("cod_enabled"),
        # Only true when a real provider is configured: in development the
        # endpoint works for testing, but the storefront should look the way
        # production will.
        phone_login=bool(current_app.config.get("SMS_PROVIDER")) and phone_login_available(),
    ), 200
