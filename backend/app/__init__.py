"""AANGA Flask application factory."""
import os

import click
from flask import Flask, jsonify, request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash

from config import DEV_DATABASE_URL, get_config
from app.extensions import db, migrate, jwt, cors, limiter


def create_app(config_object=None):
    app = Flask(__name__, static_folder="../static", static_url_path="/static")
    app.config.from_object(config_object or get_config())

    from app.observability import init_logging, init_sentry
    init_sentry(app)   # as early as possible so startup errors are captured
    init_logging(app)

    _validate_config(app)
    _apply_proxy_fix(app)
    _init_extensions(app)
    _register_blueprints(app)
    _register_jwt_handlers(app)
    _register_error_handlers(app)
    _register_security_headers(app)
    _register_health(app)

    from app.services import audit, maintenance
    maintenance.init_app(app)
    audit.init_app(app)
    _warn_runtime_config(app)
    _register_cli(app)
    _auto_seed_admin(app)

    return app


def _is_dev_or_test(app):
    return bool(app.config.get("DEBUG") or app.config.get("TESTING"))


def _apply_proxy_fix(app):
    """Trust the platform's proxy for the client IP and scheme.

    On Render/Railway the app sits behind one reverse proxy, so ``remote_addr``
    is the proxy unless we honour X-Forwarded-For. Without this, rate limiting
    would key every request on the proxy's IP — one shared bucket for everyone.
    """
    if _is_dev_or_test(app):
        return
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)


def _register_error_handlers(app):
    """Always answer with JSON, and never leak a traceback in production."""

    @app.errorhandler(HTTPException)
    def _http_error(exc):
        return jsonify(error=exc.description or exc.name), exc.code

    @app.errorhandler(Exception)
    def _unhandled(exc):
        app.logger.exception("Unhandled exception")
        # A failed flush leaves the session unusable until it is rolled back;
        # do it here so the error cannot poison whatever runs next on it.
        db.session.rollback()
        # In dev/test let it propagate so the real stack trace surfaces.
        if _is_dev_or_test(app):
            raise exc
        return jsonify(error="Internal server error"), 500


def _register_security_headers(app):
    """Add hardening headers to every response.

    This service is a JSON API plus static product images — it renders no HTML
    of its own — so a strict `default-src 'none'` CSP is safe and clickjacking
    is fully denied. HSTS is production-only (dev is plain http).
    """
    hsts = not _is_dev_or_test(app)

    @app.after_request
    def _headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault(
            "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
        )
        # Product images are embedded by the storefront on a different origin.
        resp.headers.setdefault("Cross-Origin-Resource-Policy", "cross-origin")
        if hsts:
            resp.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return resp


def _register_health(app):
    @app.route("/api/health")
    def health():
        """Liveness + DB readiness probe for the platform."""
        try:
            db.session.execute(text("SELECT 1"))
        except Exception:
            app.logger.exception("Health check DB ping failed")
            return jsonify(status="degraded"), 503
        return jsonify(status="ok"), 200


def _warn_runtime_config(app):
    """Non-fatal production warnings (fatal ones live in _validate_config)."""
    if _is_dev_or_test(app):
        return
    if str(app.config.get("RATELIMIT_STORAGE_URI", "")).startswith("memory://"):
        app.logger.warning(
            "RATELIMIT_STORAGE_URI is memory:// — rate-limit counters are "
            "per-process. Point it at Redis before running more than one worker "
            "or instance, or limits will not be enforced globally."
        )


# Values that must never survive into a real deployment.
_WEAK_SECRETS = {"dev-secret-change-me", "dev-jwt-change-me", "", None}


def _validate_config(app):
    """Fail fast if a production app is missing real secrets or a real database.

    Skipped in debug/testing so local development keeps working with defaults.
    """
    if app.config.get("DEBUG") or app.config.get("TESTING"):
        return

    problems = []
    for key in ("SECRET_KEY", "JWT_SECRET_KEY"):
        value = app.config.get(key)
        if value in _WEAK_SECRETS:
            problems.append(f"{key} is unset or still the development default")
        elif len(str(value)) < 32:
            problems.append(f"{key} is too short (use at least 32 random characters)")

    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI") or ""
    if db_uri.startswith("sqlite"):
        problems.append(
            "DATABASE_URL points at SQLite — the schema is Postgres-native "
            "(enums, generated columns, triggers) and will not work"
        )
    elif db_uri == DEV_DATABASE_URL:
        # Seeing the fallback verbatim means DATABASE_URL was never set. Without
        # this the app would boot happily and only fail on the first query.
        problems.append(
            "DATABASE_URL is unset (falling back to the local docker-compose "
            "database)"
        )

    # Uploads would land on an ephemeral filesystem and be lost on redeploy,
    # silently breaking every product image.
    from app.services.storage import is_object_storage_configured
    if not is_object_storage_configured(app.config):
        problems.append(
            "SUPABASE_URL / SUPABASE_SERVICE_KEY are unset — product images "
            "would be written to an ephemeral disk and lost on the next deploy"
        )

    problems += _half_configured_integrations(os.environ)

    if problems:
        raise RuntimeError(
            "Refusing to start: insecure production configuration.\n  - "
            + "\n  - ".join(problems)
            + "\nSet these via environment variables before deploying."
        )


