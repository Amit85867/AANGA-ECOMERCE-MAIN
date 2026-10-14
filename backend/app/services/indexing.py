"""Is this site allowed to be indexed?

Two gates, and both must be open:

* ``INDEXING`` in the environment -- the floor. Set false, nothing the admin
  does can turn indexing on. This is what stops a mis-click in the dashboard
  exposing a site that is not ready.
* the ``seo_indexing`` store setting -- the owner's switch, in
  Admin -> Store settings.

Everything that needs to know (robots.txt, the public settings the storefront
reads for its noindex tag, the sitemap) asks here, so the two can never
disagree.
"""
from flask import current_app


def is_enabled():
    if not current_app.config.get("INDEXING", False):
        return False
    from app.services import store_settings

    value = store_settings.all_values().get("seo_indexing")
    if value is None:
        return True          # env says yes and the owner has not said otherwise
    return str(value).lower() in ("1", "true", "yes", "on")


def reason():
    """Why indexing is off, for the admin's System Health page."""
    if not current_app.config.get("INDEXING", False):
        return "INDEXING is false in the server environment (the hard switch)."
    from app.services import store_settings

    value = store_settings.all_values().get("seo_indexing")
    if value is not None and str(value).lower() not in ("1", "true", "yes", "on"):
        return "Switched off in Admin -> Store settings."
    return None
