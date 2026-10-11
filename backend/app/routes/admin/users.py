"""Admin user management: list, detail, toggle active."""
import csv
import io

from flask import Response, request, jsonify
from marshmallow import Schema, ValidationError, fields, validate
from sqlalchemy import func

from app.extensions import db
from app.models.enums import AccountType
from app.models.user import User, Address
from app.models.order import Order, OrderItem, Return
from app.models.engagement import ProductReview
from app.models.catalogue import Product
from app.models.enums import OrderStatus
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
    # Marks a made-up customer so "Remove demo content" takes it away.
    is_demo = fields.Bool(truthy={True}, falsy={False})


_user_update_in = AdminUserUpdateIn()

_USER_SORTS = {
    "created_at": User.created_at,
    "full_name": User.full_name,
}


# Orders that never became (or did not stay) a sale do not count as spend.
_NOT_SPEND = (OrderStatus.cancelled, OrderStatus.returned)


def _filtered_users():
    """The customer list for the current ?q / ?account_type / ?active filters."""
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
    return q


def _order_stats(user_ids):
    """``{user_id: (orders, lifetime spend)}`` in one grouped query."""
    if not user_ids:
        return {}
    rows = (
        db.session.query(
            Order.user_id, func.count(Order.id),
            func.coalesce(func.sum(Order.total_amount).filter(Order.status.notin_(_NOT_SPEND)), 0),
        )
        .filter(Order.user_id.in_(user_ids)).group_by(Order.user_id).all()
    )
    return {uid: (count, float(spend)) for uid, count, spend in rows}


@admin_bp.route("/users/export.csv", methods=["GET"])
@admin_required
def export_users_csv():
    """The filtered customer list as a spreadsheet.

    Contact details and order totals only: no password hashes, no payment
    references, no addresses.
    """
    users = _filtered_users().order_by(User.created_at.desc()).limit(20000).all()
    stats = _order_stats([u.id for u in users])
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Name", "Email", "Phone", "Account type", "Status", "Orders", "Lifetime spend (INR)", "Joined"])
    for u in users:
        orders, spend = stats.get(u.id, (0, 0.0))
        writer.writerow([
            _csv_safe(u.full_name), _csv_safe(u.email), _csv_safe(u.phone or ""), u.account_type.value,
            "active" if u.is_active else "blocked", orders, f"{spend:.2f}", u.created_at.date().isoformat(),
        ])
    audit.record("export_customers", "users", summary=f"Exported {len(users)} customers to CSV")
    return Response(
        "\ufeff" + out.getvalue(), mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers.csv", "Cache-Control": "no-store"},
    )


def _csv_safe(value):
    """A customer can type anything as their name; a cell starting with =, +, -
    or @ would run as a formula when the file is opened in a spreadsheet."""
    text = str(value or "")
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


@admin_bp.route("/users", methods=["GET"])
@admin_required
def admin_list_users():
    q = _filtered_users()
    if request.args.get("demo") == "true":
        q = q.filter(User.is_demo.is_(True))

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
            "is_demo": u.is_demo,
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
    order_count, lifetime_spend = _order_stats([user.id]).get(user.id, (0, 0.0))
    returns = (
        db.session.query(Return, Order.order_number, Order.id)
        .join(OrderItem, Return.order_item_id == OrderItem.id)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(Return.user_id == user.id).order_by(Return.requested_at.desc()).limit(10).all()
    )
    reviews = (
        db.session.query(ProductReview, Product.name)
        .join(Product, ProductReview.product_id == Product.id)
        .filter(ProductReview.user_id == user.id).order_by(ProductReview.created_at.desc()).limit(10).all()
    )

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
        is_demo=user.is_demo,
        order_count=order_count,
        lifetime_spend=lifetime_spend,
        returns=[
            {"id": r.id, "order_id": order_id, "order_number": number, "reason": r.reason.value,
             "status": r.status.value, "requested_at": r.requested_at.isoformat()}
            for r, number, order_id in returns
        ],
        reviews=[
            {"id": rv.id, "product_name": name, "rating": rv.rating, "title": rv.title,
             "created_at": rv.created_at.isoformat()}
            for rv, name in reviews
        ],
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
    if "is_demo" in data:
        user.is_demo = data["is_demo"]

    audit.annotate(
        summary=f"Customer {user.email}: " + ", ".join(
            f"{field} → {value}" for field, value in data.items()
        ),
    )
    db.session.commit()

    return jsonify(message="User updated"), 200
