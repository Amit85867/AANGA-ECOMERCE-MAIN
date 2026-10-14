# AANGA — hosting inventory

Prepared 2026-10-12 for a hosting decision (leaning: one Hostinger VPS in
Mumbai; the domain is registered at Hostinger). Written to be handed to an
advisor.

**Scope and method.** Nothing was deployed, no code was changed, no Razorpay /
Shiprocket / Supabase / Resend key was used. Section 4 holds real measurements
taken on this machine against the production-like local stack
(`scripts/prod_local.sh`); everything else is read off the repository at commit
`399108c`. Only environment variable **names** appear in this document.

**Measurement host** (so the numbers can be scaled): Windows 11, Docker Desktop
29.6.1, Docker VM = 12 vCPU / 7.6 GiB. In `docker stats`, 100 % CPU = one core.

---

## 1. Status

### Round 4 verdict: **unfinished — not yet GO**

Taken from `docs/PRELAUNCH_REPORT.md` (Round 4) and verified against the
artefacts on disk. The report's own verdict:

> **Not yet GO: one confirmation run is outstanding.**

The last complete browser run had 11 failures. All 11 were traced and fixed (10
were the test run exhausting its own rate-limit allowance, 1 a real defect on
the Offers screen), but the run that would confirm the fixes was stopped when
the machine ran low on memory. If the outstanding checks come back clean the
verdict becomes **GO for a cash-on-delivery launch**, subject to six owner
items in the report.

No known BLOCKER or MAJOR defect is open. 3 BLOCKERs and 13 MAJORs were found
and fixed during the round; 8 MINORs are open with recommendations.

**Online payments and courier booking are not GO.** They are built and pass
every test possible without keys, and become GO when
`scripts/verify_integrations.sh` prints six PASS lines against real test keys
(`docs/GO_LIVE.md`, stages 1–3). Until then the storefront hides "Pay online"
and the delivery check, and nothing fails.

### Outstanding checks

Confirmed still outstanding by inspecting the artefacts:

| Check | Evidence on disk | State |
|---|---|---|
| Confirming browser run (`scripts/e2e.sh`, 0 failures expected) | `.prodlocal/e2e-run.log` ends `212 passed, 4 skipped, 718 did not run` | **interrupted, must be re-run** |
| Full backend run with all 668 tests | `backend/tests/.junit.xml` absent | **not run** (651 passed on the last full run; 17 newer tests pass on their own) |
| QA matrix | `docs/QA_MATRIX.md` absent | **never generated**; `scripts/gen_qa_matrix.py` has never been executed |
| Throwaway-copy backup / restore / demo-removal check | — | **never executed** (`scripts/prod_local.sh throwaway-check`) |
| Lighthouse on home, `/shop`, a product page | — | **not run this round** (Round 3 measured ≥ 90) |
| Endpoint inventory regeneration | `docs/ENDPOINTS.md` present but pre-dates the final run | to regenerate after the backend run |

The report's "Not finished" section lists the exact commands, in order.

One check the report lists as never run **was run while preparing this
document, and passed** — see section 4: the k6 load script had never been
executed; its smoke profile now passes every threshold.

### Git state

| | |
|---|---|
| Current branch | `hardening/phase-1-payment-integrity` |
| HEAD | `399108c` ("update") |
| Working tree | **clean** (0 modified, 0 untracked) |
| Pushed? | **yes** — tracking `origin/hardening/phase-1-payment-integrity`, in sync |
| Ahead of `origin/main` | **63 commits ahead, 3 behind** |
| Merged to main? | **no** |
| Local `main` | `e75c5a0`, 3 behind `origin/main` — stale, not the deploy candidate |

So: all the launch-hardening work (the whole of Rounds 1–4) lives on a feature
branch that has never been merged. It is safely on the remote, but `main` is
not the branch to deploy. Decide before go-live whether to merge to `main` or
deploy the branch, and pin the deploy to a specific commit either way.

---

## 2. Architecture

### Processes that must run in production

| # | Process | What it is | Must it run? |
|---|---|---|---|
| 1 | **API** | `backend/Dockerfile` → gunicorn, gthread workers, Flask app `run:app` | Yes |
| 2 | **Postgres 17** | the whole data store | Yes |
| 3 | **Redis / Key Value** | rate-limit counters **and** the catalogue cache | Effectively yes — see note |
| 4 | **Storefront** | static files built by Vite, served with 4 rewrites | Yes |
| 5 | **Reconcile-payments cron** | `flask --app run reconcile-payments --hours 24`, every 30 min | Yes once online payments are on |

**No worker process, no queue, no scheduler.** There is no Celery / RQ /
APScheduler anywhere (`grep` for them returns nothing). The only background
work inside the API is the e-mail thread pool — section 9.

**On Redis.** The app runs without it (`RATELIMIT_STORAGE_URI=memory://`,
per-process cache), but then rate-limit counters are per worker process, so
with 2 workers the published limits are not actually enforced. The app logs a
warning about exactly this at startup in production. On one VPS, run Redis.

**On the cron job.** `render.yaml` schedules it `*/30 * * * *`. Its purpose:
the webhook deliberately ignores captures younger than 15 minutes
(`RAZORPAY_ORPHAN_GRACE_SECONDS=900`), so refunds for checkouts abandoned after
the money was captured depend on this job running. Without it a customer can
stay charged with no order. It is a short-lived one-shot process; `render.yaml`
gives it `DB_POOL_SIZE=1`, `DB_MAX_OVERFLOW=1`.

### How the frontend is built and served

```
npm ci && npm run build          ->  frontend/dist   (2.6 MB, 76 files)
```

`dist` is static. It is served by a file server that must apply **four
rewrites** plus the SPA fallback, because the storefront deliberately has **no
`VITE_API_BASE_URL`**: it calls `/api` on its own origin so the refresh cookie
stays first-party, which the CSRF handling relies on.

