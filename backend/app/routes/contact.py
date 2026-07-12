"""Contact form submission."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from marshmallow import ValidationError

from app.extensions import db
from app.models.marketing import ContactMessage
from app.models.enums import ContactSubject
from app.schemas.marketing import ContactMessageIn

contact_bp = Blueprint("contact", __name__, url_prefix="/api/contact")

_msg_in = ContactMessageIn()


@contact_bp.route("", methods=["POST"])
def submit_contact():
    try:
        data = _msg_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    user_id = None
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
    except Exception:
        pass

    msg = ContactMessage(
        user_id=user_id,
        name=data["name"],
        email=data["email"],
        phone=data.get("phone"),
        subject=ContactSubject(data.get("subject", "general")),
        message=data["message"],
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify(message="Message sent successfully"), 201
