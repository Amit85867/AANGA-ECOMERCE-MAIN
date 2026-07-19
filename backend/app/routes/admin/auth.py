"""Admin auth: login, refresh, logout, create admin, list admins, delete admin."""
from datetime import datetime, timezone

from flask import request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_jwt,
)
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db, limiter
from app.models.admin import Admin
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required, master_required
from app.schemas.admin import AdminLoginIn, AdminCreateIn, AdminOut

_login_in = AdminLoginIn()
_create_in = AdminCreateIn()
_admin_out = AdminOut()
_admin_list_out = AdminOut(many=True)


# The admin session uses its own cookie name AND path so signing into the admin
# panel never disturbs a customer session in the same browser (and vice versa).
# flask_jwt_extended's set_refresh_cookies() only knows the single global cookie
# path, so these cookies are written explicitly.
ADMIN_REFRESH_COOKIE = "aanga_admin_refresh"
ADMIN_CSRF_COOKIE = "csrf_admin_refresh"
# The secret cookie is tightly scoped so it only ever rides along with admin
# auth calls. Its CSRF companion must live at "/" instead, because
# document.cookie only exposes cookies matching the current page path and the
# admin UI runs on /admin/* — same split flask_jwt_extended uses.
ADMIN_COOKIE_PATH = "/api/admin/auth"
ADMIN_CSRF_COOKIE_PATH = "/"


def _admin_claims(admin):
    # NOTE: "actor" — never "type", which flask_jwt_extended reserves for
    # access/refresh. Overwriting it would let a refresh token be used as an
    # access token.
    return {"actor": "admin", "role": admin.role}


def _cookie_kwargs(path):
    cfg = current_app.config
    return {
        "path": path,
        "secure": cfg.get("JWT_COOKIE_SECURE", True),
        "samesite": cfg.get("JWT_COOKIE_SAMESITE", "None"),
    }


def _set_admin_refresh_cookie(resp, admin):
    token = create_refresh_token(
        identity=str(admin.id), additional_claims=_admin_claims(admin)
    )
    max_age = int(current_app.config["JWT_REFRESH_TOKEN_EXPIRES"].total_seconds())
    resp.set_cookie(
        ADMIN_REFRESH_COOKIE, token, httponly=True, max_age=max_age,
        **_cookie_kwargs(ADMIN_COOKIE_PATH),
    )
    # Readable companion cookie for double-submit CSRF.
    csrf = decode_token(token).get("csrf")
    if csrf:
        resp.set_cookie(
            ADMIN_CSRF_COOKIE, csrf, httponly=False, max_age=max_age,
            **_cookie_kwargs(ADMIN_CSRF_COOKIE_PATH),
        )


def _clear_admin_cookies(resp):
    resp.delete_cookie(
        ADMIN_REFRESH_COOKIE, httponly=True, **_cookie_kwargs(ADMIN_COOKIE_PATH)
    )
    resp.delete_cookie(ADMIN_CSRF_COOKIE, **_cookie_kwargs(ADMIN_CSRF_COOKIE_PATH))


def _admin_auth_response(admin, status=200):
    """Access token in the body (kept in memory), refresh token in a cookie."""
    body = {
        "access_token": create_access_token(
            identity=str(admin.id), additional_claims=_admin_claims(admin)
        ),
        "admin": _admin_out.dump(admin),
    }
    resp = jsonify(body)
    _set_admin_refresh_cookie(resp, admin)
    return resp, status


@admin_bp.route("/auth/login", methods=["POST"])
@limiter.limit("5 per 15 minutes")
def admin_login():
    try:
        data = _login_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    admin = Admin.query.filter_by(email=data["email"]).first()
    if not admin or not check_password_hash(admin.password_hash, data["password"]):
        return jsonify(error="Invalid email or password"), 401

    if not admin.is_active:
        return jsonify(error="Account is deactivated"), 403

    admin.last_login = datetime.now(timezone.utc)
    db.session.commit()

    return _admin_auth_response(admin)


@admin_bp.route("/auth/refresh", methods=["POST"])
@limiter.limit("60 per hour")
def admin_refresh():
    """Mint a new admin access token from the httpOnly admin refresh cookie.

    Verified explicitly (rather than via @jwt_required(refresh=True)) because
    the admin session deliberately uses its own cookie name and path, which the
    extension's global cookie config does not know about.
    """
    token = request.cookies.get(ADMIN_REFRESH_COOKIE)
    if not token:
        return jsonify(error="Authorization required"), 401

    try:
        decoded = decode_token(token)  # verifies signature + expiry
    except Exception:
        return jsonify(error="Invalid token"), 401

    # Must be a genuine refresh token belonging to an admin.
    if decoded.get("type") != "refresh" or decoded.get("actor") != "admin":
        return jsonify(error="Invalid token"), 401

    # Double-submit CSRF: the header must match the token's csrf claim.
    expected_csrf = decoded.get("csrf")
    if expected_csrf and request.headers.get("X-CSRF-TOKEN") != expected_csrf:
        return jsonify(error="Missing or invalid CSRF token"), 401

    admin = db.session.get(Admin, decoded["sub"])
    if not admin or not admin.is_active:
        resp = jsonify(error="Admin account not found or deactivated")
        _clear_admin_cookies(resp)
        return resp, 401

    resp = jsonify(
        access_token=create_access_token(
            identity=str(admin.id), additional_claims=_admin_claims(admin)
        )
    )
    _set_admin_refresh_cookie(resp, admin)  # rotate on every use
    return resp, 200


@admin_bp.route("/auth/logout", methods=["POST"])
def admin_logout():
    resp = jsonify(message="Logged out")
    _clear_admin_cookies(resp)
    return resp, 200


@admin_bp.route("/auth/me", methods=["GET"])
@admin_required
def admin_me():
    claims = get_jwt()
    admin = db.session.get(Admin, claims["sub"])
    return jsonify(_admin_out.dump(admin)), 200


@admin_bp.route("/auth/admins", methods=["POST"])
@master_required
def create_admin():
    try:
        data = _create_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    if Admin.query.filter_by(email=data["email"]).first():
        return jsonify(error="Email already exists"), 409

    claims = get_jwt()
    admin = Admin(
        email=data["email"],
        password_hash=generate_password_hash(data["password"]),
        full_name=data["full_name"],
        role=data.get("role", "staff"),
        created_by=claims["sub"],
    )
    db.session.add(admin)
    db.session.commit()

    return jsonify(_admin_out.dump(admin)), 201


@admin_bp.route("/auth/admins", methods=["GET"])
@master_required
def list_admins():
    admins = Admin.query.order_by(Admin.created_at).all()
    return jsonify(admins=_admin_list_out.dump(admins)), 200


@admin_bp.route("/auth/admins/<admin_id>", methods=["DELETE"])
@master_required
def delete_admin(admin_id):
    claims = get_jwt()
    if claims["sub"] == admin_id:
        return jsonify(error="Cannot delete yourself"), 422

    admin = db.session.get(Admin, admin_id)
    if not admin:
        return jsonify(error="Admin not found"), 404

    db.session.delete(admin)
    db.session.commit()

    return jsonify(message="Admin deleted"), 200
