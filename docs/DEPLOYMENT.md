# AANGA — deployment runbook (Render)

Nothing in this repository deploys by itself. This is the procedure; every
step that touches Render, Neon, Razorpay or DNS is done by a person.

## 1. Layout

```
                      www.yourdomain.com  (custom domain)
                               │
                    ┌──────────▼───────────┐
   browser ───────► │  aanga-web           │  Render Static Site (frontend/dist)
                    │   /api/*  ─ rewrite ─┼──┐
                    │   /sitemap.xml, /robots.txt ─┤
                    │   /*      → index.html│  │
                    └──────────────────────┘  │
                                              ▼
   Razorpay webhook ───────────────►  aanga-api      Render Web Service
                                        │     │                (native Python)
                     Neon (production) ◄┘     └─► Upstash Redis  (optional)
                     Postgres 17, Singapore        rate limits, catalogue cache
                                        ▲
                        aanga-reconcile-payments   Render Cron Job, every 30 min

   Product images: Neon Object Storage (public_read bucket), not Render.
```

The storefront and the API share one origin from the browser's point of view.
That is deliberate: the app reads a CSRF cookie set by the API, which a browser
only allows on the same site. `render.yaml` at the repository root describes
all five pieces.

**The Razorpay webhook does not use the rewrite.** It points straight at the
backend (`https://<backend-host>/api/payments/webhook`): one fewer hop to fail,
and the request body reaches the signature check byte-for-byte.

### Switching to a single service later (layout c)

If the rewrite proves slow (section 10), the alternative is Flask serving the
built frontend from the API service. The app is already shaped for it — the
frontend calls a relative `/api`, so nothing in it changes. What the switch
needs:

1. A build command on the API service that also runs `npm ci && npm run build`
   and leaves `frontend/dist` where Flask can serve it.
2. A catch-all route in Flask returning `index.html` for any path that is not
   `/api/*`, `/static/*`, `/sitemap.xml` or `/robots.txt`.
3. A separate Content-Security-Policy for that HTML response. Today every
   response carries `default-src 'none'`, which is right for JSON and would
   block the page's own scripts.
4. In `render.yaml`: delete the `aanga-web` static site and move the custom
   domain to `aanga-api`.

Cookies, CORS, the webhook URL and the database are unaffected.

## 2. Before the first deploy

1. **Neon** — the database. Project `AANGA`, Postgres 17, Singapore, three
   branches (`production`, `dev`, `test`). See [DATABASE.md](DATABASE.md).
   Nothing to create at deploy time if it already exists.
2. **Neon Object Storage** — product images. A `public_read` bucket named
   `product-images` on the **production** branch:

   ```bash
   neonctl buckets create product-images --project-id dry-base-24522506      --org-id org-long-mud-04364433 --branch production --access-level public_read
   ```

   Then issue a credential for it (production only — never written to a file):

   ```bash
   neonctl credentials create --project-id dry-base-24522506      --org-id org-long-mud-04364433 --branch production      --name aanga-production-storage --scope storage:read --scope storage:write
   neonctl credentials reveal <tokenId> --project-id dry-base-24522506      --org-id org-long-mud-04364433 --branch production
   ```

   Supabase is no longer used for anything.
3. **Upstash Redis** — optional but strongly recommended: free tier, one
   database in `ap-south-1`/`ap-southeast-1`, paste its URL into
   `RATELIMIT_STORAGE_URI`. Without it rate-limit counters live in each
   gunicorn worker, so with `WEB_CONCURRENCY=2` a caller gets about twice the
   advertised allowance and nothing is shared between instances. There is no
   Redis container any more.
4. **Razorpay** — optional. Without keys the store runs cash-on-delivery only.
5. **Shiprocket** — optional. Without it there is no courier booking or
   delivery check.
6. **Resend** — a verified sending domain for `EMAIL_FROM`. Without it emails
   are logged, not sent.
7. **Rotate the admin password** that leaked in git history — see
   [SECURITY_TODO.md](SECURITY_TODO.md). Do not reuse it as `ADMIN_PASSWORD`.
8. **Test data** — the dev branch contains accounts created for browser
   testing (emails ending `@local.test`). A fresh branch loaded by the bootstrap holds none, but if you ever restore a local dump anywhere, run
   `backend/db/qa_cleanup.sql` against that branch first. The bootstrap
   script's verification fails if it finds any such account.

