from marshmallow import Schema, fields, validate


class OfferOut(Schema):
    id = fields.Int()
    title = fields.Str()
    description = fields.Str(allow_none=True)
    offer_type = fields.Str()
    discount_percent = fields.Float(allow_none=True)
    image_url = fields.Str(allow_none=True)
    starts_at = fields.DateTime(allow_none=True)
    ends_at = fields.DateTime(allow_none=True)


class ContactMessageIn(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    email = fields.Email(required=True)
    phone = fields.Str(validate=validate.Length(min=10, max=15))
    subject = fields.Str(
        load_default="general",
        validate=validate.OneOf([
            "general", "order_support", "wholesale",
            "returns_refunds", "feedback", "other",
        ]),
    )
    message = fields.Str(required=True, validate=validate.Length(min=10, max=2000))


class WholesaleInquiryIn(Schema):
    shop_name = fields.Str(required=True, validate=validate.Length(min=2, max=200))
    owner_name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    phone = fields.Str(required=True, validate=validate.Length(min=10, max=15))
    email = fields.Email(required=True)
    city = fields.Str(required=True)
    state = fields.Str(required=True)
    gst_number = fields.Str(allow_none=True)
    categories_interest = fields.List(fields.Str())
    monthly_volume_range = fields.Str(
        required=True,
        validate=validate.OneOf(["below_10k", "10k_50k", "50k_1lac", "above_1lac"]),
    )


class NewsletterIn(Schema):
    email = fields.Email(required=True)
