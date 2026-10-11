"""Pre-launch security audit, as tests.

Sweeps rather than samples wherever it can: every route in the URL map is
visited without a token and (for the admin API) with a customer's token, so a
route added later is covered without anyone remembering to.
"""
import io
import re

import pytest
from PIL import Image

from app.extensions import db
from app.models.cart import CartItem
from app.models.engagement import ProductReview
from app.models.enums import OrderStatus
from app.models.order import Order
from app.models.owner import MediaAsset
from app.services.order_service import create_order_from_cart
from tests.factories import make_address, make_cart, make_product, make_user
from tests.helpers import admin_headers, customer_headers

# Routes that are meant to answer without a signed-in user. Everything else
# under /api must refuse an anonymous caller. Adding a public route means
# adding it here, on purpose.
PUBLIC = {
    ("POST", "/api/auth/register"), ("POST", "/api/auth/login"), ("POST", "/api/auth/google"),
    ("POST", "/api/auth/otp/send"), ("POST", "/api/auth/otp/verify"),
    ("POST", "/api/auth/forgot-password"), ("POST", "/api/auth/reset-password"),
    ("POST", "/api/auth/refresh"), ("POST", "/api/auth/logout"),
    ("POST", "/api/admin/auth/login"), ("POST", "/api/admin/auth/refresh"), ("POST", "/api/admin/auth/logout"),
    ("GET", "/api/products"), ("GET", "/api/products/facets"), ("GET", "/api/products/<slug>"),
    ("GET", "/api/categories"), ("GET", "/api/offers"), ("GET", "/api/reviews/product/<int:product_id>"),
    ("GET", "/api/cms/banners"), ("GET", "/api/cms/announcements"), ("GET", "/api/cms/promo-banners"),
    ("GET", "/api/cms/testimonials"), ("GET", "/api/cms/features"), ("GET", "/api/cms/settings"),
    ("GET", "/api/cms/features-available"),
    ("GET", "/api/content/layout"), ("GET", "/api/content/faq"), ("GET", "/api/content/pages/<slug>"),
    ("GET", "/api/content/collections/<slug>"),
    ("POST", "/api/contact"), ("POST", "/api/wholesale"),
    ("POST", "/api/newsletter/subscribe"), ("POST", "/api/newsletter/unsubscribe"),
    ("POST", "/api/payments/webhook"), ("GET", "/api/shipping/serviceability"),
    ("GET", "/api/health"),
}


def _api_routes(app):
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api/"):
            continue
        for method in sorted(rule.methods - {"HEAD", "OPTIONS"}):
            yield method, rule.rule


def _concrete(rule):
    """/api/orders/<int:order_id> -> /api/orders/987654"""
    rule = re.sub(r"<int:[^>]+>", "987654", rule)
    return re.sub(r"<[^>]+>", "00000000-0000-4000-8000-000000000000", rule)


# ── Anonymous and wrong-kind-of-user sweeps ───────────────────

def test_every_non_public_route_refuses_an_anonymous_caller(app, client):
    checked = 0
    for method, rule in _api_routes(app):
        if (method, rule) in PUBLIC:
            continue
        resp = client.open(_concrete(rule), method=method, json={})
        assert resp.status_code == 401, f"{method} {rule} answered {resp.status_code} without a token"
        checked += 1
    assert checked > 120


def test_public_list_has_no_stale_entries(app):
    """A route removed from the app must come off the public list too."""
    existing = set(_api_routes(app))
    assert PUBLIC <= existing, PUBLIC - existing


def test_a_customer_token_opens_nothing_in_the_admin_api(app, client):
    headers = customer_headers(make_user())
    open_to_all = {"/api/admin/auth/login", "/api/admin/auth/refresh", "/api/admin/auth/logout"}
    checked = 0
    for method, rule in _api_routes(app):
        if not rule.startswith("/api/admin/") or rule in open_to_all:
            continue
        resp = client.open(_concrete(rule), method=method, json={}, headers=headers)
        assert resp.status_code == 403, f"{method} {rule} answered {resp.status_code} to a customer"
        checked += 1
    assert checked > 100


