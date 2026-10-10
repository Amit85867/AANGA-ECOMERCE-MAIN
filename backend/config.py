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
    # Connection pool, per gunicorn worker. The hard ceiling is Postgres's
    # max_connections, and every worker holds its own pool, so:
    #
    #   workers x (DB_POOL_SIZE + DB_MAX_OVERFLOW)  +  cron job  +  headroom
    #
    # must stay under it. The defaults (2 workers x (5 + 5) = 20) fit the
    # smallest managed Postgres plans. See docs/DEPLOYMENT.md before raising
    # either number or WEB_CONCURRENCY.
    SQLALCHEMY_ENGINE_OPTIONS = {
        # Check a pooled connection is alive before using it: managed
        # databases drop idle connections and restart for maintenance.
        "pool_pre_ping": True,
        "pool_size": int(os.environ.get("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "5")),
        # Fail a request after 10s waiting for a connection rather than
        # queueing forever behind a saturated pool.
        "pool_timeout": int(os.environ.get("DB_POOL_TIMEOUT", "10")),
        # Recycle before the platform's idle timeout closes it underneath us.
        "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", "280")),
    }

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

    # How many reverse proxies sit in front of the app and append to
    # X-Forwarded-For. Trusting too few makes every visitor share the proxy's
    # IP (one rate-limit bucket for everyone); trusting too many lets a client
    # forge its own address. Check with the admin System Health page.
    TRUSTED_PROXY_COUNT = int(os.environ.get("TRUSTED_PROXY_COUNT", "1"))

    # Phone-OTP sign-in needs something to deliver the code. No provider is
    # integrated yet, so this stays empty and the option stays hidden.
    SMS_PROVIDER = os.environ.get("SMS_PROVIDER", "")

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
    # Hand the HTTP call to a background thread so a slow mail provider never
    # holds up the checkout response. Off in tests, which assert on the call.
    EMAIL_ASYNC = os.environ.get("EMAIL_ASYNC", "true").lower() == "true"

    # Short-lived cache for public catalogue responses (app/services/cache.py).
    # Uses CACHE_REDIS_URL, else RATELIMIT_STORAGE_URI when that is Redis, else
    # a small per-process cache.
    CACHE_ENABLED = os.environ.get("CACHE_ENABLED", "true").lower() == "true"
    CACHE_REDIS_URL = os.environ.get("CACHE_REDIS_URL", "")

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
    # "None" is required only when the storefront calls the API cross-site.
    # Behind a same-origin /api rewrite (the Render layout) set this to "Lax",
    # which also stops the cookie riding along on cross-site requests.
    JWT_COOKIE_SAMESITE = os.environ.get("JWT_COOKIE_SAMESITE", "None")


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
    # Tests change rows directly and expect the next read to show it; the cache
    # and background email are switched on only by the tests that cover them.
    CACHE_ENABLED = False
    EMAIL_ASYNC = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    return config_by_name.get(os.environ.get("FLASK_ENV", "development"), DevelopmentConfig)
