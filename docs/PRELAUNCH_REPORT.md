# Pre-launch report (Round 4)

Branch `hardening/phase-1-payment-integrity`. Nothing was pushed, merged or
deployed. No Razorpay or Shiprocket key was used or written anywhere.

## Verdict

**Not yet GO: one confirmation run is outstanding.** The last complete browser
run had 11 failures. All 11 were traced and fixed (10 were the test run using
up its own rate-limit allowance, 1 was a real defect on the Offers screen), but
the run that would confirm this was stopped by the machine running low on
memory. Four checks were queued behind it and have not been run: Lighthouse,
the throwaway-copy check, the final backend run, and generating the QA matrix.
See "Not finished" below for the exact commands.

If those come back clean, the verdict is **GO for a cash-on-delivery launch**,
once the six owner items in "What is left for you" are done.

**Online payments and courier booking: not yet.** They are built and pass
every test that can be run without keys. They become GO when
`scripts/verify_integrations.sh` prints six PASS lines with your test keys
(`docs/GO_LIVE.md`, stages 1 to 3). Until then the store hides "Pay online"
and the delivery check, and nothing fails.

No known BLOCKER or MAJOR defect is open.

## What was tested, and on what

A production-like copy built by `scripts/prod_local.sh`: a new Postgres 17
built only by `scripts/render_bootstrap_db.sh`, the backend image under
gunicorn with production settings and Redis, the built storefront behind the
rewrites from `render.yaml`, and the demo content (60 products, a live Diwali
campaign).

| Check | Result |
| --- | --- |
| Backend tests (`pytest`) | 651 passed on the last full run. 17 tests were added after it (emails, integration check, empty database, logs); those 17 pass on their own. A full run with all 668 is outstanding. |
| Browser tests (`scripts/e2e.sh`), 390 / 768 / 1280 / 1920 px | Last complete run: 641 passed, 11 failed, 300 skipped by design. The 11 are fixed; the confirming run was interrupted (see Verdict). |
| QA matrix (`docs/QA_MATRIX.md`) | **Not generated yet.** The generator (`scripts/gen_qa_matrix.py`) and its plan of rows, columns and evidence are written; it needs the final test results as input. |
| API routes with a passing success test (`docs/ENDPOINTS.md`) | 181 of 181 at the start of the round; to be regenerated after the final backend run. |
| `pip-audit` / `npm audit` | No known vulnerabilities (after the upgrades in `7d08b7c`) |
| Secret scan of the whole history and the built storefront | One real secret, already known (see MINOR 3). Nothing in the built storefront. |
| Backup, restore, demo removal on a throwaway copy | **Not run yet.** `scripts/prod_local.sh throwaway-check` is written but has never been executed. |
| Lighthouse, campaign live (performance / accessibility) | **Not run in this round.** Round 3 measured 90 or more on the same pages. |
| Lint and production build | Clean |

Skipped browser tests are deliberate and each says why: the slow-network and
failing-backend tests run at two widths, and three sign-in tests run at one
width because sign-ins are rate limited.

## Defects found in this round

Severity: **BLOCKER** would stop the launch or lose money or data. **MAJOR**
breaks a flow or a security rule for some people. **MINOR** is everything else.

### BLOCKER (3, all fixed)

| # | Defect | Fixed in |
| --- | --- | --- |
| B1 | `scripts/render_bootstrap_db.sh` failed on every new database (a stray `\n` in its own verification list). The first deploy to Render would have stopped at the database step. | `0bcb945` |
| B2 | A coupon on a bag was honoured for ever: after it expired, after its usage limit was reached, after it was switched off, and after the bag shrank below its minimum. A flat coupon could exceed the value of the bag. A coupon with "limit 1" could be used by everyone who had typed it in. | `25da8d8` |
| B3 | Renewing an admin session was limited to 60 an hour per internet address. Every page reload renews. Two or three staff on one office connection were sent back to the sign-in page, which itself allows 5 tries in 15 minutes. | `f64907a` |

