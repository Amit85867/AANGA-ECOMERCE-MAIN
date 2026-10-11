"""Round 3: roles, staff, store settings, homepage builder, navigation, pages,
FAQ, collections, media library, customers export, demo content."""
import io
import uuid
from unittest.mock import patch

import pytest
from PIL import Image

from app.extensions import db
from app.models.admin import Admin
from app.models.catalogue import Category, Product
from app.models.cms import HeroBanner, SiteSetting
from app.models.engagement import Coupon
from app.models.ops import AuditLog
from app.models.owner import CmsPage, Collection, FaqItem, MediaAsset, NavLink
from app.models.user import User
from app.services import cache, content, permissions
from app.services.order_service import create_order_from_cart
from app.services.sanitize import clean_html
from tests.factories import make_address, make_cart, make_product, make_user
from tests.helpers import ADMIN_PASSWORD, admin_headers, customer_headers, make_admin

DEMO = {"X-Demo-Content": "1"}


def owner():
    return admin_headers(role="master")


def manager():
    return admin_headers(role="manager")


def staff():
    return admin_headers(role="staff")


# ══ Roles ════════════════════════════════════════════════════

OWNER_ONLY = [
    ("GET", "/api/admin/settings"), ("PUT", "/api/admin/settings"),
    ("GET", "/api/admin/staff"), ("POST", "/api/admin/staff"),
    ("GET", "/api/admin/demo"), ("POST", "/api/admin/demo/remove"),
    ("GET", "/api/admin/site-settings"), ("GET", "/api/admin/system/health"),
    ("GET", "/api/admin/auth/admins"),
]
MANAGER_AREAS = [
    ("GET", "/api/admin/campaigns"), ("POST", "/api/admin/campaigns"),
    ("GET", "/api/admin/collections"), ("GET", "/api/admin/homepage"),
    ("GET", "/api/admin/navigation"), ("GET", "/api/admin/pages"), ("GET", "/api/admin/faq"),
    ("GET", "/api/admin/users"), ("GET", "/api/admin/users/export.csv"),
    ("GET", "/api/admin/coupons"), ("GET", "/api/admin/banners"), ("GET", "/api/admin/audit-log"),
]
STAFF_AREAS = [
    ("GET", "/api/admin/products"), ("GET", "/api/admin/categories"), ("GET", "/api/admin/orders"),
    ("GET", "/api/admin/returns"), ("GET", "/api/admin/dashboard/overview"), ("GET", "/api/admin/media"),
    ("GET", "/api/admin/auth/me"),
]


@pytest.mark.parametrize("method,url", OWNER_ONLY + MANAGER_AREAS)
def test_staff_is_blocked_outside_catalogue_and_orders(client, method, url):
    resp = client.open(url, method=method, headers=staff(), json={})
    assert resp.status_code == 403, (url, resp.get_json())
    assert "Staff" in resp.get_json()["error"]


@pytest.mark.parametrize("method,url", STAFF_AREAS)
def test_staff_can_use_catalogue_and_orders(client, method, url):
    assert client.open(url, method=method, headers=staff()).status_code == 200


@pytest.mark.parametrize("method,url", OWNER_ONLY)
def test_manager_is_blocked_from_owner_areas(client, method, url):
    assert client.open(url, method=method, headers=manager(), json={}).status_code == 403


@pytest.mark.parametrize("method,url", [u for u in MANAGER_AREAS + STAFF_AREAS if u[0] == "GET"])
def test_manager_can_run_the_shop(client, method, url):
    assert client.open(url, method=method, headers=manager()).status_code == 200


@pytest.mark.parametrize("method,url", [u for u in OWNER_ONLY + MANAGER_AREAS if u[0] == "GET"])
def test_owner_can_open_everything(client, method, url):
    assert client.open(url, method=method, headers=owner()).status_code == 200


def test_every_admin_route_belongs_to_a_known_area(app):
    """A route added under a new URL segment would be Owner-only by default;
    this makes that a decision rather than an accident."""
    for rule in app.url_map.iter_rules():
        if rule.rule.startswith("/api/admin/"):
            area = permissions.area_of(rule.rule)
            assert area is None or area in permissions.AREAS, rule.rule


def test_role_change_applies_to_the_next_request(client):
    """The token still says manager; the database is what counts."""
    admin = make_admin(role="manager")
    headers = admin_headers(admin)
    assert client.get("/api/admin/campaigns", headers=headers).status_code == 200
    admin.role = "staff"
    db.session.commit()
    assert client.get("/api/admin/campaigns", headers=headers).status_code == 403


def test_sign_in_tells_the_app_which_areas_to_show(client):
    admin = make_admin(role="staff")
    body = client.post("/api/admin/auth/login", json={"email": admin.email, "password": ADMIN_PASSWORD}).get_json()
    assert "products" in body["admin"]["areas"]
    assert "settings" not in body["admin"]["areas"] and "campaigns" not in body["admin"]["areas"]


