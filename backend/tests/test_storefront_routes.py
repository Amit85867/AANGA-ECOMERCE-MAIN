"""Customer and public routes: catalogue, cart, wishlist, account, auth."""
import pytest
from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models.catalogue import ProductImage
from app.models.engagement import ProductReview
from app.models.enums import OrderStatus
from app.models.marketing import Offer
from app.models.enums import OfferType
from app.models.user import OTP, User
from app.services.order_service import create_order_from_cart
from tests.factories import make_address, make_cart, make_coupon, make_product, make_user
from tests.helpers import customer_headers


# ── Catalogue ─────────────────────────────────────────────────

def test_product_list_filters_sorts_and_hides_inactive(app, client):
    cheap, _ = make_product(price=400, name="Cotton Tee", slug="cotton-tee")
    dear, _ = make_product(price=2400, name="Silk Saree", slug="silk-saree")
    hidden, _ = make_product(price=900, name="Retired Kurta", slug="retired-kurta")
    hidden.is_active = False
    dear.is_featured = True
    db.session.add(ProductImage(
        product_id=cheap.id, image_url="/static/uploads/tee.webp", is_primary=True,
    ))
    db.session.commit()

    everything = client.get("/api/products?sort=price_asc")
    assert everything.status_code == 200
    body = everything.get_json()
    assert [p["slug"] for p in body["products"]] == ["cotton-tee", "silk-saree"]
    assert body["total"] == 2
    assert body["products"][0]["primary_image"] == "/static/uploads/tee.webp"

    assert [p["slug"] for p in client.get(
        "/api/products?max_price=1000").get_json()["products"]] == ["cotton-tee"]
    assert [p["slug"] for p in client.get(
        "/api/products?q=silk").get_json()["products"]] == ["silk-saree"]
    assert [p["slug"] for p in client.get(
        "/api/products?featured=true").get_json()["products"]] == ["silk-saree"]
    assert client.get("/api/products?category=test-cat").get_json()["total"] == 2
    assert client.get("/api/products?category=nope").get_json()["total"] == 0


def test_product_list_caps_page_size(app, client):
    for i in range(3):
        make_product(slug=f"p-{i}")

    body = client.get("/api/products?per_page=2").get_json()

    assert len(body["products"]) == 2
    assert body["pages"] == 2 and body["total"] == 3


def test_product_detail_by_slug(app, client):
    product, variant = make_product(price=500, slug="linen-kurta", name="Linen Kurta")

    resp = client.get("/api/products/linen-kurta")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["name"] == "Linen Kurta"
    assert [v["id"] for v in body["variants"]] == [variant.id]


def test_inactive_product_detail_is_not_found(app, client):
    product, _ = make_product(slug="retired")
    product.is_active = False
    db.session.commit()

    assert client.get("/api/products/retired").status_code == 404


def test_categories_are_returned_as_a_tree(app, client):
    make_product()   # creates the default "test-cat" category

    resp = client.get("/api/categories")

    assert resp.status_code == 200
    assert [c["slug"] for c in resp.get_json()["categories"]] == ["test-cat"]


def test_offers_lists_active_offers_only(app, client):
    db.session.add_all([
        Offer(title="Festive sale", offer_type=OfferType.percentage_off, is_active=True),
        Offer(title="Old sale", offer_type=OfferType.percentage_off, is_active=False),
    ])
    db.session.commit()

    resp = client.get("/api/offers")

    assert resp.status_code == 200
    assert [o["title"] for o in resp.get_json()["offers"]] == ["Festive sale"]


def test_product_reviews_with_average(app, client):
    product, _ = make_product()
    for rating in (5, 4):
        db.session.add(ProductReview(
            product_id=product.id, user_id=make_user().id, rating=rating, body="Nice",
        ))
    db.session.commit()

    resp = client.get(f"/api/reviews/product/{product.id}")

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["total"] == 2
    assert float(body["avg_rating"]) == 4.5


# ── Cart ──────────────────────────────────────────────────────

