# Load test

A small [k6](https://k6.io) test for the storefront API: `loadtest/storefront.js`.

**Status: written, never run.** The script parses, and every endpoint and
status code it relies on was checked against the code, but k6 itself has not
executed it. Expect to adjust something on the first smoke run.

It is meant for a **deployed staging environment**, not a laptop: the questions
it answers (does one Render instance hold a busy day, where does the database
connection pool run out, what does the `/api` rewrite cost under load) have no
meaning locally. The script refuses to start without `TARGET_ENV=staging`.

## What it covers

| Scenario | Who | Requests |
|---|---|---|
| `browse` | anonymous visitors | home page data (6 CMS calls, categories, featured products), listing with paging / category / sort / search, facets, 2–3 product pages each with reviews |
| `cart` (optional) | one signed-in test account | read cart, add a line, remove a line |

Each virtual user pauses 1–4 seconds between pages, so 50 users is roughly
15–20 requests a second.

**Never called:** placing an order, `/api/payments/*`, the webhook,
`/api/shipping/serviceability` (it reaches Shiprocket), registration, password
reset, contact / newsletter / wholesale forms, anything under `/api/admin`.
The run costs no money, sends no email and leaves no order behind. The only
thing it writes is the test account's cart, which it empties at the end.

## Before you run it

1. **A staging environment that is not production.** A second set of Render
   services from the same `render.yaml` (a separate Blueprint instance or a
   preview environment), with its **own database** and **Razorpay test keys**.
   Do not point this at the live site: the stress and spike profiles are meant
   to push it until it degrades.
2. **Same plans as production.** Numbers from a smaller instance or database
   tell you about that instance. Note the plan of the API, the database and
   Key Value in the results.
3. **A seeded catalogue** (`backend/db/seed_catalogue.py`, see DEPLOYMENT.md).
   The script stops if there are no products.
4. **`TRUSTED_PROXY_COUNT` verified** on staging (DEPLOYMENT.md, post-deploy
   step 6). All the test traffic comes from one address; if the proxy count
   is wrong the limiter behaves differently from production.
5. **For the cart scenario:** register one customer on staging by hand and
   keep its email and password out of the repository.
6. **Install k6** on the machine that will generate the load
   (<https://grafana.com/docs/k6/latest/set-up/install-k6/>): a single binary,
   nothing is added to this project. Run it from a machine with a good
   connection, ideally in or near India, not from the staging server itself.
7. **Tell Render nothing, but watch it.** Open the API service's Metrics tab
   (CPU, memory, response time), the database's Metrics tab (connections) and
   the API logs before starting.

## Running it

Go through the profiles in order and stop at the first one that fails.

```bash
# 1. Smoke — 1 visitor, 1 minute. Proves the script and the environment work.
k6 run -e BASE_URL=https://<staging-storefront-domain> -e TARGET_ENV=staging loadtest/storefront.js

# 2. Load — 50 visitors for 5 minutes (8 minutes in all). The pass/fail run.
k6 run -e PROFILE=load -e BASE_URL=https://<staging-storefront-domain> -e TARGET_ENV=staging \
  -e LOADTEST_EMAIL=<test customer> -e LOADTEST_PASSWORD=<its password> \
  --summary-export=load-summary.json loadtest/storefront.js

# 3. Stress — climbs to 300 visitors over 9 minutes. Finds the limit.
k6 run -e PROFILE=stress -e BASE_URL=... -e TARGET_ENV=staging loadtest/storefront.js

# 4. Spike — 10 visitors, then 250 within ten seconds, held for two minutes.
k6 run -e PROFILE=spike -e BASE_URL=... -e TARGET_ENV=staging loadtest/storefront.js
```

`BASE_URL` is the **storefront** domain, so requests take the same path a
browser does (static site → `/api` rewrite → API). To measure what the rewrite
costs under load, repeat the `load` profile with `BASE_URL` set to the API's
own `onrender.com` URL and compare the two `http_req_duration` lines. This is
the same question `scripts/check_rewrite_latency.sh` asks for a single request.

Leave five minutes between runs so the instance and the cache start from the
same state each time. The catalogue cache means the second run of anything is
faster than the first; the first is the honest one.

## Reading the result

k6 prints a summary and exits non-zero if a threshold fails.

| Threshold | Meaning | If it fails |
|---|---|---|
| `http_req_failed < 1%` | 5xx, timeouts, refused connections | read the API logs for the same minutes: `QueuePool limit` means the connection pool (below); `WORKER TIMEOUT` means a request took over 60 s |
| `catalogue p95 < 800 ms`, `p99 < 2 s` | product listing, product page, facets, categories, reviews | find which URL in the summary (product pages are grouped as `/api/products/:slug`); slow uncached listings point at a missing index or the cache not being Redis |
| `cms p95 < 500 ms` | banners, announcements, settings… all cached | if these are slow everything is: the instance is out of CPU |
| `cart p95 < 1 s` | signed-in reads and writes, never cached | database latency or pool wait |
| `page_data_time p95 < 2.5 s` | all the API calls one page needs, start to finish | the number a visitor feels |
| `rate_limited < 0.1%` | any 429 | the test only calls routes with no limit, so a 429 means a limiter is applied where it should not be, or keyed wrongly |
| `checks > 99%` | responses had the expected status | see which check failed in the summary |

These numbers are starting points chosen for a small store, not measured
targets. After the first `load` run, replace them with what the environment
actually does plus a margin, so the test catches regressions.

**For stress and spike, failing thresholds is expected.** Write down instead:

- the number of visitors at which p95 first passes 800 ms, and at which errors
  first appear — that is the capacity of the current plan;
- what gave way first: API CPU at 100 %, API memory (a restart shows as a gap
  in the metrics and a burst of 502s), or database connections at the limit;
- whether it recovered by itself once the load dropped, and how long that took.

### The limits you are most likely to meet

- **Database connections.** The API can open at most
  `instances × WEB_CONCURRENCY × (DB_POOL_SIZE + DB_MAX_OVERFLOW)` connections
  (2 × 10 = 20 with the defaults), and it serves `WEB_CONCURRENCY ×
  GUNICORN_THREADS` (2 × 4 = 8) requests at once. See DEPLOYMENT.md section 7
  before raising either, so the total stays under the database's
  `max_connections`.
- **One instance, 8 requests at a time.** Past that, requests queue and
  latency climbs in a straight line. More threads help while the CPU is idle;
  more instances help once it is not.
- **The cache.** If Key Value is not attached, each worker caches on its own
  and the limiter counts per worker. System Health shows whether it is.

## What this test does not tell you

- **Checkout capacity.** Orders, payment verification and the webhook are not
  exercised: they would create orders and call Razorpay. Their correctness is
  covered by the test suite; their throughput is unmeasured.
- **Browser performance.** No images, JavaScript or CSS are fetched. That is
  Lighthouse's job.
- **Many distinct customers.** The cart scenario uses one account, so it
  exercises one cart and one rate-limit key.
- **Long runs.** Nothing here runs for more than ten minutes; a slow memory
  leak would not show.

## Afterwards

- Save the k6 summary and screenshots of the Render metrics for the same
  window, and note the plans and the commit that was deployed.
- Delete the test customer, or leave it and reuse it; its cart is emptied by
  the script.
- If staging was created only for this, delete its services so they stop
  billing.
