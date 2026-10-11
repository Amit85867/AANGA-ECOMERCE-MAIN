#!/usr/bin/env bash
#
# Run the end-to-end suite against the production-like copy of the store.
# This is the regression check to run before every deploy.
#
#   scripts/e2e.sh                      everything, at 390 / 768 / 1280 / 1920 px
#   scripts/e2e.sh --fresh              rebuild the copy from nothing first (slow, exact)
#   scripts/e2e.sh --project=w390       one width
#   scripts/e2e.sh -g "CU-CHECKOUT"     tests whose id matches
#
# Anything after the options above is passed to Playwright.
# Report: e2e/playwright-report/index.html. Results for the QA matrix:
# e2e/test-results/results.json.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="http://127.0.0.1:${PRODLOCAL_PORT:-8080}"

if [ "${1:-}" = "--fresh" ]; then
  shift
  bash "$ROOT/scripts/prod_local.sh"
elif ! curl -fsS -o /dev/null --max-time 5 "$BASE/api/health" 2>/dev/null; then
  echo "The production-like copy is not running: starting it (scripts/prod_local.sh)."
  bash "$ROOT/scripts/prod_local.sh"
fi

cd "$ROOT/e2e"
[ -d node_modules ] || npm ci
npx playwright install chromium > /dev/null
E2E_BASE_URL="http://localhost:${PRODLOCAL_PORT:-8080}" npx playwright test "$@"
