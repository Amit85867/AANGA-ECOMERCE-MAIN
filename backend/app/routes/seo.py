"""SEO endpoints: sitemap.xml + robots.txt.

Served from the backend so the sitemap always reflects the live catalogue.
URLs point at the public storefront (SITE_URL), not the API. On a split
frontend/API deployment, route the storefront's /sitemap.xml and /robots.txt to
these, or submit the sitemap URL in Google Search Console.
"""
from xml.sax.saxutils import escape

from flask import Blueprint, Response, current_app

from app.models.catalogue import Product, Category

seo_bp = Blueprint("seo", __name__)

# Public storefront routes that should always be indexed.
_STATIC_PATHS = ["/", "/shop", "/about", "/contact", "/faq", "/offers",
                 "/wholesale", "/returns", "/privacy-policy", "/terms"]


def _base():
    return current_app.config.get("SITE_URL", "").rstrip("/")


def _url(path, lastmod=None):
    loc = escape(f"{_base()}{path}")
    if lastmod:
        return f"  <url><loc>{loc}</loc><lastmod>{lastmod}</lastmod></url>"
    return f"  <url><loc>{loc}</loc></url>"


@seo_bp.route("/sitemap.xml")
def sitemap():
    rows = [_url(p) for p in _STATIC_PATHS]

    for slug, in (
        Category.query.filter_by(is_active=True)
        .with_entities(Category.slug).all()
    ):
        rows.append(_url(f"/shop?category={slug}"))

    for slug, updated in (
        Product.query.filter_by(is_active=True)
        .with_entities(Product.slug, Product.updated_at).all()
    ):
        lastmod = updated.date().isoformat() if updated else None
        rows.append(_url(f"/product/{slug}", lastmod))

    from app.models.owner import CmsPage, Collection
    from app.services import content

    for slug, updated in (
        Collection.query.filter_by(is_active=True)
        .with_entities(Collection.slug, Collection.updated_at).all()
    ):
        rows.append(_url(f"/collections/{slug}", updated.date().isoformat() if updated else None))

    # Owner-written pages, once they have something on them. (The paths that
    # are also in the fixed list above are not repeated.)
    for page in CmsPage.query.filter(CmsPage.body_html != "").all():
        path = content.PAGE_PATHS.get(page.slug)
        if path and path not in _STATIC_PATHS:
            rows.append(_url(path, page.updated_at.date().isoformat() if page.updated_at else None))

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(rows)
        + "\n</urlset>\n"
    )
    return Response(xml, mimetype="application/xml")


@seo_bp.route("/robots.txt")
def robots():
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        # Keep private / non-content areas out of the index.
        "Disallow: /admin\n"
        "Disallow: /account\n"
        "Disallow: /checkout\n"
        "Disallow: /cart\n"
        f"\nSitemap: {_base()}/sitemap.xml\n"
    )
    return Response(body, mimetype="text/plain")
