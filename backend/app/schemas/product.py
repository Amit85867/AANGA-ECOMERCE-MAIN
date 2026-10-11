from marshmallow import Schema, fields, validate


class ProductImageOut(Schema):
    id = fields.Int()
    image_url = fields.Str()
    sort_order = fields.Int()
    is_primary = fields.Bool()


class ProductVariantOut(Schema):
    id = fields.Int()
    size = fields.Str()
    color_name = fields.Str()
    color_hex = fields.Str()
    stock_qty = fields.Int()
    price_override = fields.Float(allow_none=True)
    sku = fields.Str(allow_none=True)


class ProductListOut(Schema):
    id = fields.Int()
    slug = fields.Str()
    name = fields.Str()
    category_name = fields.Str()
    mrp = fields.Float()
    selling_price = fields.Float()
    discount_percent = fields.Int()
    badge_label = fields.Str(allow_none=True)
    badge_class = fields.Str(allow_none=True)
    primary_image = fields.Str(allow_none=True)
    colors = fields.List(fields.Str())
    avg_rating = fields.Float(allow_none=True)
    review_count = fields.Int()
    # Set while a campaign has this product on sale.
    on_sale = fields.Bool()
    original_price = fields.Float()
    sale_percent = fields.Float()
    sale_name = fields.Str()


class ProductDetailOut(Schema):
    id = fields.Int()
    slug = fields.Str()
    name = fields.Str()
    description = fields.Str(allow_none=True)
    category_name = fields.Str()
    category_slug = fields.Str()
    mrp = fields.Float()
    selling_price = fields.Float()
    discount_percent = fields.Int()
    badge_label = fields.Str(allow_none=True)
    badge_class = fields.Str(allow_none=True)
    is_featured = fields.Bool()
    variants = fields.List(fields.Nested(ProductVariantOut))
    images = fields.List(fields.Nested(ProductImageOut))
    avg_rating = fields.Float(allow_none=True)
    review_count = fields.Int()
    rating_count = fields.Int()
    care_details = fields.Str(allow_none=True)
    meta_title = fields.Str(allow_none=True)
    meta_description = fields.Str(allow_none=True)
    share_image_url = fields.Str(allow_none=True)
    on_sale = fields.Bool()
    original_price = fields.Float()
    sale_percent = fields.Float()
    sale_name = fields.Str()


class ReviewOut(Schema):
    id = fields.Int()
    rating = fields.Int()
    title = fields.Str(allow_none=True)
    body = fields.Str(allow_none=True)
    is_verified = fields.Bool()
    user_name = fields.Str()
    created_at = fields.DateTime()


class ReviewIn(Schema):
    product_id = fields.Int(required=True)
    # Bounded here so an out-of-range rating is a clean 422 rather than a 500
    # from the ck_review_rating check constraint.
    rating = fields.Int(required=True, validate=validate.Range(min=1, max=5))
    title = fields.Str(validate=validate.Length(max=200))
    body = fields.Str(validate=validate.Length(max=5000))
    # order_item_id is deliberately absent: "verified purchase" is resolved
    # server-side from the reviewer's delivered orders (see routes/reviews.py).
