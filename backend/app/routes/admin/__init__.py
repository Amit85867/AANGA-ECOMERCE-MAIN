"""Admin API blueprint — mounted at /api/admin."""
from flask import Blueprint

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

from app.routes.admin import (  # noqa: E402, F401
    auth,
    dashboard,
    products,
    categories,
    orders,
    users,
    coupons,
    offers,
    inquiries,
    admin_newsletter,
    upload,
    banners,
    announcements,
    promo_banners,
    site_settings,
    shipping,
    testimonials,
    features,
)
