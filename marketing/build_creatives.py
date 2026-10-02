#!/usr/bin/env python3
"""Render the Meta and Pinterest ad creatives from marketing/creatives.json.

Every concept is drawn in four sizes: Meta feed square (1:1) and portrait
(4:5), Meta Stories/Reels (9:16, text kept out of the areas the app covers)
and Pinterest (2:3). Product shots come straight from images/, unretouched;
type is Cormorant Garamond (the wordmark's face) with Jost for small labels.

    pip install Pillow
    python3 marketing/build_creatives.py            # all concepts
    python3 marketing/build_creatives.py samples    # one concept

Writes creatives/<concept>/<concept>-<format>.jpg, creatives/ad-copy.csv
and creatives/overview.jpg.
"""

import argparse
import csv
import json
import random
import re
import sys
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SPEC = Path(__file__).with_name("creatives.json")
CATALOG = ROOT / "data" / "import_update.csv"
IMAGES = ROOT / "images"
FONTS = ROOT / "brand" / "fonts"
WORDMARK = ROOT / "brand" / "hh-wordmark-dark@3x.png"
OUT_DIR = ROOT / "creatives"

INK = (28, 28, 28)
MUTED = (112, 106, 98)
PAPER = (255, 255, 255)
STONE = (237, 232, 224)
SHADOW_PAD = 0.06  # shadow margin around a chip, as a share of its size

# name: (width, height, top and bottom margins kept free of text, as a share of height)
FORMATS = {
    "meta-1x1": (1080, 1080, 0.07, 0.07),
    "meta-4x5": (1080, 1350, 0.07, 0.07),
    "meta-9x16": (1080, 1920, 0.14, 0.25),
    "pinterest-2x3": (1000, 1500, 0.07, 0.09),
}
LIMITS = {
    "meta_primary_text": 300, "meta_headline": 40, "meta_description": 30,
    "pinterest_title": 100, "pinterest_description": 500,
}


# --- type -----------------------------------------------------------------

@lru_cache(maxsize=None)
def font(face, size, weight):
    f = ImageFont.truetype(str(FONTS / face), size)
    f.set_variation_by_axes([weight])
    return f


def serif(size, weight=500):
    return font("CormorantGaramond-Variable.ttf", round(size), weight)


def sans(size, weight=400):
    return font("Jost-Variable.ttf", round(size), weight)


def tracked_width(text, f, tracking):
    return sum(f.getlength(ch) for ch in text) + tracking * (len(text) - 1)


def draw_line(draw, text, f, cx, y, fill, tracking=0):
    """Draw one line centred on cx with its cap top at y."""
    top = f.getbbox("H")[1]
    x = cx - tracked_width(text, f, tracking) / 2
    if not tracking:
        draw.text((x, y - top), text, font=f, fill=fill)
        return
    for ch in text:
        draw.text((x, y - top), ch, font=f, fill=fill)
        x += f.getlength(ch) + tracking


def wrap(text, f, width):
    """Fewest lines that fit `width`, split so the lines are as even as possible."""
    words = text.split()
    if f.getlength(text) <= width:
        return [text]
    best = None
    for n in range(2, len(words) + 1):
        for cuts in _splits(len(words), n):
            lines = [" ".join(words[a:b]) for a, b in zip((0,) + cuts, cuts + (len(words),))]
            widest = max(f.getlength(line) for line in lines)
            if any(line.startswith("&") for line in lines[1:]):
                continue  # keep the ampersand at the end of a line
            if widest <= width and (best is None or widest < best[0]):
                best = (widest, lines)
        if best:
            return best[1]
    return words


def _splits(count, parts):
    """Every way to cut `count` words into `parts` non-empty runs, as cut positions."""
    if parts == 1:
        yield ()
        return
    for first in range(1, count - parts + 2):
        for rest in _splits(count - first, parts - 1):
            yield (first,) + tuple(first + r for r in rest)


