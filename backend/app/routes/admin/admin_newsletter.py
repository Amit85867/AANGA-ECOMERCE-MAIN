"""Admin newsletter subscriber management."""
from flask import request, jsonify

from app.extensions import db
from app.models.marketing import NewsletterSubscriber
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required


@admin_bp.route("/newsletter", methods=["GET"])
@admin_required
def admin_list_subscribers():
    page = request.args.get("page", 1, type=int)
    per_page = min(request.args.get("per_page", 50, type=int), 200)
    active_only = request.args.get("active", "true").lower() == "true"

    q = NewsletterSubscriber.query
    if active_only:
        q = q.filter_by(is_active=True)

    paginated = q.order_by(NewsletterSubscriber.subscribed_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    items = [
        {
            "id": s.id,
            "email": s.email,
            "is_active": s.is_active,
            "subscribed_at": s.subscribed_at.isoformat(),
            "unsubscribed_at": s.unsubscribed_at.isoformat() if s.unsubscribed_at else None,
        }
        for s in paginated.items
    ]

    return jsonify(
        subscribers=items,
        page=paginated.page,
        pages=paginated.pages,
        total=paginated.total,
    ), 200


@admin_bp.route("/newsletter/<int:sub_id>", methods=["DELETE"])
@admin_required
def admin_remove_subscriber(sub_id):
    sub = db.session.get(NewsletterSubscriber, sub_id)
    if not sub:
        return jsonify(error="Subscriber not found"), 404

    db.session.delete(sub)
    db.session.commit()

    return jsonify(message="Subscriber removed"), 200
