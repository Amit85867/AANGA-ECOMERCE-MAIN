"""Who may use which part of the admin API.

Three roles:

* ``master``  — shown as **Owner**. Everything.
* ``manager`` — runs the shop day to day: catalogue, orders, customers, all
  storefront content, collections, campaigns, coupons. Not store settings,
  staff, maintenance mode or demo-content removal.
* ``staff``   — catalogue and orders only.

Enforced once, for every admin route, by a ``before_request`` hook on the admin
blueprint (see :func:`init_app`). The area is taken from the URL —
``/api/admin/<area>/...`` — so a new route is covered the moment it is added,
and an area nobody listed here is Owner-only rather than open.
"""
from flask import jsonify, request
from flask_jwt_extended import get_jwt, verify_jwt_in_request

from app.extensions import db

OWNER = "master"
MANAGER = "manager"
STAFF = "staff"
ROLES = (OWNER, MANAGER, STAFF)
ROLE_LABELS = {OWNER: "Owner", MANAGER: "Manager", STAFF: "Staff"}

_ALL = {OWNER, MANAGER, STAFF}
_MANAGERS = {OWNER, MANAGER}
_OWNERS = {OWNER}

# First path segment after /api/admin/ -> roles allowed.
AREAS = {
    # catalogue and orders: everyone
    "dashboard": _ALL,
    "products": _ALL,
    "categories": _ALL,
    "orders": _ALL,
    "returns": _ALL,
    "upload": _ALL,
    "media": _ALL,
    # running the shop
    "users": _MANAGERS,
    "reviews": _MANAGERS,
    "coupons": _MANAGERS,
    "offers": _MANAGERS,
    "wholesale-inquiries": _MANAGERS,
    "contact-messages": _MANAGERS,
    "newsletter": _MANAGERS,
    "settlements": _MANAGERS,
    "banners": _MANAGERS,
    "announcements": _MANAGERS,
    "promo-banners": _MANAGERS,
    "testimonials": _MANAGERS,
    "features": _MANAGERS,
    "homepage": _MANAGERS,
    "navigation": _MANAGERS,
    "pages": _MANAGERS,
    "faq": _MANAGERS,
    "collections": _MANAGERS,
    "campaigns": _MANAGERS,
    "audit-log": _MANAGERS,
    # the business itself
    "settings": _OWNERS,
    "site-settings": _OWNERS,
    "staff": _OWNERS,
    "system": _OWNERS,
    "demo": _OWNERS,
}

# Sign-in plumbing every signed-in admin needs, whatever their role.
_OPEN_AUTH = {"login", "refresh", "logout", "me"}


def allowed_areas(role):
    """Areas a role may use — sent to the admin app so it can hide the rest."""
    return sorted(area for area, roles in AREAS.items() if role in roles)


def area_of(path):
    parts = [p for p in path.split("/") if p][2:]      # drop "api", "admin"
    if not parts:
        return None
    if parts[0] == "auth":
        if len(parts) > 1 and parts[1] in _OPEN_AUTH:
            return None
        return "staff"                                   # /auth/admins (older URL)
    return parts[0]


def init_app(admin_bp):
    @admin_bp.before_request
    def _enforce_role():
        if request.method == "OPTIONS":
            return None
        area = area_of(request.path)
        if area is None:
            return None
        try:
            verify_jwt_in_request()
            claims = get_jwt()
        except Exception:  # noqa: BLE001 - no valid token: the route's own decorator answers 401
            return None
        if claims.get("actor") != "admin":
            return None

        # The role is read from the database, not the token, so a change made
        # by the Owner applies to the very next request.
        from app.models.admin import Admin
        admin = db.session.get(Admin, claims["sub"])
        if not admin or not admin.is_active:
            return None

        if admin.role not in AREAS.get(area, _OWNERS):
            return jsonify(
                error=f"Your role ({ROLE_LABELS.get(admin.role, admin.role)}) "
                      "does not have access to this part of the dashboard.",
                area=area,
            ), 403
        return None
