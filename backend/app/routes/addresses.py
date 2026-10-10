"""User addresses: list, add, update, delete, set default.

An order reads its delivery address through orders.address_id, so a row an
order points at is history: it is archived rather than deleted, and an edit
writes a new row rather than changing where a past order was delivered.
"""
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError

from app.extensions import db
from app.models.order import Order
from app.models.user import Address
from app.schemas.user import AddressIn, AddressOut

addresses_bp = Blueprint("addresses", __name__, url_prefix="/api/addresses")

_addr_in = AddressIn()
_addr_out = AddressOut()
_addr_list_out = AddressOut(many=True)


def _own(user_id):
    """The caller's address book: their rows, minus the archived ones."""
    return Address.query.filter_by(user_id=user_id, archived_at=None)


def _used_by_an_order(addr):
    return db.session.query(Order.id).filter_by(address_id=addr.id).first() is not None


def _archive(addr):
    addr.archived_at = datetime.now(timezone.utc)
    addr.is_default = False


def _ensure_a_default(user_id):
    """Checkout preselects the default, so an address book is never left without one."""
    db.session.flush()
    remaining = _own(user_id).order_by(Address.created_at.desc()).all()
    if remaining and not any(a.is_default for a in remaining):
        remaining[0].is_default = True


@addresses_bp.route("", methods=["GET"])
@jwt_required()
def list_addresses():
    addrs = (
        _own(get_jwt_identity())
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
    first = _own(user_id).count() == 0
    make_default = first or data.pop("is_default", False)
    data.pop("is_default", None)

    if make_default:
        _own(user_id).update({"is_default": False})

    addr = Address(user_id=user_id, is_default=make_default, **data)
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

    user_id = get_jwt_identity()
    addr = _own(user_id).filter_by(id=addr_id).first()
    if not addr:
        return jsonify(error="Address not found"), 404

    make_default = data.pop("is_default", False) or addr.is_default

    if _used_by_an_order(addr):
        # Keep the old row for the orders shipped to it; the edit is a new one.
        _archive(addr)
        addr = Address(user_id=user_id, **data)
        db.session.add(addr)
    else:
        for key, val in data.items():
            setattr(addr, key, val)

    if make_default:
        _own(user_id).update({"is_default": False})
    addr.is_default = make_default

    _ensure_a_default(user_id)
    db.session.commit()
    return jsonify(_addr_out.dump(addr)), 200


@addresses_bp.route("/<int:addr_id>", methods=["DELETE"])
@jwt_required()
def delete_address(addr_id):
    user_id = get_jwt_identity()
    addr = _own(user_id).filter_by(id=addr_id).first()
    if not addr:
        return jsonify(error="Address not found"), 404

    if _used_by_an_order(addr):
        _archive(addr)
    else:
        db.session.delete(addr)

    _ensure_a_default(user_id)
    db.session.commit()
    return jsonify(message="Address deleted"), 200


@addresses_bp.route("/<int:addr_id>/default", methods=["PATCH"])
@jwt_required()
def set_default(addr_id):
    user_id = get_jwt_identity()
    addr = _own(user_id).filter_by(id=addr_id).first()
    if not addr:
        return jsonify(error="Address not found"), 404

    _own(user_id).update({"is_default": False})
    addr.is_default = True
    db.session.commit()

    return jsonify(_addr_out.dump(addr)), 200
