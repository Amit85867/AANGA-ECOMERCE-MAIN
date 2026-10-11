"""Razorpay and Shiprocket, tested against provider-shaped responses.

No keys and no network: every outgoing HTTP call is answered from
tests/fixtures/, which hold responses in the shape the two providers document.
The other payment and shipping tests replace our own functions; these replace
only the wire, so they prove what we send (URL, auth, body) and that we read
what comes back correctly. When real test keys are added,
scripts/verify_integrations.sh repeats the same steps against the sandboxes.
"""
import hashlib
import hmac
import json
import pathlib
import time

import pytest
import requests

from app.extensions import db
from app.models.enums import OrderStatus, PaymentStatus
from app.models.order import Order
from app.services import shiprocket
from app.services.order_service import compute_totals, create_order_from_cart
from tests.factories import make_address, make_cart, make_product, make_user
from tests.helpers import admin_headers, customer_headers

FIXTURES = pathlib.Path(__file__).parent / "fixtures"
KEY_ID, KEY_SECRET, WEBHOOK_SECRET = "rzp_test_contract0001", "contract_test_secret", "whsec_contract_test"
PAY, ORD = "pay_Q1w2E3r4T5y6U8", "order_Q1w2E3r4T5y6U7"


def fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class Answer:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        if self._body is None:
            raise ValueError("no JSON")
        return self._body


