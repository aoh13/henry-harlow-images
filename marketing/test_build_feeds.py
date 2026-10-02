"""Tests for build_feeds.py against a fake storefront built from the real catalogue.

    python3 -m unittest marketing/test_build_feeds.py
"""

import csv
import json
import tempfile
import unittest
from pathlib import Path

import build_feeds as bf

BOX = "bardiglio-imperial-4x12-leather-tumbled-rectangle-tile"  # 5.0 sq ft per box
PIECE = "carrara-white-marble-4x36-threshold-trim-tile"
SALE = "checkerboard-thassos-white-nero-marquina-12x12-honed-tile"


def variant(vid, title, price, available=True, compare_at=None):
    return {"id": vid, "title": title, "option1": title, "option2": None, "option3": None,
            "price": price, "compare_at_price": compare_at, "available": available,
            "sku": f"SKU{vid}", "featured_image": None}


def product(pid, handle, variants, images=2):
    return {"id": pid, "handle": handle, "title": f"Title {handle}", "variants": variants,
            "images": [{"src": f"https://cdn.example/{handle}-{i}.jpg"} for i in range(images)]}


PRODUCTS = [
    product(1, BOX, [variant(11, "Box", "137.30"), variant(12, "4 inch Sample", "5.00")]),
    product(2, PIECE, [variant(21, "Default Title", "46.00", available=False)], images=0),
    product(3, SALE, [variant(31, "Box", "150.00", compare_at="185.60"), variant(32, "Sample", "5.00")]),
    product(4, "not-in-the-catalogue", [variant(41, "Default Title", "9.00")]),
    product(5, "calgldbor1401", [variant(51, "Sample", "5.00")]),
]


class BuildFeedsTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = Path(tmp.name)
        (self.tmp / "products.json").write_text(json.dumps({"products": PRODUCTS}))
        self.config = bf.load_config()
        self.config["store_url"] = "https://shop.example/"

    def run_build(self, *extra):
        cfg = self.tmp / "config.json"
        cfg.write_text(json.dumps(self.config))
        return bf.main(["--products-json", str(self.tmp / "products.json"),
                        "--config", str(cfg), "--out", str(self.tmp / "feeds"), *extra])

    def read(self, channel):
        with open(self.tmp / "feeds" / f"{channel}.csv", newline="", encoding="utf-8") as f:
            return {r["id"]: r for r in csv.DictReader(f)}

    def test_feed_items(self):
        self.assertEqual(self.run_build(), 0)
        meta = self.read("meta")
        self.assertEqual(sorted(meta), ["11", "21", "31"])  # samples and unknown handles dropped

        box = meta["11"]
        self.assertEqual(box["price"], "137.30 USD")
        self.assertEqual(box["link"], f"https://shop.example/products/{BOX}?variant=11")
        self.assertTrue(box["description"].startswith("$27.46 per sq ft, 5.0 sq ft per box (15 pieces)."))
        self.assertEqual(box["product_type"], "Natural Stone > Marble > Tile")
        self.assertEqual(box["custom_label_3"], "Core")
        self.assertEqual(box["image_link"], f"https://cdn.example/{BOX}-0.jpg")
        self.assertEqual(box["additional_image_link"], f"https://cdn.example/{BOX}-1.jpg")

        piece = meta["21"]
        self.assertEqual(piece["availability"], "out of stock")
        self.assertEqual(piece["custom_label_3"], "Per Piece")
        self.assertEqual(piece["product_type"], "Natural Stone > Marble > Trim")
        self.assertTrue(piece["image_link"].endswith(f"/images/{PIECE}.jpg"))

        sale = meta["31"]
        self.assertEqual((sale["price"], sale["sale_price"]), ("185.60 USD", "150.00 USD"))
        self.assertEqual(sale["custom_label_0"], "Checkerboard")

        pin = self.read("pinterest")["11"]
        self.assertTrue(pin["ad_link"].endswith("?variant=11&utm_source=pinterest"
                                                "&utm_medium=paid_social&utm_campaign=catalog"))
        self.assertNotIn("ad_link", box)

    def test_id_format(self):
        self.config["id_format"]["meta"] = "shopify_US_{product_id}_{variant_id}"
        self.assertEqual(self.run_build(), 0)
        self.assertIn("shopify_US_1_11", self.read("meta"))
        self.assertIn("11", self.read("pinterest"))

    def test_shrink_guard(self):
        self.assertEqual(self.run_build(), 0)
        feeds = self.tmp / "feeds" / "meta.csv"
        lines = feeds.read_text().splitlines()
        feeds.write_text("\n".join(lines + lines[1:] * 3) + "\n")  # pretend it held 12 items
        self.assertEqual(self.run_build(), 1)
        self.assertEqual(self.run_build("--allow-shrink"), 0)

    def test_empty_store_fails(self):
        (self.tmp / "products.json").write_text(json.dumps({"products": []}))
        self.assertEqual(self.run_build(), 1)
        self.assertFalse((self.tmp / "feeds" / "meta.csv").exists())


if __name__ == "__main__":
    unittest.main()