| Path | Goes to |
|---|---|
| `/api/*` | the API |
| `/sitemap.xml` | the API |
| `/robots.txt` | the API |
| `/static/*` (incl. `/static/uploads/*`) | the API |
| everything else | `/index.html` (SPA fallback, matched last) |

Cache headers the reference implementations set:
`/assets/*` → `public, max-age=31536000, immutable` (content-hashed);
`/index.html` → `no-cache` (or a deploy is never picked up);
`/static/uploads/*` → `public, max-age=31536000, immutable`.

Reference implementations to copy from: `render.yaml` (`routes:` + `headers:`)
and `scripts/prod_local/static_server.mjs` (a ~100-line Node server doing
exactly this).

### Ports

| Port | Who | Notes |
|---|---|---|
| 8000 | gunicorn (API) | `EXPOSE 8000`; honours `$PORT` if the platform injects one |
| 8080 | prod-local web tier | bound `127.0.0.1` only; `PRODLOCAL_PORT` |
| 5432 | Postgres, inside the container network | |
| 55440 | prod-local Postgres on the host | `127.0.0.1` only; `PRODLOCAL_DB_PORT` |
| 55433 | dev Postgres on the host | `backend/docker-compose.yml` |
| 55432 | pytest Postgres on the host | `backend/docker-compose.test.yml` |
| 6379 | Redis, inside the container network | not published |

### Dockerfiles

**One** application Dockerfile: `backend/Dockerfile`.

- `FROM python:3.12-slim`; `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`
- `requirements.txt` copied first for layer caching; `pip install --no-cache-dir`
- no system build toolchain needed (psycopg2-binary and Pillow ship wheels)
- built image: **210 MB**
- command:

```
gunicorn -b 0.0.0.0:${PORT:-8000} -k gthread \
  -w ${WEB_CONCURRENCY:-2} --threads ${GUNICORN_THREADS:-4} \
  --timeout 60 --graceful-timeout 30 \
  --keep-alive ${GUNICORN_KEEPALIVE:-75} --access-logfile - run:app
```

Two deliberate choices documented in the file: `gthread` because requests wait
on Postgres or an upstream API, and `--keep-alive 75` because gunicorn's
default of 2 s makes a connection-reusing proxy hand the visitor occasional
502s (this was MAJOR M11 in Round 4).

The frontend has **no** Dockerfile — it is a static build.

**It runs as root.** There is no `USER` directive. On a single VPS, behind
Caddy, add one.

### docker-compose files

| File | Purpose |
|---|---|
| `backend/docker-compose.yml` | dev Postgres, port 55433, named volume `aanga-pgdata`, runs `db/init/*` on first boot only |
| `backend/docker-compose.test.yml` | pytest Postgres, port 55432, tmpfs (wiped on restart) |
| `scripts/prod_local/docker-compose.yml` | **the production-like 4-service stack** — the closest thing in the repo to a VPS deployment |

`scripts/prod_local/docker-compose.yml` is the file to adapt for a VPS. It
already runs: `postgres:17` (named volume), `redis:7-alpine`
(`--save "" --appendonly no --maxmemory 64mb --maxmemory-policy allkeys-lru`),
the API from `backend/Dockerfile` with `FLASK_ENV=production` and a volume for
uploads, and the static web tier with the rewrites. It has healthchecks and
`depends_on: service_healthy` ordering throughout.

Its header documents the one deviation from Render: because no Supabase keys
are present it sets `ALLOW_LOCAL_UPLOADS=true` and keeps uploads on a volume —
**which is exactly what a VPS wants.** See section 11.

### render.yaml summary

A Render Blueprint, `autoDeploy: false` on every service, region `singapore`
throughout. Layout (a): a static site serves the storefront and rewrites
`/api/*` to the backend so the browser only talks to one origin.

| Resource | Type | Plan |
|---|---|---|
| `aanga-db` | Postgres 17 | `basic-256mb`, `ipAllowList: []` |
| `aanga-cache` | Key Value (Redis) | `starter`, `maxmemoryPolicy: allkeys-lru` |
| `aanga-api` | web, Docker | `starter`, health check `/api/health` |
| `aanga-reconcile-payments` | cron, Docker | `starter`, `*/30 * * * *` |
| `aanga-web` | static site | rewrites + cache/security headers, custom domain |
| `aanga-backend` | envVarGroup | shared by the API and the cron so they cannot drift |

It carries four pre-first-sync instructions in its header (substitute the real
API URL into the literal rewrite destinations, substitute the real domain, fill
every `sync: false` secret in the dashboard, then load the schema once with
`scripts/render_bootstrap_db.sh`). It also notes free web services must not be
used because they sleep, which would time out Razorpay's webhook.

**Relevance to the VPS decision:** `render.yaml` is a complete, commented
description of the target topology. A VPS replaces five managed resources with
five processes on one box. Nothing in the application needs to change — but the
five things Render was doing for you (TLS, the static tier, Redis, Postgres
backups, the cron scheduler) become yours.

---

## 3. Versions

| Component | Version | Where it is pinned |
|---|---|---|
| Python (runtime) | **3.12-slim** | `backend/Dockerfile` |
| Python (CI) | 3.12 | `.github/workflows/ci.yml` |
| Python (local venv) | 3.13.3 | this machine only — not what ships |
| Node (CI, build) | **20** | `.github/workflows/ci.yml` |
| Node (prod-local web tier) | 22-alpine | `scripts/prod_local/docker-compose.yml` |
| Node (this machine) | 22.14.0 | |
| Postgres | **17** (measured 17.10) | `render.yaml` `postgresMajorVersion: "17"`, both composes, CI |
| Redis | **7-alpine** | `scripts/prod_local/docker-compose.yml` |
| gunicorn | 23.0.0 | `backend/requirements.txt` |
| Flask / SQLAlchemy | 3.1.0 / 2.0.36 | `backend/requirements.txt` |

No `.nvmrc`, no `.python-version`, no `engines` block in
`frontend/package.json` — the Node version is pinned only in CI. Worth pinning
explicitly if the VPS builds the frontend itself.

