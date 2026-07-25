from marshmallow import Schema, fields, validate


# ── Auth ──────────────────────────────────────────────────────
class AdminLoginIn(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)


class AdminCreateIn(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128))
    full_name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    role = fields.Str(load_default="staff", validate=validate.OneOf(["master", "staff"]))


class AdminOut(Schema):
    id = fields.Str()
    email = fields.Str()
    full_name = fields.Str()
    role = fields.Str()
    is_active = fields.Bool()
    created_at = fields.DateTime()
    last_login = fields.DateTime(allow_none=True)


# ── Products ──────────────────────────────────────────────────
class AdminProductIn(Schema):
    category_id = fields.Int(required=True)
    name = fields.Str(required=True, validate=validate.Length(min=2, max=300))
    slug = fields.Str(required=True, validate=validate.Length(min=2, max=300))
    description = fields.Str(allow_none=True)
    mrp = fields.Float(required=True)
    selling_price = fields.Float(required=True)
    badge_label = fields.Str(allow_none=True)
    badge_class = fields.Str(allow_none=True)
    is_active = fields.Bool(load_default=True)
    is_featured = fields.Bool(load_default=False)


class AdminVariantIn(Schema):
    size = fields.Str(required=True)
    color_name = fields.Str(required=True)
    color_hex = fields.Str(required=True, validate=validate.Length(equal=7))
    stock_qty = fields.Int(load_default=0)
    price_override = fields.Float(allow_none=True)
    sku = fields.Str(allow_none=True)


class AdminImageIn(Schema):
    image_url = fields.Str(required=True)
    sort_order = fields.Int(load_default=0)
    is_primary = fields.Bool(load_default=False)


# ── Categories ────────────────────────────────────────────────
class AdminCategoryIn(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=200))
    slug = fields.Str(required=True, validate=validate.Length(min=2, max=200))
    description = fields.Str(allow_none=True)
    image_url = fields.Str(allow_none=True)
    parent_id = fields.Int(allow_none=True)
    sort_order = fields.Int(load_default=0)
    is_active = fields.Bool(load_default=True)


# ── Orders ────────────────────────────────────────────────────
class AdminOrderStatusIn(Schema):
    status = fields.Str(
        required=True,
        validate=validate.OneOf([
            "pending", "confirmed", "packed", "shipped",
            "out_for_delivery", "delivered", "cancelled",
            "return_requested", "returned",
        ]),
    )


class AdminTrackingIn(Schema):
    status_label = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    status_type = fields.Str(
        required=True,
        validate=validate.OneOf([
            "placed", "confirmed", "packed", "dispatched",
            "in_transit", "out_for_delivery", "delivered",
            "failed_attempt", "returned",
        ]),
    )
    courier_name = fields.Str(allow_none=True)
    tracking_number = fields.Str(allow_none=True)
    expected_delivery = fields.Date(allow_none=True)


class AdminReturnUpdateIn(Schema):
    status = fields.Str(
        required=True,
        validate=validate.OneOf([
            "requested", "approved", "pickup_scheduled",
            "picked_up", "inspected", "resolved", "rejected",
        ]),
    )
    resolution_type = fields.Str(
        allow_none=True,
        validate=validate.OneOf(["refund", "exchange", "store_credit"]),
    )
    refund_amount = fields.Float(allow_none=True)


# ── Coupons ───────────────────────────────────────────────────
class AdminCouponIn(Schema):
    code = fields.Str(required=True, validate=validate.Length(min=3, max=30))
    description = fields.Str(allow_none=True)
    discount_type = fields.Str(required=True, validate=validate.OneOf(["percentage", "flat"]))
    discount_value = fields.Float(required=True)
    min_order_value = fields.Float(load_default=0)
    max_discount = fields.Float(allow_none=True)
    usage_limit = fields.Int(allow_none=True)
    is_active = fields.Bool(load_default=True)
    expires_at = fields.DateTime(allow_none=True)


