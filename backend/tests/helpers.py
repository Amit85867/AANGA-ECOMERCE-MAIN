"""Auth headers shared by the route tests."""
import uuid

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.admin import Admin

ADMIN_PASSWORD = "AdminPass123!"


def customer_headers(user):
    return {"Authorization": f"Bearer {create_access_token(identity=str(user.id))}"}


def make_admin(role="master", **kw):
    admin = Admin(
        email=kw.get("email") or f"{role}-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=generate_password_hash(kw.get("password", ADMIN_PASSWORD)),
        full_name=kw.get("full_name", "Test Admin"),
        role=role,
    )
    db.session.add(admin)
    db.session.commit()
    return admin


def admin_headers(admin=None, role="master"):
    admin = admin or make_admin(role=role)
    token = create_access_token(
        identity=str(admin.id),
        additional_claims={"actor": "admin", "role": admin.role},
    )
    return {"Authorization": f"Bearer {token}"}
