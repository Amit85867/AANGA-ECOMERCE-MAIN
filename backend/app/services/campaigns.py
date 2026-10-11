"""Campaigns: a scheduled festival or sale, and the prices that go with it.

A campaign is **live** while ``starts_at <= now < ends_at`` and nobody has
pressed "End now". Nothing switches it on or off: every request works out the
answer from the clock, so a campaign starts and reverts by itself at the set
times. Only one can be live at a time — overlapping schedules are refused when
they are saved.

While a campaign is live:

* its announcement, hero slides and promo banners replace the usual ones;
* products in its collection are sold at ``sale_percent`` off;
* its coupons can be used (and cannot be used at any other time).

**Preview** shows the storefront as it will look, to the admin who asked for
it, through a signed token sent in the ``X-Campaign-Preview`` header. Preview
changes what is *displayed* only: the cart and checkout always use the real
clock, so a preview link can never buy at sale prices early.
"""
from datetime import datetime, timezone

from flask import current_app, has_request_context, request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from app.extensions import db
from app.services import cache

PREVIEW_HEADER = "X-Campaign-Preview"
PREVIEW_MAX_AGE = 2 * 60 * 60

# Accent presets for the decoration layer. Each is an overlay on the frozen
# theme (white page, near-black text): `accent` is used as a background with
# `on_accent` text, `accent_text` as coloured text on white, and `on_dark` as
# coloured text on the black announcement bar. All pairs pass
# WCAG AA for normal text (4.5:1) — tests/test_campaigns.py checks the maths.
ACCENT_PRESETS = {
    "marigold": {"label": "Warm marigold", "accent": "#F2A900", "on_accent": "#1F1300", "accent_text": "#8A5200", "on_dark": "#F2A900"},
    "vermilion": {"label": "Vermilion red", "accent": "#B3261E", "on_accent": "#FFFFFF", "accent_text": "#B3261E", "on_dark": "#FF9A8F"},
    "peacock": {"label": "Peacock teal", "accent": "#00696B", "on_accent": "#FFFFFF", "accent_text": "#00696B", "on_dark": "#5FD4D6"},
    "rose": {"label": "Festive rose", "accent": "#B4245D", "on_accent": "#FFFFFF", "accent_text": "#B4245D", "on_dark": "#FF9BC0"},
}


def now_utc():
    return datetime.now(timezone.utc)


def _aware(value):
    return value if value is None or value.tzinfo else value.replace(tzinfo=timezone.utc)


def status_of(campaign, now=None):
    """"scheduled", "live" or "ended" for a Campaign row."""
    now = now or now_utc()
    if campaign.ended_at is not None or _aware(campaign.ends_at) <= now:
        return "ended"
    if _aware(campaign.starts_at) > now:
        return "scheduled"
    return "live"


def effective_end(campaign):
    return _aware(campaign.ended_at) or _aware(campaign.ends_at)


def find_overlap(starts_at, ends_at, exclude_id=None):
    """Another campaign whose time on the storefront overlaps this window."""
    from app.models.owner import Campaign

    for other in Campaign.query.all():
        if other.id == exclude_id:
            continue
        # One that was ended early only occupied the time up to that moment.
        if _aware(other.starts_at) < ends_at and starts_at < effective_end(other):
            return other
    return None


# ── What is live ─────────────────────────────────────────────

def _snapshot(campaign):
    """Everything the storefront needs about one campaign, as plain data."""
    from app.models.owner import CollectionProduct

    product_ids = []
    collection = campaign.collection
    if collection is not None:
        product_ids = [
            pid for (pid,) in db.session.query(CollectionProduct.product_id)
            .filter_by(collection_id=collection.id).all()
        ]
    preset = ACCENT_PRESETS.get(campaign.accent_preset, ACCENT_PRESETS["marigold"])
    return {
        "id": campaign.id,
        "name": campaign.name,
        "starts_at": _aware(campaign.starts_at).isoformat(),
        "ends_at": effective_end(campaign).isoformat(),
        "ended": campaign.ended_at is not None,
        "announcement": {
            "text": campaign.announcement_text,
            "highlight_text": campaign.announcement_highlight,
            "link_url": campaign.announcement_link_url,
            "link_text": campaign.announcement_link_text,
        } if campaign.announcement_text else None,
        "collection": {
            "id": collection.id, "slug": collection.slug, "name": collection.name,
        } if collection is not None and collection.is_active else None,
        "sale_percent": float(campaign.sale_percent) if campaign.sale_percent else None,
        "sale_product_ids": product_ids if campaign.sale_percent else [],
        "decoration": {
            "enabled": bool(campaign.decoration_enabled),
            "preset": campaign.accent_preset if campaign.accent_preset in ACCENT_PRESETS else "marigold",
            **{k: preset[k] for k in ("accent", "on_accent", "accent_text", "on_dark")},
        },
        "show_countdown": bool(campaign.show_countdown),
    }


