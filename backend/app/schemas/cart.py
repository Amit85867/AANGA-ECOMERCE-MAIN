from marshmallow import Schema, fields, validate


# Upper bound on one line's quantity. Stock is the real limit; this only stops
# an absurd number reaching the database.
MAX_LINE_QUANTITY = 99


class CartItemIn(Schema):
    variant_id = fields.Int(required=True)
    # The cart_items_quantity_check constraint rejects anything below 1, so
    # without this a zero or negative quantity surfaced as a 500.
    quantity = fields.Int(
        load_default=1, validate=validate.Range(min=1, max=MAX_LINE_QUANTITY)
    )


class CartItemUpdateIn(Schema):
    # Zero (or less) removes the line.
    quantity = fields.Int(required=True, validate=validate.Range(max=MAX_LINE_QUANTITY))


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
