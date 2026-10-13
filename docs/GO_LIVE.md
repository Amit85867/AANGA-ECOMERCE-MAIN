# Going live: payments and delivery

The store runs today with cash on delivery only. Online payment (Razorpay) and
courier booking (Shiprocket) are built and tested but switched off, because no
keys are set. Adding the keys switches them on; no code changes.

Work through the five stages in order. Each one ends with a check that tells
you whether to continue.

Keys go in two places and nowhere else: `backend/.env` on your own machine,
and the `aanga-backend` environment group in the Render Dashboard. Never in a
code file, a commit, a chat or a screenshot.

---

> Test keys go in `backend/.env`, which talks to the Neon **dev** branch, so
> nothing here can touch production data. Live keys are only ever set in the
> Render Dashboard.

## 1. Add the TEST keys (your machine)

**Razorpay** — Dashboard, with the *Test mode* switch on:

| Setting in `backend/.env` | Where it comes from |
| --- | --- |
| `RAZORPAY_KEY_ID` | Account & Settings → API keys → Generate test key. Starts with `rzp_test_`. |
| `RAZORPAY_KEY_SECRET` | Shown once, next to the key id. |
| `RAZORPAY_WEBHOOK_SECRET` | You invent it in stage 3. Any long random text; leave empty for now. |

**Shiprocket** — Settings → API → Configure → *Create an API user*. This is a
separate login from the one you use for the Shiprocket panel.

| Setting in `backend/.env` | Where it comes from |
| --- | --- |
| `SHIPROCKET_EMAIL` | The API user's email. |
| `SHIPROCKET_PASSWORD` | The API user's password. |
| `SHIPROCKET_PICKUP_PINCODE` | The PIN code of your verified pickup address. |
| `SHIPROCKET_PICKUP_LOCATION` | The *nickname* of that pickup address in Shiprocket (Settings → Pickup addresses). Defaults to `Primary`. |

Restart the store (`scripts/dev.ps1` or `scripts/dev.sh`).

**What changes by itself after the restart**

- Checkout offers "Pay online" next to "Cash on delivery".
- Product pages show the "Check delivery" PIN code box.
- The order screen in the dashboard gets a working "Book shipment" button.
- Dashboard → System health shows Razorpay as *Connected (test mode)* and Shiprocket as *Signed in to Shiprocket*.

## 2. Check, then verify

```
cd backend
flask --app run check-integrations
```

It lists every outside service as OK, NOT CONFIGURED or PROBLEM, with the fix
for each problem. It makes one read-only call per service and prints no key.
Continue when Razorpay and Shiprocket both say OK.

Now place **one** order in the storefront with "Pay online":

- card `4111 1111 1111 1111`, any future expiry, any CVV, any name; or
- UPI id `success@razorpay`.

Then run:

```
scripts/verify_integrations.sh
```

| Step | What it proves |
| --- | --- |
| 1. Test checkout | Razorpay accepts the keys and opens a payment order. |
| 2. Payment verification | The order you just paid for is captured at Razorpay, for exactly the order total. |
| 3. Refund on cancel | Cancelling that order returns the (test) money. |
| 4. Signed webhook | The webhook accepts your secret and refuses a forgery. Fails until stage 3 is done. |
| 5. Reconcile payments | The half-hourly safety sweep runs cleanly. |
| 6. Live pincode check | Shiprocket answers a real delivery check from your pickup PIN code. |

Each line prints PASS or FAIL with the reason. The script refuses to run with
live keys, because step 3 refunds an order.

Also try, by hand, once:

- A payment that fails (card `4000 0000 0000 0002`): the customer returns to
  checkout with the bag intact and no order is created.
- "Book shipment" on a test order. **This creates a real shipment in
  Shiprocket** (it has no sandbox). Cancel it in the Shiprocket panel straight
  away, or skip this until your first real order.

## 3. Register the webhook

The webhook is how the store hears about a payment when the customer's browser
closes before returning from the payment page, and about refunds.

Razorpay Dashboard → Account & Settings → Webhooks → Add new webhook:

- **URL**: `https://<your API address>/api/payments/webhook`
  (on Render: the address of the `aanga-api` service)
