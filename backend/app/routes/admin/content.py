"""Admin: homepage builder, navigation, pages and FAQ."""
import re

from flask import jsonify, request
from marshmallow import EXCLUDE, Schema, ValidationError, fields, validate

from app.extensions import db
from app.models.owner import CmsPage, Collection, FaqItem, NavLink
from app.routes.admin import admin_bp
from app.routes.admin.decorators import admin_required
from app.services import audit, content
from app.services.sanitize import clean_html

# A link on this site ("/shop?category=men") or a full web address. Anything
# else — javascript:, data:, a bare word — is refused.
_LINK_RE = re.compile(r"^(/(?!/)[^\s<>\"']*|https?://[^\s<>\"']+|mailto:[^\s<>\"']+|tel:[+0-9 \-]+)$", re.I)
_IMAGE_RE = re.compile(r"^(https?://|/static/uploads/)[^\s<>\"']+$", re.I)


def valid_link(value):
    if not _LINK_RE.match(value or ""):
        raise ValidationError("Use a page on this site (starting with /) or a full https:// link.")


def valid_image(value):
    if value and not _IMAGE_RE.match(value):
        raise ValidationError("Choose an image from the media library.")


def no_markup(value):
    if value and ("<" in value or ">" in value):
        raise ValidationError("Plain text only.")


# ── Homepage builder ─────────────────────────────────────────

class HomeSectionIn(Schema):
    class Meta:
        unknown = EXCLUDE

    key = fields.Str(required=True, validate=validate.OneOf(content.HOME_KEYS))
    title = fields.Str(allow_none=True, validate=[validate.Length(max=80), no_markup])
    subtitle = fields.Str(allow_none=True, validate=[validate.Length(max=160), no_markup])
    is_visible = fields.Bool(required=True)
    collection_id = fields.Int(allow_none=True)


class HomepageIn(Schema):
    sections = fields.List(fields.Nested(HomeSectionIn), required=True, validate=validate.Length(min=1))


_homepage_in = HomepageIn()


def _homepage_body():
    return {
        "sections": content.homepage_sections(),
        "collections": [
            {"id": c.id, "name": c.name, "is_active": c.is_active}
            for c in Collection.query.order_by(Collection.name).all()
        ],
    }


@admin_bp.route("/homepage", methods=["GET"])
@admin_required
def admin_homepage():
    return jsonify(_homepage_body()), 200


@admin_bp.route("/homepage", methods=["PUT"])
@admin_required
def save_homepage():
    """Replace the layout: the order of ``sections`` is the order on the page."""
    try:
        data = _homepage_in.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    keys = [s["key"] for s in data["sections"]]
    if sorted(keys) != sorted(content.HOME_KEYS):
        return jsonify(error="Send every homepage section exactly once."), 422

    rows = content.ensure_homepage_rows()
    before = [s["key"] for s in content.homepage_sections() if s["is_visible"]]
    for position, item in enumerate(data["sections"]):
        row = rows[item["key"]]
        row.sort_order = position
        row.is_visible = item["is_visible"]
        if "title" in item:
            row.title = (item["title"] or "").strip() or None
        if "subtitle" in item:
            row.subtitle = (item["subtitle"] or "").strip() or None
        if item["key"] == "featured" and "collection_id" in item:
            collection_id = item["collection_id"]
            if collection_id is not None and db.session.get(Collection, collection_id) is None:
                return jsonify(errors={"collection_id": ["That collection no longer exists."]}), 422
            row.config = {**(row.config or {}), "collection_id": collection_id}
    db.session.flush()

    after = [s["key"] for s in data["sections"] if s["is_visible"]]
    audit.annotate(
        entity="homepage", summary="Homepage layout: " + " → ".join(after),
        changes={"before": before, "after": after},
    )
    db.session.commit()
    return jsonify(_homepage_body()), 200


# ── Navigation ───────────────────────────────────────────────

class NavLinkIn(Schema):
    class Meta:
        unknown = EXCLUDE

    label = fields.Str(required=True, validate=[validate.Length(min=1, max=40), no_markup])
    url = fields.Str(required=True, validate=[validate.Length(max=300), valid_link])
    group_name = fields.Str(allow_none=True, validate=[validate.Length(max=40), no_markup])
    is_visible = fields.Bool(load_default=True)


class NavigationIn(Schema):
    header = fields.List(fields.Nested(NavLinkIn), required=True, validate=validate.Length(max=12))
    footer = fields.List(fields.Nested(NavLinkIn), required=True, validate=validate.Length(max=40))


_navigation_in = NavigationIn()


@admin_bp.route("/navigation", methods=["GET"])
@admin_required
def admin_navigation():
    return jsonify(content.navigation(include_hidden=True)), 200


@admin_bp.route("/navigation", methods=["PUT"])
@admin_required
def save_navigation():
    """Replace both menus. List order is display order."""
    try:
        data = _navigation_in.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    for item in data["footer"]:
        if not (item.get("group_name") or "").strip():
            return jsonify(errors={"footer": ["Every footer link needs a column heading."]}), 422

    NavLink.query.delete()
    for location in ("header", "footer"):
        for position, item in enumerate(data[location]):
            db.session.add(NavLink(
                location=location, label=item["label"].strip(), url=item["url"].strip(),
                group_name=(item.get("group_name") or "").strip() or None if location == "footer" else None,
                sort_order=position, is_visible=item["is_visible"],
            ))
    audit.annotate(
        entity="navigation",
        summary=f"Menus saved: {len(data['header'])} header links, {len(data['footer'])} footer links",
        changes={"header": [i["label"] for i in data["header"]], "footer": [i["label"] for i in data["footer"]]},
    )
    db.session.commit()
    return jsonify(content.navigation(include_hidden=True)), 200


