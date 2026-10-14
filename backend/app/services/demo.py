"""Demo content: tag it as it is created, and remove all of it in one go.

**Tagging.** While the Owner has "Demo mode" switched on, the admin app sends
``X-Demo-Content: 1`` with every request, and anything created by that request
that has an ``is_demo`` column is marked. Nothing else about the request
changes — demo items are made through exactly the same screens and routes as
real ones.

**Removing.** :func:`remove_all` deletes everything marked, in an order the
foreign keys allow. Where a demo item has become tied to something real (a
demo product that a real customer ordered) it is deactivated and kept rather
than breaking the real record.
"""
from flask import has_request_context, request
from sqlalchemy import event

from app.extensions import db

HEADER = "X-Demo-Content"


def _models():
    from app.models.admin import Admin
    from app.models.catalogue import Category, Product
    from app.models.cms import Announcement, Feature, HeroBanner, PromoBanner, Testimonial
    from app.models.engagement import Coupon
    from app.models.marketing import Offer
    from app.models.owner import Campaign, CmsPage, Collection, FaqItem, MediaAsset
    from app.models.user import User

    return {
        "products": Product, "categories": Category, "collections": Collection,
        "campaigns": Campaign, "hero_slides": HeroBanner, "promo_banners": PromoBanner,
        "announcements": Announcement, "testimonials": Testimonial, "feature_cards": Feature,
        "coupons": Coupon, "offers": Offer, "faq_entries": FaqItem, "pages": CmsPage,
        "images": MediaAsset, "customers": User, "staff": Admin,
    }


def tagging_requested():
    return (
        has_request_context()
        and request.path.startswith("/api/admin/")
        and request.headers.get(HEADER) == "1"
    )


def init_app(app):
    @event.listens_for(db.session, "before_flush")
    def _tag_new_rows(session, _flush_context, _instances):
        if not tagging_requested():
            return
        from app.models.owner import CmsPage
        for obj in session.new:
            # Pages always exist (the rows are created on first read); one is
            # demo only when demo text is saved into it — see save_page.
            if hasattr(type(obj), "is_demo") and not isinstance(obj, CmsPage):
                obj.is_demo = True


def summary():
    """How many demo items of each kind exist."""
    return {name: model.query.filter(model.is_demo.is_(True)).count() for name, model in _models().items()}


def remove_all(keep_admin_id=None):
    """Delete everything tagged as demo. Returns ``{kind: number removed}``
    plus ``kept`` for items deactivated instead. Does not commit."""
    from app.models.catalogue import Category, Product, ProductVariant
    from app.models.order import Order, OrderItem, Return
    from app.models.owner import CmsPage, MediaAsset
    from app.services import media

    m = _models()
    removed, kept = {}, []

    # 1. Demo customers and everything they did.
    demo_users = [u.id for u in m["customers"].query.filter_by(is_demo=True).all()]
    if demo_users:
        Return.query.filter(Return.user_id.in_(demo_users)).delete(synchronize_session=False)
        order_ids = [o.id for o in Order.query.filter(Order.user_id.in_(demo_users)).all()]
        if order_ids:
            item_ids = [i.id for i in OrderItem.query.filter(OrderItem.order_id.in_(order_ids)).all()]
            if item_ids:
                Return.query.filter(Return.order_item_id.in_(item_ids)).delete(synchronize_session=False)
            # Rows are deleted, not cancelled: no status change, so no restock.
            Order.query.filter(Order.id.in_(order_ids)).delete(synchronize_session=False)
        removed["orders"] = len(order_ids)
        m["customers"].query.filter(m["customers"].id.in_(demo_users)).delete(synchronize_session=False)
    removed["customers"] = len(demo_users)

    # 2. Things with no dependants (campaign slides go with their campaign).
    for kind in ("campaigns", "hero_slides", "promo_banners", "announcements", "testimonials",
                 "feature_cards", "offers", "coupons", "collections", "faq_entries"):
        model = m[kind]
        removed[kind] = model.query.filter(model.is_demo.is_(True)).delete(synchronize_session=False)
    db.session.flush()

    # 3. Products: one a real order points at is switched off and kept.
    removed["products"] = 0
    for product in Product.query.filter_by(is_demo=True).all():
        ordered = (
            db.session.query(OrderItem.id)
            .join(ProductVariant, OrderItem.variant_id == ProductVariant.id)
            .filter(ProductVariant.product_id == product.id).first()
        )
        if ordered:
            product.is_active = False
            kept.append(f"Product \"{product.name}\" has real orders: deactivated, not deleted.")
        else:
            db.session.delete(product)
            removed["products"] += 1
    db.session.flush()

    # 4. Categories, children first; one still holding products is switched off.
    removed["categories"] = 0
    demo_categories = Category.query.filter_by(is_demo=True).all()
    for category in sorted(demo_categories, key=lambda c: c.parent_id is None):
        has_products = Product.query.filter_by(category_id=category.id).first() is not None
        has_children = Category.query.filter_by(parent_id=category.id).first() is not None
        if has_products or has_children:
            category.is_active = False
            kept.append(f"Category \"{category.name}\" still has products or sub-categories: deactivated, not deleted.")
        else:
            db.session.delete(category)
            removed["categories"] += 1
            db.session.flush()

    # 5. Pages stay (the storefront links to them) but lose their demo text.
    removed["pages"] = CmsPage.query.filter_by(is_demo=True).update(
        {"body_html": "", "meta_title": None, "meta_description": None, "share_image_url": None, "is_demo": False},
        synchronize_session=False,
    )

    # 6. Demo staff (never the admin doing the removing).
    staff = m["staff"].query.filter_by(is_demo=True)
    if keep_admin_id:
        staff = staff.filter(m["staff"].id != keep_admin_id)
    removed["staff"] = staff.delete(synchronize_session=False)
    db.session.flush()

    # 7. Images last, now that whatever used them is gone. One still in use
    #    (the owner reused a demo picture on a real product) is kept.
    removed["images"] = 0
    for asset in MediaAsset.query.filter_by(is_demo=True).all():
        if media.usage(asset.url):
            asset.is_demo = False
            kept.append(f"Image {asset.filename or asset.url} is still in use: kept.")
            continue
        media.delete_files(asset.url)
        db.session.delete(asset)
        removed["images"] += 1

    removed["kept"] = kept
    return removed
