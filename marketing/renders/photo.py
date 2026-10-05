"""Develop a render like a photograph: the small faults a camera and lens
add, which a clean render lacks and the eye reads as 'computer image'.

- vignetting: corners a little darker, as with any wide lens
- grain: fine luminance noise, stronger in the shadows, as from a sensor
- local contrast: an unsharp mask restores the crispness denoising removes
- a gentle tone curve and a slightly warm white balance
"""

import numpy as np
from PIL import Image, ImageFilter


def develop(src, dst, seed=0, vignette=0.14, grain=2.4, warmth=0.012, curve=0.08):
    img = Image.open(src).convert("RGB")
    img = img.filter(ImageFilter.UnsharpMask(radius=1.4, percent=38, threshold=2))
    a = np.asarray(img).astype(np.float32) / 255.0
    h, w, _ = a.shape

    # tone: a soft S-curve around the midtones
    a = a + curve * (a - 0.5) * (1 - np.abs(2 * a - 1))
    # white balance: a whisper warmer
    a[..., 0] *= 1 + warmth
    a[..., 2] *= 1 - warmth

    # vignette: falls off with distance from the centre, normalised to the corners
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / np.sqrt(2)
    a *= (1 - vignette * r ** 2.2)[..., None]

    # grain: half-resolution noise, upsampled so it is soft like real grain
    rng = np.random.default_rng(seed)
    small = rng.normal(0, 1, (h // 2 + 1, w // 2 + 1)).astype(np.float32)
    noise = np.asarray(Image.fromarray(small).resize((w, h), Image.BILINEAR))
    lum = a.mean(axis=2)
    a += (noise * (grain / 255.0) * (0.55 + 0.9 * (1 - lum)))[..., None]

    out = Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8))
    out.save(dst)
    return dst
