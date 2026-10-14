"""Owner-dashboard models: collections, campaigns, homepage sections,
navigation, pages, FAQ and the media library."""
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.extensions import db


class Collection(db.Model):
    """A hand-picked set of products, e.g. "Diwali Edit"."""
    __tablename__ = "collections"

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    slug = db.Column(db.Text, nullable=False, unique=True)
    description = db.Column(db.Text)
    image_url = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    meta_title = db.Column(db.Text)
    meta_description = db.Column(db.Text)
    share_image_url = db.Column(db.Text)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    items = db.relationship(
        "CollectionProduct", cascade="all, delete-orphan",
        order_by="CollectionProduct.sort_order", back_populates="collection",
    )


class CollectionProduct(db.Model):
    __tablename__ = "collection_products"

    collection_id = db.Column(db.BigInteger, db.ForeignKey("collections.id", ondelete="CASCADE"), primary_key=True)
    product_id = db.Column(db.BigInteger, db.ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    collection = db.relationship("Collection", back_populates="items")
    product = db.relationship("Product")


class Campaign(db.Model):
    """A scheduled festival or sale. See app/services/campaigns.py."""
    __tablename__ = "campaigns"

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    starts_at = db.Column(db.DateTime(timezone=True), nullable=False)
    ends_at = db.Column(db.DateTime(timezone=True), nullable=False)
    ended_at = db.Column(db.DateTime(timezone=True))
    announcement_text = db.Column(db.Text)
    announcement_highlight = db.Column(db.Text)
    announcement_link_url = db.Column(db.Text)
    announcement_link_text = db.Column(db.Text)
    collection_id = db.Column(db.BigInteger, db.ForeignKey("collections.id", ondelete="SET NULL"))
    sale_percent = db.Column(db.Numeric(4, 1))
    decoration_enabled = db.Column(db.Boolean, nullable=False, default=False)
    accent_preset = db.Column(db.Text, nullable=False, default="marigold")
    show_countdown = db.Column(db.Boolean, nullable=False, default=False)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    collection = db.relationship("Collection")


class HomepageSection(db.Model):
    __tablename__ = "homepage_sections"

    id = db.Column(db.BigInteger, primary_key=True)
    key = db.Column(db.Text, nullable=False, unique=True)
    title = db.Column(db.Text)
    subtitle = db.Column(db.Text)
    is_visible = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    config = db.Column(JSONB, nullable=False, default=dict)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class NavLink(db.Model):
    __tablename__ = "nav_links"

    id = db.Column(db.BigInteger, primary_key=True)
    location = db.Column(db.Text, nullable=False)          # "header" | "footer"
    group_name = db.Column(db.Text)                         # footer column heading
    label = db.Column(db.Text, nullable=False)
    url = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_visible = db.Column(db.Boolean, nullable=False, default=True)


class CmsPage(db.Model):
    __tablename__ = "cms_pages"

    id = db.Column(db.BigInteger, primary_key=True)
    slug = db.Column(db.Text, nullable=False, unique=True)
    title = db.Column(db.Text, nullable=False)
    body_html = db.Column(db.Text, nullable=False, default="")
    meta_title = db.Column(db.Text)
    meta_description = db.Column(db.Text)
    share_image_url = db.Column(db.Text)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class FaqItem(db.Model):
    __tablename__ = "faq_items"

    id = db.Column(db.BigInteger, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())


class MediaAsset(db.Model):
    __tablename__ = "media_assets"

    id = db.Column(db.BigInteger, primary_key=True)
    url = db.Column(db.Text, nullable=False, unique=True)
    filename = db.Column(db.Text)
    alt_text = db.Column(db.Text)
    width = db.Column(db.Integer)
    height = db.Column(db.Integer)
    size_bytes = db.Column(db.Integer)
    source_note = db.Column(db.Text)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    uploaded_by = db.Column(UUID(as_uuid=True), db.ForeignKey("admins.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