## 3. Create the services

1. Edit `render.yaml`: replace `www.example.com` with the storefront domain
   (three places) and check the region.
2. Render Dashboard → **New → Blueprint** → select this repository.
3. Fill in the values marked `sync: false`. They are secrets and are not in
   the file. Required to start: the four `S3_*` settings,
   `ADMIN_EMAIL`, `ADMIN_PASSWORD`. The rest may stay blank.
4. Once `aanga-api` exists, note its URL. If it is not
   `https://aanga-api.onrender.com`, update the three rewrite destinations in
   `render.yaml` and sync again.
5. **Do not deploy the API yet** — the database is empty.

### Environment variables

Documented in full in `backend/.env.example`. The app **refuses to start in
production** unless these are real:

| Variable | Notes |
|---|---|
| `FLASK_ENV=production` | selects the production config |
| `SECRET_KEY`, `JWT_SECRET_KEY` | generated by the Blueprint; ≥32 characters, distinct |
| `PYTHON_VERSION` | `3.12.7`, matching `backend/.python-version` |
| `DATABASE_URL` | Neon **production**, **pooled** (`-pooler` in the host) |
| `DIRECT_DATABASE_URL` | Neon **production**, **direct**. Migrations and dumps |
| `S3_ENDPOINT_URL` | the **production** branch's object-storage endpoint (it embeds the branch id) |
| `S3_BUCKET` | `product-images` |
| `S3_ACCESS_KEY_ID` | the credential's **token id** (`nak_live_…`) |
| `S3_SECRET_ACCESS_KEY` | from `neonctl credentials reveal` |
| `S3_REGION` | `ap-southeast-1` |
| `S3_PUBLIC_BASE_URL` | `<endpoint>/product-images` (or a CDN in front of it) |

Optional integrations are all-or-nothing — setting one half makes the app
refuse to start:

| If you set | You must also set |
|---|---|
| `RAZORPAY_KEY_ID` | `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` |
| `SHIPROCKET_EMAIL` | `SHIPROCKET_PASSWORD`, `SHIPROCKET_PICKUP_PINCODE` (6 digits) |

## 4. Load the database

Once, against the Neon **production** branch, using its **direct** connection
string. Fetch it into the environment for that one command so it never reaches
a file or your shell history:

```bash
DATABASE_URL="$(neonctl connection-string production   --project-id dry-base-24522506 --org-id org-long-mud-04364433   --role-name aanga_owner --database-name aanga)"   scripts/render_bootstrap_db.sh

scripts/render_bootstrap_db.sh --check    # verify, changes nothing
```

The script needs `psql` **or** just Python with `psycopg2` — it falls back to
`scripts/db_exec.py`, so there is nothing to install and no container.

> **Use the direct string, never the pooled one.** `schema.sql` is a `pg_dump`
> and contains `SELECT pg_catalog.set_config('search_path', '', false)`. Run
> through PgBouncer that setting outlives the client: the pooler keeps the
> server connection and hands it to the next caller with an empty
> `search_path`, after which every unqualified table name fails with
> "relation … does not exist" for a table that is plainly there.

Connect as `aanga_owner`, the user the app uses. The tables carry
row-level-security policies; the owner bypasses them, and loading as another
user would leave the app reading empty tables. The script checks ownership.

What it applies, in order:

| # | File | Adds |
|---|---|---|
| 1 | `backend/tests/sql/00_prereqs.sql` | `uuid-ossp`, a stub `auth.uid()` the policies reference |
| 2 | `backend/schema.sql` | every table, enum, trigger, index and policy |
| 3 | `backend/migrations_orders_idempotency.sql` | unique indexes on `payment_ref` and `idempotency_key` |
| 4 | `backend/migrations_hero_badges.sql` | hero banner badge columns |
| 5 | `backend/migrations_address_archive.sql` | `addresses.archived_at` |
| 6 | `backend/migrations_ops_tables.sql` | `webhook_events`, `job_runs` |
| 7 | `backend/migrations_admin_ops.sql` | `audit_log`, dashboard indexes |
| 8 | `backend/migrations_owner_dashboard.sql` | collections, campaigns, homepage sections, menus, pages, FAQ, media library, product SEO fields, demo flag |

Steps 3–8 are already contained in `schema.sql`; they run again because they
are idempotent and because the same list is the upgrade path.

