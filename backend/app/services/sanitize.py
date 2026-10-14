"""Make owner-written page content safe to show to customers.

The page editor produces a small amount of HTML (headings, paragraphs, lists,
bold, links). Whatever arrives is rebuilt from an allow-list: a tag or attribute
that is not listed is dropped, a link that is not http(s), mailto, tel or a
path on this site loses its address. Nothing is "cleaned" by search and
replace — the output only ever contains what this module wrote itself.
"""
from html import escape
from html.parser import HTMLParser

ALLOWED_TAGS = {
    "p", "br", "h2", "h3", "h4", "strong", "b", "em", "i", "u",
    "ul", "ol", "li", "a", "blockquote", "hr",
}
VOID_TAGS = {"br", "hr"}
# Dropped together with everything inside them.
_SKIP_CONTENT = {"script", "style", "iframe", "object", "embed", "template", "noscript", "svg", "math", "title", "head"}
# What a rich-text editor commonly emits, mapped onto the allowed set.
_RENAME = {"div": "p", "h1": "h2", "h5": "h4", "h6": "h4", "b": "strong", "i": "em"}

MAX_LENGTH = 100_000


def _safe_href(value):
    href = (value or "").strip()
    compact = "".join(href.split()).lower()
    if compact.startswith(("http://", "https://", "mailto:", "tel:")):
        return href
    if href.startswith("/") and not href.startswith("//"):
        return href
    if href.startswith("#"):
        return href
    return None


class _Sanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.open = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP_CONTENT:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        tag = _RENAME.get(tag, tag)
        if tag not in ALLOWED_TAGS:
            return
        if tag in VOID_TAGS:
            self.out.append(f"<{tag}>")
            return
        if tag == "a":
            href = _safe_href(dict(attrs).get("href"))
            if href is None:
                self.out.append("<a>")
            else:
                external = href.lower().startswith(("http://", "https://"))
                rel = ' rel="noopener noreferrer nofollow" target="_blank"' if external else ""
                self.out.append(f'<a href="{escape(href, quote=True)}"{rel}>')
        else:
            self.out.append(f"<{tag}>")
        self.open.append(tag)

    def handle_startendtag(self, tag, attrs):
        if tag in _SKIP_CONTENT or self.skip_depth:
            return
        if _RENAME.get(tag, tag) in VOID_TAGS:
            self.out.append(f"<{_RENAME.get(tag, tag)}>")

    def handle_endtag(self, tag):
        if tag in _SKIP_CONTENT:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        tag = _RENAME.get(tag, tag)
        if tag not in ALLOWED_TAGS or tag in VOID_TAGS or tag not in self.open:
            return
        # Close anything left open inside it, so the output is always balanced.
        while self.open:
            last = self.open.pop()
            self.out.append(f"</{last}>")
            if last == tag:
                break

    def handle_data(self, data):
        if not self.skip_depth:
            self.out.append(escape(data, quote=False))

    def result(self):
        while self.open:
            self.out.append(f"</{self.open.pop()}>")
        return "".join(self.out).strip()


def clean_html(html):
    """Sanitised copy of ``html``. Never raises: unparseable input comes back
    as escaped text."""
    text = (html or "")[:MAX_LENGTH]
    parser = _Sanitizer()
    try:
        parser.feed(text)
        parser.close()
    except Exception:  # noqa: BLE001
        return escape(text)
    return parser.result()


def plain_text(value, max_length=None):
    """A single-line text field with any markup removed."""
    parser = _Sanitizer()
    parser.feed(value or "")
    text = " ".join("".join(
        part for part in parser.out if not part.startswith("<")
    ).split())
    # parser.out holds escaped text; the caller stores plain text.
    text = text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    return text[:max_length] if max_length else text
