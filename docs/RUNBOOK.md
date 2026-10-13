# AANGA — runbook

What to do when something is wrong in production. Deploying is
[DEPLOYMENT.md](DEPLOYMENT.md); turning on payments and the courier is
[GO_LIVE.md](GO_LIVE.md); the database itself is [DATABASE.md](DATABASE.md).

The shape of the system, so the symptoms below make sense:

```
browser ──► aanga-web (Render static site)
               /api/* ──rewrite──► aanga-api (Render, native Python, gunicorn)
                                      ├──► Neon production branch (Postgres 17, Singapore)
                                      ├──► Upstash Redis   (rate limits + catalogue cache, optional)
                                      ├──► Supabase Storage (product images)
                                      ├──► Razorpay, Shiprocket, Resend
                                      └──◄ aanga-reconcile-payments (cron, every 30 min)
```

## First two commands, always

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://<domain>/api/ping     # the app
curl -s https://<domain>/api/health                                    # the app + database
```

`/api/ping` answers without touching the database. `/api/health` opens a
connection, so it also tells you whether Neon is reachable **and wakes a
suspended compute**.

| ping | health | Means |
|---|---|---|
| 200 | `{"status":"ok"}` | The stack is up. The fault is elsewhere — read on. |
| 200 | `{"status":"degraded"}` 503 | The app is up, the database is not. → [Database unreachable](#database-unreachable) |
| 000 / 502 / 503 | — | The service is down or restarting. → [API down](#api-down) |
| 200 but only on `aanga-api`'s own URL, not the domain | — | The rewrite is broken. → [Storefront up, API 404](#storefront-up-api-404) |

Then: Render Dashboard → `aanga-api` → **Logs**, and the admin's
**Store → System health**, which reports the database, pending migrations and
every integration in one page.

---

## The first request of the day is slow

**Not a fault.** Neon scales a branch to zero after five idle minutes. The next
connection wakes it, which takes about a second; `pool_pre_ping` discards the
connection the suspend closed instead of handing a dead one to a request.

It becomes a fault if it happens *all the time*, which means the compute is
being woken constantly — see [CU-hours climbing](#cu-hours-climbing-with-no-traffic).

## API down

`/api/ping` does not answer at all.

1. Render → `aanga-api` → **Events**: a failed deploy, or an out-of-memory
   restart?
2. **Logs**, at the top of the boot sequence. The app refuses to start, loudly
   and on purpose, when its configuration is wrong:
   `Refusing to start: insecure production configuration` lists exactly which
   variables are missing or still at a development default.
3. Common causes, in the order they actually happen:
   - a `sync: false` variable was never filled in after a Blueprint sync;
   - half an integration was set (`RAZORPAY_KEY_ID` without
     `RAZORPAY_KEY_SECRET`, `SHIPROCKET_EMAIL` without the pincode) — the app
     refuses rather than failing quietly and expensively later;
   - `RATELIMIT_ENABLED=false` leaked in from an e2e run. That switch is
     refused in production.
4. **Rollback:** Render → **Manual Deploy → Deploy a specific commit**, pick the
   previous good one. The database is *not* rolled back by this; if the bad
   deploy also changed the schema see [Bad migration](#bad-migration).

## Database unreachable

`/api/health` returns `degraded`, logs show `DATABASE_UNREACHABLE`.

1. Neon console → project `AANGA` → **Branches → production**. Is the compute
   `Active` or `Idle`? Idle is normal and resolves itself on the next request.
2. Neon status page. A regional incident in `ap-southeast-1` is not something
   you can fix from here.
3. Did someone change the password on `aanga_owner`, or reset/delete the
   production branch? A reset changes nothing about the connection string; a
   *deleted and recreated* branch changes the endpoint, and `DATABASE_URL` on
   Render must be updated.
4. Connection exhaustion is unlikely but checkable: the pooled endpoint allows
   10,000 connections. If `DATABASE_URL` was set to the **direct** string by
   mistake the ceiling is 105, and that is reachable. Confirm the host has
   `-pooler` in it.

## Bad migration

A deploy changed the schema and the app is now broken.

Neon makes this recoverable in a way a normal Postgres is not: the branch has a
continuous history within the plan's retention window (**24 hours on the free
plan**).

1. **Do not** reset the production branch — that throws away everything since
   it diverged from its parent, including real orders.
2. Neon console → **Branches → production → History**. Create a *new branch*
   from the timestamp just before the bad deploy. Inspect it. It is a full,
   writable copy and costs only what it changes.
3. If the data on the new branch is right, you have two options: point
   `DATABASE_URL` at it (fastest, and the old branch stays for forensics), or
   copy the specific rows back.
4. Then fix the migration and re-run
   `scripts/render_bootstrap_db.sh --migrate` with the **direct** string.

## Payments

### A customer was charged but has no order

This is the failure the system is built to catch, and it usually self-heals.

1. The Razorpay webhook (`payment.captured`) and the browser's `/verify` call
   race; "captured with no order" is the **normal** state for a few seconds.
2. `RAZORPAY_ORPHAN_GRACE_SECONDS` (default 900) is how long a capture may
   exist without an order before it counts as abandoned.
3. `aanga-reconcile-payments` runs every 30 minutes, finds those, and refunds
   them. Refunds carry an idempotency key, so repeats are safe.
4. To act now, from Render → `aanga-api` → **Shell**:

   ```bash
   flask --app run reconcile-payments --hours 24 --dry-run   # report only
   flask --app run reconcile-payments --hours 24             # actually refund
   ```

5. If the sweep reports nothing and the customer still has no order, check
   Render → `aanga-reconcile-payments` → **Events**: a cron job that has not
   run is the one thing that breaks this safety net.

### Webhook deliveries failing

Razorpay Dashboard → Settings → Webhooks shows delivery attempts and responses.

- `401`/`400`: `RAZORPAY_WEBHOOK_SECRET` does not match the one in the
  dashboard.
- Timeouts: the service was asleep. Free Render services sleep when idle —
  that is why the Blueprint uses `starter`, not `free`.
- The endpoint is `https://<domain>/api/payments/webhook`, and the signature is
  computed over the **raw** body, so anything that re-serialises it breaks
  authentication.

