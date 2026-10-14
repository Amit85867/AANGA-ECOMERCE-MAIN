"""Shared list plumbing for the API: paging, sorting, date filters.

Every list endpoint pages through here so the page size is always capped — an
unbounded ``.all()`` is fine with thirty rows and an outage with thirty
thousand.
"""
from datetime import datetime, timezone

from flask import request

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


def paginate(query, default=DEFAULT_PER_PAGE, cap=MAX_PER_PAGE):
    """Page a query from ``?page`` / ``?per_page``, clamped to sane values."""
    page = max(request.args.get("page", 1, type=int) or 1, 1)
    per_page = request.args.get("per_page", default, type=int) or default
    per_page = min(max(per_page, 1), cap)
    return query.paginate(page=page, per_page=per_page, error_out=False)


def page_meta(page):
    return {"page": page.page, "pages": page.pages, "total": page.total}


def apply_sort(query, columns, default):
    """Order by ``?sort`` / ``?dir`` using a whitelist of sortable columns.

    ``columns`` maps the public sort name to a column. Anything not in the map
    falls back to ``default`` (a public name), so a client can never sort by —
    or probe for — a column it was not offered.
    """
    name = request.args.get("sort") or default
    column = columns.get(name, columns[default])
    descending = (request.args.get("dir") or "desc").lower() != "asc"
    return query.order_by(column.desc() if descending else column.asc())


def parse_day(value):
    """``YYYY-MM-DD`` -> midnight UTC, or None when absent or malformed."""
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
