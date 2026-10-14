"""Admin accounts — separate from storefront users."""
import uuid

from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.extensions import db


class Admin(db.Model):
    __tablename__ = "admins"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = db.Column(db.Text, nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    full_name = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, nullable=False, default="staff")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_demo = db.Column(db.Boolean, nullable=False, default=False)
    created_by = db.Column(UUID(as_uuid=True), db.ForeignKey("admins.id", ondelete="SET NULL"))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    last_login = db.Column(db.DateTime(timezone=True))

    def __repr__(self):
        return f"<Admin {self.email} ({self.role})>"
