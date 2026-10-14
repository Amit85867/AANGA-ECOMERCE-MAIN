"""Fill the store with demo content, through the admin API.

Everything here is done the way the dashboard does it — the same routes, the
same validation, the same image pipeline — signed in as the Owner with demo
mode on (``X-Demo-Content: 1``), so every item is tagged as demo and
"Remove demo content" can take it all away again. Nothing is written to the
database directly.

    # with the API running on :5000
    DEMO_OWNER_EMAIL=...  DEMO_OWNER_PASSWORD=...  python db/demo/seed_demo.py
    python db/demo/seed_demo.py --only settings,pages        # some steps
    python db/demo/seed_demo.py --secrets-out ../demo-logins.json

Steps: tag, settings, categories, products, extras, content, pages, collections,
staff, customers, campaign. Each is safe to run again: what already exists is
left alone.

Pictures: every new image is original artwork drawn by make_art.py. The
sample catalogue that came with the project keeps its own pictures (plus
close-ups cut from them). docs/DEMO_ASSETS.md is rewritten from what this run
and earlier runs uploaded.
"""
import argparse
import io
import json
import os
import pathlib
import secrets
import sys
from datetime import datetime, timedelta, timezone

import requests
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
BACKEND = HERE.parent.parent
sys.path.insert(0, str(HERE))
import make_art as art  # noqa: E402

MANIFEST = HERE / "assets_manifest.json"
DOC = BACKEND.parent / "docs" / "DEMO_ASSETS.md"
ORIGINAL = "Original artwork drawn for this project by backend/db/demo/make_art.py. No third-party material."
STITCH = "Close-up cut from the product picture that came with the project (Stitch design export supplied by the owner)."
IST = timezone(timedelta(hours=5, minutes=30))

APPAREL = ["S", "M", "L", "XL"]
WAIST = ["28", "30", "32", "34"]
SHOES = ["6", "7", "8", "9", "10"]
ONE = ["One Size"]

CARE = {
    "cotton": "100% cotton. Machine wash cold with similar colours. Do not bleach. Warm iron.",
    "linen": "100% linen. Gentle machine wash cold. Dry in shade. Iron while slightly damp.",
    "wool": "Wool blend. Dry clean only. Store folded, not on a hanger.",
    "silk": "Silk blend. Dry clean only. Iron on the reverse on a low setting.",
    "denim": "98% cotton, 2% elastane. Wash inside out in cold water. Do not tumble dry.",
    "knit": "Fine knit. Hand wash cold, reshape and dry flat. Do not wring.",
    "active": "Polyester-elastane blend. Machine wash cold. Do not use fabric softener. Do not iron.",
    "leather": "Genuine leather. Wipe with a soft dry cloth. Keep away from water and direct heat.",
    "metal": "Plated brass. Keep dry and away from perfume. Store in the pouch provided.",
    "canvas": "Cotton canvas. Spot clean with a damp cloth. Do not machine wash.",
}

