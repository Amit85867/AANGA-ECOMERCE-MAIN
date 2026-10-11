"""Owner-editable storefront structure: homepage sections, menus and pages.

Nothing here is seeded by SQL. Each list has built-in defaults that are
written to the database the first time an admin opens the screen; until then
the storefront is served the same defaults straight from this file. So a new
database, a test database and a long-running one all behave the same.
"""
from app.extensions import db
from app.models.owner import CmsPage, HomepageSection, NavLink

# key -> (default title, default subtitle, what the admin sees, where its content is edited)
HOME_SECTIONS = [
    ("hero", None, None, "Hero slider", "/admin/banners"),
    ("category_strip", None, None, "Category shortcuts", "/admin/categories"),
    ("features", "Why Choose Us", "Our Promise", "Feature cards", "/admin/features"),
    ("category_tiles", "Shop by Category", "Explore", "Category tiles", "/admin/categories"),
    ("featured", "Best Sellers", "Trending Now", "Featured collection", "/admin/collections"),
    ("promo", None, None, "Promo banners", "/admin/promo-banners"),
    ("testimonials", "What Customers Say", "Testimonials", "Testimonials", "/admin/testimonials"),
    ("newsletter", "Stay in Style", "Get early access to new collections and offers.", "Newsletter sign-up", None),
]
HOME_KEYS = [row[0] for row in HOME_SECTIONS]
_HOME_META = {row[0]: {"label": row[3], "edit_url": row[4]} for row in HOME_SECTIONS}

PAGES = [
    ("about", "About Us"),
    ("contact", "Contact Us"),
    ("faq", "Frequently Asked Questions"),
    ("shipping", "Shipping Policy"),
    ("returns", "Returns & Exchanges"),
    ("privacy", "Privacy Policy"),
    ("terms", "Terms & Conditions"),
]
PAGE_SLUGS = [slug for slug, _ in PAGES]
# Where each page lives on the storefront.
PAGE_PATHS = {"about": "/about", "contact": "/contact", "faq": "/faq", "shipping": "/shipping",
              "returns": "/returns", "privacy": "/privacy-policy", "terms": "/terms"}

DEFAULT_NAV = [
    # (location, group, label, url)
    # A link to a category (/shop?category=<slug>) shows that category's
    # sub-categories as a drop-down on the storefront.
    ("header", None, "New In", "/shop"),
    ("header", None, "Men", "/shop?category=men"),
    ("header", None, "Women", "/shop?category=women"),
    ("header", None, "Offers", "/offers"),
    ("header", None, "Wholesale", "/wholesale"),
    ("footer", "Shop", "All Products", "/shop"),
    ("footer", "Shop", "Offers", "/offers"),
    ("footer", "Shop", "Wholesale", "/wholesale"),
    ("footer", "Help", "Track Order", "/track-order"),
    ("footer", "Help", "Shipping", "/shipping"),
    ("footer", "Help", "Returns & Exchanges", "/returns"),
    ("footer", "Help", "FAQ", "/faq"),
    ("footer", "Company", "About Us", "/about"),
    ("footer", "Company", "Contact", "/contact"),
    ("footer", "Company", "Privacy Policy", "/privacy-policy"),
    ("footer", "Company", "Terms & Conditions", "/terms"),
]


# ── Homepage ─────────────────────────────────────────────────

def _section_dict(key, row=None, position=0):
    default = next(r for r in HOME_SECTIONS if r[0] == key)
    return {
        "key": key,
        "label": _HOME_META[key]["label"],
        "edit_url": _HOME_META[key]["edit_url"],
        "title": row.title if row is not None else default[1],
        "subtitle": row.subtitle if row is not None else default[2],
        "is_visible": row.is_visible if row is not None else True,
        "sort_order": row.sort_order if row is not None else position,
        "config": (row.config or {}) if row is not None else {},
    }


def homepage_sections():
    """Every section, in display order, whether or not it has a row yet."""
    rows = {r.key: r for r in HomepageSection.query.all()}
    sections = [
        _section_dict(key, rows.get(key), position)
        for position, key in enumerate(HOME_KEYS)
    ]
    sections.sort(key=lambda s: (s["sort_order"], HOME_KEYS.index(s["key"])))
    return sections


def ensure_homepage_rows():
    existing = {r.key for r in HomepageSection.query.all()}
    for position, (key, title, subtitle, *_rest) in enumerate(HOME_SECTIONS):
        if key not in existing:
            db.session.add(HomepageSection(key=key, title=title, subtitle=subtitle, sort_order=position))
    db.session.flush()
    return {r.key: r for r in HomepageSection.query.all()}


# ── Navigation ───────────────────────────────────────────────

def _nav_dict(link):
    return {
        "id": link.id, "location": link.location, "group_name": link.group_name,
        "label": link.label, "url": link.url, "sort_order": link.sort_order,
        "is_visible": link.is_visible,
    }


def navigation(include_hidden=False):
    """``{"header": [...], "footer": [...]}``. Falls back to the defaults while
    the table is empty."""
    rows = NavLink.query.order_by(NavLink.location, NavLink.sort_order, NavLink.id).all()
    if rows:
        items = [_nav_dict(r) for r in rows if include_hidden or r.is_visible]
    else:
        items = [
            {"id": None, "location": loc, "group_name": group, "label": label, "url": url,
             "sort_order": i, "is_visible": True}
            for i, (loc, group, label, url) in enumerate(DEFAULT_NAV)
        ]
    return {
        "header": [i for i in items if i["location"] == "header"],
        "footer": [i for i in items if i["location"] == "footer"],
    }


def ensure_nav_rows():
    if NavLink.query.first() is None:
        for i, (loc, group, label, url) in enumerate(DEFAULT_NAV):
            db.session.add(NavLink(location=loc, group_name=group, label=label, url=url, sort_order=i))
        db.session.flush()


# ── Pages ────────────────────────────────────────────────────

def ensure_page_rows():
    existing = {p.slug for p in CmsPage.query.all()}
    for slug, title in PAGES:
        if slug not in existing:
            db.session.add(CmsPage(slug=slug, title=title, body_html=""))
    db.session.flush()


def page_dict(page, slug=None):
    if page is None:
        title = dict(PAGES)[slug]
        return {"slug": slug, "title": title, "body_html": "", "meta_title": None,
                "meta_description": None, "share_image_url": None, "updated_at": None}
    return {
        "slug": page.slug, "title": page.title, "body_html": page.body_html,
        "meta_title": page.meta_title, "meta_description": page.meta_description,
        "share_image_url": page.share_image_url,
        "updated_at": page.updated_at.isoformat() if page.updated_at else None,
    }
