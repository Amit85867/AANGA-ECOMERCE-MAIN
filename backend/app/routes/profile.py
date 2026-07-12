"""User profile: get, update, change password."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db
from app.models.user import User
from app.schemas.user import UserOut, ProfileUpdateIn
from app.schemas.auth import ChangePasswordSchema

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")

_user_out = UserOut()
_update_in = ProfileUpdateIn()
_password_in = ChangePasswordSchema()


@profile_bp.route("", methods=["GET"])
@jwt_required()
def get_profile():
    user = db.session.get(User, get_jwt_identity())
    if not user:
        return jsonify(error="User not found"), 404
    return jsonify(_user_out.dump(user)), 200


@profile_bp.route("", methods=["PUT"])
@jwt_required()
def update_profile():
    try:
        data = _update_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    user = db.session.get(User, get_jwt_identity())
    if not user:
        return jsonify(error="User not found"), 404

    for key, val in data.items():
        setattr(user, key, val)

    db.session.commit()
    return jsonify(_user_out.dump(user)), 200


@profile_bp.route("/password", methods=["PUT"])
@jwt_required()
def change_password():
    try:
        data = _password_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    user = db.session.get(User, get_jwt_identity())
    if not user:
        return jsonify(error="User not found"), 404

    if not user.password_hash:
        return jsonify(error="Account uses social login — no password to change"), 422

    if not check_password_hash(user.password_hash, data["current_password"]):
        return jsonify(error="Current password is incorrect"), 401

    user.password_hash = generate_password_hash(data["new_password"])
    db.session.commit()

    return jsonify(message="Password updated"), 200
