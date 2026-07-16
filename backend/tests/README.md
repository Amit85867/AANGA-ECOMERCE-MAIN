# Running the tests

The suite runs against a real **Postgres** (in Docker) so enum types, computed
columns and triggers behave exactly as they do in production on Supabase. This
is deliberate — several bugs (e.g. triggers and app code both deducting stock)
are invisible against SQLite.

## One-time setup

```bash
cd backend
python -m venv venv                 # if you don't already have one
venv/Scripts/pip install -r requirements-dev.txt   # Windows
# or: venv/bin/pip install -r requirements-dev.txt  # macOS/Linux
```

## Every run

```bash
# 1. Start the throwaway test database (host port 55432, data kept in RAM)
docker compose -f docker-compose.test.yml up -d

# 2. Run the suite
venv/Scripts/python -m pytest        # Windows
# or: venv/bin/python -m pytest       # macOS/Linux

# 3. (optional) stop the database
docker compose -f docker-compose.test.yml down
```

## How it works

- `conftest.py` rebuilds the schema once per session from **`../schema.sql`**
  (the canonical dump of the Supabase `public` schema) on top of
  `sql/00_prereqs.sql` (the Supabase extensions/`auth.uid()` helpers a plain
  Postgres lacks).
- Every test starts from empty tables (`TRUNCATE ... RESTART IDENTITY`) with a
  fresh ORM session.
- `factories.py` has small helpers to build users, products, carts, etc.

## Keeping schema.sql current

`schema.sql` is the source of truth in Git. When the Supabase schema changes,
re-dump it (uses the session-pooler URL, which is IPv4):

```bash
docker run --rm -e PGURL="$POOLER_DATABASE_URL" postgres:latest \
  sh -c 'pg_dump "$PGURL" --schema=public --schema-only --no-owner \
  --no-privileges --no-comments' > schema.sql
```
