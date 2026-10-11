"""Campaigns: the schedule decides what is live, with no switch to flip."""
from datetime import datetime, timedelta, timezone

import pytest

from app.extensions import db
from app.models.cms import Announcement, HeroBanner, PromoBanner
from app.models.engagement import Coupon
from app.models.enums import DiscountType
from app.models.owner import Campaign, Collection, CollectionProduct
from app.services import cache, campaigns
from app.services.order_service import create_order_from_cart
from tests.factories import make_address, make_cart, make_product, make_user
from tests.helpers import admin_headers, customer_headers

IST = timezone(timedelta(hours=5, minutes=30))


def now():
    return datetime.now(timezone.utc)


def ist(moment):
    return moment.astimezone(IST).isoformat()


def manager():
    return admin_headers(role="manager")


def _collection(products, name="Diwali Edit", slug="diwali-edit"):
    collection = Collection(name=name, slug=slug)
    collection.items = [CollectionProduct(product_id=p.id, sort_order=i) for i, p in enumerate(products)]
    db.session.add(collection)
    db.session.commit()
    return collection


def _payload(starts, ends, **extra):
    return {"name": "Diwali Festive Sale", "starts_at": ist(starts), "ends_at": ist(ends), **extra}


def _create(client, starts, ends, **extra):
    return client.post("/api/admin/campaigns", headers=manager(), json=_payload(starts, ends, **extra))


@pytest.fixture()
def clock(monkeypatch):
    """Move the campaign clock; the schedule cache is dropped with it."""
    def travel(moment):
        monkeypatch.setattr(campaigns, "now_utc", lambda: moment)
        cache.invalidate()
    return travel


def _live_name(client):
    cache_was = client.get("/api/content/layout").get_json()["campaign"]
    return cache_was["name"] if cache_was else None


# ── Schedule ─────────────────────────────────────────────────

def test_campaign_starts_and_reverts_by_the_clock_alone(client, clock):
    start, end = now() + timedelta(hours=1), now() + timedelta(hours=3)
    created = _create(client, start, end, announcement_text="Happy Diwali", show_countdown=True)
    assert created.status_code == 201, created.get_json()
    assert created.get_json()["status"] == "scheduled"
    campaign_id = created.get_json()["id"]

    layout = client.get("/api/content/layout").get_json()
    assert layout["campaign"] is None
    assert datetime.fromisoformat(layout["next_change_at"]) == start.replace(microsecond=start.microsecond)

    clock(start + timedelta(minutes=1))
    layout = client.get("/api/content/layout").get_json()
    assert layout["campaign"]["name"] == "Diwali Festive Sale" and layout["campaign"]["show_countdown"] is True
    assert datetime.fromisoformat(layout["campaign"]["ends_at"]) == end
    assert datetime.fromisoformat(layout["next_change_at"]) == end
    assert client.get(f"/api/admin/campaigns/{campaign_id}", headers=manager()).get_json()["status"] == "live"

    clock(end + timedelta(seconds=1))
    layout = client.get("/api/content/layout").get_json()
    assert layout["campaign"] is None and layout["next_change_at"] is None
    assert client.get(f"/api/admin/campaigns/{campaign_id}", headers=manager()).get_json()["status"] == "ended"


def test_exact_boundaries(client, clock):
    start, end = now() + timedelta(hours=1), now() + timedelta(hours=2)
    _create(client, start, end)
    clock(start - timedelta(microseconds=1))
    assert _live_name(client) is None
    clock(start)
    assert _live_name(client) == "Diwali Festive Sale"
    clock(end - timedelta(microseconds=1))
    assert _live_name(client) == "Diwali Festive Sale"
    clock(end)
    assert _live_name(client) is None


def test_a_cached_response_is_not_served_across_the_start(client, monkeypatch):
    """No cache.invalidate() here: only the clock moves, as in real life."""
    (product, _variant), = [make_product(price=1000, stock=5)]
    collection = _collection([product])
    start = now() + timedelta(hours=1)
    _create(client, start, start + timedelta(hours=1), collection_id=collection.id, sale_percent=20)

    before = client.get(f"/api/products/{product.slug}").get_json()
    assert before["selling_price"] == 1000 and before["on_sale"] is False

    monkeypatch.setattr(campaigns, "now_utc", lambda: start + timedelta(minutes=5))
    # the schedule itself is cached for 30 s and already holds this campaign
    during = client.get(f"/api/products/{product.slug}").get_json()
    assert during["selling_price"] == 800 and during["on_sale"] is True

    monkeypatch.setattr(campaigns, "now_utc", lambda: start + timedelta(hours=2))
    assert client.get(f"/api/products/{product.slug}").get_json()["selling_price"] == 1000


