"""Admin auth decorators."""
from functools import wraps

from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt

from app.extensions import db
from app.models.admin import Admin


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("type") != "admin":
            return jsonify(error="Admin access required"), 403
        admin = db.session.get(Admin, claims["sub"])
        if not admin or not admin.is_active:
            return jsonify(error="Admin account not found or deactivated"), 403
        return fn(*args, **kwargs)
    return wrapper


def master_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt()
        if claims.get("type") != "admin" or claims.get("role") != "master":
            return jsonify(error="Master admin access required"), 403
        admin = db.session.get(Admin, claims["sub"])
        if not admin or not admin.is_active:
            return jsonify(error="Admin account not found or deactivated"), 403
        return fn(*args, **kwargs)
    return wrapper
