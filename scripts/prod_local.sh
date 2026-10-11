#!/usr/bin/env bash
#
# A production-like copy of the store on this machine: what Render will run,
# built the way Render will build it. Used for the pre-launch audit and by the
# end-to-end suite (scripts/e2e.sh).
#
#   scripts/prod_local.sh              rebuild everything from nothing, with demo content
#   scripts/prod_local.sh --no-demo    the same, with an empty catalogue
#   scripts/prod_local.sh --keep       rebuild the storefront and the containers, keep the data
#   scripts/prod_local.sh throwaway-check   back up, restore into a second database, remove the demo
#                                           content there, check it, delete the copy (main data untouched)
#   scripts/prod_local.sh down         stop and delete it (containers and data)
#   scripts/prod_local.sh status
#   scripts/prod_local.sh reset-limits forget rate-limit counters (before a test run)
#   scripts/prod_local.sh flask ...    run a flask command inside the API container
#   scripts/prod_local.sh db-url       print the database address for psql / scripts
#
# What "rebuild" does, in order:
#   1. frontend:  npm ci && npm run build            (render.yaml: buildCommand)
#   2. database:  a new, EMPTY postgres:17
#   3. schema:    scripts/render_bootstrap_db.sh     (the only thing that touches the schema)
#   4. cache:     redis
#   5. api:       backend/Dockerfile, FLASK_ENV=production, gunicorn
#   6. web:       frontend/dist with the /api rewrite, on http://localhost:8080
#   7. demo:      db/seed_catalogue.py then db/demo/seed_demo.py, through the admin API
#
# Secrets (random, made on first run) live in .prodlocal/env, which git ignores.
# They are never printed. The Owner login for this copy is in that file.
#
# Needs: Docker, Node 20+, and Python with backend/requirements.txt (for step 7).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE="$ROOT/.prodlocal"
ENV_FILE="$STATE/env"
COMPOSE_FILE="$ROOT/scripts/prod_local/docker-compose.yml"
export PRODLOCAL_PORT="${PRODLOCAL_PORT:-8080}"
export PRODLOCAL_DB_PORT="${PRODLOCAL_DB_PORT:-55440}"
BASE="http://127.0.0.1:$PRODLOCAL_PORT"

say() { printf '\033[36m==> %s\033[0m\n' "$1"; }
fail() { printf '\033[31mERROR: %s\033[0m\n' "$1" >&2; exit 1; }
value() { grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2-; }
compose() { POSTGRES_PASSWORD="$(value POSTGRES_PASSWORD)" docker compose -f "$COMPOSE_FILE" "$@"; }

if [ -x "$ROOT/backend/venv/Scripts/python.exe" ]; then PY="$ROOT/backend/venv/Scripts/python.exe"
elif [ -x "$ROOT/backend/venv/bin/python" ]; then PY="$ROOT/backend/venv/bin/python"
else PY="$(command -v python3 || command -v python)"; fi

make_env() {
  mkdir -p "$STATE"
  [ -f "$ENV_FILE" ] && return 0
  say "Creating .prodlocal/env with new random secrets"
  rand() { "$PY" -c "import secrets; print(secrets.token_urlsafe($1))"; }
  umask 077
  cat > "$ENV_FILE" <<EOF
# Made by scripts/prod_local.sh for the local production-like copy only.
# Not used by any real deployment. Do not commit.
POSTGRES_PASSWORD=$(rand 24)
SECRET_KEY=$(rand 64)
JWT_SECRET_KEY=$(rand 64)
ADMIN_EMAIL=owner@prodlocal.test
ADMIN_PASSWORD=$(rand 18)
EMAIL_ASYNC=false
# Razorpay, Shiprocket, Resend, Google and Sentry are deliberately absent:
# this copy runs exactly as the store will before those keys are added.
EOF
}

db_url() { echo "postgresql://aanga:$(value POSTGRES_PASSWORD)@127.0.0.1:$PRODLOCAL_DB_PORT/aanga"; }

wait_http() {
  for _ in $(seq 1 "$2"); do
    curl -fsS -o /dev/null --max-time 3 "$1" 2>/dev/null && return 0
    sleep 1
  done
  return 1
}