### gunicorn workers / threads

| Variable | Default | Meaning |
|---|---|---|
| `WEB_CONCURRENCY` | 2 | worker processes |
| `GUNICORN_THREADS` | 4 | concurrent requests per worker (gthread) |
| `GUNICORN_KEEPALIVE` | 75 | seconds; must exceed the proxy's idle timeout |
| `--timeout` | 60 | fixed in the Dockerfile |
| `--graceful-timeout` | 30 | fixed in the Dockerfile |

One instance with the defaults serves **8 requests at once**.

### SQLAlchemy pool

Per gunicorn worker, each worker holding its own pool:

| Variable | Default | Meaning |
|---|---|---|
| `DB_POOL_SIZE` | 5 | connections a worker keeps open |
| `DB_MAX_OVERFLOW` | 5 | extra connections under load |
| `DB_POOL_TIMEOUT` | 10 | seconds before a request fails rather than queueing |
| `DB_POOL_RECYCLE` | 280 | seconds, below the platform's idle timeout |
| `pool_pre_ping` | `True` | fixed — survives a managed DB dropping idle connections |

The sizing rule, from `backend/config.py` and `docs/DEPLOYMENT.md` §7:

```
instances x WEB_CONCURRENCY x (DB_POOL_SIZE + DB_MAX_OVERFLOW)
  + 1 (cron) + 5 (headroom for migrations and a psql session)   <  max_connections
```

Defaults = 2 × (5 + 5) = **20 connections** for one instance. Keep
`GUNICORN_THREADS` ≤ `DB_POOL_SIZE + DB_MAX_OVERFLOW` or requests queue for a
connection and fail after 10 s.

**Measured on the local stack:** `max_connections = 100`,
`shared_buffers = 128 MB`, `work_mem = 4 MB`,
`effective_cache_size = 4 GB`, and **9 connections in use at idle** with 2
workers. A single VPS running its own Postgres has all 100 connections to
itself — the constraint that shapes `render.yaml` largely disappears.

---

## 4. Measured resources

### How these were taken

The prod-local stack was already up and healthy (11–17 h uptime) at commit
`399108c`, carrying the demo catalogue (60 products). `docker stats
--no-stream` was sampled in a loop; each figure below is reduced from those
samples. CPU is per-core (100 % = one of 12 vCPU).

**No code was changed to run the load test.** `loadtest/storefront.js` already
has an `ALLOW_LOCAL=yes` environment escape hatch alongside its
`TARGET_ENV=staging` guard, so the localhost run needed only environment
variables and there was nothing to revert. The working tree is clean and HEAD
is unchanged.

k6 was run from the official `grafana/k6` container attached to the stack's own
compose network, targeting `http://web:8080` — the same path a browser takes
(web tier → `/api` rewrite → API), minus Docker Desktop's host port-forwarding
proxy, which would otherwise have added its own CPU and latency to the numbers.
The throwaway k6 and build images were removed afterwards.

### (a) Idle — no traffic, 14 samples

| Container | CPU avg | CPU peak | Mem avg | Mem peak |
|---|---|---|---|---|
| api (gunicorn, 2w × 4t) | 6.59 % | 20.73 % | **205.6 MiB** | 206.0 MiB |
| db (postgres:17) | 0.04 % | 0.33 % | **59.2 MiB** | 59.5 MiB |
| redis (7-alpine) | 0.88 % | 1.21 % | **8.5 MiB** | 8.6 MiB |
| web (node:22-alpine) | 0.00 % | 0.00 % | **26.0 MiB** | 26.0 MiB |
| **total** | **7.5 %** (0.08 core) | | **299.3 MiB** | |

The api container's 6.6 % CPU *at idle* is not the application: it is the
compose healthcheck spawning a fresh Python interpreter every 3 seconds
(`interval: 3s` in `scripts/prod_local/docker-compose.yml`). That interval is a
local-testing setting. On a VPS use a longer interval or a `curl`-based check
and this disappears — otherwise you pay a few percent of a core forever.

### (b) Under the k6 smoke profile — 172 samples over ~8.5 min

Profile `smoke`: the browse scenario at 1 virtual user for 60 s, plus — because
local demo credentials were supplied — the cart scenario at 1 VU for 8 min.
Both scenarios ran.

| Container | CPU avg | CPU peak | Mem avg | Mem peak |
|---|---|---|---|---|
| api | 6.69 % | **23.53 %** | 205.9 MiB | **219.1 MiB** |
| db | 2.13 % | 5.56 % | 58.9 MiB | 62.2 MiB |
| redis | 1.42 % | 3.17 % | 8.6 MiB | 9.0 MiB |
| web | 0.15 % | 1.60 % | 26.1 MiB | 26.4 MiB |
| **total** | **10.4 %** (0.10 core) | **33.9 %** (0.34 core) | 299.4 MiB | **316.7 MiB** |

**Memory barely moved: +17 MiB peak over idle.** The application's footprint is
flat; this stack's floor is ~300 MiB and its smoke-load ceiling ~317 MiB.

k6 result — **every threshold passed, on the script's first ever execution**:

```
checks_succeeded ... 100.00%  236/236
http_req_failed .... 0.00%    0/310
rate_limited ....... 0.00%    0/108
http_req_duration .. avg=16.06ms med=12.34ms p(95)=28.23ms p(99)=65.71ms max=338.19ms
  {kind:catalogue} . p(95)=19.12ms   (threshold p95<800, p99<2000)
  {kind:cms} ....... p(95)=62.84ms   (threshold p95<500)
  {kind:cart} ...... p(95)=22.46ms   (threshold p95<1000)
page_data_time ..... p(95)=62.59ms   (threshold p95<2500)
http_reqs .......... 310 (0.60/s)    iterations 67
data_received ...... 363 kB          data_sent 138 kB
```

