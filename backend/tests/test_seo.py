"""Tests for the sitemap.xml + robots.txt endpoints."""
from tests.factories import make_product, _default_category


def test_sitemap_lists_static_and_products(app, client):
    _default_category()  # active category
    make_product(slug="silk-kurta", stock=5)

    resp = client.get("/sitemap.xml")

    assert resp.status_code == 200
    assert "xml" in resp.mimetype
    body = resp.get_data(as_text=True)
    assert "<loc>" in body
    assert "/product/silk-kurta" in body   # product URL present
    assert "/shop" in body                 # static route present


def test_sitemap_excludes_inactive_products(app, client):
    from app.extensions import db
    _, variant = make_product(slug="hidden-item", stock=1)
    variant.product.is_active = False
    db.session.commit()

    body = client.get("/sitemap.xml").get_data(as_text=True)
    assert "/product/hidden-item" not in body


def test_robots_txt(app, client, monkeypatch):
    # Indexing is off by default now (see test_jobs_and_indexing.py); this
    # covers the shape of robots.txt once it has been switched on.
    monkeypatch.setitem(app.config, "INDEXING", True)

    resp = client.get("/robots.txt")

    assert resp.status_code == 200
    assert resp.mimetype == "text/plain"
    body = resp.get_data(as_text=True)
    assert "User-agent: *" in body
    assert "Disallow: /admin" in body
    assert "Sitemap:" in body
