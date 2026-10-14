"""Admin dashboard, system health, maintenance mode, audit log, review moderation."""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.extensions import db
from app.models.engagement import ProductReview
from app.models.enums import OrderStatus, PaymentStatus, ReturnStatus
from app.models.ops import AuditLog, JobRun
from app.models.order import Order, Return
from app.services import maintenance
from app.services.order_service import create_order_from_cart
from tests.factories import make_address, make_cart, make_product, make_user
from tests.helpers import admin_headers, customer_headers, make_admin


@pytest.fixture(autouse=True)
def _fresh_maintenance_cache():
    maintenance.reset_cache()
    yield
    maintenance.reset_cache()


@pytest.fixture(autouse=True)
def _no_integrations(monkeypatch):
    for key in (
        "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET",
        "SHIPROCKET_EMAIL", "SHIPROCKET_PASSWORD", "SHIPROCKET_PICKUP_PINCODE",
        "GOOGLE_CLIENT_ID",
    ):
        monkeypatch.delenv(key, raising=False)


def _order(user=None, price=500, quantity=2, stock=10, **kw):
    user = user or make_user()
    _, variant = make_product(price=price, stock=stock)
    make_cart(user, [(variant, quantity)])
    order, err = create_order_from_cart(user.id, make_address(user).id, "cod", **kw)
    assert err is None, err
    return order, variant


def _check(body, key):
    return next(c for c in body["checks"] if c["key"] == key)


# ── Dashboard ─────────────────────────────────────────────────

def test_dashboard_overview_matches_the_database(app, client):
    order, _ = _order(quantity=2)            # 2 x 500 + GST + delivery
    cancelled, _ = _order(quantity=1)
    cancelled.status = OrderStatus.cancelled
    make_product(stock=0)                    # out of stock
    make_product(stock=3)                    # low stock
    db.session.commit()

    resp = client.get("/api/admin/dashboard/overview", headers=admin_headers())

    assert resp.status_code == 200, resp.get_data(as_text=True)
    body = resp.get_json()
    paid_total = float(order.total_amount)
    # A cancelled order is not revenue, in any window.
    assert body["revenue"]["today"] == paid_total
    assert body["revenue"]["last_7d"] == paid_total
    assert body["revenue"]["last_30d"] == paid_total
    assert body["revenue"]["range"] == paid_total
    assert body["orders"]["range"] == Order.query.count() == 2
    assert body["orders"]["by_status"]["pending"] == 1
    assert body["orders"]["by_status"]["cancelled"] == 1
    assert body["orders"]["average_value"] == paid_total
    assert body["products"]["out_of_stock"] == 1
    assert body["products"]["low_stock"] == 1
    assert {i["stock_qty"] for i in body["products"]["low_stock_items"]} == {0, 3}
    assert body["pending"]["returns"] == 0
    assert body["pending"]["orders"] == 1
    assert len(body["recent_orders"]) == 2
    assert body["recent_orders"][0]["customer_name"] == "Test User"
    assert body["top_products"][0]["units"] == 2
    # One point per day, and the days add up to the range total.
    assert len(body["series"]) == body["range"]["days"] == 30
    assert sum(point["revenue"] for point in body["series"]) == paid_total


def test_dashboard_range_excludes_orders_outside_it(app, client):
    order, _ = _order()
    order.placed_at = datetime.now(timezone.utc) - timedelta(days=60)
    db.session.commit()
    day = lambda offset: (datetime.now(timezone.utc) - timedelta(days=offset)).date().isoformat()  # noqa: E731
    headers = admin_headers()

    recent = client.get(
        f"/api/admin/dashboard/overview?from={day(7)}&to={day(0)}", headers=headers
    ).get_json()
    assert recent["revenue"]["range"] == 0
    assert recent["orders"]["range"] == 0
    assert recent["range"]["days"] == 8

    wide = client.get(
        f"/api/admin/dashboard/overview?from={day(90)}&to={day(0)}", headers=headers
    ).get_json()
    assert wide["revenue"]["range"] == float(order.total_amount)
    # "last 30 days" is fixed, whatever range is selected.
    assert wide["revenue"]["last_30d"] == 0


