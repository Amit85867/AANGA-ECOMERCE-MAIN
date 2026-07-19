"""Admin auth: login, create admin, list admins, delete admin."""
from datetime import datetime, timezone

from flask import request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt
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


def _issue_admin_tokens(admin):
    identity = str(admin.id)
    extra = {"type": "admin", "role": admin.role}
    return {
        "access_token": create_access_token(identity=identity, additional_claims=extra),
        "refresh_token": create_refresh_token(identity=identity, additional_claims=extra),
        "admin": _admin_out.dump(admin),
    }


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

    return jsonify(_issue_admin_tokens(admin)), 200


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
