#!/usr/bin/env python
"""Issue a storage credential for a Neon branch and write it into backend/.env.

    python scripts/refresh_storage_credential.py --branch dev

**Run this after every branch reset.** Resetting a Neon branch destroys the
credentials issued on it: the bucket and its objects survive, but the access
key does not, and the next upload fails with AccessDenied. The symptom is
confusing because reads keep working -- a public_read bucket needs no
credential -- so the storefront looks fine and only the admin's upload breaks.

Secrets are fetched into memory and written straight to the file; nothing is
printed. Any existing credential of the same name on that branch is revoked
first, so this does not accumulate keys.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / "backend" / ".env"

PROJECT = os.environ.get("NEON_PROJECT_ID", "dry-base-24522506")
ORG = os.environ.get("NEON_ORG_ID", "org-long-mud-04364433")
BUCKET = os.environ.get("S3_BUCKET_NAME", "product-images")
NEONCTL = os.environ.get("NEONCTL_BIN", os.path.expandvars(r"%APPDATA%\npm\neonctl.cmd"))
if not os.path.exists(NEONCTL):
    NEONCTL = "neonctl"

CRED_NAME = "aanga-{branch}-storage"


def run(args):
    r = subprocess.run([NEONCTL] + args, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"neonctl {args[0]} failed: {r.stderr.strip()[:300]}")
    return r.stdout


def first_json(raw):
    """neonctl prints a plain-text warning after the JSON on `reveal`."""
    dec = json.JSONDecoder()
    i = 0
    while i < len(raw) and raw[i] in " \t\r\n":
        i += 1
    obj, _ = dec.raw_decode(raw, i)
    return obj


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default="dev", help="branch name (default: dev)")
    ap.add_argument("--print-only", action="store_true",
                    help="do not touch .env; report what would be set (names only)")
    args = ap.parse_args()

    if args.branch == "production":
        sys.exit(
            "Refusing to write a production credential to a file.\n"
            "Issue it by hand and set the values in the Render Dashboard:\n"
            f"  neonctl credentials create --project-id {PROJECT} --org-id {ORG} \\\n"
            "    --branch production --name aanga-production-storage \\\n"
            "    --scope storage:read --scope storage:write"
        )

    common = ["--project-id", PROJECT, "--org-id", ORG, "--branch", args.branch]
    name = CRED_NAME.format(branch=args.branch)

    # The bucket is per-branch and a branch created before the bucket existed
    # does not have one. Creating an existing bucket is harmless.
    subprocess.run(
        [NEONCTL, "buckets", "create", BUCKET] + common + ["--access-level", "public_read"],
        capture_output=True, text=True,
    )

    # Revoke any previous key of this name so they do not pile up.
    for cred in first_json(run(["credentials", "list"] + common + ["--output", "json"])) or []:
        if cred.get("name") == name:
            subprocess.run([NEONCTL, "credentials", "revoke", cred["token_id"]] + common,
                           capture_output=True, text=True)

    created = first_json(run([
        "credentials", "create"] + common + [
        "--name", name, "--scope", "storage:read", "--scope", "storage:write",
        "--output", "json",
    ]))
    if isinstance(created, list):
        created = created[0]
    token_id = created["token_id"]

    revealed = first_json(run(["credentials", "reveal", token_id] + common + ["--output", "json"]))
    if isinstance(revealed, list):
        revealed = revealed[0]

    # The raw API wants the branch id; everything else accepts the name.
    branches = first_json(run([
        "branches", "list", "--project-id", PROJECT, "--org-id", ORG, "--output", "json",
    ]))
    match = next((b for b in branches if b["name"] == args.branch or b["id"] == args.branch), None)
    if match is None:
        sys.exit(f"No branch named {args.branch!r} in project {PROJECT}.")

    storage = first_json(run(["api", f"/projects/{PROJECT}/branches/{match['id']}/storage"]))
    if not storage.get("enabled"):
        sys.exit(f"Object storage is not enabled on branch {args.branch!r}.")
    endpoint = storage["s3_endpoint"].rstrip("/")

    values = {
        "S3_ENDPOINT_URL": endpoint,
        "S3_REGION": storage.get("region", "auto"),
        "S3_BUCKET": BUCKET,
        "S3_ACCESS_KEY_ID": token_id,
        "S3_SECRET_ACCESS_KEY": revealed["s3_secret_access_key"],
        "S3_PUBLIC_BASE_URL": f"{endpoint}/{BUCKET}",
        "S3_FORCE_PATH_STYLE": "true" if storage.get("force_path_style", True) else "false",
    }

    if args.print_only:
        print(f"Would set for branch '{args.branch}':")
        for k in values:
            print(f"  {k}")
        return 0

    text = ENV_FILE.read_text(encoding="utf-8")
    out, seen = [], set()
    for line in text.splitlines():
        m = re.match(r"^\s*([A-Z0-9_]+)\s*=", line)
        if m and m.group(1) in values:
            k = m.group(1)
            if k in seen:
                continue
            seen.add(k)
            out.append(f"{k}={values[k]}")
        else:
            out.append(line)
    for k, v in values.items():
        if k not in seen:
            out.append(f"{k}={v}")
    ENV_FILE.write_text("\n".join(out) + "\n", encoding="utf-8")

    print(f"Issued '{name}' on branch '{args.branch}' (storage:read + storage:write)")
    print(f"Wrote {len(values)} S3_* settings into backend/.env (values not shown)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