def test_times_are_taken_with_their_offset(client):
    """"10:00 +05:30" is 04:30 UTC, whatever the server's own zone."""
    tomorrow = (now() + timedelta(days=1)).date().isoformat()
    resp = client.post("/api/admin/campaigns", headers=manager(), json={
        "name": "Morning sale", "starts_at": f"{tomorrow}T10:00:00+05:30", "ends_at": f"{tomorrow}T22:00:00+05:30"})
    assert resp.status_code == 201
    assert resp.get_json()["starts_at"].startswith(f"{tomorrow}T04:30:00")

    naive = client.post("/api/admin/campaigns", headers=manager(), json={
        "name": "No zone", "starts_at": f"{tomorrow}T10:00:00", "ends_at": f"{tomorrow}T22:00:00"})
    assert naive.status_code == 422


@pytest.mark.parametrize("delta_start,delta_end,field", [
    (2, 1, "ends_at"),          # ends before it starts
    (-48, -24, "ends_at"),      # already over
])
def test_impossible_dates_are_refused(client, delta_start, delta_end, field):
    resp = _create(client, now() + timedelta(hours=delta_start), now() + timedelta(hours=delta_end))
    assert resp.status_code == 422 and field in resp.get_json()["errors"]
    assert Campaign.query.count() == 0


def test_validation(client):
    start, end = now() + timedelta(hours=1), now() + timedelta(hours=2)
    assert _create(client, start, end, sale_percent=20).status_code == 422                       # no collection
    assert _create(client, start, end, collection_id=999, sale_percent=20).status_code == 422
    assert _create(client, start, end, sale_percent=95, collection_id=1).status_code == 422
    assert _create(client, start, end, accent_preset="neon").status_code == 422
    assert _create(client, start, end, announcement_link_url="javascript:alert(1)").status_code == 422
    assert _create(client, start, end, announcement_text="<script>x</script>").status_code == 422
    assert _create(client, start, end, name="").status_code == 422
    assert Campaign.query.count() == 0


# ── Overlap ──────────────────────────────────────────────────

def test_overlapping_schedules_are_rejected(client):
    base = now() + timedelta(days=1)
    first = _create(client, base, base + timedelta(days=7))
    assert first.status_code == 201

    for start, end in [
        (base + timedelta(days=1), base + timedelta(days=2)),      # inside
        (base - timedelta(days=1), base + timedelta(hours=1)),     # overlaps the start
        (base + timedelta(days=6), base + timedelta(days=9)),      # overlaps the end
        (base - timedelta(days=1), base + timedelta(days=9)),      # surrounds
    ]:
        resp = client.post("/api/admin/campaigns", headers=manager(),
                           json={**_payload(start, end), "name": "Durga Puja Specials"})
        assert resp.status_code == 409, (start, end)
        assert "Diwali Festive Sale" in resp.get_json()["errors"]["starts_at"][0]
    assert Campaign.query.count() == 1

    # back to back is fine: one ends exactly when the next begins
    after = client.post("/api/admin/campaigns", headers=manager(), json={
        **_payload(base + timedelta(days=7), base + timedelta(days=8)), "name": "Durga Puja Specials"})
    assert after.status_code == 201

    # moving the first one onto the second is refused; re-saving it unchanged is not
    first_id = first.get_json()["id"]
    assert client.put(f"/api/admin/campaigns/{first_id}", headers=manager(),
                      json=_payload(base, base + timedelta(days=7, hours=1))).status_code == 409
    assert client.put(f"/api/admin/campaigns/{first_id}", headers=manager(),
                      json=_payload(base, base + timedelta(days=7))).status_code == 200


def test_ending_early_frees_the_rest_of_the_window(client):
    live = _create(client, now() - timedelta(hours=1), now() + timedelta(days=5)).get_json()
    blocked = client.post("/api/admin/campaigns", headers=manager(), json={
        **_payload(now() + timedelta(days=1), now() + timedelta(days=2)), "name": "Next"})
    assert blocked.status_code == 409

    assert client.post(f"/api/admin/campaigns/{live['id']}/end", headers=manager()).status_code == 200
    freed = client.post("/api/admin/campaigns", headers=manager(), json={
        **_payload(now() + timedelta(days=1), now() + timedelta(days=2)), "name": "Next"})
    assert freed.status_code == 201