# category slug, name, shape, colour, pattern, accent, MRP, price, sizes, colours, fabric, description
NEW_PRODUCTS = [
    ("mens-shirts", "Oxford Button-Down Shirt", "shirt", "#F1EEE8", "solid", "#31506E", 2499, 1799, APPAREL, [("Ivory", "#F1EEE8"), ("Sky Blue", "#A9C4DD")], "cotton",
     "A weekday staple in breathable Oxford cotton, with a button-down collar and a regular fit that sits well tucked or untucked."),
    ("mens-shirts", "Checked Flannel Shirt", "shirt", "#7A2E2E", "checks", "#F1EEE8", 2799, 1999, APPAREL, [("Brick Red", "#7A2E2E"), ("Forest", "#35523E")], "cotton",
     "Brushed cotton flannel in a classic check. Soft from the first wear, with a chest pocket and curved hem."),
    ("mens-tees", "Striped Crew-Neck T-Shirt", "tee", "#1F3A5F", "stripes", "#F1EEE8", 1299, 899, APPAREL, [("Navy Stripe", "#1F3A5F"), ("Olive Stripe", "#5B6C5D")], "cotton",
     "Mid-weight jersey with a yarn-dyed stripe and a ribbed crew neck. Cut slightly relaxed through the body."),
    ("mens-sweats", "Quarter-Zip Fleece Pullover", "sweater", "#4A5D4E", "solid", "#C2A878", 3299, 2399, APPAREL, [("Moss", "#4A5D4E"), ("Charcoal", "#2B2F3A")], "cotton",
     "A warm brushed-back fleece with a stand collar and quarter zip. Layers easily over a tee or under a jacket."),
    ("mens-sweats", "Garment-Dyed Pullover Hoodie", "hoodie", "#B5542B", "solid", "#F1EEE8", 2999, 2199, APPAREL, [("Rust", "#B5542B"), ("Stone", "#B9B1A2")], "cotton",
     "Heavy loopback cotton, garment dyed for a lived-in colour. Kangaroo pocket, lined hood and ribbed cuffs."),
    ("mens-outerwear", "Quilted Puffer Jacket", "jacket", "#2F3E46", "solid", "#C2A878", 6999, 4999, APPAREL, [("Slate", "#2F3E46"), ("Black", "#18181B")], "active",
     "Lightweight quilted jacket with recycled fill. Packs into its own pocket and shrugs off a light shower."),
    ("mens-bottoms", "Slim Chino Trousers", "trousers", "#C2A878", "solid", "#7B5B3A", 2799, 1999, WAIST, [("Khaki", "#C2A878"), ("Navy", "#1F2A44")], "cotton",
     "Stretch cotton twill chinos with a slim leg and a clean, flat front. Smart enough for work, easy enough for the weekend."),
    ("mens-bottoms", "Relaxed Linen Trousers", "trousers", "#E6DFD0", "solid", "#B9B1A2", 2999, 2299, WAIST, [("Oat", "#E6DFD0"), ("Olive", "#5B6C5D")], "linen",
     "Airy pure-linen trousers with a drawstring waist and a relaxed, straight leg — made for warm days."),
    ("womens-dresses", "Floral Wrap Dress", "dress", "#8A3B4B", "dots", "#F3D9C6", 3999, 2999, APPAREL, [("Mulberry", "#8A3B4B"), ("Teal", "#1F6F78")], "cotton",
     "A true wrap dress in soft printed cotton, with a tie waist, flutter sleeves and a skirt that moves."),
    ("womens-dresses", "Linen Shirt Dress", "dress", "#A7B8A8", "solid", "#F1EEE8", 3499, 2599, APPAREL, [("Sage", "#A7B8A8"), ("White", "#F5F2EC")], "linen",
     "Button-through linen with a relaxed waist and side pockets. Wear it belted or loose."),
    ("womens-dresses", "Satin Slip Dress", "dress", "#1E2A44", "solid", "#C9A227", 4499, 3299, APPAREL, [("Midnight", "#1E2A44"), ("Champagne", "#D9C7A3")], "silk",
     "Bias-cut satin that skims the body, with adjustable straps and a midi hem. Dress it up with heels or down with a knit."),
    ("womens-ethnic", "Silk Blend Anarkali Kurta", "kurta", "#7A1F3D", "solid", "#F2A900", 5999, 4499, APPAREL, [("Wine", "#7A1F3D"), ("Emerald", "#14594D")], "silk",
     "A flared anarkali in a lustrous silk blend, finished with a zari-embroidered hem and neckline. Made for festive evenings."),
    ("womens-ethnic", "Cotton Straight Kurta Set", "kurta", "#1F6F78", "solid", "#F2A900", 3499, 2499, APPAREL, [("Peacock", "#1F6F78"), ("Mustard", "#C98A12")], "cotton",
     "A straight-cut cotton kurta with matching trousers, block-print border and side slits for easy movement."),
    ("womens-ethnic", "Chanderi Festive Kurta", "kurta", "#D48A1C", "solid", "#7A1F3D", 4999, 3799, APPAREL, [("Marigold", "#D48A1C"), ("Rose", "#B4245D")], "silk",
     "Lightweight Chanderi with a subtle sheen, a contrast embroidered border and three-quarter sleeves."),
    ("womens-knitwear", "Ribbed Merino Cardigan", "sweater", "#B08968", "knit", "#F1EEE8", 4499, 3299, APPAREL, [("Camel", "#B08968"), ("Ink", "#232A3B")], "knit",
     "Fine-gauge merino in an all-over rib, with horn-effect buttons. A layer you will reach for all winter."),
    ("womens-knitwear", "Chunky Turtleneck Sweater", "sweater", "#EDE6D6", "knit", "#B9B1A2", 3999, 2899, APPAREL, [("Cream", "#EDE6D6"), ("Dusty Rose", "#C99AA0")], "knit",
     "A generous roll-neck knit with dropped shoulders and a soft, brushed handle."),
    ("womens-knitwear", "Fine-Knit Polo Sweater", "sweater", "#5B6C5D", "knit", "#EDE6D6", 3499, 2599, APPAREL, [("Sage", "#5B6C5D"), ("Black", "#18181B")], "knit",
     "A lightweight knitted polo with an open collar — neat enough for the office, relaxed enough for the weekend."),
    ("womens-blazers", "Double-Breasted Wool Blazer", "blazer", "#2B2F3A", "solid", "#C9A227", 7999, 5999, APPAREL, [("Charcoal", "#2B2F3A"), ("Camel", "#B08968")], "wool",
     "Sharp shoulders, peak lapels and a slightly longer line in a soft wool blend. Fully lined."),
    ("womens-blazers", "Checked Single-Button Blazer", "blazer", "#8C7B6B", "checks", "#2B2F3A", 6999, 5299, APPAREL, [("Taupe Check", "#8C7B6B"), ("Grey Check", "#6B7280")], "wool",
     "A heritage check in a modern cut: single button, gently nipped waist and flap pockets."),
    ("womens-blazers", "Cropped Linen Blazer", "blazer", "#E9E2D0", "solid", "#B08968", 5999, 4499, APPAREL, [("Ecru", "#E9E2D0"), ("Terracotta", "#B5542B")], "linen",
     "A cropped, boxy blazer in breathable linen. Unlined for summer and finished with patch pockets."),
    ("womens-skirts", "A-Line Denim Skirt", "skirt", "#3B5171", "denim", "#C2A878", 2499, 1899, APPAREL, [("Indigo", "#3B5171"), ("Washed Black", "#33363D")], "denim",
     "A knee-length A-line in sturdy stretch denim, with a button front and classic five-pocket styling."),
    ("womens-skirts", "Satin Bias Midi Skirt", "skirt", "#B4245D", "solid", "#F3D9C6", 2999, 2199, APPAREL, [("Fuchsia", "#B4245D"), ("Olive", "#5B6C5D")], "silk",
     "Cut on the bias so it drapes and swings. An elasticated waist keeps it comfortable all day."),
    ("womens-skirts", "Printed Cotton Wrap Skirt", "skirt", "#D48A1C", "dots", "#7A1F3D", 2299, 1699, APPAREL, [("Marigold", "#D48A1C"), ("Indigo", "#31506E")], "cotton",
     "Hand-block-inspired print on crisp cotton, with a wrap front and a tie at the side."),
    ("womens-activewear", "Seamless Sports Tank", "tank", "#1F6F78", "solid", "#F2A900", 1499, 1099, APPAREL, [("Teal", "#1F6F78"), ("Black", "#18181B")], "active",
     "A seamless, quick-dry tank with a racer back and light support. Moves with you through every session."),
    ("womens-activewear", "Tapered Training Joggers", "trousers", "#2B2F3A", "solid", "#B4245D", 2299, 1699, APPAREL, [("Graphite", "#2B2F3A"), ("Plum", "#5A2A4E")], "active",
     "Soft-touch joggers with a tapered leg, zip pockets and a wide waistband that stays put."),
    ("womens-activewear", "Zip-Front Training Jacket", "jacket", "#B4245D", "solid", "#F1EEE8", 3299, 2499, APPAREL, [("Berry", "#B4245D"), ("Slate", "#2F3E46")], "active",
     "A close-fitting layer with thumb loops, a high collar and breathable panels for warm-ups and cool-downs."),
    ("footwear", "Suede Chelsea Boots", "shoe", "#7B5B3A", "solid", "#2B2F3A", 7999, 5999, SHOES, [("Tobacco", "#7B5B3A"), ("Black", "#18181B")], "leather",
     "Classic Chelsea boots in soft suede with elastic side panels, a pull tab and a cushioned leather insole."),
    ("bags", "Canvas Weekend Tote", "bag", "#C2A878", "solid", "#7B5B3A", 3499, 2499, ONE, [("Sand", "#C2A878"), ("Navy", "#1F2A44")], "canvas",
     "A roomy tote in heavyweight canvas with leather handles, an inner zip pocket and a magnetic closure."),
    ("bags", "Mini Crossbody Bag", "bag", "#7A1F3D", "solid", "#C9A227", 4999, 3799, ONE, [("Burgundy", "#7A1F3D"), ("Tan", "#B08968")], "leather",
     "A compact crossbody in pebbled leather with an adjustable strap and a gold-tone clasp."),
    ("jewellery", "Gold-Plated Jhumka Earrings", "earrings", "#D4A017", "solid", "#B4245D", 2499, 1799, ONE, [("Gold", "#D4A017")], "metal",
     "Traditional jhumkas in gold-plated brass with a ruby-toned centre stone. Light enough to wear all evening."),
]