def test_an_admin_token_is_not_a_customer_token(client):
    """Admin and customer are separate surfaces: an Owner has no cart."""
    headers = admin_headers()
    for method, url in (("GET", "/api/cart"), ("GET", "/api/orders"), ("GET", "/api/profile"),
                        ("GET", "/api/addresses"), ("GET", "/api/wishlist"), ("GET", "/api/returns")):
        resp = client.open(url, method=method, headers=headers)
        assert resp.status_code in (401, 403, 404), f"{method} {url} -> {resp.status_code}"
        assert "items" not in (resp.get_json() or {})


# ── One customer cannot reach another's data ──────────────────

@pytest.fixture()
def two_customers(client):
    owner, intruder = make_user(email="owner@example.com"), make_user(email="intruder@example.com")
    address = make_address(owner)
    product, variant = make_product(price=500, stock=10)
    make_cart(owner, [(variant, 2)])
    order, _ = create_order_from_cart(owner.id, address.id, "cod")
    Order.query.filter_by(id=order.id).update({"status": OrderStatus.delivered})
    db.session.commit()
    ret = client.post("/api/returns", headers=customer_headers(owner),
                      json={"order_item_id": order.items[0].id, "reason": "changed_mind"}).get_json()
    # something in the owner's cart and wishlist, too
    client.post("/api/cart/items", headers=customer_headers(owner), json={"variant_id": variant.id, "quantity": 1})
    client.post("/api/wishlist", headers=customer_headers(owner), json={"product_id": product.id})
    line = CartItem.query.one()
    return {"owner": owner, "intruder": intruder, "order": order, "address": address,
            "return_id": ret["id"], "line_id": line.id, "product": product, "variant": variant}


def test_idor_every_customer_route_with_an_id(client, two_customers):
    t = two_customers
    as_intruder = customer_headers(t["intruder"])
    order_id, item_id, address_id = t["order"].id, t["order"].items[0].id, t["address"].id
    address_body = {"full_name": "Intruder", "phone": "+919800000000", "line1": "1 Road", "city": "Patna",
                    "state": "Bihar", "pin_code": "800001"}
    attempts = [
        ("GET", f"/api/orders/{order_id}", None),
        ("POST", f"/api/orders/{order_id}/cancel", None),
        ("GET", f"/api/returns/{t['return_id']}", None),
        ("GET", f"/api/returns/eligibility/{order_id}", None),
        ("POST", "/api/returns", {"order_item_id": item_id, "reason": "damaged"}),
        ("PUT", f"/api/addresses/{address_id}", address_body),
        ("DELETE", f"/api/addresses/{address_id}", None),
        ("PATCH", f"/api/cart/items/{t['line_id']}", {"quantity": 5}),
        ("DELETE", f"/api/cart/items/{t['line_id']}", None),
    ]
    for method, url, body in attempts:
        resp = client.open(url, method=method, json=body, headers=as_intruder)
        assert resp.status_code == 404, f"{method} {url} answered {resp.status_code} to another customer"
        assert "owner@example.com" not in resp.get_data(as_text=True)

    # placing an order against someone else's address
    client.post("/api/cart/items", headers=as_intruder, json={"variant_id": t["variant"].id, "quantity": 1})
    resp = client.post("/api/orders", headers=as_intruder, json={"address_id": address_id, "payment_method": "cod"})
    assert resp.status_code == 404

    # lists show only the caller's own
    assert client.get("/api/orders", headers=as_intruder).get_json()["orders"] == []
    assert client.get("/api/returns", headers=as_intruder).get_json()["returns"] == []
    assert client.get("/api/addresses", headers=as_intruder).get_json()["addresses"] == []
    assert client.get("/api/wishlist", headers=as_intruder).get_json()["items"] == []

    # and nothing of the owner's changed
    db.session.expire_all()
    assert db.session.get(Order, order_id).status == OrderStatus.return_requested
    assert CartItem.query.filter_by(id=t["line_id"]).one().quantity == 1
    assert client.get("/api/addresses", headers=customer_headers(t["owner"])).get_json()["addresses"][0]["full_name"]