# ══ Staff management ═════════════════════════════════════════

def test_owner_invites_staff_with_a_one_time_password(client):
    resp = client.post("/api/admin/staff", headers=owner(), json={
        "email": "New.Person@example.com", "full_name": "New Person", "role": "manager",
    })
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["staff"]["role"] == "manager" and body["staff"]["email"] == "new.person@example.com"
    assert "password" not in body["staff"]

    login = client.post("/api/admin/auth/login", json={
        "email": "new.person@example.com", "password": body["temporary_password"],
    })
    assert login.status_code == 200

    entry = AuditLog.query.filter_by(entity_type="staff").order_by(AuditLog.id.desc()).first()
    assert "new.person@example.com" in entry.summary
    assert body["temporary_password"] not in str(entry.changes) + entry.summary


def test_invite_validation(client):
    headers = owner()
    assert client.post("/api/admin/staff", headers=headers, json={"email": "nope", "full_name": "X Y"}).status_code == 422
    assert client.post("/api/admin/staff", headers=headers, json={
        "email": "a@example.com", "full_name": "A B", "role": "superuser"}).status_code == 422
    existing = make_admin(role="staff")
    assert client.post("/api/admin/staff", headers=headers, json={
        "email": existing.email.upper(), "full_name": "A B"}).status_code == 409


def test_edit_deactivate_reset_and_remove_staff(client):
    headers = owner()
    member = make_admin(role="staff")
    url = f"/api/admin/staff/{member.id}"

    edited = client.patch(url, headers=headers, json={"role": "manager", "full_name": "Renamed"})
    assert edited.status_code == 200 and edited.get_json()["staff"]["role_label"] == "Manager"

    reset = client.patch(url, headers=headers, json={"reset_password": True}).get_json()
    assert client.post("/api/admin/auth/login", json={
        "email": member.email, "password": reset["temporary_password"]}).status_code == 200

    assert client.patch(url, headers=headers, json={"is_active": False}).status_code == 200
    assert client.post("/api/admin/auth/login", json={
        "email": member.email, "password": reset["temporary_password"]}).status_code == 403

    assert client.delete(url, headers=headers).status_code == 200
    assert db.session.get(Admin, member.id) is None
    assert client.delete(url, headers=headers).status_code == 404
    assert client.patch("/api/admin/staff/not-a-uuid", headers=headers, json={"role": "staff"}).status_code == 404


def test_the_last_owner_cannot_be_removed_demoted_or_deactivated(client):
    only = make_admin(role="master")
    second = make_admin(role="master")
    as_second = admin_headers(second)
    url = f"/api/admin/staff/{only.id}"

    # with two owners, one can demote the other
    assert client.patch(url, headers=as_second, json={"role": "manager"}).status_code == 200
    # now `second` is the only owner left
    own = f"/api/admin/staff/{second.id}"
    assert client.patch(own, headers=as_second, json={"role": "manager"}).status_code == 409
    assert client.patch(own, headers=as_second, json={"is_active": False}).status_code == 409
    assert client.delete(own, headers=as_second).status_code == 409
    assert db.session.get(Admin, second.id).role == "master"

    # another owner, deactivated, does not count
    third = make_admin(role="master")
    third.is_active = False
    db.session.commit()
    assert client.patch(own, headers=as_second, json={"role": "staff"}).status_code == 409


def test_cannot_remove_or_deactivate_yourself(client):
    me, other = make_admin(role="master"), make_admin(role="master")
    assert other.id
    headers = admin_headers(me)
    assert client.delete(f"/api/admin/staff/{me.id}", headers=headers).status_code == 409
    assert client.patch(f"/api/admin/staff/{me.id}", headers=headers, json={"is_active": False}).status_code == 409


# ══ Store settings ═══════════════════════════════════════════

def _save(client, **values):
    return client.put("/api/admin/settings", headers=owner(), json={"values": values})


def test_settings_have_defaults_and_save(client):
    groups = client.get("/api/admin/settings", headers=owner()).get_json()["groups"]
    fields = {f["key"]: f for g in groups for f in g["fields"]}
    assert fields["delivery_charge"]["value"] == "49" and fields["cod_enabled"]["value"] == "true"

    resp = _save(client, store_name="Demo Store", store_email="hello@example.com", gstin="10abcde1234f1z5",
                 instagram_url="https://instagram.com/demo", delivery_charge="79", free_shipping_threshold=1500)
    assert resp.status_code == 200, resp.get_json()
    public = client.get("/api/cms/settings").get_json()["settings"]
    assert public["store_name"] == "Demo Store" and public["gstin"] == "10ABCDE1234F1Z5"
    assert public["delivery_charge"] == "79" and public["free_shipping_threshold"] == "1500"
    entry = AuditLog.query.filter_by(entity_type="settings").first()
    assert entry.changes["delivery_charge"] == {"from": "49", "to": "79"}


