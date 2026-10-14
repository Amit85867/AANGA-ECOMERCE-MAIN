"""Public content the owner edits: layout, menus, pages, FAQ, collections,
and the campaign that is live right now."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify

from app.models.owner import CmsPage, Collection, FaqItem
from app.services import campaigns, content, store_settings
from app.services.cache import cached_view

content_bp = Blueprint("content", __name__, url_prefix="/api/content")


def public_campaign(snapshot):
    """The live campaign as the storefront needs it (no product id list)."""
    if snapshot is None:
        return None
    return {
        "id": snapshot["id"],
        "name": snapshot["name"],
        "starts_at": snapshot["starts_at"],
        "ends_at": snapshot["ends_at"],
        "collection": snapshot["collection"],
        "sale_percent": snapshot["sale_percent"],
        "decoration": snapshot["decoration"],
        "show_countdown": snapshot["show_countdown"],
        "preview": bool(snapshot.get("preview")),
    }


@content_bp.route("/layout", methods=["GET"])
@cached_view(30)
def layout():
    """Everything the storefront shell needs in one request: homepage section
    order, both menus, store settings and the live campaign."""
    sections = []
    for section in content.homepage_sections():
        if not section["is_visible"]:
            continue
        item = {"key": section["key"], "title": section["title"], "subtitle": section["subtitle"]}
        if section["key"] == "featured":
            collection_id = section["config"].get("collection_id")
            collection = Collection.query.filter_by(id=collection_id, is_active=True).first() if collection_id else None
            item["collection"] = {"slug": collection.slug, "name": collection.name} if collection else None
        sections.append(item)

    return jsonify(
        homepage=sections,
        navigation=content.navigation(),
        settings=store_settings.all_values(),
        campaign=public_campaign(campaigns.live()),
        # When the storefront should ask again without being told: a campaign
        # starting or ending.
        next_change_at=campaigns.next_change_at(),
        server_time=datetime.now(timezone.utc).isoformat(),
    ), 200


@content_bp.route("/pages/<slug>", methods=["GET"])
@cached_view(60)
def page(slug):
    if slug not in content.PAGE_SLUGS:
        return jsonify(error="Page not found"), 404
    return jsonify(content.page_dict(CmsPage.query.filter_by(slug=slug).first(), slug)), 200


@content_bp.route("/faq", methods=["GET"])
@cached_view(60)
def faq():
    items = FaqItem.query.filter_by(is_active=True).order_by(FaqItem.sort_order, FaqItem.id).all()
    return jsonify(
        items=[{"id": i.id, "question": i.question, "answer": i.answer} for i in items],
        page=content.page_dict(CmsPage.query.filter_by(slug="faq").first(), "faq"),
    ), 200


@content_bp.route("/collections/<slug>", methods=["GET"])
@cached_view(60)
def collection(slug):
    row = Collection.query.filter_by(slug=slug, is_active=True).first()
    if row is None:
        return jsonify(error="Collection not found"), 404
    live = campaigns.live()
    on_sale = bool(live and live.get("sale_percent") and live["collection"] and live["collection"]["id"] == row.id)
    return jsonify(
        id=row.id, name=row.name, slug=row.slug, description=row.description, image_url=row.image_url,
        meta_title=row.meta_title, meta_description=row.meta_description,
        share_image_url=row.share_image_url, product_count=len(row.items),
        sale_percent=live["sale_percent"] if on_sale else None,
    ), 200
