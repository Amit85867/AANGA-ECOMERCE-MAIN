"""Create / list / update / delete for the admin resources that share one shape.

Each resource is described once; the same four checks run against all of them,
so a new admin resource gets full CRUD coverage by adding a row here.
"""
import pytest

from tests.helpers import admin_headers

# (path, list key, create payload, update payload, field the update changes)
RESOURCES = {
    "announcements": (
        "/api/admin/announcements", "announcements",
        {"text": "Free shipping over 999"},
        {"text": "Free shipping this week"},
        "text",
    ),
    "banners": (
        "/api/admin/banners", "banners",
        {"title": "Summer Edit", "image_url": "/static/uploads/a.webp"},
        {"title": "Winter Edit", "image_url": "/static/uploads/a.webp"},
        "title",
    ),
    "categories": (
        "/api/admin/categories", "categories",
        {"name": "Footwear", "slug": "footwear"},
        {"name": "Shoes", "slug": "footwear"},
        "name",
    ),
    "coupons": (
        "/api/admin/coupons", "coupons",
        {"code": "save10", "discount_type": "percentage", "discount_value": 10},
        {"code": "save10", "discount_type": "percentage", "discount_value": 15},
        "discount_value",
    ),
    "features": (
        "/api/admin/features", "features",
        {"title": "Easy returns", "icon": "refresh"},
        {"title": "7-day returns", "icon": "refresh"},
        "title",
    ),
    "offers": (
        "/api/admin/offers", "offers",
        {"title": "Festive sale", "offer_type": "percentage_off", "discount_percent": 20},
        {"title": "Festive sale", "offer_type": "percentage_off", "discount_percent": 30},
        "discount_percent",
    ),
    "promo-banners": (
        "/api/admin/promo-banners", "promo_banners",
        {"title": "Flat 40% off"},
        {"title": "Flat 50% off"},
        "title",
    ),
    "testimonials": (
        "/api/admin/testimonials", "testimonials",
        {"name": "Asha", "quote": "Lovely fabric and fit."},
        {"name": "Asha", "quote": "Lovely fabric, perfect fit."},
        "quote",
    ),
}

# Deleting these deactivates the row instead of removing it, because other
# records (products, past orders) still point at it.
SOFT_DELETED = {"categories"}

resource = pytest.mark.parametrize("name", sorted(RESOURCES))


@resource
def test_create_returns_the_new_record(app, client, name):
    path, _, create, _, _ = RESOURCES[name]

    resp = client.post(path, json=create, headers=admin_headers())

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["id"]


@resource
def test_list_includes_created_records(app, client, name):
    path, key, create, _, _ = RESOURCES[name]
    headers = admin_headers()
    created = client.post(path, json=create, headers=headers).get_json()

    resp = client.get(path, headers=headers)

    assert resp.status_code == 200
    assert created["id"] in [row["id"] for row in resp.get_json()[key]]


@resource
def test_update_changes_the_record(app, client, name):
    path, _, create, update, field = RESOURCES[name]
    headers = admin_headers()
    created = client.post(path, json=create, headers=headers).get_json()

    resp = client.put(f"{path}/{created['id']}", json=update, headers=headers)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()[field] == update[field]


@resource
def test_delete_removes_the_record(app, client, name):
    path, key, create, _, _ = RESOURCES[name]
    headers = admin_headers()
    created = client.post(path, json=create, headers=headers).get_json()

    resp = client.delete(f"{path}/{created['id']}", headers=headers)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    remaining = {row["id"]: row for row in client.get(path, headers=headers).get_json()[key]}
    if name in SOFT_DELETED:
        assert remaining[created["id"]]["is_active"] is False
    else:
        assert created["id"] not in remaining


@resource
def test_create_rejects_an_incomplete_payload(app, client, name):
    path = RESOURCES[name][0]

    resp = client.post(path, json={"is_active": True}, headers=admin_headers())

    assert resp.status_code == 422
    assert resp.get_json()["errors"]


def test_duplicate_coupon_code_is_a_conflict(app, client):
    path, _, create, _, _ = RESOURCES["coupons"]
    headers = admin_headers()
    client.post(path, json=create, headers=headers)

    resp = client.post(path, json=create, headers=headers)

    assert resp.status_code == 409


def test_site_settings_upsert_list_and_delete(app, client):
    headers = admin_headers()

    saved = client.put("/api/admin/site-settings", headers=headers, json={
        "settings": [{"key": "support_email", "value": "help@example.com"}],
    })
    assert saved.status_code == 200, saved.get_data(as_text=True)

    # Saving the same key again updates in place rather than duplicating.
    client.put("/api/admin/site-settings", headers=headers, json={
        "settings": [{"key": "support_email", "value": "care@example.com"}],
    })
    listed = client.get("/api/admin/site-settings", headers=headers).get_json()["settings"]
    matches = [s for s in listed if s["key"] == "support_email"]
    assert len(matches) == 1
    assert matches[0]["value"] == "care@example.com"

    deleted = client.delete(
        f"/api/admin/site-settings/{matches[0]['id']}", headers=headers
    )
    assert deleted.status_code == 200
    assert client.get("/api/admin/site-settings", headers=headers).get_json()["settings"] == []


def test_public_cms_shows_only_active_content(app, client):
    """What an admin publishes is what the storefront reads — and nothing else."""
    headers = admin_headers()
    client.post("/api/admin/announcements", headers=headers,
                json={"text": "Visible notice"})
    client.post("/api/admin/announcements", headers=headers,
                json={"text": "Hidden notice", "is_active": False})
    client.post("/api/admin/features", headers=headers, json={"title": "Fast delivery"})
    client.post("/api/admin/testimonials", headers=headers,
                json={"name": "Asha", "quote": "Lovely fabric and fit."})
    client.post("/api/admin/promo-banners", headers=headers, json={"title": "Flat 40% off"})
    client.put("/api/admin/site-settings", headers=headers, json={
        "settings": [{"key": "support_email", "value": "help@example.com"}],
    })

    announcements = client.get("/api/cms/announcements")
    assert announcements.status_code == 200
    texts = [a["text"] for a in announcements.get_json()["announcements"]]
    assert texts == ["Visible notice"]

    for path, key in (
        ("/api/cms/features", "features"),
        ("/api/cms/testimonials", "testimonials"),
        ("/api/cms/promo-banners", "promo_banners"),
    ):
        resp = client.get(path)
        assert resp.status_code == 200, path
        assert len(resp.get_json()[key]) == 1, path

    settings = client.get("/api/cms/settings")
    assert settings.status_code == 200
    assert "help@example.com" in settings.get_data(as_text=True)