### MAJOR (13, all fixed)

| # | Defect | Fixed in |
| --- | --- | --- |
| M1 | Two simultaneous submissions of one bag with no retry key (two tabs, a retry) made two orders. | `25da8d8` |
| M2 | Two customers racing for the last unit: the loser got a server error instead of "out of stock". Stock itself was always right. | `25da8d8` |
| M3 | Files that were not images were stored as uploaded if they had an image extension (an HTML page named `.png`, an SVG with a script). | `0bcb945` |
| M4 | The order email did not escape customer and product names. | `0bcb945` |
| M5 | Courier: no pickup was ever requested after the AWB was assigned, so nobody would come for the parcel; a courier timeout was an unhandled server error. | `6d3231e` |
| M6 | A refund bounced by the bank (`refund.failed`) left the order saying "refunded". | `6d3231e` |
| M7 | Known vulnerabilities in Pillow, requests, Flask, Werkzeug, Flask-Cors, marshmallow, python-dotenv, axios, react-router and four more. | `7d08b7c` |
| M8 | A bag or wishlist answer that arrived late replaced what the customer had just done: an added item, a removed coupon or a saved product vanished from the screen until the next reload. | `d7a2df0` |
| M9 | A returning customer who pressed "Add to bag" or the heart in the first moment after a page appeared was told to sign in (the session was still being restored). | `d7a2df0` |
| M10 | Account pages (orders, returns, addresses, profile) were wider than a phone screen; so were the Customers, Products and Newsletter screens of the dashboard on phones and tablets. | `d7a2df0`, `f64907a` |
| M11 | gunicorn closed idle connections after 2 seconds; behind a proxy that reuses connections this gives occasional 502 errors. | `6d3231e` |
| M12 | A new database had no announcement, feature cards or testimonials (the old seed migrations are not part of the bootstrap), so the home page had empty sections. The demo seed now creates them. For the real launch you add your own (Dashboard → Homepage). | `0bcb945` |
| M13 | The bootstrap script's fallback (when `psql` is not installed) could not reach a database on the same machine. | `0bcb945` |

### MINOR, fixed (9)

| Defect | Fixed in |
| --- | --- |
| Customer email addresses appeared in server logs. They are masked now (`p***@example.com`). | `25da8d8` |
| A misleading "database not reachable" warning at startup when two workers created the first admin at once. | `6d3231e` |
| Emails said "AANGA" whatever the store name setting was; amounts were not grouped the Indian way. | `0bcb945`, `25da8d8` |
| Typing the address of a dashboard screen outside your role showed a page of failed requests. It now says the screen is not part of the role. (The server always refused the data.) | `f64907a` |
| Store settings → Tagline was described as "shown in the footer" but the footer used an older setting. | `d7a2df0` |
| The Offers screen threw an unhandled error when the backend failed. | the last commit of the round |
| The courier order used a hard-coded fallback email address. | `6d3231e` |
| `scripts/prod_local.sh --keep` did not rebuild the storefront. | `451d7c8` |
| Demo removal, backup and restore had only been run on the main database. A throwaway-copy check is written (not yet run). | the last commit of the round |

### MINOR, open (8) — with a recommendation

| # | Finding | Recommendation |
| --- | --- | --- |
| 1 | Only two emails exist: order confirmation and password reset. A customer hears nothing when an order ships, is delivered, is cancelled or is refunded. | **Decision 1** below. |
| 2 | Resetting a password does not sign out the other devices that account is signed in on (sessions last until they expire). | **Decision 2** below. |
| 3 | An early `backend/.env.example` in the history (commit `4651da7`) contains a real admin password. Known since Round 1 (`docs/SECURITY_TODO.md`). | Change the admin password before launch; that makes the old one worthless. Removing it from the history is **Decision 4**. |
| 4 | Courier bookings use one parcel size and weight for every order (20 × 15 × 5 cm, 0.5 kg). Heavy orders will be under-declared. | **Decision 3** below. |
| 5 | If the courier accepts the order but assigns no AWB, the order stays in the Shiprocket panel without one. Pressing "Book shipment" again reuses it. | Leave; note it in the owner guide. |
| 6 | The audit log search looks at the summary, the action, the admin and the record id, but not inside the recorded changes (so a coupon code is found by filtering on "coupons", not by typing the code). | Small improvement after launch. |
| 7 | `backend/db/restore.ps1` restores only over the local development database. Production backups depend on the Render Postgres plan. | Check the plan's backup retention before launch (`docs/DEPLOYMENT.md`). |
| 8 | `backend/.env` still uses `localhost` in `DATABASE_URL`; on this Windows machine each new connection costs about 2 seconds more than `127.0.0.1`. Local only. | Change it by hand (I do not edit `.env`). |

