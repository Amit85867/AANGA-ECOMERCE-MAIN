from marshmallow import Schema, fields, validate


class RegisterSchema(Schema):
    full_name = fields.Str(required=True, validate=validate.Length(min=2, max=120))
    email = fields.Email(required=True)
    phone = fields.Str(validate=validate.Length(min=10, max=15))
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128))
    account_type = fields.Str(validate=validate.OneOf(["retail", "wholesale"]))


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True)


class GoogleAuthSchema(Schema):
    id_token = fields.Str()
    access_token = fields.Str()


class SendOTPSchema(Schema):
    phone = fields.Str(required=True, validate=validate.Regexp(r"^\+91\d{10}$", error="Phone must be +91 followed by 10 digits"))


class VerifyOTPSchema(Schema):
    phone = fields.Str(required=True, validate=validate.Regexp(r"^\+91\d{10}$", error="Phone must be +91 followed by 10 digits"))
    code = fields.Str(required=True, validate=validate.Length(equal=6))
    full_name = fields.Str(validate=validate.Length(min=2, max=120))


class ChangePasswordSchema(Schema):
    current_password = fields.Str(required=True)
    new_password = fields.Str(required=True, validate=validate.Length(min=8, max=128))


class ForgotPasswordSchema(Schema):
    email = fields.Email(required=True)


class ResetPasswordSchema(Schema):
    token = fields.Str(required=True)
    new_password = fields.Str(required=True, validate=validate.Length(min=8, max=128))