This closes the "written, never run" status in `docs/LOAD_TEST.md` for the
smoke profile. Update that doc's status line.

**What this does and does not tell you.** It proves the script, the stack and
the request path work, and it establishes the idle and near-idle footprint. It
is **1–2 virtual users at 0.6 requests/second**. It says nothing about a busy
day. The `load` profile (50 VUs, ~15–20 req/s), `stress` (to 300 VUs) and
`spike` (250 VUs in 10 s) were **not run** — `docs/LOAD_TEST.md` is explicit
that they belong on a deployed staging environment, not a laptop. The sizing
recommendation in section 12 therefore rests on a measured floor plus headroom,
not on a measured ceiling. **Run the `load` profile against the VPS once it is
up, before you take real orders.**

One CPU-bound path was **not** exercised and is worth knowing about: every
image upload runs Pillow resize plus WebP re-encode at `method=6` (slow,
highest compression) and writes two extra thumbnail variants (480 px, 800 px)
per image. That is the one operation on this server that will saturate a core.
It is admin-only and bursty (a catalogue import), not customer traffic.

### Peak during the backend Docker build

`docker build --no-cache -t <throwaway> ./backend`, with a privileged sidecar
sampling the Docker VM's `/proc/meminfo` every 0.5 s.

| | |
|---|---|
| Duration | **23 s** |
| Resulting image | **210 MB** |
| VM `MemAvailable` before | 6226 MiB |
| VM `MemAvailable` low point during | 6114 MiB |
| **Peak extra memory** | **≈ 113 MiB** (VM-wide, includes page cache from layer writes) |

So the build is cheap: ~113 MiB and under half a minute. A 1 GB VPS could build
this image — but not comfortably *while* serving, since the running stack
already holds ~300 MiB. Build off-box (CI, or a registry) or accept a brief
squeeze. 113 MiB is an upper bound on the build's own demand; the true figure
is lower, as some of that delta is page cache the kernel would have reclaimed
under pressure.

---

## 5. Data sizes

Measured on the prod-local database, which holds the **demo** catalogue
(60 products) plus the residue of Round 4's test runs — not real trading data.

| | |
|---|---|
| `pg_database_size('aanga')` | **12 MB** |
| Base tables in `public` | **40** |

Largest tables by live rows:

| Table | Rows | Total size |
|---|---|---|
| `audit_log` | 1 455 | 752 kB |
| `product_variants` | 313 | 248 kB |
| `media_assets` | 213 | 184 kB |
| `product_images` | 181 | 104 kB |
| `order_tracking` | 173 | 128 kB |
| `carts` | 157 | 80 kB |
| `users` | 156 | 224 kB |
| `addresses` | 99 | 104 kB |
| `order_items` | 95 | 56 kB |
| `orders` | 90 | 200 kB |
| `products` | 82 | 168 kB |
| `categories` | 17 | 80 kB |
| `product_reviews` | 12 | 96 kB |
| `returns` | 10 | 64 kB |

`audit_log` is already the biggest table at 60 products and 90 test orders. It
is the one table with no obvious bound — plan to check its growth and decide a
retention policy once real volume is known.

### Product images

| Location | Size | Files |
|---|---|---|
| prod-local uploads volume (`/app/static/uploads`) | **15 MB** | **626**, all `.webp` |
| `backend/static/uploads` (dev working copy, git-ignored) | 43 MB | 929 |
| `frontend/dist` (built storefront) | 2.6 MB | 76 (assets 1.2 MB) |

~24 kB average per file, consistent with the pipeline's intent: originals are
resized to a 1400 px longest edge and re-encoded as WebP at quality 80, and two
smaller variants (480 px, 800 px) are stored next to each original as
`<name>_<width>.webp`. `backend/app/services/storage.py` records that the raw
product shots were ~930 kB each before this.

The `_<width>` suffix and the widths `(480, 800)` are a **contract across three
files** — `storage.py`, `frontend/src/utils/image`, and an inline script in
`frontend/index.html`. Don't let a future change touch one of the three alone.

### Where images are stored

Chosen at runtime by configuration, in `backend/app/services/storage.py`:

- `SUPABASE_URL` **and** `SUPABASE_SERVICE_KEY` set → **Supabase Storage**, a
  public bucket named by `SUPABASE_STORAGE_BUCKET` (default `product-images`),
  via the Storage REST API (no SDK dependency).
- otherwise → **local disk**, served at `/static/uploads/<filename>`, written
  under the API's `static/uploads` (`os.makedirs(..., exist_ok=True)`).

In production the app **refuses to start** with neither set — unless
`ALLOW_LOCAL_UPLOADS=true`, which is the explicit declaration that
`static/uploads` is a persistent volume. The code comment names the two valid
uses: `scripts/prod_local.sh`, "or a self-hosted server with a mounted disk".
See section 11 — this is the single most consequential setting for the VPS
plan.

Uploads are the **only** thing the application writes to local disk. Logs go to
stdout; there is no `FileHandler` anywhere.

---

## 6. External services