@pytest.mark.parametrize("values,bad", [
    ({"store_email": "not-an-email"}, "store_email"),
    ({"gstin": "123"}, "gstin"),
    ({"instagram_url": "javascript:alert(1)"}, "instagram_url"),
    ({"delivery_charge": "-5"}, "delivery_charge"),
    ({"delivery_charge": "lots"}, "delivery_charge"),
    ({"return_window_days": "2.5"}, "return_window_days"),
    ({"return_window_days": "400"}, "return_window_days"),
    ({"store_name": ""}, "store_name"),
    ({"store_name": "<b>Shop</b>"}, "store_name"),
    ({"logo_url": "data:image/svg+xml,<svg onload=alert(1)>"}, "logo_url"),
    ({"cod_enabled": "maybe"}, "cod_enabled"),
    ({"not_a_setting": "x"}, "not_a_setting"),
])
def test_settings_validation_rejects_and_saves_nothing(client, values, bad):
    resp = _save(client, store_tagline="should not be saved", **values)
    assert resp.status_code == 422
    assert bad in resp.get_json()["errors"]
    assert SiteSetting.query.filter_by(key="store_tagline").first() is None


def test_shipping_settings_drive_cart_and_order_totals(client):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=500, stock=10)
    make_cart(user, [(variant, 1)])

    assert client.get("/api/cart", headers=customer_headers(user)).get_json()["delivery_charge"] == 49
    _save(client, delivery_charge="80", free_shipping_threshold="2000")
    cart = client.get("/api/cart", headers=customer_headers(user)).get_json()
    assert cart["delivery_charge"] == 80
    order, err = create_order_from_cart(user.id, address.id, "cod")
    assert err is None and float(order.delivery_charge) == 80 and float(order.total_amount) == cart["total"]

    client.post("/api/cart/items", headers=customer_headers(user), json={"variant_id": variant.id, "quantity": 1})
    _save(client, free_shipping_threshold="400")
    assert client.get("/api/cart", headers=customer_headers(user)).get_json()["delivery_charge"] == 0


def test_cod_can_be_switched_off(client):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=500, stock=10)
    make_cart(user, [(variant, 1)])
    _save(client, cod_enabled=False)

    assert client.get("/api/cms/features-available").get_json()["cash_on_delivery"] is False
    resp = client.post("/api/orders", headers=customer_headers(user),
                       json={"address_id": address.id, "payment_method": "cod"})
    assert resp.status_code == 422 and "Cash on delivery" in resp.get_json()["error"]

    _save(client, cod_enabled=True)
    assert client.post("/api/orders", headers=customer_headers(user),
                       json={"address_id": address.id, "payment_method": "cod"}).status_code == 201


def test_return_window_setting_is_used(client):
    from app.models.enums import OrderStatus
    from app.models.order import Order

    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=500, stock=10)
    make_cart(user, [(variant, 1)])
    order, _ = create_order_from_cart(user.id, address.id, "cod")
    Order.query.filter_by(id=order.id).update({"status": OrderStatus.delivered})
    db.session.commit()

    url = f"/api/returns/eligibility/{order.id}"
    assert client.get(url, headers=customer_headers(user)).get_json()["window_days"] == 7
    _save(client, return_window_days="0")
    body = client.get(url, headers=customer_headers(user)).get_json()
    assert body["window_days"] == 0
    refused = client.post("/api/returns", headers=customer_headers(user),
                          json={"order_item_id": order.items[0].id, "reason": "changed_mind"})
    assert refused.status_code == 422


# ══ Homepage builder ═════════════════════════════════════════

def _layout(client):
    cache.invalidate()
    return client.get("/api/content/layout").get_json()


def test_layout_has_defaults_before_anything_is_saved(client):
    body = _layout(client)
    assert [s["key"] for s in body["homepage"]] == content.HOME_KEYS
    assert body["navigation"]["header"] and body["navigation"]["footer"]
    assert body["campaign"] is None and body["settings"]["store_name"] == "AANGA"


def test_reorder_hide_and_retitle_sections(client):
    sections = client.get("/api/admin/homepage", headers=manager()).get_json()["sections"]
    order = [s["key"] for s in sections]
    order.remove("testimonials")
    order.insert(1, "testimonials")
    payload = [{"key": k, "is_visible": k != "newsletter", "title": "Loved by customers" if k == "testimonials" else None}
               for k in order]
    resp = client.put("/api/admin/homepage", headers=manager(), json={"sections": payload})
    assert resp.status_code == 200, resp.get_json()

    live = _layout(client)["homepage"]
    assert [s["key"] for s in live][:2] == ["hero", "testimonials"]
    assert "newsletter" not in [s["key"] for s in live]
    assert live[1]["title"] == "Loved by customers"
    assert AuditLog.query.filter_by(entity_type="homepage").count() == 1


