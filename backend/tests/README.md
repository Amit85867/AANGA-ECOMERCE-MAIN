# Running the tests

The suite runs against a real **Postgres** so enum types, computed columns and
triggers behave exactly as they do in production. This is deliberate — several
bugs (e.g. triggers and app code both deducting stock) are invisible against
SQLite.

That Postgres is the Neon **test** branch locally, and a service container in
GitHub Actions. There is no Docker in local development.

## One-time setup

```bash
cd backend
python -m venv venv                                  # if you don't already have one
venv/Scripts/pip install -r requirements-dev.txt     # Windows
# or: venv/bin/pip install -r requirements-dev.txt   # macOS/Linux
```

Then put the Neon **test** branch's strings in `backend/.env` — see
[docs/DATABASE.md](../../docs/DATABASE.md):

```
TEST_DATABASE_URL         test branch, pooled    <- the app under test
TEST_DIRECT_DATABASE_URL  test branch, direct    <- loading the schema
```

Both are required. There is no default and nothing to start.

## Every run

```bash
venv/Scripts/python -m pytest        # Windows
# or: venv/bin/python -m pytest       # macOS/Linux
```

Or, to put the schema back to whatever `production` has first — which is what
catches "the tests pass against a schema nobody will deploy":

```bash
scripts/reset_test_branch.sh             # reset, then the whole suite
scripts/reset_test_branch.sh -k payments # reset, then a subset
```

> **The suite TRUNCATEs every table in the database it is given.** `conftest.py`
> refuses to start if `TEST_DATABASE_URL` points at the `dev` or `production`
> branch. Pin the production endpoint in `NEON_PRODUCTION_ENDPOINT` so that
> protection works even on a machine that holds no production URL.

It is slower than it used to be against a container on localhost: every test
truncates forty tables, and each round trip now crosses the network to
Singapore. That is the cost of having one real Postgres everywhere instead of
three different ones.

## How it works

- `conftest.py` rebuilds the schema once per session from **`../schema.sql`**
  on top of `sql/00_prereqs.sql` (the `uuid-ossp` extension and the stub
  `auth.uid()` the row-level-security policies name).
- That rebuild goes over **`TEST_DIRECT_DATABASE_URL`**, never the pooled one.
  `schema.sql` is a `pg_dump` and contains
  `SELECT pg_catalog.set_config('search_path', '', false)`; through PgBouncer
  that setting outlives the client and the next caller gets a connection where
  unqualified table names no longer resolve.
- Every test starts from empty tables (`TRUNCATE ... RESTART IDENTITY`, names
  schema-qualified for the same reason) with a fresh ORM session.
- `factories.py` has small helpers to build users, products, carts, etc.

## Keeping schema.sql current

`schema.sql` is the source of truth in Git. After changing the schema, re-dump
it from the branch that has the change, using that branch's **direct** string:

```bash
pg_dump "$DIRECT_DATABASE_URL" --schema=public --schema-only \
  --no-owner --no-privileges --no-comments > schema.sql
```

Check the diff before committing: a dump reorders things, and a re-dump that
introduces `GRANT` or `OWNER TO` statements is the one thing that would stop it
loading cleanly into a fresh branch (see
[docs/DATABASE.md](../../docs/DATABASE.md#adaptations-needed-for-neon)).
