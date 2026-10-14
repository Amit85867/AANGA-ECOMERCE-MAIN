#!/usr/bin/env bash
#
# Reset the Neon "test" branch from its parent, then run the test suite.
#
#   scripts/reset_test_branch.sh              reset, then the full suite
#   scripts/reset_test_branch.sh --reset-only  reset and stop
#   scripts/reset_test_branch.sh -k payments   reset, then pytest -k payments
#
# Why reset at all: each test TRUNCATEs every table, so the suite is already
# isolated. The reset puts the *schema* back to whatever production has, which
# is what catches "the tests pass against a schema nobody will deploy".
#
# Needs neonctl and an authenticated session (neonctl auth). It never prints a
# connection string.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"

PROJECT_ID="${NEON_PROJECT_ID:-dry-base-24522506}"
ORG_ID="${NEON_ORG_ID:-org-long-mud-04364433}"
BRANCH="${NEON_TEST_BRANCH:-test}"

say() { printf '\033[36m==> %s\033[0m\n' "$1"; }
fail() { printf '\033[31mERROR: %s\033[0m\n' "$1" >&2; exit 1; }

command -v neonctl >/dev/null 2>&1 || fail "neonctl is not installed: npm install -g neonctl"

if [ "$BRANCH" = "production" ] || [ "$BRANCH" = "dev" ]; then
  fail "Refusing to reset the '$BRANCH' branch. This script is for 'test' only."
fi

say "Resetting the Neon '$BRANCH' branch from its parent"
neonctl branches reset "$BRANCH" \
  --project-id "$PROJECT_ID" --org-id "$ORG_ID" --parent > /dev/null \
  || fail "Reset failed. Is neonctl authenticated? (neonctl auth)"
say "Reset done"

[ "${1:-}" = "--reset-only" ] && exit 0

if [ -x "$BACKEND/venv/Scripts/python.exe" ]; then PY="$BACKEND/venv/Scripts/python.exe"
elif [ -x "$BACKEND/venv/bin/python" ]; then PY="$BACKEND/venv/bin/python"
else PY="$(command -v python3 || command -v python)"; fi

say "Running the test suite"
cd "$BACKEND"
exec "$PY" -m pytest "$@"