cmd="${1:-up}"
case "$cmd" in
  down)
    [ -f "$ENV_FILE" ] || { echo "Nothing to stop."; exit 0; }
    say "Stopping and deleting the production-like copy"
    compose down -v --remove-orphans
    exit 0 ;;
  status)
    [ -f "$ENV_FILE" ] || fail "Not created yet. Run scripts/prod_local.sh"
    compose ps
    curl -fsS --max-time 5 "$BASE/api/health" && echo
    exit 0 ;;
  reset-limits)
    compose exec -T redis redis-cli FLUSHALL > /dev/null && echo "Rate-limit counters and cache cleared."
    exit 0 ;;
  flask)
    shift
    compose exec -T api flask --app run "$@"
    exit $? ;;
  db-url)
    [ -f "$ENV_FILE" ] || fail "Not created yet. Run scripts/prod_local.sh"
    db_url
    exit 0 ;;
  throwaway-check)
    # Destructive things are proved on a copy, never on the main database:
    # back the database up, restore the backup into a second database, remove
    # the demo content THERE, check the result, and delete the copy.
    [ -f "$ENV_FILE" ] || fail "Not created yet. Run scripts/prod_local.sh"
    psql_in() { compose exec -T db psql -v ON_ERROR_STOP=1 -U aanga -d "$1" -At "${@:2}"; }
    counts() {
      psql_in "$1" -c "SELECT table_name || '=' || (xpath('/row/c/text()', query_to_xml(format('select count(*) as c from %I.%I', table_schema, table_name), false, true, '')))[1]::text FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY 1"
    }
    demo_rows() {   # "<table>=<demo rows>/<other rows>" for every table that can hold demo content
      psql_in "$1" -c "SELECT table_name || '=' || (xpath('/row/c/text()', query_to_xml(format('select count(*) filter (where is_demo) || ''/'' || count(*) filter (where not is_demo) as c from %I', table_name), false, true, '')))[1]::text FROM information_schema.columns WHERE table_schema = 'public' AND column_name = 'is_demo' ORDER BY 1"
    }
    uploads() { compose exec -T api sh -c 'find /app/static/uploads -type f | wc -l' | tr -d '[:space:]'; }

    say "1/6 Backing up the main database (pg_dump, custom format)"
    compose exec -T db pg_dump -U aanga -d aanga --format=custom --file=/tmp/throwaway.dump
    main_before="$(counts aanga)"; main_demo_before="$(demo_rows aanga)"; files_before="$(uploads)"

    say "2/6 Restoring the backup into a second, throwaway database"
    psql_in postgres -c "DROP DATABASE IF EXISTS aanga_throwaway" > /dev/null
    psql_in postgres -c "CREATE DATABASE aanga_throwaway" > /dev/null
    compose exec -T db pg_restore --no-owner --exit-on-error -U aanga -d aanga_throwaway /tmp/throwaway.dump
    copy="$(counts aanga_throwaway)"
    [ "$copy" = "$main_before" ] || { diff <(echo "$main_before") <(echo "$copy") || true; fail "The restored copy does not have the same rows as the original."; }
    echo "    PASS  backup and restore: $(echo "$copy" | wc -l | tr -d ' ') tables, every row count identical"

    say "3/6 The restored copy passes the schema check"
    api_env="$STATE/throwaway.env"
    docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' aanga-prodlocal-api-1 | grep -vE '^(DATABASE_URL|PATH|HOME|HOSTNAME)=' > "$api_env"
    image="$(docker inspect -f '{{.Config.Image}}' aanga-prodlocal-api-1)"
    network="$(docker inspect -f '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}' aanga-prodlocal-api-1)"
    # No uploads volume is mounted: whatever the removal deletes from disk, it
    # cannot be the main copy's pictures.
    on_copy() {
      MSYS_NO_PATHCONV=1 docker run --rm --network "$network" --env-file "$api_env" \
        -e "DATABASE_URL=postgresql://aanga:$(value POSTGRES_PASSWORD)@db:5432/aanga_throwaway" "$image" flask --app run "$@"
    }
    trap 'rm -f "$api_env"' EXIT
    on_copy check-schema | tail -1

    say "4/6 Removing the demo content from the copy"
    demo_before="$(demo_rows aanga_throwaway)"
    on_copy remove-demo-content --yes | tail -4
    demo_after="$(demo_rows aanga_throwaway)"
    echo "$demo_after" | grep -qvE '=0/' && { echo "$demo_after"; fail "Demo rows are left in the copy."; }
    kept_before="$(echo "$demo_before" | sed -E 's#=[0-9]+/#=#')"; kept_after="$(echo "$demo_after" | sed -E 's#=[0-9]+/#=#')"
    [ "$kept_before" = "$kept_after" ] || { diff <(echo "$kept_before") <(echo "$kept_after") || true; fail "Removing the demo content also removed rows that were not demo content."; }
    removed="$(echo "$demo_before" | sed -E 's#.*=([0-9]+)/.*#\1#' | awk '{ total += $1 } END { print total + 0 }')"
    echo "    PASS  $removed demo rows removed from $(echo "$demo_before" | wc -l | tr -d ' ') tables; every row that was not demo content is still there"
    owners="$(psql_in aanga_throwaway -c "SELECT count(*) FROM admins WHERE role = 'master' AND is_active")"
    [ "$owners" -ge 1 ] || fail "No owner account is left in the copy."
    orphans="$(psql_in aanga_throwaway -c "SELECT (SELECT count(*) FROM order_items oi LEFT JOIN orders o ON o.id = oi.order_id WHERE o.id IS NULL) + (SELECT count(*) FROM product_variants v LEFT JOIN products p ON p.id = v.product_id WHERE p.id IS NULL) + (SELECT count(*) FROM cart_items ci LEFT JOIN product_variants v ON v.id = ci.variant_id WHERE v.id IS NULL)")"
    [ "$orphans" = "0" ] || fail "$orphans orphaned rows are left in the copy."
    echo "    PASS  the owner account is still there; no orphaned order lines, variants or bag lines"

    say "5/6 The copy still passes the schema check after the removal"
    on_copy check-schema | tail -1

    say "6/6 The main database and its pictures were not touched"
    [ "$(demo_rows aanga)" = "$main_demo_before" ] || fail "The main database changed."
    [ "$(uploads)" = "$files_before" ] || fail "Files in the main copy's uploads changed."
    echo "    PASS  main database: same demo content as before; uploads: $files_before files, unchanged"
    psql_in postgres -c "DROP DATABASE aanga_throwaway" > /dev/null
    compose exec -T db rm -f /tmp/throwaway.dump
    echo "Throwaway copy deleted."
    exit 0 ;;
  up|--no-demo|--keep) ;;
  *) fail "Unknown command: $cmd (see the top of this file)" ;;