def test_cart_add_update_remove(app, client):
    user = make_user()
    _, variant = make_product(price=500, stock=5)
    headers = customer_headers(user)

    added = client.post(
        "/api/cart/items", headers=headers,
        json={"variant_id": variant.id, "quantity": 2},
    )
    assert added.status_code == 200, added.get_data(as_text=True)
    cart = added.get_json()
    assert cart["item_count"] == 2 and cart["subtotal"] == 1000
    item_id = cart["items"][0]["id"]

    changed = client.patch(
        f"/api/cart/items/{item_id}", headers=headers, json={"quantity": 3}
    )
    assert changed.status_code == 200
    assert changed.get_json()["item_count"] == 3

    removed = client.delete(f"/api/cart/items/{item_id}", headers=headers)
    assert removed.status_code == 200
    assert removed.get_json()["items"] == []
    assert removed.get_json()["total"] == 0


@pytest.mark.parametrize("quantity", [0, -3])
def test_cart_rejects_a_non_positive_quantity(app, client, quantity):
    _, variant = make_product(stock=5)

    resp = client.post(
        "/api/cart/items", headers=customer_headers(make_user()),
        json={"variant_id": variant.id, "quantity": quantity},
    )

    assert resp.status_code == 422


def test_cart_cannot_exceed_stock_by_adding_twice(app, client):
    _, variant = make_product(stock=5)
    headers = customer_headers(make_user())
    payload = {"variant_id": variant.id, "quantity": 3}
    assert client.post("/api/cart/items", headers=headers, json=payload).status_code == 200

    resp = client.post("/api/cart/items", headers=headers, json=payload)

    assert resp.status_code == 409
    assert client.get("/api/cart", headers=headers).get_json()["item_count"] == 3


def test_cart_refuses_a_deactivated_product(app, client):
    product, variant = make_product(stock=5)
    product.is_active = False
    db.session.commit()

    resp = client.post(
        "/api/cart/items", headers=customer_headers(make_user()),
        json={"variant_id": variant.id, "quantity": 1},
    )

    assert resp.status_code == 404


def test_cart_coupon_apply_and_remove(app, client):
    user = make_user()
    _, variant = make_product(price=1000, stock=5)
    make_cart(user, [(variant, 1)])
    make_coupon(code="SAVE10", discount_value=10)
    headers = customer_headers(user)

    applied = client.post("/api/cart/coupon", headers=headers, json={"code": "SAVE10"})
    assert applied.status_code == 200, applied.get_data(as_text=True)
    assert applied.get_json()["discount"] == 100
    assert applied.get_json()["coupon_code"] == "SAVE10"

    cleared = client.delete("/api/cart/coupon", headers=headers)
    assert cleared.status_code == 200
    assert cleared.get_json()["discount"] == 0

    assert client.post(
        "/api/cart/coupon", headers=headers, json={"code": "NOPE"}
    ).status_code == 404


# ── Wishlist ──────────────────────────────────────────────────

def test_wishlist_add_list_remove(app, client):
    product, _ = make_product(name="Linen Kurta")
    headers = customer_headers(make_user())

    assert client.post(
        "/api/wishlist", headers=headers, json={"product_id": product.id}
    ).status_code == 201
    # Adding the same product again is not an error and does not duplicate.
    assert client.post(
        "/api/wishlist", headers=headers, json={"product_id": product.id}
    ).status_code == 200

    listed = client.get("/api/wishlist", headers=headers)
    assert listed.status_code == 200
    assert listed.get_json()["count"] == 1

    assert client.delete(f"/api/wishlist/{product.id}", headers=headers).status_code == 200
    assert client.get("/api/wishlist", headers=headers).get_json()["count"] == 0


# ── Orders ────────────────────────────────────────────────────

def test_customer_sees_only_their_own_orders(app, client):
    user, stranger = make_user(), make_user()
    _, variant = make_product(price=500, stock=10)
    make_cart(user, [(variant, 2)])
    order, err = create_order_from_cart(user.id, make_address(user).id, "cod")
    assert err is None

    listed = client.get("/api/orders", headers=customer_headers(user))
    assert listed.status_code == 200
    assert [o["id"] for o in listed.get_json()["orders"]] == [order.id]

    detail = client.get(f"/api/orders/{order.id}", headers=customer_headers(user))
    assert detail.status_code == 200
    assert detail.get_json()["items"][0]["quantity"] == 2

    assert client.get("/api/orders", headers=customer_headers(stranger)).get_json()["orders"] == []
    assert client.get(
        f"/api/orders/{order.id}", headers=customer_headers(stranger)
    ).status_code == 404


