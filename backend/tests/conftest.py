"""Pytest fixtures.

The suite runs against a real Postgres so enum types, computed columns and
triggers behave exactly as in production. That is the Neon **test** branch
locally, or the Postgres service container in GitHub Actions.

    TEST_DATABASE_URL   required, no default (see docs/DATABASE.md)

The canonical schema (`backend/schema.sql`) is loaded once per session on top
of the prerequisites in tests/sql. Each test starts from an empty set of
tables (TRUNCATE) for isolation.

Every test TRUNCATEs every table, so pointing this at the wrong branch would
destroy it. `_refuse_wrong_branch` below makes that impossible to do by
accident.
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
# Keep auto-seeding out of tests so fixtures fully control the data.
os.environ.pop("ADMIN_EMAIL", None)
os.environ.pop("ADMIN_PASSWORD", None)

from app import create_app  # noqa: E402
from app.extensions import db as _db, limiter as _limiter  # noqa: E402
from app.services import cache as _cache, maintenance as _maintenance  # noqa: E402

BACKEND_DIR = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_SQL = BACKEND_DIR / "schema.sql"
PREREQS_SQL = pathlib.Path(__file__).resolve().parent / "sql" / "00_prereqs.sql"


def _endpoint(url):
    """The Neon endpoint a URL points at, e.g. 'ep-nameless-truth-b372e4ty'.

    Pooled and direct strings for one branch differ only by a '-pooler' suffix
    on the host, so stripping it makes the two comparable. Returns '' for a
    non-Neon host (a CI service container), which never matches.
    """
    if not url:
        return ""
    m = re.search(r"@([^/?\s]+)", url)
    if not m:
        return ""
    host = m.group(1).split(":")[0]
    if not host.endswith(".neon.tech"):
        return ""
    return host.split(".")[0].replace("-pooler", "")


def _refuse_wrong_branch():
    """Refuse to run if TEST_DATABASE_URL is not the test branch.

    The suite TRUNCATEs every table in the database it is given. Run against
    `dev` that costs you your local data; against `production` it costs you the
    shop. Both are one copy-paste away, so this is a hard stop, not a warning.
    """
    test_url = os.environ.get("TEST_DATABASE_URL")
    if not test_url:
        raise SystemExit(
            "TEST_DATABASE_URL is not set.\n"
            "It must point at the Neon *test* branch. See docs/DATABASE.md:\n"
            "  neonctl connection-string test --project-id dry-base-24522506 \\\n"
            "    --org-id org-long-mud-04364433 --role-name aanga_owner \\\n"
            "    --database-name aanga --pooled"
        )

    target = _endpoint(test_url)
    if not target:
        return  # not a Neon host: a CI service container, nothing to protect

    forbidden = {
        _endpoint(os.environ.get("DATABASE_URL")): "dev (DATABASE_URL)",
        _endpoint(os.environ.get("DIRECT_DATABASE_URL")): "dev (DIRECT_DATABASE_URL)",
        _endpoint(os.environ.get("PRODUCTION_DATABASE_URL")): "production",
        _endpoint(os.environ.get("NEON_PRODUCTION_ENDPOINT")): "production",
    }
    # The production endpoint can also be pinned by name alone, so that a
    # machine which never holds a production URL can still be protected.
    pinned = (os.environ.get("NEON_PRODUCTION_ENDPOINT") or "").strip()
    if pinned and pinned.replace("-pooler", "") == target:
        forbidden[target] = "production"
    forbidden.pop("", None)

    if target in forbidden:
        raise SystemExit(
            f"Refusing to run the tests: TEST_DATABASE_URL points at the "
            f"{forbidden[target]} branch.\n"
            "Every test TRUNCATEs every table. Point TEST_DATABASE_URL at the "
            "Neon 'test' branch and run again (docs/DATABASE.md)."
        )


_refuse_wrong_branch()
TEST_DB_URL = os.environ["TEST_DATABASE_URL"]


# Newer pg_dump versions emit \restrict / \unrestrict psql meta-commands.
# psql understands them; psycopg2 does not, so drop those lines before executing.
_PSQL_META = re.compile(r"^\\(un)?restrict\b.*$", re.MULTILINE)


def _strip_psql_meta(sql: str) -> str:
    return _PSQL_META.sub("", sql)


# Schema loads go over the DIRECT endpoint, never the pooled one.
#
# schema.sql is a pg_dump and so contains
#   SELECT pg_catalog.set_config('search_path', '', false);
# Run through PgBouncer that setting outlives the client: the pooler keeps the
# server connection and hands it to the next client with an empty search_path,
# after which every unqualified table name fails with "relation ... does not
# exist" even though the table is there. Falls back to the pooled URL when
# there is no separate direct one (the CI service container).
DDL_DB_URL = os.environ.get("TEST_DIRECT_DATABASE_URL") or os.environ["TEST_DATABASE_URL"]


def _rebuild_schema():
    """Drop and recreate the whole schema from the canonical dump."""
    try:
        conn = psycopg2.connect(DDL_DB_URL)
    except psycopg2.OperationalError as exc:  # pragma: no cover - setup guard
        # Never echo the URL: it carries the password.
        pytest.exit(
            "Cannot reach the test database.\n"
            "Check TEST_DATABASE_URL points at the Neon 'test' branch and that "
            "you are online (docs/DATABASE.md).\n"
            f"({type(exc).__name__})",
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
        # Schema-qualified on purpose: a pooled connection can come back with an
        # empty search_path (see DDL_DB_URL above), and an unqualified name
        # would then fail for a table that plainly exists.
        quoted = ", ".join(f'public."{t}"' for t in tables)
        _db.session.execute(text(f"TRUNCATE {quoted} RESTART IDENTITY CASCADE"))
    _db.session.commit()
    # Rate-limit counters are per-IP and would otherwise bleed between tests.
    _limiter.reset()
    # So would cached responses and the maintenance flag: both outlive the rows
    # they were built from.
    _cache.reset_for_tests()
    _maintenance.reset_cache()
    yield
    _db.session.rollback()
    _db.session.remove()


# ── Object storage ────────────────────────────────────────────────────────
class _FakeS3:
    """An in-memory stand-in for the S3 client boto3 would build.

    Only the four calls objectstore makes. Keeping the suite offline matters
    here: the real bucket is shared, and a test that deleted from it would take
    the storefront's images with it.
    """

    def __init__(self):
        self.objects = {}          # key -> {"Body", "ContentType", "CacheControl"}
        self.fail_on_put = False

    # -- the boto3 surface --
    def put_object(self, Bucket=None, Key=None, Body=None, ContentType=None,
                   CacheControl=None, **_):
        if self.fail_on_put:
            from botocore.exceptions import ClientError
            raise ClientError({"Error": {"Code": "AccessDenied",
                                         "Message": "denied"}}, "PutObject")
        self.objects[Key] = {"Body": Body, "ContentType": ContentType,
                             "CacheControl": CacheControl}
        return {}

    def delete_object(self, Bucket=None, Key=None, **_):
        self.objects.pop(Key, None)
        return {}

    def head_object(self, Bucket=None, Key=None, **_):
        if Key not in self.objects:
            from botocore.exceptions import ClientError
            raise ClientError({"Error": {"Code": "404", "Message": "not found"}},
                              "HeadObject")
        return {}

    def get_paginator(self, _name):
        objects = self.objects

        class _P:
            def paginate(self, Bucket=None, Prefix="", **_):
                yield {"Contents": [{"Key": k} for k in sorted(objects)
                                    if k.startswith(Prefix)]}
        return _P()

    # -- helpers for assertions --
    def keys(self):
        return sorted(self.objects)

    def body(self, key):
        return self.objects[key]["Body"]

    def content_type(self, key):
        return self.objects[key]["ContentType"]

    def cache_control(self, key):
        return self.objects[key]["CacheControl"] or ""


@pytest.fixture()
def fake_s3(app, monkeypatch):
    """Configure object storage and serve it from memory."""
    from app.services import objectstore

    settings = {
        "S3_ENDPOINT_URL": "https://s3.example",
        "S3_BUCKET": "test-bucket",
        "S3_ACCESS_KEY_ID": "key",
        "S3_SECRET_ACCESS_KEY": "secret",
        "S3_REGION": "ap-southeast-1",
        "S3_PUBLIC_BASE_URL": "",
        "S3_FORCE_PATH_STYLE": True,
    }
    for name, value in settings.items():
        monkeypatch.setitem(app.config, name, value)

    fake = _FakeS3()
    monkeypatch.setattr(objectstore, "client", lambda config=None: fake)
    objectstore.reset_client()
    yield fake
    objectstore.reset_client()
