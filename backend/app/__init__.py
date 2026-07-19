"""AANGA Flask application factory."""
import os

import click
from flask import Flask
from werkzeug.security import generate_password_hash

from config import get_config
from app.extensions import db, migrate, jwt, cors, limiter


def create_app(config_object=None):
    app = Flask(__name__, static_folder="../static", static_url_path="/static")
    app.config.from_object(config_object or get_config())

    _validate_config(app)
    _init_extensions(app)
    _register_blueprints(app)
    _register_jwt_handlers(app)
    _register_cli(app)
    _auto_seed_admin(app)

    return app


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
        problems.append("DATABASE_URL is unset (falling back to SQLite)")

    if problems:
        raise RuntimeError(
            "Refusing to start: insecure production configuration.\n  - "
            + "\n  - ".join(problems)
            + "\nSet these via environment variables before deploying."
        )


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

    for bp in (
        auth_bp, products_bp, categories_bp, cart_bp,
        wishlist_bp, orders_bp, addresses_bp, reviews_bp,
        profile_bp, offers_bp, contact_bp, wholesale_bp,
        newsletter_bp, admin_bp, cms_bp, payments_bp,
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


def _auto_seed_admin(app):
    email = os.environ.get("ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        return

    with app.app_context():
        from app.models.admin import Admin
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


def _register_cli(app):
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