class Stack:
    """A centred vertical column of blocks: text lines, images and gaps."""

    def __init__(self):
        self.blocks = []

    def text(self, text, f, fill, tracking=0, leading=1.0):
        rise = max(0, f.getbbox("H")[1] - f.getbbox(text)[1])  # ascenders above the caps
        self.blocks.append(("text", text, f, fill, tracking, rise, rise + round(f.size * leading)))

    def image(self, img):
        self.blocks.append(("image", img))

    def gap(self, h):
        self.blocks.append(("gap", round(h)))

    def height(self):
        sizes = {"text": lambda b: b[6], "image": lambda b: b[1].height, "gap": lambda b: b[1]}
        return sum(sizes[b[0]](b) for b in self.blocks)

    def draw(self, canvas, cx, y):
        draw = ImageDraw.Draw(canvas)
        for b in self.blocks:
            if b[0] == "text":
                _, text, f, fill, tracking, rise, line = b
                draw_line(draw, text, f, cx, y + rise, fill, tracking)
                y += line
            elif b[0] == "image":
                paste(canvas, b[1], round(cx - b[1].width / 2), y)
                y += b[1].height
            else:
                y += b[1]
        return y


# --- images ---------------------------------------------------------------

@lru_cache(maxsize=None)
def source(handle):
    return Image.open(IMAGES / f"{handle}.jpg").convert("RGB")


@lru_cache(maxsize=None)
def on_white(handle):
    """True when the shot is a cut-out on white rather than a full-bleed slab."""
    im = source(handle)
    w, h = im.size
    edge = [im.getpixel((x, y)) for x in range(0, w, 32) for y in (2, h - 3)]
    edge += [im.getpixel((x, y)) for y in range(0, h, 32) for x in (2, w - 3)]
    return sum(min(p) >= 245 for p in edge) / len(edge) > 0.5  # cut-outs may touch the edge


def product(handle, size):
    """The product shot filling size x size; full-bleed slabs get a soft shadow."""
    if on_white(handle):
        return source(handle).resize((size, size), Image.LANCZOS)
    inner = round(size / (1 + 2 * SHADOW_PAD))
    return shadowed(source(handle).resize((inner, inner), Image.LANCZOS))


def crop(handle, width, height, share):
    """A crop of the stone's centre, `share` of the shot's width across."""
    im = source(handle)
    cw = round(im.width * share)
    ch = round(cw * height / width)
    if ch > im.height * share:
        ch = round(im.height * share)
        cw = round(ch * width / height)
    left, top = (im.width - cw) // 2, (im.height - ch) // 2
    return im.crop((left, top, left + cw, top + ch)).resize((width, height), Image.LANCZOS)