CATEGORY_ART = {
    "men": ("shirt", "#2B3A55"), "women": ("dress", "#7A1F3D"), "footwear": ("shoe", "#4A3B2E"), "bags": ("bag", "#5A3A2E"),
    "jewellery": ("necklace", "#3A2E4A"), "accessories": ("sunglasses", "#2E3A3A"),
    "mens-shirts": ("shirt", "#31506E"), "mens-tees": ("tee", "#35523E"), "mens-sweats": ("hoodie", "#6B3A2A"),
    "mens-outerwear": ("jacket", "#2F3E46"), "mens-bottoms": ("trousers", "#4A4234"),
    "womens-dresses": ("dress", "#8A3B4B"), "womens-ethnic": ("kurta", "#14594D"), "womens-knitwear": ("sweater", "#6B5540"),
    "womens-blazers": ("blazer", "#2B2F3A"), "womens-skirts": ("skirt", "#7A3558"), "womens-activewear": ("tank", "#1F5560"),
}
CATEGORY_CARE = {
    "mens-shirts": "cotton", "mens-tees": "cotton", "mens-sweats": "cotton", "mens-outerwear": "wool", "mens-bottoms": "denim",
    "womens-dresses": "silk", "womens-ethnic": "cotton", "womens-knitwear": "knit", "womens-blazers": "linen",
    "womens-skirts": "silk", "womens-activewear": "active", "footwear": "leather", "bags": "leather",
    "jewellery": "metal", "accessories": "leather",
}

DIWALI_EDIT = [
    "silk-blend-anarkali-kurta", "chanderi-festive-kurta", "cotton-straight-kurta-set", "floral-embroidered-kurti",
    "gold-plated-jhumka-earrings", "petite-diamond-pendant-necklace", "brushed-gold-band-ring", "chunky-curb-link-bracelet",
    "draped-silk-maxi-dress", "satin-slip-dress", "mini-crossbody-bag", "structured-leather-top-handle-bag",
]
WORKWEAR_EDIT = [
    "double-breasted-wool-blazer", "checked-single-button-blazer", "oxford-button-down-shirt", "crisp-cotton-formal-shirt",
    "slim-chino-trousers", "tailored-linen-blazer", "leather-wingtip-brogues", "minimalist-leather-strap-watch",
]