# ── What a live campaign changes ─────────────────────────────

def _setup_sale(client, percent=20, **extra):
    on_sale, _v1 = make_product(price=1000, stock=10)
    regular, _v2 = make_product(price=1000, stock=10)
    collection = _collection([on_sale])
    resp = _create(client, now() - timedelta(minutes=5), now() + timedelta(days=21),
                   collection_id=collection.id, sale_percent=percent, **extra)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json(), on_sale, regular


def test_sale_prices_in_listing_and_detail(client):
    _campaign, on_sale, regular = _setup_sale(client)
    listing = {p["id"]: p for p in client.get("/api/products").get_json()["products"]}
    assert listing[on_sale.id]["selling_price"] == 800 and listing[on_sale.id]["original_price"] == 1000
    assert listing[on_sale.id]["on_sale"] is True and listing[on_sale.id]["sale_percent"] == 20
    assert listing[regular.id]["selling_price"] == 1000 and listing[regular.id]["on_sale"] is False
    # the stored price is untouched
    db.session.expire_all()
    assert float(on_sale.selling_price) == 1000

    collection = client.get("/api/content/collections/diwali-edit").get_json()
    assert collection["sale_percent"] == 20


def test_variant_price_override_is_discounted_too(client):
    campaign, on_sale, _ = _setup_sale(client, percent=25)
    assert campaign["sale_percent"] == 25
    variant = on_sale.variants[0]
    variant.price_override = 1199
    db.session.commit()
    cache.invalidate()
    detail = client.get(f"/api/products/{on_sale.slug}").get_json()
    assert detail["variants"][0]["price_override"] == 899        # 1199 * 0.75 = 899.25 -> whole rupee
    assert campaigns.unit_price(on_sale, variant) == 899


def test_cart_and_order_use_the_sale_price_and_revert_after(client):
    campaign, on_sale, regular = _setup_sale(client)
    user = make_user()
    address = make_address(user)
    headers = customer_headers(user)
    for product in (on_sale, regular):
        added = client.post("/api/cart/items", headers=headers, json={"variant_id": product.variants[0].id, "quantity": 1})
        assert added.status_code == 200

    cart = client.get("/api/cart", headers=headers).get_json()
    assert sorted(i["unit_price"] for i in cart["items"]) == [800, 1000] and cart["subtotal"] == 1800

    # the campaign ends while the items sit in the cart
    assert client.post(f"/api/admin/campaigns/{campaign['id']}/end", headers=manager()).status_code == 200
    cart = client.get("/api/cart", headers=headers).get_json()
    assert sorted(i["unit_price"] for i in cart["items"]) == [1000, 1000] and cart["subtotal"] == 2000

    order, err = create_order_from_cart(user.id, address.id, "cod")
    assert err is None and float(order.subtotal) == 2000
    assert sorted(float(i.unit_price) for i in order.items) == [1000, 1000]


def test_order_placed_during_the_sale_is_charged_the_sale_price(client):
    _campaign, on_sale, _ = _setup_sale(client)
    user = make_user()
    address = make_address(user)
    make_cart(user, [(on_sale.variants[0], 2)])          # the factory stores the full price on the line
    cart = client.get("/api/cart", headers=customer_headers(user)).get_json()
    order, err = create_order_from_cart(user.id, address.id, "cod")
    assert err is None
    assert float(order.subtotal) == 1600 == cart["subtotal"] and float(order.total_amount) == cart["total"]


