"""carts, cart_items."""
import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.extensions import db


class Cart(db.Model):
    __tablename__ = "carts"

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    coupon_id = db.Column(db.BigInteger, db.ForeignKey("coupons.id", ondelete="SET NULL"))
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    user = db.relationship("User", back_populates="cart")
    items = db.relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")
    coupon = db.relationship("Coupon")


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.BigInteger, primary_key=True)
    cart_id = db.Column(db.BigInteger, db.ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    variant_id = db.Column(db.BigInteger, db.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    added_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        db.UniqueConstraint("cart_id", "variant_id", name="uq_cart_variant"),
        db.CheckConstraint("quantity > 0", name="ck_cart_item_qty"),
    )

    cart = db.relationship("Cart", back_populates="items")
    variant = db.relationship("ProductVariant")
