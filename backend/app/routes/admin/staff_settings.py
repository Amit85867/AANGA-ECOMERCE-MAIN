"""Owner-only: staff accounts, store settings, demo content."""
import secrets

from flask import jsonify, request
from flask_jwt_extended import get_jwt
from marshmallow import Schema, ValidationError, fields, validate
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.admin import Admin
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.services import audit, demo, permissions, store_settings

_ROLE = validate.OneOf(list(permissions.ROLES))


class StaffInviteIn(Schema):
    email = fields.Email(required=True)
    full_name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    role = fields.Str(load_default=permissions.STAFF, validate=_ROLE)


class StaffUpdateIn(Schema):
    full_name = fields.Str(validate=validate.Length(min=2, max=120))
    role = fields.Str(validate=_ROLE)
    is_active = fields.Bool()
    reset_password = fields.Bool()


_invite_in = StaffInviteIn()
_update_in = StaffUpdateIn()


def _staff_dict(admin):
    return {
        "id": str(admin.id),
        "email": admin.email,
        "full_name": admin.full_name,
        "role": admin.role,
        "role_label": permissions.ROLE_LABELS.get(admin.role, admin.role),
        "is_active": admin.is_active,
        "is_demo": admin.is_demo,
        "created_at": admin.created_at.isoformat() if admin.created_at else None,
        "last_login": admin.last_login.isoformat() if admin.last_login else None,
    }


def _temporary_password():
    # Shown to the Owner once, to pass on. Long enough not to be guessable.
    return secrets.token_urlsafe(12)


def _other_active_owner_exists(admin):
    return Admin.query.filter(
        Admin.role == permissions.OWNER, Admin.is_active.is_(True), Admin.id != admin.id
    ).first() is not None


# ── Staff ────────────────────────────────────────────────────

@admin_bp.route("/staff", methods=["GET"])
@admin_required
def list_staff():
    staff = Admin.query.order_by(Admin.created_at).all()
    return jsonify(
        staff=[_staff_dict(a) for a in staff],
        roles=[
            {"value": role, "label": permissions.ROLE_LABELS[role], "areas": permissions.allowed_areas(role)}
            for role in permissions.ROLES
        ],
    ), 200


@admin_bp.route("/staff", methods=["POST"])
@admin_required
def invite_staff():
    """Create an account with a one-time password for the Owner to pass on."""
    try:
        data = _invite_in.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    email = data["email"].strip().lower()
    if Admin.query.filter(db.func.lower(Admin.email) == email).first():
        return jsonify(errors={"email": ["Someone on the team already uses this email."]}), 409

    password = _temporary_password()
    admin = Admin(
        email=email, full_name=data["full_name"].strip(), role=data["role"],
        password_hash=generate_password_hash(password), created_by=get_jwt()["sub"],
    )
    db.session.add(admin)
    db.session.flush()
    audit.annotate(
        entity="staff",
        summary=f"Added {admin.email} as {permissions.ROLE_LABELS[admin.role]}",
        changes={"email": admin.email, "role": admin.role},
    )
    db.session.commit()
    return jsonify(staff=_staff_dict(admin), temporary_password=password), 201


@admin_bp.route("/staff/<staff_id>", methods=["PATCH"])
@admin_required
def update_staff(staff_id):
    try:
        data = _update_in.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(errors=err.messages), 422
    if not data:
        return jsonify(error="Nothing to change."), 422

    admin = _find(staff_id)
    if admin is None:
        return jsonify(error="Staff member not found"), 404

    me = str(get_jwt()["sub"]) == str(admin.id)
    demoting = "role" in data and admin.role == permissions.OWNER and data["role"] != permissions.OWNER
    deactivating = data.get("is_active") is False and admin.is_active
    if (demoting or deactivating) and admin.role == permissions.OWNER and not _other_active_owner_exists(admin):
        return jsonify(error="This is the only Owner. Make someone else an Owner first."), 409
    if me and deactivating:
        return jsonify(error="You cannot deactivate your own account."), 409

    changes = {}
    for key in ("full_name", "role", "is_active"):
        if key in data and getattr(admin, key) != data[key]:
            changes[key] = {"from": getattr(admin, key), "to": data[key]}
            setattr(admin, key, data[key])

    password = None
    if data.get("reset_password"):
        password = _temporary_password()
        admin.password_hash = generate_password_hash(password)
        changes["password"] = "reset"

    audit.annotate(
        entity="staff",
        summary=f"Staff {admin.email}: " + (", ".join(
            "password reset" if k == "password" else f"{k} → {v['to']}" for k, v in changes.items()
        ) or "no change"),
        changes={"email": admin.email, **{k: v for k, v in changes.items() if k != "password"},
                 "password_reset": bool(password)},
    )
    db.session.commit()
    body = {"staff": _staff_dict(admin)}
    if password:
        body["temporary_password"] = password
    return jsonify(body), 200


