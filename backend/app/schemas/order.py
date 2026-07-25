from marshmallow import Schema, fields, validate, EXCLUDE


class PlaceOrderIn(Schema):
    class Meta:
        # Silently drop anything not declared here — in particular a client
        # trying to smuggle in a `payment_ref` to mark its own order paid.
        unknown = EXCLUDE

    address_id = fields.Int(required=True)
    payment_method = fields.Str(
        required=True,
        validate=validate.OneOf([
            "upi", "credit_card", "debit_card",
            "net_banking", "wallet", "emi", "cod",
        ]),
    )
    # NB: there is deliberately no `payment_ref` here. A client must never be
    # able to declare an order "paid" — that is proven only by the gateway
    # signature check in /api/payments/verify. This endpoint always creates an
    # unpaid (pending) order; prepaid methods still go through verify.


class OrderItemOut(Schema):
    id = fields.Int()
    product_name = fields.Str()
    product_slug = fields.Str()
    size = fields.Str()
    color_name = fields.Str()
    image_url = fields.Str(allow_none=True)
    quantity = fields.Int()
    unit_price = fields.Float()
    total_price = fields.Float()


class TrackingEventOut(Schema):
    id = fields.Int()
    status_label = fields.Str()
    description = fields.Str(allow_none=True)
    status_type = fields.Str()
    event_time = fields.DateTime()


class OrderListOut(Schema):
    id = fields.Int()
    order_number = fields.Str()
    status = fields.Str()
    total_amount = fields.Float()
    item_summary = fields.Str()
    item_count = fields.Int()
    placed_at = fields.DateTime()
    expected_delivery = fields.Date(allow_none=True)


class OrderDetailOut(Schema):
    id = fields.Int()
    order_number = fields.Str()
    status = fields.Str()
    subtotal = fields.Float()
    discount_amount = fields.Float()
    gst_amount = fields.Float()
    delivery_charge = fields.Float()
    total_amount = fields.Float()
    payment_method = fields.Str()
    payment_status = fields.Str()
    courier_name = fields.Str(allow_none=True)
    tracking_number = fields.Str(allow_none=True)
    expected_delivery = fields.Date(allow_none=True)
    placed_at = fields.DateTime()
    items = fields.List(fields.Nested(OrderItemOut))
    tracking = fields.List(fields.Nested(TrackingEventOut))
    address = fields.Dict()
