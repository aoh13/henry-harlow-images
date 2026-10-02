#!/usr/bin/env python3
"""Build the Meta and Pinterest product catalog feeds.

Prices, variant IDs, stock and images come from the live storefront
(/products.json), so the feeds always match what the shopper sees on the
product page. Material, pattern, finish, colour and coverage come from the
Matrixify sheet in data/, and become product_type and custom labels that the
ad platforms can group products by.

    python3 marketing/build_feeds.py --store https://example.com
    python3 marketing/build_feeds.py --store https://example.com --products-json saved.json

Writes feeds/meta.csv and feeds/pinterest.csv. Standard library only.
"""

import argparse
import csv
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "data" / "import_update.csv"
CONFIG = Path(__file__).with_name("feed_config.json")
OUT_DIR = ROOT / "feeds"
RAW_IMAGES = "https://raw.githubusercontent.com/aoh13/henry-harlow-images/main/images"

FIELDS = [
    "id", "item_group_id", "title", "description", "availability", "condition",
    "price", "sale_price", "link", "image_link", "additional_image_link",
    "brand", "google_product_category", "product_type",
    "custom_label_0", "custom_label_1", "custom_label_2", "custom_label_3",
    "custom_label_4",
]
CHANNEL_FIELDS = {"meta": FIELDS, "pinterest": FIELDS + ["ad_link"]}
MAX_EXTRA_IMAGES = 9  # Pinterest caps additional_image_link at 10 entries


def load_config(path=CONFIG):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_catalog(path=CATALOG):
    """Matrixify rows keyed by handle, with metafield columns shortened."""
    catalog = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            clean = {}
            for key, value in row.items():
                m = re.match(r"Metafield: custom\.(\w+)", key)
                clean[m.group(1) if m else key] = value.strip()
            catalog[clean["Handle"]] = clean
    return catalog


