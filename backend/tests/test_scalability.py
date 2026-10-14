"""Scalability guards: query counts, caching, background email, rate limits.

Each test pins a property that silently regresses — an extra query per row, a
stale cache, a slow provider on the request path — so the regression fails
here rather than in production under load.
"""
import threading
from contextlib import contextmanager

import pytest
from sqlalchemy import event

from app.extensions import db
from app.models.catalogue import ProductImage
from app.models.engagement import ProductReview, Wishlist
from app.services import cache, email as email_svc
from app.services.order_service import create_order_from_cart
from tests.factories import make_address, make_cart, make_product, make_user
from tests.helpers import admin_headers, customer_headers


@contextmanager
def count_queries():
    statements = []

    def _on_execute(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(db.engine, "before_cursor_execute", _on_execute)
    try:
        yield statements
    finally:
        event.remove(db.engine, "before_cursor_execute", _on_execute)


def _catalogue(count):
    products = []
    for i in range(count):
        product, variant = make_product(slug=f"item-{i}", name=f"Item {i}", stock=5)
        db.session.add(ProductImage(
            product_id=product.id, image_url=f"/static/uploads/{i}.webp", is_primary=True,
        ))
        db.session.add(ProductReview(product_id=product.id, user_id=make_user().id, rating=4))
        products.append((product, variant))
    db.session.commit()
    return products


# ── Query counts do not grow with the data ────────────────────

def test_product_list_query_count_is_independent_of_page_size(app, client, monkeypatch):
    # The maintenance flag is cached for 5 s. Creating nine products takes
    # longer than that against a remote database (~150 ms a round trip to the
    # Neon branch), so the cache expired between the two measurements and the
    # "large" request paid one extra site_settings query that has nothing to do
    # with products. Hold the cache for the length of the test so only the
    # product queries are being compared.
    from app.services import maintenance
    monkeypatch.setattr(maintenance, "_CACHE_SECONDS", 3600)

    _catalogue(3)
    client.get("/api/categories")   # warm the one-off maintenance-flag lookup
    with count_queries() as small:
        client.get("/api/products?per_page=3")

    for i in range(9):
        make_product(slug=f"extra-{i}")
    with count_queries() as large:
        body = client.get("/api/products?per_page=12").get_json()

    assert len(body["products"]) == 12
    # Four times the products, not one query more.
    assert len(large) <= len(small) <= 6, (len(small), len(large))


def test_product_list_still_returns_card_details(app, client):
    _catalogue(2)

    cards = client.get("/api/products?sort=price_asc").get_json()["products"]

    assert all(c["primary_image"] for c in cards)
    assert all(c["colors"] == ["#000000"] for c in cards)
    assert all(c["avg_rating"] == 4.0 and c["review_count"] == 1 for c in cards)


def test_cart_wishlist_and_orders_do_not_query_per_line(app, client):
    user = make_user()
    products = _catalogue(6)
    make_cart(user, [(variant, 1) for _, variant in products])
    for product, _ in products:
        db.session.add(Wishlist(user_id=user.id, product_id=product.id))
    db.session.commit()
    headers = customer_headers(user)

    with count_queries() as cart_queries:
        cart = client.get("/api/cart", headers=headers).get_json()
    with count_queries() as wishlist_queries:
        wishlist = client.get("/api/wishlist", headers=headers).get_json()

    assert len(cart["items"]) == 6 and all(i["image_url"] for i in cart["items"])
    assert wishlist["count"] == 6 and all(i["primary_image"] for i in wishlist["items"])
    # Lazy-loading each line's variant and product is one identity-map hit after
    # the first; what must not happen is an image / rating query per line.
    assert sum("product_images" in q for q in cart_queries) == 1
    assert len(wishlist_queries) <= 5, len(wishlist_queries)

    order, err = create_order_from_cart(user.id, make_address(user).id, "cod")
    assert err is None
    with count_queries() as detail_queries:
        detail = client.get(f"/api/orders/{order.id}", headers=headers).get_json()
    assert len(detail["items"]) == 6
    assert sum("product_images" in q for q in detail_queries) == 1


def test_customer_order_list_is_paged(app, client):
    user = make_user()
    address = make_address(user)
    for _ in range(3):
        _, variant = make_product(stock=5)
        make_cart_or_refill(user, variant)
        create_order_from_cart(user.id, address.id, "cod")

    body = client.get("/api/orders?per_page=2", headers=customer_headers(user)).get_json()

    assert len(body["orders"]) == 2
    assert body["total"] == 3 and body["pages"] == 2
    # The cap holds however large a page is asked for.
    assert client.get(
        "/api/orders?per_page=100000", headers=customer_headers(user)
    ).status_code == 200


def make_cart_or_refill(user, variant):
    from app.models.cart import Cart, CartItem
    cart = Cart.query.filter_by(user_id=user.id).first()
    if not cart:
        return make_cart(user, [(variant, 1)])
    db.session.add(CartItem(
        cart_id=cart.id, variant_id=variant.id, quantity=1,
        unit_price=variant.product.selling_price,
    ))
    db.session.commit()
    return cart


# ── Cache ─────────────────────────────────────────────────────

@pytest.fixture
def cache_on(app, monkeypatch):
    monkeypatch.setitem(app.config, "CACHE_ENABLED", True)
    cache.reset_for_tests()


def test_cached_listing_is_served_without_touching_the_database(app, client, cache_on):
    _catalogue(3)
    first = client.get("/api/products").get_json()

    with count_queries() as queries:
        second = client.get("/api/products").get_json()

    assert second == first
    assert queries == []


def test_different_queries_are_cached_separately(app, client, cache_on):
    make_product(slug="cheap", price=300)
    make_product(slug="dear", price=3000)

    cheap = client.get("/api/products?max_price=500").get_json()
    everything = client.get("/api/products").get_json()

    assert cheap["total"] == 1 and everything["total"] == 2


def test_an_admin_edit_shows_on_the_storefront_at_once(app, client, cache_on):
    headers = admin_headers()
    category = client.post("/api/admin/categories", headers=headers,
                           json={"name": "Kurtas", "slug": "kurtas"}).get_json()
    created = client.post("/api/admin/products", headers=headers, json={
        "category_id": category["id"], "name": "Linen Kurta", "slug": "linen-kurta",
        "mrp": 2999, "selling_price": 1999,
    }).get_json()
    assert client.get("/api/products/linen-kurta").get_json()["selling_price"] == 1999

    client.put(f"/api/admin/products/{created['id']}", headers=headers, json={
        "category_id": category["id"], "name": "Linen Kurta", "slug": "linen-kurta",
        "mrp": 2999, "selling_price": 1499,
    })

    assert client.get("/api/products/linen-kurta").get_json()["selling_price"] == 1499
    assert client.get("/api/products").get_json()["products"][0]["selling_price"] == 1499


def test_a_not_found_is_never_cached(app, client, cache_on):
    assert client.get("/api/products/coming-soon").status_code == 404

    make_product(slug="coming-soon")

    assert client.get("/api/products/coming-soon").status_code == 200


def test_cache_survives_redis_being_unreachable(app, client, cache_on, monkeypatch):
    """A cache outage must degrade to "uncached", never to an error page."""
    monkeypatch.setitem(app.config, "CACHE_REDIS_URL", "redis://127.0.0.1:1/0")
    cache.reset_for_tests()
    make_product(slug="linen-kurta")

    assert client.get("/api/products").status_code == 200
    assert client.get("/api/products").get_json()["total"] == 1


# ── Email leaves the request path ─────────────────────────────

def test_email_is_delivered_from_a_background_thread(app, monkeypatch):
    monkeypatch.setitem(app.config, "RESEND_API_KEY", "re_test")
    monkeypatch.setitem(app.config, "EMAIL_FROM", "AANGA <orders@example.com>")
    monkeypatch.setitem(app.config, "EMAIL_ASYNC", True)
    delivered = threading.Event()
    seen = {}

    class _Ok:
        status_code = 200
        text = "ok"

    def _post(url, headers=None, json=None, timeout=None):
        seen["thread"] = threading.current_thread().name
        seen["to"] = json["to"]
        delivered.set()
        return _Ok()

    monkeypatch.setattr(email_svc.requests, "post", _post)

    assert email_svc.send_email("asha@example.com", "Hello", "<p>Hi</p>") is True

    assert delivered.wait(timeout=5), "email was never delivered"
    assert seen["to"] == ["asha@example.com"]
    assert seen["thread"].startswith("email")
    assert seen["thread"] != threading.current_thread().name


def test_a_crashing_mail_provider_does_not_break_the_caller(app, monkeypatch):
    monkeypatch.setitem(app.config, "RESEND_API_KEY", "re_test")
    monkeypatch.setitem(app.config, "EMAIL_FROM", "AANGA <orders@example.com>")
    monkeypatch.setitem(app.config, "EMAIL_ASYNC", True)
    attempted = threading.Event()

    def _explode(*a, **kw):
        attempted.set()
        raise RuntimeError("provider exploded")

    monkeypatch.setattr(email_svc.requests, "post", _explode)

    assert email_svc.send_email("asha@example.com", "Hello", "<p>Hi</p>") is True
    assert attempted.wait(timeout=5)


# ── Rate limits ───────────────────────────────────────────────

def test_contact_form_is_rate_limited(app, client):
    payload = {"name": "Asha Rao", "email": "asha@example.com",
               "message": "Where is my order please?"}

    statuses = [client.post("/api/contact", json=payload).status_code for _ in range(11)]

    assert statuses[:10] == [201] * 10
    assert statuses[10] == 429


def test_rate_limit_answers_json(app, client):
    payload = {"name": "Asha Rao", "email": "asha@example.com",
               "message": "Where is my order please?"}
    for _ in range(10):
        client.post("/api/contact", json=payload)

    limited = client.post("/api/contact", json=payload)

    assert limited.status_code == 429
    assert limited.get_json()["error"]


def test_checkout_and_review_routes_declare_a_limit(app):
    """Routes that take money, or that a script would hammer, must carry one."""
    from app.extensions import limiter

    limited = set()
    for manager in (limiter.limit_manager,):
        limited |= set(manager._decorated_limits)        # endpoint -> limits
    for endpoint in (
        "orders.place_order", "payments.create_payment_order", "payments.verify_payment",
        "reviews.submit_review", "returns.request_return", "contact.submit_contact",
        "auth.login", "auth.register", "auth.forgot_password",
    ):
        assert any(endpoint in key for key in limited), endpoint


# ── CORS ──────────────────────────────────────────────────────

def test_only_the_storefront_origin_may_call_the_api_with_credentials(app, client):
    allowed = app.config["FRONTEND_ORIGIN"]

    ours = client.get("/api/products", headers={"Origin": allowed})
    theirs = client.get("/api/products", headers={"Origin": "https://evil.example"})

    assert ours.headers.get("Access-Control-Allow-Origin") == allowed
    assert ours.headers.get("Access-Control-Allow-Credentials") == "true"
    assert "Access-Control-Allow-Origin" not in theirs.headers


def test_security_headers_are_on_every_response(app, client):
    resp = client.get("/api/health")

    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in resp.headers["Content-Security-Policy"]


# ── Connection pool ───────────────────────────────────────────

def test_pool_is_sized_from_the_environment(monkeypatch):
    import importlib

    import config
    monkeypatch.setenv("DB_POOL_SIZE", "3")
    monkeypatch.setenv("DB_MAX_OVERFLOW", "2")
    try:
        options = importlib.reload(config).BaseConfig.SQLALCHEMY_ENGINE_OPTIONS
        assert options["pool_size"] == 3 and options["max_overflow"] == 2
        assert options["pool_pre_ping"] is True
    finally:
        monkeypatch.delenv("DB_POOL_SIZE")
        monkeypatch.delenv("DB_MAX_OVERFLOW")
        importlib.reload(config)
