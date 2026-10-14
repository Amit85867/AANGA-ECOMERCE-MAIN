#!/usr/bin/env bash
#
# Load the AANGA schema into a Neon branch (or any other Postgres 17).
#
#   DATABASE_URL=postgresql://...  scripts/render_bootstrap_db.sh            # new, empty database
#   DATABASE_URL=postgresql://...  scripts/render_bootstrap_db.sh --migrate  # existing database
#   DATABASE_URL=postgresql://...  scripts/render_bootstrap_db.sh --check    # report only
#
# Use the branch's DIRECT connection string (no "-pooler" in the host): this
# issues DDL and wants a real session, not a PgBouncer one. Fetch it into the
# environment for this one command so it never reaches a file or your history:
#
#   DATABASE_URL="$(neonctl connection-string production \
#     --project-id dry-base-24522506 --org-id org-long-mud-04364433 \
#     --role-name aanga_owner --database-name aanga)" \
#     scripts/render_bootstrap_db.sh
#
# Connect as the SAME user the application uses (aanga_owner). The tables carry
# row-level-security policies
# inherited from Supabase; the table owner bypasses them, anyone else is
# filtered by them. Loading the schema as a different user would leave the app
# reading empty tables.
#
# Fresh load, in order:
#   1. tests/sql/00_prereqs.sql   uuid-ossp + a stub auth.uid() the policies name
#   2. schema.sql                 every table, enum, trigger, index and policy
#   3. migrations (below)         idempotent; already inside schema.sql, re-run
#                                 so this script is also the upgrade path
#   4. verification
#
# It never drops anything that holds data: a database that already has tables
# is refused unless --migrate is given.
#
# Seeding products is a separate, optional step that goes through the running
# API (it uploads images through the real storage path), so it comes after the
# first deploy:
#   ADMIN_EMAIL=... ADMIN_PASSWORD=... \
#     python backend/db/seed_catalogue.py --api https://<backend-url>
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"

# Applied in this order. All are written with IF NOT EXISTS guards.
# (migrations_cms*.sql and migrations_password_resets.sql are NOT here: their
# tables are part of schema.sql and their INSERTs are not re-runnable.)
MIGRATIONS=(
  migrations_orders_idempotency.sql   # payment_ref / idempotency_key unique indexes
  migrations_hero_badges.sql          # hero banner pill / chip columns
  migrations_address_archive.sql      # addresses.archived_at
  migrations_ops_tables.sql           # webhook_events, job_runs
  migrations_admin_ops.sql            # audit_log + dashboard indexes
  migrations_owner_dashboard.sql      # collections, campaigns, homepage, pages, media, demo flag
)

MODE="fresh"
case "${1:-}" in
  "") ;;
  --migrate) MODE="migrate" ;;
  --check) MODE="check" ;;
  -h|--help) sed -n '2,32p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
  *) echo "Unknown option: $1 (try --help)" >&2; exit 2 ;;
esac

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is not set. Use the database's External Database URL." >&2
  exit 2
fi

# psql if this machine has it, otherwise scripts/db_exec.py (psycopg2). The
# Python path is the normal one: Neon is a managed Postgres 17, so no local
# server or container is needed to load a dump into it, and the backend's
# virtualenv already has psycopg2.
if command -v psql >/dev/null 2>&1; then
  run_file() { PGOPTIONS="--client-min-messages=warning" psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -X -q -f "$1"; }
  run_sql()  { PGOPTIONS="--client-min-messages=warning" psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -X -q -c "$1"; }
  query()    { psql "$DATABASE_URL" -X -At -c "$1"; }
else
  if [ -x "$BACKEND/venv/Scripts/python.exe" ]; then PY="$BACKEND/venv/Scripts/python.exe"
  elif [ -x "$BACKEND/venv/bin/python" ]; then PY="$BACKEND/venv/bin/python"
  else PY="$(command -v python3 || command -v python || true)"; fi
  [ -n "$PY" ] || { echo "Need either psql or Python with psycopg2." >&2; exit 2; }
  "$PY" -c "import psycopg2" 2>/dev/null || {
    echo "Python found but psycopg2 is missing. Install backend/requirements.txt." >&2
    exit 2
  }
  run_file() { "$PY" "$ROOT/scripts/db_exec.py" --file "$1"; }
  run_sql()  { "$PY" "$ROOT/scripts/db_exec.py" --query "$1" >/dev/null; }
  query()    { "$PY" "$ROOT/scripts/db_exec.py" --query "$1"; }
fi

