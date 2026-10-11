"""offers, wholesale_inquiries, newsletter_subscribers, contact_messages."""
import uuid

from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func

from app.extensions import db
from app.models._types import pg_enum
from app.models.enums import (
    OfferType,
    VolumeRange,
    InquiryStatus,
    ContactSubject,
    MessageStatus,
)


class Offer(db.Model):
    __tablename__ = "offers"

    id = db.Column(db.BigInteger, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.BigInteger, db.ForeignKey("categories.id", ondelete="SET NULL"))
    offer_type = db.Column(pg_enum(OfferType, "offer_type"), nullable=False)
    discount_percent = db.Column(db.Numeric(5, 2))
    image_url = db.Column(db.Text)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    starts_at = db.Column(db.DateTime(timezone=True))
    ends_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())


class WholesaleInquiry(db.Model):
    __tablename__ = "wholesale_inquiries"

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="SET NULL"))
    shop_name = db.Column(db.Text, nullable=False)
    owner_name = db.Column(db.Text, nullable=False)
    phone = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    city = db.Column(db.Text, nullable=False)
    state = db.Column(db.Text, nullable=False)
    gst_number = db.Column(db.Text)
    categories_interest = db.Column(ARRAY(db.Text))
    monthly_volume_range = db.Column(pg_enum(VolumeRange, "volume_range"), nullable=False)
    status = db.Column(pg_enum(InquiryStatus, "inquiry_status"), nullable=False, default=InquiryStatus.new)
    notes = db.Column(db.Text)
    submitted_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())


class NewsletterSubscriber(db.Model):
    __tablename__ = "newsletter_subscribers"

    id = db.Column(db.BigInteger, primary_key=True)
    email = db.Column(db.Text, nullable=False, unique=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    subscribed_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    unsubscribed_at = db.Column(db.DateTime(timezone=True))


class ContactMessage(db.Model):
    __tablename__ = "contact_messages"

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="SET NULL"))
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    phone = db.Column(db.Text)
    subject = db.Column(pg_enum(ContactSubject, "contact_subject"), nullable=False, default=ContactSubject.general)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(pg_enum(MessageStatus, "message_status"), nullable=False, default=MessageStatus.unread)
    sent_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    replied_at = db.Column(db.DateTime(timezone=True))
