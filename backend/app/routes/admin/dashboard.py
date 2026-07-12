"""Admin dashboard: overview stats — optimised for remote DB."""
from datetime import datetime, timezone, timedelta

from flask import jsonify
from sqlalchemy import func, case, text

from app.extensions import db
from app.models.user import User
from app.models.catalogue import Product, ProductVariant
from app.models.order import Order
from app.models.marketing import WholesaleInquiry, ContactMessage
from app.models.enums import OrderStatus, InquiryStatus, MessageStatus
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required


@admin_bp.route("/dashboard/stats", methods=["GET"])
@admin_required
def dashboard_stats():
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)

    user_stats = db.session.query(
        func.count(User.id),
        func.count(case((User.created_at >= thirty_days_ago, 1))),
    ).first()

    product_total = Product.query.filter_by(is_active=True).count()

    order_stats = db.session.query(
        func.count(Order.id),
        func.count(case((Order.placed_at >= thirty_days_ago, 1))),
        func.count(case((Order.status == OrderStatus.pending, 1))),
        func.coalesce(func.sum(case(
            (Order.status != OrderStatus.cancelled, Order.total_amount),
            else_=0,
        )), 0),
        func.coalesce(func.sum(case(
            ((Order.status != OrderStatus.cancelled) & (Order.placed_at >= thirty_days_ago), Order.total_amount),
            else_=0,
        )), 0),
    ).first()

    misc = db.session.query(
        func.count(case((WholesaleInquiry.status == InquiryStatus.new, 1))),
        func.count(case((ContactMessage.status == MessageStatus.unread, 1))),
    ).select_from(WholesaleInquiry).outerjoin(
        ContactMessage, text("1=1")
    ).first() if False else None

    pending_inquiries = WholesaleInquiry.query.filter_by(status=InquiryStatus.new).count()
    unread_messages = ContactMessage.query.filter_by(status=MessageStatus.unread).count()

    recent_orders = (
        Order.query
        .order_by(Order.placed_at.desc())
        .limit(5)
        .all()
    )

    return jsonify(
        users={"total": user_stats[0], "new_30d": user_stats[1]},
        products={"total": product_total, "out_of_stock": 0},
        orders={
            "total": order_stats[0],
            "last_30d": order_stats[1],
            "pending": order_stats[2],
        },
        revenue={
            "total": float(order_stats[3]),
            "last_30d": float(order_stats[4]),
        },
        pending_inquiries=pending_inquiries,
        unread_messages=unread_messages,
        recent_orders=[
            {
                "id": o.id,
                "order_number": o.order_number,
                "status": o.status.value,
                "total_amount": float(o.total_amount),
                "placed_at": o.placed_at.isoformat(),
            }
            for o in recent_orders
        ],
    ), 200
