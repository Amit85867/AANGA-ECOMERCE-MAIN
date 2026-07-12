"""User addresses: list, add, update, delete, set default."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.extensions import db
from app.models.user import Address
from app.schemas.user import AddressIn, AddressOut

addresses_bp = Blueprint("addresses", __name__, url_prefix="/api/addresses")

_addr_in = AddressIn()
_addr_out = AddressOut()
_addr_list_out = AddressOut(many=True)


@addresses_bp.route("", methods=["GET"])
@jwt_required()
def list_addresses():
    addrs = (
        Address.query
        .filter_by(user_id=get_jwt_identity())
        .order_by(Address.is_default.desc(), Address.created_at.desc())
        .all()
    )
    return jsonify(addresses=_addr_list_out.dump(addrs)), 200


@addresses_bp.route("", methods=["POST"])
@jwt_required()
def add_address():
    try:
        data = _addr_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    user_id = get_jwt_identity()

    if data.get("is_default"):
        Address.query.filter_by(user_id=user_id, is_default=True).update({"is_default": False})

    first = Address.query.filter_by(user_id=user_id).count() == 0

    addr = Address(user_id=user_id, is_default=first or data.get("is_default", False), **{
        k: v for k, v in data.items() if k != "is_default"
    })
    db.session.add(addr)
    db.session.commit()

    return jsonify(_addr_out.dump(addr)), 201


@addresses_bp.route("/<int:addr_id>", methods=["PUT"])
@jwt_required()
def update_address(addr_id):
    try:
        data = _addr_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    addr = Address.query.filter_by(id=addr_id, user_id=get_jwt_identity()).first()
    if not addr:
        return jsonify(error="Address not found"), 404

    for key, val in data.items():
        setattr(addr, key, val)

    if data.get("is_default"):
        Address.query.filter(
            Address.user_id == get_jwt_identity(),
            Address.id != addr.id,
        ).update({"is_default": False})

    db.session.commit()
    return jsonify(_addr_out.dump(addr)), 200


@addresses_bp.route("/<int:addr_id>", methods=["DELETE"])
@jwt_required()
def delete_address(addr_id):
    addr = Address.query.filter_by(id=addr_id, user_id=get_jwt_identity()).first()
    if not addr:
        return jsonify(error="Address not found"), 404

    db.session.delete(addr)
    db.session.commit()
    return jsonify(message="Address deleted"), 200


@addresses_bp.route("/<int:addr_id>/default", methods=["PATCH"])
@jwt_required()
def set_default(addr_id):
    user_id = get_jwt_identity()
    addr = Address.query.filter_by(id=addr_id, user_id=user_id).first()
    if not addr:
        return jsonify(error="Address not found"), 404

    Address.query.filter_by(user_id=user_id, is_default=True).update({"is_default": False})
    addr.is_default = True
    db.session.commit()

    return jsonify(_addr_out.dump(addr)), 200
