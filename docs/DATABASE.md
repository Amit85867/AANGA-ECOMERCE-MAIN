# AANGA — database (dockerized Postgres)

The database runs in Docker rather than on Supabase's managed Postgres.
This document covers the layout, the one-time migration off Supabase, and the
backup/restore drill that Supabase used to do for you.

Object storage (product images) is **still Supabase** — see
[Still on Supabase](#still-on-supabase) at the bottom.

## Three databases, three compose files

| Purpose | File | Port | Persistence |
|---|---|---|---|
| Dev / production data | `backend/docker-compose.yml` | 55433 | named volume `aanga-pgdata` |
| pytest | `backend/docker-compose.test.yml` | 55432 | tmpfs, wiped on restart |
| Supabase (migration source) | — | — | read-only, being retired |

Port 55433 was chosen because 5432/5433 are usually taken by a local Postgres
install and 55432 belongs to the test database.

## Quick start

Add to `backend/.env` (see `.env.example`):

```bash
POSTGRES_USER=aanga
POSTGRES_PASSWORD=<pick-one>
POSTGRES_DB=aanga
POSTGRES_PORT=55433
DATABASE_URL=postgresql://aanga:<same-password>@127.0.0.1:55433/aanga
```

Then, from `backend/`:

```bash
docker compose up -d db
```

First boot runs `/docker-entrypoint-initdb.d` in order and builds the whole
schema. Watch it with `docker compose logs -f db`; it is ready when the
healthcheck reports `healthy` (`docker compose ps`).

| Script | Source file | Does |
|---|---|---|
| `00_bootstrap.sql` | `db/init/00_bootstrap.sql` | drops the stock `public` schema, creates `anon` / `authenticated` / `service_role` stub roles |
| `01_supabase_compat.sql` | `tests/sql/00_prereqs.sql` | `extensions.uuid_generate_v4()` + a stub `auth.uid()` |
| `02_schema.sql` | `schema.sql` | the canonical schema dump |

`tests/sql/00_prereqs.sql` is bind-mounted, not copied, so the dev container
and the test suite can never drift apart.

> **These scripts only run when the data volume is empty.** Editing them does
> nothing to a database that already exists. To rebuild from scratch:
> `docker compose down -v && docker compose up -d db` — which destroys all
> local data.

## Migrating the data off Supabase

One command, from `backend/`:

```bash
powershell -File .\db\migrate-from-supabase.ps1
```

It reads `POOLER_DATABASE_URL` from `.env`, dumps Supabase's `public` schema
into `db/backups/`, restores it into the container, and prints a per-table row
count of Supabase vs local so you can see the migration was complete.

Everything runs inside the `postgres:17` container, so no local `pg_dump` is
needed and the client version always matches the server. **Supabase is only
ever read from.**

### It also re-applies outstanding migrations

A dump reflects the state of the **live** Supabase database, which is not
necessarily what `schema.sql` describes. `migrations_orders_idempotency.sql`
(the `payment_ref` / `idempotency_key` unique indexes) was never applied to
Supabase, so a straight restore would silently drop the payment-integrity
guards a fresh container gets for free. The script re-applies it after the
restore; the file is `IF NOT EXISTS` throughout, so it is safe either way.

If that step fails, the restored data already violates the constraint. Find the
offenders with:

```sql
SELECT payment_ref, count(*) FROM orders
WHERE payment_ref IS NOT NULL GROUP BY payment_ref HAVING count(*) > 1;
```

Useful variants:

```bash
powershell -File .\db\migrate-from-supabase.ps1 -DumpOnly
powershell -File .\db\migrate-from-supabase.ps1 -RestoreOnly supabase-20260808-142530.dump
```

### Why the pooler URL

`db.<ref>.supabase.co` resolves to IPv6 only and is unreachable from inside a
container. The session pooler host is IPv4. Supabase → Project Settings →
Database → Connection string → **Session pooler**.

### Cutting over

1. Run the migration, confirm every row count matches.
2. In `backend/.env`, rename the Supabase `DATABASE_URL` to
   `SUPABASE_DATABASE_URL` (keeping it) and point `DATABASE_URL` at the
   container.
3. Restart the API and exercise a full checkout — the order path leans on
   triggers, so it is the honest smoke test.
4. Rolling back is a one-line edit while the Supabase project still exists.

Leave the Supabase project running until you have taken and *test-restored* at
least one local backup.

## Backups

Supabase did this for you. Now you do.

```bash
powershell -File .\db\backup.ps1            # -> db/backups/aanga-<timestamp>.dump
powershell -File .\db\backup.ps1 -Keep 30   # retention, default 14
```

```bash
powershell -File .\db\restore.ps1                                  # newest backup
powershell -File .\db\restore.ps1 -File aanga-20260808-030000.dump
```

`restore.ps1` is destructive: it drops `public`, re-applies the compat shims
and restores. It prompts unless given `-Force`.

Schedule `backup.ps1` daily (Task Scheduler on Windows, cron on a VPS) — and
**actually run a restore once** against a scratch database. An untested backup
is not a backup.

Dumps are gitignored (`backend/db/backups/`): they contain customer data.

## Re-dumping schema.sql

`schema.sql` is the canonical DDL, consumed by both the dev container and the
test suite. After changing the schema, re-dump it from whichever database is
now authoritative:

```bash
docker compose exec -T db pg_dump -U aanga -d aanga --schema=public --schema-only --no-owner --no-privileges > schema.sql
```

Commit the result. The test suite picks it up on the next run.

## Common problems

**`POSTGRES_PASSWORD is required` on `docker compose up`** — the three
`POSTGRES_*` variables are not in `backend/.env`. Compose reads that file for
interpolation.

**`invalid command \restrict` during init** — the Postgres image is older than
17.6. The dump was produced by pg_dump 17.6 and contains `\restrict`
meta-commands that older `psql` builds reject. Pull a current `postgres:17`.

**Init scripts appear to have been ignored** — the volume already existed. They
run only against an empty `aanga-pgdata`.

**Port 55433 already in use** — set `POSTGRES_PORT` in `.env` and update
`DATABASE_URL` to match.

**`FATAL: (ENOTFOUND) tenant/user postgres.<ref> not found`** — this is the
pooler answering, so DNS and TCP are fine; it simply has no such tenant. The
Supabase project is **paused or deleted**, not misconfigured, and no password
change will fix it. Free-tier projects auto-pause after a period of inactivity;
restore it from the Supabase dashboard before running the migration. A wrong
password gives `password authentication failed` instead.

**`role "anon" does not exist` during a restore** — the volume predates
`00_bootstrap.sql`. Create the roles by hand, or rebuild with
`docker compose down -v`.

## Still on Supabase

Migrating the database does **not** retire the Supabase account. Product images
still go to Supabase Storage (`app/services/storage.py`), and `_validate_config`
in `app/__init__.py` refuses to boot a production app without
`SUPABASE_URL` + `SUPABASE_SERVICE_KEY` — local disk is ephemeral on
Render/Railway, so images would vanish on redeploy.

To leave Supabase entirely, that backend has to be replaced first (MinIO in the
same compose stack, S3/R2, or a persistent volume on a host that has one).
Until then, keep the Storage credentials even after the database has moved.

Related: [DEPLOYMENT.md](DEPLOYMENT.md), `backend/tests/README.md`.
