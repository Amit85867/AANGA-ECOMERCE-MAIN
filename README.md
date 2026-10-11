# AANGA

An online clothing store: a Flask API (`backend/`), a React storefront and
admin dashboard (`frontend/`), and Postgres in Docker.

## Start it (one command)

You need Docker Desktop running, Python 3.11+, Node 20+, and `backend/.env`
(copy `backend/.env.example` and fill it in — see `docs/DATABASE.md` for the
database values).

**Windows (PowerShell), from this folder:**

```powershell
powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
```

**macOS / Linux / Git Bash:**

```bash
scripts/dev.sh
```

It starts the database, applies any pending migrations, starts the API and
then the storefront — checking each before the next — and prints:

| | |
|---|---|
| Storefront | http://localhost:5173 |
| Admin dashboard | http://localhost:5173/admin |
| API health | http://127.0.0.1:5000/api/health |

To stop the API and storefront: `scripts\dev.ps1 -Stop` (or `scripts/dev.sh --stop`).
The database container keeps running; `docker compose stop db` in `backend/`
stops it.

## If something does not load

1. Sign in to the admin and open **Store → System health**. It shows whether
   the database is reachable, whether migrations are pending, and the state of
   every integration.
2. The same check from a terminal, in `backend/`:

   ```bash
   venv/Scripts/python -m flask --app run check-schema     # Windows
   venv/bin/python -m flask --app run check-schema         # macOS / Linux
   ```

3. Look at the API's window (or `.dev/api.log`). At startup it logs one of
   `DATABASE_OK`, `DATABASE_MIGRATIONS_PENDING …` or `DATABASE_UNREACHABLE …`.
4. If a page loaded while the API was still starting, reload it.

## Doing the steps by hand

```bash
cd backend
docker compose up -d db                                   # 1. database
venv/Scripts/python -m flask --app run apply-migrations   # 2. migrations (safe to repeat)
venv/Scripts/python run.py                                # 3. API on :5000

cd ../frontend
npm run dev                                               # 4. storefront on :5173
```

Start the API before the storefront, and only one of each: a second API on the
same port answers some requests and not others.

## Database migrations

One command, safe to run any number of times:

```bash
cd backend
venv/Scripts/python -m flask --app run apply-migrations
```

It applies whichever of the `backend/migrations_*.sql` files have not been
applied yet to the database in `DATABASE_URL`. A brand-new, empty database is
loaded with `scripts/render_bootstrap_db.sh` instead (see `docs/DEPLOYMENT.md`).
To add a migration, see the top of `backend/app/services/schema_check.py`.

## Tests

```bash
cd backend
docker compose -f docker-compose.test.yml up -d    # throwaway Postgres on :55432
venv/Scripts/python -m pytest

cd ../frontend
npm run lint && npm run build
```

## Where things are written down

| | |
|---|---|
| `docs/OWNER_GUIDE.md` | Running the store from the admin dashboard (also under **Help** in the admin) |
| `docs/ADMIN_CAPABILITIES.md` | What each role can do |
| `docs/DEPLOYMENT.md` | Deploying to Render |
| `docs/DATABASE.md` | The local database, backups and restores |
| `docs/ENDPOINTS.md` | Every API route (generated) |
| `docs/DEMO_ASSETS.md` | Where the demo images came from |
| `docs/LOAD_TEST.md` | The k6 load test for staging |
| `docs/SECURITY_TODO.md` | Security follow-ups |
| `docs/PROGRESS.md` | What has been done, round by round |

## Before a deploy

```
scripts/prod_local.sh        # a production-like copy on http://localhost:8080 (Docker)
scripts/e2e.sh               # every customer and admin flow, at four screen widths
scripts/prod_local.sh down   # remove the copy
```

`scripts/prod_local.sh` builds the store the way Render will (new database from
`scripts/render_bootstrap_db.sh`, the backend image under gunicorn, Redis, the
built storefront) and loads the demo content. `scripts/e2e.sh --fresh` rebuilds
it first. The audit that these came from is in `docs/PRELAUNCH_REPORT.md`; the
steps for adding payment and courier keys are in `docs/GO_LIVE.md`.
