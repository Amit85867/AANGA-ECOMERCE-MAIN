#!/usr/bin/env bash
#
# Start the whole AANGA stack for local development (macOS / Linux / Git Bash).
# Windows PowerShell users: scripts\dev.ps1 does the same.
#
#   scripts/dev.sh          database -> migrations -> API -> storefront
#   scripts/dev.sh --stop   stop the API and storefront started here
#
# Each step is checked before the next one starts. Logs: .dev/api.log and
# .dev/storefront.log.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
RUN="$ROOT/.dev"
mkdir -p "$RUN"

if [ -x "$BACKEND/venv/Scripts/python.exe" ]; then PY="$BACKEND/venv/Scripts/python.exe"; else PY="$BACKEND/venv/bin/python"; fi

say() { printf '\033[36m==> %s\033[0m\n' "$1"; }
fail() { printf '\033[31mERROR: %s\033[0m\n' "$1" >&2; exit 1; }
up() { curl -fsS -o /dev/null --max-time 3 "$1" 2>/dev/null; }
wait_for() { for _ in $(seq 1 "$2"); do up "$1" && return 0; sleep 1; done; return 1; }

stop_pid() {
  [ -f "$1" ] || return 0
  pid="$(cat "$1")"
  # the whole process group: the dev servers start children of their own
  kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null || true
  rm -f "$1"
}

if [ "${1:-}" = "--stop" ]; then
  say "Stopping the API and the storefront"
  stop_pid "$RUN/api.pid"; stop_pid "$RUN/storefront.pid"
  echo "Stopped. The Neon database is unaffected."
  exit 0
fi

[ -f "$BACKEND/.env" ] || fail "backend/.env is missing. Copy backend/.env.example to backend/.env and fill it in."
if [ ! -x "$PY" ]; then
  say "Creating the Python virtual environment (first run only)"
  python3 -m venv "$BACKEND/venv"
  PY="$BACKEND/venv/bin/python"
  "$PY" -m pip install --quiet -r "$BACKEND/requirements-dev.txt"
fi
[ -d "$FRONTEND/node_modules" ] || { say "Installing the storefront packages (first run only)"; (cd "$FRONTEND" && npm ci); }

# The database is Neon and is always there; nothing to start. The first query
# after five quiet minutes wakes the compute and takes about a second.
say "Checking the Neon dev branch is reachable"
(cd "$BACKEND" && "$PY" -c "
import os, sys
from dotenv import load_dotenv
import psycopg2
load_dotenv('.env')
url = os.environ.get('DATABASE_URL')
if not url:
    sys.exit('DATABASE_URL is not set in backend/.env (see docs/DATABASE.md).')
try:
    psycopg2.connect(url, connect_timeout=30).close()
except Exception as exc:
    sys.exit(f'Cannot reach the database: [{type(exc).__name__}] see docs/DATABASE.md')
") || fail "The Neon dev branch is not reachable (message above)."

say "Applying database migrations"
(cd "$BACKEND" && "$PY" -m flask --app run apply-migrations) || fail "Migrations failed (message above). Nothing else was started."

if up http://127.0.0.1:5000/api/health; then
  say "The API is already running on port 5000: using it"
else
  say "Starting the API (log: .dev/api.log)"
  (cd "$BACKEND" && setsid "$PY" run.py > "$RUN/api.log" 2>&1 & echo $! > "$RUN/api.pid") 2>/dev/null \
    || (cd "$BACKEND" && "$PY" run.py > "$RUN/api.log" 2>&1 & echo $! > "$RUN/api.pid")
  wait_for http://127.0.0.1:5000/api/health 60 || fail "The API did not start. See .dev/api.log"
fi
curl -fsS --max-time 20 "http://127.0.0.1:5000/api/products?per_page=1" > /dev/null \
  || fail "The API is running but /api/products failed. See .dev/api.log"

if up http://localhost:5173/; then
  say "The storefront is already running on port 5173: using it"
else
  say "Starting the storefront (log: .dev/storefront.log)"
  (cd "$FRONTEND" && setsid npm run dev > "$RUN/storefront.log" 2>&1 & echo $! > "$RUN/storefront.pid") 2>/dev/null \
    || (cd "$FRONTEND" && npm run dev > "$RUN/storefront.log" 2>&1 & echo $! > "$RUN/storefront.pid")
  wait_for http://localhost:5173/ 60 || fail "The storefront did not start. See .dev/storefront.log"
fi

printf '\n\033[32mReady.\033[0m\n  Storefront  http://localhost:5173\n  Admin       http://localhost:5173/admin\n  API         http://127.0.0.1:5000/api/health\n  Stop        scripts/dev.sh --stop\n'