def test_campaign_slides_banners_and_announcement_take_over_and_revert(client):
    db.session.add(HeroBanner(title="Everyday hero", image_url="/static/uploads/a.webp"))
    db.session.add(PromoBanner(title="Everyday promo"))
    db.session.add(Announcement(text="Free shipping over 999"))
    db.session.commit()
    campaign = _create(client, now() - timedelta(minutes=1), now() + timedelta(days=1),
                       announcement_text="Happy Diwali", announcement_highlight="Up to 25% off",
                       decoration_enabled=True, accent_preset="marigold").get_json()

    # no campaign slides yet: the everyday ones stay
    assert [b["title"] for b in client.get("/api/cms/banners").get_json()["banners"]] == ["Everyday hero"]

    for title in ("Lights", "Diyas", "Gifting"):
        made = client.post("/api/admin/banners", headers=manager(), json={
            "title": title, "image_url": "/static/uploads/d.webp", "campaign_id": campaign["id"],
            "link_url": "/collections/diwali-edit", "link_text": "Shop the Diwali Edit"})
        assert made.status_code == 201, made.get_json()
    client.post("/api/admin/promo-banners", headers=manager(), json={"title": "Festive promo", "campaign_id": campaign["id"]})

    assert [b["title"] for b in client.get("/api/cms/banners").get_json()["banners"]] == ["Lights", "Diyas", "Gifting"]
    assert [p["title"] for p in client.get("/api/cms/promo-banners").get_json()["promo_banners"]] == ["Festive promo"]
    bar = client.get("/api/cms/announcements").get_json()["announcements"]
    assert len(bar) == 1 and bar[0]["text"] == "Happy Diwali" and bar[0]["highlight_color"] == "#F2A900"
    layout = client.get("/api/content/layout").get_json()
    assert layout["campaign"]["decoration"]["enabled"] is True and layout["campaign"]["decoration"]["preset"] == "marigold"

    # the everyday admin list does not mix them in; the campaign shows its own
    assert [b["title"] for b in client.get("/api/admin/banners", headers=manager()).get_json()["banners"]] == ["Everyday hero"]
    detail = client.get(f"/api/admin/campaigns/{campaign['id']}", headers=manager()).get_json()
    assert len(detail["slides"]) == 3 and len(detail["promo_banners"]) == 1

    client.post(f"/api/admin/campaigns/{campaign['id']}/end", headers=manager())
    assert [b["title"] for b in client.get("/api/cms/banners").get_json()["banners"]] == ["Everyday hero"]
    assert [p["title"] for p in client.get("/api/cms/promo-banners").get_json()["promo_banners"]] == ["Everyday promo"]
    assert client.get("/api/cms/announcements").get_json()["announcements"][0]["text"] == "Free shipping over 999"
    assert client.get("/api/content/layout").get_json()["campaign"] is None

    # deleting the campaign takes its slides with it
    assert client.delete(f"/api/admin/campaigns/{campaign['id']}", headers=manager()).status_code == 200
    assert HeroBanner.query.count() == 1 and PromoBanner.query.count() == 1


# ── Coupons ──────────────────────────────────────────────────

def _coupon(code, **kw):
    coupon = Coupon(code=code, discount_type=kw.pop("discount_type", DiscountType.percentage),
                    discount_value=kw.pop("discount_value", 10), **kw)
    db.session.add(coupon)
    db.session.commit()
    return coupon


def test_campaign_coupons_work_only_while_it_is_live(client, clock):
    diwali10 = _coupon("DIWALI10", min_order_value=999, usage_limit=500)
    festive500 = _coupon("FESTIVE500", discount_type=DiscountType.flat, discount_value=500, min_order_value=2999, usage_limit=100)
    start, end = now() + timedelta(hours=1), now() + timedelta(days=21)
    campaign = _create(client, start, end, coupon_ids=[diwali10.id, festive500.id]).get_json()
    assert {c["code"] for c in campaign["coupons"]} == {"DIWALI10", "FESTIVE500"}
    db.session.expire_all()
    assert diwali10.expires_at == end and festive500.expires_at == end

    user = make_user()
    _, variant = make_product(price=1500, stock=10)
    make_cart(user, [(variant, 1)])
    headers = customer_headers(user)

    early = client.post("/api/cart/coupon", headers=headers, json={"code": "DIWALI10"})
    assert early.status_code == 410 and "not valid right now" in early.get_json()["error"]

    clock(start + timedelta(minutes=1))
    applied = client.post("/api/cart/coupon", headers=headers, json={"code": "diwali10"})
    assert applied.status_code == 200 and applied.get_json()["discount"] == 150
    too_small = client.post("/api/cart/coupon", headers=headers, json={"code": "FESTIVE500"})
    assert too_small.status_code == 422                      # below its minimum order

    # ended early with the coupon still on the cart: it comes off
    client.post(f"/api/admin/campaigns/{campaign['id']}/end", headers=manager())
    clock(start + timedelta(minutes=2))
    cart = client.get("/api/cart", headers=headers).get_json()
    assert cart["discount"] == 0 and cart["coupon_code"] is None
    assert client.post("/api/cart/coupon", headers=headers, json={"code": "DIWALI10"}).status_code == 410


