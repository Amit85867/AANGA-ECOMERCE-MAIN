"""Seed the storefront catalogue through the admin REST API.

Creates the category tree, then uploads one image per product and creates the
product with its variants. Everything goes through /api/admin/* exactly as the
admin UI would, so the real auth, validation and storage paths are exercised.

Images come from the Stitch zip at the repo root. Their folder names are
unreliable -- roughly a third describe something other than what the picture
shows -- so PRODUCTS below is keyed by the image's position in the sorted zip
listing and was written by looking at each one.

Source images are 1024x1024 PNGs averaging 930 KB, which is far too heavy for a
listing page. They are resized and converted to WebP before upload (~15x
smaller); the stored files are what the storefront serves.

Usage (with the API running on :5000):
    python db/seed_catalogue.py
    python db/seed_catalogue.py --api https://api.example.com
    python db/seed_catalogue.py --dry-run

Idempotent: products whose slug already exists are skipped.
"""
import argparse
import io
import os
import re
import sys
import zipfile

import requests
from dotenv import load_dotenv
from PIL import Image

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(BACKEND_DIR)

# Same ADMIN_EMAIL / ADMIN_PASSWORD the app auto-seeds the master admin from.
load_dotenv(os.path.join(BACKEND_DIR, ".env"))
ZIP_NAME = "stitch_stylehub_premium_e_commerce_interface (1).zip"

# Upload target: long edge in px, and WebP quality.
IMAGE_MAX_EDGE = 1200
IMAGE_QUALITY = 82

TOPS = ["S", "M", "L", "XL"]
MENS_BOTTOMS = ["30", "32", "34", "36"]
WOMENS_BOTTOMS = ["XS", "S", "M", "L"]
SHOES = ["7", "8", "9", "10"]
ONE_SIZE = ["One Size"]

# Category tree: (name, slug, parent_slug, sort_order)
CATEGORIES = [
    ("Men", "men", None, 1),
    ("Women", "women", None, 2),
    ("Footwear", "footwear", None, 3),
    ("Bags", "bags", None, 4),
    ("Jewellery", "jewellery", None, 5),
    ("Accessories", "accessories", None, 6),

    ("Shirts", "mens-shirts", "men", 1),
    ("T-Shirts & Polos", "mens-tees", "men", 2),
    ("Sweatshirts & Hoodies", "mens-sweats", "men", 3),
    ("Jackets & Coats", "mens-outerwear", "men", 4),
    ("Trousers & Jeans", "mens-bottoms", "men", 5),

    ("Dresses", "womens-dresses", "women", 1),
    ("Ethnic Wear", "womens-ethnic", "women", 2),
    ("Knitwear", "womens-knitwear", "women", 3),
    ("Blazers", "womens-blazers", "women", 4),
    ("Skirts", "womens-skirts", "women", 5),
    ("Activewear", "womens-activewear", "women", 6),
]