- **Secret**: a long random text. Put the same text in `RAZORPAY_WEBHOOK_SECRET`.
- **Events**: `payment.captured`, `payment.failed`, `refund.processed`, `refund.failed`

Test mode and live mode have separate webhook lists. Register it in both.

Run `scripts/verify_integrations.sh` again; step 4 now passes.

## 4. Switch to LIVE keys

Do this only after Razorpay has approved your KYC and activated the account.

1. Razorpay Dashboard → switch to *Live mode* → generate live keys (`rzp_live_…`).
2. Add the webhook again under Live mode (stage 3) with a **new** secret.
3. In Render → `aanga-backend` environment group, set `RAZORPAY_KEY_ID`,
   `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` and the four `SHIPROCKET_…`
   values. Save; Render restarts the services.
4. Dashboard → System health must show Razorpay as **Connected (live mode)** and
   Shiprocket as **Signed in to Shiprocket**.
5. Buy one cheap product yourself with a real card. Check that the order shows
   as paid, the confirmation email arrives, and the payment appears in
   Razorpay. Cancel it from the dashboard and check that the refund appears in
   Razorpay (the money takes 5–7 working days to reach the card).

Do not run `scripts/verify_integrations.sh` against live keys; it will refuse.
`flask check-integrations` is safe with live keys.

If something is wrong, remove `RAZORPAY_KEY_ID` from Render and save. Within a
minute "Pay online" disappears and the store carries on with cash on delivery.

## 4b. Product images are already live

Images do not need keys and are not part of the payment/courier switch-on: they
are served from the Neon `product-images` bucket as soon as the `S3_*` values
are set on Render (see [DEPLOYMENT.md](DEPLOYMENT.md) §10b).

Check once, before the first order:

* Admin → **Store → System health** → *Object storage* must say **Connected**.
  The probe writes an object, fetches it back **with no credentials**, and
  deletes it, so it catches a bucket that is private — the failure where the
  admin can upload happily and every customer sees a broken image.
* Open a product page as a visitor and confirm the pictures load.

If uploads start failing with `AccessDenied` after someone resets a branch,
that is expected: a reset destroys that branch's storage credentials. Re-issue
them (`python scripts/refresh_storage_credential.py --branch dev`) or, for
production, issue a new credential and update the values on Render.

## 5. What to watch in the first week

Daily, two minutes:

| Where | What you want to see |
| --- | --- |
| Dashboard → System health | Every row green. "Reconcile payments" ran in the last 30 minutes with 0 failed. |
| Dashboard → Settlements | Yesterday's paid orders match the Razorpay settlement report. |
| Dashboard → Orders, filter *Payment: paid*, *Status: cancelled* | None. A cancelled order that still says "paid" means its refund did not go through: refund it from the Razorpay Dashboard. |
| Razorpay Dashboard → Webhooks | No failed deliveries. |
| Shiprocket panel | Every shipped order has a pickup scheduled. |

Log lines that need a person the same day (Render → `aanga-api` → Logs; search for the word):

| Log line | Meaning | What to do |
| --- | --- | --- |
| `PAID_BUT_NO_ORDER` | A customer paid but the last unit sold first. The payment was refunded automatically if the line says `refunded=True`. | If `refunded=False`, refund it in Razorpay and write to the customer. |
| `ORPHANED_CAPTURE_REFUND_FAILED` | The sweep found a payment with no order and could not refund it. | Refund it in Razorpay. |
| `RAZORPAY_REFUND_FAILED` | The bank bounced a refund. The order is marked paid again. | Refund it again from Razorpay. |
| `SHIPROCKET_PICKUP_NOT_SCHEDULED` | The shipment was booked but the courier did not accept the pickup. | Press "Schedule pickup" in Shiprocket. |
| `PAYMENT_AMOUNT_MISMATCH` | Someone changed their bag between paying and confirming. No order was made. | Nothing, unless it repeats for one customer. |

Before every later deploy, run the regression suite: `scripts/e2e.sh --fresh`.
It resets the Neon dev branch to match production, reseeds it, and drives every
customer and admin flow at four screen widths.

When something is wrong in production, start from [RUNBOOK.md](RUNBOOK.md).