## Rate limiting behaving oddly

### Everyone is being limited at once

`TRUSTED_PROXY_COUNT` is wrong, so every request looks like it comes from the
proxy's IP and they all share one bucket. Admin → **System health** reports
"Proxies in front of the server: N seen" and "Your IP as seen by the server".
Set the variable to that N and redeploy. Check it through the **storefront
domain**, not the API's own URL — the hop count differs.

### Limits are far looser than documented

`RATELIMIT_STORAGE_URI` is unset, so counters live in each gunicorn worker.
With `WEB_CONCURRENCY=2` a caller gets roughly twice the advertised allowance
and nothing is shared between instances. The startup log says so explicitly.
Fix: an Upstash Redis URL.

## Storefront up, API 404

Pages load, every API call 404s. The static site's rewrite is pointed at the
wrong host: `render.yaml` hard-codes `https://aanga-api.onrender.com` in three
places because Render cannot reference a service by name there. If the API got
a suffixed name, update all three and sync.

## Images missing

Product pages render with broken images.

1. `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` set? The app refuses to start
   without them in production, so if it is running they are set — the bucket
   may still be wrong or private. It must be **public** and named
   `product-images`.
2. **The likely cause for demo data:** images follow whoever ran the seed. The
   `production` branch was seeded from a laptop with no Supabase keys, so those
   `product_images` rows point at `/static/uploads/…` files that exist only on
   that laptop. See the warning in [DATABASE.md](DATABASE.md#seeding-the-catalogue).
   Fix by replacing the demo catalogue with real products through the admin, or
   re-seeding against the deployed API.

## Nobody is getting email

Order confirmations and password resets are the only two emails.

1. Blank `RESEND_API_KEY` means emails are **logged, not sent** — by design,
   and the app runs happily. Check the logs for the message body.
2. `EMAIL_FROM` must be on a domain verified in Resend.
3. Email is sent from a two-thread in-process pool. On a graceful shutdown the
   queue is flushed; on a hard kill (OOM, `SIGKILL`) anything queued is **lost
   silently** — there is no retry and no outbox. A lost confirmation does not
   lose the order, which is committed to Postgres first. A lost password reset
   is recovered by asking again.

## CU-hours climbing with no traffic

Neon bills compute time. Something is holding the branch awake.

1. **A health check that touches the database.** The Render health check must
   be `/api/ping`, which touches nothing. If it is `/api/health`, every probe
   opens a connection and the compute never sleeps.
2. External uptime monitors pointed at `/api/health` — same problem.
3. The cron job wakes the compute every 30 minutes by design; that is a few
   seconds each time, not a day's worth.
4. Check: Neon console → **Branches**, the "Compute last active" column, and
   Monitoring for the shape of the usage.

## Useful commands

From Render → `aanga-api` → **Shell** (the service's own environment, so
`DATABASE_URL` is already set):

```bash
flask --app run check-schema                 # does the database match the code?
flask --app run check-integrations           # which integrations are configured
flask --app run verify-integrations          # actually call them (uses live keys)
flask --app run reconcile-payments --hours 24 --dry-run
flask --app run set-admin-password           # rotate the master admin password
flask --app run remove-demo-content          # delete demo products, banners, testimonials
```

From a laptop with this repository, against a branch's **direct** string:

```bash
scripts/render_bootstrap_db.sh --check       # verify schema, change nothing
scripts/render_bootstrap_db.sh --migrate     # apply outstanding migrations
```

## Escalation order

1. `/api/ping`, then `/api/health`.
2. Render logs and Events for `aanga-api`.
3. Admin → Store → System health.
4. Neon console: branch state, Monitoring, History.
5. Provider dashboards: Razorpay webhooks, Shiprocket, Resend, Sentry.
6. Roll back the deploy (Render → Manual Deploy → previous commit) before
   touching the database. Rolling the app back is cheap and reversible;
   rolling the database back is neither.