def test_dashboard_tolerates_a_reversed_or_malformed_range(app, client):
    headers = admin_headers()

    reversed_range = client.get(
        "/api/admin/dashboard/overview?from=2026-03-10&to=2026-03-01", headers=headers
    )
    garbage = client.get(
        "/api/admin/dashboard/overview?from=yesterday&to=", headers=headers
    )

    assert reversed_range.status_code == 200
    assert reversed_range.get_json()["range"] == {
        "from": "2026-03-01", "to": "2026-03-10", "days": 10, "timezone": "Asia/Kolkata",
    }
    assert garbage.status_code == 200


def test_dashboard_runs_a_fixed_number_of_queries(app, client):
    """The point of one endpoint: its cost must not grow with the data."""
    from sqlalchemy import event

    for _ in range(6):
        _order()
    headers = admin_headers()
    statements = []

    def _count(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(db.engine, "before_cursor_execute", _count)
    try:
        client.get("/api/admin/dashboard/overview", headers=headers)
    finally:
        event.remove(db.engine, "before_cursor_execute", _count)

    # 8 data queries + the admin lookup in the auth decorator.
    assert len(statements) <= 12, len(statements)


# ── System health ─────────────────────────────────────────────

def test_health_reports_unconfigured_integrations_without_erroring(app, client):
    resp = client.get("/api/admin/system/health", headers=admin_headers())

    assert resp.status_code == 200
    body = resp.get_json()
    assert _check(body, "database")["status"] == "ok"
    assert _check(body, "database")["latency_ms"] >= 0
    for key in ("razorpay", "shiprocket", "google_login"):
        assert _check(body, key)["status"] == "not_configured", key
    assert body["status"] == "ok"   # "not configured" is a valid way to run
    assert body["reconcile_payments"] is None
    assert body["app"]["environment"] == "testing"


def test_health_flags_a_half_configured_integration(app, client, monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_abc")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "s3cr3t-value")

    body = client.get("/api/admin/system/health", headers=admin_headers()).get_json()

    razorpay = _check(body, "razorpay")
    assert razorpay["status"] == "error"
    assert "Webhook secret" in razorpay["detail"]
    assert razorpay["mode"] == "test"
    assert body["status"] == "error"


def test_health_never_returns_a_configured_value(app, client, monkeypatch):
    secrets = {
        "RAZORPAY_KEY_ID": "rzp_live_PUBLICKEYID", "RAZORPAY_KEY_SECRET": "RZP-SECRET-VALUE",
        "RAZORPAY_WEBHOOK_SECRET": "WHSEC-VALUE",
        "SHIPROCKET_EMAIL": "courier-api@example.com", "SHIPROCKET_PASSWORD": "SHIP-PASSWORD",
        "SHIPROCKET_PICKUP_PINCODE": "800001", "GOOGLE_CLIENT_ID": "google-client-id-value",
    }
    for key, value in secrets.items():
        monkeypatch.setenv(key, value)
    # Object storage, configured explicitly. This used the old Supabase
    # settings and passed locally only because a real S3_* .env leaked in;
    # CI, with no .env, showed storage as "not configured".
    monkeypatch.setitem(app.config, "S3_ENDPOINT_URL", "https://project-ref.storage.example")
    monkeypatch.setitem(app.config, "S3_BUCKET", "product-images")
    monkeypatch.setitem(app.config, "S3_ACCESS_KEY_ID", "S3-ACCESS-KEY-ID-VALUE")
    monkeypatch.setitem(app.config, "S3_SECRET_ACCESS_KEY", "S3-SECRET-ACCESS-KEY-VALUE")
    monkeypatch.setitem(app.config, "SENTRY_DSN", "https://key@sentry.example/1")
    monkeypatch.setitem(app.config, "RESEND_API_KEY", "RESEND-KEY")
    monkeypatch.setitem(app.config, "EMAIL_FROM", "orders@example.com")

    resp = client.get("/api/admin/system/health", headers=admin_headers())

    text = resp.get_data(as_text=True)
    for value in list(secrets.values()) + [
        "project-ref", "S3-ACCESS-KEY-ID-VALUE", "S3-SECRET-ACCESS-KEY-VALUE",
        "sentry.example", "RESEND-KEY",
    ]:
        if value == "800001":
            continue
        assert value not in text, value
    body = resp.get_json()
    for key in ("razorpay", "shiprocket", "storage", "email", "sentry", "google_login"):
        assert _check(body, key)["status"] == "ok", key
    assert _check(body, "razorpay")["mode"] == "live"


def test_health_probe_reports_rejected_credentials(app, client, monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_abc")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "wrong")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", "whsec")

    class _Unauthorised:
        status_code = 401

    with patch("app.services.health.requests.get", return_value=_Unauthorised()):
        body = client.get(
            "/api/admin/system/health?probe=1", headers=admin_headers()
        ).get_json()

    assert body["probed"] is True
    assert _check(body, "razorpay")["status"] == "error"
    assert "rejected" in _check(body, "razorpay")["detail"]


def test_health_shows_the_last_reconcile_run(app, client):
    db.session.add(JobRun(
        name="reconcile-payments", ok=True,
        summary={"checked": 4, "refunded": 1, "failed": 0, "orphans": 1},
    ))
    db.session.commit()

    body = client.get("/api/admin/system/health", headers=admin_headers()).get_json()

    assert body["reconcile_payments"]["ok"] is True
    assert body["reconcile_payments"]["summary"]["refunded"] == 1
    assert body["reconcile_payments"]["stale"] is False


# ── Maintenance mode ──────────────────────────────────────────

def test_maintenance_closes_the_storefront_but_not_the_admin_panel(app, client):
    master = make_admin(role="master")
    headers = admin_headers(master)
    make_product(slug="linen-kurta")
    assert client.get("/api/products").status_code == 200

    switched = client.put(
        "/api/admin/system/maintenance", headers=headers,
        json={"enabled": True, "message": "Back at 6 pm."},
    )
    assert switched.status_code == 200
    assert switched.get_json() == {"enabled": True, "message": "Back at 6 pm."}

    closed = client.get("/api/products")
    assert closed.status_code == 503
    assert closed.get_json() == {"error": "Back at 6 pm.", "maintenance": True}
    assert closed.headers["Retry-After"]
    assert client.post("/api/auth/login", json={
        "email": "a@example.com", "password": "whatever",
    }).status_code == 503

    # Still open: admin (including sign-in), the settings the maintenance page
    # reads, the health probe, and the payment webhook.
    assert client.get("/api/admin/products", headers=headers).status_code == 200
    assert client.post("/api/admin/auth/login", json={
        "email": master.email, "password": "AdminPass123!",
    }).status_code == 200
    settings = client.get("/api/cms/settings")
    assert settings.status_code == 200
    assert settings.get_json()["settings"]["maintenance_mode"] == "true"
    assert client.get("/api/health").status_code == 200
    assert client.post("/api/payments/webhook", data=b"{}").status_code != 503 or \
        "not configured" in client.post("/api/payments/webhook", data=b"{}").get_json()["error"]

    client.put("/api/admin/system/maintenance", headers=headers, json={"enabled": False})
    assert client.get("/api/products").status_code == 200


def test_only_a_master_admin_can_switch_maintenance_mode(app, client):
    resp = client.put(
        "/api/admin/system/maintenance", headers=admin_headers(role="staff"),
        json={"enabled": True},
    )

    assert resp.status_code == 403
    assert client.get("/api/products").status_code == 200


def test_maintenance_falls_back_to_a_default_message(app, client):
    headers = admin_headers()
    client.put("/api/admin/system/maintenance", headers=headers, json={"enabled": True})

    state = client.get("/api/admin/system/maintenance", headers=headers).get_json()

    assert state["enabled"] is True
    assert "back shortly" in state["message"]


# ── Audit log ─────────────────────────────────────────────────

def test_admin_writes_are_recorded_with_who_and_what(app, client):
    admin = make_admin(email="auditor@example.com")
    headers = admin_headers(admin)

    created = client.post("/api/admin/categories", headers=headers,
                          json={"name": "Footwear", "slug": "footwear"}).get_json()
    client.get("/api/admin/categories", headers=headers)   # reads are not audited

    entries = AuditLog.query.all()
    assert len(entries) == 1
    entry = entries[0]
    assert entry.actor_type == "admin"
    assert entry.actor_label == "auditor@example.com"
    assert entry.action == "create_category"
    assert entry.entity_type == "categories"
    assert entry.entity_id == str(created["id"])
    assert entry.changes["slug"] == "footwear"


def test_failed_admin_writes_are_not_recorded(app, client):
    client.post("/api/admin/categories", headers=admin_headers(), json={"name": "x"})

    assert AuditLog.query.count() == 0


def test_passwords_never_reach_the_audit_log(app, client):
    client.post("/api/admin/auth/admins", headers=admin_headers(), json={
        "email": "staff@example.com", "password": "StaffPass123!",
        "full_name": "Staff Member",
    })

    entry = AuditLog.query.one()
    assert entry.changes["password"] == "[redacted]"
    assert "StaffPass123!" not in str(entry.changes)


def test_order_status_change_is_summarised(app, client):
    order, _ = _order()

    client.patch(f"/api/admin/orders/{order.id}/status", headers=admin_headers(),
                 json={"status": "confirmed"})

    entry = AuditLog.query.one()
    assert entry.entity_type == "orders"
    assert entry.entity_id == str(order.id)
    assert "pending → confirmed" in entry.summary
    assert entry.changes == {"from": "pending", "to": "confirmed"}


def test_audit_log_can_be_filtered_and_searched(app, client):
    headers = admin_headers()
    client.post("/api/admin/categories", headers=headers,
                json={"name": "Footwear", "slug": "footwear"})
    client.post("/api/admin/coupons", headers=headers, json={
        "code": "SAVE10", "discount_type": "percentage", "discount_value": 10,
    })

    everything = client.get("/api/admin/audit-log", headers=headers)
    assert everything.status_code == 200
    body = everything.get_json()
    assert body["total"] == 2
    assert body["entity_types"] == ["categories", "coupons"]
    # Newest first.
    assert [e["entity_type"] for e in body["entries"]] == ["coupons", "categories"]

    coupons = client.get("/api/admin/audit-log?entity_type=coupons", headers=headers).get_json()
    assert [e["action"] for e in coupons["entries"]] == ["create_coupon"]
    found = client.get("/api/admin/audit-log?q=create_category", headers=headers).get_json()
    assert found["total"] == 1
    future = client.get("/api/admin/audit-log?from=2999-01-01", headers=headers).get_json()
    assert future["total"] == 0


def test_customer_cancellation_refund_is_on_the_trail(app, client, monkeypatch):
    user = make_user()
    order, _ = _order(user=user, payment_ref="pay_PREPAID", paid=True)

    with patch("app.routes.payments.refund_payment", return_value=True):
        resp = client.post(f"/api/orders/{order.id}/cancel", headers=customer_headers(user))

    assert resp.status_code == 200
    entry = AuditLog.query.one()
    assert entry.entity_type == "refunds"
    assert entry.actor_type == "customer"
    assert entry.changes["succeeded"] is True
    assert order.order_number in entry.summary


# ── Reviews ───────────────────────────────────────────────────

def test_reviews_can_be_listed_filtered_and_removed(app, client):
    product, _ = make_product(name="Linen Kurta")
    asha = make_user(full_name="Asha Rao")
    db.session.add_all([
        ProductReview(product_id=product.id, user_id=asha.id, rating=5,
                      title="Lovely", body="Great fabric.", is_verified=True),
        ProductReview(product_id=product.id, user_id=make_user().id, rating=1,
                      title="Spam", body="Buy followers at example.com"),
    ])
    db.session.commit()
    headers = admin_headers()

    listed = client.get("/api/admin/reviews", headers=headers)
    assert listed.status_code == 200
    assert listed.get_json()["total"] == 2

    one_star = client.get("/api/admin/reviews?rating=1", headers=headers).get_json()["reviews"]
    assert [r["title"] for r in one_star] == ["Spam"]
    assert client.get("/api/admin/reviews?q=asha", headers=headers).get_json()["total"] == 1
    assert client.get("/api/admin/reviews?verified=true", headers=headers).get_json()["total"] == 1
    by_rating = client.get("/api/admin/reviews?sort=rating&dir=asc", headers=headers).get_json()
    assert [r["rating"] for r in by_rating["reviews"]] == [1, 5]

    removed = client.delete(f"/api/admin/reviews/{one_star[0]['id']}", headers=headers)
    assert removed.status_code == 200
    assert ProductReview.query.count() == 1
    # What was removed is kept on the trail.
    entry = AuditLog.query.filter_by(action="admin_delete_review").one()
    assert entry.changes["body"] == "Buy followers at example.com"


# ── Returns: resolving one moves money and stock ──────────────

def _requested_return(client, paid=False):
    user = make_user()
    kw = {"payment_ref": "pay_PREPAID", "paid": True} if paid else {}
    order, variant = _order(user=user, quantity=2, stock=10, **kw)
    order.status = OrderStatus.delivered
    db.session.commit()
    return_id = client.post(
        "/api/returns", headers=customer_headers(user),
        json={"order_item_id": order.items[0].id, "reason": "size_issue"},
    ).get_json()["id"]
    return order, variant, return_id


def test_resolving_a_prepaid_return_refunds_through_the_gateway(app, client):
    order, variant, return_id = _requested_return(client, paid=True)

    with patch("app.routes.payments.refund_payment", return_value=True) as refund:
        resp = client.patch(f"/api/admin/returns/{return_id}", headers=admin_headers(), json={
            "status": "resolved", "resolution_type": "refund",
            "refund_amount": 600, "restock": True,
        })

    assert resp.status_code == 200, resp.get_data(as_text=True)
    assert resp.get_json()["refund_method"] == "gateway"
    refund.assert_called_once_with("pay_PREPAID", 60000, reason=f"return_{return_id}")
    db.session.expire_all()
    assert db.session.get(Return, return_id).status == ReturnStatus.resolved
    assert variant.stock_qty == 10          # 10 - 2 sold + 2 restocked
    assert db.session.get(Order, order.id).status == OrderStatus.returned
    entry = AuditLog.query.filter_by(entity_type="refunds").one()
    assert "refunded ₹600.00 (gateway)" in entry.summary
    assert "item restocked" in entry.summary


def test_a_failed_gateway_refund_leaves_the_return_open(app, client):
    order, variant, return_id = _requested_return(client, paid=True)

    with patch("app.routes.payments.refund_payment", return_value=False):
        resp = client.patch(f"/api/admin/returns/{return_id}", headers=admin_headers(), json={
            "status": "resolved", "resolution_type": "refund", "restock": True,
        })

    assert resp.status_code == 502
    db.session.expire_all()
    assert db.session.get(Return, return_id).status == ReturnStatus.requested
    assert variant.stock_qty == 8           # nothing restocked
    assert AuditLog.query.count() == 0


def test_a_cod_return_is_resolved_as_a_manual_refund(app, client):
    order, variant, return_id = _requested_return(client, paid=False)

    with patch("app.routes.payments.refund_payment") as refund:
        resp = client.patch(f"/api/admin/returns/{return_id}", headers=admin_headers(), json={
            "status": "resolved", "resolution_type": "refund",
        })

    assert resp.status_code == 200
    body = resp.get_json()
    assert body["refund_method"] == "manual"
    assert body["refund_amount"] == 1000    # defaults to what the item cost
    refund.assert_not_called()
    db.session.expire_all()
    assert variant.stock_qty == 8           # restock was not asked for


def test_a_closed_return_cannot_be_resolved_again(app, client):
    order, variant, return_id = _requested_return(client, paid=True)
    headers = admin_headers()
    payload = {"status": "resolved", "resolution_type": "refund", "restock": True}

    with patch("app.routes.payments.refund_payment", return_value=True) as refund:
        first = client.patch(f"/api/admin/returns/{return_id}", headers=headers, json=payload)
        second = client.patch(f"/api/admin/returns/{return_id}", headers=headers, json=payload)

    assert first.status_code == 200
    assert second.status_code == 409
    refund.assert_called_once()
    db.session.expire_all()
    assert variant.stock_qty == 10          # restocked once, not twice


def test_resolving_needs_a_resolution_type(app, client):
    order, variant, return_id = _requested_return(client)

    resp = client.patch(f"/api/admin/returns/{return_id}", headers=admin_headers(),
                        json={"status": "resolved"})

    assert resp.status_code == 422


def test_rejecting_a_return_puts_the_order_back_to_delivered(app, client):
    order, variant, return_id = _requested_return(client)
    assert db.session.get(Order, order.id).status == OrderStatus.return_requested

    resp = client.patch(f"/api/admin/returns/{return_id}", headers=admin_headers(),
                        json={"status": "rejected"})

    assert resp.status_code == 200
    db.session.expire_all()
    assert db.session.get(Order, order.id).status == OrderStatus.delivered
    assert db.session.get(Order, order.id).payment_status == PaymentStatus.unpaid \
        if hasattr(PaymentStatus, "unpaid") else True


# ── Lists are paged and searchable ────────────────────────────

def test_simple_admin_lists_are_capped_and_searchable(app, client):
    headers = admin_headers()
    for i in range(5):
        client.post("/api/admin/coupons", headers=headers, json={
            "code": f"SAVE{i}0", "discount_type": "percentage", "discount_value": 10,
        })
    client.post("/api/admin/coupons", headers=headers, json={
        "code": "FESTIVE", "discount_type": "flat", "discount_value": 100,
    })

    first = client.get("/api/admin/coupons?per_page=4", headers=headers).get_json()
    assert len(first["coupons"]) == 4
    assert first["total"] == 6 and first["pages"] == 2

    found = client.get("/api/admin/coupons?q=fest", headers=headers).get_json()
    assert [c["code"] for c in found["coupons"]] == ["FESTIVE"]

    # A silly page size is clamped, not obeyed.
    huge = client.get("/api/admin/coupons?per_page=100000", headers=headers).get_json()
    assert len(huge["coupons"]) == 6
    assert client.get("/api/admin/coupons?per_page=-5&page=-2", headers=headers).status_code == 200


def test_user_list_counts_orders_without_a_query_per_row(app, client):
    from sqlalchemy import event

    for _ in range(4):
        _order()
    headers = admin_headers()
    statements = []

    def _count(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(db.engine, "before_cursor_execute", _count)
    try:
        body = client.get("/api/admin/users", headers=headers).get_json()
    finally:
        event.remove(db.engine, "before_cursor_execute", _count)

    assert [u["order_count"] for u in body["users"]] == [1, 1, 1, 1]
    assert len(statements) <= 5, len(statements)


def test_user_update_rejects_values_of_the_wrong_type(app, client):
    user = make_user()
    headers = admin_headers()

    assert client.patch(f"/api/admin/users/{user.id}", headers=headers,
                        json={"is_active": "false"}).status_code == 422
    assert client.patch(f"/api/admin/users/{user.id}", headers=headers,
                        json={"account_type": "vip"}).status_code == 422
    assert client.patch(f"/api/admin/users/{user.id}", headers=headers,
                        json={}).status_code == 422

    ok = client.patch(f"/api/admin/users/{user.id}", headers=headers,
                      json={"account_type": "wholesale"})
    assert ok.status_code == 200
    db.session.expire_all()
    assert user.account_type.value == "wholesale"


# ── Search, filter and sort on the big lists ──────────────────

def test_orders_list_search_filter_sort(app, client):
    asha = make_user(email="asha@example.com", full_name="Asha Rao")
    small, _ = _order(user=asha, price=300, quantity=1)
    big, _ = _order(price=900, quantity=2)
    big.status = OrderStatus.delivered
    db.session.commit()
    headers = admin_headers()
    ids = lambda url: [o["id"] for o in client.get(url, headers=headers).get_json()["orders"]]  # noqa: E731

    # Found by customer name or email, not only by order number.
    assert ids("/api/admin/orders?q=asha") == [small.id]
    assert ids("/api/admin/orders?q=asha@example.com") == [small.id]
    assert ids(f"/api/admin/orders?q={big.order_number}") == [big.id]
    assert ids("/api/admin/orders?status=delivered") == [big.id]
    assert ids("/api/admin/orders?sort=total_amount&dir=asc") == [small.id, big.id]
    assert ids("/api/admin/orders?sort=total_amount&dir=desc") == [big.id, small.id]
    assert ids("/api/admin/orders?from=2999-01-01") == []
    # An unknown sort column falls back instead of erroring or leaking columns.
    assert client.get("/api/admin/orders?sort=password_hash", headers=headers).status_code == 200


def test_orders_list_does_not_query_per_row(app, client):
    from sqlalchemy import event

    for _ in range(5):
        _order()
    headers = admin_headers()
    statements = []

    def _count(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(db.engine, "before_cursor_execute", _count)
    try:
        body = client.get("/api/admin/orders", headers=headers).get_json()
    finally:
        event.remove(db.engine, "before_cursor_execute", _count)

    assert len(body["orders"]) == 5
    assert body["orders"][0]["customer_name"] == "Test User"
    assert len(statements) <= 5, len(statements)


def test_products_list_stock_filter_and_sort(app, client):
    make_product(name="Alpha Kurta", slug="alpha", price=900, stock=0)
    make_product(name="Beta Saree", slug="beta", price=300, stock=3)
    make_product(name="Gamma Tee", slug="gamma", price=600, stock=40)
    headers = admin_headers()
    names = lambda url: [p["name"] for p in client.get(url, headers=headers).get_json()["products"]]  # noqa: E731

    assert names("/api/admin/products?stock=out") == ["Alpha Kurta"]
    assert names("/api/admin/products?stock=low") == ["Beta Saree"]
    assert names("/api/admin/products?sort=selling_price&dir=asc") == [
        "Beta Saree", "Gamma Tee", "Alpha Kurta",
    ]
    assert names("/api/admin/products?sort=name&dir=asc")[0] == "Alpha Kurta"
    assert names("/api/admin/products?q=gamma") == ["Gamma Tee"]


def test_returns_list_shows_what_the_admin_needs_to_decide(app, client):
    order, variant, return_id = _requested_return(client, paid=True)
    headers = admin_headers()

    body = client.get("/api/admin/returns?status=open", headers=headers).get_json()

    row = body["returns"][0]
    assert row["order_number"] == order.order_number
    assert row["item_total"] == 1000 and row["quantity"] == 2
    assert row["prepaid"] is True
    assert client.get(
        f"/api/admin/returns?q={order.order_number}", headers=headers
    ).get_json()["total"] == 1
    assert client.get("/api/admin/returns?q=nobody", headers=headers).get_json()["total"] == 0

    client.patch(f"/api/admin/returns/{return_id}", headers=headers, json={"status": "rejected"})
    assert client.get("/api/admin/returns?status=open", headers=headers).get_json()["total"] == 0


def test_the_settings_form_cannot_flip_maintenance_mode(app, client):
    headers = admin_headers()
    client.put("/api/admin/system/maintenance", headers=headers, json={"enabled": True})

    listed = client.get("/api/admin/site-settings", headers=headers).get_json()["settings"]
    assert "maintenance_mode" not in [s["key"] for s in listed]

    resp = client.put("/api/admin/site-settings", headers=headers, json={
        "settings": [{"key": "maintenance_mode", "value": "false"}],
    })
    assert resp.status_code == 422
    assert client.get("/api/admin/system/maintenance", headers=headers).get_json()["enabled"] is True


# ── Database schema check ─────────────────────────────────────

def test_schema_check_passes_on_a_migrated_database(app, client):
    from app.services import schema_check

    result = schema_check.status()
    assert result == {"reachable": True, "empty": False, "pending": [], "missing": [], "error": None}
    checks = {c["key"]: c for c in client.get("/api/admin/system/health", headers=admin_headers()).get_json()["checks"]}
    assert checks["schema"]["status"] == "ok" and "migrations applied" in checks["schema"]["detail"]

    runner = app.test_cli_runner()
    assert runner.invoke(args=["check-schema"]).exit_code == 0
    done = runner.invoke(args=["apply-migrations"])
    assert done.exit_code == 0 and "Nothing to apply" in done.output


def test_schema_check_names_a_pending_migration_and_the_command_applies_it(app, client):
    """Drop what one migration creates, see it reported everywhere, apply, see it clear."""
    from sqlalchemy import text
    from app.services import schema_check

    db.session.execute(text("DROP TABLE public.faq_items"))
    db.session.commit()
    try:
        result = schema_check.status()
        assert result["pending"] == ["migrations_owner_dashboard.sql"] and result["missing"] == ["faq_items"]
        assert "flask apply-migrations" in schema_check.describe(result)

        body = client.get("/api/admin/system/health", headers=admin_headers()).get_json()
        checks = {c["key"]: c for c in body["checks"]}
        assert body["status"] == "error" and checks["schema"]["status"] == "error"
        assert "migrations_owner_dashboard.sql" in checks["schema"]["detail"]
        assert app.test_cli_runner().invoke(args=["check-schema"]).exit_code == 1
    finally:
        # (the test's own open transaction would otherwise block the ALTER TABLEs)
        db.session.rollback()
        applied = app.test_cli_runner().invoke(args=["apply-migrations"])
    assert applied.exit_code == 0 and "applied migrations_owner_dashboard.sql" in applied.output
    assert schema_check.status()["pending"] == []
    assert client.get("/api/content/faq").status_code == 200


def test_unreachable_database_is_reported_not_raised(app, monkeypatch):
    from app.services import schema_check

    class Broken:
        def connect(self):
            raise RuntimeError("connection refused\nmore detail")

    monkeypatch.setattr(type(db), "engine", property(lambda self: Broken()))
    result = schema_check.status()
    assert result["reachable"] is False and result["error"] == "connection refused"
    assert "cannot be reached" in schema_check.describe(result)