def test_homepage_save_needs_every_section_once(client):
    partial = [{"key": "hero", "is_visible": True}]
    assert client.put("/api/admin/homepage", headers=manager(), json={"sections": partial}).status_code == 422
    doubled = [{"key": k, "is_visible": True} for k in content.HOME_KEYS + ["hero"]]
    assert client.put("/api/admin/homepage", headers=manager(), json={"sections": doubled}).status_code == 422
    unknown = [{"key": "popup", "is_visible": True}]
    assert client.put("/api/admin/homepage", headers=manager(), json={"sections": unknown}).status_code == 422


def test_featured_section_can_show_a_collection(client):
    collection = Collection(name="Festive Picks", slug="festive-picks")
    db.session.add(collection)
    db.session.commit()
    payload = [{"key": k, "is_visible": True, **({"collection_id": collection.id} if k == "featured" else {})}
               for k in content.HOME_KEYS]
    assert client.put("/api/admin/homepage", headers=manager(), json={"sections": payload}).status_code == 200
    featured = next(s for s in _layout(client)["homepage"] if s["key"] == "featured")
    assert featured["collection"] == {"slug": "festive-picks", "name": "Festive Picks"}

    payload[content.HOME_KEYS.index("featured")]["collection_id"] = 99999
    assert client.put("/api/admin/homepage", headers=manager(), json={"sections": payload}).status_code == 422


# ══ Navigation ═══════════════════════════════════════════════

def test_menus_are_replaced_in_order(client):
    payload = {
        "header": [{"label": "Sale", "url": "/offers"}, {"label": "Hidden", "url": "/shop", "is_visible": False}],
        "footer": [{"label": "Blog", "url": "https://example.com/blog", "group_name": "Company"}],
    }
    resp = client.put("/api/admin/navigation", headers=manager(), json=payload)
    assert resp.status_code == 200, resp.get_json()
    assert [l["label"] for l in resp.get_json()["header"]] == ["Sale", "Hidden"]

    public = _layout(client)["navigation"]
    assert [l["label"] for l in public["header"]] == ["Sale"]
    assert public["footer"][0]["group_name"] == "Company"
    assert NavLink.query.count() == 3


@pytest.mark.parametrize("url", ["javascript:alert(1)", "//evil.example", "data:text/html,x", "shop", "/ok\"><script>"])
def test_menu_links_must_be_safe(client, url):
    payload = {"header": [{"label": "X", "url": url}], "footer": []}
    assert client.put("/api/admin/navigation", headers=manager(), json=payload).status_code == 422
    assert NavLink.query.count() == 0


def test_footer_links_need_a_column_and_labels_are_plain(client):
    assert client.put("/api/admin/navigation", headers=manager(), json={
        "header": [], "footer": [{"label": "About", "url": "/about"}]}).status_code == 422
    assert client.put("/api/admin/navigation", headers=manager(), json={
        "header": [{"label": "<img src=x>", "url": "/"}], "footer": []}).status_code == 422


# ══ Pages and sanitising ═════════════════════════════════════

DIRTY = (
    '<h1>About</h1><p onclick="steal()">We <b>make</b> clothes.<script>alert(1)</script></p>'
    '<img src=x onerror=alert(1)><iframe src="https://evil.example"></iframe>'
    '<a href="javascript:alert(1)">bad</a> <a href="/shop">shop</a> '
    '<a href="https://example.com" onmouseover="x()">out</a><style>p{display:none}</style>'
    '<ul><li>One<li>Two</ul><svg><script>alert(2)</script></svg><p>unclosed'
)


def test_sanitiser_keeps_formatting_and_drops_everything_else():
    out = clean_html(DIRTY)
    for bad in ("<script", "alert(", "onclick", "onerror", "onmouseover", "<img", "<iframe", "javascript:", "<style", "<svg", "display:none"):
        assert bad not in out, bad
    assert "<h2>About</h2>" in out and "<strong>make</strong>" in out
    assert '<a href="/shop">shop</a>' in out
    assert '<a href="https://example.com" rel="noopener noreferrer nofollow" target="_blank">out</a>' in out
    assert "<a>bad</a>" in out
    assert out.count("<li>") == out.count("</li>") == 2 and out.endswith("</p>")


@pytest.mark.parametrize("payload", [
    "<a href=\"JaVaScRiPt:alert(1)\">x</a>", "<a href=\" java\tscript:alert(1)\">x</a>",
    "<a href=\"data:text/html;base64,PHNjcmlwdD4=\">x</a>", "<a href=\"//evil.example\">x</a>",
    "<p style=\"background:url(javascript:alert(1))\">x</p>", "<math><mtext><script>alert(1)</script></mtext></math>",
    "<<script>script>alert(1)<</script>/script>", "<scr<script>ipt>alert(1)</scr</script>ipt>",
    "&lt;script&gt;alert(1)&lt;/script&gt;",
])
def test_sanitiser_attack_strings(payload):
    out = clean_html(payload)
    assert "<script" not in out.lower() and "href=\"j" not in out.lower()
    assert "href=\"data" not in out.lower() and "href=\"//" not in out and "style=" not in out


