"""Admin dashboard: everything the overview screen shows, in one response.

One endpoint rather than a call per card: the dashboard is the first thing an
admin sees, and a dozen round-trips to a remote database made it the slowest
page in the panel. The whole response is seven queries, all on indexed columns
(see migrations_admin_ops.sql).
"""
from datetime import datetime, timedelta, timezone

from flask import jsonify, request
from sqlalchemy import and_, case, func

from app.extensions import db
from app.models.catalogue import Product, ProductVariant
from app.models.enums import InquiryStatus, MessageStatus, OrderStatus, ReturnStatus
from app.models.marketing import ContactMessage, WholesaleInquiry
from app.models.order import Order, OrderItem, Return
from app.models.user import User
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.utils.pagination import parse_day

# The store trades in India, so "today" and each day on the chart are IST days,
# not UTC ones. India has no daylight saving, so a fixed offset is exact.
IST = timezone(timedelta(hours=5, minutes=30))

# Stock at or below this (and above zero) is "low".
LOW_STOCK_THRESHOLD = 5

# Longest range the chart will draw; keeps the daily series bounded.
MAX_RANGE_DAYS = 366

# An order that was cancelled or sent back is not revenue.
_NOT_REVENUE = (OrderStatus.cancelled, OrderStatus.returned)


def _resolve_range():
    """(start, end) as aware datetimes, end exclusive, from ?from / ?to (IST days).

    Defaults to the last 30 days. A reversed or oversized range is clamped
    rather than rejected: the screen should always draw something.
    """
    today = datetime.now(IST).replace(hour=0, minute=0, second=0, microsecond=0)
    start, end_day = parse_day(request.args.get("from")), parse_day(request.args.get("to"))

    end_day = end_day.replace(tzinfo=IST) if end_day else today
    start = start.replace(tzinfo=IST) if start else end_day - timedelta(days=29)
    if start > end_day:
        start, end_day = end_day, start
    if (end_day - start).days >= MAX_RANGE_DAYS:
        start = end_day - timedelta(days=MAX_RANGE_DAYS - 1)
    return start, end_day + timedelta(days=1), today


def _revenue_between(start, end=None):
    window = Order.placed_at >= start
    if end is not None:
        window = and_(window, Order.placed_at < end)
    return func.coalesce(func.sum(case(
        (and_(window, Order.status.notin_(_NOT_REVENUE)), Order.total_amount),
        else_=0,
    )), 0)


