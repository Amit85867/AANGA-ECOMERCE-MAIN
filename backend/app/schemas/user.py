from marshmallow import Schema, fields, validate


def _enum_value(obj, attr):
    val = getattr(obj, attr, None)
    return val.value if val is not None else None


class UserOut(Schema):
    id = fields.Str()
    full_name = fields.Str()
    email = fields.Str()
    phone = fields.Str(allow_none=True)
    account_type = fields.Function(lambda obj: _enum_value(obj, "account_type"))
    auth_provider = fields.Function(lambda obj: _enum_value(obj, "auth_provider"))
    is_verified = fields.Bool()
    avatar_url = fields.Str(allow_none=True)
    created_at = fields.DateTime()


class ProfileUpdateIn(Schema):
    full_name = fields.Str(validate=validate.Length(min=2, max=120))
    phone = fields.Str(validate=validate.Length(min=10, max=15))
    avatar_url = fields.Str()


class AddressIn(Schema):
    label = fields.Str(load_default="Home")
    full_name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    phone = fields.Str(required=True, validate=validate.Length(min=10, max=15))
    line1 = fields.Str(required=True)
    line2 = fields.Str(allow_none=True)
    city = fields.Str(required=True)
    state = fields.Str(required=True)
    pin_code = fields.Str(required=True, validate=validate.Length(equal=6))
    is_default = fields.Bool(load_default=False)


class AddressOut(Schema):
    id = fields.Int()
    label = fields.Str()
    full_name = fields.Str()
    phone = fields.Str()
    line1 = fields.Str()
    line2 = fields.Str(allow_none=True)
    city = fields.Str()
    state = fields.Str()
    pin_code = fields.Str()
    is_default = fields.Bool()