# ── Offers ────────────────────────────────────────────────────
class AdminOfferIn(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=2, max=300))
    description = fields.Str(allow_none=True)
    category_id = fields.Int(allow_none=True)
    offer_type = fields.Str(
        required=True,
        validate=validate.OneOf(["percentage_off", "flat_off", "free_shipping", "bogo"]),
    )
    discount_percent = fields.Float(allow_none=True)
    image_url = fields.Str(allow_none=True)
    is_active = fields.Bool(load_default=True)
    starts_at = fields.DateTime(allow_none=True)
    ends_at = fields.DateTime(allow_none=True)


# ── Inquiries ─────────────────────────────────────────────────
class AdminInquiryStatusIn(Schema):
    status = fields.Str(
        required=True,
        validate=validate.OneOf(["new", "contacted", "qualified", "converted", "rejected"]),
    )
    notes = fields.Str(allow_none=True)


class AdminMessageStatusIn(Schema):
    status = fields.Str(
        required=True,
        validate=validate.OneOf(["unread", "read", "replied", "closed"]),
    )


# ── CMS: Hero Banners ───────────────────────────────────────
class AdminHeroBannerIn(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=2, max=300))
    subtitle = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    image_url = fields.Str(required=True)
    mobile_image_url = fields.Str(allow_none=True)
    link_url = fields.Str(allow_none=True)
    link_text = fields.Str(allow_none=True)
    secondary_link_url = fields.Str(allow_none=True)
    secondary_link_text = fields.Str(allow_none=True)
    pill_label = fields.Str(allow_none=True)
    pill_value = fields.Str(allow_none=True)
    chip_value = fields.Str(allow_none=True)
    chip_label = fields.Str(allow_none=True)
    sort_order = fields.Int(load_default=0)
    is_active = fields.Bool(load_default=True)
    starts_at = fields.DateTime(allow_none=True)
    ends_at = fields.DateTime(allow_none=True)


# ── CMS: Announcements ──────────────────────────────────────
class AdminAnnouncementIn(Schema):
    text = fields.Str(required=True, validate=validate.Length(min=2, max=500))
    highlight_text = fields.Str(allow_none=True)
    link_url = fields.Str(allow_none=True)
    link_text = fields.Str(allow_none=True)
    bg_color = fields.Str(load_default="#0A0A0A")
    text_color = fields.Str(load_default="#ffffff")
    highlight_color = fields.Str(load_default="#D4AF37")
    sort_order = fields.Int(load_default=0)
    is_active = fields.Bool(load_default=True)
    starts_at = fields.DateTime(allow_none=True)
    ends_at = fields.DateTime(allow_none=True)


# ── CMS: Promo Banners ──────────────────────────────────────
class AdminPromoBannerIn(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=2, max=300))
    subtitle = fields.Str(allow_none=True)
    description = fields.Str(allow_none=True)
    badge_text = fields.Str(allow_none=True)
    image_url = fields.Str(allow_none=True)
    link_url = fields.Str(allow_none=True)
    link_text = fields.Str(allow_none=True)
    items = fields.List(fields.Dict(), allow_none=True)
    sort_order = fields.Int(load_default=0)
    is_active = fields.Bool(load_default=True)
    starts_at = fields.DateTime(allow_none=True)
    ends_at = fields.DateTime(allow_none=True)


# ── CMS: Site Settings ──────────────────────────────────────
class AdminSiteSettingIn(Schema):
    key = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    value = fields.Str(required=True)
    label = fields.Str(allow_none=True)
    group_name = fields.Str(load_default="general")


class AdminSiteSettingBulkIn(Schema):
    settings = fields.List(fields.Nested(AdminSiteSettingIn), required=True)


# ── CMS: Testimonials ───────────────────────────────────────
class AdminTestimonialIn(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    location = fields.Str(allow_none=True)
    rating = fields.Int(load_default=5, validate=validate.Range(min=1, max=5))
    quote = fields.Str(required=True, validate=validate.Length(min=5, max=1000))
    avatar_url = fields.Str(allow_none=True)
    sort_order = fields.Int(load_default=0)
    is_active = fields.Bool(load_default=True)


# ── CMS: Features (Why Choose) ──────────────────────────────
class AdminFeatureIn(Schema):
    icon = fields.Str(allow_none=True)
    title = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    description = fields.Str(allow_none=True)
    image_url = fields.Str(allow_none=True)
    sort_order = fields.Int(load_default=0)
    is_active = fields.Bool(load_default=True)
