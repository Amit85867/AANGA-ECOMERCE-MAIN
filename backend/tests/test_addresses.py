"""Customer address book."""
from app.extensions import db
from app.models.user import Address
from app.services.order_service import create_order_from_cart
from tests.factories import make_address, make_cart, make_product, make_user
from tests.helpers import admin_headers, customer_headers, make_admin

ADDRESS = {
    "full_name": "Asha Rao", "phone": "9000000000", "line1": "12 Park Street",
    "city": "Kolkata", "state": "West Bengal", "pin_code": "700016",
}


def test_first_address_becomes_the_default(app, client):
    headers = customer_headers(make_user())

    first = client.post("/api/addresses", headers=headers, json=ADDRESS)
    second = client.post("/api/addresses", headers=headers, json={**ADDRESS, "label": "Work"})

    assert first.status_code == 201, first.get_data(as_text=True)
    assert first.get_json()["is_default"] is True
    assert second.get_json()["is_default"] is False

    listed = client.get("/api/addresses", headers=headers)
    assert listed.status_code == 200
    # The default is listed first.
    assert [a["is_default"] for a in listed.get_json()["addresses"]] == [True, False]


def test_update_and_switch_default(app, client):
    headers = customer_headers(make_user())
    first = client.post("/api/addresses", headers=headers, json=ADDRESS).get_json()
    second = client.post("/api/addresses", headers=headers, json=ADDRESS).get_json()

    edited = client.put(
        f"/api/addresses/{second['id']}", headers=headers,
        json={**ADDRESS, "city": "Howrah"},
    )
    assert edited.status_code == 200
    assert edited.get_json()["city"] == "Howrah"

    switched = client.patch(f"/api/addresses/{second['id']}/default", headers=headers)
    assert switched.status_code == 200
    defaults = {a["id"]: a["is_default"] for a in client.get(
        "/api/addresses", headers=headers).get_json()["addresses"]}
    assert defaults == {first["id"]: False, second["id"]: True}


def test_delete_address(app, client):
    headers = customer_headers(make_user())
    created = client.post("/api/addresses", headers=headers, json=ADDRESS).get_json()

    resp = client.delete(f"/api/addresses/{created['id']}", headers=headers)

    assert resp.status_code == 200
    assert client.get("/api/addresses", headers=headers).get_json()["addresses"] == []


def test_address_used_by_an_order_can_still_be_removed_from_the_book(app, client):
    """The order keeps its delivery address; the customer just stops seeing it."""
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=500, stock=5)
    make_cart(user, [(variant, 1)])
    order, err = create_order_from_cart(user.id, address.id, "cod")
    assert err is None
    headers = customer_headers(user)

    resp = client.delete(f"/api/addresses/{address.id}", headers=headers)

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert client.get("/api/addresses", headers=headers).get_json()["addresses"] == []
    detail = client.get(f"/api/orders/{order.id}", headers=headers)
    assert detail.status_code == 200
    assert detail.get_json()["address"]["pin_code"] == "700001"


def test_address_rejects_a_malformed_pin_or_phone(app, client):
    headers = customer_headers(make_user())

    for bad in ({"pin_code": "abcdef"}, {"pin_code": "012345"}, {"phone": "phone-number"}):
        resp = client.post("/api/addresses", headers=headers, json={**ADDRESS, **bad})
        assert resp.status_code == 422, (bad, resp.get_data(as_text=True))


def test_addresses_are_private(app, client):
    owner, stranger = make_user(), make_user()
    address = make_address(owner)
    headers = customer_headers(stranger)

    assert client.put(
        f"/api/addresses/{address.id}", headers=headers, json=ADDRESS
    ).status_code == 404
    assert client.delete(f"/api/addresses/{address.id}", headers=headers).status_code == 404
    assert db.session.get(Address, address.id) is not None


def test_master_admin_can_create_staff(app, client):
    headers = admin_headers(make_admin(role="master"))

    resp = client.post("/api/admin/auth/admins", headers=headers, json={
        "email": "staff@example.com", "password": "StaffPass123!",
        "full_name": "Staff Member",
    })

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["role"] == "staff"
    assert "password" not in resp.get_data(as_text=True)
    assert client.post("/api/admin/auth/login", json={
        "email": "staff@example.com", "password": "StaffPass123!",
    }).status_code == 200


def test_editing_an_address_does_not_rewrite_a_past_order(app, client):
    user = make_user()
    address = make_address(user, city="Kolkata")
    _, variant = make_product(price=500, stock=5)
    make_cart(user, [(variant, 1)])
    order, _ = create_order_from_cart(user.id, address.id, "cod")
    headers = customer_headers(user)

    edited = client.put(
        f"/api/addresses/{address.id}", headers=headers,
        json={**ADDRESS, "city": "Mumbai", "pin_code": "400001"},
    )

    assert edited.status_code == 200, edited.get_data(as_text=True)
    assert edited.get_json()["city"] == "Mumbai"
    assert edited.get_json()["is_default"] is True
    book = client.get("/api/addresses", headers=headers).get_json()["addresses"]
    assert [a["city"] for a in book] == ["Mumbai"]
    shipped_to = client.get(f"/api/orders/{order.id}", headers=headers).get_json()["address"]
    assert shipped_to["city"] == "Kolkata"


def test_an_archived_address_cannot_be_used_for_a_new_order(app, client):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=500, stock=5)
    make_cart(user, [(variant, 1)])
    create_order_from_cart(user.id, address.id, "cod")
    headers = customer_headers(user)
    client.delete(f"/api/addresses/{address.id}", headers=headers)
    make_cart_again = client.post(
        "/api/cart/items", headers=headers, json={"variant_id": variant.id, "quantity": 1}
    )
    assert make_cart_again.status_code == 200

    resp = client.post("/api/orders", headers=headers, json={
        "address_id": address.id, "payment_method": "cod",
    })

    assert resp.status_code == 404


def test_deleting_the_default_promotes_another_address(app, client):
    headers = customer_headers(make_user())
    first = client.post("/api/addresses", headers=headers, json=ADDRESS).get_json()
    client.post("/api/addresses", headers=headers, json=ADDRESS)

    client.delete(f"/api/addresses/{first['id']}", headers=headers)

    book = client.get("/api/addresses", headers=headers).get_json()["addresses"]
    assert [a["is_default"] for a in book] == [True]


def test_phone_typed_with_spaces_is_accepted_and_stored_clean(app, client):
    resp = client.post(
        "/api/addresses", headers=customer_headers(make_user()),
        json={**ADDRESS, "phone": "+91 98765-43210"},
    )

    assert resp.status_code == 201, resp.get_data(as_text=True)
    assert resp.get_json()["phone"] == "+919876543210"
