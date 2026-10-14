"""Original placeholder artwork for the demo store.

Every picture the demo content uses that did not come with the project is
drawn here, from shapes, with Pillow. Nothing is downloaded and no photograph
or third-party artwork is involved, so there is no licence to track: the
images are original to this project (see docs/DEMO_ASSETS.md).

They are deliberately simple, flat illustrations. Their job is to make the
store look complete until the owner uploads real photographs.

    python db/demo/make_art.py out/         # writes a contact sheet of samples
"""
import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SS = 2            # drawn at twice the size, then scaled down, for smooth edges


# ── colour helpers ───────────────────────────────────────────

def rgb(hex_colour):
    hex_colour = hex_colour.lstrip("#")
    return tuple(int(hex_colour[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def lighten(colour, t):
    return mix(colour, (255, 255, 255), t)


def darken(colour, t):
    return mix(colour, (0, 0, 0), t)


def font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:                      # very old Pillow
        return ImageFont.load_default()


def backdrop(w, h, top, bottom, glow=None):
    """A soft vertical gradient with an optional lighter pool in the middle."""
    img = Image.new("RGB", (w, h), top)
    px = ImageDraw.Draw(img)
    for y in range(h):
        px.line([(0, y), (w, y)], fill=mix(top, bottom, y / max(1, h - 1)))
    if glow:
        layer = Image.new("RGB", (w, h), glow)
        mask = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask).ellipse([w * 0.1, h * 0.12, w * 0.9, h * 0.8], fill=150)
        img.paste(layer, (0, 0), mask.filter(ImageFilter.GaussianBlur(w * 0.12)))
    return img


def finish(img, w, h, label=None):
    """Scale down to the final size and add the small "sample" caption."""
    img = img.resize((w, h), Image.LANCZOS)
    if label:
        d = ImageDraw.Draw(img)
        f = font(max(14, w // 60))
        d.text((w * 0.04, h - w * 0.05), label, fill=(120, 120, 120), font=f)
    return img


# ── garments and objects, as polygons in a 0..1 box ──────────

TEE = [(.30, .12), (.42, .08), (.50, .13), (.58, .08), (.70, .12), (.92, .28), (.80, .42), (.71, .34),
       (.71, .92), (.29, .92), (.29, .34), (.20, .42), (.08, .28)]
LONG = [(.30, .12), (.42, .08), (.50, .13), (.58, .08), (.70, .12), (.90, .30), (.94, .78), (.82, .80),
        (.76, .40), (.72, .36), (.72, .92), (.28, .92), (.28, .36), (.24, .40), (.18, .80), (.06, .78), (.10, .30)]
TANK = [(.36, .06), (.44, .06), (.50, .20), (.56, .06), (.64, .06), (.70, .32), (.70, .92), (.30, .92), (.30, .32)]
TROUSERS = [(.28, .06), (.72, .06), (.77, .94), (.55, .94), (.50, .36), (.45, .94), (.23, .94)]
LEGGINGS = [(.34, .06), (.66, .06), (.66, .94), (.54, .94), (.50, .34), (.46, .94), (.34, .94)]
SKIRT = [(.34, .10), (.66, .10), (.88, .90), (.12, .90)]
DRESS = [(.38, .06), (.46, .11), (.54, .11), (.62, .06), (.68, .22), (.62, .40), (.86, .94), (.14, .94),
         (.38, .40), (.32, .22)]
KURTA = [(.30, .10), (.44, .06), (.56, .06), (.70, .10), (.90, .50), (.78, .56), (.70, .36), (.75, .94),
         (.25, .94), (.30, .36), (.22, .56), (.10, .50)]
SHOE_UPPER = [(.08, .70), (.10, .50), (.30, .42), (.42, .30), (.56, .30), (.62, .44), (.90, .58), (.94, .70)]

SHAPES = {
    "tee": TEE, "polo": TEE, "shirt": LONG, "hoodie": LONG, "sweater": LONG, "jacket": LONG, "blazer": LONG,
    "tank": TANK, "trousers": TROUSERS, "jeans": TROUSERS, "leggings": LEGGINGS, "skirt": SKIRT,
    "dress": DRESS, "kurta": KURTA,
}


def _poly(points, box):
    x0, y0, x1, y1 = box
    return [(x0 + px * (x1 - x0), y0 + py * (y1 - y0)) for px, py in points]


def _pattern(size, colour, kind, accent, seed):
    """The garment's surface: solid, stripes, checks, dots or a woven texture."""
    w, h = size
    layer = Image.new("RGB", size, colour)
    d = ImageDraw.Draw(layer)
    rnd = random.Random(seed)
    line = darken(colour, .16)
    if kind == "stripes":
        step = w // 14
        for x in range(0, w, step):
            d.rectangle([x, 0, x + step // 3, h], fill=accent)
    elif kind == "checks":
        step = w // 12
        for x in range(0, w, step):
            d.rectangle([x, 0, x + step // 5, h], fill=line)
        for y in range(0, h, step):
            d.rectangle([0, y, w, y + step // 5], fill=line)
    elif kind == "dots":
        step = w // 11
        for i, y in enumerate(range(step // 2, h, step)):
            for x in range(step // 2 + (step // 2 if i % 2 else 0), w, step):
                d.ellipse([x - step // 7, y - step // 7, x + step // 7, y + step // 7], fill=accent)
    elif kind == "knit":
        step = w // 18
        for x in range(0, w, step):
            for y in range(0, h, step):
                d.arc([x, y, x + step, y + step * 2], 200, 340, fill=line, width=max(2, w // 300))
    elif kind == "denim":
        for _ in range(900):
            x, y = rnd.randrange(w), rnd.randrange(h)
            d.line([x, y, x + w // 40, y - w // 40], fill=lighten(colour, .12), width=1)
    else:                                   # a faint weave so a solid is not flat
        for y in range(0, h, max(6, h // 160)):
            d.line([0, y, w, y], fill=lighten(colour, .04), width=1)
    return layer


def _shadow(img, box, strength=70):
    x0, y0, x1, y1 = box
    w = x1 - x0
    layer = Image.new("L", img.size, 0)
    ImageDraw.Draw(layer).ellipse([x0 + w * .12, y1 - w * .03, x1 - w * .12, y1 + w * .05], fill=strength)
    img.paste((40, 40, 40), (0, 0), layer.filter(ImageFilter.GaussianBlur(w * .03)))


def draw_garment(img, kind, box, colour, pattern="solid", accent=None, seed=0):
    """Draw one garment into ``box`` on ``img``."""
    accent = accent or lighten(colour, .55)
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    d = ImageDraw.Draw(img)
    stroke = max(3, w // 160)
    dark = darken(colour, .28)

    if kind in SHAPES:
        _shadow(img, (x0, y0, x1, y1))
        if kind == "hoodie":                # the hood sits behind the body
            d.ellipse([x0 + w * .34, y0 - h * .02, x0 + w * .66, y0 + h * .22], fill=darken(colour, .12), outline=dark, width=stroke)
        points = _poly(SHAPES[kind], (x0, y0, x1, y1))
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).polygon(points, fill=255)
        surface = _pattern((w, h), colour, pattern, accent, seed)
        img.paste(surface, (x0, y0), mask.crop((x0, y0, x1, y1)))
        d = ImageDraw.Draw(img)
        d.line(points + [points[0]], fill=dark, width=stroke, joint="curve")
        cx = x0 + w * .5

        if kind in ("shirt", "polo", "kurta"):
            top = y0 + h * (.13 if kind != "kurta" else .07)
            end = y0 + h * (.92 if kind == "shirt" else .40 if kind == "polo" else .50)
            d.line([cx, top, cx, end], fill=dark, width=stroke)
            for i in range(5 if kind == "shirt" else 3):
                by = top + (end - top) * (i + .6) / (5.2 if kind == "shirt" else 3.4)
                d.ellipse([cx - w * .012, by - w * .012, cx + w * .012, by + w * .012], fill=lighten(colour, .7), outline=dark)
        if kind in ("shirt", "polo"):
            for sx in (-1, 1):
                d.polygon([(cx, y0 + h * .13), (cx + sx * w * .10, y0 + h * .07), (cx + sx * w * .09, y0 + h * .20)],
                          fill=lighten(colour, .12), outline=dark)
        if kind in ("jacket", "blazer"):
            d.polygon([(cx - w * .08, y0 + h * .10), (cx, y0 + h * .48), (cx + w * .08, y0 + h * .10), (cx, y0 + h * .16)],
                      fill=lighten(colour, .82))
            for sx in (-1, 1):
                d.polygon([(cx + sx * w * .08, y0 + h * .10), (cx + sx * w * .17, y0 + h * .30), (cx, y0 + h * .48)],
                          fill=darken(colour, .14), outline=dark)
            d.line([cx, y0 + h * .48, cx, y0 + h * .92], fill=dark, width=stroke)
            for i in range(2 if kind == "blazer" else 4):
                by = y0 + h * (.56 + i * (.14 if kind == "blazer" else .09))
                d.ellipse([cx + w * .02, by, cx + w * .05, by + w * .03], fill=dark)
        if kind == "hoodie":
            d.rounded_rectangle([x0 + w * .36, y0 + h * .62, x0 + w * .64, y0 + h * .82], radius=w // 30, outline=dark, width=stroke)
            for sx in (-1, 1):
                d.line([cx + sx * w * .04, y0 + h * .16, cx + sx * w * .05, y0 + h * .36], fill=lighten(colour, .7), width=stroke)
        if kind in ("sweater", "hoodie"):
            for yy in (.88, .90):
                d.line([x0 + w * .29, y0 + h * yy, x0 + w * .71, y0 + h * yy], fill=dark, width=max(2, stroke // 2))
        if kind in ("trousers", "jeans", "leggings", "skirt"):
            top = y0 + h * (.06 if kind != "skirt" else .10)
            left = x0 + w * (.28 if kind in ("trousers", "jeans") else .34)
            d.rectangle([left, top, x1 - (left - x0), top + h * .045], fill=darken(colour, .14), outline=dark)
        if kind in ("trousers", "jeans"):
            for sx in (-1, 1):
                d.arc([cx + sx * w * .10 - w * .08, y0 + h * .10, cx + sx * w * .10 + w * .08, y0 + h * .26], 20, 160, fill=dark, width=stroke)
        if kind == "skirt":
            for i in range(1, 7):
                t = i / 7
                d.line([x0 + w * (.34 + .32 * t), y0 + h * .15, x0 + w * (.12 + .76 * t), y0 + h * .90], fill=dark, width=max(2, stroke // 2))
        if kind == "dress":
            d.line([x0 + w * .38, y0 + h * .40, x0 + w * .62, y0 + h * .40], fill=dark, width=stroke)
        if kind == "kurta":
            # an embroidered border at the hem and neckline, in the accent colour
            d.rectangle([x0 + w * .26, y0 + h * .86, x0 + w * .74, y0 + h * .91], fill=accent)
            for i in range(9):
                dx = x0 + w * (.29 + i * .0525)
                d.ellipse([dx - w * .012, y0 + h * .875, dx + w * .012, y0 + h * .875 + w * .024], fill=dark)
            d.arc([cx - w * .07, y0 + h * .02, cx + w * .07, y0 + h * .12], 0, 180, fill=accent, width=stroke * 2)
        return

    _shadow(img, (x0, y0 + h * .1, x1, y0 + h * .86))
    d = ImageDraw.Draw(img)
    if kind == "shoe":
        d.polygon(_poly(SHOE_UPPER, (x0, y0, x1, y1)), fill=colour, outline=dark)
        d.rounded_rectangle([x0 + w * .06, y0 + h * .70, x0 + w * .96, y0 + h * .80], radius=h // 30, fill=lighten(colour, .85), outline=dark, width=stroke)
        for i in range(4):
            lx = x0 + w * (.40 + i * .045)
            d.line([lx, y0 + h * (.34 + i * .03), lx + w * .10, y0 + h * (.40 + i * .03)], fill=lighten(colour, .8), width=stroke)
        d.polygon(_poly([(.08, .70), (.10, .52), (.24, .46), (.26, .70)], (x0, y0, x1, y1)), fill=accent, outline=dark)
    elif kind == "bag":
        d.arc([x0 + w * .30, y0 + h * .06, x0 + w * .70, y0 + h * .52], 180, 360, fill=dark, width=stroke * 3)
        d.rounded_rectangle([x0 + w * .14, y0 + h * .30, x0 + w * .86, y0 + h * .88], radius=w // 14, fill=colour, outline=dark, width=stroke)
        d.rounded_rectangle([x0 + w * .14, y0 + h * .30, x0 + w * .86, y0 + h * .52], radius=w // 14, fill=darken(colour, .12), outline=dark, width=stroke)
        d.rounded_rectangle([x0 + w * .45, y0 + h * .46, x0 + w * .55, y0 + h * .58], radius=w // 60, fill=accent, outline=dark, width=stroke)
    elif kind == "backpack":
        d.arc([x0 + w * .38, y0 + h * .04, x0 + w * .62, y0 + h * .24], 180, 360, fill=dark, width=stroke * 3)
        d.rounded_rectangle([x0 + w * .22, y0 + h * .14, x0 + w * .78, y0 + h * .90], radius=w // 7, fill=colour, outline=dark, width=stroke)
        d.rounded_rectangle([x0 + w * .30, y0 + h * .52, x0 + w * .70, y0 + h * .82], radius=w // 20, fill=darken(colour, .12), outline=dark, width=stroke)
        d.line([x0 + w * .30, y0 + h * .36, x0 + w * .70, y0 + h * .36], fill=accent, width=stroke * 2)
    elif kind == "necklace":
        d.arc([x0 + w * .18, y0 - h * .30, x0 + w * .82, y0 + h * .62], 0, 180, fill=colour, width=stroke * 2)
        for i in range(7):
            a = math.radians(20 + i * 23.3)
            bx, by = x0 + w * .5 + math.cos(a) * w * .32, y0 + h * .16 + math.sin(a) * h * .46
            d.ellipse([bx - w * .018, by - w * .018, bx + w * .018, by + w * .018], fill=lighten(colour, .3), outline=dark)
        d.polygon([(x0 + w * .5, y0 + h * .60), (x0 + w * .56, y0 + h * .70), (x0 + w * .5, y0 + h * .82), (x0 + w * .44, y0 + h * .70)], fill=accent, outline=dark)
    elif kind == "ring":
        d.ellipse([x0 + w * .22, y0 + h * .30, x0 + w * .78, y0 + h * .86], outline=colour, width=stroke * 8)
        d.ellipse([x0 + w * .22, y0 + h * .30, x0 + w * .78, y0 + h * .86], outline=dark, width=stroke)
        d.polygon([(x0 + w * .5, y0 + h * .12), (x0 + w * .60, y0 + h * .24), (x0 + w * .5, y0 + h * .38), (x0 + w * .40, y0 + h * .24)], fill=accent, outline=dark)
    elif kind == "bracelet":
        for i in range(3):
            pad = i * w * .05
            d.ellipse([x0 + w * .16 + pad, y0 + h * .30 + pad, x0 + w * .84 - pad, y0 + h * .74 - pad * .4], outline=colour if i != 1 else accent, width=stroke * 4)
    elif kind == "earrings":
        for sx in (.34, .66):
            d.line([x0 + w * sx, y0 + h * .16, x0 + w * sx, y0 + h * .34], fill=dark, width=stroke)
            d.ellipse([x0 + w * (sx - .03), y0 + h * .12, x0 + w * (sx + .03), y0 + h * .18], fill=colour, outline=dark)
            d.polygon([(x0 + w * sx, y0 + h * .34), (x0 + w * (sx + .10), y0 + h * .58), (x0 + w * sx, y0 + h * .82), (x0 + w * (sx - .10), y0 + h * .58)], fill=colour, outline=dark)
            d.ellipse([x0 + w * (sx - .03), y0 + h * .54, x0 + w * (sx + .03), y0 + h * .62], fill=accent)
    elif kind == "sunglasses":
        for sx in (.28, .72):
            d.rounded_rectangle([x0 + w * (sx - .19), y0 + h * .36, x0 + w * (sx + .19), y0 + h * .64], radius=w // 12, fill=colour, outline=dark, width=stroke * 2)
            d.line([x0 + w * (sx - .12), y0 + h * .42, x0 + w * (sx - .02), y0 + h * .42], fill=lighten(colour, .5), width=stroke)
        d.arc([x0 + w * .44, y0 + h * .38, x0 + w * .56, y0 + h * .52], 180, 360, fill=dark, width=stroke * 2)
    elif kind == "watch":
        d.rounded_rectangle([x0 + w * .40, y0 + h * .06, x0 + w * .60, y0 + h * .94], radius=w // 30, fill=colour, outline=dark, width=stroke)
        d.ellipse([x0 + w * .27, y0 + h * .30, x0 + w * .73, y0 + h * .70], fill=lighten(colour, .88), outline=dark, width=stroke * 2)
        d.line([x0 + w * .5, y0 + h * .5, x0 + w * .5, y0 + h * .38], fill=dark, width=stroke)
        d.line([x0 + w * .5, y0 + h * .5, x0 + w * .60, y0 + h * .54], fill=accent, width=stroke)
    elif kind == "belt":
        d.arc([x0 + w * .10, y0 + h * .22, x0 + w * .90, y0 + h * .82], 0, 360, fill=colour, width=stroke * 9)
        d.rounded_rectangle([x0 + w * .40, y0 + h * .72, x0 + w * .60, y0 + h * .90], radius=w // 60, outline=accent, width=stroke * 3)
    elif kind == "cap":
        d.pieslice([x0 + w * .18, y0 + h * .22, x0 + w * .82, y0 + h * 1.02], 180, 360, fill=colour, outline=dark, width=stroke)
        d.rounded_rectangle([x0 + w * .50, y0 + h * .60, x0 + w * .96, y0 + h * .68], radius=h // 40, fill=darken(colour, .14), outline=dark, width=stroke)
        d.ellipse([x0 + w * .48, y0 + h * .20, x0 + w * .52, y0 + h * .24], fill=accent)
    elif kind == "wallet":
        d.rounded_rectangle([x0 + w * .16, y0 + h * .30, x0 + w * .84, y0 + h * .74], radius=w // 22, fill=colour, outline=dark, width=stroke)
        d.line([x0 + w * .16, y0 + h * .44, x0 + w * .84, y0 + h * .44], fill=dark, width=stroke)
        d.rounded_rectangle([x0 + w * .66, y0 + h * .50, x0 + w * .84, y0 + h * .62], radius=w // 60, fill=accent, outline=dark, width=stroke)


# ── product pictures ─────────────────────────────────────────

def product_image(kind, colour_hex, view="front", pattern="solid", accent_hex=None, swatches=(), seed=0, w=1200, h=1600):
    """One product picture.

    ``view``: "front" (the whole item), "detail" (close up) or "flat" (the
    item with its colour swatches, the way a look-book page shows options).
    """
    colour = rgb(colour_hex)
    accent = rgb(accent_hex) if accent_hex else lighten(colour, .55)
    W, H = w * SS, h * SS
    tint = mix(lighten(colour, .86), (244, 240, 234), .55)
    img = backdrop(W, H, lighten(tint, .35), darken(tint, .05), glow=(255, 255, 255))
    wide = kind in ("shoe", "sunglasses", "bag", "belt", "bracelet", "wallet", "cap", "ring", "necklace", "earrings", "watch", "backpack")

    if view == "detail":
        box = (-W * .35, -H * .10, W * 1.35, H * 1.40) if not wide else (-W * .30, H * .02, W * 1.30, H * .98)
        draw_garment(img, kind, box, colour, pattern, accent, seed)
    elif view == "flat":
        box = (W * .20, H * .10, W * .80, H * .66) if not wide else (W * .14, H * .16, W * .86, H * .62)
        draw_garment(img, kind, box, colour, pattern, accent, seed)
        d = ImageDraw.Draw(img)
        chips = list(swatches)[:5] or [colour_hex]
        size = W * .085
        start = W * .5 - (len(chips) * size * 1.5 - size * .5) / 2
        for i, chip in enumerate(chips):
            cx = start + i * size * 1.5
            d.ellipse([cx, H * .76, cx + size, H * .76 + size], fill=rgb(chip), outline=darken(rgb(chip), .3), width=4)
        d.line([W * .30, H * .72, W * .70, H * .72], fill=darken(tint, .18), width=3)
    else:
        box = (W * .12, H * .10, W * .88, H * .88) if not wide else (W * .08, H * .22, W * .92, H * .78)
        draw_garment(img, kind, box, colour, pattern, accent, seed)
    return finish(img, w, h, "Sample image")


def category_tile(kind, colour_hex, w=900, h=1200):
    colour = rgb(colour_hex)
    W, H = w * SS, h * SS
    img = backdrop(W, H, darken(colour, .10), darken(colour, .45))
    d = ImageDraw.Draw(img)
    for i in range(5):                      # quiet concentric rings behind the item
        r = W * (.28 + i * .11)
        d.ellipse([W * .5 - r, H * .42 - r, W * .5 + r, H * .42 + r], outline=lighten(colour, .10 + i * .02), width=3)
    wide = kind not in SHAPES
    box = (W * .18, H * .12, W * .82, H * .72) if not wide else (W * .12, H * .22, W * .88, H * .62)
    draw_garment(img, kind, box, lighten(colour, .78), "solid", lighten(colour, .35))
    return finish(img, w, h)


def avatar(initials, colour_hex, size=320):
    colour = rgb(colour_hex)
    S = size * SS
    img = backdrop(S, S, lighten(colour, .15), darken(colour, .2))
    d = ImageDraw.Draw(img)
    f = font(S // 3)
    box = d.textbbox((0, 0), initials, font=f)
    d.text(((S - (box[2] - box[0])) / 2 - box[0], (S - (box[3] - box[1])) / 2 - box[1]), initials, fill=(255, 255, 255), font=f)
    return img.resize((size, size), Image.LANCZOS)


# ── hero and banner scenes ───────────────────────────────────

def _bokeh(img, colours, count, seed, y_range=(0, 1), radius=(.02, .07)):
    w, h = img.size
    rnd = random.Random(seed)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(count):
        r = w * rnd.uniform(*radius)
        x, y = rnd.uniform(0, w), rnd.uniform(h * y_range[0], h * y_range[1])
        d.ellipse([x - r, y - r, x + r, y + r], fill=rgb(rnd.choice(colours)) + (rnd.randint(40, 120),))
    img.paste(layer.filter(ImageFilter.GaussianBlur(w * .006)), (0, 0), layer.filter(ImageFilter.GaussianBlur(w * .006)))


def _diya(d, cx, cy, size, clay=(184, 92, 46)):
    """An oil lamp: a clay bowl, a rim, and a flame."""
    d.pieslice([cx - size, cy - size * .55, cx + size, cy + size * .75], 0, 180, fill=clay, outline=darken(clay, .35), width=max(3, int(size * .04)))
    d.ellipse([cx - size, cy - size * .16, cx + size, cy + size * .16], fill=darken(clay, .18), outline=darken(clay, .35), width=max(3, int(size * .04)))
    for i in range(5):
        dx = cx - size * .6 + i * size * .3
        d.ellipse([dx - size * .05, cy + size * .28, dx + size * .05, cy + size * .38], fill=(244, 196, 48))
    glow = [(255, 214, 102), (255, 170, 51), (255, 240, 190)]
    for i, scale in enumerate((1.0, .68, .36)):
        fw, fh = size * .30 * scale, size * .78 * scale
        d.polygon([(cx, cy - size * .10 - fh), (cx + fw, cy - size * .06 - fh * .25), (cx, cy - size * .02), (cx - fw, cy - size * .06 - fh * .25)], fill=glow[i])


def _gift(d, x, y, size, colour, ribbon):
    d.rectangle([x, y, x + size, y + size * .82], fill=colour, outline=darken(colour, .3), width=4)
    d.rectangle([x - size * .05, y - size * .16, x + size * 1.05, y + size * .06], fill=lighten(colour, .12), outline=darken(colour, .3), width=4)
    d.rectangle([x + size * .43, y - size * .16, x + size * .57, y + size * .82], fill=ribbon)
    for sx in (-1, 1):
        d.ellipse([x + size * .5 + sx * size * .02 - (size * .22 if sx < 0 else 0), y - size * .40,
                   x + size * .5 + sx * size * .02 + (size * .22 if sx > 0 else 0), y - size * .14], outline=ribbon, width=max(6, int(size * .05)))


def _marigolds(d, y, w, size, colours=((242, 169, 0), (255, 122, 0))):
    """A garland: a sagging string of round flowers."""
    n = int(w / (size * 1.5)) + 1
    for i in range(n):
        x = i * size * 1.5
        sag = math.sin(i / max(1, n - 1) * math.pi) * size * 2.2
        c = colours[i % 2]
        d.ellipse([x - size, y + sag - size, x + size, y + sag + size], fill=c, outline=darken(c, .25), width=3)
        d.ellipse([x - size * .45, y + sag - size * .45, x + size * .45, y + sag + size * .45], fill=lighten(c, .25))


def hero_scene(theme, w=1200, h=1500, seed=1):
    """A hero slide. Everyday: "new-season", "workwear", "weekend".
    Diwali: "lights", "diyas", "gifting"."""
    W, H = w * SS, h * SS
    if theme == "lights":
        img = backdrop(W, H, (22, 16, 48), (74, 22, 52))
        _bokeh(img, ["#F2A900", "#FFD36B", "#FF8A3D", "#FFF1C2"], 70, seed, (0, .75))
        d = ImageDraw.Draw(img)
        for row, y in enumerate((H * .10, H * .24)):
            for i in range(12):
                x = W * (i / 11)
                sag = math.sin(i / 11 * math.pi) * H * .05
                d.line([x, y + sag, x, y + sag + H * .02], fill=(255, 236, 179), width=3)
                c = [(242, 169, 0), (255, 122, 0), (255, 214, 102)][(i + row) % 3]
                d.polygon([(x, y + sag + H * .02), (x + W * .022, y + sag + H * .05), (x, y + sag + H * .085), (x - W * .022, y + sag + H * .05)], fill=c, outline=darken(c, .2))
        for i, (cx, s) in enumerate(((W * .26, W * .13), (W * .52, W * .17), (W * .78, W * .12))):
            _diya(d, cx, H * (.78 if i != 1 else .74), s)
    elif theme == "diyas":
        img = backdrop(W, H, (110, 28, 30), (48, 12, 34))
        d = ImageDraw.Draw(img)
        cx, cy = W * .5, H * .46                 # a rangoli of petals
        for ring, (count, r, c) in enumerate(((16, W * .40, (242, 169, 0)), (12, W * .29, (255, 122, 0)), (8, W * .18, (255, 240, 190)))):
            for i in range(count):
                a = 2 * math.pi * i / count + ring * .2
                px, py = cx + math.cos(a) * r, cy + math.sin(a) * r
                pr = W * (.055 - ring * .008)
                d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=c, outline=darken(c, .3), width=4)
        d.ellipse([cx - W * .09, cy - W * .09, cx + W * .09, cy + W * .09], fill=(180, 36, 93), outline=(242, 169, 0), width=10)
        for i in range(5):
            _diya(d, W * (.14 + i * .18), H * .86, W * .075)
    elif theme == "gifting":
        img = backdrop(W, H, (16, 74, 76), (10, 36, 52))
        _bokeh(img, ["#F2A900", "#FFD36B", "#FFFFFF"], 35, seed, (0, .5), (.01, .04))
        d = ImageDraw.Draw(img)
        _marigolds(d, H * .06, W, W * .03)
        _gift(d, W * .12, H * .56, W * .36, (180, 36, 93), (255, 214, 102))
        _gift(d, W * .50, H * .46, W * .40, (242, 169, 0), (110, 28, 30))
        _gift(d, W * .34, H * .74, W * .26, (245, 240, 230), (180, 36, 93))
        _diya(d, W * .82, H * .90, W * .07)
    else:
        scenes = {
            "new-season": ((236, 228, 216), (214, 200, 182), [("dress", "#8A3B4B", "solid"), ("shirt", "#31506E", "stripes"), ("skirt", "#C7A66B", "solid")]),
            "workwear": ((224, 228, 232), (190, 198, 206), [("blazer", "#2B2F3A", "solid"), ("trousers", "#6B7280", "checks"), ("shirt", "#F1EEE8", "solid")]),
            "weekend": ((240, 232, 214), (222, 196, 158), [("hoodie", "#B5542B", "solid"), ("jeans", "#3B5171", "denim"), ("tee", "#EDE6D6", "dots")]),
        }
        top, bottom, items = scenes.get(theme, scenes["new-season"])
        img = backdrop(W, H, top, bottom, glow=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.rectangle([W * .08, H * .08, W * .92, H * .92], outline=darken(bottom, .18), width=6)
        slots = [(W * .10, H * .14, W * .62, H * .70), (W * .44, H * .30, W * .92, H * .82), (W * .14, H * .56, W * .52, H * .94)]
        for (kind, colour, pattern), slot in zip(items, slots):
            draw_garment(img, kind, slot, rgb(colour), pattern, seed=seed)
    return finish(img, w, h)


def promo_scene(colour_hex="#1C1C1E", w=1200, h=900):
    W, H = w * SS, h * SS
    colour = rgb(colour_hex)
    img = backdrop(W, H, lighten(colour, .06), darken(colour, .3))
    d = ImageDraw.Draw(img)
    for i in range(8):
        d.rectangle([W * (.06 + i * .12), H * .16, W * (.06 + i * .12) + W * .05, H * .84], fill=lighten(colour, .08 + (i % 3) * .04))
    draw_garment(img, "jacket", (W * .30, H * .08, W * .70, H * .96), (198, 160, 96), "solid")
    return finish(img, w, h)


def share_card(store_name, tagline, w=1200, h=630):
    W, H = w * SS, h * SS
    img = backdrop(W, H, (20, 20, 22), (0, 0, 0))
    d = ImageDraw.Draw(img)
    f = font(H // 5)
    box = d.textbbox((0, 0), store_name, font=f)
    d.text(((W - (box[2] - box[0])) / 2 - box[0], H * .30), store_name, fill=(255, 255, 255), font=f)
    f2 = font(H // 18)
    box = d.textbbox((0, 0), tagline, font=f2)
    d.text(((W - (box[2] - box[0])) / 2 - box[0], H * .62), tagline, fill=(200, 200, 200), font=f2)
    d.line([W * .42, H * .56, W * .58, H * .56], fill=(245, 55, 101), width=8)
    return img.resize((w, h), Image.LANCZOS)


def crop_detail(source, zoom=1.9, focus=(.5, .42)):
    """A close-up cut from an existing product picture (same picture, so the
    same rights as the original)."""
    w, h = source.size
    cw, ch = w / zoom, h / zoom
    left = min(max(focus[0] * w - cw / 2, 0), w - cw)
    top = min(max(focus[1] * h - ch / 2, 0), h - ch)
    return source.crop((int(left), int(top), int(left + cw), int(top + ch))).resize((w, h), Image.LANCZOS)


if __name__ == "__main__":
    import pathlib
    import sys

    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "demo-art-samples")
    out.mkdir(parents=True, exist_ok=True)
    samples = {
        "product-kurta-front": product_image("kurta", "#7A1F3D", "front", accent_hex="#F2A900"),
        "product-kurta-detail": product_image("kurta", "#7A1F3D", "detail", accent_hex="#F2A900"),
        "product-shirt-flat": product_image("shirt", "#31506E", "flat", "stripes", swatches=["#31506E", "#F1EEE8", "#6B7280"]),
        "product-shoe": product_image("shoe", "#F3F0EA", "front", accent_hex="#B5542B"),
        "product-earrings": product_image("earrings", "#D4A017", "front", accent_hex="#B4245D"),
        "category-dress": category_tile("dress", "#8A3B4B"),
        "hero-lights": hero_scene("lights"), "hero-diyas": hero_scene("diyas"), "hero-gifting": hero_scene("gifting"),
        "hero-new-season": hero_scene("new-season"), "promo": promo_scene(), "share": share_card("AANGA", "Premium fashion, delivered across India"),
    }
    for name, image in samples.items():
        image.save(out / f"{name}.webp", "WEBP", quality=82)
    print(f"wrote {len(samples)} samples to {out}")