# Keyed by 1-based position in the sorted zip listing.
#   name, category slug, mrp, selling price, sizes, [(colour, hex)], badge, featured
PRODUCTS = {
    1:  ("Essential Cotton Baseball Cap", "accessories", 1299, 899, ONE_SIZE,
         [("Black", "#111111")], None, False),
    2:  ("Loopback Cotton Sweatshirt", "mens-sweats", 2999, 2199, TOPS,
         [("Heather Grey", "#b6b6b6")], None, False),
    3:  ("Cable-Knit Cashmere Sweater", "womens-knitwear", 6999, 4999, TOPS,
         [("Blush Pink", "#e8b4b8")], "Bestseller", True),
    4:  ("Structured Leather Top-Handle Bag", "bags", 12999, 8999, ONE_SIZE,
         [("Black", "#111111")], "Bestseller", True),
    5:  ("Crisp Cotton Formal Shirt", "mens-shirts", 2799, 1999, TOPS,
         [("White", "#fdfdfd")], None, False),
    6:  ("Washed Linen Shirt", "mens-shirts", 3299, 2499, TOPS,
         [("Navy", "#27374a")], "New", False),
    7:  ("Petite Diamond Pendant Necklace", "jewellery", 8999, 6499, ONE_SIZE,
         [("Gold", "#d4af37")], None, True),
    8:  ("Brushed Gold Band Ring", "jewellery", 5999, 4499, ONE_SIZE,
         [("Gold", "#d4af37")], None, False),
    9:  ("Minimalist Leather-Strap Watch", "accessories", 9999, 6999, ONE_SIZE,
         [("Silver / Black", "#c0c0c0")], "Bestseller", True),
    10: ("Classic Bomber Jacket", "mens-outerwear", 5999, 4299, TOPS,
         [("Navy", "#1f2a44")], None, False),
    11: ("Heavyweight Cotton Hoodie", "mens-sweats", 3499, 2599, TOPS,
         [("Heather Grey", "#b6b6b6")], None, False),
    12: ("Bifold Leather Wallet", "accessories", 2499, 1699, ONE_SIZE,
         [("Chocolate Brown", "#4a2c18")], None, False),
    13: ("Oversized Cotton T-Shirt", "mens-tees", 1499, 999, TOPS,
         [("Washed Black", "#2b2b2b")], "New", False),
    14: ("Double-Breasted Wool Overcoat", "mens-outerwear", 14999, 10999, TOPS,
         [("Camel", "#c19a6b")], "Bestseller", True),
    15: ("Chunky Curb Link Bracelet", "jewellery", 4499, 3199, ONE_SIZE,
         [("Silver", "#c0c0c0")], None, False),
    16: ("Technical Commuter Backpack", "bags", 6499, 4799, ONE_SIZE,
         [("Black", "#111111")], "New", False),
    17: ("Full-Grain Leather Belt", "accessories", 1999, 1399, ONE_SIZE,
         [("Tan", "#a9622f")], None, False),
    18: ("Technical Hooded Windbreaker", "mens-outerwear", 7999, 5999, TOPS,
         [("Black", "#111111")], None, False),
    19: ("Pique Cotton Polo", "mens-tees", 1999, 1499, TOPS,
         [("White", "#fdfdfd")], None, False),
    20: ("Tailored Linen Blazer", "womens-blazers", 6999, 4999, TOPS,
         [("Beige", "#d9cbb3")], None, True),
    21: ("Floral Embroidered Kurti", "womens-ethnic", 3499, 2499, TOPS,
         [("Ivory", "#f2eadb")], "Bestseller", True),
    22: ("Pleated Chiffon Midi Skirt", "womens-skirts", 3299, 2399, WOMENS_BOTTOMS,
         [("Cream", "#efe6d5")], None, False),
    23: ("Draped Silk Maxi Dress", "womens-dresses", 8999, 6499, TOPS,
         [("Emerald", "#0f7355")], "Bestseller", True),
    24: ("Leather Wingtip Brogues", "footwear", 7999, 5999, SHOES,
         [("Tan", "#8b4a20")], None, False),
    25: ("Classic Aviator Sunglasses", "accessories", 3499, 2499, ONE_SIZE,
         [("Black", "#111111")], None, False),
    26: ("Performance Running Shoes", "footwear", 6999, 4999, SHOES,
         [("Cyan / Lime", "#00a3e0")], "New", False),
    27: ("Minimal Leather Sneakers", "footwear", 5499, 3999, SHOES,
         [("White", "#fdfdfd")], "Bestseller", True),
    28: ("High-Rise Performance Leggings", "womens-activewear", 2499, 1799, WOMENS_BOTTOMS,
         [("Black", "#111111")], None, False),
    29: ("Cotton Cargo Trousers", "mens-bottoms", 3499, 2599, MENS_BOTTOMS,
         [("Olive", "#5a5f3d")], None, False),
    30: ("Straight-Fit Denim Jeans", "mens-bottoms", 3999, 2999, MENS_BOTTOMS,
         [("Indigo", "#3b5171")], None, True),
}

STOCK_PER_VARIANT = 25


def slugify(text):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", text.lower())).strip("-")


class AdminAPI:
    def __init__(self, base, email, password):
        self.base = base.rstrip("/")
        self.s = requests.Session()
        r = self.s.post(
            f"{self.base}/api/admin/auth/login",
            json={"email": email, "password": password},
            timeout=30,
        )
        if r.status_code != 200:
            raise SystemExit(f"Admin login failed ({r.status_code}): {r.text[:300]}")
        self.s.headers["Authorization"] = f"Bearer {r.json()['access_token']}"

    def get(self, path, **kw):
        return self.s.get(f"{self.base}{path}", timeout=30, **kw)

    def post(self, path, **kw):
        return self.s.post(f"{self.base}{path}", timeout=120, **kw)


def to_webp(png_bytes):
    """Downscale and re-encode. Returns (bytes, original_kb, new_kb)."""
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    im.thumbnail((IMAGE_MAX_EDGE, IMAGE_MAX_EDGE), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=IMAGE_QUALITY, method=6)
    return buf.getvalue(), len(png_bytes) // 1024, buf.tell() // 1024


