import re

from marshmallow import Schema, fields, pre_load, validate


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
    phone = fields.Str(required=True, validate=validate.Regexp(
        r"^\+?\d{10,14}$", error="Enter a valid phone number."
    ))
    line1 = fields.Str(required=True, validate=validate.Length(min=3, max=300))
    line2 = fields.Str(allow_none=True, validate=validate.Length(max=300))
    city = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    state = fields.Str(required=True, validate=validate.Length(min=2, max=100))
    # Indian PIN codes: six digits, never starting with 0. The courier rejects
    # anything else, long after the customer has paid.
    pin_code = fields.Str(required=True, validate=validate.Regexp(
        r"^[1-9]\d{5}$", error="Enter a valid 6-digit PIN code."
    ))
    is_default = fields.Bool(load_default=False)

    @pre_load
    def _tidy(self, data, **kwargs):
        """Accept a phone typed the way people type them ("98765 43210")."""
        if isinstance(data, dict) and isinstance(data.get("phone"), str):
            data = {**data, "phone": re.sub(r"[\s\-()]", "", data["phone"])}
        return data


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