PAGES = {
    "about": ("About Us", "<h2>Clothing with a story</h2><p>We started as a family-run shop and grew into an online store for men, women and children across India. We still choose every piece the same way: good fabric, honest pricing, and styles you will wear for years.</p><h3>What we stand for</h3><ul><li><strong>Quality first.</strong> We work directly with makers we know and check every batch ourselves.</li><li><strong>Fair prices.</strong> No inflated MRPs — the price you see is the price we believe is right.</li><li><strong>Service that answers.</strong> Real people reply to your messages, usually within a working day.</li></ul><h3>Retail and wholesale</h3><p>Alongside our online store we supply shops and boutiques. If you buy in bulk, see our <a href=\"/wholesale\">wholesale page</a>.</p>"),
    "contact": ("Contact Us", "<p>We are happy to help with orders, sizing, returns or anything else. Use the form on this page, or reach us with the details shown here. We reply to every message, usually within one working day.</p>"),
    "faq": ("Frequently Asked Questions", "<p>Quick answers to the questions we hear most. If yours is not here, <a href=\"/contact\">send us a message</a>.</p>"),
    "shipping": ("Shipping Policy", "<h2>Where we deliver</h2><p>We deliver across India through our courier partners.</p><h2>Delivery times</h2><ul><li>Metro cities: usually 3–5 working days.</li><li>Rest of India: usually 4–7 working days.</li></ul><p>Orders are packed within one working day. Times are estimates and can be longer during festivals and bad weather.</p><h2>Shipping charges</h2><p>Shipping is free above the amount shown at checkout; below it a flat fee is added. The exact charge is always shown in your cart before you pay.</p><h2>Tracking your order</h2><p>Sign in and open <a href=\"/track-order\">Track Order</a> to see where your parcel is.</p>"),
    "returns": ("Returns & Exchanges", "<h2>Easy returns</h2><p>If something is not right, you can ask for a return from your account within the return window shown on your order.</p><h3>How it works</h3><ol><li>Sign in, open the order under My Orders, and choose <strong>Return an item</strong>.</li><li>Pack the item unused, with its tags, in the original packaging.</li><li>Once we receive and check it, your refund is sent to the original payment method. Cash-on-delivery orders are refunded by bank transfer.</li></ol><h3>What cannot be returned</h3><ul><li>Items that have been worn, washed or altered.</li><li>Innerwear and jewellery, for hygiene reasons.</li></ul>"),
    "privacy": ("Privacy Policy", "<h2>What we collect</h2><p>When you create an account or place an order we store your name, email address, phone number and delivery addresses, and the details of your orders.</p><h2>How we use it</h2><ul><li>To deliver your orders and keep you informed about them.</li><li>To answer your questions.</li><li>To send offers, only if you have subscribed to our newsletter.</li></ul><h2>Payments</h2><p>Online payments are handled by our payment partner. We never see or store your card or UPI details.</p><h2>Your choices</h2><p>You can ask us to correct or delete your account details at any time through the <a href=\"/contact\">contact page</a>.</p><p><em>This is sample text. Have it reviewed before you rely on it.</em></p>"),
    "terms": ("Terms & Conditions", "<h2>Using this store</h2><p>By placing an order you agree to these terms.</p><h2>Prices and availability</h2><p>Prices are in Indian Rupees and include applicable taxes unless stated. We may correct an obvious pricing error and will tell you before your order is sent.</p><h2>Orders</h2><p>An order is accepted when we confirm it. We may cancel an order if an item is out of stock, in which case any payment is refunded in full.</p><h2>Returns</h2><p>See our <a href=\"/returns\">returns policy</a>.</p><p><em>This is sample text. Have it reviewed before you rely on it.</em></p>"),
}
FAQ = [
    ("How long does delivery take?", "Metro cities usually receive orders in 3–5 working days and the rest of India in 4–7. Orders are packed within one working day."),
    ("How much is shipping?", "Shipping is free above the amount shown in your cart. Below that, a flat fee is added — you will always see the exact charge before you pay."),
    ("Do you offer cash on delivery?", "Yes. Choose Cash on Delivery at checkout and pay when your order arrives."),
    ("Which payment methods do you accept?", "Cash on delivery, and online payment by UPI, cards and net banking where it is shown at checkout."),
    ("How do I return an item?", "Sign in, open the order under My Orders and choose Return an item. The return window is shown on the order."),
    ("When will I get my refund?", "Refunds are sent once we have received and checked the item. Online payments go back to the original method; cash-on-delivery orders are refunded by bank transfer."),
    ("How do I find my size?", "Each product lists the sizes it comes in. If you are between sizes we suggest the larger one; you can exchange if it does not fit."),
    ("Can I cancel my order?", "Yes, from your account, any time before the order is packed. After that you can return it once it arrives."),
    ("Do you sell wholesale?", "Yes. Tell us about your shop on the Wholesale page and we will get in touch with pricing."),
]
CUSTOMERS = [
    ("Ananya Sharma", "ananya", "Patna", "Bihar", "800001", "14 Boring Road"),
    ("Rohan Mehta", "rohan", "Mumbai", "Maharashtra", "400050", "22 Hill Road, Bandra West"),
    ("Priya Nair", "priya", "Bengaluru", "Karnataka", "560034", "7 1st Block, Koramangala"),
    ("Arjun Verma", "arjun", "New Delhi", "Delhi", "110017", "B-12 Malviya Nagar"),
    ("Kavya Reddy", "kavya", "Hyderabad", "Telangana", "500081", "301 Madhapur Main Road"),
]
# customer index, [product slugs], final status, review?, return?
ORDERS = [
    (0, ["floral-wrap-dress", "gold-plated-jhumka-earrings"], "delivered", (5, "Lovely fabric", "Fits perfectly and the print is even nicer in person."), None),
    (0, ["ribbed-merino-cardigan"], "shipped", None, None),
    (1, ["oxford-button-down-shirt", "slim-chino-trousers"], "delivered", (4, "Good everyday shirt", "Nice weight to the cotton. Sleeves are a touch long on me."), "size_issue"),
    (1, ["quilted-puffer-jacket"], "pending", None, None),
    (2, ["cotton-straight-kurta-set"], "delivered", (5, "Beautiful colour", "Comfortable enough to wear all day at a family function."), None),
    (2, ["canvas-weekend-tote", "seamless-sports-tank"], "out_for_delivery", None, None),
    (3, ["suede-chelsea-boots"], "packed", None, None),
    (3, ["striped-crew-neck-t-shirt", "relaxed-linen-trousers"], "cancelled", None, None),
    (4, ["satin-bias-midi-skirt", "chunky-turtleneck-sweater"], "confirmed", None, None),
    (4, ["mini-crossbody-bag"], "pending", None, None),
]
STATUS_PATH = ["confirmed", "packed", "shipped", "out_for_delivery", "delivered"]


def slugify(name):
    out = "".join(c.lower() if c.isalnum() else "-" for c in name)
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")


class Api:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.http = requests.Session()
        self.token = None
        self.manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
        # False for a throwaway environment: its uploads are not the demo
        # assets the repository documents.
        self.keep_manifest = True

    def call(self, method, path, token=None, ok=(200, 201), **kw):
        headers = kw.pop("headers", {})
        token = token or self.token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if path.startswith("/admin/"):
            headers["X-Demo-Content"] = "1"
        resp = self.http.request(method, f"{self.base}/api{path}", headers=headers, timeout=120, **kw)
        if resp.status_code not in ok:
            raise SystemExit(f"{method} {path} -> {resp.status_code}: {resp.text[:300]}")
        return resp.json() if resp.content and "json" in resp.headers.get("content-type", "") else None

    def get(self, path, **kw):
        return self.call("GET", path, **kw)

    def post(self, path, json=None, **kw):
        return self.call("POST", path, json=json, **kw)

    def put(self, path, json=None, **kw):
        return self.call("PUT", path, json=json, **kw)

    def upload(self, image, name, used_for, source=ORIGINAL, alt=None):
        buf = io.BytesIO()
        image.convert("RGB").save(buf, "WEBP", quality=86, method=4)
        buf.seek(0)
        asset = self.call("POST", "/admin/media", files={"file": (f"{name}.webp", buf, "image/webp")},
                          data={"alt_text": alt or used_for, "source_note": source})
        self.manifest.append({"file": f"{name}.webp", "url": asset["url"], "used_for": used_for, "source": source})
        return asset["url"]

    def save_manifest(self):
        if self.keep_manifest:
            MANIFEST.write_text(json.dumps(self.manifest, indent=1))


def login(api, email, password):
    body = api.post("/admin/auth/login", json={"email": email, "password": password})
    api.token = body["access_token"]
    if body["admin"]["role"] != "master":
        raise SystemExit("Sign in as an Owner: only the Owner can use demo mode.")
    print(f"signed in as {email} (Owner)")


def all_products(api):
    products, page = [], 1
    while True:
        body = api.get(f"/admin/products?per_page=100&page={page}")
        products += body["products"]
        if page >= body.get("pages", 1):
            return {p["slug"]: p for p in products}
        page += 1


