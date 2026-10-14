"""Flask extension singletons, initialised in the app factory."""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request
from flask_jwt_extended import get_jwt, verify_jwt_in_request

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()

# Brute-force protection. Per-route limits are declared on the auth endpoints;
# there is deliberately no global default so normal browsing is untouched.
limiter = Limiter(key_func=get_remote_address)


def user_or_ip():
    """Rate-limit key for signed-in routes: the account, else the address.

    Many customers share one address (mobile carriers, offices), so a limit
    keyed on IP alone lets one of them use up everybody's allowance, and one
    account switching networks escapes it. Only a token that verifies counts;
    anything else falls back to the address.
    """
    try:
        verify_jwt_in_request(optional=True)
        claims = get_jwt()
    except Exception:
        return get_remote_address()
    if claims.get("sub"):
        return f"{claims.get('actor') or 'user'}:{claims['sub']}"
    return get_remote_address()


def login_email():
    """Rate-limit key for sign-in: the account being tried.

    Stops a password being guessed from many addresses at once, which a
    per-address limit cannot see.
    """
    body = request.get_json(silent=True)
    email = body.get("email") if isinstance(body, dict) else None
    if isinstance(email, str) and email.strip():
        return f"login:{email.strip().lower()[:254]}"
    return get_remote_address()
