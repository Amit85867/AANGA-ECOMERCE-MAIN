"""Tests for structured logging + Sentry gating."""
import json
import logging

from app.observability import JsonFormatter, init_sentry


def test_json_formatter_emits_valid_json():
    record = logging.LogRecord(
        name="app", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hello %s", args=("world",), exc_info=None,
    )
    out = json.loads(JsonFormatter().format(record))
    assert out["level"] == "INFO"
    assert out["logger"] == "app"
    assert out["message"] == "hello world"
    assert "time" in out


def test_json_formatter_includes_exception():
    try:
        raise ValueError("boom")
    except ValueError:
        import sys
        record = logging.LogRecord(
            name="app", level=logging.ERROR, pathname=__file__, lineno=1,
            msg="failed", args=(), exc_info=sys.exc_info(),
        )
    out = json.loads(JsonFormatter().format(record))
    assert "ValueError: boom" in out["exception"]


def test_init_sentry_noop_without_dsn(app):
    # No SENTRY_DSN in test config → must not raise or initialise anything.
    assert init_sentry(app) is None
