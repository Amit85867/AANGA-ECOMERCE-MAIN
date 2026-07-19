"""Admin category CRUD.

Regression cover for a bug where create/update referenced an undefined
`_serialize_category`, raising NameError -> 500 *after* the row had already
been committed (so the category was silently created while the admin UI
reported a server error).
"""
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.admin import Admin
from app.models.catalogue import Category

PASSWORD = "AdminPass123!"


def _auth(client):
    db.session.add(Admin(
        email="cat-admin@example.com",
        password_hash=generate_password_hash(PASSWORD),
        full_name="Cat Admin",
        role="master",
    ))
    db.session.commit()
    resp = client.post(
        "/api/admin/auth/login",
        json={"email": "cat-admin@example.com", "password": PASSWORD},
    )
    return {"Authorization": f"Bearer {resp.get_json()['access_token']}"}


def test_create_category_returns_201_with_body(app, client):
    headers = _auth(client)

    resp = client.post(
        "/api/admin/categories",
        json={"name": "Footwear", "slug": "footwear"},
        headers=headers,
    )

    assert resp.status_code == 201, resp.get_data(as_text=True)
    body = resp.get_json()
    assert body["id"]
    assert body["slug"] == "footwear"
    assert body["name"] == "Footwear"
    assert Category.query.filter_by(slug="footwear").first() is not None


def test_create_child_category(app, client):
    headers = _auth(client)
    parent = client.post(
        "/api/admin/categories",
        json={"name": "Women", "slug": "women"},
        headers=headers,
    ).get_json()

    resp = client.post(
        "/api/admin/categories",
        json={"name": "Skirts", "slug": "womens-skirts", "parent_id": parent["id"]},
        headers=headers,
    )

    assert resp.status_code == 201
    assert resp.get_json()["parent_id"] == parent["id"]


def test_update_category_returns_200_with_body(app, client):
    headers = _auth(client)
    created = client.post(
        "/api/admin/categories",
        json={"name": "Bags", "slug": "bags"},
        headers=headers,
    ).get_json()

    resp = client.put(
        f"/api/admin/categories/{created['id']}",
        json={"name": "Bags & Luggage", "slug": "bags"},
        headers=headers,
    )

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["name"] == "Bags & Luggage"


def test_duplicate_slug_rejected(app, client):
    headers = _auth(client)
    client.post("/api/admin/categories",
                json={"name": "Jewellery", "slug": "jewellery"}, headers=headers)

    resp = client.post("/api/admin/categories",
                       json={"name": "Jewels", "slug": "jewellery"}, headers=headers)

    assert resp.status_code == 409


def test_categories_require_admin_auth(app, client):
    resp = client.post("/api/admin/categories", json={"name": "X", "slug": "x"})
    assert resp.status_code in (401, 403)
