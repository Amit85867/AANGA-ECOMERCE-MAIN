#!/usr/bin/env bash
#
# How much time does the static site's /api rewrite add?
#
#   scripts/check_rewrite_latency.sh https://www.example.com https://aanga-api.onrender.com
#
# Calls /api/health through the storefront (the rewrite) and on the backend
# directly, several times each, and compares the medians. Every API call a
# shopper makes takes the rewrite path, so its overhead is paid on every click.
#
# Exit code 1 when the rewrite adds more than the threshold (default 150 ms),
# so this can gate a deploy. If it does, layout (c) — Flask serving the built
# frontend from the one service — removes the hop; see docs/DEPLOYMENT.md.
#
set -euo pipefail

SITE="${1:?usage: $0 <storefront-url> <backend-url> [samples] [threshold-ms]}"
BACKEND="${2:?usage: $0 <storefront-url> <backend-url> [samples] [threshold-ms]}"
SAMPLES="${3:-15}"
THRESHOLD_MS="${4:-150}"

median_ms() {
  local url="$1" i code time
  local -a times=()
  # One unmeasured request first: it pays for DNS, TLS and any cold start,
  # none of which is the thing being compared.
  curl -s -o /dev/null --max-time 30 "$url" || true
  for ((i = 0; i < SAMPLES; i++)); do
    read -r code time < <(curl -s -o /dev/null --max-time 30 -w '%{http_code} %{time_total}\n' "$url")
    if [ "$code" != "200" ]; then
      echo "  $url answered $code" >&2
      return 1
    fi
    times+=("$time")
  done
  printf '%s\n' "${times[@]}" | sort -n | awk '{ a[NR] = $1 } END { printf "%.0f", a[int((NR + 1) / 2)] * 1000 }'
}

echo "Sampling $SAMPLES requests each..."
via_rewrite="$(median_ms "${SITE%/}/api/health")"
direct="$(median_ms "${BACKEND%/}/api/health")"
added=$((via_rewrite - direct))

echo "  through the rewrite : ${via_rewrite} ms (median)"
echo "  backend directly    : ${direct} ms (median)"
echo "  added by the rewrite: ${added} ms"

if [ "$added" -gt "$THRESHOLD_MS" ]; then
  echo "FLAG: the rewrite adds more than ${THRESHOLD_MS} ms. Consider layout (c)."
  exit 1
fi
echo "OK: within ${THRESHOLD_MS} ms."
