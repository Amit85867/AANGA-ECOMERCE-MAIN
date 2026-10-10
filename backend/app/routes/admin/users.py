"""Admin user management: list, detail, toggle active."""
from flask import request, jsonify
from marshmallow import Schema, ValidationError, fields, validate
from sqlalchemy import func

from app.extensions import db
from app.models.enums import AccountType
from app.models.user import User, Address
from app.models.order import Order
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.services import audit
from app.utils.pagination import apply_sort, paginate


class AdminUserUpdateIn(Schema):
    """Every field optional, and booleans must be real JSON booleans.

    ``bool("false")`` is True, so coercing whatever arrived used to turn the
    string "false" into a toggle pointing the wrong way.
    """
    is_active = fields.Bool(truthy={True}, falsy={False})
    is_verified = fields.Bool(truthy={True}, falsy={False})
    account_type = fields.Str(validate=validate.OneOf(["retail", "wholesale"]))


_user_update_in = AdminUserUpdateIn()

_USER_SORTS = {
    "created_at": User.created_at,
    "full_name": User.full_name,
}


@admin_bp.route("/users", methods=["GET"])
@admin_required
def admin_list_users():
    search = (request.args.get("q") or "").strip()
    account_type = request.args.get("account_type")

    q = User.query

    if search:
        q = q.filter(
            (User.full_name.ilike(f"%{search}%"))
            | (User.email.ilike(f"%{search}%"))
            | (User.phone.ilike(f"%{search}%"))
        )

    if account_type in ("retail", "wholesale"):
        q = q.filter(User.account_type == AccountType(account_type))

    active = request.args.get("active", "").lower()
    if active in ("true", "false"):
        q = q.filter(User.is_active.is_(active == "true"))

    paginated = paginate(apply_sort(q, _USER_SORTS, "created_at"))

    # One grouped query for the whole page, not a COUNT per row.
    order_counts = dict(
        db.session.query(Order.user_id, func.count(Order.id))
        .filter(Order.user_id.in_([u.id for u in paginated.items]))
        .group_by(Order.user_id)
        .all()
    ) if paginated.items else {}

    users = []
    for u in paginated.items:
        order_count = order_counts.get(u.id, 0)
        users.append({
            "id": str(u.id),
            "full_name": u.full_name,
            "email": u.email,
            "phone": u.phone,
            "account_type": u.account_type.value,
            "auth_provider": u.auth_provider.value,
            "is_verified": u.is_verified,
            "is_active": u.is_active,
            "order_count": order_count,
            "created_at": u.created_at.isoformat(),
        })

    return jsonify(
        users=users,
        page=paginated.page,
        pages=paginated.pages,
        total=paginated.total,
    ), 200


@admin_bp.route("/users/<user_id>", methods=["GET"])
@admin_required
def admin_user_detail(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify(error="User not found"), 404

    orders = (
        Order.query
        .filter_by(user_id=user.id)
        .order_by(Order.placed_at.desc())
        .limit(10)
        .all()
    )
    addresses = Address.query.filter_by(user_id=user.id).all()

    return jsonify(
        id=str(user.id),
        full_name=user.full_name,
        email=user.email,
        phone=user.phone,
        account_type=user.account_type.value,
        auth_provider=user.auth_provider.value,
        is_verified=user.is_verified,
        is_active=user.is_active,
        avatar_url=user.avatar_url,
        created_at=user.created_at.isoformat(),
        addresses=[
            {
                "id": a.id,
                "label": a.label,
                "full_name": a.full_name,
                "city": a.city,
                "state": a.state,
                "pin_code": a.pin_code,
                "is_default": a.is_default,
            }
            for a in addresses
        ],
        recent_orders=[
            {
                "id": o.id,
                "order_number": o.order_number,
                "status": o.status.value,
                "total_amount": float(o.total_amount),
                "placed_at": o.placed_at.isoformat(),
            }
            for o in orders
        ],
    ), 200


@admin_bp.route("/users/<user_id>", methods=["PATCH"])
@admin_required
def admin_update_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify(error="User not found"), 404

    try:
        data = _user_update_in.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(errors=err.messages), 422
    if not data:
        return jsonify(error="Nothing to update"), 422

    if "is_active" in data:
        user.is_active = data["is_active"]
    if "is_verified" in data:
        user.is_verified = data["is_verified"]
    if "account_type" in data:
        user.account_type = AccountType(data["account_type"])

    audit.annotate(
        summary=f"Customer {user.email}: " + ", ".join(
            f"{field} → {value}" for field, value in data.items()
        ),
    )
    db.session.commit()

    return jsonify(message="User updated"), 200
