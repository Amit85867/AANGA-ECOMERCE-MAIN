"""users, user_sessions, addresses."""
import uuid

from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.sql import func

from app.extensions import db
from app.models._types import pg_enum
from app.models.enums import AccountType, AuthProviderType


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False, unique=True)
    phone = db.Column(db.Text)
    password_hash = db.Column(db.Text)  # null for social auth
    auth_provider = db.Column(
        pg_enum(AuthProviderType, "auth_provider_type"),
        nullable=False,
        default=AuthProviderType.email,
    )
    auth_provider_id = db.Column(db.Text)
    account_type = db.Column(
        pg_enum(AccountType, "account_type"),
        nullable=False,
        default=AccountType.retail,
    )
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    avatar_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        db.UniqueConstraint("auth_provider", "auth_provider_id", name="uq_provider"),
    )

    # Relationships
    sessions = db.relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    addresses = db.relationship("Address", back_populates="user", cascade="all, delete-orphan")
    cart = db.relationship("Cart", back_populates="user", uselist=False, cascade="all, delete-orphan")
    orders = db.relationship("Order", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"


class UserSession(db.Model):
    __tablename__ = "user_sessions"

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = db.Column(db.Text, nullable=False, unique=True)
    device_info = db.Column(db.Text)
    ip_address = db.Column(INET)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    user = db.relationship("User", back_populates="sessions")


class OTP(db.Model):
    __tablename__ = "otps"

    id = db.Column(db.BigInteger, primary_key=True)
    phone = db.Column(db.Text, nullable=False, index=True)
    code = db.Column(db.CHAR(6), nullable=False)
    attempts = db.Column(db.SmallInteger, nullable=False, default=0)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())


class PasswordReset(db.Model):
    __tablename__ = "password_resets"

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = db.Column(db.Text, nullable=False, index=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())


class Address(db.Model):
    __tablename__ = "addresses"

    id = db.Column(db.BigInteger, primary_key=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    label = db.Column(db.Text, nullable=False, default="Home")
    full_name = db.Column(db.Text, nullable=False)
    phone = db.Column(db.Text, nullable=False)
    line1 = db.Column(db.Text, nullable=False)
    line2 = db.Column(db.Text)
    city = db.Column(db.Text, nullable=False)
    state = db.Column(db.Text, nullable=False)
    pin_code = db.Column(db.CHAR(6), nullable=False)
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())
    # Set instead of deleting/rewriting a row an order still points at; see
    # routes/addresses.py.
    archived_at = db.Column(db.DateTime(timezone=True))

    user = db.relationship("User", back_populates="addresses")
