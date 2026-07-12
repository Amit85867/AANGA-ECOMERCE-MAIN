from marshmallow import Schema, fields


class CartItemIn(Schema):
    variant_id = fields.Int(required=True)
    quantity = fields.Int(load_default=1)


class CartItemUpdateIn(Schema):
    quantity = fields.Int(required=True)


class ApplyCouponIn(Schema):
    code = fields.Str(required=True)


class CartItemOut(Schema):
    id = fields.Int()
    variant_id = fields.Int()
    product_name = fields.Str()
    product_slug = fields.Str()
    size = fields.Str()
    color_name = fields.Str()
    color_hex = fields.Str()
    image_url = fields.Str(allow_none=True)
    quantity = fields.Int()
    unit_price = fields.Float()
    mrp = fields.Float()
    line_total = fields.Float()


class CartOut(Schema):
    id = fields.Int()
    items = fields.List(fields.Nested(CartItemOut))
    coupon_code = fields.Str(allow_none=True)
    subtotal = fields.Float()
    discount = fields.Float()
    gst = fields.Float()
    delivery_charge = fields.Float()
    total = fields.Float()
    savings = fields.Float()
    item_count = fields.Int()