def _half_configured_integrations(env):
    """An integration is all-or-nothing.

    Razorpay and Shiprocket are optional — left blank the store runs COD-only
    and hides delivery checks. But switched on *without* their companion
    settings they fail quietly and expensively: payments are taken with no
    webhook to catch an abandoned checkout, or the delivery widget reports
    every PIN code as unserviceable.
    """
    def has(key):
        return bool((env.get(key) or "").strip())

    problems = []
    if has("RAZORPAY_KEY_ID") or has("RAZORPAY_KEY_SECRET"):
        for key in ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET"):
            if not has(key):
                problems.append(f"{key} is unset but Razorpay is otherwise configured")
        if not has("RAZORPAY_WEBHOOK_SECRET"):
            problems.append(
                "RAZORPAY_WEBHOOK_SECRET is unset — a checkout abandoned after "
                "capture would leave the customer charged with no order"
            )

    if has("SHIPROCKET_EMAIL") or has("SHIPROCKET_PASSWORD"):
        for key in ("SHIPROCKET_EMAIL", "SHIPROCKET_PASSWORD"):
            if not has(key):
                problems.append(f"{key} is unset but Shiprocket is otherwise configured")
        pincode = (env.get("SHIPROCKET_PICKUP_PINCODE") or "").strip()
        if not (len(pincode) == 6 and pincode.isdigit() and pincode[0] != "0"):
            problems.append(
                "SHIPROCKET_PICKUP_PINCODE must be the 6-digit PIN code of the "
                "Shiprocket pickup address"
            )
    return problems


def _init_extensions(app):
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    limiter.init_app(app)
    cors.init_app(
        app,
        origins=[app.config["FRONTEND_ORIGIN"]],
        supports_credentials=True,  # required for the httpOnly refresh cookie
        expose_headers=["X-CSRF-TOKEN"],
    )

    import app.models  # noqa: F401 – register models for Alembic


def _register_blueprints(app):
    from app.routes.auth import auth_bp
    from app.routes.products import products_bp
    from app.routes.categories import categories_bp
    from app.routes.cart import cart_bp
    from app.routes.wishlist import wishlist_bp
    from app.routes.orders import orders_bp
    from app.routes.returns import returns_bp
    from app.routes.addresses import addresses_bp
    from app.routes.reviews import reviews_bp
    from app.routes.profile import profile_bp
    from app.routes.offers import offers_bp
    from app.routes.contact import contact_bp
    from app.routes.wholesale import wholesale_bp
    from app.routes.newsletter import newsletter_bp
    from app.routes.admin import admin_bp
    from app.routes.cms import cms_bp
    from app.routes.payments import payments_bp
    from app.routes.shipping import shipping_bp
    from app.routes.seo import seo_bp

    for bp in (
        auth_bp, products_bp, categories_bp, cart_bp,
        wishlist_bp, orders_bp, returns_bp, addresses_bp, reviews_bp,
        profile_bp, offers_bp, contact_bp, wholesale_bp,
        newsletter_bp, admin_bp, cms_bp, payments_bp, shipping_bp, seo_bp,
    ):
        app.register_blueprint(bp)


def _register_jwt_handlers(app):
    @jwt.expired_token_loader
    def expired_token(jwt_header, jwt_payload):
        return {"error": "Token has expired"}, 401

    @jwt.invalid_token_loader
    def invalid_token(error_string):
        return {"error": "Invalid token"}, 401

    @jwt.unauthorized_loader
    def missing_token(error_string):
        return {"error": "Authorization required"}, 401

    @jwt.token_verification_loader
    def token_matches_surface(jwt_header, jwt_payload):
        """Admin tokens work only under /api/admin, customer tokens only outside it.

        Both are signed with the same key and carry a UUID subject, so without
        this an admin token passed @jwt_required on customer routes and acted
        as a customer who does not exist (a foreign-key 500 on the cart, an
        empty order list elsewhere).
        """
        is_admin_token = jwt_payload.get("actor") == "admin"
        return is_admin_token == request.path.startswith("/api/admin/")

    @jwt.token_verification_failed_loader
    def wrong_surface(jwt_header, jwt_payload):
        if jwt_payload.get("actor") == "admin":
            return {"error": "Admin tokens cannot be used on customer endpoints"}, 403
        return {"error": "Admin access required"}, 403