class Wire:
    """Stands in for the network. ``on(method, url_part, status, body)`` queues
    an answer; the last one queued for a route repeats. Every call is kept in
    ``calls`` so a test can check what was sent."""

    def __init__(self):
        self.routes, self.calls = {}, []

    def on(self, method, part, status=200, body=None, error=None):
        self.routes.setdefault((method, part), []).append((status, body, error))
        return self

    def __call__(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        matches = [k for k in self.routes if k[0] == method and k[1] in url]
        assert matches, f"unexpected call to the network: {method} {url}"
        queue = self.routes[max(matches, key=lambda k: len(k[1]))]
        status, body, error = queue.pop(0) if len(queue) > 1 else queue[0]
        if error:
            raise error
        return Answer(status, fixture(body) if isinstance(body, str) else body)

    def sent(self, method, part):
        return [c for c in self.calls if c["method"] == method and part in c["url"]]


@pytest.fixture
def wire(monkeypatch, app):
    w = Wire()
    monkeypatch.setattr(requests, "request", w)
    monkeypatch.setattr(requests, "get", lambda url, **kw: w("GET", url, **kw))
    monkeypatch.setattr(requests, "post", lambda url, **kw: w("POST", url, **kw))
    app.config["RATELIMIT_ENABLED"] = False
    yield w
    app.config["RATELIMIT_ENABLED"] = True


@pytest.fixture
def razorpay_keys(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", KEY_ID)
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", KEY_SECRET)
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)


@pytest.fixture
def no_keys(monkeypatch):
    for name in ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET",
                 "SHIPROCKET_EMAIL", "SHIPROCKET_PASSWORD", "SHIPROCKET_PICKUP_PINCODE"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def shiprocket_keys(monkeypatch):
    monkeypatch.setenv("SHIPROCKET_EMAIL", "api-user@example.com")
    monkeypatch.setenv("SHIPROCKET_PASSWORD", "contract-test-password")
    monkeypatch.setenv("SHIPROCKET_PICKUP_PINCODE", "800001")
    shiprocket._token_cache.update(token=None, fetched_at=0)
    yield
    shiprocket._token_cache.update(token=None, fetched_at=0)


def _shopper(price=500, quantity=1, stock=10):
    user = make_user()
    address = make_address(user)
    _, variant = make_product(price=price, stock=stock)
    cart = make_cart(user, [(variant, quantity)])
    return user, address, variant, cart


def _checkout_signature(order_id=ORD, payment_id=PAY, secret=KEY_SECRET):
    return hmac.new(secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256).hexdigest()


def _captured(amount_paise, **over):
    return {**fixture("razorpay/payment.captured.json"), "amount": amount_paise, **over}


# ════════════════════════════════════════════════════════════════
# Razorpay
# ════════════════════════════════════════════════════════════════

def test_create_order_sends_paise_and_returns_only_the_public_key(client, wire, razorpay_keys):
    user, _address, _variant, cart = _shopper(price=500)
    wire.on("POST", "/v1/orders", 200, "razorpay/order.created.json")

    resp = client.post("/api/payments/create-order", headers=customer_headers(user))

    assert resp.status_code == 200
    body = resp.get_json()
    expected = int(round(compute_totals(cart)["total"] * 100))
    assert body == {"razorpay_order_id": ORD, "amount": expected, "currency": "INR", "key_id": KEY_ID}
    assert KEY_SECRET not in resp.get_data(as_text=True)

    call = wire.sent("POST", "/v1/orders")[0]
    assert call["url"] == "https://api.razorpay.com/v1/orders"
    assert call["auth"] == (KEY_ID, KEY_SECRET)                 # HTTP basic auth, as Razorpay requires
    assert call["json"]["amount"] == expected and isinstance(call["json"]["amount"], int)
    assert call["json"]["currency"] == "INR"
    assert call["json"]["payment_capture"] == 1
    assert len(call["json"]["receipt"]) <= 40                   # Razorpay's limit on receipt


@pytest.mark.parametrize("status, body", [(401, "razorpay/error.unauthorized.json"), (400, "razorpay/error.bad_request.json"), (500, None)])
def test_create_order_reports_a_gateway_refusal_without_leaking_it(client, wire, razorpay_keys, status, body):
    user, *_ = _shopper()
    wire.on("POST", "/v1/orders", status, body)
    resp = client.post("/api/payments/create-order", headers=customer_headers(user))
    assert resp.status_code == 502
    assert resp.get_json() == {"error": "Could not initiate payment"}


def test_create_order_survives_the_gateway_being_unreachable(client, wire, razorpay_keys):
    user, *_ = _shopper()
    wire.on("POST", "/v1/orders", error=requests.ConnectTimeout("timed out"))
    resp = client.post("/api/payments/create-order", headers=customer_headers(user))
    assert resp.status_code == 502


def test_checkout_signature_is_hmac_sha256_of_order_and_payment_with_the_key_secret(client, wire, razorpay_keys):
    """The whole paid checkout: signature, the gateway's own record, the order."""
    user, address, variant, cart = _shopper(price=500, quantity=2)
    total_paise = int(round(compute_totals(cart)["total"] * 100))
    wire.on("GET", f"/v1/payments/{PAY}", 200, _captured(total_paise))

    resp = client.post("/api/payments/verify", headers=customer_headers(user), json={
        "razorpay_order_id": ORD, "razorpay_payment_id": PAY, "razorpay_signature": _checkout_signature(),
        "address_id": address.id, "payment_method": "card",
    })

    assert resp.status_code in (200, 201), resp.get_json()
    order = db.session.get(Order, resp.get_json()["order_id"])
    assert order.payment_status == PaymentStatus.paid
    assert order.payment_ref == PAY
    assert order.payment_method.value == "upi"                  # what Razorpay says, not what the browser claimed
    assert int(round(float(order.total_amount) * 100)) == total_paise
    db.session.refresh(variant)
    assert variant.stock_qty == 8
    call = wire.sent("GET", f"/v1/payments/{PAY}")[0]
    assert call["auth"] == (KEY_ID, KEY_SECRET)


@pytest.mark.parametrize("signature", [
    _checkout_signature(secret="some_other_secret"),            # signed with the wrong secret
    _checkout_signature(order_id="order_SOMEONEELSE"),          # a real signature for another order
    hashlib.sha256(f"{ORD}|{PAY}".encode()).hexdigest(),        # a bare hash, no secret
    "",
])
def test_a_forged_checkout_signature_never_reaches_the_gateway(client, wire, razorpay_keys, signature):
    user, address, *_ = _shopper()
    resp = client.post("/api/payments/verify", headers=customer_headers(user), json={
        "razorpay_order_id": ORD, "razorpay_payment_id": PAY, "razorpay_signature": signature, "address_id": address.id,
    })
    assert resp.status_code in (400, 422)
    assert wire.calls == []
    assert Order.query.count() == 0


def test_an_authorised_but_uncaptured_payment_does_not_make_an_order(client, wire, razorpay_keys):
    user, address, _variant, cart = _shopper()
    total_paise = int(round(compute_totals(cart)["total"] * 100))
    wire.on("GET", f"/v1/payments/{PAY}", 200, {**fixture("razorpay/payment.authorized.json"), "amount": total_paise})
    resp = client.post("/api/payments/verify", headers=customer_headers(user), json={
        "razorpay_order_id": ORD, "razorpay_payment_id": PAY, "razorpay_signature": _checkout_signature(), "address_id": address.id,
    })
    assert resp.status_code == 400
    assert Order.query.count() == 0


def test_paid_but_out_of_stock_is_refunded_through_the_refund_api(client, wire, razorpay_keys):
    user, address, variant, cart = _shopper(quantity=1, stock=1)
    total_paise = int(round(compute_totals(cart)["total"] * 100))
    variant.stock_qty = 0                                       # someone else bought it while the customer paid
    db.session.commit()
    wire.on("GET", f"/v1/payments/{PAY}", 200, _captured(total_paise))
    wire.on("POST", f"/v1/payments/{PAY}/refund", 200, "razorpay/refund.created.json")

    resp = client.post("/api/payments/verify", headers=customer_headers(user), json={
        "razorpay_order_id": ORD, "razorpay_payment_id": PAY, "razorpay_signature": _checkout_signature(), "address_id": address.id,
    })

    assert resp.status_code >= 400
    assert Order.query.count() == 0
    refund = wire.sent("POST", "/refund")[0]
    assert refund["url"] == f"https://api.razorpay.com/v1/payments/{PAY}/refund"
    assert refund["json"] == {"amount": total_paise}
    assert refund["headers"]["Idempotency-Key"] == f"refund_{PAY}"


def _paid_order(payment_ref=PAY):
    user, address, variant, _cart = _shopper()
    order, err = create_order_from_cart(user.id, address.id, "upi", payment_ref=payment_ref, paid=True)
    assert err is None, err
    return user, order, variant


def test_cancelling_a_paid_order_refunds_the_full_amount(client, wire, razorpay_keys):
    user, order, variant = _paid_order()
    wire.on("POST", f"/v1/payments/{PAY}/refund", 200, "razorpay/refund.created.json")

    resp = client.post(f"/api/orders/{order.id}/cancel", headers=customer_headers(user))

    assert resp.status_code == 200, resp.get_json()
    refund = wire.sent("POST", "/refund")
    assert len(refund) == 1
    assert refund[0]["json"] == {"amount": int(round(float(order.total_amount) * 100))}
    assert refund[0]["auth"] == (KEY_ID, KEY_SECRET)
    db.session.expire_all()
    order = db.session.get(Order, order.id)
    assert order.status == OrderStatus.cancelled
    assert order.payment_status == PaymentStatus.refunded
    db.session.refresh(variant)
    assert variant.stock_qty == 10


def test_a_refused_refund_still_cancels_and_leaves_the_order_marked_paid(client, wire, razorpay_keys):
    user, order, _variant = _paid_order()
    wire.on("POST", f"/v1/payments/{PAY}/refund", 400, "razorpay/error.bad_request.json")
    resp = client.post(f"/api/orders/{order.id}/cancel", headers=customer_headers(user))
    assert resp.status_code == 200
    db.session.expire_all()
    order = db.session.get(Order, order.id)
    assert order.status == OrderStatus.cancelled
    assert order.payment_status == PaymentStatus.paid           # so it shows up as "refund owed"


# ── Webhook: every event Razorpay sends for a payment or a refund ──

def _webhook(client, name, secret=WEBHOOK_SECRET, event_id=None, edit=None):
    event = fixture(name)
    if edit:
        edit(event)
    raw = json.dumps(event, separators=(",", ":")).encode()
    headers = {"X-Razorpay-Signature": hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()}
    if event_id:
        headers["X-Razorpay-Event-Id"] = event_id
    return client.post("/api/payments/webhook", data=raw, content_type="application/json", headers=headers)


@pytest.mark.parametrize("name", sorted(p.name for p in (FIXTURES / "razorpay").glob("webhook.*.json")))
def test_every_webhook_event_is_accepted_when_signed_and_refused_when_not(client, wire, razorpay_keys, name):
    assert _webhook(client, f"razorpay/{name}", secret="wrong_secret").status_code in (400, 401)
    wire.on("POST", "/refund", 200, "razorpay/refund.created.json")
    resp = _webhook(client, f"razorpay/{name}")
    assert resp.status_code == 200, name


def test_webhook_payment_captured_for_an_existing_order_changes_nothing(client, wire, razorpay_keys):
    _user, order, _variant = _paid_order()
    assert _webhook(client, "razorpay/webhook.payment.captured.json").status_code == 200
    assert wire.calls == []
    db.session.expire_all()
    assert db.session.get(Order, order.id).payment_status == PaymentStatus.paid


def test_webhook_payment_captured_with_no_order_is_refunded_once_it_is_stale(client, wire, razorpay_keys):
    wire.on("POST", f"/v1/payments/{PAY}/refund", 200, "razorpay/refund.created.json")

    def fresh(event):
        event["payload"]["payment"]["entity"]["created_at"] = int(time.time())

    assert _webhook(client, "razorpay/webhook.payment.captured.json", edit=fresh).status_code == 200
    assert wire.calls == []                                     # a checkout still in flight is left alone

    assert _webhook(client, "razorpay/webhook.payment.captured.json").status_code == 200   # the fixture is long past
    refund = wire.sent("POST", "/refund")
    assert len(refund) == 1 and refund[0]["json"] == {"amount": 52500}


def test_webhook_payment_failed_marks_the_order(client, wire, razorpay_keys):
    _user, order, _variant = _paid_order()
    assert _webhook(client, "razorpay/webhook.payment.failed.json").status_code == 200
    db.session.expire_all()
    assert db.session.get(Order, order.id).payment_status == PaymentStatus.failed


def test_webhook_refund_processed_then_failed(client, wire, razorpay_keys):
    """A refund the bank bounces must not leave the order saying "refunded"."""
    _user, order, _variant = _paid_order()
    assert _webhook(client, "razorpay/webhook.refund.processed.json").status_code == 200
    db.session.expire_all()
    assert db.session.get(Order, order.id).payment_status == PaymentStatus.refunded

    assert _webhook(client, "razorpay/webhook.refund.failed.json").status_code == 200
    db.session.expire_all()
    assert db.session.get(Order, order.id).payment_status == PaymentStatus.paid


def test_webhook_delivered_twice_acts_once(client, wire, razorpay_keys):
    wire.on("POST", "/refund", 200, "razorpay/refund.created.json")
    first = _webhook(client, "razorpay/webhook.payment.captured.json", event_id="evt_contract_1")
    again = _webhook(client, "razorpay/webhook.payment.captured.json", event_id="evt_contract_1")
    assert first.status_code == 200 and again.status_code == 200
    assert again.get_json() == {"status": "duplicate"}
    assert len(wire.sent("POST", "/refund")) == 1


def test_reconcile_reads_the_payment_list_and_refunds_the_stale_orphan(app, wire, razorpay_keys):
    from app.routes.payments import reconcile_orphaned_captures

    wire.on("GET", "/v1/payments", 200, "razorpay/payment.list.json")
    wire.on("POST", f"/v1/payments/{PAY}/refund", 200, "razorpay/refund.created.json")
    # the fixture payment is far older than the sweep's window start, so widen it
    result = reconcile_orphaned_captures(window_seconds=10 * 365 * 86400)
    listing = wire.sent("GET", "/v1/payments")[0]
    assert listing["auth"] == (KEY_ID, KEY_SECRET)
    assert {"from", "to", "count", "skip"} <= set(listing["params"])
    assert len(wire.sent("POST", "/refund")) == 1
    assert result["refunded"] == 1 and result["failed"] == 0


# ── Without keys: nothing is offered, nothing breaks ──

def test_without_keys_online_payment_is_off_and_cash_on_delivery_works(client, wire, no_keys):
    user, address, _variant, _cart = _shopper()
    headers = customer_headers(user)

    features = client.get("/api/cms/features-available").get_json()
    assert features["online_payments"] is False
    assert features["delivery_check"] is False
    assert features["cash_on_delivery"] is True

    assert client.post("/api/payments/create-order", headers=headers).status_code == 503
    verify = client.post("/api/payments/verify", headers=headers, json={
        "razorpay_order_id": ORD, "razorpay_payment_id": PAY, "razorpay_signature": "x", "address_id": address.id})
    assert verify.status_code == 503
    assert client.post("/api/payments/webhook", data=b"{}", content_type="application/json").status_code in (400, 401, 503)
    pincode = client.get("/api/shipping/serviceability?pincode=400050")
    assert pincode.status_code < 500

    placed = client.post("/api/orders", headers=headers, json={"address_id": address.id, "payment_method": "cod"})
    assert placed.status_code in (200, 201), placed.get_json()
    assert wire.calls == []                                     # not one call left the building


def test_without_keys_system_health_says_not_configured(client, wire, no_keys):
    resp = client.get("/api/admin/system/health", headers=admin_headers())
    assert resp.status_code == 200
    text = json.dumps(resp.get_json()).lower()
    assert "not configured" in text or "not_configured" in text
    assert wire.calls == []


def test_without_keys_booking_a_shipment_explains_itself(client, wire, no_keys):
    _user, order, _variant = _paid_order()
    resp = client.post(f"/api/admin/orders/{order.id}/ship", headers=admin_headers())
    assert resp.status_code == 502
    assert "not configured" in resp.get_json()["error"]
    assert wire.calls == []


def test_keys_switch_the_features_on_with_no_code_change(client, wire, razorpay_keys, shiprocket_keys, app):
    from app.services import cache
    cache.clear() if hasattr(cache, "clear") else None
    features = client.get("/api/cms/features-available?fresh=1").get_json()
    assert features["online_payments"] is True
    assert features["delivery_check"] is True


# ════════════════════════════════════════════════════════════════
# Shiprocket
# ════════════════════════════════════════════════════════════════

def _sr(wire):
    return wire.on("POST", "/auth/login", 200, "shiprocket/auth.login.json")


def test_shiprocket_signs_in_once_and_reuses_the_token(wire, shiprocket_keys):
    _sr(wire).on("GET", "/courier/serviceability/", 200, "shiprocket/serviceability.json")
    shiprocket.check_serviceability("400050")
    shiprocket.check_serviceability("110001")

    logins = wire.sent("POST", "/auth/login")
    assert len(logins) == 1
    assert logins[0]["url"] == "https://apiv2.shiprocket.in/v1/external/auth/login"
    assert logins[0]["json"] == {"email": "api-user@example.com", "password": "contract-test-password"}
    for call in wire.sent("GET", "/courier/serviceability/"):
        assert call["headers"]["Authorization"] == "Bearer TEST.SHIPROCKET.TOKEN-1"


def test_shiprocket_renews_an_expired_token_and_retries_once(wire, shiprocket_keys):
    wire.on("POST", "/auth/login", 200, "shiprocket/auth.login.json")
    wire.on("POST", "/auth/login", 200, {**fixture("shiprocket/auth.login.json"), "token": "TEST.SHIPROCKET.TOKEN-2"})
    wire.on("GET", "/courier/track/awb/", 401, "shiprocket/unauthenticated.json")
    wire.on("GET", "/courier/track/awb/", 200, "shiprocket/tracking.json")

    events = shiprocket.track_by_awb("1091234567890")

    assert len(events) == 2
    assert len(wire.sent("POST", "/auth/login")) == 2
    tokens = [c["headers"]["Authorization"] for c in wire.sent("GET", "/courier/track/awb/")]
    assert tokens == ["Bearer TEST.SHIPROCKET.TOKEN-1", "Bearer TEST.SHIPROCKET.TOKEN-2"]


def test_shiprocket_wrong_credentials_are_reported_plainly(wire, shiprocket_keys):
    wire.on("POST", "/auth/login", 400, "shiprocket/auth.failed.json")
    with pytest.raises(shiprocket.ShiprocketError, match="authentication failed"):
        shiprocket.track_by_awb("1091234567890")


def test_serviceability_reads_couriers_cheapest_first(client, wire, shiprocket_keys):
    _sr(wire).on("GET", "/courier/serviceability/", 200, "shiprocket/serviceability.json")
    result = shiprocket.check_serviceability("400050", cod=True, weight=0.5)

    assert result["serviceable"] is True
    assert [c["name"] for c in result["couriers"]] == ["Delhivery Surface", "Xpressbees Air"]
    assert result["cheapest_rate"] == 62.5
    assert result["estimated_days"] == 2
    assert result["couriers"][0]["cod_available"] is True
    params = wire.sent("GET", "/courier/serviceability/")[0]["params"]
    assert params == {"pickup_postcode": "800001", "delivery_postcode": "400050", "cod": 1, "weight": 0.5}


def test_serviceability_for_a_pincode_nobody_serves(client, wire, shiprocket_keys):
    _sr(wire).on("GET", "/courier/serviceability/", 404, "shiprocket/serviceability.none.json")
    assert shiprocket.check_serviceability("999999")["serviceable"] is False
    resp = client.get("/api/shipping/serviceability?pincode=999999")
    assert resp.status_code == 200
    assert resp.get_json()["serviceable"] is False


def _book(wire):
    return (_sr(wire)
            .on("POST", "/orders/create/adhoc", 200, "shiprocket/order.created.json")
            .on("POST", "/courier/assign/awb", 200, "shiprocket/awb.assigned.json")
            .on("POST", "/courier/generate/pickup", 200, "shiprocket/pickup.scheduled.json"))


def test_booking_a_shipment_creates_the_order_assigns_an_awb_and_requests_pickup(client, wire, shiprocket_keys):
    _user, order, _variant = _paid_order()
    _book(wire)

    resp = client.post(f"/api/admin/orders/{order.id}/ship", headers=admin_headers())

    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["tracking_number"] == "1091234567890"
    assert body["courier_name"] == "Delhivery Surface"
    assert body["pickup_scheduled"] is True and body["pickup_date"] == "2026-10-12 10:00:00"

    sent = wire.sent("POST", "/orders/create/adhoc")[0]["json"]
    db.session.expire_all()
    order = db.session.get(Order, order.id)
    assert sent["order_id"] == order.order_number
    assert sent["payment_method"] == "Prepaid"
    assert sent["billing_pincode"] == order.address.pin_code
    assert sent["billing_country"] == "India"
    assert sent["shipping_is_billing"] is True
    assert sent["sub_total"] == float(order.total_amount)
    assert [(i["units"], i["selling_price"]) for i in sent["order_items"]] == [(1, 500.0)]
    assert all(sent[k] for k in ("billing_customer_name", "billing_last_name", "billing_address", "billing_city",
                                 "billing_state", "billing_email", "billing_phone", "pickup_location",
                                 "length", "breadth", "height", "weight"))
    assert wire.sent("POST", "/courier/assign/awb")[0]["json"] == {"shipment_id": 15151515}
    assert wire.sent("POST", "/courier/generate/pickup")[0]["json"] == {"shipment_id": [15151515]}

    assert order.status == OrderStatus.shipped
    assert order.tracking_number == "1091234567890"

    # a second press does not book a second parcel
    again = client.post(f"/api/admin/orders/{order.id}/ship", headers=admin_headers())
    assert again.status_code == 409
    assert len(wire.sent("POST", "/orders/create/adhoc")) == 1


def test_a_cash_on_delivery_order_is_booked_as_cod(client, wire, shiprocket_keys):
    user, address, _variant, _cart = _shopper()
    order, err = create_order_from_cart(user.id, address.id, "cod")
    assert err is None
    _book(wire)
    assert client.post(f"/api/admin/orders/{order.id}/ship", headers=admin_headers()).status_code == 201
    assert wire.sent("POST", "/orders/create/adhoc")[0]["json"]["payment_method"] == "COD"


def test_no_courier_available_leaves_the_order_unshipped(client, wire, shiprocket_keys):
    _user, order, _variant = _paid_order()
    (_sr(wire).on("POST", "/orders/create/adhoc", 200, "shiprocket/order.created.json")
              .on("POST", "/courier/assign/awb", 200, "shiprocket/awb.not_assigned.json"))
    resp = client.post(f"/api/admin/orders/{order.id}/ship", headers=admin_headers())
    assert resp.status_code == 502
    assert "serviceable" in resp.get_json()["error"]
    db.session.expire_all()
    order = db.session.get(Order, order.id)
    assert order.tracking_number is None and order.status != OrderStatus.shipped


def test_a_rejected_order_shows_the_couriers_own_reason(client, wire, shiprocket_keys):
    _user, order, _variant = _paid_order()
    _sr(wire).on("POST", "/orders/create/adhoc", 422, "shiprocket/order.rejected.json")
    resp = client.post(f"/api/admin/orders/{order.id}/ship", headers=admin_headers())
    assert resp.status_code == 502
    assert "Pickup location" in resp.get_json()["error"]


def test_a_refused_pickup_still_ships_and_says_so(client, wire, shiprocket_keys):
    _user, order, _variant = _paid_order()
    (_sr(wire).on("POST", "/orders/create/adhoc", 200, "shiprocket/order.created.json")
              .on("POST", "/courier/assign/awb", 200, "shiprocket/awb.assigned.json")
              .on("POST", "/courier/generate/pickup", 400, "shiprocket/pickup.refused.json"))
    resp = client.post(f"/api/admin/orders/{order.id}/ship", headers=admin_headers())
    assert resp.status_code == 201
    assert resp.get_json()["pickup_scheduled"] is False
    assert "Pickup Queue" in resp.get_json()["pickup_problem"]
    db.session.expire_all()
    assert db.session.get(Order, order.id).tracking_number == "1091234567890"


def test_the_courier_being_unreachable_is_a_502_not_a_crash(client, wire, shiprocket_keys):
    _user, order, _variant = _paid_order()
    _sr(wire).on("POST", "/orders/create/adhoc", error=requests.ReadTimeout("timed out"))
    resp = client.post(f"/api/admin/orders/{order.id}/ship", headers=admin_headers())
    assert resp.status_code == 502
    assert "Could not reach Shiprocket" in resp.get_json()["error"]


def test_tracking_sync_adds_each_event_once(client, wire, shiprocket_keys):
    _user, order, _variant = _paid_order()
    _book(wire).on("GET", "/courier/track/awb/1091234567890", 200, "shiprocket/tracking.json")
    headers = admin_headers()
    client.post(f"/api/admin/orders/{order.id}/ship", headers=headers)

    first = client.post(f"/api/admin/orders/{order.id}/sync-tracking", headers=headers)
    again = client.post(f"/api/admin/orders/{order.id}/sync-tracking", headers=headers)

    assert first.status_code == 200 and first.get_json()["added"] == 2
    assert again.status_code == 200 and again.get_json()["added"] == 0
    db.session.expire_all()
    labels = [t.status_label for t in db.session.get(Order, order.id).tracking]
    assert "In transit - Shipment picked up" in labels and "Manifested - Pickup scheduled" in labels


def test_tracking_with_no_events_yet_is_not_an_error(client, wire, shiprocket_keys):
    _user, order, _variant = _paid_order()
    _book(wire).on("GET", "/courier/track/awb/", 200, "shiprocket/tracking.none.json")
    headers = admin_headers()
    client.post(f"/api/admin/orders/{order.id}/ship", headers=headers)
    resp = client.post(f"/api/admin/orders/{order.id}/sync-tracking", headers=headers)
    assert resp.status_code == 200 and resp.get_json()["added"] == 0
