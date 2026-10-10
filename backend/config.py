"""Application configuration objects, selected via FLASK_ENV."""
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

# The dockerized Postgres from backend/docker-compose.yml. Used as the
# development fallback, and recognised by _validate_config so a production app
# that forgot to set DATABASE_URL fails on boot rather than on first query.
DEV_DATABASE_URL = "postgresql://aanga:aanga@localhost:55433/aanga"


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # SQLAlchemy. The fallback points at the dockerized Postgres from
    # backend/docker-compose.yml — the schema is Postgres-native (UUID PKs, PG
    # enums, generated columns, triggers), so a SQLite fallback would only fail
    # in confusing ways. Production must set DATABASE_URL explicitly.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", DEV_DATABASE_URL)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # JWT
    # The access token is short-lived and lives only in the client's memory
    # (sent as an Authorization header). The refresh token is long-lived and
    # travels exclusively in an httpOnly cookie, so XSS cannot read it.
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_REFRESH_COOKIE_NAME = "aanga_refresh"
    # Scope the cookie to the auth routes that need it (refresh + logout).
    JWT_REFRESH_COOKIE_PATH = "/api/auth"
    # Double-submit CSRF protection for anything authenticated via a cookie.
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_CSRF_IN_COOKIES = True
    # Overridden per environment below.
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_SAMESITE = "None"

    # Observability (Sentry). Leave SENTRY_DSN blank to disable entirely.
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
    SENTRY_ENVIRONMENT = os.environ.get("SENTRY_ENVIRONMENT", os.environ.get("FLASK_ENV", "development"))
    SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0"))
    APP_RELEASE = os.environ.get("APP_RELEASE", "")

    # Rate limiting (Flask-Limiter). In-memory is fine for a single instance;
    # point this at Redis once the API runs on more than one process.
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True

    # CORS
    FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")

    # Public storefront origin used to build absolute URLs in sitemap.xml /
    # robots.txt (canonical links, Open Graph). Defaults to the frontend origin.
    SITE_URL = os.environ.get("SITE_URL", os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173"))

    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

    # Razorpay (online payments)
    RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

    # Supabase Storage (product images).
    # Required in production: Render/Railway filesystems are ephemeral, so
    # images written to local disk vanish on the next deploy.
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
    SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "product-images")

    # Transactional email (Resend). Leave RESEND_API_KEY blank to log instead
    # of sending (local dev). EMAIL_ENABLED is a manual kill switch.
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
    EMAIL_FROM = os.environ.get("EMAIL_FROM", "AANGA <orders@aanga.in>")
    EMAIL_ENABLED = os.environ.get("EMAIL_ENABLED", "true").lower() == "true"

    # Shiprocket (delivery)
    SHIPROCKET_EMAIL = os.environ.get("SHIPROCKET_EMAIL", "")
    SHIPROCKET_PASSWORD = os.environ.get("SHIPROCKET_PASSWORD", "")
    SHIPROCKET_PICKUP_LOCATION = os.environ.get("SHIPROCKET_PICKUP_LOCATION", "Primary")


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    # localhost:5173 and localhost:5000 are the same site, so Lax works and we
    # can't use Secure cookies over plain http.
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_SAMESITE = "Lax"


class ProductionConfig(BaseConfig):
    DEBUG = False


class TestingConfig(BaseConfig):
    TESTING = True
    # Tests run against a real Postgres (Docker) so enum types, computed
    # columns and triggers behave exactly as in production. Spin it up with
    # `docker compose -f docker-compose.test.yml up -d`.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "TEST_DATABASE_URL", "postgresql://postgres:test@localhost:55432/aanga_test"
    )
    JWT_SECRET_KEY = "test-jwt-secret-that-is-long-enough-for-hs256"
    SECRET_KEY = "test-secret"
    JWT_COOKIE_SECURE = False
    JWT_COOKIE_SAMESITE = "Lax"
    # Limiter stays enabled (so its behaviour is actually tested) but the
    # conftest resets counters between tests to keep them isolated.
    RATELIMIT_STORAGE_URI = "memory://"


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    return config_by_name.get(os.environ.get("FLASK_ENV", "development"), DevelopmentConfig)
