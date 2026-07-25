"""Authentication: register, login, Google OAuth, phone OTP, refresh, logout."""
import os
import random
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
    set_refresh_cookies,
    unset_jwt_cookies,
)
from marshmallow import ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

from app.extensions import db, limiter
from app.models.user import User, OTP, PasswordReset
from app.models.cart import Cart
from app.models.enums import AuthProviderType, AccountType
from app.schemas.auth import (
    RegisterSchema,
    LoginSchema,
    GoogleAuthSchema,
    SendOTPSchema,
    VerifyOTPSchema,
    ForgotPasswordSchema,
    ResetPasswordSchema,
)
from app.schemas.user import UserOut

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

_register_schema = RegisterSchema()
_login_schema = LoginSchema()
_google_schema = GoogleAuthSchema()
_send_otp_schema = SendOTPSchema()
_verify_otp_schema = VerifyOTPSchema()
_forgot_schema = ForgotPasswordSchema()
_reset_schema = ResetPasswordSchema()
_user_out = UserOut()


def _hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _auth_response(user, status=200, **extra):
    """Build a sign-in response.

    The access token goes in the JSON body — the client keeps it in memory
    only. The refresh token is set as an httpOnly cookie so JavaScript (and
    therefore XSS) can never read it.
    """
    identity = str(user.id)
    body = {
        "access_token": create_access_token(identity=identity),
        "user": _user_out.dump(user),
        **extra,
    }
    resp = jsonify(body)
    set_refresh_cookies(resp, create_refresh_token(identity=identity))
    return resp, status


# ── Email/Password ─────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per hour")
def register():
    try:
        data = _register_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    if User.query.filter_by(email=data["email"]).first():
        return jsonify(error="Email already registered"), 409

    user = User(
        full_name=data["full_name"],
        email=data["email"],
        phone=data.get("phone"),
        password_hash=generate_password_hash(data["password"]),
        auth_provider=AuthProviderType.email,
        account_type=AccountType(data.get("account_type", "retail")),
    )
    db.session.add(user)
    db.session.flush()

    db.session.add(Cart(user_id=user.id))
    db.session.commit()

    return _auth_response(user, 201)


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per 15 minutes")
def login():
    try:
        data = _login_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    user = User.query.filter_by(email=data["email"]).first()
    if not user or not user.password_hash or not check_password_hash(user.password_hash, data["password"]):
        return jsonify(error="Invalid email or password"), 401

    if not user.is_active:
        return jsonify(error="Account is deactivated"), 403

    return _auth_response(user)


# ── Google OAuth ───────────────────────────────────────────────

@auth_bp.route("/google", methods=["POST"])
@limiter.limit("20 per hour")
def google_auth():
    try:
        data = _google_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    if not data.get("id_token") and not data.get("access_token"):
        return jsonify(error="Provide id_token or access_token"), 422

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        return jsonify(error="Google OAuth not configured"), 503

    if data.get("id_token"):
        try:
            idinfo = google_id_token.verify_oauth2_token(
                data["id_token"], google_requests.Request(), client_id,
            )
        except ValueError:
            return jsonify(error="Invalid Google token"), 401
    else:
        import requests as http_requests
        # userinfo confirms the token is valid, but NOT that it was issued for
        # *our* app. Verify the audience via tokeninfo first, so an access token
        # minted for a different Google client cannot be replayed here.
        tokeninfo = http_requests.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"access_token": data["access_token"]},
            timeout=10,
        )
        if tokeninfo.status_code != 200 or tokeninfo.json().get("aud") != client_id:
            return jsonify(error="Invalid Google access token"), 401
        resp = http_requests.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {data['access_token']}"},
            timeout=10,
        )
        if resp.status_code != 200:
            return jsonify(error="Invalid Google access token"), 401
        idinfo = resp.json()
        idinfo.setdefault("email_verified", True)

    email = idinfo.get("email")
    if not email:
        return jsonify(error="Could not retrieve email from Google"), 400

    user = User.query.filter_by(email=email).first()

    if user:
        if user.auth_provider != AuthProviderType.google:
            user.auth_provider = AuthProviderType.google
            user.auth_provider_id = idinfo.get("sub")
            if not user.avatar_url and idinfo.get("picture"):
                user.avatar_url = idinfo["picture"]
            db.session.commit()
    else:
        user = User(
            full_name=idinfo.get("name", email.split("@")[0]),
            email=email,
            auth_provider=AuthProviderType.google,
            auth_provider_id=idinfo.get("sub"),
            avatar_url=idinfo.get("picture"),
            is_verified=idinfo.get("email_verified", False),
        )
        db.session.add(user)
        db.session.flush()
        db.session.add(Cart(user_id=user.id))
        db.session.commit()

    return _auth_response(user)


# ── Phone OTP ──────────────────────────────────────────────────

