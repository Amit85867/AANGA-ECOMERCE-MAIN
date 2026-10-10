"""Pytest fixtures.

The suite runs against a real Postgres (Docker) so enum types, computed
columns and triggers behave exactly as in production. Start it first:

    docker compose -f docker-compose.test.yml up -d

The canonical schema (`backend/schema.sql`, dumped from Supabase) is loaded
once per session on top of the Supabase prerequisites in tests/sql. Each test
starts from an empty set of tables (TRUNCATE) for isolation.
"""
import json
import os
import pathlib
import re

import psycopg2
import pytest
from flask import request
from sqlalchemy import text

# Force the testing config before the app package (and its config) import.
os.environ["FLASK_ENV"] = "testing"
os.environ.setdefault(
    "TEST_DATABASE_URL", "postgresql://postgres:test@localhost:55432/aanga_test"
)
# Keep auto-seeding out of tests so fixtures fully control the data.
os.environ.pop("ADMIN_EMAIL", None)
os.environ.pop("ADMIN_PASSWORD", None)

from app import create_app  # noqa: E402
from app.extensions import db as _db, limiter as _limiter  # noqa: E402

BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_SQL = BACKEND_DIR / "schema.sql"
PREREQS_SQL = pathlib.Path(__file__).resolve().parent / "sql" / "00_prereqs.sql"
TEST_DB_URL = os.environ["TEST_DATABASE_URL"]


# Newer pg_dump versions emit \restrict / \unrestrict psql meta-commands.
# psql understands them; psycopg2 does not, so drop those lines before executing.
_PSQL_META = re.compile(r"^\\(un)?restrict\b.*$", re.MULTILINE)


def _strip_psql_meta(sql: str) -> str:
    return _PSQL_META.sub("", sql)


def _rebuild_schema():
    """Drop and recreate the whole schema from the canonical dump."""
    try:
        conn = psycopg2.connect(TEST_DB_URL)
    except psycopg2.OperationalError as exc:  # pragma: no cover - setup guard
        pytest.exit(
            "Cannot reach the test database at "
            f"{TEST_DB_URL}.\nStart it with: "
            "docker compose -f docker-compose.test.yml up -d\n"
            f"({exc})",
            returncode=1,
        )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS public CASCADE;")
            cur.execute("DROP SCHEMA IF EXISTS auth CASCADE;")
            cur.execute("DROP SCHEMA IF EXISTS extensions CASCADE;")
            cur.execute(_strip_psql_meta(PREREQS_SQL.read_text()))
            cur.execute(_strip_psql_meta(SCHEMA_SQL.read_text()))
    finally:
        conn.close()


# Every (method, route, status) the suite produces, written out for
# scripts/gen_endpoints.py so docs/ENDPOINTS.md reports what is actually
# exercised rather than what someone remembered to tick.
ROUTE_COVERAGE_FILE = pathlib.Path(__file__).resolve().parent / ".route_coverage.json"


@pytest.fixture(scope="session")
def app():
    _rebuild_schema()
    application = create_app()
    seen = set()

    @application.after_request
    def _record(resp):
        if request.url_rule is not None:
            seen.add((request.method, request.url_rule.rule, resp.status_code))
        return resp

    with application.app_context():
        yield application

    ROUTE_COVERAGE_FILE.write_text(json.dumps(sorted(seen)))


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def _clean_db(app):
    """Empty every table and reset the ORM session before each test.

    Clearing the scoped session (identity map) is essential: TRUNCATE ...
    RESTART IDENTITY reuses ids, so a leftover object would otherwise mask the
    fresh row and leak state across tests.
    """
    _db.session.remove()
    rows = _db.session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    ).all()
    tables = [r[0] for r in rows]
    if tables:
        quoted = ", ".join(f'"{t}"' for t in tables)
        _db.session.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))
    _db.session.commit()
    # Rate-limit counters are per-IP and would otherwise bleed between tests.
    _limiter.reset()
    yield
    _db.session.rollback()
    _db.session.remove()
