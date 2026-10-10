"""SQLAlchemy models mirroring the AANGA Supabase schema.

Importing this package registers every model on the shared metadata so
Flask-Migrate / Alembic can discover them.
"""
from app.models.user import User, UserSession, Address, OTP, PasswordReset
from app.models.catalogue import Category, Product, ProductVariant, ProductImage
from app.models.engagement import ProductReview, Wishlist, Coupon
from app.models.cart import Cart, CartItem
from app.models.order import Order, OrderItem, OrderTracking, Return
from app.models.marketing import (
    Offer,
    WholesaleInquiry,
    NewsletterSubscriber,
    ContactMessage,
)
from app.models.admin import Admin
from app.models.cms import HeroBanner, Announcement, PromoBanner, SiteSetting, Testimonial, Feature
from app.models.ops import WebhookEvent, JobRun

__all__ = [
    "User",
    "UserSession",
    "Address",
    "OTP",
    "PasswordReset",
    "Category",
    "Product",
    "ProductVariant",
    "ProductImage",
    "ProductReview",
    "Wishlist",
    "Coupon",
    "Cart",
    "CartItem",
    "Order",
    "OrderItem",
    "OrderTracking",
    "Return",
    "Offer",
    "WholesaleInquiry",
    "NewsletterSubscriber",
    "ContactMessage",
    "Admin",
    "HeroBanner",
    "Announcement",
    "PromoBanner",
    "SiteSetting",
    "Testimonial",
    "Feature",
    "WebhookEvent",
    "JobRun",
]
