"""Admin hero banner CRUD — with the decorative badge fields.

The badges (pill_label/pill_value, chip_value/chip_label) match the reference
hero design and must round-trip through the admin API and surface on the public
CMS endpoint the storefront reads.
"""
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.admin import Admin

PASSWORD = "AdminPass123!"


def _auth(client):
    db.session.add(Admin(
        email="banner-admin@example.com",
        password_hash=generate_password_hash(PASSWORD),
        full_name="Banner Admin",
        role="master",
    ))
    db.session.commit()
    resp = client.post(
        "/api/admin/auth/login",
        json={"email": "banner-admin@example.com", "password": PASSWORD},
    )
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


_BANNER = {
    "title": "Wear the Story of India's Finest",
    "subtitle": "Summer Collection 2026",
    "image_url": "https://example.com/hero.webp",
    "link_url": "/shop", "link_text": "Shop Now",
    "pill_label": "This Season", "pill_value": "Summer Edit '26",
    "chip_value": "40%", "chip_label": "Off Sale Items",
}


def test_create_banner_persists_badges(app, client):
    headers = _auth(client)

    resp = client.post("/api/admin/banners", json=_BANNER, headers=headers)

    assert resp.status_code == 201
    body = resp.get_json()
    assert body["pill_label"] == "This Season"
    assert body["pill_value"] == "Summer Edit '26"
    assert body["chip_value"] == "40%"
    assert body["chip_label"] == "Off Sale Items"


def test_public_cms_exposes_badges(app, client):
    headers = _auth(client)
    client.post("/api/admin/banners", json=_BANNER, headers=headers)

    # Public storefront endpoint — no auth.
    resp = client.get("/api/cms/banners")

    assert resp.status_code == 200
    banner = resp.get_json()["banners"][0]
    assert banner["pill_value"] == "Summer Edit '26"
    assert banner["chip_value"] == "40%"
    assert banner["chip_label"] == "Off Sale Items"


def test_badges_are_optional(app, client):
    headers = _auth(client)
    payload = {"title": "Plain banner", "image_url": "https://example.com/x.webp"}

    resp = client.post("/api/admin/banners", json=payload, headers=headers)

    assert resp.status_code == 201
    body = resp.get_json()
    assert body["pill_value"] is None
    assert body["chip_value"] is None


def test_update_banner_changes_badges(app, client):
    headers = _auth(client)
    created = client.post("/api/admin/banners", json=_BANNER, headers=headers).get_json()

    updated = dict(_BANNER, chip_value="50%", pill_value="Winter Edit '26")
    resp = client.put(f"/api/admin/banners/{created['id']}", json=updated, headers=headers)

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["chip_value"] == "50%"
    assert body["pill_value"] == "Winter Edit '26"
