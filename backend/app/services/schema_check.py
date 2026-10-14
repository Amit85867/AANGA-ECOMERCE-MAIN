"""Is the database the one this code expects?

The schema is kept in ``schema.sql`` plus a short list of idempotent migration
files (there is no Alembic history). A migration is "pending" when something it
creates is not in the database yet, so this module knows one or two objects per
migration and looks for them. It is used in three places:

* at startup, to log clearly when the database is unreachable or behind;
* by the admin System Health page;
* by ``flask apply-migrations``, to report what it did.

To add a migration: put the file in ``backend/``, add it to ``MIGRATIONS`` with
something it creates, and add it to ``scripts/render_bootstrap_db.sh``.
"""
import pathlib

from sqlalchemy import text

from app.extensions import db

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[2]

# (file, [things it creates]) in the order they are applied. A thing is
# "table", "table.column" or "index:name".
MIGRATIONS = [
    ("migrations_orders_idempotency.sql", ["orders.idempotency_key", "index:uq_orders_payment_ref"]),
    ("migrations_hero_badges.sql", ["hero_banners.pill_label"]),
    ("migrations_address_archive.sql", ["addresses.archived_at"]),
    ("migrations_ops_tables.sql", ["webhook_events", "job_runs"]),
    ("migrations_admin_ops.sql", ["audit_log"]),
    ("migrations_owner_dashboard.sql", [
        "collections", "campaigns", "homepage_sections", "nav_links", "cms_pages", "faq_items",
        "media_assets", "products.is_demo", "products.meta_title", "hero_banners.campaign_id",
        "coupons.campaign_id",
    ]),
]
# Without these there is no schema at all (schema.sql was never loaded).
_BASE_TABLES = ["users", "products", "orders"]


def _present(connection):
    """Every table, column and index in the public schema, as a set of the
    same strings MIGRATIONS uses."""
    found = set()
    for (table,) in connection.execute(text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
    )):
        found.add(table)
    for table, column in connection.execute(text(
        "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema = 'public'"
    )):
        found.add(f"{table}.{column}")
    for (index,) in connection.execute(text(
        "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
    )):
        found.add(f"index:{index}")
    return found


def status():
    """``{"reachable", "empty", "pending": [files], "missing": [objects], "error"}``.

    Never raises: an unreachable database is a result, not an exception.
    """
    try:
        # Its own connection, so a failure here cannot leave a request's
        # session in a broken transaction.
        with db.engine.connect() as connection:
            found = _present(connection)
    except Exception as exc:  # noqa: BLE001
        reason = str(getattr(exc, "orig", exc)).strip().splitlines()[0] if str(exc).strip() else type(exc).__name__
        return {"reachable": False, "empty": False, "pending": [], "missing": [], "error": reason[:300]}

    if not all(table in found for table in _BASE_TABLES):
        return {"reachable": True, "empty": True, "pending": [name for name, _ in MIGRATIONS], "missing": _BASE_TABLES, "error": None}

    pending, missing = [], []
    for name, creates in MIGRATIONS:
        absent = [thing for thing in creates if thing not in found]
        if absent:
            pending.append(name)
            missing.extend(absent)
    return {"reachable": True, "empty": False, "pending": pending, "missing": missing, "error": None}


def describe(result):
    """One sentence a person can act on."""
    if not result["reachable"]:
        return f"The database cannot be reached: {result['error']}"
    if result["empty"]:
        return "The database has no tables. Load backend/schema.sql (scripts/render_bootstrap_db.sh), then run: flask apply-migrations"
    if result["pending"]:
        return (
            f"{len(result['pending'])} migration(s) have not been applied: {', '.join(result['pending'])}. "
            "Run: flask apply-migrations"
        )
    return "Up to date."


def apply_pending(all_files=False):
    """Run the migration files (pending ones, or all — they are idempotent).

    Returns the list of files applied. Each file runs in its own transaction.
    """
    before = status()
    if not before["reachable"]:
        raise RuntimeError(describe(before))
    if before["empty"]:
        raise RuntimeError(describe(before))
    names = [name for name, _ in MIGRATIONS] if all_files else before["pending"]
    applied = []
    for name in names:
        sql = (BACKEND_DIR / name).read_text(encoding="utf-8")
        with db.engine.begin() as connection:
            # Adding a column needs the table to itself for an instant. If
            # something is holding it, fail with a clear message rather than
            # wait for ever.
            connection.exec_driver_sql("SET LOCAL lock_timeout = '20s'")
            connection.exec_driver_sql(sql)
        applied.append(name)
    return applied
