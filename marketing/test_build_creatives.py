"""Tests for build_creatives.py. Skipped when Pillow is not installed.

    python3 -m unittest discover -s marketing
"""

import importlib.util
import json
import unittest

HAVE_PIL = importlib.util.find_spec("PIL") is not None
if HAVE_PIL:
    import build_creatives as bc


@unittest.skipUnless(HAVE_PIL, "Pillow not installed")
class BuildCreativesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.concepts = json.loads(bc.SPEC.read_text(encoding="utf-8"))["concepts"]

    def test_copy_fits_platform_limits(self):
        problems = [p for c in self.concepts for p in bc.check_copy(c)]
        self.assertEqual(problems, [])
        self.assertEqual(len({c["id"] for c in self.concepts}), len(self.concepts))

    def test_wrap_is_even_and_fits(self):
        f = bc.serif(73)
        self.assertEqual(bc.wrap("Nero Marquina & Calacatta Gold", f, 908),
                         ["Nero Marquina &", "Calacatta Gold"])
        self.assertEqual(bc.wrap("Rojo Alicante", f, 908), ["Rojo Alicante"])
        for line in bc.wrap("A very long headline that has to wrap onto several lines", f, 400):
            self.assertLessEqual(f.getlength(line), 400)

    def test_spec_line(self):
        self.assertEqual(bc.spec_line("rojo-alicante-marble-12x12-wall-floor-tile"),
                         'POLISHED MARBLE · 12" × 12"')

    def test_every_type_and_format_keeps_text_in_the_safe_area(self):
        by_type = {}
        for c in self.concepts:
            by_type.setdefault(c["type"], c)
        self.assertEqual(set(by_type), set(bc.RENDERERS))

        for kind, concept in by_type.items():
            for fmt, (w, h, top, bottom) in bc.FORMATS.items():
                with self.subTest(kind=kind, fmt=fmt):
                    img = bc.RENDERERS[kind](concept, fmt)
                    self.assertEqual(img.size, (w, h))
                    # Below the safe line there is only flat background.
                    band = img.crop((0, h - round(h * bottom), w, h))
                    self.assertEqual(len(band.getcolors(1) or []), 1, "content below safe area")
                    if kind != "brand":  # brand art bleeds off the top on purpose
                        band = img.crop((0, 0, w, round(h * top)))
                        self.assertEqual(len(band.getcolors(1) or []), 1, "content above safe area")


if __name__ == "__main__":
    unittest.main()