def test_page_is_stored_sanitised_and_served(client):
    resp = client.put("/api/admin/pages/about", headers=manager(), json={
        "title": "Our Story", "body_html": DIRTY, "meta_title": "About us", "meta_description": "Who we are",
    })
    assert resp.status_code == 200, resp.get_json()
    stored = CmsPage.query.filter_by(slug="about").first().body_html
    assert "<script" not in stored and "onclick" not in stored

    cache.invalidate()
    public = client.get("/api/content/pages/about").get_json()
    assert public["title"] == "Our Story" and public["body_html"] == stored and public["meta_title"] == "About us"


def test_pages_list_unknown_slug_and_validation(client):
    pages = client.get("/api/admin/pages", headers=manager()).get_json()["pages"]
    assert [p["slug"] for p in pages] == content.PAGE_SLUGS and all(p["is_empty"] for p in pages)
    assert client.put("/api/admin/pages/secret", headers=manager(), json={"title": "x"}).status_code == 404
    assert client.get("/api/content/pages/secret").status_code == 404
    assert client.put("/api/admin/pages/about", headers=manager(), json={"title": ""}).status_code == 422
    assert client.put("/api/admin/pages/about", headers=manager(), json={
        "title": "About", "share_image_url": "javascript:alert(1)"}).status_code == 422
    assert client.get("/api/content/pages/shipping").get_json()["body_html"] == ""


# ══ FAQ ══════════════════════════════════════════════════════

def test_faq_is_managed_from_the_dashboard(client):
    headers = manager()
    first = client.post("/api/admin/faq", headers=headers, json={"question": "How long is delivery?", "answer": "4-7 days."}).get_json()
    second = client.post("/api/admin/faq", headers=headers, json={"question": "Do you take COD?", "answer": "Yes."}).get_json()
    hidden = client.post("/api/admin/faq", headers=headers, json={"question": "Draft question", "answer": "Later.", "is_active": False}).get_json()

    assert client.put("/api/admin/faq/order", headers=headers, json={"ids": [second["id"], hidden["id"], first["id"]]}).status_code == 200
    assert client.put(f"/api/admin/faq/{first['id']}", headers=headers, json={"question": "Delivery time?", "answer": "A week."}).status_code == 200

    cache.invalidate()
    public = client.get("/api/content/faq").get_json()["items"]
    assert [i["question"] for i in public] == ["Do you take COD?", "Delivery time?"]

    assert client.delete(f"/api/admin/faq/{second['id']}", headers=headers).status_code == 200
    assert client.delete(f"/api/admin/faq/{second['id']}", headers=headers).status_code == 404
    assert client.put("/api/admin/faq/order", headers=headers, json={"ids": [first["id"]]}).status_code == 422
    assert client.post("/api/admin/faq", headers=headers, json={"question": "Q?", "answer": ""}).status_code == 422
    assert client.post("/api/admin/faq", headers=headers, json={"question": "Is <b>this</b> ok?", "answer": "No"}).status_code == 422


# ══ Collections ══════════════════════════════════════════════

def _products(n, **kw):
    return [make_product(**kw)[0] for _ in range(n)]


def test_collection_crud_and_storefront_order(client):
    a, b, c = _products(3)
    headers = manager()
    created = client.post("/api/admin/collections", headers=headers, json={
        "name": "Diwali Edit", "description": "Festive picks", "product_ids": [c.id, a.id, c.id],
    })
    assert created.status_code == 201, created.get_json()
    body = created.get_json()
    assert body["slug"] == "diwali-edit" and [p["id"] for p in body["products"]] == [c.id, a.id]

    cache.invalidate()
    listing = client.get("/api/products?collection=diwali-edit").get_json()
    assert [p["id"] for p in listing["products"]] == [c.id, a.id] and listing["total"] == 2
    meta = client.get("/api/content/collections/diwali-edit").get_json()
    assert meta["name"] == "Diwali Edit" and meta["product_count"] == 2

    updated = client.put(f"/api/admin/collections/{body['id']}", headers=headers, json={
        "name": "Diwali Edit", "product_ids": [b.id], "is_active": False})
    assert updated.status_code == 200 and updated.get_json()["product_count"] == 1
    cache.invalidate()
    assert client.get("/api/content/collections/diwali-edit").status_code == 404
    assert client.get("/api/products?collection=diwali-edit").get_json()["total"] == 0

    assert client.delete(f"/api/admin/collections/{body['id']}", headers=headers).status_code == 200
    assert Collection.query.count() == 0


