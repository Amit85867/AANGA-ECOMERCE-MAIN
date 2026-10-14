#!/usr/bin/env bash
#
# Once the Razorpay and Shiprocket TEST keys are in backend/.env, run the six
# checks that only the providers' sandboxes can confirm:
#
#   1. test checkout          4. signed webhook
#   2. payment verification   5. reconcile-payments
#   3. refund on cancel       6. live pincode check
#
#   scripts/verify_integrations.sh
#
# Prints PASS or FAIL for each step and exits non-zero if any failed. Refuses
# to run with live keys (step 3 refunds an order). Never prints a key.
#
# Before running: place ONE order in the storefront with "Pay online" (test
# card 4111 1111 1111 1111, any future expiry, any CVV). Steps 2 and 3 use it.
# The full procedure is in docs/GO_LIVE.md.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

if [ -x venv/Scripts/python ]; then PY=venv/Scripts/python
elif [ -x venv/bin/python ]; then PY=venv/bin/python
else PY=python; fi

echo "== Settings and one read-only call to each service =="
"$PY" -m flask --app run check-integrations || {
  echo
  echo "Fix what is listed above first, then run this again."
  exit 1
}

echo
echo "== The six steps =="
"$PY" -m flask --app run verify-integrations