| Service | Used for | Free tier? | If unavailable |
|---|---|---|---|
| **Supabase Storage** | product images in production (object store only — the database was migrated off Supabase to self-hosted Postgres) | yes, generous for this volume (15 MB measured) | **Avoidable entirely on a VPS** via `ALLOW_LOCAL_UPLOADS=true` + a mounted disk. If kept and it is down: existing images 404 (they are served from Supabase URLs), new uploads fail. The app refuses to *start* in production if the keys are absent and `ALLOW_LOCAL_UPLOADS` is not set. |
| **Razorpay** | online payments (UPI / cards / netbanking / wallet); REST API + HMAC signature, no SDK | no — per-transaction fees | Leave the keys blank and the store is **COD-only** by design: "Pay online" is hidden and nothing errors. If configured and down: online checkout fails; COD keeps working. Note the webhook must reach the server for abandoned-capture refunds. |
| **Shiprocket** | courier booking, AWB, pickup requests, delivery/ETA checks | no — per-shipment | Leave blank and the store runs **without booking or delivery checks**; the storefront hides the delivery widget. If configured and down: booking and the PIN-code check fail (handled — a courier timeout was fixed in Round 4, M5); orders still complete. |
| **Resend** | transactional e-mail: order confirmation and password reset (only two e-mails exist today) | yes, limited | Blank `RESEND_API_KEY` → e-mails are **logged, not sent**, and the store works. If down: a customer gets no order confirmation and **password reset becomes unusable** — the most user-visible outage of the lot. |
| **Sentry** | error tracking, backend and frontend | yes | Blank DSN → disabled. If down: no error reporting; the app is unaffected. |
| **Google OAuth** | "Continue with Google" sign-in | yes | Blank `GOOGLE_CLIENT_ID` → the endpoint answers 503 and the button is hidden. If down: that one sign-in route fails; e-mail/password still works. |
| **Google Fonts** | Inter + Poppins, loaded from `fonts.googleapis.com` / `fonts.gstatic.com` at runtime, injected by a script with a `<noscript>` fallback | yes | Text falls back to the stack's next font — cosmetic. But it is a **third-party request on every first page load from India**; self-hosting the two families would remove a cross-border round trip and a privacy footnote. Worth doing. |
| **WhatsApp (`wa.me`)** | an outbound contact link | n/a | A link; nothing to break. |

No SMS provider is integrated — `SMS_PROVIDER` is deliberately blank and the
phone-OTP sign-in option stays hidden on the storefront while it is.

**Net for the VPS plan:** of eight external dependencies, the only one that is
*architecturally* required is the one you can drop (Supabase Storage). Razorpay
and Shiprocket are optional-by-design for a COD launch. Resend is the one to
keep, because password reset depends on it.

---

## 7. Environment variables

Names only. "Secret" = must never be committed, logged, or pasted into a
ticket.

### Required in production — the app refuses to start without these

`backend/app/__init__.py::_validate_config` enforces this at boot, which is why
a misconfigured deploy fails loudly instead of at the first query.

| Name | Secret | Notes |
|---|---|---|
| `FLASK_ENV` | no | must be `production` |
| `SECRET_KEY` | **yes** | ≥ 32 random chars; rejected if it is the dev default |
| `JWT_SECRET_KEY` | **yes** | ≥ 32 random chars, distinct from the above |
| `DATABASE_URL` | **yes** (contains the password) | must not be SQLite, must not be the dev fallback |
| `FRONTEND_ORIGIN` | no | CORS + cookie origin |
| `SUPABASE_URL` | no | required *unless* `ALLOW_LOCAL_UPLOADS=true` |
| `SUPABASE_SERVICE_KEY` | **yes** | required *unless* `ALLOW_LOCAL_UPLOADS=true` |

### Strongly recommended in production

