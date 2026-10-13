#!/usr/bin/env python
"""Run SQL against a Postgres URL without needing the psql binary.

Used by scripts/render_bootstrap_db.sh so loading the schema needs nothing but
Python and psycopg2 — no local Postgres install, no Docker.

    python scripts/db_exec.py --file backend/schema.sql
    python scripts/db_exec.py --query "SELECT count(*) FROM pg_tables"

Reads the connection string from DATABASE_URL. Prints query results the way
`psql -At` does (tab-separated, no header, no decoration) so the shell script
can consume them unchanged. Never prints the connection string, and redacts it
out of any error message.
"""
import argparse
import os
import re
import sys

import psycopg2

# pg_dump >= 17 emits \restrict / \unrestrict psql meta-commands. psql
# understands them; psycopg2 does not, so drop those lines. Same treatment as
# backend/tests/conftest.py.
_PSQL_META = re.compile(r"^\\(un)?restrict\b.*$", re.MULTILINE)


def redact(text):
    text = re.sub(r"postgresql://[^\s'\"]+", "<url>", str(text))
    text = re.sub(r"npg_[A-Za-z0-9]+", "<redacted>", text)
    return text


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--file", help="path to a .sql file to execute")
    g.add_argument("--query", help="a single statement whose rows are printed")
    args = ap.parse_args()

    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL is not set.")

    try:
        conn = psycopg2.connect(url, connect_timeout=60)
    except Exception as exc:
        sys.exit(f"Could not connect: [{type(exc).__name__}] {redact(exc)}")

    # DDL in the dump is not transaction-wrapped by us; match psql's default of
    # autocommit so a failure leaves the work that already succeeded in place
    # and ON_ERROR_STOP-style behaviour comes from the non-zero exit below.
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            if args.file:
                sql = _PSQL_META.sub("", open(args.file, encoding="utf-8").read())
                cur.execute(sql)
            else:
                cur.execute(args.query)
                if cur.description:
                    for row in cur.fetchall():
                        print("\t".join("" if v is None else str(v) for v in row))
    except Exception as exc:
        where = args.file or "query"
        print(f"SQL failed in {where}: [{type(exc).__name__}] {redact(exc)}",
              file=sys.stderr)
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
