---
name: monasteel-offer
description: Generate a Mona Steel LLC quotation PDF for the US market (US Letter, imperial units, US business wording, Mona Steel logo and charcoal brand rules). Use whenever Onur asks for a Mona Steel / Monasteel offer, quote or "teklif", e.g. "monasteel için teklif hazırla", "Mona Steel quote for W16x67".
---

# Mona Steel — Quotation Generator

Same layout as the Yilmaz Sac offer form, re-branded for Mona Steel LLC and
adapted to the US market. Self-contained — everything lives in this folder:

- `scripts/build_monasteel.py` — the generator (run this)
- `scripts/generate_offer.py` — shared layout engine (copied from yilmaz-offer; patched in memory, never edit it)
- `assets/monasteel_logo.png` — Mona Steel wordmark (transparent)
- `assets/example_config.json` — reference config (W-shape order, Oct 2026)

```bash
python <skill dir>/scripts/build_monasteel.py config.json MSDDMMYYYYNN.pdf
pdftoppm -r 150 -png -singlefile MSDDMMYYYYNN.pdf preview
```

Prints `OK | Grand total: USD X | Total weight: N lbs | <path>`.
Always look at the rendered PNG before sending, and send **both** the PNG
(the chat preview cannot always show PDFs) and the PDF.

**Editable Excel version** (same layout, same config; when Onur wants to edit
the quote himself):

```bash
python <skill dir>/scripts/build_monasteel_xlsx.py config.json MSDDMMYYYYNN.xlsx
python <xlsx skill dir>/scripts/recalc.py MSDDMMYYYYNN.xlsx 60   # must report 0 errors
```

Live formulas: Total Wt. = lb/ft × ft × qty, Extended = qty × unit price,
Subtotal/TOTAL, Valid Through = Quote Date + 30. Ten item rows (blank rows stay
empty), prints on one US Letter page, a "How to use" sheet lists the editable cells.

---

## ⚠️ Strict rules

1. **Never add anything on your own.** Only what Onur asked for plus the defaults
   below. No Remarks, no extra notes, no reworded terms. Assumptions and notes go
   in the chat message, never into the PDF. If something seems off, ask.
2. **One page when it fits; never split blocks.** The terms block and the
   signature block are each kept together (built in). Check the page count after
   generating.
3. **No orange.** Rules use Mona Steel charcoal `#2D2D2D` (built in).
4. Talk to Onur in Turkish; the document is in US English.

---

## Defaults (built in)

| Item | Value |
|---|---|
| Page | US Letter |
| Title | QUOTATION |
| Units | Imperial — weight lb/ft, length ft, total weight lbs |
| Dates | `October 9, 2026` style; Valid Through = quote date + 30 days |
| Prepared By | Onur H. |
| Company (footer + signature) | Mona Steel LLC · 720 Debra Ln, Anaheim, CA 92680 · (949) 200-3797 · contact@monasteel.com · www.monasteel.com |

The ZIP 92680 came from a web search snippet and was not confirmed against the
website — flag it to Onur if it hasn't been confirmed yet.

**Terms** (order as shown; an empty value keeps the label with a blank line to fill in):

| Key | Default |
|---|---|
| Shipping Terms | *(blank)* |
| Payment Terms | Net 90 days from date of Bill of Lading. |
| Quote Validity | This quotation is valid for 30 days from the date of issue. |
| Lead Time | To be confirmed upon receipt of purchase order. |
| Material | As specified per line item. |
| Tolerances | Dimensional tolerances per ASTM A6/A6M. Weights are theoretical; certified scale weights govern at shipment. |
| Partial Orders | This quotation is based on the full quantity listed. Partial orders are subject to re-quote. |
| Price Adjustment | Prices are subject to adjustment if steel costs change by more than 5%. |
| Bank Details | *(blank)* |

There is deliberately **no Governing Law** row. Override a term only when Onur
asks: `"terms": {"Shipping Terms": "FOB Houston, TX"}`.

---

## Config schema

```json
{
  "language": "en",
  "currency": "USD",
  "customer": "ACME Steel Erectors",
  "attn": "John Smith",
  "offer_no": "0910202626",
  "offer_date": "October 9, 2026",
  "valid_until": "November 8, 2026",
  "prepared_by": "Onur H.",
  "company": {
    "name": "Mona Steel LLC",
    "footer": ["Mona Steel LLC   |   720 Debra Ln, Anaheim, CA 92680",
               "Phone: (949) 200-3797   Email: contact@monasteel.com   www.monasteel.com"]
  },
  "line_items": [
    {"size": "W16 x 67", "shape": "Wide Flange", "grade": "", "lb_ft": 67, "length_ft": 40, "qty": 1, "unit_price": 0}
  ],
  "terms": {}
}
```

Copy `company` exactly from `assets/example_config.json`.

### Line items

- `size` — as written in US practice, e.g. `W16 x 67`
- `shape` — `Wide Flange` for W-shapes (use the common US name for others: Channel, Angle, HSS, Plate…)
- `grade` — only if Onur gives it (e.g. ASTM A992); blank shows "—". You may suggest A992 for W-shapes in chat.
- `lb_ft` — nominal weight per foot. For W/S/M/C/MC shapes it's the number after the
  `x` (W16x67 → 67). For angles, HSS, plate etc. it is not in the name — take it from
  AISC tables and tell Onur the value you used.
- `length_ft`, `qty`
- `unit_price` — USD per piece; `0` = blank. Extended = unit price × qty.

Total Wt. (lbs) = lb_ft × length_ft × qty, computed automatically.

If Onur asks for one length for everything (e.g. "hepsini 40 feet sun"), set every
line to that length; lines that become identical can be merged (sum the qty) — say
so in chat.

---

## Filename & quote number

- `suffix = random.randint(10, 99)`
- Quote No: `DDMMYYYYNN` (e.g. `0910202626`)
- Filename: `MSDDMMYYYYNN.pdf` (e.g. `MS0910202626.pdf`) — no customer or product names.
