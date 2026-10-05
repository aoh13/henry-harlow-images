"""Checks that the renders show the product as sold.

    python3 -m unittest discover -s marketing/renders

The layout test needs Blender's module (pip install bpy==4.2.0) and is
skipped without it.
"""

import importlib.util
import json
import math
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import products  # noqa: E402

HAVE_BPY = importlib.util.find_spec("bpy") is not None


class ProductTest(unittest.TestCase):
    def test_modelled_sizes_match_the_catalogue(self):
        for handle in products.PRODUCTS:
            with self.subTest(handle=handle):
                products.check_against_catalog(handle)  # raises on a mismatch

    def test_mosaic_sheets_are_twelve_inches(self):
        for handle, spec in products.PRODUCTS.items():
            if spec["kind"] == "sheet":
                cols, rows = spec["cells"]
                self.assertAlmostEqual(cols * spec["pitch"], 12.0, places=6, msg=handle)
                self.assertAlmostEqual(spec["chip"][0] + spec["grout"], spec["pitch"], places=6, msg=handle)

    def test_every_piece_is_cut_from_the_photo(self):
        handle = "rainbow-slate-wall-and-floor-tile"
        pieces = products.pieces(handle)
        self.assertEqual(len(pieces), 8)
        for p in pieces:  # six by three inch pieces photographed landscape
            self.assertGreater(p.width / p.height, 1.6)


class CopyTest(unittest.TestCase):
    def test_pin_copy(self):
        pins = json.loads((HERE / "pins.json").read_text(encoding="utf-8"))["pins"]
        self.assertEqual(len({p["room"] for p in pins}), len(pins))
        for p in pins:
            with self.subTest(room=p["room"]):
                self.assertLessEqual(len(p["title"]), 100)
                self.assertLessEqual(len(p["description"]), 500)
                self.assertIn("3D rendering", p["description"])


@unittest.skipUnless(HAVE_BPY, "Blender's Python module not installed")
class LayoutTest(unittest.TestCase):
    def raster(self, tw, th, joint, pattern, angle=0.0, size=1.0, res=0.001):
        import numpy as np
        from kit import _clip, layout

        n = int(size / res)
        count = np.zeros((n, n), np.uint8)
        ys, xs = np.mgrid[0:n, 0:n]
        px, py = (xs + 0.5) * res, (ys + 0.5) * res
        for (ox, oy), ax, ay, w, h in layout(size, size, tw, th, joint, pattern, angle):
            corners = [(ox, oy), (ox + ax[0] * w, oy + ax[1] * w),
                       (ox + ax[0] * w + ay[0] * h, oy + ax[1] * w + ay[1] * h), (ox + ay[0] * h, oy + ay[1] * h)]
            if len(_clip(corners, 0, 0, size, size)) < 3:
                continue
            a = (px - ox) * ax[0] + (py - oy) * ax[1]
            b = (px - ox) * ay[0] + (py - oy) * ay[1]
            count += ((a >= 0) & (a < w) & (b >= 0) & (b < h)).astype(np.uint8)
        return count

    def test_patterns_never_overlap_and_leave_true_joints(self):
        from kit import INCH
        cases = [
            ("12x12 stacked", 12, 12, 1 / 16, "grid", 0),
            ("12x12 diagonal", 12, 12, 1 / 16, "grid", 45),
            ("3x6 half offset", 6, 3, 1 / 8, "running", 0),
            ("3x6 herringbone", 6, 3, 1 / 8, "herringbone", 45),
            ("12x24 third offset", 24, 12, 1 / 8, "third", 0),
            ("2x2 mosaic", 1.875, 1.875, 1 / 8, "grid", 0),
        ]
        for name, w, h, j, pattern, angle in cases:
            with self.subTest(name):
                count = self.raster(w * INCH, h * INCH, j * INCH, pattern, angle)
                self.assertEqual(count.max(), 1, "tiles overlap")
                covered = (count > 0).mean()
                expected = (w * h) / ((w + j) * (h + j))
                self.assertLess(abs(covered - expected), 0.006, f"coverage {covered:.4f} vs {expected:.4f}")

    def test_centred_layout_has_equal_end_cuts(self):
        from rooms import centred
        length, tile, joint = 3.0, 12 * 0.0254, 0.0254 / 16
        off = centred(length, tile, joint)
        pitch = tile + joint
        n = math.ceil(length / pitch)
        left_cut = off + tile  # the first tile starts at off, before the wall's edge
        right_cut = length - (off + (n - 1) * pitch)
        self.assertAlmostEqual(left_cut, right_cut, places=9)


if __name__ == "__main__":
    unittest.main()