def ensure_categories(api, dry_run):
    """Create the tree parents-first and return {slug: id}."""
    existing = {}
    r = api.get("/api/admin/categories")
    if r.status_code == 200:
        def walk(nodes):
            for n in nodes:
                existing[n["slug"]] = n["id"]
                walk(n.get("children", []))
        walk(r.json().get("categories", []))

    ids = dict(existing)
    for name, slug, parent_slug, sort_order in CATEGORIES:
        if slug in ids:
            print(f"  = {name} (exists)")
            continue
        if dry_run:
            print(f"  + {name}  [dry-run]")
            ids[slug] = -1
            continue
        payload = {
            "name": name,
            "slug": slug,
            "parent_id": ids.get(parent_slug) if parent_slug else None,
            "sort_order": sort_order,
        }
        r = api.post("/api/admin/categories", json=payload)
        if r.status_code not in (200, 201):
            raise SystemExit(f"Category '{name}' failed ({r.status_code}): {r.text[:300]}")
        ids[slug] = r.json()["id"]
        print(f"  + {name}")
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:5000")
    ap.add_argument("--email", default=os.environ.get("ADMIN_EMAIL"))
    ap.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD"))
    ap.add_argument("--zip", default=os.path.join(REPO_ROOT, ZIP_NAME))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not args.email or not args.password:
        raise SystemExit("Set ADMIN_EMAIL / ADMIN_PASSWORD (env or --email/--password).")
    if not os.path.exists(args.zip):
        raise SystemExit(f"Image archive not found: {args.zip}")

    zf = zipfile.ZipFile(args.zip)
    images = sorted(n for n in zf.namelist() if n.lower().endswith(".png"))
    if len(images) != len(PRODUCTS):
        raise SystemExit(
            f"Expected {len(PRODUCTS)} images, found {len(images)}. The index-to-product "
            "mapping in PRODUCTS would be wrong -- re-check before seeding."
        )

    api = AdminAPI(args.api, args.email, args.password)
    print(f"Authenticated against {args.api}\n")

    print("Categories")
    cat_ids = ensure_categories(api, args.dry_run)

    r = api.get("/api/admin/products?per_page=500")
    existing_slugs = {p["slug"] for p in r.json().get("products", [])} if r.status_code == 200 else set()

    print("\nProducts")
    created = skipped = 0
    saved_kb = 0
    for idx, entry in sorted(PRODUCTS.items()):
        name, cat_slug, mrp, price, sizes, colors, badge, featured = entry
        slug = slugify(name)

        if slug in existing_slugs:
            print(f"  = {name} (exists)")
            skipped += 1
            continue
        if args.dry_run:
            print(f"  + {name}  ->  {cat_slug}  Rs.{price}  {len(sizes)*len(colors)} variants  [dry-run]")
            created += 1
            continue

        webp, old_kb, new_kb = to_webp(zf.read(images[idx - 1]))
        saved_kb += old_kb - new_kb

        r = api.post(
            "/api/admin/upload",
            files={"file": (f"{slug}.webp", webp, "image/webp")},
        )
        if r.status_code != 201:
            raise SystemExit(f"Upload for '{name}' failed ({r.status_code}): {r.text[:300]}")
        image_url = r.json()["url"]

        payload = {
            "category_id": cat_ids[cat_slug],
            "name": name,
            "slug": slug,
            "description": f"{name}. Part of the AANGA edit -- placeholder copy pending final catalogue text.",
            "mrp": float(mrp),
            "selling_price": float(price),
            "is_active": True,
            "is_featured": featured,
        }
        if badge:
            payload["badge_label"] = badge
        r = api.post("/api/admin/products", json=payload)
        if r.status_code != 201:
            raise SystemExit(f"Product '{name}' failed ({r.status_code}): {r.text[:300]}")
        pid = r.json()["id"]

        r = api.post(
            f"/api/admin/products/{pid}/images",
            json={"image_url": image_url, "sort_order": 0, "is_primary": True},
        )
        if r.status_code != 201:
            raise SystemExit(f"Image link for '{name}' failed ({r.status_code}): {r.text[:300]}")

        for color_name, color_hex in colors:
            for size in sizes:
                r = api.post(
                    f"/api/admin/products/{pid}/variants",
                    json={
                        "size": size,
                        "color_name": color_name,
                        "color_hex": color_hex,
                        "stock_qty": STOCK_PER_VARIANT,
                        "sku": f"{slug[:20].upper().replace('-', '')}-{slugify(color_name)[:6].upper()}-{size}",
                    },
                )
                if r.status_code != 201:
                    raise SystemExit(
                        f"Variant {size}/{color_name} for '{name}' failed "
                        f"({r.status_code}): {r.text[:300]}"
                    )

        flags = " ".join(x for x in [badge, "featured" if featured else ""] if x)
        print(f"  + {name:<38} {cat_slug:<20} {old_kb:>4}KB -> {new_kb:>3}KB  {flags}")
        created += 1

    print(f"\nCreated {created}, skipped {skipped}.")
    if saved_kb:
        print(f"Image payload reduced by {saved_kb/1024:.1f} MB across the catalogue.")


if __name__ == "__main__":
    sys.exit(main())
