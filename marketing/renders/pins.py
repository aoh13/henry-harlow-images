#!/usr/bin/env python3
"""Turn finished room renders into Pinterest pins and a bulk-upload sheet.

    python3 marketing/renders/pins.py                          # images only
    python3 marketing/renders/pins.py --store https://shop.com  # images + pins.csv

Reads the renders from marketing/renders/build/out (render_room.py) and the
copy from pins.json. Writes creatives/rooms/<room>.jpg (the clean render),
<room>-pin.jpg (wordmark and product line on the ceiling), overview.jpg and,
given the store URL, pins.csv for Pinterest's bulk Pin upload.
"""

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageStat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RENDERS = HERE / "build" / "out"
COPY = HERE / "pins.json"
OUT = ROOT / "creatives" / "rooms"
FONT = ROOT / "brand" / "fonts" / "CormorantGaramond-Variable.ttf"
WORDMARKS = {True: ROOT / "brand" / "hh-wordmark-dark@3x.png", False: ROOT / "brand" / "hh-wordmark-light@3x.png"}
RAW = "https://raw.githubusercontent.com/aoh13/henry-harlow-images/main/creatives/rooms"
CSV_FIELDS = ["Title", "Media URL", "Pinterest board", "Thumbnail", "Description", "Link", "Publish date", "Keywords"]
LIMITS = {"title": 100, "description": 500}


def serif(size, weight=500):
    f = ImageFont.truetype(str(FONT), size)
    f.set_variation_by_axes([weight])
    return f


def pin_image(render, label):
    """The render with the wordmark and product line set on its ceiling, in
    dark ink on a light ceiling and light ink on a dark one."""
    img = render.convert("RGB")
    w, h = img.size
    top = img.crop((0, 0, w, round(h * 0.12)))
    stat = ImageStat.Stat(top)
    dark_ink = sum(stat.mean[:3]) / 3 > 140
    # a soft veil in the ceiling's own colour keeps type legible over fixtures
    veil_h = round(h * 0.17)
    veil = Image.new("RGB", (w, veil_h), tuple(round(c) for c in stat.median[:3]))
    mask = Image.linear_gradient("L").resize((w, veil_h)).point(lambda v: round((255 - v) * 0.6))
    img.paste(veil, (0, 0), mask)

    mark = Image.open(WORDMARKS[dark_ink]).convert("RGBA")
    mw = round(w * 0.3)
    mark = mark.resize((mw, round(mark.height * mw / mark.width)), Image.LANCZOS)
    y = round(h * 0.032)
    img.paste(mark, ((w - mw) // 2, y), mark)
    font = serif(round(w * 0.036))
    draw = ImageDraw.Draw(img)
    ink = (28, 28, 28) if dark_ink else (246, 242, 234)
    tw = draw.textlength(label, font=font)
    draw.text(((w - tw) / 2, y + mark.height + round(h * 0.014)), label, font=font, fill=ink)
    return img


def overview(paths, out):
    thumbs = [Image.open(p) for p in paths]
    tw, th, gap = 300, 450, 14
    cols = 4
    rows = -(-len(thumbs) // cols)
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * gap, rows * th + (rows + 1) * gap), (237, 232, 224))
    for i, im in enumerate(thumbs):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (gap + (i % cols) * (tw + gap), gap + (i // cols) * (th + gap)))
    sheet.save(out, quality=88)


def check(pins):
    problems = []
    for p in pins:
        for field, limit in LIMITS.items():
            if len(p[field]) > limit:
                problems.append(f"{p['room']}: {field} is {len(p[field])} chars (max {limit})")
        if not (RENDERS / f"{p['room']}.png").exists():
            problems.append(f"{p['room']}: no render in {RENDERS}")
    return problems


def store_url(arg):
    if arg:
        return arg.rstrip("/")
    cfg = ROOT / "marketing" / "feed_config.json"
    return json.loads(cfg.read_text()).get("store_url", "").rstrip("/") if cfg.exists() else ""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--store", help="storefront URL for the pin links; defaults to feed_config.json")
    ap.add_argument("--start", default=None, help="first publish date, YYYY-MM-DD (default: in 3 days)")
    ap.add_argument("--hour", type=int, default=15, help="publish hour, UTC")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)

    pins = json.loads(COPY.read_text(encoding="utf-8"))["pins"]
    problems = check(pins)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    pin_paths = []
    for p in pins:
        render = Image.open(RENDERS / f"{p['room']}.png").convert("RGB")
        render.save(args.out / f"{p['room']}.jpg", quality=92, optimize=True, progressive=True)
        path = args.out / f"{p['room']}-pin.jpg"
        pin_image(render, p["label"]).save(path, quality=92, optimize=True, progressive=True)
        pin_paths.append(path)
        print(f"  {p['room']}")
    overview(pin_paths, args.out / "overview.jpg")

    store = store_url(args.store)
    if not store:
        print("no store URL: pins.csv not written (pass --store or set store_url in feed_config.json)")
        return 0
    start = dt.date.fromisoformat(args.start) if args.start else dt.date.today() + dt.timedelta(days=3)
    with open(args.out / "pins.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for i, p in enumerate(pins):
            handle = json.loads((RENDERS / f"{p['room']}.json").read_text())["handle"]
            when = dt.datetime.combine(start + dt.timedelta(days=i), dt.time(args.hour))
            writer.writerow({
                "Title": p["title"],
                "Media URL": f"{RAW}/{p['room']}-pin.jpg",
                "Pinterest board": p["board"],
                "Thumbnail": "",
                "Description": p["description"],
                "Link": f"{store}/products/{handle}?utm_source=pinterest&utm_medium=organic_social"
                        f"&utm_campaign=room_renders&utm_content={p['room']}",
                "Publish date": when.strftime("%Y-%m-%dT%H:%M:%S"),
                "Keywords": p["keywords"],
            })
    print(f"wrote {args.out / 'pins.csv'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
