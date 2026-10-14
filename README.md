# AANGA

An online clothing store: a Flask API (`backend/`), a React storefront and
admin dashboard (`frontend/`), and **Neon** serverless Postgres.

There is no Docker anywhere — nothing to install, start or keep running. The
database lives in the cloud and every environment talks to a branch of it.

## Set up (first time, about five minutes)

You need Python 3.12, Node 20+ and a Neon account.

1. **Get the connection strings.** Never paste one into a terminal or a commit;
   redirect them straight into the file:

   ```bash
   npm install -g neonctl
   neonctl auth                       # browser sign-in, once

   cd backend && cp .env.example .env
   ```

   Then append the four database lines, from `docs/DATABASE.md` §"Getting the
   connection strings". `backend/.env` is gitignored.

2. **Fill in the rest of `backend/.env`.** Only `SECRET_KEY`, `JWT_SECRET_KEY`,
   `ADMIN_EMAIL` and `ADMIN_PASSWORD` are needed to start; every integration
   (payments, courier, email) is optional and the store runs without it.

3. **Start everything:**

   **Windows (PowerShell), from this folder:**

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
   ```

   **macOS / Linux / Git Bash:**

   ```bash
   scripts/dev.sh
   ```

It checks the database is reachable, applies any pending migrations, starts the
API and then the storefront — checking each before the next — and prints:

| | |
|---|---|
| Storefront | http://localhost:5173 |
| Admin dashboard | http://localhost:5173/admin |
| API liveness | http://127.0.0.1:5000/api/ping |
| API + database | http://127.0.0.1:5000/api/health |

To stop: `scripts\dev.ps1 -Stop` (or `scripts/dev.sh --stop`). There is nothing
else to shut down; Neon suspends itself after five idle minutes.

> **The first request after a quiet spell takes about a second.** Neon scales
> the branch to zero after five minutes and wakes it on the next connection.
> That is the design, not a fault.

## If something does not load

1. Sign in to the admin and open **Store → System health**: whether the
   database is reachable, whether migrations are pending, and the state of
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
venv/Scripts/python -m flask --app run apply-migrations   # 1. migrations (safe to repeat)
venv/Scripts/python run.py                                # 2. API on :5000

cd ../frontend
npm run dev                                               # 3. storefront on :5173
```

Start the API before the storefront, and only one of each: a second API on the
same port answers some requests and not others.

## Database

Three branches of one Neon project: `production` (Render), `dev` (your laptop)
and `test` (pytest). Full detail — pooled vs direct strings, resetting a branch,
backups, what the schema load needed — is in **`docs/DATABASE.md`**.

Migrations, safe to run any number of times:

```bash
cd backend
venv/Scripts/python -m flask --app run apply-migrations
```

A brand-new, empty branch is loaded with `scripts/render_bootstrap_db.sh`
instead. To add a migration, see the top of
`backend/app/services/schema_check.py`.

## Tests

The suite runs against the Neon **test** branch. It TRUNCATEs every table, so
`conftest.py` refuses to start if `TEST_DATABASE_URL` points at `dev` or
`production`.

```bash
scripts/reset_test_branch.sh        # reset the test branch, then the full suite

cd backend && venv/Scripts/python -m pytest     # or just the suite
cd ../frontend && npm run lint && npm run build
```

CI runs the backend suite against a Postgres service container rather than the
shared test branch — see the comment at the top of `.github/workflows/ci.yml`
for why, and how to point it at Neon instead.

## Before a deploy

```bash
scripts/e2e.sh            # every customer and admin flow, at four screen widths
scripts/e2e.sh --fresh    # reset the dev branch and reseed first
```

The suite drives the local stack on :5173 against the Neon dev branch, with
rate limiting off for the run (it registers dozens of accounts; no test asserts
limiting). The audit these came from is in `docs/PRELAUNCH_REPORT.md`; the
steps for adding payment and courier keys are in `docs/GO_LIVE.md`.

## Where things are written down

| | |
|---|---|
| `docs/OWNER_GUIDE.md` | Running the store from the admin dashboard (also under **Help** in the admin) |
| `docs/ADMIN_CAPABILITIES.md` | What each role can do |
| `docs/DATABASE.md` | Neon: branches, connection strings, loading, resetting, backups |
| `docs/DEPLOYMENT.md` | Deploying to Render (native Python runtime) |
| `docs/RUNBOOK.md` | When something is wrong in production |
| `docs/GO_LIVE.md` | Turning on payments and the courier |
| `docs/ENDPOINTS.md` | Every API route (generated) |
| `docs/DEMO_ASSETS.md` | Where the demo images came from |
| `docs/LOAD_TEST.md` | The k6 load test for staging |
| `docs/SECURITY_TODO.md` | Security follow-ups |
| `docs/PROGRESS.md` | What has been done, round by round |