host="$(printf '%s' "$DATABASE_URL" | sed -E 's#^[a-z]+://([^@]*@)?([^:/?]+).*#\2#')"
echo "Database host: $host"

server_major="$(query "SHOW server_version_num" | cut -c1-2)"
echo "Server version: $server_major"
if [ "$server_major" != "17" ]; then
  echo "Warning: schema.sql was dumped from Postgres 17; this server is $server_major." >&2
fi

table_count="$(query "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")"
echo "Tables in public: $table_count"

verify() {
  echo
  echo "Verification"
  query "SELECT '  tables:   ' || count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'"
  query "SELECT '  triggers: ' || count(*) FROM information_schema.triggers WHERE trigger_schema='public'"
  missing=0
  for object in \
      "orders.idempotency_key" "addresses.archived_at" "hero_banners.pill_label" \
      "products.is_demo" "hero_banners.campaign_id" "coupons.campaign_id" "products.meta_title"; do
    table="${object%%.*}"; column="${object##*.}"
    found="$(query "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='$table' AND column_name='$column'")"
    [ "$found" = "1" ] && echo "  ok   column $object" || { echo "  MISSING column $object"; missing=1; }
  done
  for table in webhook_events job_runs audit_log collections campaigns homepage_sections nav_links cms_pages faq_items media_assets; do
    found="$(query "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='$table'")"
    [ "$found" = "1" ] && echo "  ok   table $table" || { echo "  MISSING table $table"; missing=1; }
  done
  for index in uq_orders_payment_ref uq_orders_idempotency_key idx_orders_status_placed_at; do
    found="$(query "SELECT count(*) FROM pg_indexes WHERE schemaname='public' AND indexname='$index'")"
    [ "$found" = "1" ] && echo "  ok   index $index" || { echo "  MISSING index $index"; missing=1; }
  done
  # The app must own the tables, or row-level security hides every row from it.
  foreign="$(query "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner <> current_user")"
  [ "$foreign" = "0" ] && echo "  ok   all tables owned by $(query 'SELECT current_user')" \
    || { echo "  WRONG OWNER on $foreign table(s): the app will read them as empty"; missing=1; }
  # Test accounts from the local walkthrough must never reach a live database.
  qa="$(query "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='users'")"
  if [ "$qa" = "1" ]; then
    qa_users="$(query "SELECT count(*) FROM public.users WHERE email LIKE '%@local.test'")"
    [ "$qa_users" = "0" ] && echo "  ok   no QA test accounts" \
      || { echo "  FOUND $qa_users QA test account(s): run backend/db/qa_cleanup.sql"; missing=1; }
  fi
  return $missing
}

apply_migrations() {
  for entry in "${MIGRATIONS[@]}"; do
    file="$BACKEND/$entry"
    [ -f "$file" ] || { echo "Missing migration file: $entry" >&2; exit 1; }
    echo "  applying $entry"
    run_file "$file"
  done
}

case "$MODE" in
  check)
    verify || { echo; echo "Database is NOT up to date."; exit 1; }
    echo; echo "Database is up to date."
    ;;

  migrate)
    if [ "$table_count" = "0" ]; then
      echo "This database is empty. Run without --migrate to load the schema." >&2
      exit 1
    fi
    echo; echo "Applying migrations to the existing database"
    apply_migrations
    verify || { echo; echo "Migration finished but verification failed."; exit 1; }
    echo; echo "Done."
    ;;

  fresh)
    if [ "$table_count" != "0" ]; then
      echo >&2
      echo "Refusing to load: this database already has $table_count table(s)." >&2
      echo "  To upgrade it in place:   $0 --migrate" >&2
      echo "  To see what is missing:   $0 --check" >&2
      exit 1
    fi

    echo; echo "Loading the schema into an empty database"
    # schema.sql begins with its own CREATE SCHEMA public. Safe to drop: the
    # check above just confirmed it holds no tables.
    echo "  resetting the empty public schema"
    run_sql "DROP SCHEMA IF EXISTS public CASCADE"
    echo "  applying tests/sql/00_prereqs.sql"
    run_file "$BACKEND/tests/sql/00_prereqs.sql"
    echo "  applying schema.sql"
    run_file "$BACKEND/schema.sql"
    apply_migrations
    verify || { echo; echo "Load finished but verification failed."; exit 1; }
    echo
    echo "Done. Next: deploy the API (it creates the master admin from"
    echo "ADMIN_EMAIL / ADMIN_PASSWORD on first boot), then seed the catalogue."
    ;;
esac