def test_a_review_cannot_be_written_as_someone_else(client, two_customers):
    t = two_customers
    resp = client.post("/api/reviews", headers=customer_headers(t["intruder"]),
                       json={"product_id": t["product"].id, "rating": 1, "body": "x", "user_id": str(t["owner"].id)})
    # accepted or refused, it is never attributed to the owner
    assert resp.status_code in (201, 403, 409, 422)
    assert ProductReview.query.filter_by(user_id=t["owner"].id).count() == 0


# ── Text that people type is stored as text ───────────────────

XSS = '<img src=x onerror=alert(1)><script>alert(2)</script>"\'>'


def test_script_in_customer_text_comes_back_as_inert_json(client, two_customers):
    """The storefront is React, which renders strings as text. What matters on
    the server is that such text is never served as HTML and never rewritten
    into something else."""
    t = two_customers
    owner = customer_headers(t["owner"])
    client.put("/api/profile", headers=owner, json={"full_name": XSS[:100]})
    client.post("/api/contact", json={"name": XSS[:80], "email": "x@example.com", "subject": "general", "message": XSS * 2})
    for url, headers in (("/api/profile", owner), (f"/api/reviews/product/{t['product'].id}", None),
                         ("/api/admin/contact-messages", admin_headers())):
        resp = client.get(url, headers=headers)
        assert resp.status_code == 200
        assert resp.mimetype == "application/json"
        assert resp.headers["X-Content-Type-Options"] == "nosniff"


def test_order_email_escapes_names(app, client, two_customers):
    from app.services.email import order_confirmation_content

    t = two_customers
    t["owner"].full_name = '<script>alert("me")</script>'
    t["product"].name = '<img src=x onerror=alert(1)> Kurta'
    db.session.commit()
    _subject, html, _text = order_confirmation_content(db.session.get(Order, t["order"].id))
    assert "<script>" not in html and "<img" not in html
    assert "&lt;script&gt;" in html and "&lt;img src=x onerror=alert(1)&gt; Kurta" in html


# ── Uploads ───────────────────────────────────────────────────

def _image_bytes(fmt="PNG", size=(32, 32)):
    buf = io.BytesIO()
    Image.new("RGB", size, "#336699").save(buf, fmt)
    return buf.getvalue()


@pytest.fixture()
def no_disk(monkeypatch):
    """Let save_image run for real (validation, re-encoding) but keep files off the disk."""
    written = []
    monkeypatch.setattr("app.services.storage._save_bytes_to_disk",
                        lambda data, name: written.append((name, data)) or f"/static/uploads/{name}")
    return written


def _post_file(client, name, data, url="/api/admin/media"):
    return client.post(url, headers=admin_headers(), content_type="multipart/form-data",
                       data={"file": (io.BytesIO(data), name)})