def _auto_seed_admin(app):
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        return

    with app.app_context():
        from app.models.admin import Admin
        try:
            if not Admin.query.filter_by(email=email).first():
                admin = Admin(
                    email=email,
                    password_hash=generate_password_hash(password),
                    full_name="Master Admin",
                    role="master",
                )
                db.session.add(admin)
                db.session.commit()
                app.logger.info(f"Auto-seeded master admin: {email}")
        except SQLAlchemyError:
            # Seeding is a convenience, not a startup requirement. Letting this
            # raise means a database that is merely slow to accept connections
            # (a cold managed instance, a container still starting) takes the
            # whole app down instead of booting and serving /api/health.
            db.session.rollback()
            app.logger.warning(
                "Could not auto-seed the master admin — the database was not "
                "reachable at startup. Run `flask seed-admin` once it is up.",
                exc_info=True,
            )


def _register_cli(app):
    @app.cli.command("reconcile-payments")
    @click.option("--hours", default=24, help="How far back to scan.")
    @click.option("--dry-run", is_flag=True, help="Report orphans without refunding.")
    def reconcile_payments(hours, dry_run):
        """Refund captured payments that never became an order.

        Safety net for a webhook that was never delivered. Schedule it (cron /
        platform scheduler) a few times a day:

            flask reconcile-payments --hours 24
        """
        from app.routes.payments import reconcile_orphaned_captures

        result = reconcile_orphaned_captures(
            window_seconds=hours * 3600, dry_run=dry_run
        )
        if not result.get("configured"):
            click.echo("Razorpay is not configured — nothing to reconcile.")
            return
        if result.get("error"):
            # Non-zero exit: a sweep that could not run is a failed run, and the
            # scheduler should say so rather than report success.
            raise click.ClickException(f"Could not reconcile: {result['error']}")

        click.echo(f"Checked {result['checked']} payment(s) from the last {hours}h.")
        if not result["orphans"]:
            click.echo("No orphaned captures found.")
            return
        for o in result["orphans"]:
            click.echo(f"  orphan {o['id']} amount={o['amount']} age={o['age']}s")
        if dry_run:
            click.echo(f"{len(result['orphans'])} orphan(s) found (dry run — nothing refunded).")
        else:
            click.echo(f"Refunded {result['refunded']} of {len(result['orphans'])} orphan(s).")
        if result.get("failed"):
            # Non-zero exit so the scheduler flags the run: these need a manual refund.
            raise click.ClickException(
                f"{result['failed']} refund(s) failed - "
                "see ORPHANED_CAPTURE_REFUND_FAILED in the logs."
            )

    @app.cli.command("seed-admin")
    @click.option("--email", default=None, help="Master admin email")
    @click.option("--password", default=None, help="Master admin password")
    @click.option("--name", default="Master Admin", help="Display name")
    def seed_admin(email, password, name):
        """Create the master admin account."""
        from app.models.admin import Admin

        email = email or os.environ.get("ADMIN_EMAIL")
        password = password or os.environ.get("ADMIN_PASSWORD")

        if not email or not password:
            click.echo("Error: Provide --email and --password, or set ADMIN_EMAIL / ADMIN_PASSWORD env vars.")
            return

        existing = Admin.query.filter_by(email=email).first()
        if existing:
            click.echo(f"Admin {email} already exists (role={existing.role}).")
            return

        admin = Admin(
            email=email,
            password_hash=generate_password_hash(password),
            full_name=name,
            role="master",
        )
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Master admin created: {email}")

    @app.cli.command("set-admin-password")
    @click.option("--email", default=None, help="Admin email (default: ADMIN_EMAIL)")
    def set_admin_password(email):
        """Change an existing admin's password.

        ADMIN_PASSWORD only seeds an account that does not exist yet, so editing
        it in .env never changes a live password — this does. The new password
        is read from ADMIN_PASSWORD, or prompted for; it is deliberately not a
        command-line option, which would leave it in shell history.
        """
        from app.models.admin import Admin

        email = email or os.environ.get("ADMIN_EMAIL")
        if not email:
            raise click.ClickException("Provide --email or set ADMIN_EMAIL.")

        admin = Admin.query.filter_by(email=email).first()
        if not admin:
            raise click.ClickException(f"No admin with email {email}.")

        password = os.environ.get("ADMIN_PASSWORD") or click.prompt(
            "New password", hide_input=True, confirmation_prompt=True
        )
        if len(password) < 12:
            raise click.ClickException("Use at least 12 characters.")

        admin.password_hash = generate_password_hash(password)
        db.session.commit()
        click.echo(f"Password updated for {email}.")
