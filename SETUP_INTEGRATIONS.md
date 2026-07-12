# AANGA — Activating the New Features

Everything below is code-complete. To make it live, apply the two SQL scripts
and (optionally) add the payment/delivery API keys. Nothing new breaks if you
skip the keys — the site simply keeps COD-only and hides Shiprocket errors
behind admin buttons.

---

## 1. Run the SQL migrations (Supabase → SQL Editor)

Run these files' contents, in any order:

- `backend/migrations_cms.sql` — hero banners, announcements, promo banners,
  site settings (+ seed rows that mirror the current homepage).
- `backend/migrations_cms_components.sql` — testimonials, feature ("Why Choose")
  cards, and homepage-text settings (+ example rows so nothing renders blank).
- `backend/migrations_password_resets.sql` — the `password_resets` table used by
  the forgot-password flow.

The rest of the schema already exists.

### Admin sections these unlock
- **Testimonials** — customer reviews. Only 4–5★ appear up front on the homepage;
  lower ratings sit behind a "View more reviews" button. Each has a photo (upload
  or URL).
- **Why Choose** — the promise/feature cards (icon or uploaded image + text).
- **Site Settings → Homepage Text** — section headings ("Best Sellers", "Shop by
  Category"), newsletter heading/subtitle, and footer tagline. Footer social icons
  come from the Social Media settings (blank ones are hidden automatically).

---

## 2. Add environment variables (`backend/.env`)

All are optional — add them when you're ready. See `backend/.env.example`.

### Razorpay (online payments: UPI / cards / netbanking)
```
RAZORPAY_KEY_ID=rzp_test_xxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxx
```
- Get them from Razorpay Dashboard → Settings → API Keys.
- Start with **test** keys (`rzp_test_…`). Until these are set, the checkout
  shows the online options but returns a friendly "not enabled yet" message and
  COD keeps working.
- No new pip package is needed — the integration uses the Razorpay REST API and
  verifies the payment signature with HMAC.

### Shiprocket (delivery)
```
SHIPROCKET_EMAIL=your-api-user@example.com
SHIPROCKET_PASSWORD=your-api-user-password
SHIPROCKET_PICKUP_LOCATION=Primary
```
- Create an **API user** in Shiprocket → Settings → API → Configure.
- `SHIPROCKET_PICKUP_LOCATION` must match a pickup address nickname exactly
  (Shiprocket → Settings → Company → Pickup Addresses).

---

## 3. How each feature works

### Payments
- COD: order is placed immediately (`POST /api/orders`).
- Online: checkout calls `POST /api/payments/create-order` → opens Razorpay →
  on success `POST /api/payments/verify` checks the signature and *then* creates
  the order (marked paid). An order is never created for an unpaid online
  attempt.

### Forgot password
- `/forgot-password` → enter email → `POST /api/auth/forgot-password`.
- In development (`FLASK_ENV=development`) the reset link is returned in the
  response and logged to the server console (no email provider wired yet — see
  the `TODO` in `backend/app/routes/auth.py` to plug in SMTP/SendGrid/SES).
- `/reset-password?token=…` → set a new password.

### Shiprocket (admin)
- Open an order in the admin panel → **Delivery** card → **Ship via Shiprocket**.
  This creates the Shiprocket order, assigns an AWB/courier, marks the order
  *shipped*, and records a tracking event.
- After that, **Sync tracking** pulls the latest courier scans into the order's
  timeline, which the customer sees on `/track-order`.

---

## 4. Weights & dimensions (Shiprocket)

Products don't yet store weight/dimensions, so shipments use defaults
(0.5 kg, 20×15×5 cm) in `backend/app/services/shiprocket.py`. Adjust there, or
add weight/dimension fields to the product/variant model later for accuracy.
