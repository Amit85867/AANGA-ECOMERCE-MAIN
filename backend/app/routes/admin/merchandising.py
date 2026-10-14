"""Admin: collections, campaigns and the media library."""
import os
import re
from datetime import timezone

from flask import current_app, jsonify, request
from flask_jwt_extended import get_jwt
from marshmallow import EXCLUDE, Schema, ValidationError, fields, validate
from sqlalchemy import or_

from app.extensions import db
from app.models.catalogue import Product
from app.models.cms import HeroBanner, PromoBanner
from app.models.engagement import Coupon
from app.models.owner import Campaign, Collection, CollectionProduct, MediaAsset
from app.routes.admin import admin_bp
from app.routes.admin.content import no_markup, valid_image, valid_link
from app.routes.admin.decorators import admin_required
from app.services import audit, campaigns, media
from app.services.catalogue import primary_images
from app.services.storage import InvalidImage, StorageError, save_image
from app.utils.pagination import page_meta, paginate


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:80]


# ══ Collections ══════════════════════════════════════════════

class CollectionIn(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.Str(required=True, validate=[validate.Length(min=2, max=80), no_markup])
    slug = fields.Str(allow_none=True, validate=validate.Regexp(r"^[a-z0-9]+(-[a-z0-9]+)*$", error="Lower-case letters, numbers and hyphens only."))
    description = fields.Str(allow_none=True, validate=[validate.Length(max=500), no_markup])
    image_url = fields.Str(allow_none=True, validate=valid_image)
    is_active = fields.Bool(load_default=True)
    meta_title = fields.Str(allow_none=True, validate=[validate.Length(max=70), no_markup])
    meta_description = fields.Str(allow_none=True, validate=[validate.Length(max=200), no_markup])
    share_image_url = fields.Str(allow_none=True, validate=valid_image)
    product_ids = fields.List(fields.Int(), load_default=None, validate=validate.Length(max=200))


_collection_in = CollectionIn()


def _collection_dict(c, with_products=False):
    data = {
        "id": c.id, "name": c.name, "slug": c.slug, "description": c.description,
        "image_url": c.image_url, "is_active": c.is_active, "is_demo": c.is_demo,
        "meta_title": c.meta_title, "meta_description": c.meta_description,
        "share_image_url": c.share_image_url, "product_count": len(c.items),
    }
    if with_products:
        ids = [i.product_id for i in c.items]
        images = primary_images(ids)
        products = {p.id: p for p in Product.query.filter(Product.id.in_(ids)).all()} if ids else {}
        data["products"] = [
            {"id": pid, "name": products[pid].name, "slug": products[pid].slug,
             "selling_price": float(products[pid].selling_price), "is_active": products[pid].is_active,
             "image_url": images.get(pid)}
            for pid in ids if pid in products
        ]
    return data


def _apply_collection(collection, data):
    for key in ("description", "image_url", "meta_title", "meta_description", "share_image_url"):
        if key in data:
            setattr(collection, key, (data[key] or "").strip() or None)
    collection.name = data["name"].strip()
    collection.is_active = data["is_active"]
    slug = data.get("slug") or slugify(collection.name)
    if not slug:
        return {"name": ["Use at least one letter or number."]}
    clash = Collection.query.filter(Collection.slug == slug, Collection.id != collection.id).first()
    if clash:
        return {"slug": [f"Another collection (\"{clash.name}\") already uses this web address."]}
    collection.slug = slug

    if data.get("product_ids") is not None:
        wanted = list(dict.fromkeys(data["product_ids"]))            # keep order, drop repeats
        found = {p.id for p in Product.query.filter(Product.id.in_(wanted)).all()} if wanted else set()
        missing = [pid for pid in wanted if pid not in found]
        if missing:
            return {"product_ids": [f"Product {missing[0]} no longer exists."]}
        collection.items = [
            CollectionProduct(product_id=pid, sort_order=position) for position, pid in enumerate(wanted)
        ]
    return None


@admin_bp.route("/collections", methods=["GET"])
@admin_required
def list_collections():
    rows = Collection.query.order_by(Collection.name).all()
    return jsonify(collections=[_collection_dict(c) for c in rows]), 200


@admin_bp.route("/collections/<int:collection_id>", methods=["GET"])
@admin_required
def get_collection(collection_id):
    collection = db.session.get(Collection, collection_id)
    if collection is None:
        return jsonify(error="Collection not found"), 404
    return jsonify(_collection_dict(collection, with_products=True)), 200


@admin_bp.route("/collections", methods=["POST"])
@admin_required
def create_collection():
    try:
        data = _collection_in.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(errors=err.messages), 422
    collection = Collection()
    errors = _apply_collection(collection, data)
    if errors:
        db.session.rollback()
        return jsonify(errors=errors), 422
    db.session.add(collection)
    db.session.flush()
    audit.annotate(entity="collections", summary=f"Collection \"{collection.name}\" created with {len(collection.items)} products")
    db.session.commit()
    return jsonify(_collection_dict(collection, with_products=True)), 201


@admin_bp.route("/collections/<int:collection_id>", methods=["PUT"])
@admin_required
def update_collection(collection_id):
    collection = db.session.get(Collection, collection_id)
    if collection is None:
        return jsonify(error="Collection not found"), 404
    try:
        data = _collection_in.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(errors=err.messages), 422
    errors = _apply_collection(collection, data)
    if errors:
        db.session.rollback()
        return jsonify(errors=errors), 422
    db.session.flush()
    audit.annotate(entity="collections", summary=f"Collection \"{collection.name}\" saved ({len(collection.items)} products)")
    db.session.commit()
    return jsonify(_collection_dict(collection, with_products=True)), 200


@admin_bp.route("/collections/<int:collection_id>", methods=["DELETE"])
@admin_required
def delete_collection(collection_id):
    collection = db.session.get(Collection, collection_id)
    if collection is None:
        return jsonify(error="Collection not found"), 404
    in_use = [
        c.name for c in Campaign.query.filter_by(collection_id=collection.id).all()
        if campaigns.status_of(c) != "ended"
    ]
    if in_use:
        return jsonify(error=f"The campaign \"{in_use[0]}\" uses this collection. Change or end the campaign first."), 409
    audit.annotate(entity="collections", summary=f"Collection \"{collection.name}\" deleted")
    db.session.delete(collection)
    db.session.commit()
    return jsonify(message="Collection deleted"), 200


# ══ Campaigns ════════════════════════════════════════════════

class CampaignIn(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.Str(required=True, validate=[validate.Length(min=2, max=80), no_markup])
    # With an offset: the admin app always sends Indian time ("+05:30").
    starts_at = fields.AwareDateTime(required=True, format="iso")
    ends_at = fields.AwareDateTime(required=True, format="iso")
    announcement_text = fields.Str(allow_none=True, validate=[validate.Length(max=140), no_markup])
    announcement_highlight = fields.Str(allow_none=True, validate=[validate.Length(max=140), no_markup])
    announcement_link_url = fields.Str(allow_none=True, validate=validate.Length(max=300))
    announcement_link_text = fields.Str(allow_none=True, validate=[validate.Length(max=40), no_markup])
    collection_id = fields.Int(allow_none=True)
    sale_percent = fields.Float(allow_none=True, validate=validate.Range(min=1, max=90))
    decoration_enabled = fields.Bool(load_default=False)
    accent_preset = fields.Str(load_default="marigold", validate=validate.OneOf(list(campaigns.ACCENT_PRESETS)))
    show_countdown = fields.Bool(load_default=False)
    coupon_ids = fields.List(fields.Int(), load_default=None, validate=validate.Length(max=20))


_campaign_in = CampaignIn()


def _slide_dict(b):
    return {"id": b.id, "title": b.title, "subtitle": b.subtitle, "image_url": b.image_url,
            "link_url": b.link_url, "link_text": b.link_text, "is_active": b.is_active, "sort_order": b.sort_order}


def _campaign_dict(c, detail=False):
    data = {
        "id": c.id, "name": c.name, "status": campaigns.status_of(c),
        "starts_at": c.starts_at.astimezone(timezone.utc).isoformat(),
        "ends_at": c.ends_at.astimezone(timezone.utc).isoformat(),
        "ended_at": c.ended_at.astimezone(timezone.utc).isoformat() if c.ended_at else None,
        "announcement_text": c.announcement_text, "announcement_highlight": c.announcement_highlight,
        "announcement_link_url": c.announcement_link_url, "announcement_link_text": c.announcement_link_text,
        "collection_id": c.collection_id,
        "collection_name": c.collection.name if c.collection else None,
        "collection_slug": c.collection.slug if c.collection else None,
        "sale_percent": float(c.sale_percent) if c.sale_percent else None,
        "decoration_enabled": c.decoration_enabled, "accent_preset": c.accent_preset,
        "show_countdown": c.show_countdown, "is_demo": c.is_demo,
    }
    if detail:
        data["slides"] = [_slide_dict(b) for b in HeroBanner.query.filter_by(campaign_id=c.id).order_by(HeroBanner.sort_order, HeroBanner.id)]
        data["promo_banners"] = [
            {"id": p.id, "title": p.title, "subtitle": p.subtitle, "image_url": p.image_url, "is_active": p.is_active}
            for p in PromoBanner.query.filter_by(campaign_id=c.id).order_by(PromoBanner.sort_order, PromoBanner.id)
        ]
        data["coupons"] = [
            {"id": k.id, "code": k.code, "description": k.description, "used_count": k.used_count,
             "usage_limit": k.usage_limit, "is_active": k.is_active}
            for k in Coupon.query.filter_by(campaign_id=c.id).order_by(Coupon.code)
        ]
    return data


def _apply_campaign(campaign, data):
    """Copy validated input onto the row. Returns ``(errors, status_code)`` or None."""
    starts, ends = data["starts_at"], data["ends_at"]
    if ends <= starts:
        return {"ends_at": ["The end must be after the start."]}, 422
    if ends <= campaigns.now_utc():
        return {"ends_at": ["The end is already in the past."]}, 422

    clash = campaigns.find_overlap(starts, ends, exclude_id=campaign.id)
    if clash is not None:
        return {"starts_at": [
            f"These dates overlap \"{clash.name}\". Only one campaign can run at a time — "
            "change the dates, or end the other campaign first."
        ]}, 409

    link = (data.get("announcement_link_url") or "").strip()
    if link:
        try:
            valid_link(link)
        except ValidationError as err:
            return {"announcement_link_url": err.messages}, 422

    collection_id = data.get("collection_id")
    if collection_id is not None and db.session.get(Collection, collection_id) is None:
        return {"collection_id": ["That collection no longer exists."]}, 422
    if data.get("sale_percent") and collection_id is None:
        return {"sale_percent": ["Choose the collection the sale applies to."]}, 422

    campaign.name = data["name"].strip()
    campaign.starts_at, campaign.ends_at = starts, ends
    campaign.ended_at = None                      # saving new dates re-opens an ended campaign
    for key in ("announcement_text", "announcement_highlight", "announcement_link_text"):
        setattr(campaign, key, (data.get(key) or "").strip() or None)
    campaign.announcement_link_url = link or None
    campaign.collection_id = collection_id
    campaign.sale_percent = data.get("sale_percent") or None
    campaign.decoration_enabled = data["decoration_enabled"]
    campaign.accent_preset = data["accent_preset"]
    campaign.show_countdown = data["show_countdown"]
    db.session.flush()

    if data.get("coupon_ids") is not None:
        wanted = set(data["coupon_ids"])
        found = Coupon.query.filter(Coupon.id.in_(wanted)).all() if wanted else []
        if len(found) != len(wanted):
            return {"coupon_ids": ["One of those coupons no longer exists."]}, 422
        taken = [k.code for k in found if k.campaign_id not in (None, campaign.id)]
        if taken:
            return {"coupon_ids": [f"{taken[0]} already belongs to another campaign."]}, 409
        for coupon in Coupon.query.filter_by(campaign_id=campaign.id).all():
            if coupon.id not in wanted:
                coupon.campaign_id = None
        for coupon in found:
            coupon.campaign_id = campaign.id
    # A campaign's coupons stop with it.
    db.session.flush()
    for coupon in Coupon.query.filter_by(campaign_id=campaign.id).all():
        coupon.expires_at = ends
    return None


def _presets():
    return [{"value": key, **preset} for key, preset in campaigns.ACCENT_PRESETS.items()]


@admin_bp.route("/campaigns", methods=["GET"])
@admin_required
def list_campaigns():
    rows = Campaign.query.order_by(Campaign.starts_at.desc()).all()
    return jsonify(campaigns=[_campaign_dict(c) for c in rows], presets=_presets()), 200


@admin_bp.route("/campaigns/<int:campaign_id>", methods=["GET"])
@admin_required
def get_campaign(campaign_id):
    campaign = db.session.get(Campaign, campaign_id)
    if campaign is None:
        return jsonify(error="Campaign not found"), 404
    return jsonify(_campaign_dict(campaign, detail=True)), 200


@admin_bp.route("/campaigns", methods=["POST"])
@admin_required
def create_campaign():
    try:
        data = _campaign_in.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(errors=err.messages), 422
    campaign = Campaign()
    db.session.add(campaign)
    with db.session.no_autoflush:
        failure = _apply_campaign(campaign, data)
    if failure:
        db.session.rollback()
        return jsonify(errors=failure[0]), failure[1]
    audit.annotate(entity="campaigns", summary=f"Campaign \"{campaign.name}\" scheduled",
                   changes={"starts_at": data["starts_at"].isoformat(), "ends_at": data["ends_at"].isoformat()})
    db.session.commit()
    return jsonify(_campaign_dict(campaign, detail=True)), 201


@admin_bp.route("/campaigns/<int:campaign_id>", methods=["PUT"])
@admin_required
def update_campaign(campaign_id):
    campaign = db.session.get(Campaign, campaign_id)
    if campaign is None:
        return jsonify(error="Campaign not found"), 404
    try:
        data = _campaign_in.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(errors=err.messages), 422
    with db.session.no_autoflush:
        failure = _apply_campaign(campaign, data)
    if failure:
        db.session.rollback()
        return jsonify(errors=failure[0]), failure[1]
    audit.annotate(entity="campaigns", summary=f"Campaign \"{campaign.name}\" saved",
                   changes={"starts_at": data["starts_at"].isoformat(), "ends_at": data["ends_at"].isoformat()})
    db.session.commit()
    return jsonify(_campaign_dict(campaign, detail=True)), 200


@admin_bp.route("/campaigns/<int:campaign_id>/end", methods=["POST"])
@admin_required
def end_campaign(campaign_id):
    """"End now": the storefront goes back to normal on the next request."""
    campaign = db.session.get(Campaign, campaign_id)
    if campaign is None:
        return jsonify(error="Campaign not found"), 404
    if campaigns.status_of(campaign) != "live":
        return jsonify(error="Only a campaign that is live can be ended."), 409
    now = campaigns.now_utc()
    campaign.ended_at = now
    for coupon in Coupon.query.filter_by(campaign_id=campaign.id).all():
        coupon.expires_at = now
    audit.annotate(entity="campaigns", summary=f"Campaign \"{campaign.name}\" ended early")
    db.session.commit()
    return jsonify(_campaign_dict(campaign, detail=True)), 200


@admin_bp.route("/campaigns/<int:campaign_id>/preview", methods=["POST"])
@admin_required
def preview_campaign(campaign_id):
    """A link that shows the storefront as it will look during the campaign."""
    campaign = db.session.get(Campaign, campaign_id)
    if campaign is None:
        return jsonify(error="Campaign not found"), 404
    token = campaigns.make_preview_token(campaign.id)
    audit.annotate(skip=True)
    return jsonify(token=token, path=f"/?campaign_preview={token}",
                   expires_in_minutes=campaigns.PREVIEW_MAX_AGE // 60), 200


@admin_bp.route("/campaigns/<int:campaign_id>", methods=["DELETE"])
@admin_required
def delete_campaign(campaign_id):
    campaign = db.session.get(Campaign, campaign_id)
    if campaign is None:
        return jsonify(error="Campaign not found"), 404
    if campaigns.status_of(campaign) == "live":
        return jsonify(error="This campaign is live. End it first, then delete it."), 409
    for coupon in Coupon.query.filter_by(campaign_id=campaign.id).all():
        coupon.is_active = False            # the coupon row stays for past orders
    audit.annotate(entity="campaigns", summary=f"Campaign \"{campaign.name}\" deleted")
    db.session.delete(campaign)
    db.session.commit()
    return jsonify(message="Campaign deleted"), 200


# ══ Media library ════════════════════════════════════════════

ALLOWED = {"png", "jpg", "jpeg", "webp", "gif"}
MAX_SIZE = 5 * 1024 * 1024


def _asset_dict(asset, used=None):
    data = {
        "id": asset.id, "url": asset.url, "filename": asset.filename, "alt_text": asset.alt_text,
        "width": asset.width, "height": asset.height, "size_bytes": asset.size_bytes,
        "source_note": asset.source_note, "is_demo": asset.is_demo,
        "created_at": asset.created_at.isoformat() if asset.created_at else None,
    }
    if used is not None:
        data["used_count"] = used
    return data


def store_upload(file_storage, alt_text=None, source_note=None):
    """Validate, store and catalogue one uploaded image.

    Returns ``(asset, None)`` or ``(None, (message, status))``. Shared with the
    older /upload route so every image lands in the library.
    """
    if not file_storage or not file_storage.filename:
        return None, ("Choose an image to upload.", 400)
    name = file_storage.filename
    if "." not in name or name.rsplit(".", 1)[1].lower() not in ALLOWED:
        return None, (f"Allowed types: {', '.join(sorted(ALLOWED))}", 400)
    file_storage.seek(0, os.SEEK_END)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > MAX_SIZE:
        return None, ("File too large (max 5 MB)", 400)
    try:
        url = save_image(file_storage)
    except InvalidImage as exc:
        return None, (str(exc), 400)
    except StorageError as exc:
        current_app.logger.error("Image upload failed: %s", exc)
        return None, ("Could not store the image. Please try again.", 502)
    asset = media.record(url, file_storage, uploaded_by=get_jwt()["sub"], alt_text=alt_text, source_note=source_note)
    db.session.commit()
    return asset, None


@admin_bp.route("/media", methods=["GET"])
@admin_required
def list_media():
    query = MediaAsset.query
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{term}%"
        query = query.filter(or_(MediaAsset.filename.ilike(like), MediaAsset.alt_text.ilike(like),
                                 MediaAsset.source_note.ilike(like)))
    if request.args.get("demo") == "true":
        query = query.filter(MediaAsset.is_demo.is_(True))
    page = paginate(query.order_by(MediaAsset.created_at.desc(), MediaAsset.id.desc()), default=24)
    counts = media.usage_counts([a.url for a in page.items])
    return jsonify(assets=[_asset_dict(a, counts.get(a.url, 0)) for a in page.items], **page_meta(page)), 200


@admin_bp.route("/media", methods=["POST"])
@admin_required
def upload_media():
    if "file" not in request.files:
        return jsonify(error="No file provided"), 400
    asset, failure = store_upload(
        request.files["file"],
        alt_text=(request.form.get("alt_text") or "").strip()[:200],
        source_note=(request.form.get("source_note") or "").strip()[:500],
    )
    if failure:
        return jsonify(error=failure[0]), failure[1]
    return jsonify(_asset_dict(asset, 0)), 201


@admin_bp.route("/media/<int:asset_id>", methods=["PATCH"])
@admin_required
def update_media(asset_id):
    asset = db.session.get(MediaAsset, asset_id)
    if asset is None:
        return jsonify(error="Image not found"), 404
    body = request.get_json(silent=True) or {}
    for key, limit in (("alt_text", 200), ("source_note", 500)):
        if key in body:
            value = str(body[key] or "").strip()
            if "<" in value or ">" in value:
                return jsonify(errors={key: ["Plain text only."]}), 422
            setattr(asset, key, value[:limit] or None)
    db.session.commit()
    return jsonify(_asset_dict(asset)), 200


@admin_bp.route("/media/<int:asset_id>/usage", methods=["GET"])
@admin_required
def media_usage(asset_id):
    asset = db.session.get(MediaAsset, asset_id)
    if asset is None:
        return jsonify(error="Image not found"), 404
    return jsonify(usage=media.usage(asset.url)), 200


@admin_bp.route("/media/<int:asset_id>", methods=["DELETE"])
@admin_required
def delete_media(asset_id):
    asset = db.session.get(MediaAsset, asset_id)
    if asset is None:
        return jsonify(error="Image not found"), 404
    used = media.usage(asset.url)
    if used:
        return jsonify(
            error=f"This image is used in {len(used)} place{'s' if len(used) != 1 else ''}. "
                  "Replace it there first, then delete it.",
            usage=used,
        ), 409
    audit.annotate(entity="media", summary=f"Image {asset.filename or asset.url} deleted")
    media.delete_files(asset.url)
    db.session.delete(asset)
    db.session.commit()
    return jsonify(message="Image deleted"), 200
