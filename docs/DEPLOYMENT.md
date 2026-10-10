# AANGA — Deployment runbook

Backend: Flask + gunicorn (Docker). Frontend: static Vite build. Database:
**dockerized Postgres** (`backend/docker-compose.yml`) — see
[DATABASE.md](DATABASE.md). Object storage: Supabase Storage (still). Target
hosts: Render / Railway (backend), any static host / CDN (frontend).

## 1. Prerequisites (one-time)

1. **Postgres** — `docker compose -f backend/docker-compose.yml up -d db`, which
   builds the full schema on first boot. Migrating existing data off Supabase is
   a single command; the whole procedure, plus backups, is in
   **[DATABASE.md](DATABASE.md)**.
2. **Supabase Storage** — a **public** bucket named `product-images`
   (Storage → New bucket). Only Storage is still Supabase; the database has
   moved. The app refuses to boot in production without it.
3. **SQL migrations** — a container built from `schema.sql` already includes
   every migration under `backend/`. They matter only when restoring a dump
   taken from the old Supabase database, and `db/migrate-from-supabase.ps1`
   re-applies the outstanding ones (`migrations_orders_idempotency.sql`)
   automatically after the restore.
3. **Razorpay** live keys (or leave blank for COD-only).
4. **Resend** account + a verified sending domain for `EMAIL_FROM`.
5. **Redis** instance (Render/Railway add-on) for rate limiting across >1
   instance — see step 4.
6. Optional: **Sentry** project DSN.

## 2. Environment variables

Copy `backend/.env.example` and fill in. The app **refuses to boot in
production** (`_validate_config`) unless these are real:

| Variable | Notes |
|---|---|
| `FLASK_ENV=production` | selects `ProductionConfig` |
| `SECRET_KEY`, `JWT_SECRET_KEY` | ≥32 random chars each, distinct |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | drive the `db` container; `POSTGRES_PORT` defaults to 55433 |
| `DATABASE_URL` | Postgres URI built from the three above (not SQLite) |
| `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` | Storage only — required, disk is ephemeral |
| `FRONTEND_ORIGIN` | storefront origin (CORS + cookies) |
| `SITE_URL` | public storefront origin (sitemap/OG); defaults to `FRONTEND_ORIGIN` |
| `RAZORPAY_KEY_ID/SECRET` | blank ⇒ COD-only |
| `RESEND_API_KEY`, `EMAIL_FROM` | blank ⇒ emails logged, not sent |
| `RATELIMIT_STORAGE_URI` | `redis://…` in production |
| `SENTRY_DSN` | blank ⇒ Sentry off |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | auto-seeds the master admin on boot |

> ⚠️ Rotate the admin password that previously shipped in `.env.example`
> (`AANGA@144amit`) — it is in git history.

## 3. Backend (Docker)

```bash
# from repo root
docker build -t aanga-api ./backend
docker run --env-file backend/.env -p 8000:8000 aanga-api
```

On Render/Railway: point the service at `backend/Dockerfile`. The platform
injects `$PORT`; gunicorn binds it automatically. Set the **health check path
to `/api/health`** (returns 200 with a DB ping, 503 if the DB is unreachable).
`WEB_CONCURRENCY` controls gunicorn workers (default 2).

## 4. Rate limiting across instances

`RATELIMIT_STORAGE_URI` defaults to `memory://` (per-process). With more than
one gunicorn worker or instance, limits are **not** enforced globally and the
app logs a warning on boot. Set `RATELIMIT_STORAGE_URI=redis://<host>:6379`.

## 5. Frontend

```bash
cd frontend
npm ci
npm run build      # -> frontend/dist
```

Deploy `frontend/dist` to a static host. Configure it to:
- rewrite unknown routes to `/index.html` (SPA client routing), and
- serve `/sitemap.xml` and `/robots.txt` from the backend (proxy those two
  paths, or submit the sitemap URL — `${SITE_URL}/sitemap.xml` — in Google
  Search Console).

Build-time: set `VITE_*` vars if/when the frontend needs them (none required
today; the API base is configured in `services/apiClient`).

## 6. CI

`.github/workflows/ci.yml` runs on every PR and on `main`:
- **backend**: pytest against a Postgres 16 service (schema rebuilt from
  `schema.sql` by `conftest`).
- **frontend**: `npm ci`, `oxlint`, `vite build`.

## 7. Backups

Supabase provides automated daily backups; enable **Point-in-Time Recovery**
(Project → Database → Backups) before launch. For an extra off-site copy,
schedule `pg_dump` via the session-pooler URI (IPv4) — see
`backend/tests/README.md` for the pooler-URI note.

## 8. Post-deploy smoke check

```bash
curl -s https://<api-host>/api/health          # {"status":"ok"}
curl -s https://<api-host>/sitemap.xml | head  # product URLs
curl -sI https://<api-host>/api/health | grep -i strict-transport-security
```