@pytest.mark.parametrize("name,data", [
    ("page.png", b"<html><script>alert(1)</script></html>"),              # HTML wearing a .png name
    ("photo.jpg", b"GIF89a<script>alert(1)</script>"),                    # a broken "GIF" header
    ("anim.gif", b"<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'/>"),  # SVG wearing a .gif name
    ("logo.svg", b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"),
    ("shell.php", _image_bytes()),                                        # a real image with a script's name
    ("double.png.exe", _image_bytes()),
    ("empty.png", b""),
    ("notes.txt", b"hello"),
])
def test_upload_refuses_what_is_not_an_allowed_image(client, no_disk, name, data):
    for url in ("/api/admin/media", "/api/admin/upload"):
        resp = _post_file(client, name, data, url)
        assert resp.status_code == 400, f"{url} {name} -> {resp.status_code}"
    assert no_disk == [] and MediaAsset.query.count() == 0


def test_upload_is_judged_by_content_and_re_encoded(client, no_disk):
    """A JPEG named .png is accepted as what it is, and never stored raw."""
    original = _image_bytes("JPEG")
    resp = _post_file(client, "really-a-jpeg.png", original)
    assert resp.status_code == 201, resp.get_json()
    name, stored = no_disk[0]
    assert name.endswith(".webp") and stored != original
    assert Image.open(io.BytesIO(stored)).format == "WEBP"
    # the stored name is ours, not the uploader's
    assert "really-a-jpeg" not in resp.get_json()["url"] and ".." not in resp.get_json()["url"]


def test_upload_size_limit_and_pixel_limit(client, no_disk, monkeypatch):
    too_big = _image_bytes() + b"\0" * (5 * 1024 * 1024)
    assert _post_file(client, "big.png", too_big).status_code == 400
    monkeypatch.setattr("app.services.storage.MAX_PIXELS", 500)
    assert _post_file(client, "wide.png", _image_bytes(size=(40, 40))).status_code == 400
    assert no_disk == []


def test_upload_path_traversal_in_the_file_name_is_harmless(client, no_disk):
    resp = _post_file(client, "../../../etc/passwd.png", _image_bytes())
    assert resp.status_code == 201
    assert re.fullmatch(r"/static/uploads/[0-9a-f]{32}\.webp", resp.get_json()["url"])


# ── Headers, CORS, cookies ────────────────────────────────────

def test_security_headers_on_every_kind_of_response(client):
    for resp in (client.get("/api/products"), client.get("/api/nope"), client.get("/api/cart"),
                 client.post("/api/auth/login", json={})):
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
        assert resp.headers["X-Frame-Options"] == "DENY"
        assert "default-src 'none'" in resp.headers["Content-Security-Policy"]
        assert resp.headers["Referrer-Policy"]


def test_cors_allows_only_the_storefront(app, client):
    own = app.config["FRONTEND_ORIGIN"]
    ok = client.get("/api/products", headers={"Origin": own})
    assert ok.headers.get("Access-Control-Allow-Origin") == own
    for origin in ("https://evil.example", "null", own + ".evil.example"):
        resp = client.get("/api/products", headers={"Origin": origin})
        assert resp.headers.get("Access-Control-Allow-Origin") in (None, own)
        assert resp.headers.get("Access-Control-Allow-Origin") != "*"
    preflight = client.options("/api/orders", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert preflight.headers.get("Access-Control-Allow-Origin") is None


def test_refresh_cookies_are_http_only_and_need_the_csrf_header(client):
    client.post("/api/auth/register", json={
        "full_name": "Cookie Check", "email": "cookie@example.com", "password": "CorrectHorse1!"})
    cookies = {c.key: c for c in client._cookies.values()} if hasattr(client, "_cookies") else {}
    refresh = next((c for name, c in cookies.items() if "refresh" in name and "csrf" not in name), None)
    assert refresh is not None and refresh.http_only
    # the cookie alone (what a cross-site form post would carry) is not enough
    assert client.post("/api/auth/refresh").status_code == 401
    csrf = next(c.value for name, c in cookies.items() if "csrf" in name)
    assert client.post("/api/auth/refresh", headers={"X-CSRF-TOKEN": csrf}).status_code == 200


def test_state_changing_routes_ignore_cookies_without_a_bearer_token(client):
    """Every write is authorised by the Authorization header, which a
    cross-site request cannot set — so there is nothing for CSRF to ride on."""
    client.post("/api/auth/register", json={
        "full_name": "Csrf Check", "email": "csrf@example.com", "password": "CorrectHorse1!"})
    # the browser still holds the refresh cookie; no Authorization header is sent
    for method, url in (("POST", "/api/orders"), ("POST", "/api/cart/items"), ("PUT", "/api/profile"),
                        ("POST", "/api/addresses"), ("DELETE", "/api/cart/coupon"), ("PUT", "/api/profile/password")):
        assert client.open(url, method=method, json={}).status_code == 401, url


def test_errors_do_not_leak_internals(client):
    resp = client.get("/api/orders/not-a-number", headers=customer_headers(make_user()))
    assert resp.status_code == 404
    body = resp.get_data(as_text=True)
    for leak in ("Traceback", "sqlalchemy", "psycopg", "File \"", "werkzeug"):
        assert leak not in body