def flat_categories(api):
    out = {}

    def walk(nodes):
        for node in nodes:
            out[node["slug"]] = node
            walk(node.get("children", []))
    walk(api.get("/admin/categories")["categories"])
    return out


# ── steps ────────────────────────────────────────────────────

def step_tag(api):
    """What was in the store before demo mode existed is sample content too."""
    for kind in ("products", "categories", "hero_slides", "promo_banners", "announcements", "testimonials",
                 "feature_cards", "coupons", "offers"):
        changed = api.post("/admin/demo/tag", json={"kind": kind, "all": True, "is_demo": True})["changed"]
        print(f"  tagged {changed} existing {kind}")
    users = api.get("/admin/users?per_page=100")["users"]
    test_ids = [u["id"] for u in users if u["email"].endswith(("@local.test", "@example.com"))]
    if test_ids:
        api.post("/admin/demo/tag", json={"kind": "customers", "ids": test_ids, "is_demo": True})
        print(f"  tagged {len(test_ids)} test customers")


def step_settings(api):
    share = api.upload(art.share_card("AANGA", "Premium fashion, delivered across India"), "share-card", "Store settings: default share image")
    api.put("/admin/settings", json={"values": {
        "store_name": "AANGA",
        "store_tagline": "Premium fashion for men, women and kids — retail and wholesale.",
        "store_email": "hello@example.com",
        "store_phone": "+91 98000 00000",
        "store_address": "Sample Address Line, Boring Road, Patna, Bihar 800001",
        "whatsapp_number": "+91 98000 00000",
        "instagram_url": "https://www.instagram.com/",
        "facebook_url": "https://www.facebook.com/",
        "youtube_url": "https://www.youtube.com/",
        "delivery_charge": "49", "free_shipping_threshold": "999", "cod_enabled": True, "return_window_days": "7",
        "seo_title": "AANGA — Premium Fashion for Men, Women & Kids",
        "seo_description": "Curated clothing, footwear, bags and jewellery with fast delivery across India. Free shipping over ₹999 and easy 7-day returns.",
        "seo_share_image": share,
    }})
    print("  store settings saved (contact details and social links are placeholders; GSTIN left empty)")


def step_categories(api):
    for slug, node in flat_categories(api).items():
        if node.get("image_url") or slug not in CATEGORY_ART:
            continue
        kind, colour = CATEGORY_ART[slug]
        url = api.upload(art.category_tile(kind, colour), f"category-{slug}", f"Category tile: {node['name']}")
        api.put(f"/admin/categories/{node['id']}", json={
            "name": node["name"], "slug": node["slug"], "description": node.get("description"), "image_url": url,
            "parent_id": node.get("parent_id"), "sort_order": node.get("sort_order", 0), "is_active": node["is_active"],
        })
        print(f"  tile for {node['name']}")


def step_products(api):
    categories = flat_categories(api)
    existing = all_products(api)
    for index, (cat, name, kind, colour, pattern, accent, mrp, price, sizes, colours, fabric, description) in enumerate(NEW_PRODUCTS):
        slug = slugify(name)
        if slug in existing:
            continue
        product = api.post("/admin/products", json={
            "category_id": categories[cat]["id"], "name": name, "slug": slug, "description": description,
            "mrp": mrp, "selling_price": price, "care_details": CARE[fabric], "is_active": True,
            "is_featured": index % 4 == 0,
            "badge_label": "New" if index % 5 == 0 else None,
            "meta_title": f"{name} — Buy Online",
            "meta_description": description[:180],
        })
        swatches = [hex_ for _name, hex_ in colours]
        for view_index, view in enumerate(("front", "detail", "flat")):
            image = art.product_image(kind, colour, view, pattern, accent, swatches, seed=index)
            url = api.upload(image, f"{slug}-{view}", f"Product: {name} ({view})", alt=f"{name} — {view} view")
            api.post(f"/admin/products/{product['id']}/images", json={"image_url": url, "sort_order": view_index, "is_primary": view_index == 0})
        for colour_name, colour_hex in colours:
            for size_index, size in enumerate(sizes):
                api.post(f"/admin/products/{product['id']}/variants", json={
                    "size": size, "color_name": colour_name, "color_hex": colour_hex,
                    "stock_qty": 12 + (index * 7 + size_index * 5) % 30,
                    "sku": f"{slug[:18].upper().replace('-', '')}-{colour_name[:3].upper()}-{size.replace(' ', '')}",
                })
        print(f"  product {name}")


def step_extras(api):
    """Give the sample catalogue that came with the project care details, search
    text and two close-up pictures each."""
    categories = {c["id"]: slug for slug, c in flat_categories(api).items()}
    new_slugs = {slugify(p[1]) for p in NEW_PRODUCTS}
    for slug, product in all_products(api).items():
        if slug in new_slugs or not product["is_active"]:
            continue
        detail = api.get(f"/admin/products/{product['id']}")
        if not detail.get("care_details"):
            api.put(f"/admin/products/{product['id']}", json={
                "category_id": detail["category_id"], "name": detail["name"], "slug": detail["slug"],
                "description": detail.get("description"), "mrp": detail["mrp"], "selling_price": detail["selling_price"],
                "badge_label": detail.get("badge_label"), "badge_class": detail.get("badge_class"),
                "is_active": detail["is_active"], "is_featured": detail["is_featured"],
                "care_details": CARE[CATEGORY_CARE.get(categories.get(detail["category_id"]), "cotton")],
                "meta_title": f"{detail['name']} — Buy Online",
                "meta_description": (detail.get("description") or detail["name"])[:180],
            })
        images = detail.get("images", [])
        if len(images) != 1:
            continue
        src = images[0]["image_url"]
        raw = requests.get(src if src.startswith("http") else api.base + src, timeout=60)
        if raw.status_code != 200:
            print(f"  could not read the picture of {detail['name']}; left with one image")
            continue
        source = Image.open(io.BytesIO(raw.content)).convert("RGB")
        for n, (zoom, focus) in enumerate(((1.8, (.5, .40)), (2.4, (.5, .62))), start=1):
            url = api.upload(art.crop_detail(source, zoom, focus), f"{slug}-closeup-{n}", f"Product: {detail['name']} (close-up {n})",
                             source=STITCH, alt=f"{detail['name']} — close-up")
            api.post(f"/admin/products/{product['id']}/images", json={"image_url": url, "sort_order": n, "is_primary": False})
        print(f"  close-ups for {detail['name']}")


