"""The reconcile-payments sweep: the safety net behind the Razorpay webhook."""
import hashlib
import hmac
import json
import time
from unittest.mock import patch

import pytest
import requests

from app.models.ops import JobRun, WebhookEvent
from app.routes import payments
from app.services.order_service import create_order_from_cart
from tests.factories import make_address, make_cart, make_product, make_user

WEBHOOK_SECRET = "whsec_test_secret"


@pytest.fixture(autouse=True)
def _configured(monkeypatch):
    monkeypatch.setenv("RAZORPAY_KEY_ID", "rzp_test_x")
    monkeypatch.setenv("RAZORPAY_KEY_SECRET", "secret")
    monkeypatch.setenv("RAZORPAY_WEBHOOK_SECRET", WEBHOOK_SECRET)


def _payment(payment_id, status="captured", age=7200, amount=50000, refunded=0):
    return {
        "id": payment_id, "status": status, "amount": amount,
        "amount_refunded": refunded, "created_at": int(time.time()) - age,
    }


class _Gateway:
    """Stands in for GET /payments, honouring count / skip like Razorpay."""

    def __init__(self, payments_, status_code=200):
        self.payments, self.status_code, self.calls = payments_, status_code, []

    def get(self, url, params=None, **kw):
        self.calls.append(params)
        page = self.payments[params["skip"]: params["skip"] + params["count"]]
        gateway = self

        class _Resp:
            status_code = gateway.status_code

            @staticmethod
            def json():
                return {"items": page}

        return _Resp()


def _run(gateway, **kw):
    with patch.object(payments.requests, "get", gateway.get), \
         patch.object(payments, "refund_payment", return_value=True) as refund:
        return payments.reconcile_orphaned_captures(**kw), refund


def test_refunds_only_stale_captures_without_an_order(app):
    user = make_user()
    _, variant = make_product(price=500, stock=5)
    make_cart(user, [(variant, 1)])
    order, err = create_order_from_cart(
        user.id, make_address(user).id, "upi", payment_ref="pay_HAS_ORDER", paid=True
    )
    assert err is None
    gateway = _Gateway([
        _payment("pay_ORPHAN"),
        _payment("pay_HAS_ORDER"),
        _payment("pay_INFLIGHT", age=30),
        _payment("pay_FAILED", status="failed"),
        _payment("pay_ALREADY_REFUNDED", refunded=50000),
    ])

    result, refund = _run(gateway)

    assert result["checked"] == 5
    assert [o["id"] for o in result["orphans"]] == ["pay_ORPHAN"]
    refund.assert_called_once_with("pay_ORPHAN", 50000)
    assert result["refunded"] == 1 and result["failed"] == 0


def test_pages_past_the_first_hundred_payments(app):
    gateway = _Gateway(
        [_payment(f"pay_{i}", status="failed") for i in range(230)]
        + [_payment("pay_LATE_ORPHAN")]
    )

    result, refund = _run(gateway)

    assert result["checked"] == 231
    assert [call["skip"] for call in gateway.calls] == [0, 100, 200]
    refund.assert_called_once_with("pay_LATE_ORPHAN", 50000)


def test_running_twice_does_not_refund_twice(app):
    """After a refund Razorpay reports the payment as refunded, not captured."""
    first, refund = _run(_Gateway([_payment("pay_ORPHAN")]))
    assert first["refunded"] == 1

    second, refund_again = _run(_Gateway([_payment("pay_ORPHAN", status="refunded")]))

    assert second["orphans"] == []
    refund_again.assert_not_called()


def test_dry_run_reports_without_refunding(app):
    result, refund = _run(_Gateway([_payment("pay_ORPHAN")]), dry_run=True)

    assert [o["id"] for o in result["orphans"]] == ["pay_ORPHAN"]
    assert result["refunded"] == 0
    refund.assert_not_called()


