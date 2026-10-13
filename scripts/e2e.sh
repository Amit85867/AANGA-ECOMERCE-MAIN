#!/usr/bin/env bash
#
# Run the end-to-end suite against the local development stack: the storefront
# on :5173, the API on :5000, and the Neon **dev** branch as the database.
# This is the regression check to run before every deploy.
#
#   scripts/e2e.sh                      everything, at 390 / 768 / 1280 / 1920 px
#   scripts/e2e.sh --fresh              reset the dev branch and reseed first
#   scripts/e2e.sh --project=w390       one width
#   scripts/e2e.sh -g "CU-CHECKOUT"     tests whose id matches
#
# Anything after the options above is passed to Playwright.
# Report: e2e/playwright-report/index.html. Results for the QA matrix:
# e2e/test-results/results.json.
#
# The API is started with RATELIMIT_ENABLED=false: the suite registers dozens of
# accounts in a few minutes and would otherwise spend the run testing the
# limiter. No test asserts limiting behaviour, so nothing is lost. The switch is
# refused in production by _validate_config.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
STATE="$ROOT/.e2e"
BASE="http://127.0.0.1:5173"
API="http://127.0.0.1:5000"

say() { printf '\033[36m==> %s\033[0m\n' "$1"; }
fail() { printf '\033[31mERROR: %s\033[0m\n' "$1" >&2; exit 1; }
up() { curl -fsS -o /dev/null --max-time 5 "$1" 2>/dev/null; }

if [ -x "$BACKEND/venv/Scripts/python.exe" ]; then PY="$BACKEND/venv/Scripts/python.exe"
elif [ -x "$BACKEND/venv/bin/python" ]; then PY="$BACKEND/venv/bin/python"
else PY="$(command -v python3 || command -v python)"; fi

mkdir -p "$STATE"

if [ "${1:-}" = "--fresh" ]; then
  shift
  command -v neonctl >/dev/null 2>&1 || fail "--fresh needs neonctl (npm install -g neonctl)"
  say "Resetting the Neon dev branch from its parent"
  neonctl branches reset "${NEON_DEV_BRANCH:-dev}" \
    --project-id "${NEON_PROJECT_ID:-dry-base-24522506}" \
    --org-id "${NEON_ORG_ID:-org-long-mud-04364433}" --parent > /dev/null \
    || fail "Reset failed. Is neonctl authenticated? (neonctl auth)"
  rm -f "$STATE/demo_logins.json"
fi

# The rate limiter has to be off before the API starts, so if something is
# already running on :5000 we cannot know how it was started.
if up "$API/api/ping"; then
  say "An API is already running on :5000 — using it"
  echo "    If the run trips rate limits, stop it (scripts/dev.sh --stop) and re-run."
else
  say "Starting the stack (scripts/dev.sh), rate limiting off"
  RATELIMIT_ENABLED=false bash "$ROOT/scripts/dev.sh" >/dev/null \
    || fail "The stack did not start. See .dev/api.log and .dev/storefront.log"
fi

up "$BASE/" || fail "The storefront is not answering on :5173. See .dev/storefront.log"

if [ ! -f "$STATE/demo_logins.json" ]; then
  say "Seeding the demo content and its logins (first run, or --fresh)"
  (cd "$BACKEND" && "$PY" db/demo/seed_demo.py --api "$API" \
      --secrets-out "$STATE/demo_logins.json" --no-manifest) \
    || fail "Seeding failed. The suite needs the demo manager, staff and shopper."
fi

cd "$ROOT/e2e"
[ -d node_modules ] || npm ci
npx playwright install chromium > /dev/null
E2E_BASE_URL="$BASE" npx playwright test "$@"
