"""product_reviews, wishlist, coupons."""
import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.extensions import db
from app.models._types import pg_enum
from app.models.enums import DiscountType


class ProductReview(db.Model):
    __tablename__ = "product_reviews"

    id = db.Column(db.BigInteger, primary_key=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    order_item_id = db.Column(
        db.BigInteger, db.ForeignKey("order_items.id", ondelete="SET NULL")
    )
    rating = db.Column(db.SmallInteger, nullable=False)
    title = db.Column(db.Text)
    body = db.Column(db.Text)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uq_review"),
        db.CheckConstraint("rating between 1 and 5", name="ck_review_rating"),
    )

    product = db.relationship("Product", back_populates="reviews")


class Wishlist(db.Model):
    __tablename__ = "wishlist"

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    product_id = db.Column(db.BigInteger, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    variant_id = db.Column(db.BigInteger, db.ForeignKey("product_variants.id", ondelete="SET NULL"))
    added_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="uq_wishlist"),
    )


class Coupon(db.Model):
    __tablename__ = "coupons"

    id = db.Column(db.BigInteger, primary_key=True)
    code = db.Column(db.Text, nullable=False, unique=True)
    description = db.Column(db.Text)
    discount_type = db.Column(pg_enum(DiscountType, "discount_type"), nullable=False)
    discount_value = db.Column(db.Numeric(10, 2), nullable=False)
    min_order_value = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    max_discount = db.Column(db.Numeric(10, 2))
    usage_limit = db.Column(db.Integer)
    used_count = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    expires_at = db.Column(db.DateTime(timezone=True))
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    campaign_id = db.Column(db.BigInteger, db.ForeignKey("campaigns.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self):
        return f"<Coupon {self.code}>"