def test_collection_validation(client):
    headers = manager()
    assert client.post("/api/admin/collections", headers=headers, json={"name": "A"}).status_code == 422
    assert client.post("/api/admin/collections", headers=headers, json={"name": "First One"}).status_code == 201
    clash = client.post("/api/admin/collections", headers=headers, json={"name": "first one"})
    assert clash.status_code == 422 and "slug" in clash.get_json()["errors"]
    assert client.post("/api/admin/collections", headers=headers, json={"name": "Ghosts", "product_ids": [424242]}).status_code == 422
    assert client.post("/api/admin/collections", headers=headers, json={"name": "Bad", "slug": "Not A Slug"}).status_code == 422
    assert client.post("/api/admin/collections", headers=headers, json={"name": "Pic", "image_url": "javascript:x"}).status_code == 422
    assert Collection.query.count() == 1


# ══ Media library ════════════════════════════════════════════

def _png():
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), "#F2A900").save(buf, "PNG")
    buf.seek(0)
    return buf


@pytest.fixture()
def fake_storage():
    deleted = []
    with patch("app.routes.admin.merchandising.save_image",
               side_effect=lambda f: f"/static/uploads/{uuid.uuid4().hex}.webp"), \
         patch("app.services.media.delete_files", side_effect=deleted.append):
        yield deleted


def _upload(client, headers, **form):
    return client.post("/api/admin/media", headers=headers, content_type="multipart/form-data",
                       data={"file": (_png(), "marigold.png"), **form})


def test_upload_is_catalogued_and_reusable(client, fake_storage):
    resp = _upload(client, staff(), alt_text="Marigold", source_note="Original artwork")
    assert resp.status_code == 201, resp.get_json()
    asset = resp.get_json()
    assert (asset["width"], asset["height"]) == (40, 30) and asset["alt_text"] == "Marigold"

    # the older per-form upload route lands in the same library
    old = client.post("/api/admin/upload", headers=staff(), content_type="multipart/form-data",
                      data={"file": (_png(), "second.png")})
    assert old.status_code == 201 and old.get_json()["url"].startswith("/static/uploads/")

    listing = client.get("/api/admin/media", headers=staff()).get_json()
    assert listing["total"] == 2 and all(a["used_count"] == 0 for a in listing["assets"])
    assert client.get("/api/admin/media?q=marig", headers=staff()).get_json()["total"] == 1

    patched = client.patch(f"/api/admin/media/{asset['id']}", headers=staff(), json={"alt_text": "A marigold"})
    assert patched.get_json()["alt_text"] == "A marigold"
    assert client.patch(f"/api/admin/media/{asset['id']}", headers=staff(), json={"alt_text": "<x>"}).status_code == 422


def test_upload_rejects_what_is_not_an_image(client, fake_storage):
    bad = client.post("/api/admin/media", headers=staff(), content_type="multipart/form-data",
                      data={"file": (io.BytesIO(b"<svg onload=alert(1)>"), "x.svg")})
    assert bad.status_code == 400
    assert client.post("/api/admin/media", headers=staff()).status_code == 400
    assert MediaAsset.query.count() == 0


def test_image_in_use_is_reported_and_cannot_be_deleted(client, fake_storage):
    asset = _upload(client, manager()).get_json()
    db.session.add(HeroBanner(title="Festive lights", image_url=asset["url"]))
    category = Category(name="Sarees", slug="sarees", image_url=asset["url"])
    db.session.add(category)
    db.session.commit()

    usage = client.get(f"/api/admin/media/{asset['id']}/usage", headers=manager()).get_json()["usage"]
    assert {(u["where"], u["name"]) for u in usage} == {("Hero slide", "Festive lights"), ("Category", "Sarees")}
    assert client.get("/api/admin/media", headers=manager()).get_json()["assets"][0]["used_count"] == 2

    refused = client.delete(f"/api/admin/media/{asset['id']}", headers=manager())
    assert refused.status_code == 409 and len(refused.get_json()["usage"]) == 2
    assert fake_storage == []

    HeroBanner.query.delete()
    category.image_url = None
    db.session.commit()
    assert client.delete(f"/api/admin/media/{asset['id']}", headers=manager()).status_code == 200
    assert fake_storage == [asset["url"]] and MediaAsset.query.count() == 0


# ══ Customers ════════════════════════════════════════════════

def test_customer_detail_has_spend_returns_and_reviews(client):
    user = make_user()
    address = make_address(user)
    product, variant = make_product(price=500, stock=10)
    make_cart(user, [(variant, 2)])
    order, _ = create_order_from_cart(user.id, address.id, "cod")

    body = client.get(f"/api/admin/users/{user.id}", headers=manager()).get_json()
    assert body["order_count"] == 1 and body["lifetime_spend"] == float(order.total_amount)
    assert body["returns"] == [] and body["reviews"] == []
    for secret in ("password", "payment_ref", "token"):
        assert secret not in str(body).lower()

    # a cancelled order is not money spent
    from app.models.enums import OrderStatus
    from app.models.order import Order
    Order.query.filter_by(id=order.id).update({"status": OrderStatus.cancelled})
    db.session.commit()
    assert client.get(f"/api/admin/users/{user.id}", headers=manager()).get_json()["lifetime_spend"] == 0