@admin_bp.route("/staff/<staff_id>", methods=["DELETE"])
@admin_required
def remove_staff(staff_id):
    admin = _find(staff_id)
    if admin is None:
        return jsonify(error="Staff member not found"), 404
    if str(get_jwt()["sub"]) == str(admin.id):
        return jsonify(error="You cannot remove your own account."), 409
    if admin.role == permissions.OWNER and not _other_active_owner_exists(admin):
        return jsonify(error="This is the only Owner and cannot be removed."), 409

    audit.annotate(
        entity="staff", summary=f"Removed {admin.email} ({permissions.ROLE_LABELS.get(admin.role, admin.role)})",
        changes={"email": admin.email, "role": admin.role},
    )
    db.session.delete(admin)
    db.session.commit()
    return jsonify(message="Staff member removed"), 200


def _find(staff_id):
    try:
        return db.session.get(Admin, staff_id)
    except Exception:  # noqa: BLE001 - not a UUID
        db.session.rollback()
        return None


# ── Store settings ───────────────────────────────────────────

def _settings_body():
    values = store_settings.all_values()
    groups = []
    for field in store_settings.FIELDS:
        if not groups or groups[-1]["name"] != field.group:
            groups.append({"name": field.group, "fields": []})
        groups[-1]["fields"].append({
            "key": field.key, "label": field.label, "type": field.kind, "help": field.help,
            "value": values.get(field.key, field.default),
        })
    return {"groups": groups}


@admin_bp.route("/settings", methods=["GET"])
@admin_required
def get_store_settings():
    return jsonify(_settings_body()), 200


@admin_bp.route("/settings", methods=["PUT"])
@admin_required
def save_store_settings():
    values = (request.get_json(silent=True) or {}).get("values")
    if not isinstance(values, dict) or not values:
        return jsonify(error="Nothing to save."), 422

    changes, errors = store_settings.save(values)
    if errors:
        db.session.rollback()
        return jsonify(errors=errors), 422

    audit.annotate(
        entity="settings",
        summary="Store settings: " + (", ".join(
            store_settings.BY_KEY[k].label for k in changes) or "saved, nothing changed"),
        changes=changes,
    )
    db.session.commit()
    # The after_request hook drops the cache; do it now too so the body below
    # is read back fresh.
    from app.services import cache
    cache.invalidate()
    return jsonify(_settings_body()), 200


# ── Demo content ─────────────────────────────────────────────

CONFIRM_PHRASE = "REMOVE DEMO"


@admin_bp.route("/demo", methods=["GET"])
@admin_required
def demo_summary():
    counts = demo.summary()
    return jsonify(counts=counts, total=sum(counts.values()), confirm_phrase=CONFIRM_PHRASE), 200


@admin_bp.route("/demo/remove", methods=["POST"])
@admin_required
def demo_remove():
    if (request.get_json(silent=True) or {}).get("confirm") != CONFIRM_PHRASE:
        return jsonify(error=f"Type {CONFIRM_PHRASE} to confirm."), 422

    removed = demo.remove_all(keep_admin_id=get_jwt()["sub"])
    kept = removed.pop("kept")
    audit.annotate(
        entity="demo",
        summary="Removed demo content: " + ", ".join(f"{n} {kind}" for kind, n in removed.items() if n),
        changes={"removed": removed, "kept": kept},
    )
    db.session.commit()
    return jsonify(removed=removed, kept=kept), 200