def test_return_detail_is_private_to_its_owner(app, client):
    user, stranger = make_user(), make_user()
    _, variant = make_product(price=500, stock=10)
    make_cart(user, [(variant, 1)])
    order, _ = create_order_from_cart(user.id, make_address(user).id, "cod")
    order.status = OrderStatus.delivered
    db.session.commit()
    return_id = client.post(
        "/api/returns", headers=customer_headers(user),
        json={"order_item_id": order.items[0].id, "reason": "damaged"},
    ).get_json()["id"]

    mine = client.get(f"/api/returns/{return_id}", headers=customer_headers(user))
    assert mine.status_code == 200
    assert mine.get_json()["reason"] == "damaged"

    assert client.get(
        f"/api/returns/{return_id}", headers=customer_headers(stranger)
    ).status_code == 404


# ── Account ───────────────────────────────────────────────────

def test_me_and_profile_return_the_signed_in_user(app, client):
    user = make_user(email="asha@example.com", full_name="Asha Rao")
    headers = customer_headers(user)

    for path in ("/api/auth/me", "/api/profile"):
        resp = client.get(path, headers=headers)
        assert resp.status_code == 200, path
        body = resp.get_json()
        assert body["email"] == "asha@example.com"
        assert "password_hash" not in body


def test_change_password_requires_the_current_one(app, client):
    user = make_user(password_hash=generate_password_hash("OldPass123!"))
    headers = customer_headers(user)

    wrong = client.put("/api/profile/password", headers=headers, json={
        "current_password": "not-it", "new_password": "NewPass123!",
    })
    assert wrong.status_code == 401

    changed = client.put("/api/profile/password", headers=headers, json={
        "current_password": "OldPass123!", "new_password": "NewPass123!",
    })
    assert changed.status_code == 200
    assert client.post("/api/auth/login", json={
        "email": user.email, "password": "NewPass123!",
    }).status_code == 200


def test_password_reset_round_trip(app, client, monkeypatch):
    user = make_user(password_hash=generate_password_hash("OldPass123!"))
    links = []
    monkeypatch.setattr(
        "app.services.email.send_password_reset",
        lambda email, link: links.append(link),
    )

    asked = client.post("/api/auth/forgot-password", json={"email": user.email})
    assert asked.status_code == 200
    token = links[0].split("token=")[1]

    reset = client.post("/api/auth/reset-password", json={
        "token": token, "new_password": "FreshPass123!",
    })
    assert reset.status_code == 200, reset.get_data(as_text=True)
    assert client.post("/api/auth/login", json={
        "email": user.email, "password": "FreshPass123!",
    }).status_code == 200

    # A reset link works once.
    assert client.post("/api/auth/reset-password", json={
        "token": token, "new_password": "Another123!",
    }).status_code == 400


def test_forgot_password_does_not_reveal_whether_an_account_exists(app, client):
    known = make_user(password_hash=generate_password_hash("OldPass123!"))

    a = client.post("/api/auth/forgot-password", json={"email": known.email})
    b = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})

    assert a.status_code == b.status_code == 200
    assert a.get_json() == b.get_json()


def test_otp_sign_in_creates_the_account_and_burns_the_code(app, client):
    phone = "+919000000001"
    assert client.post("/api/auth/otp/send", json={"phone": phone}).status_code == 200
    code = OTP.query.filter_by(phone=phone).one().code
    wrong = "000000" if code != "000000" else "111111"

    assert client.post(
        "/api/auth/otp/verify", json={"phone": phone, "code": wrong}
    ).status_code == 401

    ok = client.post("/api/auth/otp/verify", json={"phone": phone, "code": code})
    assert ok.status_code in (200, 201), ok.get_data(as_text=True)
    assert ok.get_json()["access_token"]
    assert User.query.filter_by(phone=phone).count() == 1

    assert client.post(
        "/api/auth/otp/verify", json={"phone": phone, "code": code}
    ).status_code == 400