# ── Pages ────────────────────────────────────────────────────

class PageIn(Schema):
    class Meta:
        unknown = EXCLUDE

    title = fields.Str(required=True, validate=[validate.Length(min=1, max=120), no_markup])
    body_html = fields.Str(load_default="", validate=validate.Length(max=100_000))
    meta_title = fields.Str(allow_none=True, validate=[validate.Length(max=70), no_markup])
    meta_description = fields.Str(allow_none=True, validate=[validate.Length(max=200), no_markup])
    share_image_url = fields.Str(allow_none=True, validate=valid_image)


_page_in = PageIn()


@admin_bp.route("/pages", methods=["GET"])
@admin_required
def admin_pages():
    content.ensure_page_rows()
    db.session.commit()
    pages = {p.slug: p for p in CmsPage.query.all()}
    return jsonify(pages=[
        {**content.page_dict(pages[slug]), "path": content.PAGE_PATHS[slug],
         "is_empty": not pages[slug].body_html.strip(), "is_demo": pages[slug].is_demo}
        for slug in content.PAGE_SLUGS
    ]), 200


@admin_bp.route("/pages/<slug>", methods=["GET"])
@admin_required
def admin_page(slug):
    if slug not in content.PAGE_SLUGS:
        return jsonify(error="Page not found"), 404
    content.ensure_page_rows()
    db.session.commit()
    page = CmsPage.query.filter_by(slug=slug).first()
    return jsonify({**content.page_dict(page), "path": content.PAGE_PATHS[slug]}), 200


@admin_bp.route("/pages/<slug>", methods=["PUT"])
@admin_required
def save_page(slug):
    if slug not in content.PAGE_SLUGS:
        return jsonify(error="Page not found"), 404
    try:
        data = _page_in.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(errors=err.messages), 422

    content.ensure_page_rows()
    page = CmsPage.query.filter_by(slug=slug).first()
    page.title = data["title"].strip()
    # Stored already sanitised: whatever reads this later cannot forget to.
    page.body_html = clean_html(data["body_html"])
    page.meta_title = (data.get("meta_title") or "").strip() or None
    page.meta_description = (data.get("meta_description") or "").strip() or None
    page.share_image_url = data.get("share_image_url") or None
    from app.services import demo
    if demo.tagging_requested():
        page.is_demo = True
    elif page.is_demo:
        page.is_demo = False          # the owner has written their own text
    audit.annotate(entity="pages", summary=f"Page \"{page.title}\" saved", changes={"slug": slug})
    db.session.commit()
    return jsonify({**content.page_dict(page), "path": content.PAGE_PATHS[slug]}), 200


# ── FAQ ──────────────────────────────────────────────────────

class FaqIn(Schema):
    class Meta:
        unknown = EXCLUDE

    question = fields.Str(required=True, validate=[validate.Length(min=3, max=200), no_markup])
    answer = fields.Str(required=True, validate=[validate.Length(min=1, max=2000), no_markup])
    is_active = fields.Bool(load_default=True)


_faq_in = FaqIn()


def _faq_dict(item):
    return {"id": item.id, "question": item.question, "answer": item.answer,
            "sort_order": item.sort_order, "is_active": item.is_active, "is_demo": item.is_demo}


def _faq_list():
    return [_faq_dict(i) for i in FaqItem.query.order_by(FaqItem.sort_order, FaqItem.id).all()]


@admin_bp.route("/faq", methods=["GET"])
@admin_required
def admin_faq():
    return jsonify(items=_faq_list()), 200


@admin_bp.route("/faq", methods=["POST"])
@admin_required
def create_faq():
    try:
        data = _faq_in.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(errors=err.messages), 422
    last = db.session.query(db.func.max(FaqItem.sort_order)).scalar()
    item = FaqItem(question=data["question"].strip(), answer=data["answer"].strip(),
                   is_active=data["is_active"], sort_order=(last or 0) + 1)
    db.session.add(item)
    audit.annotate(entity="faq", summary=f"FAQ added: {item.question}")
    db.session.commit()
    return jsonify(_faq_dict(item)), 201


@admin_bp.route("/faq/<int:item_id>", methods=["PUT"])
@admin_required
def update_faq(item_id):
    item = db.session.get(FaqItem, item_id)
    if item is None:
        return jsonify(error="Question not found"), 404
    try:
        data = _faq_in.load(request.get_json(silent=True) or {})
    except ValidationError as err:
        return jsonify(errors=err.messages), 422
    item.question, item.answer, item.is_active = data["question"].strip(), data["answer"].strip(), data["is_active"]
    audit.annotate(entity="faq", summary=f"FAQ edited: {item.question}")
    db.session.commit()
    return jsonify(_faq_dict(item)), 200


@admin_bp.route("/faq/<int:item_id>", methods=["DELETE"])
@admin_required
def delete_faq(item_id):
    item = db.session.get(FaqItem, item_id)
    if item is None:
        return jsonify(error="Question not found"), 404
    audit.annotate(entity="faq", summary=f"FAQ removed: {item.question}")
    db.session.delete(item)
    db.session.commit()
    return jsonify(message="Question removed"), 200


@admin_bp.route("/faq/order", methods=["PUT"])
@admin_required
def reorder_faq():
    ids = (request.get_json(silent=True) or {}).get("ids")
    items = {i.id: i for i in FaqItem.query.all()}
    if not isinstance(ids, list) or sorted(ids) != sorted(items):
        return jsonify(error="Send every question id exactly once."), 422
    for position, item_id in enumerate(ids):
        items[item_id].sort_order = position
    audit.annotate(entity="faq", summary="FAQ reordered")
    db.session.commit()
    return jsonify(items=_faq_list()), 200