@admin_bp.route("/dashboard/overview", methods=["GET"])
@admin_required
def dashboard_overview():
    start, end, today = _resolve_range()
    in_range = and_(Order.placed_at >= start, Order.placed_at < end)

    # 1. Revenue for the fixed windows and the chosen range, in one pass.
    money = db.session.query(
        _revenue_between(today),
        _revenue_between(today - timedelta(days=6)),
        _revenue_between(today - timedelta(days=29)),
        _revenue_between(start, end),
        func.count(case((and_(in_range, Order.status.notin_(_NOT_REVENUE)), 1))),
    ).one()
    range_revenue, range_orders = float(money[3]), money[4]

    # 2. Orders by status in the range.
    by_status = dict(
        db.session.query(Order.status, func.count(Order.id))
        .filter(in_range).group_by(Order.status).all()
    )

    # 3. Revenue and order count per IST day in the range.
    day = func.date(func.timezone("Asia/Kolkata", Order.placed_at))
    per_day = {
        row[0].isoformat(): (float(row[1]), row[2])
        for row in db.session.query(
            day,
            func.coalesce(func.sum(case(
                (Order.status.notin_(_NOT_REVENUE), Order.total_amount), else_=0,
            )), 0),
            func.count(Order.id),
        ).filter(in_range).group_by(day).all()
    }
    series = []
    cursor = start
    while cursor < end:
        key = cursor.date().isoformat()
        revenue, orders = per_day.get(key, (0.0, 0))
        series.append({"date": key, "revenue": revenue, "orders": orders})
        cursor += timedelta(days=1)

    # 4. Stock on active products.
    stock = db.session.query(
        func.count(case((ProductVariant.stock_qty <= 0, 1))),
        func.count(case((and_(
            ProductVariant.stock_qty > 0,
            ProductVariant.stock_qty <= LOW_STOCK_THRESHOLD,
        ), 1))),
    ).join(Product, ProductVariant.product_id == Product.id).filter(
        Product.is_active.is_(True)
    ).one()

    low_stock_items = (
        db.session.query(ProductVariant, Product)
        .join(Product, ProductVariant.product_id == Product.id)
        .filter(
            Product.is_active.is_(True),
            ProductVariant.stock_qty <= LOW_STOCK_THRESHOLD,
        )
        .order_by(ProductVariant.stock_qty.asc(), Product.name.asc())
        .limit(8)
        .all()
    )

    # 5. Work waiting for an admin, and customers.
    counts = db.session.query(
        db.session.query(func.count(Product.id))
        .filter(Product.is_active.is_(True)).scalar_subquery(),
        db.session.query(func.count(Return.id))
        .filter(Return.status.notin_([ReturnStatus.resolved, ReturnStatus.rejected]))
        .scalar_subquery(),
        db.session.query(func.count(WholesaleInquiry.id))
        .filter(WholesaleInquiry.status == InquiryStatus.new).scalar_subquery(),
        db.session.query(func.count(ContactMessage.id))
        .filter(ContactMessage.status == MessageStatus.unread).scalar_subquery(),
        db.session.query(func.count(User.id)).scalar_subquery(),
        db.session.query(func.count(User.id))
        .filter(User.created_at >= start, User.created_at < end).scalar_subquery(),
    ).one()

    # 6. Latest orders, with the customer's name.
    recent = (
        db.session.query(Order, User.full_name)
        .outerjoin(User, Order.user_id == User.id)
        .order_by(Order.placed_at.desc())
        .limit(8)
        .all()
    )

    # 7. Best sellers in the range.
    units = func.sum(OrderItem.quantity)
    top_products = (
        db.session.query(Product.id, Product.name, units)
        .join(ProductVariant, ProductVariant.product_id == Product.id)
        .join(OrderItem, OrderItem.variant_id == ProductVariant.id)
        .join(Order, OrderItem.order_id == Order.id)
        .filter(in_range, Order.status.notin_(_NOT_REVENUE))
        .group_by(Product.id, Product.name)
        .order_by(units.desc())
        .limit(5)
        .all()
    )

    return jsonify(
        range={
            "from": start.date().isoformat(),
            "to": (end - timedelta(days=1)).date().isoformat(),
            "days": (end - start).days,
            "timezone": "Asia/Kolkata",
        },
        revenue={
            "today": float(money[0]),
            "last_7d": float(money[1]),
            "last_30d": float(money[2]),
            "range": range_revenue,
        },
        orders={
            "range": sum(by_status.values()),
            "paid_range": range_orders,
            "average_value": round(range_revenue / range_orders, 2) if range_orders else 0,
            "by_status": {s.value: by_status.get(s, 0) for s in OrderStatus},
        },
        series=series,
        products={
            "active": counts[0],
            "out_of_stock": stock[0],
            "low_stock": stock[1],
            "low_stock_threshold": LOW_STOCK_THRESHOLD,
            "low_stock_items": [
                {
                    "product_id": product.id,
                    "name": product.name,
                    "size": variant.size,
                    "color_name": variant.color_name,
                    "sku": variant.sku,
                    "stock_qty": variant.stock_qty,
                }
                for variant, product in low_stock_items
            ],
        },
        pending={
            "returns": counts[1],
            "inquiries": counts[2],
            "messages": counts[3],
            "orders": by_status_all_pending(),
        },
        users={"total": counts[4], "new_range": counts[5]},
        recent_orders=[
            {
                "id": order.id,
                "order_number": order.order_number,
                "customer_name": name or "Unknown",
                "status": order.status.value,
                "payment_status": order.payment_status.value,
                "total_amount": float(order.total_amount),
                "placed_at": order.placed_at.isoformat(),
            }
            for order, name in recent
        ],
        top_products=[
            {"product_id": pid, "name": name, "units": int(sold or 0)}
            for pid, name, sold in top_products
        ],
    ), 200


def by_status_all_pending():
    """Orders awaiting action right now — not limited to the selected range,
    because an order placed before the range still needs shipping."""
    return Order.query.filter(
        Order.status.in_([OrderStatus.pending, OrderStatus.confirmed, OrderStatus.packed])
    ).count()