def shadowed(img, angle=0):
    """img on a transparent sheet with a soft drop shadow, optionally rotated."""
    w, h = img.size
    pad = round(max(w, h) * SHADOW_PAD)
    sheet = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    shadow = Image.new("RGBA", sheet.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle(
        (pad, pad + round(h * 0.015), pad + w, pad + h + round(h * 0.015)), fill=(40, 34, 28, 70))
    sheet = Image.alpha_composite(sheet, shadow.filter(ImageFilter.GaussianBlur(pad / 3)))
    sheet.paste(img, (pad, pad))
    return sheet.rotate(angle, resample=Image.BICUBIC, expand=True) if angle else sheet


def paste(canvas, img, x, y):
    canvas.paste(img, (x, y), img if img.mode == "RGBA" else None)


@lru_cache(maxsize=None)
def wordmark(width):
    mark = Image.open(WORDMARK).convert("RGBA")
    return mark.resize((width, round(mark.height * width / mark.width)), Image.LANCZOS)


# --- catalogue ------------------------------------------------------------

@lru_cache(maxsize=None)
def catalog():
    with open(CATALOG, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    clean = []
    for row in rows:
        clean.append({(re.match(r"Metafield: custom\.(\w+)", k) or [None, k])[1]: v.strip()
                      for k, v in row.items()})
    return {r["Handle"]: r for r in clean}


def spec_line(handle):
    """'POLISHED MARBLE · 12" × 12"' from the product's metafields."""
    row = catalog()[handle]
    words = " ".join(w for w in (row["finish"], row["material"]) if w)
    size = row["nominal_size"].replace(" x ", " × ")
    return " · ".join(p for p in (words, size) if p).upper()


def count(rule):
    return sum(1 for r in catalog().values()
               if all(r[field] in values for field, values in rule.items()))


# --- layouts --------------------------------------------------------------

def frame(fmt):
    w, h, top, bottom = FORMATS[fmt]
    return w, h, round(h * top), h - round(h * bottom)


def render_product(c, fmt):
    w, h, top, bottom = frame(fmt)
    canvas = Image.new("RGB", (w, h), PAPER)
    margin = round(w * 0.08)

    text = Stack()
    text.text(c["kicker"].upper(), sans(w * 0.024, 500), MUTED, tracking=w * 0.005)
    text.gap(w * 0.026)
    for line in wrap(c["headline"], serif(w * 0.068), w - 2 * margin):
        text.text(line, serif(w * 0.068), INK, leading=1.12)
    text.gap(w * 0.008)
    text.text(spec_line(c["handle"]), sans(w * 0.022, 450), MUTED, tracking=w * 0.003)

    mark = wordmark(round(w * 0.36))
    gaps = round(w * 0.05) + round(w * 0.045)
    size = min(w - 2 * margin, bottom - top - mark.height - gaps - text.height())

    stack = Stack()
    stack.image(mark)
    stack.gap(w * 0.05)
    stack.image(product(c["handle"], size))
    stack.gap(w * 0.045)
    stack.blocks += text.blocks
    stack.draw(canvas, w / 2, top + (bottom - top - stack.height()) // 2)
    return canvas


def render_collection(c, fmt):
    w, h, top, bottom = frame(fmt)
    canvas = Image.new("RGB", (w, h), PAPER)
    margin = round(w * 0.07)
    gutter = round(w * 0.02)
    subline = c["subline"].format(count=count(c["count"])) if "count" in c else c["subline"]

    head = Stack()
    head.text(c["headline"], serif(w * 0.078), INK)
    head.gap(w * 0.03)
    head.text(subline.upper(), sans(w * 0.024, 500), MUTED, tracking=w * 0.005)
    mark = wordmark(round(w * 0.34))

    room = bottom - top - head.height() - mark.height - 2 * round(w * 0.06)
    cell = min((w - 2 * margin - gutter) // 2, (room - gutter) // 2)
    grid = Image.new("RGB", (2 * cell + gutter, 2 * cell + gutter), PAPER)
    for i, handle in enumerate(c["handles"][:4]):
        grid.paste(source(handle).resize((cell, cell), Image.LANCZOS),
                   ((i % 2) * (cell + gutter), (i // 2) * (cell + gutter)))

    stack = Stack()
    stack.blocks += head.blocks
    stack.gap(w * 0.06)
    stack.image(grid)
    stack.gap(w * 0.06)
    stack.image(mark)
    stack.draw(canvas, w / 2, top + (bottom - top - stack.height()) // 2)
    return canvas


def render_samples(c, fmt):
    """Loose 4-inch sample chips on a stone-coloured ground."""
    w, h, top, bottom = frame(fmt)
    canvas = Image.new("RGB", (w, h), STONE)
    margin = round(w * 0.09)

    head = Stack()
    for line in wrap(c["headline"], serif(w * 0.072), w - 2 * margin):
        head.text(line, serif(w * 0.072), INK, leading=1.1)
    head.gap(w * 0.025)
    head.text(c["subline"].upper(), sans(w * 0.024, 500), MUTED, tracking=w * 0.005)
    mark = wordmark(round(w * 0.34))

    room = bottom - top - head.height() - mark.height - 2 * w * 0.07
    gap = round(w * 0.045)
    chip = min((w - 2 * margin - 2 * gap) // 3, round((room - gap) / 2 * 0.9))
    field_w, field_h = 3 * chip + 2 * gap, 2 * chip + gap
    field = Image.new("RGBA", (field_w + chip, field_h + chip), (0, 0, 0, 0))
    rng = random.Random(c["id"])  # same scatter every build
    for i, handle in enumerate(c["handles"][:6]):
        sheet = shadowed(crop(handle, chip, chip, 0.42), angle=rng.uniform(-4, 4))
        x = chip // 2 + (i % 3) * (chip + gap) + chip // 2 - sheet.width // 2 + rng.randint(-gap // 4, gap // 4)
        y = chip // 2 + (i // 3) * (chip + gap) + chip // 2 - sheet.height // 2 + rng.randint(-gap // 4, gap // 4)
        field.alpha_composite(sheet, (x, y))
    field = field.crop((chip // 2 - gap // 2, chip // 2 - gap // 2,
                        chip // 2 + field_w + gap // 2, chip // 2 + field_h + gap // 2))

    stack = Stack()
    stack.blocks += head.blocks
    stack.gap(w * 0.07 - gap // 2)
    stack.image(field)
    stack.gap(w * 0.07 - gap // 2)
    stack.image(mark)
    stack.draw(canvas, w / 2, top + (bottom - top - stack.height()) // 2)
    return canvas


def render_brand(c, fmt):
    """Full-bleed stone above, the line and wordmark below."""
    w, h, top, bottom = frame(fmt)
    canvas = Image.new("RGB", (w, h), PAPER)

    text = Stack()
    text.text(c["headline"], serif(w * 0.082, 500), INK)
    text.gap(w * 0.032)
    text.text(c["subline"].upper(), sans(w * 0.024, 500), MUTED, tracking=w * 0.005)
    text.gap(w * 0.06)
    text.image(wordmark(round(w * 0.34)))

    pad = round(w * 0.075)
    stone_h = bottom - text.height() - 2 * pad  # the text ends at the safe-area line
    canvas.paste(crop(c["handle"], w, stone_h, c.get("crop", 0.62)), (0, 0))
    text.draw(canvas, w / 2, stone_h + pad)
    return canvas


RENDERERS = {"product": render_product, "collection": render_collection,
             "samples": render_samples, "brand": render_brand}


# --- output ---------------------------------------------------------------

def check_copy(c):
    problems = [f"{c['id']}: {field} is {len(c[field])} chars (max {limit})"
                for field, limit in LIMITS.items() if len(c.get(field, "")) > limit]
    problems += [f"{c['id']}: unknown handle {h}"
                 for h in c.get("handles", []) + [c.get("handle")] if h and h not in catalog()]
    return problems


def overview(paths, out):
    """Contact sheet of the 4:5 versions for a quick look."""
    thumbs = [Image.open(p) for p in paths if p.name.endswith("meta-4x5.jpg")]
    tw, th, cols, gap = 270, 338, 5, 16
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * th + (rows + 1) * gap), STONE)
    for i, im in enumerate(thumbs):
        sheet.paste(im.resize((tw, th), Image.LANCZOS),
                    (gap + (i % cols) * (tw + gap), gap + (i // cols) * (th + gap)))
    sheet.save(out, quality=85)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("concepts", nargs="*", help="concept ids to render (default: all)")
    ap.add_argument("--spec", type=Path, default=SPEC)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    args = ap.parse_args(argv)

    concepts = json.loads(args.spec.read_text(encoding="utf-8"))["concepts"]
    problems = [p for c in concepts for p in check_copy(c)]
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    chosen = [c for c in concepts if not args.concepts or c["id"] in args.concepts]

    written = []
    for c in chosen:
        folder = args.out / c["id"]
        folder.mkdir(parents=True, exist_ok=True)
        for fmt in FORMATS:
            path = folder / f"{c['id']}-{fmt}.jpg"
            RENDERERS[c["type"]](c, fmt).save(path, quality=90, optimize=True, progressive=True)
            written.append(path)
        print(f"  {c['id']}: {len(FORMATS)} sizes")

    if not args.concepts:
        with open(args.out / "ad-copy.csv", "w", newline="", encoding="utf-8") as f:
            fields = ["concept", "type", "link", *LIMITS, "files"]
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for c in concepts:
                files = ";".join(f"{c['id']}/{c['id']}-{fmt}.jpg" for fmt in FORMATS)
                writer.writerow({**c, "concept": c["id"], "files": files})
        overview(written, args.out / "overview.jpg")
    print(f"wrote {len(written)} images to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
