"""Create the missing "<name>_480.webp" / "<name>_800.webp" copies of uploaded images.

New uploads get a thumbnail automatically (app/services/storage.py). This is
for images stored before that existed. Safe to run again: existing thumbnails
are left alone.

Local disk (development):
    python db/make_thumbnails.py

Supabase Storage (production) — reads SUPABASE_URL / SUPABASE_SERVICE_KEY /
SUPABASE_STORAGE_BUCKET from the environment or backend/.env:
    python db/make_thumbnails.py --supabase

The storefront works without thumbnails (it falls back to the full image), so
this is an optimisation, not a required migration step.
"""
import argparse
import os
import pathlib
import re
import sys

BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import requests  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from app.services.storage import VARIANT_WIDTHS, make_variant, variant_name  # noqa: E402

ORIGINAL = re.compile(r"^[0-9a-f]{32}\.webp$")


def local():
    folder = BACKEND / "static" / "uploads"
    made = skipped = 0
    for path in sorted(folder.glob("*.webp")):
        if not ORIGINAL.match(path.name):
            continue
        for width in VARIANT_WIDTHS:
            target = path.with_name(variant_name(path.name, width))
            if target.exists():
                skipped += 1
                continue
            variant = make_variant(path.read_bytes(), width)
            if variant:
                target.write_bytes(variant)
                made += 1
    print(f"local: {made} thumbnails created, {skipped} already present")


def supabase():
    load_dotenv(BACKEND / ".env")
    base = (os.environ.get("SUPABASE_URL") or "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    bucket = os.environ.get("SUPABASE_STORAGE_BUCKET", "product-images")
    if not base or not key:
        raise SystemExit("Set SUPABASE_URL and SUPABASE_SERVICE_KEY.")
    auth = {"Authorization": f"Bearer {key}", "apikey": key}

    names, offset = [], 0
    while True:
        resp = requests.post(
            f"{base}/storage/v1/object/list/{bucket}", headers=auth, timeout=30,
            json={"prefix": "", "limit": 1000, "offset": offset},
        )
        resp.raise_for_status()
        page = [o["name"] for o in resp.json()]
        names += page
        if len(page) < 1000:
            break
        offset += 1000

    existing = set(names)
    made = 0
    for name in names:
        if not ORIGINAL.match(name):
            continue
        missing = [w for w in VARIANT_WIDTHS if variant_name(name, w) not in existing]
        if not missing:
            continue
        original = requests.get(f"{base}/storage/v1/object/public/{bucket}/{name}", timeout=60)
        original.raise_for_status()
        for width in missing:
            variant = make_variant(original.content, width)
            if not variant:
                continue
            put = requests.post(
                f"{base}/storage/v1/object/{bucket}/{variant_name(name, width)}", data=variant, timeout=60,
                headers={**auth, "Content-Type": "image/webp", "x-upsert": "true"},
            )
            put.raise_for_status()
            made += 1
    print(f"supabase: {made} thumbnails created in bucket {bucket}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--supabase", action="store_true", help="work on the Supabase bucket instead of local disk")
    args = parser.parse_args()
    supabase() if args.supabase else local()
