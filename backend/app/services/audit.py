"""Audit trail: who changed what.

Two ways in:

* **Automatic.** Every successful admin write (POST / PUT / PATCH / DELETE under
  /api/admin) is recorded by an ``after_request`` hook, so a new admin endpoint
  is audited without anyone remembering to add a call. A view can enrich its
  entry with ``annotate(summary=..., changes=..., entity=...)``.
* **Explicit.** ``record(...)`` for events that are not an admin request — a
  refund issued when a customer cancels, or by the reconcile sweep.

Writing the trail must never break the action it describes: failures are logged
and swallowed.
"""
from flask import current_app, g, has_request_context, request
from flask_jwt_extended import get_jwt

from app.extensions import db
from app.models.ops import AuditLog

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Not changes to the store: sign-in plumbing is logged as its own event below.
_SKIP_ENDPOINTS = {"admin.admin_refresh", "admin.admin_logout", "admin.admin_login"}

# Never copied into the trail, at any depth.
_SECRET_KEYS = ("password", "token", "secret", "authorization", "otp")

_MAX_VALUE_CHARS = 500


_NOTES_KEY = "aanga.audit"


def annotate(**notes):
    """Attach details to this request's audit entry.

    Recognised: ``summary``, ``changes``, ``entity`` (overrides the entity type
    taken from the URL), ``skip`` and ``by_admin``.

    Kept on the request rather than ``flask.g``: ``g`` belongs to the
    application context, which can outlive a single request (it does under the
    test client), and a note left behind would be stamped on the next entry.
    """
    request.environ.setdefault(_NOTES_KEY, {}).update(notes)


def notes():
    if not has_request_context():
        return {}
    return request.environ.get(_NOTES_KEY, {})


def _scrub(value, depth=0):
    """A copy of a request payload that is safe and small enough to store."""
    if depth > 4:
        return "…"
    if isinstance(value, dict):
        return {
            str(k): "[redacted]" if any(s in str(k).lower() for s in _SECRET_KEYS)
            else _scrub(v, depth + 1)
            for k, v in list(value.items())[:50]
        }
    if isinstance(value, list):
        return [_scrub(v, depth + 1) for v in value[:50]]
    if isinstance(value, str) and len(value) > _MAX_VALUE_CHARS:
        return value[:_MAX_VALUE_CHARS] + "…"
    return value


def _current_admin():
    """(admin_id, label) for the admin making this request, or (None, None)."""
    try:
        claims = get_jwt()
    except Exception:  # noqa: BLE001 - no verified token on this request
        return None, None
    if claims.get("actor") != "admin":
        return None, None
    from app.models.admin import Admin
    admin = db.session.get(Admin, claims["sub"])
    return claims["sub"], (admin.email if admin else None)


def record(action, entity_type, entity_id=None, summary=None, changes=None,
           actor_type=None, actor_label=None, commit=True):
    """Append one entry. Returns the row, or None if it could not be written."""
    in_request = has_request_context()
    admin_id, admin_label = _current_admin() if in_request else (None, None)

    entry = AuditLog(
        actor_type=actor_type or ("admin" if admin_id else "system"),
        admin_id=admin_id,
        actor_label=actor_label or admin_label,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        summary=summary,
        changes=_scrub(changes or {}),
        ip=request.remote_addr if in_request else None,
        request_id=getattr(g, "request_id", None) if in_request else None,
    )
    try:
        db.session.add(entry)
        if commit:
            db.session.commit()
        return entry
    except Exception:  # noqa: BLE001
        db.session.rollback()
        current_app.logger.exception("AUDIT_WRITE_FAILED action=%s", action)
        return None


def _entity_from_path(path):
    """/api/admin/orders/12/status -> ("orders", ...)."""
    parts = [p for p in path.split("/") if p][2:]   # drop "api", "admin"
    return parts[0] if parts else "unknown"


def init_app(app):
    @app.after_request
    def _audit_admin_writes(resp):
        if (
            request.method not in WRITE_METHODS
            or not request.path.startswith("/api/admin/")
            or not (200 <= resp.status_code < 300)
            or request.endpoint in _SKIP_ENDPOINTS
            or notes().get("skip")
        ):
            return resp

        view_args = request.view_args or {}
        entity_id = next(iter(view_args.values()), None)
        if entity_id is None and resp.is_json:
            body = resp.get_json(silent=True)
            if isinstance(body, dict):
                entity_id = body.get("id")

        noted = notes()
        changes = noted.get("changes")
        if changes is None:
            changes = request.get_json(silent=True) if request.is_json else {}

        record(
            action=(request.endpoint or "admin.unknown").split(".", 1)[-1],
            entity_type=noted.get("entity") or _entity_from_path(request.path),
            entity_id=entity_id,
            summary=noted.get("summary"),
            changes=changes if isinstance(changes, (dict, list)) else {},
        )
        return resp