def test_otp_is_never_returned_outside_debug(app, client):
    resp = client.post("/api/auth/otp/send", json={"phone": "+919000000002"})

    assert "dev_otp" not in resp.get_json()


def test_google_sign_in_checks_the_token_audience(app, client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "our-client-id")

    class _Resp:
        def __init__(self, payload):
            self.status_code, self._payload = 200, payload

        def json(self):
            return self._payload

    def _google(aud):
        def _get(url, **kw):
            if "tokeninfo" in url:
                return _Resp({"aud": aud})
            return _Resp({"email": "asha@example.com", "name": "Asha Rao", "sub": "g-1"})
        return _get

    monkeypatch.setattr("requests.get", _google("someone-elses-client"))
    assert client.post(
        "/api/auth/google", json={"access_token": "tok"}
    ).status_code == 401

    monkeypatch.setattr("requests.get", _google("our-client-id"))
    ok = client.post("/api/auth/google", json={"access_token": "tok"})
    assert ok.status_code in (200, 201), ok.get_data(as_text=True)
    assert User.query.filter_by(email="asha@example.com").count() == 1


def test_google_sign_in_reports_when_unconfigured(app, client, monkeypatch):
    monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)

    resp = client.post("/api/auth/google", json={"access_token": "tok"})

    assert resp.status_code == 503


# ── Payments ──────────────────────────────────────────────────

def test_create_payment_order_charges_the_server_computed_total(app, client, monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_x")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "secret")
    user = make_user()
    _, variant = make_product(price=1000, stock=5)
    make_cart(user, [(variant, 1)])
    sent = {}

    class _Resp:
        status_code = 200

        @staticmethod
        def json():
            return {"id": "order_test_1"}

    def _post(url, **kw):
        sent.update(kw["json"])
        return _Resp()

    monkeypatch.setattr("app.routes.payments.requests.post", _post)

    resp = client.post("/api/payments/create-order", headers=customer_headers(user))

    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    cart_total = client.get("/api/cart", headers=customer_headers(user)).get_json()["total"]
    assert body["razorpay_order_id"] == "order_test_1"
    assert body["amount"] == sent["amount"] == int(round(cart_total * 100))
    # The secret never leaves the server.
    assert "secret" not in resp.get_data(as_text=True)


def test_create_payment_order_reports_when_unconfigured(app, client, monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID", raising=False)
    monkeypatch.delenv("RAZORPAY_KEY_SECRET", raising=False)

    resp = client.post(
        "/api/payments/create-order", headers=customer_headers(make_user())
    )

    assert resp.status_code == 503
    assert "not configured" in resp.get_json()["error"]


# ── Optional features are advertised honestly ─────────────────

def test_features_available_reflects_configuration_without_values(app, client, monkeypatch):
    for key in ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "SHIPROCKET_EMAIL",
                "SHIPROCKET_PASSWORD", "SHIPROCKET_PICKUP_PINCODE", "GOOGLE_CLIENT_ID"):
        monkeypatch.delenv(key, raising=False)

    off = client.get("/api/cms/features-available")
    assert off.status_code == 200
    assert off.get_json() == {
        "online_payments": False, "delivery_check": False,
        "google_login": False, "phone_login": False,
    }

    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_PUBLIC")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "RZP-SECRET")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "google-client-id")
    on = client.get("/api/cms/features-available")
    assert on.get_json()["online_payments"] is True
    assert on.get_json()["google_login"] is True
    assert "RZP-SECRET" not in on.get_data(as_text=True)
    assert "rzp_test_PUBLIC" not in on.get_data(as_text=True)


def test_phone_sign_in_is_refused_in_production_without_an_sms_provider(app, client, monkeypatch):
    monkeypatch.setitem(app.config, "TESTING", False)
    monkeypatch.setitem(app.config, "DEBUG", False)
    monkeypatch.setitem(app.config, "SMS_PROVIDER", "")
    try:
        sent = client.post("/api/auth/otp/send", json={"phone": "+919000000009"})
        verified = client.post("/api/auth/otp/verify",
                               json={"phone": "+919000000009", "code": "123456"})
    finally:
        app.config["TESTING"] = True

    assert sent.status_code == verified.status_code == 503
    assert OTP.query.count() == 0
