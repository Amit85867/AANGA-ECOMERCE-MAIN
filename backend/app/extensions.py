"""Flask extension singletons, initialised in the app factory."""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()

# Brute-force protection. Per-route limits are declared on the auth endpoints;
# there is deliberately no global default so normal browsing is untouched.
limiter = Limiter(key_func=get_remote_address)