@auth_bp.route("/otp/send", methods=["POST"])
@limiter.limit("10 per hour")
def send_otp():
    try:
        data = _send_otp_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    phone = data["phone"]

    recent = OTP.query.filter(
        OTP.phone == phone,
        OTP.created_at > datetime.now(timezone.utc) - timedelta(minutes=1),
    ).first()
    if recent:
        return jsonify(error="Please wait 60 seconds before requesting another OTP"), 429

    code = f"{random.randint(0, 999999):06d}"

    otp = OTP(
        phone=phone,
        code=code,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.session.add(otp)
    db.session.commit()

    # TODO: integrate an SMS provider (MSG91 / Twilio) to actually deliver this.
    current_app.logger.info(f"[DEV] OTP for {phone}: {code}")

    resp = {"message": "OTP sent successfully"}
    # NEVER expose the code outside local development — returning it would let
    # anyone sign in as any phone number.
    if current_app.config.get("DEBUG"):
        resp["dev_otp"] = code
    return jsonify(resp), 200


@auth_bp.route("/otp/verify", methods=["POST"])
@limiter.limit("20 per hour")
def verify_otp():
    try:
        data = _verify_otp_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    phone = data["phone"]
    code = data["code"]

    otp = OTP.query.filter(
        OTP.phone == phone,
        OTP.used == False,
        OTP.expires_at > datetime.now(timezone.utc),
    ).order_by(OTP.created_at.desc()).first()

    if not otp:
        return jsonify(error="OTP expired or not found. Request a new one."), 400

    otp.attempts += 1
    if otp.attempts > 5:
        otp.used = True
        db.session.commit()
        return jsonify(error="Too many attempts. Request a new OTP."), 429

    if otp.code != code:
        db.session.commit()
        return jsonify(error="Invalid OTP"), 401

    otp.used = True
    db.session.commit()

    user = User.query.filter_by(phone=phone).first()

    if not user:
        user = User(
            full_name=data.get("full_name", phone[-4:] + " User"),
            email=f"{phone.replace('+', '')}@phone.aanga.in",
            phone=phone,
            auth_provider=AuthProviderType.phone,
            is_verified=True,
        )
        db.session.add(user)
        db.session.flush()
        db.session.add(Cart(user_id=user.id))
        db.session.commit()

    is_new = user.created_at > datetime.now(timezone.utc) - timedelta(seconds=5)
    return _auth_response(user, is_new_user=is_new)


# ── Token management ──────────────────────────────────────────

@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Mint a new access token from the httpOnly refresh cookie.

    The refresh token is rotated on every use, so a stolen one is only good
    until the legitimate client next refreshes.
    """
    identity = get_jwt_identity()
    user = db.session.get(User, identity)
    if not user or not user.is_active:
        resp = jsonify(error="Account is no longer active")
        unset_jwt_cookies(resp)
        return resp, 401

    resp = jsonify(access_token=create_access_token(identity=identity))
    set_refresh_cookies(resp, create_refresh_token(identity=identity))
    return resp, 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Clear the refresh cookie. The in-memory access token dies with the tab."""
    resp = jsonify(message="Logged out")
    unset_jwt_cookies(resp)
    return resp, 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user = db.session.get(User, get_jwt_identity())
    if not user:
        return jsonify(error="User not found"), 404
    return jsonify(_user_out.dump(user)), 200


# ── Password reset ────────────────────────────────────────────

@auth_bp.route("/forgot-password", methods=["POST"])
@limiter.limit("5 per hour")
def forgot_password():
    try:
        data = _forgot_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    generic = {"message": "If an account exists for that email, a reset link has been sent."}

    user = User.query.filter_by(email=data["email"]).first()
    # Only email/password accounts can reset a password.
    if not user or not user.password_hash:
        return jsonify(generic), 200

    # Invalidate any outstanding tokens for this user.
    PasswordReset.query.filter_by(user_id=user.id, used=False).update({"used": True})

    raw_token = secrets.token_urlsafe(32)
    reset = PasswordReset(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db.session.add(reset)
    db.session.commit()

    frontend = current_app.config.get("FRONTEND_ORIGIN", "http://localhost:5173")
    reset_link = f"{frontend}/reset-password?token={raw_token}"

    from app.services.email import send_password_reset
    send_password_reset(user.email, reset_link)
    # When email isn't configured, send_* logs the message so dev still works.

    resp = dict(generic)
    if current_app.config.get("DEBUG"):
        resp["dev_reset_link"] = reset_link
        resp["dev_token"] = raw_token
    return jsonify(resp), 200


@auth_bp.route("/reset-password", methods=["POST"])
@limiter.limit("10 per hour")
def reset_password():
    try:
        data = _reset_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    reset = PasswordReset.query.filter_by(
        token_hash=_hash_token(data["token"]),
        used=False,
    ).first()

    if not reset or reset.expires_at < datetime.now(timezone.utc):
        return jsonify(error="This reset link is invalid or has expired."), 400

    user = db.session.get(User, reset.user_id)
    if not user:
        return jsonify(error="Account not found"), 404

    user.password_hash = generate_password_hash(data["new_password"])
    reset.used = True
    db.session.commit()

    return jsonify(message="Password updated. You can now sign in."), 200