def test_customer_csv_export(client):
    make_user(email="plain@example.com", full_name="Plain Person")
    make_user(email="tricky@example.com", full_name="=HYPERLINK(\"http://evil\")")
    blocked = make_user(email="blocked@example.com")
    blocked.is_active = False
    db.session.commit()

    resp = client.get("/api/admin/users/export.csv", headers=manager())
    assert resp.status_code == 200 and resp.mimetype == "text/csv"
    assert "attachment" in resp.headers["Content-Disposition"]
    text = resp.get_data(as_text=True)
    header = text.splitlines()[0].lower()
    for forbidden in ("password", "hash", "payment", "address", "token"):
        assert forbidden not in header
    assert "plain@example.com" in text and "'=HYPERLINK" in text
    assert text.count("\n") == 4

    only_blocked = client.get("/api/admin/users/export.csv?active=false", headers=manager()).get_data(as_text=True)
    assert "blocked@example.com" in only_blocked and "plain@example.com" not in only_blocked
    assert AuditLog.query.filter_by(action="export_customers").count() == 2


# ══ SEO ══════════════════════════════════════════════════════

def test_product_meta_fields_and_sitemap(client):
    category = Category(name="Kurtas", slug="kurtas")
    db.session.add(category)
    db.session.commit()
    created = client.post("/api/admin/products", headers=staff(), json={
        "category_id": category.id, "name": "Silk Kurta", "slug": "silk-kurta", "mrp": 2999, "selling_price": 1999,
        "care_details": "Dry clean only.", "meta_title": "Silk Kurta for Men", "meta_description": "Festive silk kurta.",
        "share_image_url": "/static/uploads/share.webp",
    })
    assert created.status_code == 201, created.get_json()
    detail = client.get("/api/products/silk-kurta").get_json()
    assert detail["meta_title"] == "Silk Kurta for Men" and detail["care_details"] == "Dry clean only."
    assert detail["share_image_url"] == "/static/uploads/share.webp" and detail["on_sale"] is False

    db.session.add(Collection(name="Diwali Edit", slug="diwali-edit"))
    db.session.add(Collection(name="Hidden", slug="hidden", is_active=False))
    db.session.commit()
    client.put("/api/admin/pages/shipping", headers=manager(), json={"title": "Shipping", "body_html": "<p>Free over 999.</p>"})

    xml = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/collections/diwali-edit" in xml and "/collections/hidden" not in xml
    assert "/shipping</loc>" in xml and xml.count("/about</loc>") == 1


# ══ Demo content ═════════════════════════════════════════════

def test_demo_mode_tags_what_is_created(client):
    category = Category(name="Real", slug="real")
    db.session.add(category)
    db.session.commit()
    product = {"category_id": category.id, "name": "Demo Tee", "slug": "demo-tee", "mrp": 999, "selling_price": 799}

    client.post("/api/admin/products", headers={**owner(), **DEMO}, json=product)
    client.post("/api/admin/products", headers=owner(), json={**product, "name": "Real Tee", "slug": "real-tee"})
    client.post("/api/admin/faq", headers={**owner(), **DEMO}, json={"question": "Demo question?", "answer": "Yes."})
    client.put("/api/admin/pages/about", headers={**owner(), **DEMO}, json={"title": "About", "body_html": "<p>Demo text</p>"})

    assert Product.query.filter_by(slug="demo-tee").one().is_demo is True
    assert Product.query.filter_by(slug="real-tee").one().is_demo is False
    assert FaqItem.query.one().is_demo is True and CmsPage.query.filter_by(slug="about").one().is_demo is True
    # the header means nothing outside the admin API
    client.post("/api/auth/register", headers=DEMO, json={
        "full_name": "Real Customer", "email": "real@example.com", "password": "CorrectHorse1!"})
    assert User.query.filter_by(email="real@example.com").one().is_demo is False

    counts = client.get("/api/admin/demo", headers=owner()).get_json()
    assert counts["counts"]["products"] == 1 and counts["counts"]["faq_entries"] == 1 and counts["total"] == 3

    # the owner rewriting a demo page makes it theirs
    client.put("/api/admin/pages/about", headers=owner(), json={"title": "About", "body_html": "<p>Ours</p>"})
    assert CmsPage.query.filter_by(slug="about").one().is_demo is False


