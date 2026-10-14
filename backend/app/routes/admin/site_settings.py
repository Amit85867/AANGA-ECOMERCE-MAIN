"""Admin site settings management."""
from flask import request, jsonify
from marshmallow import ValidationError

from app.extensions import db
from app.models.cms import SiteSetting
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.schemas.admin import AdminSiteSettingBulkIn
from app.services import maintenance

_bulk_in = AdminSiteSettingBulkIn()

_RESERVED_KEYS = (maintenance.FLAG_KEY, maintenance.MESSAGE_KEY)


def _serialize_setting(s):
    return {
        "id": s.id,
        "key": s.key,
        "value": s.value,
        "label": s.label,
        "group_name": s.group_name,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@admin_bp.route("/site-settings", methods=["GET"])
@admin_required
def admin_list_settings():
    return jsonify(settings=[_serialize_setting(s) for s in _editable_settings()]), 200


def _editable_settings():
    """Everything except the maintenance switch.

    That one closes the whole storefront and belongs to master admins on the
    System page. Left in this form, any admin saving an unrelated setting would
    write back whatever value their page had loaded — reopening (or closing) the
    store by accident.
    """
    # ...and the store's own fields, which have their own screen with proper
    # validation (Store settings).
    from app.services import store_settings
    hidden = list(_RESERVED_KEYS) + list(store_settings.BY_KEY)
    return (
        SiteSetting.query
        .filter(SiteSetting.key.notin_(hidden))
        .order_by(SiteSetting.group_name, SiteSetting.key)
        .all()
    )


@admin_bp.route("/site-settings", methods=["PUT"])
@admin_required
def update_settings_bulk():
    try:
        data = _bulk_in.load(request.get_json())
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    from app.services import store_settings
    if any(item["key"] in store_settings.BY_KEY for item in data["settings"]):
        return jsonify(error="That setting is changed on the Store settings page."), 422

    reserved = [item["key"] for item in data["settings"] if item["key"] in _RESERVED_KEYS]
    if reserved:
        return jsonify(
            error="Maintenance mode is changed on the System page, not here."
        ), 422

    for item in data["settings"]:
        setting = SiteSetting.query.filter_by(key=item["key"]).first()
        if setting:
            setting.value = item["value"]
            if item.get("label"):
                setting.label = item["label"]
            if item.get("group_name"):
                setting.group_name = item["group_name"]
        else:
            setting = SiteSetting(
                key=item["key"],
                value=item["value"],
                label=item.get("label"),
                group_name=item.get("group_name", "general"),
            )
            db.session.add(setting)

    db.session.commit()
    return jsonify(settings=[_serialize_setting(s) for s in _editable_settings()]), 200


@admin_bp.route("/site-settings/<int:setting_id>", methods=["DELETE"])
@admin_required
def delete_setting(setting_id):
    setting = db.session.get(SiteSetting, setting_id)
    if not setting or setting.key in _RESERVED_KEYS:
        return jsonify(error="Setting not found"), 404

    db.session.delete(setting)
    db.session.commit()
    return jsonify(message="Setting deleted"), 200
