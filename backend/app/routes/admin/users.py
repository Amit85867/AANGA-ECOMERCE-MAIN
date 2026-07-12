"""Admin user management: list, detail, toggle active."""
from flask import request, jsonify

from app.extensions import db
from app.models.user import User, Address
from app.models.order import Order
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required


@admin_bp.route("/users", methods=["GET"])
@admin_required
def admin_list_users():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 20, type=int), 100)
    search = request.args.get("q")
    account_type = request.args.get("account_type")

    q = User.query

    if search:
        q = q.filter(
            (User.full_name.ilike(f"%{search}%"))
            | (User.email.ilike(f"%{search}%"))
            | (User.phone.ilike(f"%{search}%"))
        )

    if account_type:
        q = q.filter_by(account_type=account_type)

    paginated = q.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    users = []
    for u in paginated.items:
        order_count = Order.query.filter_by(user_id=u.id).count()
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

    data = request.get_json()
    if "is_active" in data:
        user.is_active = bool(data["is_active"])
    if "is_verified" in data:
        user.is_verified = bool(data["is_verified"])
    if "account_type" in data and data["account_type"] in ("retail", "wholesale"):
        from app.models.enums import AccountType
        user.account_type = AccountType(data["account_type"])

    db.session.commit()

    return jsonify(message="User updated"), 200
