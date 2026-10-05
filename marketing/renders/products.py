"""Tile products used in the room renders, and their textures cut from the
catalogue photographs.

Every product here is a real Henry Harlow listing. Sizes come from the
catalogue (data/import_update.csv); the stone on each rendered tile is a
piece of that listing's own photograph, so what a shopper sees in a room is
what arrives in the box.

A product photo shows one of three things, and is cut accordingly:

  sheet  a 12" x 12" mosaic sheet; cut into its rows x cols chips
  grid   several loose tiles photographed together; cut into each tile
  single one tile; used whole

`atlas()` packs the pieces into one image per product, with each piece's
cell recorded so the tiler can give every tile in a room its own stone.
"""

import csv
import json
import re
from fractions import Fraction
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "images"
CATALOG = ROOT / "data" / "import_update.csv"
INCH = 0.0254  # metres

# handle: how the photo is laid out, and the physical tile.
#   chip      face size of one piece in inches (w, h) as laid
#   pitch     centre-to-centre spacing on the sheet, for sheet mosaics
#   grout     joint width in inches, as installed
#   cells     (cols, rows) of pieces in the photo
#   box       sheet or tile bounds in the photo (left, top, right, bottom) px
#   inset     share of each cell trimmed off to lose joints and photo edges
PRODUCTS = {
    "golden-coast-slate-mosaic-wall-and-floor-tile": dict(
        kind="sheet", chip=(1.875, 1.875), pitch=2.0, grout=0.125, cells=(6, 6),
        box=(128, 135, 1917, 1915), inset=0.06, finish="cleft", grout_rgb=(118, 112, 104)),
    "rainbow-slate-1x1-square-tumbled-mosaic-tile": dict(
        kind="sheet", chip=(1.0, 1.0), pitch=12 / 11, grout=12 / 11 - 1.0, cells=(11, 11),
        box=(133, 133, 1920, 1917), inset=0.08, finish="cleft", grout_rgb=(120, 112, 102)),
    "rainbow-slate-wall-and-floor-tile": dict(
        kind="grid", chip=(6.0, 3.0), grout=0.125, cells=(2, 4),
        box=(151, 132, 1904, 1901), inset=0.035, finish="cleft", grout_rgb=(112, 106, 98)),
    "golden-coast": dict(
        kind="grid", chip=(6.0, 3.0), grout=0.125, cells=(2, 4),
        box=(147, 129, 1910, 1901), inset=0.035, finish="cleft", grout_rgb=(110, 106, 100)),
    "chakra-slate-tile": dict(
        kind="grid", chip=(6.0, 3.0), grout=0.125, cells=(2, 4),
        box=(133, 129, 1914, 1912), inset=0.035, finish="cleft", grout_rgb=(96, 98, 100)),
    "empress-green-marble-tile": dict(
        kind="grid", chip=(12.0, 12.0), grout=1 / 16, cells=(2, 2),
        box=(0, 0, 2048, 2048), inset=0.02, finish="honed", grout_rgb=(70, 82, 74)),
    "rosso-levanto-12x12-modern-tumbled-square-tile": dict(
        kind="single", chip=(12.0, 12.0), grout=1 / 8, cells=(1, 1),
        box=(148, 137, 1900, 1901), inset=0.035, finish="tumbled", grout_rgb=(92, 66, 66)),
    "walnut-travertine-tile-cross-cut-18x18-1-2-unfilled-brushed-chiseled": dict(
        kind="single", chip=(18.0, 18.0), grout=1 / 8, cells=(1, 1),
        box=(128, 133, 1916, 1920), inset=0.03, finish="brushed", grout_rgb=(196, 170, 136)),
    "rojo-alicante-marble-12x12-wall-floor-tile": dict(
        kind="single", chip=(12.0, 12.0), grout=1 / 16, cells=(1, 1),
        box=(147, 126, 1910, 1904), inset=0.02, finish="polished", grout_rgb=(214, 196, 182)),
    "amazon-black-slate-wall-and-floor-tile-1": dict(
        kind="single", chip=(24.0, 12.0), grout=1 / 8, cells=(1, 1),
        box=(133, 565, 1924, 1475), inset=0.015, finish="cleft", grout_rgb=(84, 86, 88)),
}


