"""Newsletter subscribe / unsubscribe."""
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from marshmallow import ValidationError

from app.extensions import db
from app.models.marketing import NewsletterSubscriber
from app.schemas.marketing import NewsletterIn

newsletter_bp = Blueprint("newsletter", __name__, url_prefix="/api/newsletter")

_sub_in = NewsletterIn()


@newsletter_bp.route("/subscribe", methods=["POST"])
def subscribe():
    try:
        data = _sub_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    existing = NewsletterSubscriber.query.filter_by(email=data["email"]).first()
    if existing:
        if existing.is_active:
            return jsonify(message="Already subscribed"), 200
        existing.is_active = True
        existing.unsubscribed_at = None
        db.session.commit()
        return jsonify(message="Subscription reactivated"), 200

    sub = NewsletterSubscriber(email=data["email"])
    db.session.add(sub)
    db.session.commit()

    return jsonify(message="Subscribed successfully"), 201


@newsletter_bp.route("/unsubscribe", methods=["POST"])
def unsubscribe():
    try:
        data = _sub_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    sub = NewsletterSubscriber.query.filter_by(email=data["email"], is_active=True).first()
    if not sub:
        return jsonify(error="Email not found in subscribers"), 404

    sub.is_active = False
    sub.unsubscribed_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify(message="Unsubscribed successfully"), 200