| Name | Secret | Notes |
|---|---|---|
| `RATELIMIT_STORAGE_URI` | **yes** if it embeds a password | `memory://` logs a warning and silently under-enforces limits across workers |
| `SITE_URL` | no | absolute URLs in `sitemap.xml` / `robots.txt` / OG tags; defaults to `FRONTEND_ORIGIN` |
| `TRUSTED_PROXY_COUNT` | no | see section 8 — wrong value breaks rate limiting |
| `JWT_COOKIE_SAMESITE` | no | `Lax` for a same-origin `/api` rewrite; `None` only for a cross-site API |
| `ALLOW_LOCAL_UPLOADS` | no | `true` only where `static/uploads` is a persistent disk |
| `WEB_CONCURRENCY`, `GUNICORN_THREADS`, `GUNICORN_KEEPALIVE` | no | sizing |
| `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, `DB_POOL_RECYCLE` | no | sizing |
| `CACHE_ENABLED`, `CACHE_REDIS_URL` | `CACHE_REDIS_URL` if it embeds a password | catalogue cache; falls back to `RATELIMIT_STORAGE_URI` when that is Redis |

### Optional — blank disables the feature cleanly

| Name | Secret | Group |
|---|---|---|
| `RAZORPAY_KEY_ID` | no | **all-or-nothing**: once the key is set, the secret and webhook secret are required or the app refuses to start |
| `RAZORPAY_KEY_SECRET` | **yes** | " |
| `RAZORPAY_WEBHOOK_SECRET` | **yes** | " |
| `RAZORPAY_ORPHAN_GRACE_SECONDS` | no | default 900 |
| `SHIPROCKET_EMAIL` | no | **all-or-nothing** with the password and pickup PIN |
| `SHIPROCKET_PASSWORD` | **yes** | " |
| `SHIPROCKET_PICKUP_LOCATION` | no | default `Primary` |
| `SHIPROCKET_PICKUP_PINCODE` | no | " |
| `RESEND_API_KEY` | **yes** | blank → e-mails logged, not sent |
| `EMAIL_FROM` | no | must be a verified Resend sending domain |
| `EMAIL_ENABLED` | no | manual kill switch |
| `EMAIL_ASYNC` | no | default `true`; see section 9 |
| `GOOGLE_CLIENT_ID` | no | public by nature |
| `SENTRY_DSN` | **yes**-ish | treat as a secret |
| `SENTRY_ENVIRONMENT`, `SENTRY_TRACES_SAMPLE_RATE`, `APP_RELEASE` | no | |
| `ADMIN_EMAIL` | no | first master admin, created on first boot |
| `ADMIN_PASSWORD` | **yes** | change it after first boot: `flask --app run set-admin-password` |
| `SMS_PROVIDER` | no | leave blank — no provider integrated |

### Local / tooling only — never in production

`POSTGRES_USER`, `POSTGRES_PASSWORD` (**secret**), `POSTGRES_DB`,
`POSTGRES_PORT`, `POOLER_DATABASE_URL` (**secret**, Supabase migration source),
`DEMO_OWNER_EMAIL`, `DEMO_OWNER_PASSWORD` (**secret**),
`PRODLOCAL_PORT`, `PRODLOCAL_DB_PORT`, `TEST_DATABASE_URL`.

### Frontend (build-time, baked into the bundle — never secret)

`VITE_GOOGLE_CLIENT_ID`, `VITE_SENTRY_DSN`, `VITE_SENTRY_ENVIRONMENT`,
`VITE_APP_RELEASE`, and `VITE_API_BASE_URL` — which should stay **unset** so
the storefront calls `/api` on its own origin.

Anything named `VITE_*` is compiled into public JavaScript. Round 4's secret
scan confirmed the built storefront contains no secret; keep it that way.

### One known secret-handling item

`docs/PRELAUNCH_REPORT.md` MINOR 3 / `docs/SECURITY_TODO.md`: an early
`backend/.env.example` in the git history (commit `4651da7`) contains a real
admin password. Change the admin password before launch and the old value is
worthless. Scrubbing history is optional (Decision 4 in the report) and
rewrites every commit.

---

## 8. Domain needs

### Hostnames

With the single-origin layout the storefront and the API share one hostname, so
**one** is strictly required:

| Hostname | Serves | Required |
|---|---|---|
| `www.<domain>` (or the apex) | storefront **and** `/api/*`, `/sitemap.xml`, `/robots.txt`, `/static/*` | **yes** |
| the other of apex / `www` | 301 redirect to the canonical one | strongly recommended |
| `staging.<domain>` | a second environment to run the `load` profile and rehearse deploys | recommended |

A separate `api.<domain>` is **not** wanted. Splitting the API onto its own
hostname makes the refresh cookie cross-site, which forces
`JWT_COOKIE_SAMESITE=None` and gives up the simplicity the current design buys.
Keep one origin.

### Settings that depend on the domain

| Setting | Value on a single VPS behind Caddy |
|---|---|
| `FRONTEND_ORIGIN` | `https://www.<domain>` — CORS origin and cookie scope |
| `SITE_URL` | `https://www.<domain>` — absolute URLs in `sitemap.xml`, `robots.txt`, OG tags. Defaults to `FRONTEND_ORIGIN`; set it explicitly. |
| `JWT_COOKIE_SAMESITE` | **`Lax`** — correct, because `/api` is same-origin through the rewrite |
| `JWT_COOKIE_SECURE` | `True` in production config — requires HTTPS, which Caddy provides |
| `JWT_REFRESH_COOKIE_PATH` | `/api/auth` (fixed in config) — scoping the refresh cookie to the routes that need it |
| `render.yaml` rewrite destinations | **not applicable** on a VPS; Caddy does the rewriting |
| `domains:` in `render.yaml` | `www.example.com` — a placeholder that must be replaced if Render is ever used |

CORS is configured from a **single** origin (`origins=[FRONTEND_ORIGIN]`) with
`supports_credentials=True` and `expose_headers=["X-CSRF-TOKEN"]`. There is no
wildcard and no list — one origin, deliberately.

### Proxy hop (ProxyFix)

`backend/app/__init__.py::_apply_proxy_fix`, skipped entirely in dev/test:

```python
hops = max(int(app.config.get("TRUSTED_PROXY_COUNT", 1)), 0)
if hops:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=1, x_host=1)
```

This matters more than its size suggests. Rate limiting keys on the client IP
(`get_remote_address`); if the hop count is wrong the app either keys every
request on the proxy's IP — one shared bucket for all visitors — or trusts a
client-supplied `X-Forwarded-For` and lets an attacker forge their way past the
limiter.

- **On Render:** `render.yaml` sets `"1"` and says so honestly — "a starting
  value, not a known one", because Render does not document how many hops its
  static-site rewrite plus the API load balancer add.
- **On one VPS behind Caddy:** **`TRUSTED_PROXY_COUNT=1`** is not a guess.
  Caddy is the only proxy, and it appends exactly one `X-Forwarded-For` entry.
  This is a genuine simplification of the Render setup.

Either way, verify it: the admin **System Health** page reports "Proxies in
front of the server: N seen" and "Your IP as seen by the server". Check both
through the real domain after the first deploy. This is post-deploy step 6 in
`docs/DEPLOYMENT.md`.

### Single VPS behind Caddy vs Render — what changes

| | Render | One VPS + Caddy |
|---|---|---|
| TLS | automatic | **Caddy, automatic** (ACME); point DNS at the VPS first |
| Static tier | `aanga-web` static site | Caddy `file_server` over `frontend/dist` |
| `/api/*` rewrite | `routes:` in `render.yaml` | Caddy `reverse_proxy` to `127.0.0.1:8000` |
| Cache headers | `headers:` in `render.yaml` | Caddy `header` directives — must be reproduced |
| Postgres | managed, `basic-256mb` | your container; **backups become yours** |
| Redis | managed Key Value | your container; cap `maxmemory`, `allkeys-lru` |
| Cron | `aanga-reconcile-payments` service | host `cron` → `docker compose exec`/`run`, or a sidecar |
| `TRUSTED_PROXY_COUNT` | `1`, unverified | **`1`, known** |
| Uploads | Supabase Storage (disk is ephemeral) | **local volume + `ALLOW_LOCAL_UPLOADS=true`** |
| `max_connections` | shared with the plan's limit | all 100 are yours |
| Scaling | add instances | one box; vertical only |

A Caddyfile for this needs five route rules (the four API paths plus the SPA
fallback) and three header blocks. `scripts/prod_local/static_server.mjs` and
the `routes:`/`headers:` blocks of `render.yaml` are both faithful specs to
translate from — the rewrite set and cache policy are already settled, not open
questions.

---

## 9. Background work and e-mail

### How background work runs

There is **no queue and no scheduler** in the application. Two mechanisms only:

1. **An in-process thread pool for e-mail.**
   `backend/app/services/email.py` holds a module-level
   `ThreadPoolExecutor(max_workers=2, thread_name_prefix="email")`, registered
   with `atexit.register(_executor.shutdown, wait=True)`. Used when
   `EMAIL_ASYNC` is true (the default) so a slow mail provider never delays
   checkout. Two threads is deliberate: sending is one short HTTPS call and a
   burst simply queues.

2. **A CLI command run by an external scheduler.**
   `flask --app run reconcile-payments --hours 24`, scheduled every 30 minutes
   by `render.yaml`. On a VPS this becomes a host `cron` entry. Eight CLI
   commands exist in total: `apply-migrations`, `check-integrations`,
   `verify-integrations`, `check-schema`, `remove-demo-content`,
   `reconcile-payments`, `seed-admin`, `set-admin-password`.

### Does it survive a restart?

**No, and this is the honest answer to give the advisor.**

- A queued e-mail lives only in the worker process's memory. On a **graceful**
  shutdown (SIGTERM, gunicorn's `--graceful-timeout 30`, then `atexit`) the
  pool is joined and queued mail is delivered. On a **hard** kill (SIGKILL,
  OOM-killer, power loss, `docker kill`) anything queued is **lost silently**.
  There is no persistence, no retry, no dead-letter record.
- The practical consequence is bounded: only two e-mails exist today (order
  confirmation and password reset), and losing an order confirmation does not
  lose the order — the order is committed to Postgres first. A lost password
  reset is recoverable by asking again.
- **Payments are not exposed to this.** The reconcile sweep is the durable
  safety net: it is stateless, idempotent (Razorpay dedupes refunds on an
  `Idempotency-Key` header), and re-scans a 24-hour window on every run, so a
  missed run is caught by the next one. Webhook events are recorded in a
  `webhook_events` table, so repeated delivery is handled in the database
  rather than in memory.

If the e-mail set grows (the report's Decision 1 proposes shipped / delivered /
cancelled / refunded notifications), revisit this: at four more e-mails on the
order lifecycle, an in-memory pool with no retry starts to be the wrong shape,
and a persisted outbox table would be the natural next step. For a COD launch
with two e-mails, it is proportionate.

---

## 10. Backups

### What exists

| Script | Does | Platform |
|---|---|---|
| `backend/db/backup.ps1` | `pg_dump` **inside the container**, custom format, to `db/backups/aanga-<timestamp>.dump`; `-Keep N` prunes to the N most recent (default 14) | **PowerShell** |
| `backend/db/restore.ps1` | **destructive** — drops the `public` schema, re-applies the Supabase compatibility shims, restores a named dump (or the most recent) | **PowerShell** |
| `backend/db/migrate-from-supabase.ps1` | one-time migration off Supabase; dumps Supabase's `public` schema, restores locally, prints a per-table row-count comparison; re-applies outstanding migrations; **only ever reads** Supabase | **PowerShell** |
| `scripts/prod_local.sh throwaway-check` | backs up, restores into a second database, removes demo content there, checks it, deletes the copy — main data untouched | bash — **never executed** |

`backup.ps1`'s own documentation is blunt about the change of responsibility:
Supabase used to take backups for you; self-hosting makes it your job, so
schedule it (Task Scheduler, or cron on a VPS) and — "the part people skip" —
actually run `restore.ps1` against a scratch database once, so you know the
backups are readable before you need them.

Both run `pg_dump` / `pg_restore` *inside* the `postgres:17` container, so no
local client is needed and the client version always matches the server. That
design carries over to a VPS unchanged.

`backend/db/backups/` is git-ignored except for a `.gitkeep` — dumps may
contain customer data and must never be committed.

### What is backed up, and where to

Today: **the database only**, to `backend/db/backups/` on the same machine.

Three gaps for a single-VPS deployment:

1. **Both scripts are PowerShell.** On a Linux VPS they do not run. The logic
   is a dozen lines of `docker compose exec pg_dump`, so a shell port is small
   — but it does not exist yet, and `restore.ps1` additionally targets the
   local dev compose database (MINOR 7 in the report).
2. **Uploads are not backed up at all.** On Render that was fine, because
   images lived in Supabase. The moment you set `ALLOW_LOCAL_UPLOADS=true`, the
   uploads volume becomes irreplaceable primary data (15 MB / 626 files
   measured) and needs backing up alongside the database.
3. **Same-machine backups are not backups.** They survive a bad deploy or a
   dropped table; they do not survive losing the VPS. Ship the dumps off-box —
   object storage, or Hostinger's own snapshots as a second layer.

The report's MINOR 7 says to check the hosting plan's backup retention before
launch. On Render that meant the Postgres plan. On a VPS it means: your cron
job, your off-box copy, and one rehearsed restore. Nobody else is doing it.

---

## 11. Risks for single-server hosting, from the code

Read in the order that matters.

### 1. Uploads on local disk — the setting that makes or breaks the plan

The app refuses to start in production without Supabase keys **unless**
`ALLOW_LOCAL_UPLOADS=true`. The code comment is explicit that this flag is for
"a self-hosted server with a mounted disk", and `scripts/prod_local.sh` already
runs this way. **This is a supported configuration, not a workaround** — the
best news in this inventory for the VPS plan.

The obligations that come with it:
- `static/uploads` must be a **persistent** volume, never a container layer.
- It becomes primary data and must be in your backups (section 10, gap 2).
- The API serves `/static/uploads/*` itself, so image traffic now goes through
  gunicorn. Let Caddy serve that directory directly from the volume instead,
  with `public, max-age=31536000, immutable` — it keeps image bytes out of your
  8 concurrent request slots.

### 2. Rate limiting is only global if Redis is

`Limiter(key_func=get_remote_address)` with `RATELIMIT_STORAGE_URI`. With
`memory://` the counters are **per worker process**, so 2 workers means roughly
double the advertised allowance and no coordination. The app logs a warning
about this at startup in production. Mitigation on one box is easy — run Redis
— but the failure is silent if you skip it, and Round 4's BLOCKER B3 and ten of
its eleven e2e failures were rate-limiter behaviour, so this is a live area.

Related: `TRUSTED_PROXY_COUNT` must be exactly 1 behind Caddy (section 8).
Wrong in one direction, every visitor shares one bucket; wrong in the other, a
forged `X-Forwarded-For` walks past the limiter.

### 3. "The API is stateless and scales by adding instances" is now out of date

`docs/DEPLOYMENT.md` §7 opens: *"The API is stateless — no local files (uploads
go to Supabase Storage) … so it scales by adding instances."* Setting
`ALLOW_LOCAL_UPLOADS=true` makes that sentence false: the API becomes
disk-stateful and horizontal scaling stops being free. For one VPS that is an
acceptable trade — but it is a real architectural change, it is the direction
you are choosing, and the document should say so.

### 4. Everything shares one failure domain, and one CPU

On Render, Postgres, Redis, the API, the cron and the static tier fail
independently. On one box they do not: an OOM event takes the database down
with the API, and the image-upload path (Pillow + WebP `method=6` + two
thumbnail variants per image) competes for the same cores that are serving
customers. The measured smoke load is trivial (0.34 core peak) but that path
was not measured under concurrency. Expect admin bulk-uploads to be felt by
shoppers on a 1–2 vCPU box; do catalogue imports off-peak.

### 5. No migration tool — schema changes are hand-applied SQL

Flask-Migrate and Alembic are installed and initialised, but there is **no
`migrations/` directory and no `alembic.ini`**. The schema's source of truth is
`backend/schema.sql` (a `pg_dump`), applied once by
`scripts/render_bootstrap_db.sh`, with changes shipped as hand-numbered
`migrations_*.sql` files and a `flask apply-migrations` command.
`docs/DATABASE.md` documents a case where exactly this drifted —
`migrations_orders_idempotency.sql` had never been applied to the live Supabase
database, so a straight restore would have silently dropped the
payment-integrity guards. This is not a VPS-specific risk, but on a VPS you are
the only safety net. A `schema_migrations` ledger table, or adopting Alembic
properly, would pay for itself.

### 6. Backup scripts are PowerShell-only

Section 10, gap 1. They will not run on a Linux VPS as written.

### 7. The container runs as root

`backend/Dockerfile` has no `USER` directive. Behind Caddy on a shared box, add
one — a one-line change.

### 8. The deploy candidate is an unmerged branch

Section 1. 63 commits ahead of `origin/main`, never merged; local `main` is
stale. Decide the merge story and pin the deploy to a commit.

### Things that are *not* a problem

Worth stating plainly, because they are the usual single-server traps:

- **No in-process session state.** Auth is JWT; sessions live in a
  `user_sessions` table. Restarts do not sign anyone out.
- **No local log files.** Logs go to stdout — `docker logs` / journald work
  as-is.
- **Nothing assumes more than one instance.** No leader election, no
  instance-count arithmetic, no sticky sessions. The multi-instance reasoning
  in the docs is about connection *ceilings*, which only get roomier on one box
  with all 100 connections to itself.
- **The cache degrades gracefully.** No Redis → a small per-process cache; the
  only loss is hit rate.
- **Uploads are the only disk write.** One directory to persist and back up.

---

## 12. Recommendation

Ten lines, from the measurements above rather than from habit.

1. **Measured floor:** the whole four-process stack idles at **299 MiB** and
   peaked at **317 MiB** under the k6 smoke profile — api 206, db 59, web 26,
   redis 9 MiB. CPU peaked at **0.34 of one core**.
2. **Measured build cost:** `docker build --no-cache` took **23 s** and about
   **113 MiB** peak, producing a **210 MB** image — cheap enough to build
   on-box if you accept a brief squeeze, though CI is tidier.
3. **Measured data:** database **12 MB** / 40 tables, uploads **15 MB** / 626
   WebP files, built storefront **2.6 MB** — all tiny; disk is about Docker
   images, backups and growth, not today's data.
4. **RAM: 4 GB.** Not because 317 MiB needs it, but because the honest ceiling
   is unmeasured — only 1–2 virtual users were ever applied — and because
   Postgres deserves more than a container-default 128 MB `shared_buffers`, the
   build and `pg_dump` want headroom, and the OOM-killer on one box takes the
   database down with the API. 2 GB would run a COD launch; 4 GB is the first
   size where nothing on the list competes, and the price delta is small.
5. **CPU: 2 vCPU.** Customer traffic measured at a third of a core, so this is
   not about serving pages: it is the image pipeline (Pillow resize + WebP
   `method=6` + two thumbnail variants per upload), the one CPU-bound path,
   which was *not* measured under concurrency. On 1 vCPU an admin bulk-upload
   would be felt by shoppers.
6. **Disk: 50 GB NVMe.** Docker images alone are ~870 MB before layers
   (`postgres:17` 454, api 210, `node:22-alpine` 167, `redis:7-alpine` 39); add
   the database, the uploads volume as it grows, 14 retained dumps, and logs.
   50 GB is comfortable for years at this catalogue size; 25 GB would work and
   leave less room for carelessness.
7. **Region Mumbai is the right call** — customers, Razorpay and Shiprocket are
   all in India, and it beats `render.yaml`'s Singapore region for latency.
8. **Before taking real orders, run the `load` profile** (50 VUs, ~15–20 req/s)
   against the VPS and watch `docker stats`. That is the one number this
   inventory cannot give you, and it is the number that validates lines 4–6.
9. **Three things the VPS adds to your job:** Postgres backups shipped off-box
   *including the uploads volume*, the reconcile cron as a host `cron` entry,
   and a shell port of the two PowerShell backup scripts.
10. **Set these four correctly and the rest follows:**
    `ALLOW_LOCAL_UPLOADS=true` (with a real volume),
    `TRUSTED_PROXY_COUNT=1` (verify on System Health),
    `RATELIMIT_STORAGE_URI` pointing at Redis, and
    `JWT_COOKIE_SAMESITE=Lax` with one hostname for both storefront and API.
