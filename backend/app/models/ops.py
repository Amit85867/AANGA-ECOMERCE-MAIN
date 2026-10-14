"""Operational bookkeeping: webhook de-duplication and scheduled-job history."""
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.extensions import db


class WebhookEvent(db.Model):
    """One row per webhook delivery we have acted on.

    Providers retry deliveries, so the same event can arrive several times; the
    primary key on the provider's event id is what makes handling it idempotent.
    """
    __tablename__ = "webhook_events"

    event_id = db.Column(db.Text, primary_key=True)
    source = db.Column(db.Text, nullable=False)
    kind = db.Column(db.Text)
    received_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class JobRun(db.Model):
    """History of scheduled jobs (e.g. reconcile-payments), newest read by the
    admin System Health panel to show when a job last ran and what it did."""
    __tablename__ = "job_runs"

    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    started_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at = db.Column(db.DateTime(timezone=True))
    ok = db.Column(db.Boolean, nullable=False, default=True)
    summary = db.Column(JSONB, nullable=False, default=dict)


class AuditLog(db.Model):
    """Who changed what. See app/services/audit.py for how rows are written."""
    __tablename__ = "audit_log"

    id = db.Column(db.BigInteger, primary_key=True)
    # "admin", "customer", "system" (scheduled jobs, webhooks) or
    # "anonymous" (a failed admin sign-in: nobody proved who they were).
    actor_type = db.Column(db.Text, nullable=False, default="admin")
    admin_id = db.Column(UUID(as_uuid=True))
    # Copied onto the row so the trail outlives the account it names.
    actor_label = db.Column(db.Text)
    action = db.Column(db.Text, nullable=False)
    entity_type = db.Column(db.Text, nullable=False)
    entity_id = db.Column(db.Text)
    summary = db.Column(db.Text)
    changes = db.Column(JSONB, nullable=False, default=dict)
    ip = db.Column(db.Text)
    request_id = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=func.now()
    )