def fetch_store(store_url):
    """Every published product from the storefront's public products.json."""
    products, page = [], 1
    while True:
        url = f"{store_url.rstrip('/')}/products.json?limit=250&page={page}"
        req = urllib.request.Request(url, headers={"User-Agent": "henry-harlow-feeds/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            batch = json.load(resp).get("products", [])
        if not batch:
            return products
        products.extend(batch)
        page += 1


def tags_of(row):
    return {t.strip() for t in row["Tags"].split(",") if t.strip()}


def product_format(row):
    tags, title = tags_of(row), row["Title"].lower()
    if "coaster" in title:
        return "Coaster"
    if "Trim" in tags:
        return "Trim"
    if "Paver" in tags:
        return "Paver"
    if "ledger" in title:
        return "Ledger"
    if "Mosaic Tile" in tags:
        return "Mosaic"
    return "Tile"


def price_per_sqft(row, price):
    """Live per-sq-ft price, or None for products sold by the piece."""
    if row["price_unit"] != "per sq ft" or not row["sqft_per_box"]:
        return None
    sqft = float(row["sqft_per_box"])
    return round(price / sqft, 2) if sqft > 0 else None


def price_tier(per_sqft, tiers):
    if per_sqft is None:
        return "Per Piece"
    for ceiling, name in tiers:
        if ceiling is None or per_sqft < ceiling:
            return name
    return tiers[-1][1]


def coverage(row):
    m = re.search(r"Coverage</strong> — ([^<]+)", row["Body HTML"])
    return html.unescape(m.group(1)).strip() if m else ""


def variation_note(row):
    """The body's sentence on natural variation, without the generic opener."""
    first = re.sub(r"<[^>]+>", "", row["Body HTML"].split("</p>")[0])
    first = html.unescape(first).strip()
    return re.sub(r"^A natural \w+, cut and finished for interiors\.\s*", "", first)


def describe(row, per_sqft):
    parts = []
    if per_sqft is not None:
        line = f"${per_sqft:.2f} per sq ft"
        if coverage(row):
            line += f", {coverage(row)}"
        parts.append(line + ".")
    spec = f"Natural {row['material'].lower()}"
    if row["finish"]:
        spec += f", {row['finish'].lower()} finish"
    if row["nominal_size"]:
        spec += f", {row['nominal_size']}"
    parts.append(spec + ".")
    parts.append(variation_note(row))
    parts.append("4 inch samples available. Ships across the continental US.")
    return " ".join(p for p in parts if p)


def is_sample(variant, pattern):
    names = [variant.get("title")] + [variant.get(f"option{i}") for i in (1, 2, 3)]
    return any(n and re.search(pattern, n, re.IGNORECASE) for n in names)


def images_for(product, variant, handle):
    srcs = [img["src"] for img in product.get("images", []) if img.get("src")]
    featured = (variant.get("featured_image") or {}).get("src")
    if featured:
        srcs = [featured] + [s for s in srcs if s != featured]
    if not srcs:
        srcs = [f"{RAW_IMAGES}/{handle}.jpg"]
    return srcs[0], srcs[1:1 + MAX_EXTRA_IMAGES]


def build_items(products, catalog, config):
    """One feed item per sellable (non-sample) variant of a catalogued product."""
    store = config["store_url"].rstrip("/")
    currency = config["currency"]
    items, skipped = [], {"not_in_catalog": [], "no_price": [], "sample_only": []}
    live_handles = set()

    for product in products:
        handle = product["handle"]
        live_handles.add(handle)
        row = catalog.get(handle)
        if row is None:
            skipped["not_in_catalog"].append(handle)
            continue
        variants = [v for v in product.get("variants", [])
                    if not is_sample(v, config["sample_variant_pattern"])]
        if not variants:
            skipped["sample_only"].append(handle)
            continue

        for variant in variants:
            price = float(variant.get("price") or 0)
            if price <= 0:
                skipped["no_price"].append(handle)
                continue
            compare_at = float(variant.get("compare_at_price") or 0)
            per_sqft = price_per_sqft(row, price)
            title = product["title"]
            if len(variants) > 1:
                title = f"{title} — {variant['title']}"
            image, extra = images_for(product, variant, handle)
            ids = {
                "variant_id": variant["id"], "product_id": product["id"],
                "handle": handle, "sku": variant.get("sku") or "",
            }
            items.append({
                "_ids": ids,
                "item_group_id": product["id"],
                "title": title[:150],
                "description": describe(row, per_sqft),
                "availability": "in stock" if variant.get("available") else "out of stock",
                "condition": "new",
                "price": f"{(compare_at if compare_at > price else price):.2f} {currency}",
                "sale_price": f"{price:.2f} {currency}" if compare_at > price else "",
                "link": f"{store}/products/{handle}?variant={variant['id']}",
                "image_link": image,
                "additional_image_link": ",".join(extra),
                "brand": config["brand"],
                "google_product_category": config["google_product_category"],
                "product_type": f"Natural Stone > {row['material']} > {product_format(row)}",
                "custom_label_0": row["pattern"] or "None",
                "custom_label_1": row["color_family"] or "Other",
                "custom_label_2": row["finish"] or "Other",
                "custom_label_3": price_tier(per_sqft, config["price_tiers_per_sqft"]),
                "custom_label_4": "Outdoor" if "Outdoor" in tags_of(row) else "Indoor",
            })

    skipped["not_live"] = sorted(set(catalog) - live_handles)
    return items, skipped


def channel_rows(items, channel, config):
    id_format = config["id_format"][channel]
    for item in items:
        row = {k: v for k, v in item.items() if not k.startswith("_")}
        row["id"] = id_format.format(**item["_ids"])
        if channel == "pinterest":
            row["ad_link"] = f"{item['link']}&{config['pinterest_ad_link_params']}"
        yield row


def existing_count(path):
    if not path.exists():
        return 0
    with open(path, newline="", encoding="utf-8") as f:
        return max(sum(1 for _ in f) - 1, 0)


def write_feed(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--store", help="storefront URL; overrides store_url in the config")
    ap.add_argument("--products-json", type=Path,
                    help="read a saved products.json instead of fetching from the store")
    ap.add_argument("--config", type=Path, default=CONFIG)
    ap.add_argument("--catalog", type=Path, default=CATALOG)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--allow-shrink", action="store_true",
                    help="write even if the feed loses more than 20%% of its items")
    args = ap.parse_args(argv)

    config = load_config(args.config)
    if args.store:
        config["store_url"] = args.store
    if not config["store_url"]:
        ap.error("no store URL: pass --store or set store_url in feed_config.json")

    catalog = load_catalog(args.catalog)
    if args.products_json:
        data = json.loads(args.products_json.read_text(encoding="utf-8"))
        products = data["products"] if isinstance(data, dict) else data
    else:
        products = fetch_store(config["store_url"])

    items, skipped = build_items(products, catalog, config)
    print(f"{len(products)} live products, {len(catalog)} catalogued, {len(items)} feed items")
    for reason, handles in skipped.items():
        if handles:
            print(f"  skipped {reason}: {len(handles)} (e.g. {', '.join(handles[:3])})")

    if not items:
        print("error: no feed items; is the store password-protected?", file=sys.stderr)
        return 1
    for channel, fields in CHANNEL_FIELDS.items():
        path = args.out / f"{channel}.csv"
        before = existing_count(path)
        if before and len(items) < 0.8 * before and not args.allow_shrink:
            print(f"error: {path.name} would drop from {before} to {len(items)} items; "
                  "rerun with --allow-shrink if that is intended", file=sys.stderr)
            return 1
        write_feed(path, fields, channel_rows(items, channel, config))
        print(f"  wrote {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