`migrations_orders_idempotency.sql` (step 3) used to be listed as "still to
apply to the live Supabase database". That no longer applies: Supabase is gone
entirely -- the database and the image bucket are both Neon. The
script above is the only place the migration needs to run, and it checks for
both indexes when it finishes.

To upgrade a database that already has data (either command; the second needs
only the app's own environment, so it also works from a Render shell):

```bash
scripts/render_bootstrap_db.sh --migrate   # bring an existing database up to date
flask --app run apply-migrations           # the same, from backend/ with DATABASE_URL set
```

The script refuses to load into a database that already has tables, and never
drops anything that holds data. A future migration is added to the
`MIGRATIONS` list in the script, in order, and to `schema.sql`.

## 5. Deploy

1. Deploy `aanga-api`. On first boot it creates the master admin from
   `ADMIN_EMAIL` / `ADMIN_PASSWORD`. Health check path: `/api/health`.
2. Deploy `aanga-web`.
3. Point the custom domain at `aanga-web` (Render shows the DNS records) and
   wait for the certificate.
4. Seed the catalogue, if you want the starter products. It goes through the
   live admin API so images take the real storage path:

   ```bash
   ADMIN_EMAIL=... ADMIN_PASSWORD=... \
     python backend/db/seed_catalogue.py --api https://<backend-host>
   ```

5. Change the admin password from the bootstrap value: Render Shell on
   `aanga-api` → `flask --app run set-admin-password`.

## 6. Razorpay webhook

Razorpay Dashboard → Settings → Webhooks → Add:

- **URL:** `https://<backend-host>/api/payments/webhook` — the backend's own
  `onrender.com` URL (or an `api.` subdomain pointed at it), **not** the
  storefront domain.
- **Secret:** the same value as `RAZORPAY_WEBHOOK_SECRET`.
- **Events:** `payment.captured`, `payment.failed`, `refund.processed`.

Use test-mode keys (`rzp_test_…`) and a test-mode webhook until a full test
purchase and refund have gone through; the System Health page shows which mode
the configured key is in.

## 7. Sizing: workers, threads and database connections

The API is stateless — no local files (uploads go to object storage), no
in-process sessions (auth is JWT; rate limits and the catalogue cache live in
Redis) — so it scales by adding instances. The one shared limit is Postgres
connections.

**The rule.** Every gunicorn worker keeps its own pool, so the most connections
the API can open is:

```
instances x WEB_CONCURRENCY x (DB_POOL_SIZE + DB_MAX_OVERFLOW)
```

and that, plus the cron job (1) and headroom for migrations and a psql session
(5), must stay under the database's `max_connections`.

| Setting | Default | Meaning |
|---|---|---|
| `WEB_CONCURRENCY` | 2 | gunicorn worker processes per instance |
| `GUNICORN_THREADS` | 4 | concurrent requests per worker (gthread) |
| `DB_POOL_SIZE` | 5 | connections a worker keeps open |
| `DB_MAX_OVERFLOW` | 5 | extra connections a worker may open under load |

With the defaults one instance serves 8 requests at once and can open at most
**2 x (5 + 5) = 20** connections. Keep `GUNICORN_THREADS` at or below
`DB_POOL_SIZE + DB_MAX_OVERFLOW`, or requests will queue for a connection and
fail after 10 seconds (`DB_POOL_TIMEOUT`).

Check the real limit on the database you provision rather than trusting a
plan page:

```sql
SHOW max_connections;
SELECT count(*) FROM pg_stat_activity;   -- in use right now
```

Worked example for a limit of 100: 3 instances x 2 workers x 10 = 60, + 1 cron
+ 5 headroom = 66. A fourth instance (86) still fits; a fifth does not without
lowering `DB_MAX_OVERFLOW`.

**What is cached.** Product lists and detail, categories, offers and CMS content
are cached for 30–300 seconds and dropped on any admin edit. With Redis the drop
is immediate everywhere; without Redis each worker holds its own copy and an edit
can take up to a minute to appear on other workers. Prices and stock are always
re-checked against the database at add-to-cart and at checkout, so a stale
listing can never sell at a stale price.

**What runs in the background.** Emails are sent from a small thread pool
inside the worker, so a slow mail provider does not delay checkout. Shiprocket
booking is an admin action that needs its answer and stays in the request;
delivery-check answers are cached for ten minutes per PIN code.

## 8. Scheduled job — `reconcile-payments`

The Razorpay webhook deliberately ignores a capture younger than 15 minutes
(it is almost always a checkout still in flight), so refunding a payment whose
checkout was abandoned depends on this sweep. Without it, such a customer stays
charged with no order.

```bash
flask reconcile-payments --hours 24            # refund abandoned captures
flask reconcile-payments --hours 24 --dry-run  # report only
```

- **Schedule:** every 30 minutes (`*/30 * * * *`). On Render this is a Cron
  Job service on the same native Python runtime, with the same environment
  group as the web service, and the command
  `flask reconcile-payments --hours 24`.
- **Safe to overlap and repeat:** a refunded payment stops reporting as
  captured, and each refund call carries an idempotency key.
- **Exit code:** non-zero when the gateway could not be reached or a refund
  failed, so the scheduler shows the run as failed. Search the logs for
  `ORPHANED_CAPTURE_REFUND_FAILED` — those payments need a manual refund in
  the Razorpay Dashboard.
- **History:** every run is written to the `job_runs` table and shown on the
  admin System Health panel.
- **Window:** `--hours` must be larger than the gap between runs. 24 gives
  plenty of overlap and costs nothing — already-refunded payments are skipped.

## 9. Frontend build

The static site builds with `npm ci && npm run build` in `frontend/` and
publishes `frontend/dist`. Build-time variables (all optional):

| Variable | Notes |
|---|---|
| `VITE_API_BASE_URL` | **leave unset** — the app then calls `/api` on its own origin |
| `VITE_GOOGLE_CLIENT_ID` | must match the backend's `GOOGLE_CLIENT_ID` |
| `VITE_SENTRY_DSN` | browser-project DSN; unset means the SDK is never downloaded |

## 10. Post-deploy checks

Run all of these after the first deploy, and the first three after every deploy.

```bash
# 1. The API is up and can reach its database.
curl -s https://<backend-host>/api/health                 # {"status":"ok"}

# 2. The storefront reaches the API through the rewrite.
curl -s https://www.yourdomain.com/api/health             # {"status":"ok"}
curl -s https://www.yourdomain.com/sitemap.xml | head     # product URLs

# 3. Security headers are present.
curl -sI https://<backend-host>/api/health | grep -iE "strict-transport|x-frame|content-security"

# 4. The database matches the code.
DATABASE_URL=... scripts/render_bootstrap_db.sh --check
```

**5. Rewrite latency.** Every API call a shopper makes goes through the
static site's rewrite, so its overhead is paid on every click:

```bash
scripts/check_rewrite_latency.sh https://www.yourdomain.com https://<backend-host>
```

It compares the median of 15 `/api/health` calls through the rewrite with 15
made to the backend directly, and exits non-zero if the rewrite adds more than
**150 ms**. If it does, that is the signal to move to the single-service layout
in section 1 — report the two numbers before deciding. Run it from a network
near your customers (India), not from a CI runner in another region.

**6. In the admin panel → System Health:**

- every service you configured shows **Configured**, none shows **Error**;
- press **Test connections** — each still shows Configured;
- open this page **through the storefront domain** (not the `onrender.com`
  backend URL). **Proxies in front of the server** must read the same number
  twice, e.g. "2 seen · 2 trusted". If they differ, set `TRUSTED_PROXY_COUNT`
  to the "seen" number and redeploy; the page shows a warning until they
  match. Then **Your IP as seen by the server** must be your own public IP
  (compare with any "what is my IP" site). Until this is right, either every
  visitor shares one rate-limit bucket (count too low) or a visitor can pick
  their own address (count too high);
- known limit of this layout: a request sent straight to the backend URL
  passes through fewer proxies than one sent through the rewrite, so there a
  caller can forge the address. Limits on signed-in routes are keyed on the
  account and sign-in is also limited per email, so neither depends on the
  address alone; the anonymous forms (contact, newsletter, wholesale,
  register, forgot-password) do. The single-service layout in section 1
  removes the difference;
- after 30 minutes, **Payment reconcile job** shows a recent successful run.

**7. By hand, once:** register, add to cart, check out cash-on-delivery, see
the order in the admin panel, cancel it. Reload a page while signed in — you
must stay signed in (this is what the same-origin rewrite is for). With
Razorpay test keys: one test payment, then cancel the order and confirm the
refund appears in the Razorpay Dashboard.

## 10b. Images and object storage

Images go to an S3-compatible bucket; the code is plain boto3 with
`endpoint_url` and path-style addressing (`app/services/objectstore.py`), so
any S3 store works by changing environment variables.

Three facts about Neon's buckets that are easy to trip over:

| | |
|---|---|
| The endpoint embeds the **branch id** | dev, test and production each have their own `S3_ENDPOINT_URL`. There is no single "project" endpoint. |
| Buckets are **per branch** | A branch created *before* the bucket existed does not have one. `scripts/refresh_storage_credential.py` creates it if missing. |
| A branch **reset destroys that branch's credentials** | The bucket and its objects survive, and public reads keep working — so the storefront looks healthy and only uploads fail, with `AccessDenied`. Re-run `python scripts/refresh_storage_credential.py --branch dev` after any reset. |

Moving existing images into a bucket (idempotent, `--dry-run` first):

```bash
DATABASE_URL=<branch, DIRECT> S3_ENDPOINT_URL=... S3_BUCKET=... S3_ACCESS_KEY_ID=... S3_SECRET_ACCESS_KEY=...   python scripts/migrate_images_to_objectstore.py --dry-run
```

It uploads each original plus the srcset widths (regenerating any that are
missing) and rewrites every stored URL. Admin → **System health** → storage
probes it for real: it writes an object, fetches it back with **no
credentials**, and deletes it, so a private bucket is caught before customers
see broken images.

## 11. Backups

Neon keeps a continuous history and can branch or restore from any point inside
the plan's retention window — **24 hours on the free plan**. Check that number
before launch; it is the one that decides how much you can lose.

That is not an off-platform copy. For anything you would be sorry to lose, dump
with the **direct** string and keep it elsewhere:

```bash
pg_dump "$DIRECT_DATABASE_URL" -Fc -f aanga-$(date +%Y%m%d).dump
```

The old `backend/db/backup.ps1` and `restore.ps1` were for the local Docker
database and were removed with it. See [DATABASE.md](DATABASE.md).

## 12. CI

`.github/workflows/ci.yml` runs on every pull request and on `main`: backend
`pytest` against a Postgres 17 **service container**, frontend `npm ci`,
`oxlint`, `vite build`. The service container is deliberate — concurrent runs
would fight over the single shared Neon `test` branch, and a fork's pull
request cannot read repository secrets. The comment at the top of the workflow
says how to point it at Neon instead. Render's `autoDeploy` is off in the
Blueprint, so a merge does not ship until someone presses Deploy.

## 13. Local development

The database is the Neon **dev** branch; there is nothing to install or start.
See [DATABASE.md](DATABASE.md). To bring it up to date after pulling new
migrations:

```bash
cd backend && venv/Scripts/python -m flask --app run apply-migrations
```

or, for the full idempotent pass with verification:

```bash
DATABASE_URL="$(neonctl connection-string dev   --project-id dry-base-24522506 --org-id org-long-mud-04364433   --role-name aanga_owner --database-name aanga)"   scripts/render_bootstrap_db.sh --migrate
```

## Rehearse a deploy locally

There is no longer a container stack that mirrors Render, and with the database
in the cloud and the runtime native there is much less left to mirror. What
remains worth doing before a deploy:

| Command | What it proves |
| --- | --- |
| `scripts/e2e.sh --fresh` | Every customer and admin flow, at four widths, against a dev branch reset to match production. The check before every deploy. |
| `scripts/reset_test_branch.sh` | The full backend suite against a `test` branch reset to production's schema — catches "the tests pass against a schema nobody will deploy". |
| `scripts/render_bootstrap_db.sh --check` | The deployed schema matches the code. |
| `cd frontend && npm run lint && npm run build` | What the static site build will do. |
| `pip install -r backend/requirements.txt` in a clean venv | What Render's build command will do. |

What this no longer covers, and the honest cost of removing Docker: gunicorn
itself is not exercised locally (it needs Unix; `flask run` is used instead), so
a fault specific to gunicorn's worker model would first appear on Render. The
API's own logs and `/api/ping` after a deploy are the compensating check.

Payments and courier keys: [GO_LIVE.md](GO_LIVE.md). When something is wrong in
production: [RUNBOOK.md](RUNBOOK.md).
