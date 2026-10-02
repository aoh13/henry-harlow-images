# Henry Harlow — product imagery

Public host for the Shopify product swatches. Each file is a 2048x2048 sRGB
JPEG of a real slab: cropped, de-skewed and re-lit, never generated.

Served to Shopify's product importer over raw.githubusercontent.com, because
the importer will not fetch images from the store's own CDN.

`feeds/` holds the Meta and Pinterest catalog feeds, rebuilt daily from the
live store by `marketing/build_feeds.py`; see `marketing/README.md` for the
ad setup.
