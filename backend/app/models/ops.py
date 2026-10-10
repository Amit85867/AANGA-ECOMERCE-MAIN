"""Operational bookkeeping: webhook de-duplication and scheduled-job history."""
from sqlalchemy.dialects.postgresql import JSONB
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
