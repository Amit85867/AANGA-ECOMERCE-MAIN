from marshmallow import Schema, fields


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
    order_item_id = fields.Int(allow_none=True)
    rating = fields.Int(required=True)
    title = fields.Str()
    body = fields.Str()