def step_content(api):
    banners = api.get("/admin/banners?per_page=50")["banners"]
    if not any(b["title"].startswith("The New Season") for b in banners):
        for b in banners:                       # the single slide the project started with steps aside
            api.put(f"/admin/banners/{b['id']}", json={**{k: b.get(k) for k in (
                "title", "subtitle", "description", "image_url", "mobile_image_url", "link_url", "link_text",
                "secondary_link_url", "secondary_link_text", "pill_label", "pill_value", "chip_value", "chip_label")},
                "sort_order": 9, "is_active": False})
        slides = [
            ("new-season", "The New Season\nHas Arrived", "New arrivals", "Fresh colours, lighter fabrics and easy shapes for the months ahead.", "Shop new in", "/shop", "This season", "Autumn Edit"),
            ("workwear", "Workwear,\nSharpened", "The Workwear Edit", "Blazers, shirts and trousers that take you from the first meeting to dinner.", "Shop workwear", "/collections/workwear-edit", "Tailoring", "From ₹1,799"),
            ("weekend", "Made for\nthe Weekend", "Off duty", "Soft hoodies, relaxed denim and tees you will live in.", "Shop casual", "/shop?category=men", "Free shipping", "Over ₹999"),
        ]
        for order, (theme, title, subtitle, text, cta, link, pill_label, pill_value) in enumerate(slides):
            url = api.upload(art.hero_scene(theme, seed=order + 1), f"hero-{theme}", f"Hero slide: {title.replace(chr(10), ' ')}")
            api.post("/admin/banners", json={
                "title": title, "subtitle": subtitle, "description": text, "image_url": url, "link_text": cta, "link_url": link,
                "secondary_link_text": "View offers", "secondary_link_url": "/offers",
                "pill_label": pill_label, "pill_value": pill_value, "sort_order": order, "is_active": True})
            print(f"  hero slide {theme}")

    promos = api.get("/admin/promo-banners?per_page=50")["promo_banners"]
    for promo in promos:
        if not promo.get("image_url"):
            url = api.upload(art.promo_scene(), "promo-everyday", f"Promo banner: {promo['title']}")
            api.put(f"/admin/promo-banners/{promo['id']}", json={**{k: promo.get(k) for k in (
                "title", "subtitle", "description", "badge_text", "link_url", "link_text", "items", "sort_order", "is_active")}, "image_url": url})
            print("  picture for the promo banner")

    # A database built from schema.sql alone has none of the home page's
    # supporting content, so make it. (An older database got these rows from
    # the one-off CMS migrations and they are left as they are.)
    if not api.get("/admin/announcements?per_page=50")["announcements"]:
        api.post("/admin/announcements", json={
            "text": "New season, new styles", "highlight_text": "Free shipping on orders above ₹999",
            "link_url": "/shop", "link_text": "Shop now", "is_active": True})
        print("  announcement")
    if not promos:
        url = api.upload(art.promo_scene(), "promo-everyday", "Promo banner: End of season sale")
        api.post("/admin/promo-banners", json={
            "title": "End of Season Sale", "subtitle": "Sale", "badge_text": "Limited time",
            "description": "Selected styles at up to 40% off while stocks last.", "image_url": url,
            "link_url": "/offers", "link_text": "Shop the sale", "is_active": True,
            "items": [{"pct": "40%", "label": "On jackets"}, {"pct": "30%", "label": "On knitwear"},
                      {"pct": "25%", "label": "On denim"}, {"pct": "20%", "label": "On accessories"}]})
        print("  promo banner")
    if not api.get("/admin/features?per_page=50")["features"]:
        for order, (icon, title, text) in enumerate((
            ("shield-check", "Premium Quality", "Every piece is checked by hand. Good fabric, clean stitching, made to last."),
            ("truck", "Fast Delivery", "Delivered across India. Free shipping on orders above ₹999."),
            ("refresh", "Easy Returns", "Changed your mind? Return within 7 days of delivery."),
            ("headset", "Real Support", "Questions answered by real people, usually within a working day."),
        )):
            api.post("/admin/features", json={"icon": icon, "title": title, "description": text, "sort_order": order, "is_active": True})
        print("  4 feature cards")
    if not api.get("/admin/testimonials?per_page=50")["testimonials"]:
        for order, (name, place, rating, quote) in enumerate((
            ("Rahul Kumar", "Patna, Bihar", 5, "Ordered three shirts for a wedding. The fabric and the fit were far better than I expected at this price."),
            ("Priya Singh", "Muzaffarpur, Bihar", 5, "I run a small boutique and buy wholesale here. Fair pricing and something new every month."),
            ("Arjun Verma", "Ranchi, Jharkhand", 5, "The hoodie arrived in four days and has survived a winter of daily wear."),
            ("Neha Gupta", "Gaya, Bihar", 4, "Lovely quality. The size ran a little large for me, but the exchange was quick."),
            ("Sana Rizvi", "Lucknow, Uttar Pradesh", 5, "The festive kurta looked exactly like the picture. I have already ordered another colour."),
        )):
            api.post("/admin/testimonials", json={"name": name, "location": place, "rating": rating, "quote": quote, "sort_order": order, "is_active": True})
        print("  5 testimonials")

    palette = ["#7A1F3D", "#1F6F78", "#31506E", "#B5542B", "#5B6C5D", "#6B5540"]
    for index, t in enumerate(api.get("/admin/testimonials?per_page=50")["testimonials"]):
        if t.get("avatar_url"):
            continue
        initials = "".join(part[0] for part in t["name"].split()[:2]).upper()
        url = api.upload(art.avatar(initials, palette[index % len(palette)]), f"avatar-{slugify(t['name'])}", f"Testimonial photo: {t['name']} (initials)")
        api.put(f"/admin/testimonials/{t['id']}", json={
            "name": t["name"], "location": t.get("location"), "rating": t["rating"], "quote": t["quote"],
            "avatar_url": url, "sort_order": t.get("sort_order", 0), "is_active": t["is_active"]})
    print("  testimonial avatars done")