def test_a_coupon_belongs_to_one_campaign(client):
    coupon = _coupon("DIWALI10")
    base = now() + timedelta(days=1)
    first = _create(client, base, base + timedelta(days=1), coupon_ids=[coupon.id]).get_json()
    second = client.post("/api/admin/campaigns", headers=manager(), json={
        **_payload(base + timedelta(days=2), base + timedelta(days=3)), "name": "Second", "coupon_ids": [coupon.id]})
    assert second.status_code == 409

    # removing it from the first frees it
    assert client.put(f"/api/admin/campaigns/{first['id']}", headers=manager(),
                      json={**_payload(base, base + timedelta(days=1)), "coupon_ids": []}).status_code == 200
    db.session.expire_all()
    assert coupon.campaign_id is None
    assert _create(client, base, base + timedelta(days=1), coupon_ids=[4242]).status_code in (409, 422)


# ── Preview and End now ──────────────────────────────────────

def test_preview_shows_the_campaign_without_selling_at_its_prices(client):
    product, variant = make_product(price=1000, stock=10)
    collection = _collection([product])
    start = now() + timedelta(days=30)
    campaign = _create(client, start, start + timedelta(days=5), collection_id=collection.id,
                       sale_percent=20, announcement_text="Durga Puja Specials").get_json()

    token = client.post(f"/api/admin/campaigns/{campaign['id']}/preview", headers=manager()).get_json()["token"]
    preview = {campaigns.PREVIEW_HEADER: token}

    # everyone else sees the normal store, before and after a preview request
    assert client.get(f"/api/products/{product.slug}").get_json()["selling_price"] == 1000
    seen = client.get(f"/api/products/{product.slug}", headers=preview).get_json()
    assert seen["selling_price"] == 800 and seen["on_sale"] is True
    layout = client.get("/api/content/layout", headers=preview).get_json()
    assert layout["campaign"]["preview"] is True and layout["campaign"]["name"] == "Diwali Festive Sale"
    assert client.get("/api/cms/announcements", headers=preview).get_json()["announcements"][0]["text"] == "Durga Puja Specials"
    assert client.get(f"/api/products/{product.slug}").get_json()["selling_price"] == 1000
    assert client.get("/api/content/layout").get_json()["campaign"] is None

    # the cart ignores the preview: nothing can be bought at the future price
    user = make_user()
    headers = {**customer_headers(user), **preview}
    client.post("/api/cart/items", headers=headers, json={"variant_id": variant.id, "quantity": 1})
    assert client.get("/api/cart", headers=headers).get_json()["subtotal"] == 1000


@pytest.mark.parametrize("token", ["", "garbage", "eyJjIjoxfQ.bad.sig"])
def test_a_bad_preview_token_is_ignored(client, token):
    start = now() + timedelta(days=30)
    _create(client, start, start + timedelta(days=5), announcement_text="Later")
    assert client.get("/api/content/layout", headers={campaigns.PREVIEW_HEADER: token}).get_json()["campaign"] is None


def test_end_now_only_applies_to_a_live_campaign(client):
    scheduled = _create(client, now() + timedelta(days=1), now() + timedelta(days=2)).get_json()
    assert client.post(f"/api/admin/campaigns/{scheduled['id']}/end", headers=manager()).status_code == 409
    assert client.post("/api/admin/campaigns/9999/end", headers=manager()).status_code == 404

    live = _create(client, now() - timedelta(minutes=1), now() + timedelta(hours=5)).get_json()
    assert client.delete(f"/api/admin/campaigns/{live['id']}", headers=manager()).status_code == 409
    ended = client.post(f"/api/admin/campaigns/{live['id']}/end", headers=manager())
    assert ended.status_code == 200 and ended.get_json()["status"] == "ended" and ended.get_json()["ended_at"]
    assert client.post(f"/api/admin/campaigns/{live['id']}/end", headers=manager()).status_code == 409

    # saving new dates on an ended campaign schedules it again
    again = client.put(f"/api/admin/campaigns/{live['id']}", headers=manager(),
                       json=_payload(now() + timedelta(days=10), now() + timedelta(days=11)))
    assert again.status_code == 200 and again.get_json()["status"] == "scheduled"


# ── Decoration presets ───────────────────────────────────────

def _luminance(hex_colour):
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    lighter, darker = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


@pytest.mark.parametrize("name", list(campaigns.ACCENT_PRESETS))
def test_accent_presets_pass_wcag_aa_on_the_frozen_theme(name):
    preset = campaigns.ACCENT_PRESETS[name]
    assert contrast(preset["on_accent"], preset["accent"]) >= 4.5       # badge / button text on the accent
    assert contrast(preset["accent_text"], "#FFFFFF") >= 4.5            # accent-coloured text on the white page
    assert contrast(preset["on_dark"], "#0A0A0A") >= 4.5               # the offer line on the black announcement bar


