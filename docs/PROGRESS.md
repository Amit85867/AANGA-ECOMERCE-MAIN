# AANGA — production-readiness progress

Working checklist for the hardening loop. One task at a time: investigate,
change, verify, commit, tick. A ticked task carries a one-line note of what
changed and how it was verified.

Legend: `[x]` done · `[ ]` open · **BLOCKED** = failed verification three times ·
**DEFERRED** = waiting on something outside the repo · **CHECKPOINT** = stop and ask.

## Deferred (waiting on the owner)

- **DEFERRED — Razorpay test keys.** `RAZORPAY_KEY_ID` (must start `rzp_test_`),
  `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` go in `backend/.env` only.
  Until then payment endpoints answer "integration not configured" and tests
  use mocks. Blocks the live-payment steps of Phase 7.
- **DEFERRED — Shiprocket credentials.** `SHIPROCKET_EMAIL`, `SHIPROCKET_PASSWORD`,
  `SHIPROCKET_PICKUP_PINCODE` go in `backend/.env` only. Read-only calls
  (serviceability, tracking) only; shipment / AWB / pickup creation stays mocked.
  Blocks the live pincode check in Phase 7.

## Phase 0 — Secure the current work

- [x] Run the full test suite — 141 passed on Postgres 17 (run twice); `vite build` clean.
- [x] Commit the uncommitted batch — `d7cedc1` DB dockerization, `58f76b8` order
  lifecycle, `1eb4b91` admin settlements / feature icons, plus `efc8cb0` for
  storefront fixes that fitted none of the three.
- [x] Ignore `backend/static/uploads/` — `13b9048`. Note: 30 images committed
  earlier are still tracked; the 47 new ones are now ignored.

## Phase 1 — Endpoint inventory and contract tests

- [ ] Generate the route inventory from Flask's `url_map` into `docs/ENDPOINTS.md`
  (method, path, auth: public / customer / admin, status).
- [ ] Map every frontend API call to a backend route; flag calls with no route,
  routes no screen uses, and payload mismatches.
- [ ] Fix every mismatched or failing endpoint found by the mapping.
- [ ] Contract tests per route: success, validation error, unauthenticated,
  wrong role, not found. Add what is missing.
- [ ] Every row in `ENDPOINTS.md` ✅ with a test.

## Phase 2 — Known loose ends

- [ ] `reconcile-payments`: paginate past 100 payments, idempotent, logs what it did.
- [ ] Webhook handler idempotent on the Razorpay event id.
- [ ] `RAZORPAY_WEBHOOK_SECRET` / `SHIPROCKET_PICKUP_PINCODE` in `.env.example`
  and in production config validation.
- [ ] Every production env var documented in `.env.example`.
- [ ] Document scheduling `reconcile-payments` as a Render Cron Job.
- [ ] `docs/SECURITY_TODO.md`: rotating the leaked admin password and purging it
  from history. **CHECKPOINT before the purge.**

## Phase 3 — Admin dashboard

- [ ] Audit every admin page; record gaps per page here as new tasks.
- [ ] Lists: server-side pagination, search, filters, sort, empty / loading / error states.
- [ ] Forms: validation matching the backend, disabled submit while saving, toasts, no double submit.
- [ ] Destructive actions: confirmation dialog; soft delete where the model allows.
- [ ] Dashboard: one aggregated KPI endpoint (revenue today/7d/30d, orders by
  status, out-of-stock, low-stock, pending returns, recent orders) with a
  date-range filter; index the columns it uses.
- [ ] System Health panel + admin-only endpoint (DB, Redis, Razorpay, Shiprocket,
  Supabase, version, last reconcile run). Integrations show Configured /
  Not configured / Error and never display values.
- [ ] Maintenance mode toggle: friendly customer page, admins can still log in.
- [ ] Audit log for orders, refunds, products and settings, viewable by admins.
- [ ] Every admin endpoint enforces the admin role server-side (covered by Phase 1 tests).

## Phase 4 — Modern corporate UI (theme frozen)

- [ ] **CHECKPOINT** — `docs/UI_PLAN.md`: frozen theme tokens, component list,
  page-by-page plan. Show before building.
- [ ] Shared component layer on the tokens.
- [ ] Product listing with filters.
- [ ] Product detail.
- [ ] Cart.
- [ ] Checkout and order success.
- [ ] Account dashboard (orders, returns, addresses).
- [ ] Auth pages.
- [ ] Admin shell.
- [ ] Responsive 360px → wide, keyboard access, visible focus, AA contrast, no layout shift.
- [ ] Lighthouse mobile ≥ 90 performance / ≥ 95 accessibility on home, listing, product. Scores recorded here.

## Phase 5 — Scalability and production readiness

- [ ] Stateless app: no local file storage in production, limits in Redis.
- [ ] Indexes for common filters / sorts; remove N+1 queries (SQL logging).
- [ ] SQLAlchemy pool sized against the Postgres connection limit; numbers documented.
- [ ] Every list endpoint paginated with a capped page size.
- [ ] Short-TTL cache on catalogue / categories, invalidated on admin edits.
- [ ] Slow work (email, Shiprocket) off the request path.
- [ ] JSON logging with request ids; Sentry on frontend and backend.
- [ ] Security headers, CORS locked to `SITE_URL`, rate limits on auth, checkout, reviews, returns.

## Phase 6 — Render deployment preparation (no deploy)

- [ ] **CHECKPOINT** — choose the layout: (a) static site + `/api` rewrite,
  (b) custom domain with api subdomain, (c) Flask serves the built frontend.
- [ ] `render.yaml` for the chosen layout.
- [ ] `scripts/render_bootstrap_db.sh`.
- [ ] `docs/DEPLOYMENT.md` updated; webhook URL points straight at the backend.

## Phase 7 — End-to-end verification and browser demo

- [ ] Start the full stack locally.
- [ ] Customer walkthrough in Chrome (payment and pincode steps need the deferred credentials).
- [ ] Admin walkthrough in Chrome.
- [ ] Console and network clean on every page; mobile width checked.
- [ ] GIFs of both flows.
- [ ] Final summary: changes per phase, test counts, Lighthouse scores, BLOCKED items, manual steps left.

## Discovered along the way

- [ ] `.claude/settings.local.json` is tracked and shows as modified on every
  session — decide whether to untrack it (owner's call).