def test_a_failed_refund_is_counted_and_the_sweep_continues(app):
    gateway = _Gateway([_payment("pay_A"), _payment("pay_B")])
    with patch.object(payments.requests, "get", gateway.get), \
         patch.object(payments, "refund_payment", side_effect=[False, True]):
        result = payments.reconcile_orphaned_captures()

    assert result["failed"] == 1 and result["refunded"] == 1


def test_gateway_errors_are_reported_not_raised(app):
    result, refund = _run(_Gateway([], status_code=500))
    assert result["error"] == "gateway returned 500"
    refund.assert_not_called()

    def _down(*a, **kw):
        raise requests.ConnectionError("no route")

    with patch.object(payments.requests, "get", _down):
        assert payments.reconcile_orphaned_captures()["error"] == "gateway unreachable"


def test_each_run_is_recorded_for_the_health_panel(app):
    _run(_Gateway([_payment("pay_ORPHAN")]))

    run = JobRun.query.filter_by(name="reconcile-payments").one()
    assert run.ok is True
    assert run.finished_at is not None
    assert run.summary["checked"] == 1 and run.summary["refunded"] == 1
    # Counts only: payment ids stay in the logs, not in a table an admin screen reads.
    assert run.summary["orphans"] == 1


def test_unconfigured_gateway_is_a_no_op(app, monkeypatch):
    monkeypatch.delenv("RAZORPAY_KEY_ID")

    result = payments.reconcile_orphaned_captures()

    assert result["configured"] is False
    assert JobRun.query.count() == 0


def test_cli_exits_non_zero_when_a_refund_fails(app):
    gateway = _Gateway([_payment("pay_A")])
    with patch.object(payments.requests, "get", gateway.get), \
         patch.object(payments, "refund_payment", return_value=False):
        result = app.test_cli_runner().invoke(args=["reconcile-payments"])

    assert result.exit_code != 0
    assert "refund(s) failed" in result.output


def test_cli_dry_run_exits_cleanly(app):
    gateway = _Gateway([_payment("pay_A")])
    with patch.object(payments.requests, "get", gateway.get), \
         patch.object(payments, "refund_payment") as refund:
        result = app.test_cli_runner().invoke(args=["reconcile-payments", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "dry run" in result.output
    refund.assert_not_called()


# ── Webhook idempotency ───────────────────────────────────────

def _deliver(client, event, event_id):
    raw = json.dumps(event).encode()
    signature = hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
    return client.post(
        "/api/payments/webhook", data=raw, content_type="application/json",
        headers={"X-Razorpay-Signature": signature, "X-Razorpay-Event-Id": event_id},
    )


def _captured(payment_id):
    return {"event": "payment.captured",
            "payload": {"payment": {"entity": _payment(payment_id)}}}


def test_a_redelivered_event_is_acknowledged_but_not_acted_on_twice(app, client):
    with patch.object(payments, "refund_payment", return_value=True) as refund:
        first = _deliver(client, _captured("pay_ORPHAN"), "evt_1")
        second = _deliver(client, _captured("pay_ORPHAN"), "evt_1")

    assert first.status_code == second.status_code == 200
    assert first.get_json()["status"] == "ok"
    assert second.get_json()["status"] == "duplicate"
    refund.assert_called_once()
    assert WebhookEvent.query.count() == 1


def test_a_different_event_id_is_processed(app, client):
    with patch.object(payments, "refund_payment", return_value=True) as refund:
        _deliver(client, _captured("pay_A"), "evt_1")
        _deliver(client, _captured("pay_B"), "evt_2")

    assert refund.call_count == 2


def test_an_event_that_fails_mid_handling_can_be_retried(app, client):
    """The claim on the event id rolls back with the failed request."""
    with patch.object(payments, "refund_payment", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            _deliver(client, _captured("pay_ORPHAN"), "evt_1")
    assert WebhookEvent.query.count() == 0

    with patch.object(payments, "refund_payment", return_value=True) as refund:
        retry = _deliver(client, _captured("pay_ORPHAN"), "evt_1")

    assert retry.get_json()["status"] == "ok"
    refund.assert_called_once()
