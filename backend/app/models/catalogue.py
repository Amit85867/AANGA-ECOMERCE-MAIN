"""categories, products, product_variants, product_images."""
from sqlalchemy import Computed
from sqlalchemy.sql import func

from app.extensions import db


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.BigInteger, primary_key=True)
    parent_id = db.Column(db.BigInteger, db.ForeignKey("categories.id", ondelete="SET NULL"))
    name = db.Column(db.Text, nullable=False)
    slug = db.Column(db.Text, nullable=False, unique=True)
    description = db.Column(db.Text)
    image_url = db.Column(db.Text)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    children = db.relationship("Category", backref=db.backref("parent", remote_side=[id]))
    products = db.relationship("Product", back_populates="category")

    def __repr__(self):
        return f"<Category {self.slug}>"


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.BigInteger, primary_key=True)
    category_id = db.Column(db.BigInteger, db.ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False)
    name = db.Column(db.Text, nullable=False)
    slug = db.Column(db.Text, nullable=False, unique=True)
    description = db.Column(db.Text)
    mrp = db.Column(db.Numeric(10, 2), nullable=False)
    selling_price = db.Column(db.Numeric(10, 2), nullable=False)
    # Generated column — computed by Postgres, read-only here.
    discount_percent = db.Column(
        db.Integer,
        Computed("round(((mrp - selling_price) / mrp) * 100)", persisted=True),
    )
    badge_label = db.Column(db.Text)
    badge_class = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_featured = db.Column(db.Boolean, nullable=False, default=False)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    care_details = db.Column(db.Text)
    meta_title = db.Column(db.Text)
    meta_description = db.Column(db.Text)
    share_image_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    category = db.relationship("Category", back_populates="products")
    variants = db.relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")
    images = db.relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    reviews = db.relationship("ProductReview", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product {self.slug}>"


class ProductVariant(db.Model):
    __tablename__ = "product_variants"

    id = db.Column(db.BigInteger, primary_key=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    size = db.Column(db.Text, nullable=False)
    color_name = db.Column(db.Text, nullable=False)
    color_hex = db.Column(db.CHAR(7), nullable=False)
    stock_qty = db.Column(db.Integer, nullable=False, default=0)
    price_override = db.Column(db.Numeric(10, 2))
    sku = db.Column(db.Text, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        db.UniqueConstraint("product_id", "size", "color_name", name="uq_variant"),
    )

    product = db.relationship("Product", back_populates="variants")


class ProductImage(db.Model):
    __tablename__ = "product_images"

    id = db.Column(db.BigInteger, primary_key=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    image_url = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_primary = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    product = db.relationship("Product", back_populates="images")
