"""Application configuration objects, selected via FLASK_ENV."""
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

# There is no local database any more: every environment uses a Neon branch,
# so an unset DATABASE_URL is always a mistake. This sentinel is what the app
# falls back to, and _validate_config recognises it, so the failure is a clear
# message at boot rather than a confusing one on the first query. It points
# nowhere on purpose.
UNSET_DATABASE_URL = "postgresql://unset:unset@database.invalid:5432/unset"

# Old name, kept so nothing importing it breaks.
DEV_DATABASE_URL = UNSET_DATABASE_URL


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # SQLAlchemy. There is no fallback database to connect to: set DATABASE_URL
    # to a Neon branch (docs/DATABASE.md). The schema is Postgres-native (UUID
    # PKs, PG enums, generated columns, triggers), so a SQLite fallback would
    # only fail in confusing ways.
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", UNSET_DATABASE_URL)
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
    # The CSRF cookie is deliberately NOT httpOnly: the storefront reads it and
    # echoes it back in X-CSRF-TOKEN. The refresh cookie itself stays httpOnly.
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_CSRF_IN_COOKIES = True

    # Cross-subdomain auth: the storefront is https://example.com and the API
    # is https://api.example.com. Different ORIGINS (so CORS applies) but the
    # same registrable domain, so a cookie scoped to ".example.com" is sent on
    # both and SameSite=Lax is enough -- "None" would be needed only for a
    # genuinely cross-SITE API, and it is weaker.
    #
    # Leave COOKIE_DOMAIN blank for localhost: a Domain attribute of
    # "localhost" is rejected by some browsers, and host-only cookies are
    # correct there anyway.
    COOKIE_DOMAIN = os.environ.get("COOKIE_DOMAIN", "").strip()
    JWT_COOKIE_DOMAIN = COOKIE_DOMAIN or None
    SESSION_COOKIE_DOMAIN = COOKIE_DOMAIN or None
    # Overridden per environment below.
    JWT_COOKIE_SECURE = True
    JWT_COOKIE_SAMESITE = "Lax"

    # Observability (Sentry). Leave SENTRY_DSN blank to disable entirely.
    SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
    SENTRY_ENVIRONMENT = os.environ.get("SENTRY_ENVIRONMENT", os.environ.get("FLASK_ENV", "development"))
    SENTRY_TRACES_SAMPLE_RATE = float(os.environ.get("SENTRY_TRACES_SAMPLE_RATE", "0.0"))
    APP_RELEASE = os.environ.get("APP_RELEASE", "")

    # Rate limiting (Flask-Limiter).
    #
    # Blank (the default) = "memory://": counters live in each gunicorn worker.
    # With WEB_CONCURRENCY=2 that means a caller gets roughly twice the
    # advertised allowance, and nothing is shared between instances. Acceptable
    # for development and for a single-worker deployment; not for production.
    #
    # In production point this at a managed Redis. Upstash has a free tier that
    # is ample for rate-limit counters (they are small and short-lived):
    #   Upstash -> Redis -> Create database (region: ap-south-1 / ap-southeast-1)
    #   -> copy the "redis://" (TLS: "rediss://") URL into RATELIMIT_STORAGE_URI.
    # There is no Redis container any more; nothing to run locally.
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True
    # Off only for the end-to-end run, which registers dozens of accounts in a
    # few minutes and would otherwise spend its time testing the limiter.
    # _validate_config refuses to start a production app with this set.
    RATELIMIT_ENABLED = os.environ.get("RATELIMIT_ENABLED", "true").lower() != "false"

    # How many reverse proxies sit in front of the app and append to
    # X-Forwarded-For. Trusting too few makes every visitor share the proxy's
    # IP (one rate-limit bucket for everyone); trusting too many lets a client
    # forge its own address. Check with the admin System Health page.
    TRUSTED_PROXY_COUNT = int(os.environ.get("TRUSTED_PROXY_COUNT", "1"))

    # Phone-OTP sign-in needs something to deliver the code. No provider is
    # integrated yet, so this stays empty and the option stays hidden.
    SMS_PROVIDER = os.environ.get("SMS_PROVIDER", "")

    # CORS. The storefront is on its own origin now (Hostinger) and the API on
    # another (Render), so this is a real cross-origin setup with credentials:
    # the allow-list must be exact, and "*" is not legal with credentials.
    #
    # CORS_ORIGINS is a comma-separated list; apex and www are usually both
    # needed because a visitor can arrive at either before the redirect.
    FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
    CORS_ORIGINS = [
        o.strip().rstrip("/")
        for o in os.environ.get("CORS_ORIGINS", "").split(",")
        if o.strip()
    ] or [FRONTEND_ORIGIN]

    # Public storefront origin used to build absolute URLs in sitemap.xml /
    # robots.txt (canonical links, Open Graph). Defaults to the frontend origin.
    SITE_URL = os.environ.get("SITE_URL", os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173"))

    # Search-engine indexing. OFF for launch: a half-finished catalogue indexed
    # on day one is expensive to undo, because removing pages from an index is
    # far slower than adding them.
    #
    # OFF  -> robots.txt disallows everything, every page carries
    #         <meta name="robots" content="noindex">, sitemap.xml still builds
    #         (so it is ready) but is not advertised.
    # ON   -> normal robots.txt and no noindex tag.
    #
    # The environment variable is the floor: with INDEXING=false the admin
    # toggle cannot turn indexing on, so a live site cannot be exposed by a
    # mis-click in the dashboard.
    INDEXING = os.environ.get("INDEXING", "false").lower() in ("1", "true", "yes", "on")

    # Google OAuth
    GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

    # Razorpay (online payments)
    RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

    # Object storage for product images (Neon Object Storage, which speaks S3).
    # Required in production: Render's filesystem is ephemeral, so images
    # written to local disk vanish on the next deploy.
    #
    # Nothing here is Neon-specific -- any S3-compatible store works by
    # changing these values. Note the Neon endpoint embeds the BRANCH id, so
    # dev, test and production each have a different S3_ENDPOINT_URL.
    S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "")
    S3_BUCKET = os.environ.get("S3_BUCKET", "")
    S3_ACCESS_KEY_ID = os.environ.get("S3_ACCESS_KEY_ID", "")
    S3_SECRET_ACCESS_KEY = os.environ.get("S3_SECRET_ACCESS_KEY", "")
    S3_REGION = os.environ.get("S3_REGION", "auto")
    # What a browser fetches. Defaults to <endpoint>/<bucket>, which is correct
    # for a path-style public_read bucket; set it if you put a CDN in front.
    S3_PUBLIC_BASE_URL = os.environ.get("S3_PUBLIC_BASE_URL", "")
    S3_FORCE_PATH_STYLE = os.environ.get("S3_FORCE_PATH_STYLE", "true").lower() != "false"

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
    # Lax is correct for the storefront/API-subdomain split: same site, so the
    # cookie is sent, and it still does not ride along on requests from other
    # sites. "None" would only be needed for a different registrable domain.
    JWT_COOKIE_SAMESITE = os.environ.get("JWT_COOKIE_SAMESITE", "Lax")
    JWT_COOKIE_SECURE = True


class TestingConfig(BaseConfig):
    TESTING = True
    # Tests run against a real Postgres so enum types, computed columns and
    # triggers behave exactly as in production: the Neon "test" branch locally,
    # a service container in CI.
    #
    # No default on purpose. The suite TRUNCATEs every table in whatever it is
    # given, so a default is one typo away from emptying the wrong database;
    # backend/tests/conftest.py refuses to start without this set, and refuses
    # it outright if it names the dev or production branch.
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", UNSET_DATABASE_URL)
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
