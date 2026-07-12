"""orders, order_items, order_tracking, returns."""
import uuid

from sqlalchemy import Computed
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.extensions import db
from app.models._types import pg_enum
from app.models.enums import (
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
    TrackingStatusType,
    ReturnReason,
    ReturnStatus,
    ResolutionType,
)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    address_id = db.Column(db.BigInteger, db.ForeignKey("addresses.id", ondelete="RESTRICT"), nullable=False)
    coupon_id = db.Column(db.BigInteger, db.ForeignKey("coupons.id", ondelete="SET NULL"))

    order_number = db.Column(db.Text, nullable=False, unique=True)  # assigned by DB trigger
    status = db.Column(pg_enum(OrderStatus, "order_status"), nullable=False, default=OrderStatus.pending)

    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    gst_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    delivery_charge = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)

    payment_method = db.Column(pg_enum(PaymentMethod, "payment_method"), nullable=False)
    payment_status = db.Column(pg_enum(PaymentStatus, "payment_status"), nullable=False, default=PaymentStatus.pending)
    payment_ref = db.Column(db.Text)

    courier_name = db.Column(db.Text)
    tracking_number = db.Column(db.Text)
    expected_delivery = db.Column(db.Date)

    placed_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    user = db.relationship("User", back_populates="orders")
    address = db.relationship("Address")
    coupon = db.relationship("Coupon")
    items = db.relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    tracking = db.relationship("OrderTracking", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Order {self.order_number}>"


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.BigInteger, primary_key=True)
    order_id = db.Column(db.BigInteger, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    variant_id = db.Column(db.BigInteger, db.ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(
        db.Numeric(10, 2),
        Computed("quantity * unit_price", persisted=True),
    )

    __table_args__ = (
        db.CheckConstraint("quantity > 0", name="ck_order_item_qty"),
    )

    order = db.relationship("Order", back_populates="items")
    variant = db.relationship("ProductVariant")


class OrderTracking(db.Model):
    __tablename__ = "order_tracking"

    id = db.Column(db.BigInteger, primary_key=True)
    order_id = db.Column(db.BigInteger, db.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False)
    status_label = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    status_type = db.Column(pg_enum(TrackingStatusType, "tracking_status_type"), nullable=False)
    event_time = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    order = db.relationship("Order", back_populates="tracking")


class Return(db.Model):
    __tablename__ = "returns"

    id = db.Column(db.BigInteger, primary_key=True)
    order_item_id = db.Column(db.BigInteger, db.ForeignKey("order_items.id", ondelete="RESTRICT"), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    reason = db.Column(pg_enum(ReturnReason, "return_reason"), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(pg_enum(ReturnStatus, "return_status"), nullable=False, default=ReturnStatus.requested)
    resolution_type = db.Column(pg_enum(ResolutionType, "resolution_type"))
    refund_amount = db.Column(db.Numeric(10, 2))
    requested_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    resolved_at = db.Column(db.DateTime(timezone=True))

    order_item = db.relationship("OrderItem")
