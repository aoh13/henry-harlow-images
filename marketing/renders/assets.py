"""Painted assets for the renders: a soft garden seen through windows and a
few abstract canvases. Generated, so the renders have no third-party images."""

import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def garden(path, seed=1, size=(2400, 1400)):
    """Out-of-focus garden: pale sky over layered foliage."""
    rnd = random.Random(seed)
    w, h = size
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    for y in range(h):  # sky gradient
        t = y / h
        d.line([(0, y), (w, y)], fill=(int(206 + 30 * t), int(222 + 18 * t), int(236 + 10 * t)))
    greens = [(86, 112, 64), (108, 132, 76), (64, 88, 52), (132, 150, 90), (150, 162, 104), (98, 118, 84)]
    for layer, (top, count, rmin, rmax) in enumerate(((0.35, 120, 60, 180), (0.5, 160, 50, 140), (0.65, 200, 40, 110))):
        for _ in range(count):
            x = rnd.uniform(-100, w + 100)
            y = rnd.uniform(h * top, h * 1.05)
            r = rnd.uniform(rmin, rmax)
            c = rnd.choice(greens)
            shade = 1.0 - 0.12 * layer + rnd.uniform(-0.08, 0.1)
            d.ellipse([x - r, y - r * 0.8, x + r, y + r * 0.8], fill=tuple(int(min(255, v * shade)) for v in c))
    for _ in range(60):  # sunlit highlights
        x, y, r = rnd.uniform(0, w), rnd.uniform(h * 0.35, h), rnd.uniform(10, 40)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(196, 206, 140))
    img = img.filter(ImageFilter.GaussianBlur(28))
    img.save(path)
    return path


PALETTES = {
    "terracotta": [(234, 224, 206), (196, 120, 82), (152, 82, 58), (220, 182, 140)],
    "sage": [(232, 228, 214), (138, 152, 120), (98, 112, 88), (204, 196, 170)],
    "ink": [(236, 232, 224), (40, 38, 36), (150, 140, 128), (210, 200, 186)],
    "ochre": [(238, 230, 214), (204, 154, 80), (120, 96, 70), (226, 206, 168)],
}


def canvas(path, palette="terracotta", seed=3, size=(1200, 1500)):
    """A quiet abstract: a few overlapping soft forms on a paper ground."""
    rnd = random.Random(seed)
    pal = PALETTES[palette]
    w, h = size
    img = Image.new("RGB", size, pal[0])
    d = ImageDraw.Draw(img)
    # an arch, a circle and a stone-like blob
    aw = rnd.uniform(0.35, 0.5) * w
    ax = rnd.uniform(0.15, 0.45) * w
    ay = rnd.uniform(0.35, 0.5) * h
    d.rectangle([ax, ay + aw / 2, ax + aw, h * 0.85], fill=pal[1])
    d.ellipse([ax, ay, ax + aw, ay + aw], fill=pal[1])
    r = rnd.uniform(0.12, 0.2) * w
    cx, cy = rnd.uniform(0.5, 0.8) * w, rnd.uniform(0.2, 0.4) * h
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=pal[2])
    bx = rnd.uniform(0.45, 0.75) * w
    pts = [(bx + rnd.uniform(90, 140) * math.cos(a / 7 * 2 * math.pi),
            0.7 * h + rnd.uniform(70, 100) * math.sin(a / 7 * 2 * math.pi)) for a in range(7)]
    d.polygon(pts, fill=pal[3])
    img = img.filter(ImageFilter.GaussianBlur(1.5))
    noise = Image.effect_noise(size, 18).convert("RGB")
    img = Image.blend(img, noise, 0.04)
    img.save(path)
    return path


def build(out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    garden(out / "garden.png")
    for i, pal in enumerate(PALETTES):
        canvas(out / f"art-{pal}.png", pal, seed=10 + i)
    return out


if __name__ == "__main__":
    import sys
    print(build(sys.argv[1] if len(sys.argv) > 1 else "build/assets"))
