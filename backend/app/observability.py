"""Structured logging + Sentry error reporting.

Both are safe no-ops without configuration: Sentry only initialises when
SENTRY_DSN is set, and JSON logging is skipped under TESTING so pytest's log
capture is untouched. The PAID_BUT_NO_ORDER / refund `critical` logs become
first-class Sentry events automatically.
"""
import json
import logging
import uuid

from flask import g, request, has_request_context


class JsonFormatter(logging.Formatter):
    """One JSON object per log line — parseable by the platform log viewer."""

    def format(self, record):
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if has_request_context():
            payload["request_id"] = getattr(g, "request_id", None)
            payload["method"] = request.method
            payload["path"] = request.path
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def init_logging(app):
    if app.config.get("TESTING"):
        return

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())

    level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Flask's own logger should use the same handler, once.
    app.logger.handlers = [handler]
    app.logger.setLevel(level)
    app.logger.propagate = False

    @app.before_request
    def _assign_request_id():
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex

    @app.after_request
    def _echo_request_id(resp):
        rid = getattr(g, "request_id", None)
        if rid:
            resp.headers.setdefault("X-Request-ID", rid)
        return resp


def init_sentry(app):
    dsn = app.config.get("SENTRY_DSN")
    if not dsn:
        return

    import sentry_sdk
    from sentry_sdk.integrations.flask import FlaskIntegration

    sentry_sdk.init(
        dsn=dsn,
        integrations=[FlaskIntegration()],
        environment=app.config.get("SENTRY_ENVIRONMENT", "production"),
        release=app.config.get("APP_RELEASE") or None,
        traces_sample_rate=float(app.config.get("SENTRY_TRACES_SAMPLE_RATE", 0.0)),
        # Never ship PII (emails, phones, addresses) to the error tracker.
        send_default_pii=False,
    )
