"""Active offers listing."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify

from app.models.marketing import Offer
from app.schemas.marketing import OfferOut
from app.services.cache import cached_view

offers_bp = Blueprint("offers", __name__, url_prefix="/api/offers")

_offer_out = OfferOut(many=True)


@offers_bp.route("", methods=["GET"])
@cached_view(60)
def list_offers():
    now = datetime.now(timezone.utc)
    offers = (
        Offer.query
        .filter(
            Offer.is_active.is_(True),
            (Offer.starts_at.is_(None)) | (Offer.starts_at <= now),
            (Offer.ends_at.is_(None)) | (Offer.ends_at >= now),
        )
        .order_by(Offer.created_at.desc())
        .all()
    )
    return jsonify(offers=_offer_out.dump(offers)), 200