## Not finished

Stopped when the machine ran low on memory. In this order, on a machine with
memory to spare (Docker plus four browsers):

```
scripts/prod_local.sh --keep
scripts/e2e.sh                                   # expect 0 failed
scripts/prod_local.sh throwaway-check            # first ever run: may need a fix
cd backend
venv/Scripts/python -m pytest -o addopts="" -q --junitxml=tests/.junit.xml
venv/Scripts/python scripts/gen_endpoints.py
cd ..
backend/venv/Scripts/python scripts/gen_qa_matrix.py   # exits 1 and lists any cell without passing evidence
```

Then Lighthouse on the home page, `/shop` and a product page. `gen_qa_matrix.py`
has never been run either, so expect to correct a few evidence names on its
first run.

## Decisions I need from you

These are product decisions, not bug fixes, so nothing was built for them.

1. **More emails?** Shipped (with tracking link), delivered, cancelled, refund
   issued. Recommended before the first paid order; about a day of work.
2. **Sign out everywhere on password reset?** Recommended: yes. It needs a
   small change to how sessions are checked.
3. **Per-product weight for courier rates?** Needed only if you sell items
   much heavier than a shirt. Otherwise leave the default.
4. **Remove the old admin password from the git history?** It rewrites every
   commit and everyone must clone again. Optional once the password is changed.

## What is left for you

Before a cash-on-delivery launch:

1. Change the admin password (`flask --app run set-admin-password`), because
   of MINOR 3.
2. In the Render Dashboard, fill in the `aanga-backend` values marked
   `sync: false` in `render.yaml`: `ADMIN_EMAIL`, `ADMIN_PASSWORD`,
   `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` (product pictures are stored there
   in production), `RESEND_API_KEY` and `EMAIL_FROM` (without them no email is
   sent; the store still works).
3. Replace the demo content with your own: products, pictures, hero slides,
   testimonials, About / Shipping / Returns / Privacy / Terms text, GSTIN and
   contact details (Dashboard → Store settings). Then Dashboard → Demo content
   → Remove demo content.
4. Check the Render Postgres plan's backups (MINOR 7).
5. Answer decisions 1 and 2.
6. Run `scripts/e2e.sh --fresh` once more on the commit you deploy.

For online payments and courier booking, follow `docs/GO_LIVE.md`: add test
keys, run the check and the verify script, register the webhook, switch to
live keys after KYC, and watch the five things listed there in the first week.

## The integration boundary

What "tested without keys" means for Razorpay and Shiprocket:

- Every outgoing call is answered from `backend/tests/fixtures/` in the shape
  the providers document, so the tests prove what the store sends (address,
  authentication, amounts in paise, idempotency keys) and that it reads every
  answer correctly, including refusals, timeouts and an expired token.
- Covered: payment order, checkout signature (HMAC with a test secret),
  capture check, refund on cancel and on "paid but out of stock", every
  webhook event (authorized, captured, failed, order.paid, refund created /
  processed / failed), repeated delivery, the reconcile sweep; courier sign-in
  and token renewal, delivery check, order, AWB, pickup, tracking.
- Not covered, because only the providers can show it: that your keys are
  right, that your account is activated, that your pickup address is verified.
  Those are exactly the six steps of `scripts/verify_integrations.sh`.
