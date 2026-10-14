"""``flask check-integrations``: are the outside services set up, and do they answer?

For each service it says one of:

* **OK**             — configured, and (unless ``--offline``) one read-only call succeeded
* **NOT CONFIGURED** — nothing is set; the store runs without it
* **PROBLEM**        — something is set but wrong, with what to do about it

Only read-only calls are made: listing one payment, signing in to the courier,
reading the storage bucket's settings. Nothing is created or charged, and no
key or password is ever printed — only whether each one is present.
"""
import os

from app.services import health

# What each variable is, and where its value comes from.
VARIABLES = {
    "razorpay": [
        ("RAZORPAY_KEY_ID", "Razorpay Dashboard -> Account & Settings -> API Keys (starts with rzp_test_ or rzp_live_)"),
        ("RAZORPAY_KEY_SECRET", "shown once, next to the Key ID, when the key is generated"),
        ("RAZORPAY_WEBHOOK_SECRET", "the secret you type when adding the webhook under Account & Settings -> Webhooks"),
    ],
    "shiprocket": [
        ("SHIPROCKET_EMAIL", "Shiprocket -> Settings -> API -> the API user's email (not your login email)"),
        ("SHIPROCKET_PASSWORD", "the password set for that API user"),
        ("SHIPROCKET_PICKUP_PINCODE", "the 6-digit PIN code of your pickup address"),
        ("SHIPROCKET_PICKUP_LOCATION", "the pickup location's nickname in Shiprocket -> Settings -> Pickup Addresses"),
    ],
    "storage": [
        ("S3_ENDPOINT_URL", "Neon -> the branch's object-storage endpoint (neon api /projects/<id>/branches/<id>/storage)"),
        ("S3_BUCKET", "the bucket name, e.g. product-images"),
        ("S3_ACCESS_KEY_ID", "Neon -> credentials: the token id of a storage:read + storage:write credential"),
        ("S3_SECRET_ACCESS_KEY", "Neon -> credentials reveal <tokenId> -> s3_secret_access_key"),
    ],
    "email": [("RESEND_API_KEY", "Resend -> API Keys")],
    "google_login": [("GOOGLE_CLIENT_ID", "Google Cloud Console -> Credentials -> OAuth client ID")],
    "sentry": [("SENTRY_DSN", "Sentry -> Project Settings -> Client Keys")],
}
LABELS = {
    "database": "Database", "schema": "Database migrations", "rate_limit_store": "Redis",
    "razorpay": "Razorpay (payments)", "shiprocket": "Shiprocket (delivery)", "storage": "Object storage (images)",
    "email": "Resend (email)", "google_login": "Google sign-in", "sentry": "Sentry (error reports)",
}
FIXES = {
    "razorpay": {
        "Key ID and key secret must both be set.": "Set both RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET, from the same key pair.",
        "Webhook secret is missing": "Add the webhook in the Razorpay Dashboard (URL: https://<your-api-host>/api/payments/webhook, events: payment.captured, payment.failed, refund.processed), then set RAZORPAY_WEBHOOK_SECRET to the secret you typed there.",
        "rejected the credentials": "The Key ID and secret do not match, or the key was regenerated. Generate a new key pair and set both values.",
        "Could not reach": "No answer from api.razorpay.com. Check the server's outbound internet access and try again.",
    },
    "shiprocket": {
        "API email and password must both be set.": "Set both SHIPROCKET_EMAIL and SHIPROCKET_PASSWORD (the API user, created under Settings -> API).",
        "Pickup PIN code is missing": "Set SHIPROCKET_PICKUP_PINCODE to the PIN code of your pickup address.",
    },
    "storage": {
        "Incomplete": "Set every S3_* value. The endpoint embeds the branch id, so dev, test and production each have their own.",
        "Could not write": "The credential needs storage:write, and the bucket must exist on THIS branch (buckets are per-branch; a branch made before the bucket does not inherit it).",
        "not publicly readable": "Recreate the bucket with --access-level public_read: neonctl buckets create product-images --branch <branch> --access-level public_read",
    },
}


def _present(name):
    return bool((os.environ.get(name) or "").strip())


def _fix(key, detail):
    for fragment, advice in FIXES.get(key, {}).items():
        if fragment in detail:
            return advice
    if key == "shiprocket":
        return "Shiprocket did not accept the sign-in. Check the API user's email and password (Settings -> API), and that the API user is active."
    return None


def run(probe=True):
    """``(lines, exit_code)``. Exit 1 when anything is a PROBLEM."""
    lines, problems = [], 0
    for check in health.run_all(probe=probe):
        key, status, detail = check["key"], check["status"], check["detail"]
        word = {"ok": "OK", "not_configured": "NOT CONFIGURED", "error": "PROBLEM"}[status]
        lines.append(f"[{word}] {LABELS.get(key, check['label'])}: {detail}")

        for name, where in VARIABLES.get(key, []):
            if key == "shiprocket" and name == "SHIPROCKET_PICKUP_LOCATION" and not _present(name):
                lines.append(f"    {name}: not set (\"Primary\" will be used)")
                continue
            lines.append(f"    {name}: {'set' if _present(name) else 'NOT SET  <- ' + where}")

        if key == "razorpay" and _present("RAZORPAY_KEY_ID"):
            key_id = os.environ["RAZORPAY_KEY_ID"].strip()
            if key_id.startswith("rzp_test_"):
                lines.append("    mode: TEST - no real money moves. Switch to live keys only after KYC (docs/GO_LIVE.md).")
            elif key_id.startswith("rzp_live_"):
                lines.append("    mode: LIVE - real payments. The webhook must be registered in LIVE mode too; it is separate from the test one.")
            else:
                status = "error"
                lines.append("    mode: UNKNOWN - a Razorpay Key ID starts with rzp_test_ or rzp_live_. Check the value was pasted whole.")

        if status == "error":
            problems += 1
            advice = _fix(key, detail)
            if advice:
                lines.append(f"    fix: {advice}")
        elif status == "not_configured" and key in ("razorpay", "shiprocket"):
            consequence = (
                "Checkout offers cash on delivery only." if key == "razorpay"
                else "The delivery-date check is hidden and couriers are booked by hand."
            )
            lines.append(f"    effect: {consequence} Add the variables above and restart to switch it on.")

    lines.append("")
    lines.append(
        f"{problems} problem(s) found." if problems
        else "No problems found." + ("" if probe else " (Offline: nothing was contacted.)")
    )
    return lines, (1 if problems else 0)