def _schedule():
    """Every campaign that has not finished, soonest first. Cached, and dropped
    on any admin save like the rest of the catalogue cache."""
    from app.models.owner import Campaign

    def compute():
        rows = (
            Campaign.query.filter(Campaign.ended_at.is_(None), Campaign.ends_at > now_utc())
            .order_by(Campaign.starts_at).all()
        )
        return [_snapshot(c) for c in rows]

    return cache.get_or_set("campaign-schedule", 30, compute, scoped=False)


def _parse(iso):
    return datetime.fromisoformat(iso)


def _previewed():
    """The campaign named by a valid preview token on this request, if any."""
    if not has_request_context():
        return None
    token = request.headers.get(PREVIEW_HEADER)
    if not token:
        return None
    campaign_id = read_preview_token(token)
    if campaign_id is None:
        return None
    from app.models.owner import Campaign
    campaign = db.session.get(Campaign, campaign_id)
    return _snapshot(campaign) if campaign else None


def live(allow_preview=True):
    """The live campaign as a snapshot dict, or None.

    ``allow_preview=False`` is for anything that takes money: it ignores
    preview tokens.
    """
    if allow_preview:
        preview = _previewed()
        if preview is not None:
            return {**preview, "preview": True}
    now = now_utc()
    for item in _schedule():
        if _parse(item["starts_at"]) <= now < _parse(item["ends_at"]):
            return item
    return None


def next_change_at():
    """When the storefront should next look different: the live campaign's end
    or the next one's start. ISO string or None."""
    now = now_utc()
    times = []
    for item in _schedule():
        for key in ("starts_at", "ends_at"):
            moment = _parse(item[key])
            if moment > now:
                times.append(moment)
    return min(times).isoformat() if times else None


def cache_scope():
    """Folded into every catalogue cache key, so a cached response is never
    served across a campaign starting or ending."""
    try:
        current = live()
    except Exception:  # noqa: BLE001 - the cache must not break on a schema hiccup
        return "c0"
    if current is None:
        return "c0"
    return f"{'p' if current.get('preview') else 'c'}{current['id']}"


# ── Preview tokens ───────────────────────────────────────────

def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="campaign-preview")


def make_preview_token(campaign_id):
    return _serializer().dumps({"c": int(campaign_id)})


def read_preview_token(token):
    try:
        return int(_serializer().loads(token, max_age=PREVIEW_MAX_AGE)["c"])
    except (BadSignature, KeyError, TypeError, ValueError):
        return None


# ── Prices ───────────────────────────────────────────────────

def sale_price(base, percent):
    """``percent`` off ``base``, to the nearest whole rupee (never below ₹1)."""
    return float(max(1, round(float(base) * (100 - float(percent)) / 100)))


def unit_price(product, variant=None, campaign="live"):
    """What one unit costs right now.

    ``campaign`` is a snapshot from :func:`live`, None for "no campaign", or
    the default "live" to look it up without preview.
    """
    if campaign == "live":
        campaign = live(allow_preview=False)
    base = float(variant.price_override) if variant is not None and variant.price_override else float(product.selling_price)
    if campaign and campaign.get("sale_percent") and product.id in campaign["sale_product_ids"]:
        return sale_price(base, campaign["sale_percent"])
    return base


def apply_to_product(data, product_id, campaign):
    """Rewrite a product's serialised prices for the campaign sale, in place.

    ``data`` has mrp / selling_price / discount_percent and optionally
    variants with price_override.
    """
    data["on_sale"] = False
    if not campaign or not campaign.get("sale_percent") or product_id not in campaign["sale_product_ids"]:
        return data
    percent = campaign["sale_percent"]
    original = float(data["selling_price"])
    data["original_price"] = original
    data["selling_price"] = sale_price(original, percent)
    mrp = float(data.get("mrp") or 0)
    if mrp > 0:
        data["discount_percent"] = max(0, round((mrp - data["selling_price"]) / mrp * 100))
    data["on_sale"] = True
    data["sale_percent"] = percent
    data["sale_name"] = campaign["name"]
    for variant in data.get("variants") or []:
        if variant.get("price_override"):
            variant["price_override"] = sale_price(variant["price_override"], percent)
    return data


def reprice_cart(cart):
    """Bring every cart line to today's price, and drop a coupon that belongs
    to a campaign which is not live. Called before any total is computed, so a
    cart filled during a sale cannot be checked out at sale prices afterwards
    (or the other way round). Does not commit."""
    campaign = live(allow_preview=False)
    for line in cart.items:
        price = unit_price(line.variant.product, line.variant, campaign)
        if float(line.unit_price) != price:
            line.unit_price = price
    coupon = cart.coupon
    if coupon is not None and coupon.campaign_id and (not campaign or campaign["id"] != coupon.campaign_id):
        cart.coupon_id = None
        cart.coupon = None


def coupon_usable(coupon):
    """False for a campaign coupon outside its campaign."""
    if not coupon.campaign_id:
        return True
    campaign = live(allow_preview=False)
    return bool(campaign and campaign["id"] == coupon.campaign_id)
