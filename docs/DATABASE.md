# AANGA — database (Neon Postgres)

The database is **Neon** serverless Postgres. There is no local Postgres, no
Docker, and no Supabase database any more. Every environment — your laptop, CI
and Render — talks to a branch of one Neon project.

Object storage for product images is still Supabase (or local disk in
development); only the *database* moved.

## The project

| | |
|---|---|
| Project | `AANGA` (`dry-base-24522506`) |
| Region | AWS Asia Pacific 1, Singapore (`aws-ap-southeast-1`) |
| Postgres | 17 |
| Database | `aanga` |
| Role | `aanga_owner` |

## Three branches, one schema

| Branch | Used by | Compute | Auto-delete |
|---|---|---|---|
| `production` (default) | Render | 0.25 CU fixed | — |
| `dev` | your laptop | 0.25 ↔ 2 CU | Never |
| `test` | pytest, CI | 0.25 ↔ 2 CU | Never |

`dev` and `test` are branches *of* `production`, so they start as an exact copy
and cost storage only for what they change. Resetting a branch throws away its
changes and re-copies the parent — instant, and the normal way to get back to a
known state.

> **Auto-delete.** Neon's "Create branch" dialog defaults to **After 1 day**.
> Both branches here were created with **Never**. If you add a branch by hand,
> change that field or it will vanish overnight.

### Pooled vs direct

Every branch has two connection strings:

| | Host | Use for |
|---|---|---|
| **Pooled** | `…-pooler.…` | the application (PgBouncer, thousands of connections) |
| **Direct** | no `-pooler` | migrations, `pg_dump`/`pg_restore`, DDL, anything needing session state |

Both appear in `backend/.env`:

```
DATABASE_URL              dev, pooled     <- the app in development
DIRECT_DATABASE_URL       dev, direct     <- migrations, dumps
TEST_DATABASE_URL         test, pooled    <- pytest
TEST_DIRECT_DATABASE_URL  test, direct    <- test schema loads
```

**Production strings live only in the Render dashboard**, never in a file in
this repository.

### Connection limits

At 0.25 CU the production compute allows **105 direct** and **10,000 pooled**
connections. That is why the application uses the pooled string: the pool
ceiling stops being the thing you have to size around. See
`docs/DEPLOYMENT.md` for worker/pool arithmetic.

## Getting the connection strings

Never copy them out of the console into a terminal, a commit or a chat. Use the
CLI and redirect:

```bash
npm install -g neonctl
neonctl auth                      # browser sign-in, once

# write one into a file without it passing through your screen
neonctl connection-string dev \
  --project-id dry-base-24522506 --org-id org-long-mud-04364433 \
  --role-name aanga_owner --database-name aanga --pooled >> backend/.env
```

`backend/.env` is gitignored (`.gitignore` line 2).

Add `--pooled` for the pooled string, leave it off for the direct one.

## Loading a branch from scratch

`scripts/render_bootstrap_db.sh` is the only thing that builds the schema. It
needs a **direct** connection string, passed in the environment for that one
process:

```bash
DATABASE_URL="$(neonctl connection-string production \
  --project-id dry-base-24522506 --org-id org-long-mud-04364433 \
  --role-name aanga_owner --database-name aanga)" \
  scripts/render_bootstrap_db.sh
```

Order, all of it idempotent except the first load:

1. `backend/tests/sql/00_prereqs.sql` — `uuid-ossp` in an `extensions` schema,
   and a stub `auth.uid()` the row-level-security policies name.
2. `backend/schema.sql` — every table, enum, trigger, index and policy.
3. The six migrations listed in the script, in order.
4. Verification — table and trigger counts, named columns, tables, indexes,
   table ownership, and a check that no `@local.test` QA account leaked in.

Modes: no argument = fresh load (refuses a database that already has tables);
`--migrate` = apply migrations to an existing database; `--check` = report only.

## Adaptations needed for Neon

**None.** The schema, the prerequisites and all six migrations loaded into Neon
unchanged on the first attempt, and every verification check passed:

```
tables: 40   triggers: 10
ok  all 7 expected columns, all 10 expected tables, all 3 expected indexes
ok  all tables owned by aanga_owner
ok  no QA test accounts
```

This was not a given, so it is worth recording *why* nothing had to change:

| Thing that usually breaks on a managed Postgres | Why it did not here |
|---|---|
| `GRANT` / `REVOKE` to Supabase's `anon`, `authenticated`, `service_role` roles | `schema.sql` contains none — zero `GRANT`, `REVOKE`, `CREATE ROLE`, `ALTER … OWNER`, `ALTER DEFAULT PRIVILEGES`, `CREATE PUBLICATION` or `CREATE EVENT TRIGGER` statements |
| `CREATE EXTENSION` for an unavailable extension | the only extension is `uuid-ossp`, which Neon supports; it is created `WITH SCHEMA extensions` by the prereqs file |
| RLS policies calling Supabase's `auth.uid()` | the prereqs file creates a stub `auth.uid()` returning `NULL`; the app connects as the table owner and bypasses RLS anyway |
| `DROP SCHEMA public` refused | `aanga_owner` owns `public` on Neon and may drop it; the script only does so after confirming the database holds no tables |
| `\restrict` / `\unrestrict` psql meta-commands in the dump | the bootstrap runs real `psql`, which understands them (the Python test loader strips them — see `backend/tests/conftest.py`) |
| Version mismatch with a Postgres 17 dump | the Neon branch is Postgres 17 (17.11) |

So the record of adaptations is: **no SQL was modified, no statement was
skipped, and no object was created by hand.** If a future `schema.sql` re-dump
introduces role grants, this table is the list of things to re-check.

## Seeding the catalogue

Separate from the schema, and it goes through the **running admin API** so that
uploads take the real storage path:

```bash
python backend/db/seed_catalogue.py --api http://127.0.0.1:5000
```

It is idempotent (an existing slug is skipped) and creates 30 products, 90
variants, 30 images and 17 categories from the Stitch zip at the repo root,
resizing and re-encoding each image to WebP on the way in.

> ### ⚠️ The images follow whoever runs the API
>
> The seed uploads through the API, so the files land wherever **that**
> process's storage is configured to put them. The current `production` branch
> was seeded from a laptop with no Supabase keys, so its 30 `product_images`
> rows point at `/static/uploads/…` files that exist **only on that laptop**.
>
> Before go-live, do one of these:
>
> * replace the demo catalogue with real products through the admin UI (which
>   the pre-launch report lists as an owner task anyway), then
>   `flask --app run remove-demo-content`; or
> * re-run the seed against the **deployed** API once `SUPABASE_URL` and
>   `SUPABASE_SERVICE_KEY` are set, so the images are written to object storage; or
> * reset the `production` branch to drop the demo data entirely.

## Resetting a branch

The everyday way to get back to a known state. Destroys that branch's changes
and re-copies its parent:

```bash
neonctl branches reset dev  --project-id dry-base-24522506 \
  --org-id org-long-mud-04364433 --parent
neonctl branches reset test --project-id dry-base-24522506 \
  --org-id org-long-mud-04364433 --parent
```

After the initial load all three branches were verified identical:

```
                   production      dev     test
tables                     40       40       40
triggers                   10       10       10
db size                 10 MB    10 MB    10 MB
products                   30       30       30
product_variants           90       90       90
product_images             30       30       30
categories                 17       17       17
admins                      1        1        1
```

`scripts/reset_test_branch.sh` wraps the `test` reset and is what the test
suite uses before a full run.

## Backups

Neon keeps a continuous history and lets you branch or restore from any point
inside the retention window of your plan (**24 hours on the free plan** — check
this before launch; it is the single most important number here). That replaces
the old scheduled `pg_dump`.

It does **not** replace an off-platform copy. For anything you would be sorry
to lose, take a dump with the **direct** string and keep it somewhere else:

```bash
pg_dump "$DIRECT_DATABASE_URL" -Fc -f aanga-$(date +%Y%m%d).dump
pg_restore -d "$DIRECT_DATABASE_URL" --clean --if-exists aanga-20261013.dump
```

Point-in-time restore and branch-from-timestamp are in the Neon console under
the branch's **History**.

## Scale to zero

Every branch suspends after **5 minutes** of inactivity (fixed on the free
plan) and resumes on the next connection. The first query after a quiet period
therefore pays a cold start of roughly a second. Consequences:

* `pool_pre_ping` is on, so SQLAlchemy discards a connection the suspend closed
  instead of handing a dead one to a request.
* A health check that touches the database keeps the compute awake and burns
  CU-hours. `/api/ping` deliberately does not touch it; `/api/health` does.
* The first request after a deploy, or after a quiet night, is slow. That is
  the design, not a fault.

## What happened to the old setup

Everything Docker- and Supabase-shaped was removed in the Neon migration. If
you need to look at it:

```bash
git checkout pre-neon-docker
```

Gone: `backend/docker-compose.yml` (local Postgres on 55433),
`backend/docker-compose.test.yml` (pytest Postgres on 55432),
`scripts/prod_local/` and `scripts/prod_local.sh` (the four-container
production-like stack), `backend/db/init/` (container bootstrap scripts),
`backend/db/migrate-from-supabase.ps1`, `backend/db/backup.ps1`,
`backend/db/restore.ps1` and `backend/Dockerfile`.

Kept and now pointed at Neon: `backend/schema.sql`, the `migrations_*.sql`
files, `backend/tests/sql/00_prereqs.sql`, `backend/db/seed_catalogue.py` and
`scripts/render_bootstrap_db.sh`.
