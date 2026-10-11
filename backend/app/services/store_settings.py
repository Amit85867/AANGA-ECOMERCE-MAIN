"""The store's own settings: name, contact details, shipping fee, COD, returns.

A fixed list of typed fields kept in the ``site_settings`` key/value table.
Read through a short cache that every admin save clears (the catalogue cache
drops on any admin write), so a change is live on the next request with no
deploy.
"""
import re

from app.extensions import db
from app.models.cms import SiteSetting
from app.services import cache

TEXT, LONGTEXT, EMAIL, PHONE, URL, IMAGE, MONEY, INT, BOOL, GSTIN = (
    "text", "longtext", "email", "phone", "url", "image", "money", "int", "bool", "gstin",
)


class Field:
    def __init__(self, key, label, kind, group, default="", help="", minimum=None, maximum=None, max_length=300):
        self.key, self.label, self.kind, self.group = key, label, kind, group
        self.default, self.help = default, help
        self.minimum, self.maximum, self.max_length = minimum, maximum, max_length


FIELDS = [
    Field("store_name", "Store name", TEXT, "Store", "AANGA", max_length=60),
    Field("store_tagline", "Tagline", TEXT, "Store", "", "Shown in the footer and in search results.", max_length=160),
    Field("logo_url", "Logo", IMAGE, "Store", "", "Square image, at least 168 px. Leave empty for the built-in logo."),
    Field("favicon_url", "Browser tab icon (favicon)", IMAGE, "Store", "", "Square image. Leave empty for the built-in icon."),
    Field("gstin", "GSTIN", GSTIN, "Store", "", "15 characters. Printed in the footer when filled in."),

    Field("store_email", "Contact email", EMAIL, "Contact"),
    Field("store_phone", "Contact phone", PHONE, "Contact"),
    Field("store_address", "Address", LONGTEXT, "Contact", max_length=500),
    Field("whatsapp_number", "WhatsApp number", PHONE, "Contact", "", "With country code, e.g. +91 98765 43210."),

    Field("instagram_url", "Instagram", URL, "Social links"),
    Field("facebook_url", "Facebook", URL, "Social links"),
    Field("twitter_url", "X (Twitter)", URL, "Social links"),
    Field("youtube_url", "YouTube", URL, "Social links"),

    Field("delivery_charge", "Shipping fee (₹)", MONEY, "Shipping and payment", "49",
          "Charged on orders below the free-shipping amount. 0 for always free.", minimum=0, maximum=5000),
    Field("free_shipping_threshold", "Free shipping from (₹)", MONEY, "Shipping and payment", "999",
          "Orders with a subtotal of at least this much ship free. 0 for always free.", minimum=0, maximum=1000000),
    Field("cod_enabled", "Accept cash on delivery", BOOL, "Shipping and payment", "true"),
    Field("return_window_days", "Return window (days)", INT, "Shipping and payment", "7",
          "How long after delivery a customer may request a return. 0 switches returns off.", minimum=0, maximum=90),

    Field("seo_title", "Default page title", TEXT, "Search and sharing", "", "Used on the home page and wherever a page has no title of its own.", max_length=70),
    Field("seo_description", "Default description", LONGTEXT, "Search and sharing", "", max_length=200),
    Field("seo_share_image", "Default share image", IMAGE, "Search and sharing", "", "Shown when a link to the store is shared. 1200 × 630 works best."),
]
BY_KEY = {f.key: f for f in FIELDS}

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^\+?[0-9][0-9 \-]{6,18}$")
_GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
_URL_RE = re.compile(r"^https?://[^\s<>\"']+$", re.I)
_IMAGE_RE = re.compile(r"^(https?://|/static/uploads/)[^\s<>\"']+$", re.I)


def clean(field, raw):
    """Validated, normalised string for storage. Raises ValueError with a
    message meant for the owner."""
    if field.kind == BOOL:
        if isinstance(raw, bool):
            return "true" if raw else "false"
        if str(raw).strip().lower() in ("true", "false"):
            return str(raw).strip().lower()
        raise ValueError("Choose yes or no.")

    value = "" if raw is None else str(raw).strip()
    if field.kind in (MONEY, INT):
        if value == "":
            raise ValueError("Enter a number.")
        try:
            number = float(value)
        except ValueError:
            raise ValueError("Enter a number.") from None
        if field.kind == INT and number != int(number):
            raise ValueError("Enter a whole number.")
        if field.minimum is not None and number < field.minimum:
            raise ValueError(f"Cannot be less than {field.minimum}.")
        if field.maximum is not None and number > field.maximum:
            raise ValueError(f"Cannot be more than {field.maximum}.")
        return str(int(number)) if number == int(number) else f"{number:.2f}"

    if len(value) > field.max_length:
        raise ValueError(f"Keep this under {field.max_length} characters.")
    if value == "":
        if field.key == "store_name":
            raise ValueError("The store needs a name.")
        return ""
    if "<" in value or ">" in value:
        raise ValueError("Plain text only.")
    if field.kind == EMAIL and not _EMAIL_RE.match(value):
        raise ValueError("Enter a valid email address.")
    if field.kind == PHONE and not _PHONE_RE.match(value):
        raise ValueError("Enter a phone number, digits only, with an optional + at the start.")
    if field.kind == URL and not _URL_RE.match(value):
        raise ValueError("Enter a full link starting with https://")
    if field.kind == IMAGE and not _IMAGE_RE.match(value):
        raise ValueError("Choose an image from the media library.")
    if field.kind == GSTIN:
        value = value.upper().replace(" ", "")
        if not _GSTIN_RE.match(value):
            raise ValueError("A GSTIN has 15 characters, e.g. 10ABCDE1234F1Z5.")
    return value


def _load():
    rows = SiteSetting.query.filter(SiteSetting.key.in_(list(BY_KEY))).all()
    stored = {r.key: r.value for r in rows}
    values = {}
    for f in FIELDS:
        value = stored.get(f.key)
        # A number or a switch always has a value; text may be left empty.
        if value is None or (value == "" and f.kind in (MONEY, INT, BOOL)):
            value = f.default
        values[f.key] = value
    return values


def all_values():
    return cache.get_or_set("store-settings", 60, _load, scoped=False)


def get(key):
    return all_values().get(key, BY_KEY[key].default)


def number(key):
    try:
        return float(get(key))
    except (TypeError, ValueError):
        return float(BY_KEY[key].default)


def flag(key):
    return str(get(key)).lower() == "true"


def save(values):
    """Validate and store ``{key: value}``. Returns ``(changes, errors)``;
    nothing is written when there are errors."""
    errors, cleaned = {}, {}
    for key, raw in values.items():
        field = BY_KEY.get(key)
        if field is None:
            errors[key] = ["Unknown setting."]
            continue
        try:
            cleaned[key] = clean(field, raw)
        except ValueError as exc:
            errors[key] = [str(exc)]
    if errors:
        return {}, errors

    existing = {r.key: r for r in SiteSetting.query.filter(SiteSetting.key.in_(list(cleaned))).all()}
    changes = {}
    for key, value in cleaned.items():
        row = existing.get(key)
        before = row.value if row else BY_KEY[key].default
        if row is None:
            db.session.add(SiteSetting(key=key, value=value, label=BY_KEY[key].label, group_name="store"))
        else:
            row.value = value
        if before != value:
            changes[key] = {"from": before, "to": value}
    return changes, {}