# ── Listing during a sale: sort, filter and facets use the price on show ──

def _sale_catalogue(client):
    """Stored prices 1000 / 1200 / 1500 / 2000; the 1500 and 2000 ones are in a
    collection on sale at 40% off, so they are SHOWN at 900 and 1200."""
    a, _ = make_product(price=1000, stock=5)
    b, _ = make_product(price=1200, stock=5)
    c, _ = make_product(price=1500, stock=5)
    d, _ = make_product(price=2000, stock=0)          # sold out
    collection = _collection([c, d])
    resp = _create(client, now() - timedelta(minutes=5), now() + timedelta(days=5),
                   collection_id=collection.id, sale_percent=40)
    assert resp.status_code == 201, resp.get_json()
    return a, b, c, d


def _listing(client, query=""):
    resp = client.get(f"/api/products?per_page=12&page=1{query}")
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()


def test_listing_works_with_a_live_campaign_sale_collection_and_filters(client):
    a, b, c, d = _sale_catalogue(client)
    shown = {a.id: 1000, b.id: 1200, c.id: 900, d.id: 1200}

    everything = _listing(client, "&sort=newest")
    assert everything["total"] == 4
    assert {p["id"]: p["selling_price"] for p in everything["products"]} == shown
    assert {p["id"] for p in everything["products"] if p["on_sale"]} == {c.id, d.id}

    # sorted by the price on show, not the stored one
    asc = [p["selling_price"] for p in _listing(client, "&sort=price_asc")["products"]]
    assert asc == sorted(asc) == [900, 1000, 1200, 1200]
    desc = [p["selling_price"] for p in _listing(client, "&sort=price_desc")["products"]]
    assert desc == sorted(desc, reverse=True)
    assert _listing(client, "&sort=price_asc")["products"][0]["id"] == c.id

    # price range: c (stored 1500, shown 900) is inside "up to 950"; a (1000) is not
    assert [p["id"] for p in _listing(client, "&max_price=950")["products"]] == [c.id]
    assert {p["id"] for p in _listing(client, "&min_price=1100&max_price=1300")["products"]} == {b.id, d.id}
    assert _listing(client, "&min_price=1400")["total"] == 0          # nothing is shown at 1500 or 2000

    # combined with the collection, stock and size filters, and paging
    in_collection = _listing(client, "&collection=diwali-edit")
    assert [p["id"] for p in in_collection["products"]] == [c.id, d.id]
    assert [p["id"] for p in _listing(client, "&collection=diwali-edit&in_stock=true")["products"]] == [c.id]
    assert [p["id"] for p in _listing(client, "&collection=diwali-edit&sort=price_desc&max_price=1000")["products"]] == [c.id]
    size = c.variants[0].size
    assert c.id in [p["id"] for p in _listing(client, f"&size={size}&max_price=950")["products"]]
    paged = client.get("/api/products?per_page=1&page=2&sort=price_asc").get_json()
    assert paged["pages"] == 4 and paged["products"][0]["selling_price"] == 1000

    facets = client.get("/api/products/facets").get_json()
    assert facets["price"] == {"min": 900, "max": 1200}


def test_listing_goes_back_to_stored_prices_when_the_sale_ends(client):
    a, b, c, d = _sale_catalogue(client)
    campaign = Campaign.query.one()
    assert client.post(f"/api/admin/campaigns/{campaign.id}/end", headers=manager()).status_code == 200
    asc = [(p["id"], p["selling_price"]) for p in _listing(client, "&sort=price_asc")["products"]]
    assert asc == [(a.id, 1000), (b.id, 1200), (c.id, 1500), (d.id, 2000)]
    assert _listing(client, "&max_price=950")["total"] == 0
    assert client.get("/api/products/facets").get_json()["price"] == {"min": 1000, "max": 2000}


@pytest.mark.parametrize("base,percent", [(999, 15), (1299, 25), (2499, 12.5), (4999, 20), (1, 90), (3333, 17.5), (1050, 10)])
def test_python_and_sql_round_the_sale_price_the_same_way(client, base, percent):
    """Sorting happens in SQL, the price on the card is computed in Python:
    a rupee of disagreement would put a product in the wrong place."""
    product, _ = make_product(price=base, mrp=base + 1000, stock=1)
    snapshot = {"sale_percent": percent, "sale_product_ids": [product.id]}
    in_sql = db.session.query(campaigns.effective_price_sql(snapshot)).filter_by(id=product.id).scalar()
    assert float(in_sql) == campaigns.sale_price(base, percent)
