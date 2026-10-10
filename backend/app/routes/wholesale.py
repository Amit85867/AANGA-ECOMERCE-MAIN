"""Wholesale inquiry submission."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from marshmallow import ValidationError

from app.extensions import db, limiter
from app.models.marketing import WholesaleInquiry
from app.models.enums import VolumeRange
from app.schemas.marketing import WholesaleInquiryIn

wholesale_bp = Blueprint("wholesale", __name__, url_prefix="/api/wholesale")

_inquiry_in = WholesaleInquiryIn()


@wholesale_bp.route("", methods=["POST"])
@limiter.limit("10 per hour")
def submit_inquiry():
    try:
        data = _inquiry_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    user_id = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
    except Exception:
        pass

    inquiry = WholesaleInquiry(
        user_id=user_id,
        shop_name=data["shop_name"],
        owner_name=data["owner_name"],
        phone=data["phone"],
        email=data["email"],
        city=data["city"],
        state=data["state"],
        gst_number=data.get("gst_number"),
        categories_interest=data.get("categories_interest", []),
        monthly_volume_range=VolumeRange(data["monthly_volume_range"]),
    )
    db.session.add(inquiry)
    db.session.commit()

    return jsonify(message="Inquiry submitted successfully"), 201