def catalog_row(handle):
    with open(CATALOG, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["Handle"] == handle:
                return {(re.match(r"Metafield: custom\.(\w+)", k) or [None, k])[1]: v
                        for k, v in row.items()}
    raise KeyError(handle)


def inches(text):
    """'3 7/8' -> 3.875"""
    return float(sum(Fraction(part) for part in text.split()))


def check_against_catalog(handle):
    """The modelled piece must match the listing's nominal size.

    Mosaics are named by their nominal chip (2" x 2" is a 1 7/8" chip on a
    2" pitch), so for sheets the pitch is what has to match.
    """
    spec = PRODUCTS[handle]
    nominal = catalog_row(handle)["nominal_size"]
    listed = sorted(inches(n) for n in re.findall(r'([\d /]+)"', nominal))
    modelled = sorted([round(spec["pitch"])] * 2 if spec["kind"] == "sheet" else spec["chip"])
    if listed != modelled:
        raise ValueError(f"{handle}: modelled {modelled} but the catalogue says {nominal!r}")
    return nominal


def pieces(handle):
    """Each stone piece in the photo, as an RGB image."""
    spec = PRODUCTS[handle]
    photo = Image.open(IMAGES / f"{handle}.jpg").convert("RGB")
    left, top, right, bottom = spec["box"]
    cols, rows = spec["cells"]
    cw, ch = (right - left) / cols, (bottom - top) / rows
    out = []
    for r in range(rows):
        for c in range(cols):
            x0, y0, x1, y1 = left + c * cw, top + r * ch, left + (c + 1) * cw, top + (r + 1) * ch
            if spec["kind"] == "sheet":  # chips sit slightly off the grid
                x0, y0, x1, y1 = chip_bounds(photo, x0, y0, x1, y1)
            dx, dy = (x1 - x0) * spec["inset"], (y1 - y0) * spec["inset"]
            out.append(photo.crop((round(x0 + dx), round(y0 + dy), round(x1 - dx), round(y1 - dy))))
    return out


def chip_bounds(photo, x0, y0, x1, y1, pad=0.15):
    """The chip inside a nominal grid cell: the run of stone-coloured rows and
    columns around the cell centre, bounded by the lighter joints."""
    w, h = x1 - x0, y1 - y0
    box = (round(x0 - w * pad), round(y0 - h * pad), round(x1 + w * pad), round(y1 + h * pad))
    grey = np.asarray(photo.crop(box).convert("L"), dtype=float)
    gh, gw = grey.shape
    dark = grey < np.median(grey) + 40  # stone, as opposed to the lighter joints
    col, row = dark.mean(axis=0), dark.mean(axis=1)

    def run(profile, centre):
        lo = hi = centre
        while lo > 0 and profile[lo - 1] > 0.5:
            lo -= 1
        while hi < len(profile) - 1 and profile[hi + 1] > 0.5:
            hi += 1
        return lo, hi

    cx0, cx1 = run(col, gw // 2)
    cy0, cy1 = run(row, gh // 2)
    # fall back to the grid cell if the joint could not be found
    if not (0.7 * w < cx1 - cx0 < 1.15 * w and 0.7 * h < cy1 - cy0 < 1.15 * h):
        return x0, y0, x1, y1
    return box[0] + cx0, box[1] + cy0, box[0] + cx1, box[1] + cy1


def atlas(handle, out_dir, cell_px=None):
    """Pack the pieces into a square-celled atlas; returns (png path, meta)."""
    spec = PRODUCTS[handle]
    tiles = pieces(handle)
    cw, ch = spec["chip"]
    if cell_px is None:  # keep the photo's resolution, capped for memory
        cell_px = min(1024, max(tiles[0].size))
    aspect = cw / ch
    pw, ph = (cell_px, round(cell_px / aspect)) if aspect >= 1 else (round(cell_px * aspect), cell_px)
    n = len(tiles)
    per_row = max(1, round(n ** 0.5))
    rows = -(-n // per_row)
    sheet = Image.new("RGB", (per_row * pw, rows * ph))
    cells = []
    for i, tile in enumerate(tiles):
        # photos of grid tiles show them in their photographed orientation;
        # rotate portrait crops of landscape pieces back to landscape
        if (tile.width >= tile.height) != (pw >= ph):
            tile = tile.rotate(90, expand=True)
        x, y = (i % per_row) * pw, (i // per_row) * ph
        sheet.paste(tile.resize((pw, ph), Image.LANCZOS), (x, y))
        cells.append([x / sheet.width, 1 - (y + ph) / sheet.height, pw / sheet.width, ph / sheet.height])
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{handle}.png"
    sheet.save(path)
    meta = {"handle": handle, **{k: v for k, v in spec.items() if k != "box"}, "uv_cells": cells}
    (out_dir / f"{handle}.json").write_text(json.dumps(meta))
    return path, meta


if __name__ == "__main__":
    import sys
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "marketing" / "renders" / "build" / "atlas"
    for h in PRODUCTS:
        nominal = check_against_catalog(h)
        p, m = atlas(h, out)
        print(f"{h[:50]:50} {nominal:12} {len(m['uv_cells'])} pieces -> {p.name}")