def step_pages(api):
    for slug, (title, html) in PAGES.items():
        page = api.get(f"/admin/pages/{slug}")
        if page["body_html"]:
            continue
        api.put(f"/admin/pages/{slug}", json={
            "title": title, "body_html": html, "meta_title": title,
            "meta_description": f"{title} — everything you need to know before you order."})
        print(f"  page {slug}")
    if not api.get("/admin/faq")["items"]:
        for question, answer in FAQ:
            api.post("/admin/faq", json={"question": question, "answer": answer})
        print(f"  {len(FAQ)} FAQ entries")


def step_collections(api):
    products = all_products(api)
    existing = {c["slug"]: c for c in api.get("/admin/collections")["collections"]}
    wanted = [
        ("Diwali Edit", "diwali-edit", "Festive kurtas, jewellery and gifts, chosen for the season of lights.", DIWALI_EDIT, ("kurta", "#7A1F3D")),
        ("Workwear Edit", "workwear-edit", "Sharp tailoring and smart essentials for the working week.", WORKWEAR_EDIT, ("blazer", "#2B2F3A")),
    ]
    for name, slug, description, slugs, (kind, colour) in wanted:
        if slug in existing:
            continue
        missing = [s for s in slugs if s not in products]
        if missing:
            raise SystemExit(f"collection {name}: products not found: {missing} (run the products step first)")
        image = api.upload(art.category_tile(kind, colour), f"collection-{slug}", f"Collection picture: {name}")
        api.post("/admin/collections", json={
            "name": name, "slug": slug, "description": description, "image_url": image,
            "product_ids": [products[s]["id"] for s in slugs],
            "meta_title": f"{name} — Shop the Collection", "meta_description": description})
        print(f"  collection {name} ({len(slugs)} products)")


def step_staff(api, logins):
    existing = {s["email"] for s in api.get("/admin/staff")["staff"]}
    for name, email, role in (("Meera Iyer", "demo.manager@example.com", "manager"), ("Vikram Singh", "demo.staff@example.com", "staff")):
        if email in existing:
            continue
        body = api.post("/admin/staff", json={"full_name": name, "email": email, "role": role})
        logins[role] = {"email": email, "password": body["temporary_password"]}
        print(f"  staff {name} ({role})")


def step_customers(api, logins):
    products = all_products(api)
    users = {u["email"]: u for u in api.get("/admin/users?per_page=100")["users"]}
    tokens, addresses = {}, {}
    people = CUSTOMERS + [("Demo Shopper", "shopper", "Patna", "Bihar", "800001", "5 Fraser Road")]
    for index, (name, key, city, state, pin, line1) in enumerate(people):
        email = f"demo.{key}@example.com"
        if email in users:
            continue
        password = "Demo-" + secrets.token_urlsafe(9)
        body = api.post("/auth/register", json={"full_name": name, "email": email, "password": password})
        tokens[index] = body["access_token"]
        address = api.post("/addresses", token=tokens[index], json={
            "label": "Home", "full_name": name, "phone": f"+9198000000{index + 10}", "line1": line1,
            "city": city, "state": state, "pin_code": pin, "is_default": True})
        addresses[index] = address["id"]
        api.post("/admin/demo/tag", json={"kind": "customers", "ids": [body["user"]["id"]], "is_demo": True})
        if key == "shopper":
            logins["shopper"] = {"email": email, "password": password}
        print(f"  customer {name}")

    for customer, slugs, status, review, returned in ORDERS:
        if customer not in tokens:
            continue                              # this customer already existed: their orders were made earlier
        token = tokens[customer]
        for slug in slugs:
            variant = next(v for v in api.get(f"/products/{slug}", token=token)["variants"] if v["stock_qty"] > 0)
            api.post("/cart/items", token=token, json={"variant_id": variant["id"], "quantity": 1})
        placed = api.post("/orders", token=token, json={"address_id": addresses[customer], "payment_method": "cod"},
                          headers={"Idempotency-Key": secrets.token_hex(12)})
        order_id = placed["order_id"]
        if status == "cancelled":
            api.post(f"/orders/{order_id}/cancel", token=token)
        elif status != "pending":
            for step in STATUS_PATH[: STATUS_PATH.index(status) + 1]:
                api.call("PATCH", f"/admin/orders/{order_id}/status", json={"status": step})
        if review:
            rating, title, body = review
            api.post("/reviews", token=token, json={"product_id": products[slugs[0]]["id"], "rating": rating, "title": title, "body": body})
        if returned:
            item = api.get(f"/orders/{order_id}", token=token)["items"][-1]
            api.post("/returns", token=token, json={"order_item_id": item["id"], "reason": returned})
        print(f"  order {placed['order_number']} -> {status}{' + review' if review else ''}{' + return' if returned else ''}")


