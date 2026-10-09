"""
Mona Steel quotation — same layout as the Yilmaz offer engine, adapted for the
US market (US Letter, imperial units, US business wording, Mona Steel branding).

Loads the bundled offer engine (generate_offer.py, copied from yilmaz-offer)
and patches it in memory; the engine file itself is never edited.

Usage:
    python build_monasteel.py config.json OUT.pdf
"""
import json, os, sys, types

HERE = os.path.dirname(os.path.abspath(__file__))
SK = HERE   # engine (generate_offer.py) ships next to this script
src = open(SK + '/generate_offer.py', encoding='utf-8').read()


def patch(old, new):
    global src
    assert old in src, f'patch target not found: {old[:60]!r}'
    src = src.replace(old, new)


# ── Brand colour: Mona Steel charcoal (from the logo) instead of Yilmaz orange ─
patch("ORANGE   = colors.HexColor('#E8420A')", "ORANGE   = colors.HexColor('#2D2D2D')")

# ── Page: US Letter, footer rule anchored to the bottom edge ─────────────────
patch('from reportlab.lib.pagesizes import A4', 'from reportlab.lib.pagesizes import letter as A4')
patch('bot_rule_y = H - 791', 'bot_rule_y = 51')

# ── Logo: Mona Steel wordmark (wide), bottom edge level with the Yilmaz logo ──
patch("os.path.join(SCRIPT_DIR, '..', 'assets', 'yilmaz_logo.png'))",
      "os.path.join(HERE, '..', 'assets', 'monasteel_logo.png'))")
patch('logo_w = 100          #', 'logo_w = 165          #')
patch('top_y = 40            #', 'top_y = 70 - lh       #')

# ── Footer company details (filled from config) ─────────────────────────────
patch("""        line1 = ('Yilmaz Sac Profil San. ve Tic. Ltd. Sti.   |   '
                 'Organize Sanayi Bolgesi 18. Cadde No:12, Kayseri, Turkey')
        line2 = ('Tel: +90 352 321 39 99   Fax: +90 352 321 13 66   '
                 'E-Mail: info@yilmazsac.com.tr   www.yilmazsac.com.tr')""",
      """        line1, line2 = FOOTER""")

# ── US wording ───────────────────────────────────────────────────────────────
patch("'title':       'COMMERCIAL OFFER',", "'title':       'QUOTATION',")
patch("'to':          'To:',", "'to':          'Customer:',")
patch("'attn':        'Attn.:',", "'attn':        'Attn:',")
patch("'page_no':     'Page No',", "'page_no':     'Page',")
patch("'offer_date':  'Offer Date',", "'offer_date':  'Quote Date',")
patch("'offer_no':    'Offer No',", "'offer_no':    'Quote No.',")
patch("'valid_until': 'Valid Until',", "'valid_until': 'Valid Through',")
patch("'opening':     'Thank you for your inquiry. Please find below our commercial offer for the requested components.',",
      "'opening':     'Thank you for your inquiry. We are pleased to quote the following material:',")
patch("""        'cols': ['No.', 'Part ID', 'Profile', 'Section', 'Material Grade',
                 't (mm)', 'Length\\n(mm)', 'Qty\\n(pcs)', 'Unit Price\\n({u}/pc)', 'Total ({u})'],""",
      """        'cols': ['No.', 'Size', 'Shape', 'Grade', 'Weight\\n(lb/ft)',
                 'Length\\n(ft)', 'Qty\\n(pcs)', 'Total Wt.\\n(lbs)', 'Unit Price\\n({u}/pc)', 'Extended\\n({u})'],""")
patch("'grand_total': 'GRAND TOTAL — FOB {port}',", "'grand_total': 'TOTAL',")
patch("'closing':     'We value your business and look forward to your esteemed order.',",
      "'closing':     'We appreciate the opportunity to quote and look forward to receiving your order.',")
patch("'auth':        'Authorised by:',", "'auth':        'Authorized By:',")
patch("'cust':        'Customer Approval (Signature & Stamp):',", "'cust':        'Customer Acceptance (Signature & Date):',")
patch("'company':     'Yilmaz Sac Profil San. ve Tic. Ltd. Sti.',", "'company':     COMPANY,")
patch("title=f'Commercial Offer {offer_no}'", "title=f'Quotation {offer_no}'")

