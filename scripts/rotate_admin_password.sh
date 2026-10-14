#!/usr/bin/env bash
#
# Change the master admin's password on a Neon branch.
#
#   scripts/rotate_admin_password.sh production
#   scripts/rotate_admin_password.sh dev
#
# You type the new password at the prompt (hidden, asked twice). It is never
# passed as an argument, so it does not reach your shell history, and the
# connection string is fetched into this process only -- never into a file.
#
# ADMIN_PASSWORD is deliberately cleared before running: the CLI command uses
# it when set, and backend/.env defines it, so without this the "rotation"
# would silently re-apply the OLD password and look like it worked.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"

PROJECT="${NEON_PROJECT_ID:-dry-base-24522506}"
ORG="${NEON_ORG_ID:-org-long-mud-04364433}"
BRANCH="${1:-}"

case "$BRANCH" in
  production|dev|test) ;;
  *) echo "Usage: $0 <production|dev|test>" >&2; exit 2 ;;
esac

if [ -x "$BACKEND/venv/Scripts/python.exe" ]; then PY="$BACKEND/venv/Scripts/python.exe"
elif [ -x "$BACKEND/venv/bin/python" ]; then PY="$BACKEND/venv/bin/python"
else PY="$(command -v python3 || command -v python)"; fi

command -v neonctl >/dev/null 2>&1 || { echo "neonctl is not installed." >&2; exit 2; }

# Direct string: this is a write to a single row, and the pooled endpoint adds
# nothing here.
url="$(neonctl connection-string "$BRANCH" --project-id "$PROJECT" --org-id "$ORG" \
        --role-name aanga_owner --database-name aanga 2>/dev/null)"
[ -n "$url" ] || { echo "Could not get the connection string for '$BRANCH'." >&2; exit 1; }

email="${ADMIN_EMAIL_OVERRIDE:-$(grep -E '^ADMIN_EMAIL=' "$BACKEND/.env" | head -1 | cut -d= -f2- | tr -d '\r')}"
[ -n "$email" ] || { echo "No ADMIN_EMAIL in backend/.env; pass ADMIN_EMAIL_OVERRIDE." >&2; exit 1; }

printf '\033[36m==> Branch: %s   Admin: %s\033[0m\n' "$BRANCH" "$email"
echo "    You will be asked for the new password twice. Minimum 12 characters."
echo

cd "$BACKEND"
ADMIN_PASSWORD= \
DATABASE_URL="$url" \
FLASK_ENV=development \
  "$PY" -m flask --app run set-admin-password --email "$email"