def step_campaign(api):
    """The Diwali showcase: one campaign that carries everything festive."""
    campaigns = api.get("/admin/campaigns")["campaigns"]
    if any(c["name"] == "Diwali Festive Sale" for c in campaigns):
        print("  Diwali Festive Sale already exists")
        return
    collection = next(c for c in api.get("/admin/collections")["collections"] if c["slug"] == "diwali-edit")
    now = datetime.now(IST)
    coupons = {c["code"]: c for c in api.get("/admin/coupons?per_page=100")["coupons"]}
    for code, kind, value, minimum, limit, note in (
        ("DIWALI10", "percentage", 10, 1499, 500, "Diwali: 10% off orders above ₹1,499"),
        ("FESTIVE500", "flat", 500, 4999, 200, "Diwali: ₹500 off orders above ₹4,999"),
    ):
        if code not in coupons:
            coupons[code] = api.post("/admin/coupons", json={
                "code": code, "description": note, "discount_type": kind, "discount_value": value,
                "min_order_value": minimum, "usage_limit": limit, "is_active": True})
    campaign = api.post("/admin/campaigns", json={
        "name": "Diwali Festive Sale",
        "starts_at": now.isoformat(timespec="seconds"),
        "ends_at": (now + timedelta(days=21)).isoformat(timespec="seconds"),
        "announcement_text": "Happy Diwali!",
        "announcement_highlight": "20% off the Diwali Edit · Extra 10% with DIWALI10",
        "announcement_link_text": "Shop now", "announcement_link_url": "/collections/diwali-edit",
        "collection_id": collection["id"], "sale_percent": 20,
        "decoration_enabled": True, "accent_preset": "marigold", "show_countdown": True,
        "coupon_ids": [coupons["DIWALI10"]["id"], coupons["FESTIVE500"]["id"]],
    })
    slides = [
        ("lights", "Light Up\nYour Diwali", "Diwali Festive Sale", "Festive kurtas, jewellery and gifts — 20% off the whole Diwali Edit.", "Lights", "20%", "Off the Diwali Edit"),
        ("diyas", "Dressed for\nthe Festival", "The Diwali Edit", "Silks, Chanderi and gold-toned jewellery for every celebration.", "Diyas", "DIWALI10", "Extra 10% off"),
        ("gifting", "Gifts They\nWill Treasure", "Festive gifting", "Bags, jewellery and keepsakes, ready to wrap. ₹500 off above ₹4,999 with FESTIVE500.", "Gifting", "₹500", "Off with FESTIVE500"),
    ]
    for order, (theme, title, subtitle, text, alt, chip_value, chip_label) in enumerate(slides):
        url = api.upload(art.hero_scene(theme, seed=order + 11), f"diwali-hero-{theme}", f"Diwali hero slide: {alt}", alt=f"Diwali artwork: {alt.lower()}")
        api.post("/admin/banners", json={
            "title": title, "subtitle": subtitle, "description": text, "image_url": url,
            "link_text": "Shop the Diwali Edit", "link_url": "/collections/diwali-edit",
            "chip_value": chip_value, "chip_label": chip_label,
            "campaign_id": campaign["id"], "sort_order": order, "is_active": True})
    api.post("/admin/promo-banners", json={
        "title": "The Festival of Lights Sale", "subtitle": "Diwali", "badge_text": "Ends soon",
        "description": "Everything in the Diwali Edit is 20% off, with free shipping over ₹999.",
        "link_text": "Shop the Diwali Edit", "link_url": "/collections/diwali-edit",
        "items": [{"pct": "20%", "label": "Off the Diwali Edit"}, {"pct": "10%", "label": "Extra with DIWALI10"},
                  {"pct": "₹500", "label": "Off above ₹4,999"}, {"pct": "Free", "label": "Shipping over ₹999"}],
        "campaign_id": campaign["id"], "is_active": True})
    print(f"  Diwali Festive Sale is live until {(now + timedelta(days=21)).strftime('%d %b %Y, %H:%M')} IST")


def write_doc(api):
    by_source = {}
    for item in api.manifest:
        by_source.setdefault(item["source"], []).append(item)
    lines = [
        "# Demo assets",
        "",
        "Every picture used by the demo content, where it came from, and under what terms.",
        "This file is rewritten by `backend/db/demo/seed_demo.py` from what it uploaded.",
        "",
        "**No image was taken from a stock-photo site or from another brand's website.**",
        "",
        "| Source | Licence | Images |",
        "|---|---|---|",
        f"| Original artwork drawn by `backend/db/demo/make_art.py` (flat illustrations built from shapes with Pillow) | Original to this project; no third-party rights. Yours to use, change or delete. | {len(by_source.get(ORIGINAL, []))} |",
        f"| Close-ups cut from the product pictures that came with the project (the Stitch design export in the repository root) | Same rights as those pictures. They were supplied with the project, not sourced by this script — **confirm you may use them commercially, or replace them.** | {len(by_source.get(STITCH, []))} |",
        "| The 30 product pictures that came with the project (Stitch design export) | As above. Not uploaded by this script; listed here because the demo catalogue uses them. | 30 |",
        "",
        "All of these are tagged **Demo** in the admin's Media library, and each carries its source in the",
        "\"Source and licence\" field. \"Remove demo content\" deletes them with the rest of the demo data.",
        "",
        "## Every uploaded image",
        "",
        "| File | Used for | Source |",
        "|---|---|---|",
    ]
    for item in api.manifest:
        lines.append(f"| `{item['file']}` | {item['used_for']} | {'Original artwork' if item['source'] == ORIGINAL else 'Close-up of a supplied product picture'} |")
    DOC.write_text("\n".join(lines) + "\n", encoding="utf-8")


STEPS = ["tag", "settings", "categories", "products", "extras", "content", "pages", "collections", "staff", "customers", "campaign"]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--api", default="http://localhost:5000")
    parser.add_argument("--only", help="comma-separated steps: " + ", ".join(STEPS))
    parser.add_argument("--no-manifest", action="store_true", help="do not record uploads in assets_manifest.json or rewrite docs/DEMO_ASSETS.md (throwaway environments)")
    parser.add_argument("--secrets-out", help="write the generated demo logins to this JSON file (keep it out of git)")
    args = parser.parse_args()

    email, password = os.environ.get("DEMO_OWNER_EMAIL"), os.environ.get("DEMO_OWNER_PASSWORD")
    if not email or not password:
        from dotenv import load_dotenv
        load_dotenv(BACKEND / ".env")
        email, password = os.environ.get("ADMIN_EMAIL"), os.environ.get("ADMIN_PASSWORD")
    if not email or not password:
        raise SystemExit("Set DEMO_OWNER_EMAIL and DEMO_OWNER_PASSWORD (an Owner account).")

    api = Api(args.api)
    api.keep_manifest = not args.no_manifest
    login(api, email, password)
    logins = {}
    chosen = [s.strip() for s in args.only.split(",")] if args.only else STEPS
    for step in STEPS:
        if step not in chosen:
            continue
        print(f"[{step}]")
        function = globals()[f"step_{step}"]
        function(api, logins) if step in ("staff", "customers") else function(api)
        api.save_manifest()
    if api.keep_manifest:
        write_doc(api)
    if logins and args.secrets_out:
        path = pathlib.Path(args.secrets_out)
        known = json.loads(path.read_text()) if path.exists() else {}
        path.write_text(json.dumps({**known, **logins}, indent=1))
        print(f"demo logins written to {path}")
    elif logins:
        print("demo logins were generated but not saved (pass --secrets-out to keep them)")
    print("done")


if __name__ == "__main__":
    main()
