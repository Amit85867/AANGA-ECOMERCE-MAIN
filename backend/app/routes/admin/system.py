"""Admin maintenance tools: system health, maintenance mode, audit log."""
import os
import time
from datetime import datetime, timedelta, timezone

from flask import current_app, jsonify, request
from marshmallow import Schema, ValidationError, fields, validate
from sqlalchemy import or_

from app.models.ops import AuditLog, JobRun
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required, master_required
from app.services import audit, health, maintenance
from app.utils.pagination import paginate, parse_day

_STARTED_AT = time.time()


class MaintenanceIn(Schema):
    enabled = fields.Bool(required=True)
    message = fields.Str(allow_none=True, validate=validate.Length(max=500))


_maintenance_in = MaintenanceIn()


# ── System health ─────────────────────────────────────────────

def _forwarded_hops():
    """How many proxies this request came through.

    Counted from the X-Forwarded-For header as it arrived (ProxyFix keeps the
    original). A browser sends none of its own, so for the admin looking at
    this page the number is the right value for TRUSTED_PROXY_COUNT.
    """
    original = request.environ.get("werkzeug.proxy_fix.orig") or {}
    header = original.get("HTTP_X_FORWARDED_FOR")
    if header is None:
        header = request.environ.get("HTTP_X_FORWARDED_FOR", "")
    return len([part for part in header.split(",") if part.strip()])


@admin_bp.route("/system/health", methods=["GET"])
@admin_required
def system_health():
    """Status of everything the store depends on.

    ``?probe=1`` also contacts the external services; without it they are
    reported from configuration alone.
    """
    probe = request.args.get("probe", "").lower() in ("1", "true", "yes")
    checks = health.run_all(probe=probe)

    last_run = (
        JobRun.query.filter_by(name="reconcile-payments")
        .order_by(JobRun.started_at.desc())
        .first()
    )
    reconcile = None
    if last_run:
        age_hours = (datetime.now(timezone.utc) - last_run.started_at).total_seconds() / 3600
        reconcile = {
            "ran_at": last_run.started_at.isoformat(),
            "ok": last_run.ok,
            "summary": last_run.summary,
            # Scheduled every 30 minutes; a gap this long means the cron job
            # is not running.
            "stale": age_hours > 6,
        }

    worst = "ok"
    for check in checks:
        if check["status"] == "error":
            worst = "error"

    return jsonify(
        status=worst,
        probed=probe,
        checked_at=datetime.now(timezone.utc).isoformat(),
        app={
            "version": current_app.config.get("APP_RELEASE") or "unversioned",
            "environment": os.environ.get("FLASK_ENV", "development"),
            "uptime_seconds": int(time.time() - _STARTED_AT),
            "debug": bool(current_app.config.get("DEBUG")),
            # The viewing admin's own address, as the server resolved it. If
            # this is not their real IP, TRUSTED_PROXY_COUNT is wrong and rate
            # limits are being applied to the proxy instead of to visitors.
            "client_ip": request.remote_addr,
            "proxy_hops_seen": _forwarded_hops(),
            "proxy_hops_trusted": int(current_app.config.get("TRUSTED_PROXY_COUNT", 0)),
        },
        checks=checks,
        maintenance=maintenance.get_state(fresh=True),
        reconcile_payments=reconcile,
    ), 200


# ── Maintenance mode ──────────────────────────────────────────

@admin_bp.route("/system/maintenance", methods=["GET"])
@admin_required
def get_maintenance():
    return jsonify(maintenance.get_state(fresh=True)), 200


@admin_bp.route("/system/maintenance", methods=["PUT"])
@master_required
def set_maintenance():
    """Closing the storefront stops every sale, so only a master admin may."""
    try:
        data = _maintenance_in.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    state = maintenance.set_state(data["enabled"], data.get("message"))
    audit.annotate(
        entity="settings",
        summary=(
            "Maintenance mode switched ON — storefront closed to customers"
            if state["enabled"] else "Maintenance mode switched OFF — storefront open"
        ),
    )
    return jsonify(state), 200


# ── Audit log ─────────────────────────────────────────────────

@admin_bp.route("/audit-log", methods=["GET"])
@admin_required
def list_audit_log():
    q = AuditLog.query

    entity_type = request.args.get("entity_type")
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)

    actor_type = request.args.get("actor_type")
    if actor_type:
        q = q.filter(AuditLog.actor_type == actor_type)

    search = (request.args.get("q") or "").strip()
    if search:
        like = f"%{search}%"
        q = q.filter(or_(
            AuditLog.summary.ilike(like),
            AuditLog.action.ilike(like),
            AuditLog.actor_label.ilike(like),
            AuditLog.entity_id == search,
        ))

    since, until = parse_day(request.args.get("from")), parse_day(request.args.get("to"))
    if since:
        q = q.filter(AuditLog.created_at >= since)
    if until:
        q = q.filter(AuditLog.created_at < until + timedelta(days=1))

    page = paginate(q.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()))

    return jsonify(
        entries=[
            {
                "id": e.id,
                "created_at": e.created_at.isoformat(),
                "actor_type": e.actor_type,
                "actor": e.actor_label or ("System" if e.actor_type == "system" else "Unknown"),
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "summary": e.summary,
                "changes": e.changes,
                "ip": e.ip,
            }
            for e in page.items
        ],
        entity_types=[
            row[0] for row in
            AuditLog.query.with_entities(AuditLog.entity_type).distinct()
            .order_by(AuditLog.entity_type)
        ],
        page=page.page, pages=page.pages, total=page.total,
    ), 200