def test_remove_demo_content_needs_the_phrase_and_spares_real_data(client, fake_storage):
    headers = {**owner(), **DEMO}
    real_category = Category(name="Real", slug="real")
    db.session.add(real_category)
    db.session.commit()

    demo_category = client.post("/api/admin/categories", headers=headers, json={"name": "Demo Cat", "slug": "demo-cat"}).get_json()
    asset = _upload(client, headers).get_json()
    for slug in ("demo-a", "demo-b"):
        created = client.post("/api/admin/products", headers=headers, json={
            "category_id": demo_category["id"], "name": slug, "slug": slug, "mrp": 999, "selling_price": 799}).get_json()
        client.post(f"/api/admin/products/{created['id']}/variants", headers=headers,
                    json={"size": "M", "color_name": "Black", "color_hex": "#000000", "stock_qty": 5})
        client.post(f"/api/admin/products/{created['id']}/images", headers=headers,
                    json={"image_url": asset["url"], "is_primary": True})
    client.post("/api/admin/products", headers=owner(), json={
        "category_id": real_category.id, "name": "Real", "slug": "real-one", "mrp": 999, "selling_price": 799})
    client.post("/api/admin/coupons", headers=headers, json={"code": "DEMO10", "discount_type": "percentage", "discount_value": 10})
    client.post("/api/admin/faq", headers=headers, json={"question": "Demo question?", "answer": "Yes."})
    client.put("/api/admin/pages/terms", headers=headers, json={"title": "Terms", "body_html": "<p>Demo</p>"})
    client.post("/api/admin/staff", headers=headers, json={"email": "demo.staff@example.com", "full_name": "Demo Staff"})

    # a demo customer with an order for demo-a, and a REAL customer who also bought demo-b
    demo_user, real_user = make_user(email="demo.customer@example.com"), make_user(email="real.customer@example.com")
    client.patch(f"/api/admin/users/{demo_user.id}", headers=owner(), json={"is_demo": True})
    variants = {p.slug: p.variants[0] for p in Product.query.filter(Product.slug.in_(["demo-a", "demo-b"]))}
    for user, slug in ((demo_user, "demo-a"), (real_user, "demo-b")):
        make_cart(user, [(variants[slug], 1)])
        _, err = create_order_from_cart(user.id, make_address(user).id, "cod")
        assert err is None

    assert client.post("/api/admin/demo/remove", headers=owner(), json={"confirm": "yes"}).status_code == 422
    assert Product.query.count() == 3
    assert client.post("/api/admin/demo/remove", headers=manager(), json={"confirm": "REMOVE DEMO"}).status_code == 403

    resp = client.post("/api/admin/demo/remove", headers=owner(), json={"confirm": "REMOVE DEMO"})
    assert resp.status_code == 200, resp.get_json()
    body = resp.get_json()
    assert body["removed"]["products"] == 1 and body["removed"]["customers"] == 1 and body["removed"]["orders"] == 1
    assert body["removed"]["staff"] == 1 and body["removed"]["coupons"] == 1 and body["removed"]["pages"] == 1
    assert any("demo-b" in line for line in body["kept"])

    db.session.expire_all()
    assert {p.slug for p in Product.query.all()} == {"demo-b", "real-one"}
    assert Product.query.filter_by(slug="demo-b").one().is_active is False      # a real order points at it
    assert User.query.filter_by(email="real.customer@example.com").count() == 1
    assert User.query.filter_by(email="demo.customer@example.com").count() == 0
    assert Coupon.query.count() == 0 and FaqItem.query.count() == 0
    assert CmsPage.query.filter_by(slug="terms").one().body_html == ""
    assert Admin.query.filter_by(email="demo.staff@example.com").count() == 0
    assert Category.query.filter_by(slug="real").count() == 1
    assert Category.query.filter_by(slug="demo-cat").one().is_active is False    # still holds demo-b
    assert MediaAsset.query.count() == 1 and fake_storage == []                  # still used by demo-b
    assert client.get("/api/admin/demo", headers=owner()).get_json()["counts"]["products"] == 1
    assert AuditLog.query.filter_by(entity_type="demo").count() == 1


def test_remove_demo_content_command(app, fake_storage):
    category = Category(name="Demo", slug="demo", is_demo=True)
    db.session.add(category)
    db.session.add(FaqItem(question="Demo?", answer="Yes", is_demo=True))
    db.session.add(MediaAsset(url="/static/uploads/demo.webp", is_demo=True))
    db.session.commit()

    runner = app.test_cli_runner()
    declined = runner.invoke(args=["remove-demo-content"], input="n\n")
    assert "Nothing removed" in declined.output and FaqItem.query.count() == 1

    done = runner.invoke(args=["remove-demo-content", "--yes"])
    assert done.exit_code == 0 and "Demo content removed" in done.output
    assert FaqItem.query.count() == 0 and Category.query.count() == 0 and MediaAsset.query.count() == 0
    assert fake_storage == ["/static/uploads/demo.webp"]
    assert "no demo content" in runner.invoke(args=["remove-demo-content", "--yes"]).output