# ── Line items in imperial units ────────────────────────────────────────────
patch("""                kg, mt = resolve_weight(item)
                total_mt_all += mt
                unit_price = item.get('unit_price')
                if unit_price in (None, 0) and rate and mt:
                    unit_price = kg * rate / 1000
                unit_price = unit_price or 0""",
      """                lb_ft = float(item.get('lb_ft', 0))
                ft    = float(item.get('length_ft', 0))
                qty   = int(item.get('qty', 0))
                lbs   = lb_ft * ft * qty
                total_mt_all += lbs
                unit_price = item.get('unit_price') or 0""")
patch("""                    Paragraph(str(item.get('part_id','')), S['TC']),
                    Paragraph(str(item.get('profile','')), S['TL']),
                    Paragraph(str(item.get('section','')), S['TC']),
                    Paragraph(str(item.get('grade','')), S['TC']),
                    Paragraph(str(item.get('t','')), S['TC']),
                    Paragraph(f"{int(item.get('length_mm',0)):,}", S['TC']),
                    Paragraph(f"{int(item.get('qty',0)):,}", S['TC']),""",
      """                    Paragraph(str(item.get('size','')), S['TL']),
                    Paragraph(str(item.get('shape','')), S['TC']),
                    Paragraph(str(item.get('grade','')) or '—', S['TC']),
                    Paragraph(f"{lb_ft:g}", S['TC']),
                    Paragraph(f"{ft:g}'", S['TC']),
                    Paragraph(f"{qty:,}", S['TC']),
                    Paragraph(f"{lbs:,.0f}", S['TC']),""")
patch("COL_W = [19, 37, 87, 37, 65, 31, 36, 39, 64, 67]",
      "COL_W = [22, 70, 58, 50, 40, 38, 34, 50, 60, 60]")
patch("Total weight: {total_mt_all:,.2f} MT", "Total weight: {total_mt_all:,.0f} lbs")

# ── Terms: US wording; empty values keep their row so they can be filled in ─
patch("""        if val and str(val).strip():
            val = str(val).replace('{port}', port)
            terms.append((k, val))""",
      """        if val is not None:
            terms.append((k, str(val)))""")
patch("    base_terms = DEFAULT_TERMS[lang]", "    base_terms = US_TERMS")

# ── Signature block kept on one page, tighter spacing (as in the Yilmaz form) ─
patch("    story.append(title_tbl)",
      "    from reportlab.platypus import KeepTogether\n    _ts = len(story)\n    story.append(title_tbl)")
patch("    story.append(tt)\n", "    story.append(tt)\n    story[_ts:] = [KeepTogether(story[_ts:])]\n")
patch("    story.append(Spacer(1, 10*mm))", "    story.append(Spacer(1, 4*mm))")
patch("[Spacer(1, 16*mm), '', Spacer(1, 16*mm)]", "[Spacer(1, 12*mm), '', Spacer(1, 12*mm)]")
patch("    story.append(sig)", "    story.append(KeepTogether([sig]))")
patch("(L['page_no'], '1 / 1'),", "(L['page_no'], PAGES),")


US_TERMS = [
    ('Shipping Terms',  ''),
    ('Payment Terms',   'Net 90 days from date of Bill of Lading.'),
    ('Quote Validity',  'This quotation is valid for 30 days from the date of issue.'),
    ('Lead Time',       'To be confirmed upon receipt of purchase order.'),
    ('Material',        'As specified per line item.'),
    ('Tolerances',      'Dimensional tolerances per ASTM A6/A6M. Weights are theoretical; '
                        'certified scale weights govern at shipment.'),
    ('Partial Orders',  'This quotation is based on the full quantity listed. Partial orders are subject to re-quote.'),
    ('Price Adjustment','Prices are subject to adjustment if steel costs change by more than 5%.'),
    ('Bank Details',    ''),
]


def run(cfg, out):
    from pypdf import PdfReader
    pages = 1
    for _ in range(2):                      # 2nd pass writes the real page count
        g = types.ModuleType('g'); g.__file__ = SK + '/generate_offer.py'
        g.HERE = HERE
        g.PAGES = f'1 / {pages}'
        g.COMPANY = cfg['company']['name']
        g.FOOTER = cfg['company']['footer']
        g.US_TERMS = [(k, cfg.get('terms', {}).get(k, v)) for k, v in US_TERMS]
        exec(compile(src, 'g', 'exec'), g.__dict__)
        g.build_offer(cfg, out)
        pages = len(PdfReader(out).pages)


if __name__ == '__main__':
    with open(sys.argv[1], encoding='utf-8') as f:
        run(json.load(f), sys.argv[2])
