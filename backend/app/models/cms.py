"""CMS models: hero banners, announcements, promo banners, site settings."""
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.extensions import db


class HeroBanner(db.Model):
    __tablename__ = "hero_banners"

    id = db.Column(db.BigInteger, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    subtitle = db.Column(db.Text)
    description = db.Column(db.Text)
    image_url = db.Column(db.Text, nullable=False)
    mobile_image_url = db.Column(db.Text)
    link_url = db.Column(db.Text)
    link_text = db.Column(db.Text)
    secondary_link_url = db.Column(db.Text)
    secondary_link_text = db.Column(db.Text)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    starts_at = db.Column(db.DateTime(timezone=True))
    ends_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class Announcement(db.Model):
    __tablename__ = "announcements"

    id = db.Column(db.BigInteger, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    highlight_text = db.Column(db.Text)
    link_url = db.Column(db.Text)
    link_text = db.Column(db.Text)
    bg_color = db.Column(db.Text, nullable=False, default="#0A0A0A")
    text_color = db.Column(db.Text, nullable=False, default="#ffffff")
    highlight_color = db.Column(db.Text, nullable=False, default="#D4AF37")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    starts_at = db.Column(db.DateTime(timezone=True))
    ends_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())


class PromoBanner(db.Model):
    __tablename__ = "promo_banners"

    id = db.Column(db.BigInteger, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    subtitle = db.Column(db.Text)
    description = db.Column(db.Text)
    badge_text = db.Column(db.Text)
    image_url = db.Column(db.Text)
    link_url = db.Column(db.Text)
    link_text = db.Column(db.Text)
    items = db.Column(JSONB)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    starts_at = db.Column(db.DateTime(timezone=True))
    ends_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())


class Testimonial(db.Model):
    __tablename__ = "testimonials"

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    location = db.Column(db.Text)
    rating = db.Column(db.SmallInteger, nullable=False, default=5)
    quote = db.Column(db.Text, nullable=False)
    avatar_url = db.Column(db.Text)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())


class Feature(db.Model):
    __tablename__ = "features"

    id = db.Column(db.BigInteger, primary_key=True)
    icon = db.Column(db.Text)  # Tabler icon name, e.g. "shield-check"
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.Text)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())


class SiteSetting(db.Model):
    __tablename__ = "site_settings"

    id = db.Column(db.BigInteger, primary_key=True)
    key = db.Column(db.Text, nullable=False, unique=True)
    value = db.Column(db.Text, nullable=False, default="")
    label = db.Column(db.Text)
    group_name = db.Column(db.Text, nullable=False, default="general")
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
