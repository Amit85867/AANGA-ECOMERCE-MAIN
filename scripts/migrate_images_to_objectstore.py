#!/usr/bin/env python
"""Move locally-stored product images into S3-compatible object storage.

The demo catalogue was seeded from a laptop with no object storage configured,
so its image rows point at ``/static/uploads/<file>`` -- files that exist on
that one machine and nowhere else. This uploads them to the bucket and rewrites
every stored URL to the public one.

Run it against the branch whose rows you want rewritten, with that branch's
storage settings in the environment:

    DATABASE_URL=<branch, DIRECT>  \\
    S3_ENDPOINT_URL=... S3_BUCKET=... S3_ACCESS_KEY_ID=... \\
    S3_SECRET_ACCESS_KEY=... S3_REGION=... \\
      python scripts/migrate_images_to_objectstore.py --dry-run

Idempotent: a URL that already points at the bucket is left alone, and an
object that is already there is not re-uploaded unless --force is given. Safe
to re-run after a partial failure.

Every variant (the srcset widths) is carried across too, and a missing variant
is regenerated from the original rather than being lost.
"""
import argparse
import mimetypes
import os
import sys

BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, BACKEND)

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.services import media, objectstore, storage  # noqa: E402

LOCAL_PREFIX = "/static/uploads/"


def local_path(filename):
    return os.path.join(BACKEND, "static", "uploads", filename)


def content_type_for(filename):
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or "application/octet-stream"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report, change nothing")
    ap.add_argument("--force", action="store_true", help="re-upload objects that already exist")
    args = ap.parse_args()

    app = create_app()
    with app.app_context():
        if not objectstore.is_configured():
            sys.exit(
                "Object storage is not configured: "
                + ", ".join(objectstore.missing_settings())
            )
        bucket = app.config["S3_BUCKET"]
        print(f"Bucket        : {bucket}")
        print(f"Public base   : {objectstore.public_base_url()}")
        print(f"Mode          : {'DRY RUN' if args.dry_run else 'APPLY'}\n")

        # ---- 1. every distinct local URL currently stored, and where ----
        targets = []          # (label, model, column)
        local_urls = set()
        for label, model, column, _name in media._columns():
            col = getattr(model, column)
            rows = db.session.query(col).filter(col.like(f"{LOCAL_PREFIX}%")).all()
            if rows:
                targets.append((label, model, column))
            for (value,) in rows:
                local_urls.add(value)

        print(f"Rows to rewrite are in : {', '.join(l for l, _, _ in targets) or 'nothing'}")
        print(f"Distinct local images  : {len(local_urls)}\n")
        if not local_urls:
            print("Nothing to migrate.")
            return 0

        # ---- 2. upload each original plus its srcset variants ----
        uploaded = skipped = regenerated = missing = 0
        rewrite = {}
        for url in sorted(local_urls):
            filename = url[len(LOCAL_PREFIX):]
            path = local_path(filename)
            if not os.path.exists(path):
                print(f"  MISSING on disk: {filename}")
                missing += 1
                continue

            with open(path, "rb") as fh:
                data = fh.read()

            names = [(filename, data)]
            # Variants: carry the stored ones, regenerate any that are absent.
            if filename.lower().endswith(".webp"):
                for width in storage.VARIANT_WIDTHS:
                    vname = storage.variant_name(filename, width)
                    vpath = local_path(vname)
                    if os.path.exists(vpath):
                        with open(vpath, "rb") as fh:
                            names.append((vname, fh.read()))
                    else:
                        try:
                            made = storage.make_variant(data, width)
                        except Exception as exc:  # noqa: BLE001
                            print(f"  variant {width} not made for {filename}: {exc}")
                            continue
                        if made:
                            names.append((vname, made))
                            regenerated += 1

            for name, payload in names:
                if not args.force and objectstore.exists(name):
                    skipped += 1
                    continue
                if args.dry_run:
                    uploaded += 1
                    continue
                objectstore.put_bytes(name, payload, content_type_for(name))
                uploaded += 1

            rewrite[url] = objectstore.public_url(filename)

        print(f"\nObjects uploaded     : {uploaded}")
        print(f"Already present      : {skipped}")
        print(f"Variants regenerated : {regenerated}")
        print(f"Local files missing  : {missing}")

        # ---- 3. rewrite the stored URLs ----
        changed = 0
        for label, model, column in targets:
            col = getattr(model, column)
            for old, new in rewrite.items():
                n = db.session.query(model).filter(col == old).update(
                    {column: new}, synchronize_session=False
                )
                changed += n
        if args.dry_run:
            db.session.rollback()
            print(f"Rows that WOULD be rewritten: {changed}  (dry run, rolled back)")
        else:
            db.session.commit()
            print(f"Rows rewritten       : {changed}")

        # ---- 4. prove it ----
        left = 0
        for label, model, column, _name in media._columns():
            col = getattr(model, column)
            left += db.session.query(col).filter(col.like(f"{LOCAL_PREFIX}%")).count()
        print(f"Rows still pointing at local disk: {left}")
        if left and not args.dry_run:
            print("  (these are the ones whose file was missing on disk)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