esac

command -v docker > /dev/null || fail "Docker is not installed or not on PATH."
docker info > /dev/null 2>&1 || fail "Docker is not running."
make_env

if [ "$cmd" = "--keep" ]; then
  say "Rebuilding the storefront and the containers, keeping the data"
  (cd "$ROOT/frontend" && { [ -d node_modules ] || npm ci; } && npm run build > "$STATE/frontend-build.log" 2>&1)     || fail "The storefront build failed. See .prodlocal/frontend-build.log"
  compose up -d --build
  compose restart web > /dev/null 2>&1        # picks up a changed static_server.mjs
  wait_http "$BASE/api/health" 120 || fail "The store did not come up. See: docker compose -f scripts/prod_local/docker-compose.yml logs api"
  echo "Ready: http://localhost:$PRODLOCAL_PORT"
  exit 0
fi

say "1/7 Building the storefront (npm ci && npm run build)"
(cd "$ROOT/frontend" && { [ -d node_modules ] || npm ci; } && npm run build > "$STATE/frontend-build.log" 2>&1) \
  || fail "The storefront build failed. See .prodlocal/frontend-build.log"

say "2/7 Starting a new, empty Postgres 17"
compose down -v --remove-orphans > /dev/null 2>&1 || true
compose up -d db redis
for _ in $(seq 1 60); do
  [ "$(compose ps db --format '{{.Health}}' 2>/dev/null)" = "healthy" ] && break
  sleep 1
done
[ "$(compose ps db --format '{{.Health}}')" = "healthy" ] || fail "Postgres did not become healthy."

say "3/7 Building the schema with scripts/render_bootstrap_db.sh"
DATABASE_URL="$(db_url)" bash "$ROOT/scripts/render_bootstrap_db.sh" > "$STATE/bootstrap.log" 2>&1 \
  || { tail -20 "$STATE/bootstrap.log"; fail "The bootstrap script failed (full output: .prodlocal/bootstrap.log)"; }
grep -E "^  (ok|MISSING|WRONG|FOUND)|tables:|triggers:" "$STATE/bootstrap.log" | sed 's/^/    /' | tail -30

say "4-6/7 Building and starting the API image (production settings) and the web tier"
compose up -d --build api web > "$STATE/compose-up.log" 2>&1 \
  || { tail -30 "$STATE/compose-up.log"; compose logs --tail 40 api; fail "The API or web tier did not start."; }
wait_http "$BASE/api/health" 120 || { compose logs --tail 40 api; fail "The store did not answer on $BASE"; }
compose exec -T api flask --app run check-schema | sed 's/^/    schema: /'

if [ "$cmd" != "--no-demo" ]; then
  say "7/7 Loading the demo content through the admin API"
  export ADMIN_EMAIL="$(value ADMIN_EMAIL)" ADMIN_PASSWORD="$(value ADMIN_PASSWORD)"
  export DEMO_OWNER_EMAIL="$ADMIN_EMAIL" DEMO_OWNER_PASSWORD="$ADMIN_PASSWORD"
  "$PY" "$ROOT/backend/db/seed_catalogue.py" --api "$BASE" > "$STATE/seed-catalogue.log" 2>&1 \
    || { tail -15 "$STATE/seed-catalogue.log"; fail "seed_catalogue.py failed (.prodlocal/seed-catalogue.log)"; }
  "$PY" "$ROOT/backend/db/demo/seed_demo.py" --api "$BASE" --no-manifest --secrets-out "$STATE/demo_logins.json" > "$STATE/seed-demo.log" 2>&1 \
    || { tail -15 "$STATE/seed-demo.log"; fail "seed_demo.py failed (.prodlocal/seed-demo.log)"; }
  tail -1 "$STATE/seed-demo.log" | sed 's/^/    /'
  # The seeding signed in several times; start the audit with clean counters.
  compose exec -T redis redis-cli FLUSHALL > /dev/null
fi

printf '\n\033[32mReady.\033[0m\n'
echo "  Storefront  http://localhost:$PRODLOCAL_PORT"
echo "  Admin       http://localhost:$PRODLOCAL_PORT/admin   (Owner login: ADMIN_EMAIL / ADMIN_PASSWORD in .prodlocal/env)"
echo "  Stop        scripts/prod_local.sh down"
