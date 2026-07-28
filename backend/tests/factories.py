"""Small helpers to build database rows for tests.

Plain functions (not factory_boy) to keep dependencies light. Each commits so
the objects have server-generated ids/defaults populated.
"""
import uuid
from datetime import datetime, timezone, timedelta

from app.extensions import db
from app.models.user import User, Address
from app.models.catalogue import Category, Product, ProductVariant
from app.models.cart import Cart, CartItem
from app.models.engagement import Coupon
from app.models.enums import DiscountType


def make_user(email=None, **kw):
    user = User(
        full_name=kw.get("full_name", "Test User"),
        email=email or f"user_{uuid.uuid4().hex[:8]}@example.com",
        phone=kw.get("phone", "9000000000"),
        password_hash=kw.get("password_hash", "x"),
    )
    db.session.add(user)
    db.session.commit()
    return user


def make_address(user, **kw):
    addr = Address(
        user_id=user.id,
        full_name=kw.get("full_name", user.full_name),
        phone=kw.get("phone", "9000000000"),
        line1=kw.get("line1", "1 Test Street"),
        city=kw.get("city", "Kolkata"),
        state=kw.get("state", "West Bengal"),
        pin_code=kw.get("pin_code", "700001"),
    )
    db.session.add(addr)
    db.session.commit()
    return addr


_category_cache = {}


def _default_category():
    cat = Category.query.filter_by(slug="test-cat").first()
    if not cat:
        cat = Category(name="Test Category", slug="test-cat")
        db.session.add(cat)
        db.session.commit()
    return cat


def make_product(price=500, stock=10, mrp=None, **kw):
    """Create a product with a single variant. Returns (product, variant)."""
    slug = kw.get("slug", f"prod-{uuid.uuid4().hex[:8]}")
    product = Product(
        category_id=_default_category().id,
        name=kw.get("name", "Test Product"),
        slug=slug,
        mrp=mrp if mrp is not None else price,
        selling_price=price,
    )
    db.session.add(product)
    db.session.flush()

    variant = ProductVariant(
        product_id=product.id,
        size=kw.get("size", "M"),
        color_name=kw.get("color_name", "Black"),
        color_hex="#000000",
        stock_qty=stock,
    )
    db.session.add(variant)
    db.session.commit()
    return product, variant


def make_coupon(code="SAVE10", discount_type=DiscountType.percentage,
                discount_value=10, max_discount=None, **kw):
    coupon = Coupon(
        code=code,
        discount_type=discount_type,
        discount_value=discount_value,
        max_discount=max_discount,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db.session.add(coupon)
    db.session.commit()
    return coupon


def make_cart(user, items, coupon=None):
    """items: list of (variant, quantity). unit_price taken from variant."""
    cart = Cart(user_id=user.id, coupon_id=coupon.id if coupon else None)
    db.session.add(cart)
    db.session.flush()
    for variant, qty in items:
        db.session.add(CartItem(
            cart_id=cart.id,
            variant_id=variant.id,
            quantity=qty,
            unit_price=variant.product.selling_price,
        ))
    db.session.commit()
    return cart
