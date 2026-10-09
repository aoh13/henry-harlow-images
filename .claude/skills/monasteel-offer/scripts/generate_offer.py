"""
Yilmaz Sac Profil — Commercial Offer Generator
================================================
Matches the exact company template (ref: YL1205202633).

Features:
  - Bilingual: language='en' or 'tr'
  - Weight logic BAKED IN: pass profile dimensions, weights auto-calculate
  - Roll-forming strip method (density 7.9 g/cm3)
  - Auto unit-price from rate_usd_per_tonne (or pass unit_price directly, or 0 for blank)
  - Series grouping with subtotals; grand total with FOB port
  - All terms hardcoded with override support; Remarks optional
  - Self-contained: logo lives in ../assets/yilmaz_logo.png

Usage:
    python generate_offer.py --config config.json --output OUT.pdf
"""

import argparse
import json
import os
import re
from itertools import groupby

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, Image, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage

# ── Font registration ────────────────────────────────────────────────────────
# English  -> Helvetica (built-in, matches reference exactly)
# Turkish  -> DejaVu Sans (Unicode, supports ş ı ğ İ ç ü ö)
_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets')

def _register_dejavu():
    """Register DejaVu fonts; return True if all available."""
    reg = {
        'YSans':         'DejaVuSans.ttf',
        'YSans-Bold':    'DejaVuSans-Bold.ttf',
        'YSans-Oblique': 'DejaVuSans-Oblique.ttf',
    }
    ok = True
    for name, fn in reg.items():
        path = os.path.join(_FONT_DIR, fn)
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
            except Exception:
                ok = False
        else:
            ok = False
    return ok

_DEJAVU_OK = _register_dejavu()

def get_fonts(lang):
    """Return (regular, bold, italic) font names for the language."""
    if lang == 'tr' and _DEJAVU_OK:
        return 'YSans', 'YSans-Bold', 'YSans-Oblique'
    return 'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique'

# Module-level default (English/Helvetica); overridden per-build by language
FONT, FONT_B, FONT_I = 'Helvetica', 'Helvetica-Bold', 'Helvetica-Oblique'

# ── Brand colours ───────────────────────────────────────────────────────────
ORANGE   = colors.HexColor('#E8420A')   # exact orange rule colour
NEARBLK  = colors.HexColor('#1A1A1A')   # exact text/fill near-black
DARKGREY = colors.HexColor('#333333')   # table header + grand total fill
MIDGREY  = colors.HexColor('#666666')   # offer-info labels, footer
HDRGREY  = colors.HexColor('#333333')   # table header bg (exact)
GRPGREY  = colors.HexColor('#E8E8E8')   # series group row (exact)
ROWBLUE  = colors.HexColor('#F2F2F2')   # alt row (exact)
LINEGREY = colors.HexColor('#CCCCCC')
WHITE    = colors.white

# ── Paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH  = os.environ.get('LOGO_PATH',
             os.path.join(SCRIPT_DIR, '..', 'assets', 'yilmaz_logo.png'))

# ── Page geometry ───────────────────────────────────────────────────────────
PAGE_W, PAGE_H = A4
ML = MR = 57    # exact: 57pt left/right (table 482pt wide)
MT = 90         # first flowable starts at y=90 (just below top rule at y=85)
MB = 60         # bottom margin for footer
TW = PAGE_W - ML - MR

# Column widths (points) — EXACT from reference YL1205202633 (profile/pcs mode)
COL_W = [19, 37, 87, 37, 65, 31, 36, 39, 64, 67]   # sum = 482pt
_scale = TW / sum(COL_W)
COL_W  = [w * _scale for w in COL_W]

# Tonnage mode: No / Profile / Dimensions / Material / Qty(t) / Unit Price / Total
# Keep same total width 482pt, redistribute
COL_W_T = [28, 105, 80, 95, 48, 62, 64]   # sum = 482pt
_scale_t = TW / sum(COL_W_T)
COL_W_T  = [w * _scale_t for w in COL_W_T]

DENSITY = 7.9  # g/cm3 — company standard, never 7.85


# ════════════════════════════════════════════════════════════════════════════
# WEIGHT LOGIC (baked in — formerly the profile-weight skill)
# ════════════════════════════════════════════════════════════════════════════
def parse_profile(profile: str, section: str):
    """
    Parse a profile string into (sides[], corners) for strip calculation.
    Handles formats like:
      C120x60x15x2.5  -> web,flange,flange,lip,lip  (4 corners)
      C200x80x3.5     -> web,flange,flange           (2 corners, plain C/U)
      U50x35x3        -> web,flange,flange           (2 corners)
      CFU70*50*4      -> web,flange,flange           (2 corners)
      CFC40*30*10*3   -> web,flange,flange,lip,lip   (4 corners)
      CFS160*60*20*2  -> sigma (approx as lipped C)   (4 corners)
      CFO140*120*2    -> closed/omega                  (handled via override)
    Returns (sides, corners) or (None, None) if it can't parse — then
    the caller must supply explicit `sides` and `corners` in the item.
    """
    # Split on x or *
    nums = re.split(r'[x*X]', profile)
    # strip leading letters from first token
    nums[0] = re.sub(r'^[A-Za-z]+', '', nums[0])
    try:
        dims = [float(n) for n in nums if n.strip() != '']
    except ValueError:
        return None, None

    sect = (section or '').upper()
    prof = profile.upper()

    # Determine the family
    is_U = prof.startswith('U') or 'CFU' in prof or sect in ('CFU', 'U', 'U PROFIL', 'U-PROFILE')
    is_C_lipped = (prof.startswith('C') and len(dims) >= 4) or 'CFC' in prof or sect in ('CFC',)
    is_C_plain  = prof.startswith('C') and len(dims) == 3

    # dims layout: [web, flange, (lip), thickness]
    if len(dims) == 4:   # web, flange, lip, t  -> lipped C
        web, flange, lip, t = dims
        sides = [web, flange, flange, lip, lip]
        corners = 4
        return sides, corners
    elif len(dims) == 3: # web, flange, t -> plain U/C
        web, flange, t = dims
        sides = [web, flange, flange]
        corners = 2
        return sides, corners
    elif len(dims) == 5: # web, flange, lip, ?, t — sigma-like; treat extra as a fold
        web, flange, lip, extra, t = dims
        sides = [web, flange, flange, lip, lip]
        corners = 4
        return sides, corners
    return None, None


def strip_width(sides, corners, t):
    return sum(sides) - (corners * 2 * t)


def weight_kg_per_pc(sides, corners, t, length_mm):
    sw = strip_width(sides, corners, t)
    return sw * t * length_mm * DENSITY * 1e-6


def resolve_weight(item):
    """Return (kg_per_pc, total_mt) for a line item."""
    t   = float(item.get('t', 0))
    L   = float(item.get('length_mm', 0))
    qty = int(item.get('qty', 0))

    # explicit sides/corners win
    sides   = item.get('sides')
    corners = item.get('corners')

    if sides is None or corners is None:
        sides, corners = parse_profile(item.get('profile', ''), item.get('section', ''))

    if sides is None:
        return 0.0, 0.0  # cannot compute

    kg = weight_kg_per_pc(sides, corners, t, L)
    mt = kg * qty / 1000
    return kg, mt


# ════════════════════════════════════════════════════════════════════════════
# LANGUAGE LABELS
# ════════════════════════════════════════════════════════════════════════════
LABELS = {
    'en': {
        'title':       'COMMERCIAL OFFER',
        'to':          'To:',
        'attn':        'Attn.:',
        'page_no':     'Page No',
        'offer_date':  'Offer Date',
        'offer_no':    'Offer No',
        'valid_until': 'Valid Until',
        'prepared_by': 'Prepared By',
        'opening':     'Thank you for your inquiry. Please find below our commercial offer for the requested components.',
        'cols': ['No.', 'Part ID', 'Profile', 'Section', 'Material Grade',
                 't (mm)', 'Length\n(mm)', 'Qty\n(pcs)', 'Unit Price\n({u}/pc)', 'Total ({u})'],
        'cols_t': ['No.', 'Profile', 'Dimensions', 'Material Grade',
                   'Qty\n(t)', 'Unit Price\n({u}/t)', 'Total ({u})'],
        'subtotal':    'Subtotal',
        'grand_total': 'GRAND TOTAL — FOB {port}',
        'terms_title': 'TERMS AND CONDITIONS',
        'closing':     'We value your business and look forward to your esteemed order.',
        'auth':        'Authorised by:',
        'cust':        'Customer Approval (Signature & Stamp):',
        'company':     'Yilmaz Sac Profil San. ve Tic. Ltd. Sti.',
    },
    'tr': {
        'title':       'TİCARİ TEKLİF',
        'to':          'Sayın:',
        'attn':        'İlgili:',
        'page_no':     'Sayfa No',
        'offer_date':  'Teklif Tarihi',
        'offer_no':    'Teklif No',
        'valid_until': 'Geçerlilik',
        'prepared_by': 'Hazırlayan',
        'opening':     'Talebiniz için teşekkür ederiz. Aşağıda talep ettiğiniz ürünlere ilişkin ticari teklifimizi bulabilirsiniz.',
        'cols': ['No.', 'Parça No', 'Profil', 'Kesit', 'Malzeme Kalitesi',
                 't (mm)', 'Boy\n(mm)', 'Adet', 'Birim Fiyat\n({u}/adet)', 'Toplam ({u})'],
        'cols_t': ['No.', 'Profil', 'Ölçü', 'Malzeme Kalitesi',
                   'Miktar\n(ton)', 'Birim Fiyat\n({u}/ton)', 'Toplam ({u})'],
        'subtotal':    'Ara Toplam',
        'grand_total': 'GENEL TOPLAM — FOB {port}',
        'terms_title': 'ŞARTLAR VE KOŞULLAR',
        'closing':     'İş birliğiniz için teşekkür eder, değerli siparişlerinizi bekleriz.',
        'auth':        'Yetkili:',
        'cust':        'Müşteri Onayı (İmza & Kaşe):',
        'company':     'Yılmaz Sac Profil San. ve Tic. Ltd. Şti.',
    },
}

# Default terms per language (label, text)
DEFAULT_TERMS = {
    'en': [
        ('Delivery',          'FOB {port}, Turkey.'),
        ('Payment',           '100% within 90 days from date of B/L.'),
        ('Validity',          '30 days from date of issue.'),
        ('Lead Time',         'To be confirmed upon receipt of purchase order.'),
        ('Material & Coating','As specified per line item.'),
        ('Tolerances',        'Dimensional tolerances per EN 10162. Weights are theoretical; '
                              'company scales shall prevail at delivery.'),
        ('Partial Orders',    'This offer is submitted as a whole. Partial orders are subject to re-evaluation.'),
        ('Price Validity',    'Prices are subject to revision if steel material costs fluctuate by more than 5%.'),
        ('Jurisdiction',      'Any disputes shall be subject to the jurisdiction of Kayseri courts, Turkey.'),
        ('Bank Details',      'USD: IBAN TR18 0006 7010 0000 0024 6160 46  \u2022  SWIFT: YAPITRISXXX<br/>'
                              'EUR: IBAN TR79 0006 7010 0000 0024 6714 02  \u2022  SWIFT: YAPITRISXXX'),
    ],
    'tr': [
        ('Teslim',            'FOB {port}, Türkiye.'),
        ('Ödeme',             'Konşimento tarihinden itibaren 90 gün içinde %100.'),
        ('Geçerlilik',        'Teklif tarihinden itibaren 30 gün.'),
        ('Termin',            'Sipariş alındığında teyit edilecektir.'),
        ('Malzeme & Kaplama', 'Her kalem için belirtildiği gibidir.'),
        ('Toleranslar',       'Boyutsal toleranslar EN 10162 standardına göredir. Ağırlıklar teoriktir; '
                              'teslimatta firma kantarı esas alınır.'),
        ('Kısmi Siparişler',  'Bu teklif bir bütün olarak sunulmuştur. Kısmi siparişler yeniden değerlendirmeye tabidir.'),
        ('Fiyat Geçerliliği', 'Çelik hammadde maliyetleri %5\'ten fazla değişirse fiyatlar revize edilebilir.'),
        ('Yetki Mahkemesi',   'Doğabilecek uyuşmazlıklarda Kayseri mahkemeleri yetkilidir.'),
        ('Banka Bilgileri',   'USD: IBAN TR18 0006 7010 0000 0024 6160 46  \u2022  SWIFT: YAPITRISXXX<br/>'
                              'EUR: IBAN TR79 0006 7010 0000 0024 6714 02  \u2022  SWIFT: YAPITRISXXX'),
    ],
}


# ════════════════════════════════════════════════════════════════════════════
# STYLES
# ════════════════════════════════════════════════════════════════════════════
def make_styles():
    def ps(name, bold=False, size=7.5, leading=9.5, color=DARKGREY, align=TA_LEFT, italic=False):
        font = FONT
        if bold: font = FONT_B
        elif italic: font = FONT_I
        return ParagraphStyle(name, fontName=font, fontSize=size, leading=leading,
                              textColor=color, alignment=align)
    return {
        'TH':  ps('TH',  bold=True, size=7, leading=8.5, color=WHITE, align=TA_CENTER),
        'TC':  ps('TC',  size=7, leading=8.5, align=TA_CENTER, color=NEARBLK),
        'TL':  ps('TL',  size=7, leading=8.5, align=TA_LEFT,   color=NEARBLK),
        'TR':  ps('TR',  size=7, leading=8.5, align=TA_RIGHT,  color=NEARBLK),
        'GRP': ps('GRP', bold=True, size=7, leading=8.5, color=NEARBLK, align=TA_LEFT),
        'SUB': ps('SUB', bold=True, size=7, leading=8.5, color=NEARBLK, align=TA_RIGHT),
        'SUBV':ps('SUBV',bold=True, size=7, leading=8.5, color=NEARBLK, align=TA_RIGHT),
        'GTL': ps('GTL', bold=True, size=8, leading=10, color=WHITE, align=TA_CENTER),
        'GTV': ps('GTV', bold=True, size=8, leading=10, color=WHITE, align=TA_RIGHT),
        'TITLE':ps('TITLE', bold=True, size=13, leading=16, color=NEARBLK, align=TA_CENTER),
        'CUST':ps('CUST', bold=True, size=11, leading=14, color=NEARBLK, align=TA_LEFT),
        'LBL': ps('LBL', bold=True, size=8, leading=11, color=NEARBLK, align=TA_LEFT),
        'INF': ps('INF', size=8, leading=11, color=NEARBLK, align=TA_LEFT),
        'INFL':ps('INFL',bold=True, size=8, leading=11, color=MIDGREY, align=TA_LEFT),
        'OPN': ps('OPN', size=8, leading=11, color=NEARBLK, align=TA_LEFT),
        'TKL': ps('TKL', bold=True, size=8, leading=11, color=NEARBLK, align=TA_LEFT),
        'TKV': ps('TKV', size=8, leading=11, color=NEARBLK, align=TA_LEFT),
        'TT':  ps('TT',  bold=True, size=9, leading=12, color=NEARBLK, align=TA_LEFT),
        'CLO': ps('CLO', size=8, leading=11, color=NEARBLK, align=TA_LEFT),
        'SIG': ps('SIG', bold=True, size=8, color=NEARBLK, align=TA_LEFT),
        'SIGC':ps('SIGC',size=7.5, color=NEARBLK, align=TA_LEFT),
    }


def fnum(v, dec=2):
    if not v:
        return '—'
    return f'{v:,.{dec}f}'


# ════════════════════════════════════════════════════════════════════════════
# FOOTER / HEADER CANVAS
# ════════════════════════════════════════════════════════════════════════════
def make_page_decorator(lang, logo_path, logo_w, logo_h):
    L = LABELS[lang]
    def decorate(canvas, doc):
        canvas.saveState()
        H = PAGE_H
        # Coordinates use reportlab origin (bottom-left). Reference uses top-left.
        # Reference (top-left): top rule y=85, bottom rule y=791, x 57..539
        x0, x1 = 57, PAGE_W - 57
        # ── Logo (every page), top-right, right edge at x1 ─────────────────────
        if logo_path and os.path.exists(logo_path):
            lw, lh = logo_w, logo_h
            lx1 = x1
            lx0 = lx1 - lw
            top_y = 40            # top-left y for logo top
            ry = H - (top_y + lh)
            canvas.drawImage(logo_path, lx0, ry, width=lw, height=lh,
                             preserveAspectRatio=True, mask='auto')
        # ── Top orange rule (every page) ───────────────────────────────────────
        canvas.setStrokeColor(ORANGE)
        canvas.setLineWidth(2)
        top_rule_y = H - 85
        canvas.line(x0, top_rule_y, x1, top_rule_y)
        # ── Bottom orange rule + footer ────────────────────────────────────────
        bot_rule_y = H - 791
        canvas.line(x0, bot_rule_y, x1, bot_rule_y)
        canvas.setFont(FONT, 6.5)
        canvas.setFillColor(MIDGREY)
        line1 = ('Yilmaz Sac Profil San. ve Tic. Ltd. Sti.   |   '
                 'Organize Sanayi Bolgesi 18. Cadde No:12, Kayseri, Turkey')
        line2 = ('Tel: +90 352 321 39 99   Fax: +90 352 321 13 66   '
                 'E-Mail: info@yilmazsac.com.tr   www.yilmazsac.com.tr')
        canvas.drawString(x0, bot_rule_y - 11, line1)
        canvas.drawString(x0, bot_rule_y - 21, line2)
        canvas.drawRightString(x1, bot_rule_y - 11, f'Page {doc.page}')
        canvas.restoreState()
    return decorate


# ════════════════════════════════════════════════════════════════════════════
# MAIN BUILD
# ════════════════════════════════════════════════════════════════════════════
def build_offer(config, output_path):
    lang = config.get('language', 'en')
    L    = LABELS.get(lang, LABELS['en'])
    # Select fonts for this language (Helvetica for en, DejaVu for tr)
    global FONT, FONT_B, FONT_I
    FONT, FONT_B, FONT_I = get_fonts(lang)
    S    = make_styles()

    currency = config.get('currency', 'USD')
    cur_sym  = currency  # show "USD"/"EUR" text in headers like reference (EUR/pc)
    port     = config.get('fob_port', 'Diliskelesi')
    rate     = config.get('rate_per_tonne')  # optional global USD/MT or EUR/MT

    customer    = config['customer']
    attn        = config.get('attn', '')
    offer_no    = config['offer_no']
    offer_date  = config.get('offer_date', '')
    valid_until = config.get('valid_until', '')
    prepared_by = config.get('prepared_by', '')
    line_items  = config['line_items']
    overrides   = config.get('terms', {})

    # ── Logo dims ────────────────────────────────────────────────────────────
    if os.path.exists(LOGO_PATH):
        im = PILImage.open(LOGO_PATH)
        iw, ih = im.size
        logo_w = 100          # actual ink width in reference (logo box has padding)
        logo_h = logo_w * ih / iw
    else:
        logo_w = logo_h = 0

    doc = SimpleDocTemplate(output_path, pagesize=A4,
                            leftMargin=ML, rightMargin=MR,
                            topMargin=MT, bottomMargin=MB,
                            title=f'Commercial Offer {offer_no}')
    story = []

    # Logo and top orange rule are drawn on the canvas (see make_page_decorator)
    # at exact reference coordinates. Reserve vertical space so the centered
    # title begins just below the rule (ref: title baseline ~y=98 top-left).
    # topMargin=MT already accounts for some; add spacer to reach title position.
    story.append(Spacer(1, 6))    # title sits just below the rule (y=85)

    # ── Centered title ─────────────────────────────────────────────────────────
    story.append(Paragraph(L['title'], S['TITLE']))
    story.append(Spacer(1, 6*mm))

    # ── Customer block left / offer info right ─────────────────────────────────
    left_block = [
        Paragraph(L['to'], S['LBL']),
        Paragraph(f'<b>{customer}</b>', S['CUST']),
        Spacer(1, 20),                 # gap between customer name and Attn (ref ~29pt)
        Paragraph(L['attn'], S['LBL']),
        Paragraph(attn, S['INF']),
    ]
    info_rows = [
        (L['page_no'], '1 / 1'),
        (L['offer_date'], offer_date),
        (L['offer_no'], offer_no),
        (L['valid_until'], valid_until),
        (L['prepared_by'], prepared_by),
    ]
    # Label col + value col; value starts ~x=437 in reference (right-aligned labels)
    info_tbl = Table(
        [[Paragraph(f'{k}', S['INFL']), Paragraph(f': {v}', S['INF'])] for k, v in info_rows],
        colWidths=[24*mm, 28*mm])
    info_tbl.setStyle(TableStyle([
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
        ('TOPPADDING',(0,0),(-1,-1),1.5),('BOTTOMPADDING',(0,0),(-1,-1),1.5),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
    ]))

    # Push the info block to the right: left col wide, info col narrow & right-positioned
    head2 = Table([[left_block, info_tbl]], colWidths=[TW*0.60, TW*0.40])
    head2.setStyle(TableStyle([
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('ALIGN',(1,0),(1,0),'RIGHT'),     # right-align the info table in its cell
        ('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),
    ]))
    story.append(head2)
    story.append(Spacer(1, 5*mm))

    # ── Opening line ───────────────────────────────────────────────────────────
    story.append(Paragraph(L['opening'], S['OPN']))
    story.append(Spacer(1, 4*mm))

    # ── Products table ─────────────────────────────────────────────────────────
    table_mode = config.get('table_mode', 'profile')   # 'profile' | 'tonnage'
    is_ton = (table_mode == 'tonnage')

    col_src   = L['cols_t'] if is_ton else L['cols']
    col_width = COL_W_T if is_ton else COL_W
    ncol      = len(col_src)
    cols = [c.replace('{u}', cur_sym) for c in col_src]
    header_row = [Paragraph(c.replace('\n', '<br/>'), S['TH']) for c in cols]
    rows = [header_row]
    styles = [
        ('BACKGROUND', (0,0), (-1,0), HDRGREY),
        ('GRID', (0,0), (-1,-1), 0.3, LINEGREY),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 2),
        ('RIGHTPADDING', (0,0), (-1,-1), 2),
    ]

    grand_total = 0.0
    total_mt_all = 0.0
    ridx = 1
    seq = 0

    for series, group in groupby(line_items, key=lambda x: x.get('series', '')):
        group = list(group)
        has_series = bool(series and str(series).strip())
        sub_total = 0.0

        if has_series:
            rows.append([Paragraph(str(series), S['GRP'])] + ['']*(ncol-1))
            styles += [
                ('BACKGROUND', (0,ridx), (-1,ridx), GRPGREY),
                ('SPAN', (0,ridx), (-1,ridx)),
            ]
            ridx += 1

        for item in group:
            seq += 1

            if is_ton:
                qty_t      = float(item.get('qty', 0))       # tonnage
                unit_price = float(item.get('unit_price', 0))  # €/ton
                total      = unit_price * qty_t
                sub_total += total
                rows.append([
                    Paragraph(str(seq), S['TC']),
                    Paragraph(str(item.get('profile','')), S['TL']),
                    Paragraph(str(item.get('dimensions','')), S['TC']),
                    Paragraph(str(item.get('grade','')), S['TC']),
                    Paragraph(fnum(qty_t, 0), S['TC']),
                    Paragraph(fnum(unit_price), S['TR']),
                    Paragraph(fnum(total), S['TR']),
                ])
            else:
                kg, mt = resolve_weight(item)
                total_mt_all += mt
                unit_price = item.get('unit_price')
                if unit_price in (None, 0) and rate and mt:
                    unit_price = kg * rate / 1000
                unit_price = unit_price or 0
                total = unit_price * item.get('qty', 0)
                sub_total += total
                rows.append([
                    Paragraph(str(seq), S['TC']),
                    Paragraph(str(item.get('part_id','')), S['TC']),
                    Paragraph(str(item.get('profile','')), S['TL']),
                    Paragraph(str(item.get('section','')), S['TC']),
                    Paragraph(str(item.get('grade','')), S['TC']),
                    Paragraph(str(item.get('t','')), S['TC']),
                    Paragraph(f"{int(item.get('length_mm',0)):,}", S['TC']),
                    Paragraph(f"{int(item.get('qty',0)):,}", S['TC']),
                    Paragraph(fnum(unit_price), S['TR']),
                    Paragraph(fnum(total), S['TR']),
                ])
            # alt row shading
            if (ridx % 2) == 0:
                styles.append(('BACKGROUND', (0,ridx), (-1,ridx), ROWBLUE))
            ridx += 1

        # subtotal
        label = f"{L['subtotal']} — {series}" if has_series else L['subtotal']
        span_end = ncol - 2
        rows.append(['']*(ncol-2) + [Paragraph(label, S['SUB']), Paragraph(fnum(sub_total), S['SUBV'])])
        styles += [
            ('BACKGROUND', (0,ridx), (-1,ridx), GRPGREY),
            ('LINEABOVE', (0,ridx), (-1,ridx), 0.5, MIDGREY),
            ('LINEBELOW', (0,ridx), (-1,ridx), 0.5, MIDGREY),
            ('SPAN', (0,ridx), (span_end-1, ridx)),
        ]
        ridx += 1
        grand_total += sub_total

    # grand total row (suppressed if show_grand_total = false)
    if config.get('show_grand_total', True):
        rows.append([Paragraph(L['grand_total'].format(port=port.upper()), S['GTL'])] + ['']*(ncol-2) +
                    [Paragraph(f'{cur_sym} {fnum(grand_total)}', S['GTV'])])
        styles += [
            ('BACKGROUND', (0,ridx), (-1,ridx), NEARBLK),
            ('LINEABOVE', (0,ridx), (-1,ridx), 1.5, ORANGE),
            ('SPAN', (0,ridx), (ncol-2, ridx)),
            ('VALIGN', (0,ridx), (-1,ridx), 'MIDDLE'),
        ]

    tbl = Table(rows, colWidths=col_width, repeatRows=1)
    tbl.setStyle(TableStyle(styles))
    story.append(tbl)
    story.append(Spacer(1, 7*mm))

    # ── Terms ──────────────────────────────────────────────────────────────────
    base_terms = DEFAULT_TERMS[lang]
    terms = []
    for k, v in base_terms:
        val = overrides.get(k, v)
        if val and str(val).strip():
            val = str(val).replace('{port}', port)
            terms.append((k, val))
    # extra override keys not in defaults
    base_keys = {k for k, _ in base_terms}
    for k, v in overrides.items():
        if k not in base_keys and k != 'Remarks' and v and str(v).strip():
            terms.append((k, str(v)))
    # Remarks last
    rem = overrides.get('Remarks', '')
    if rem and str(rem).strip():
        rem_label = 'Açıklama' if lang == 'tr' else 'Remarks'
        terms.append((rem_label, str(rem)))

    # Title wrapped in a zero-padding table cell so it aligns exactly to x=57
    # (a bare Paragraph picks up ~6pt of left offset; the table forces flush-left)
    title_tbl = Table([[Paragraph(L['terms_title'], S['TT'])]], colWidths=[TW])
    title_tbl.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(title_tbl)
    story.append(HRFlowable(width=TW, thickness=0.5, color=LINEGREY, spaceBefore=2, spaceAfter=3))

    term_rows = [[Paragraph(k, S['TKL']), Paragraph(v, S['TKV'])] for k, v in terms]
    tt = Table(term_rows, colWidths=[32*mm, TW - 32*mm])
    tt.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('LINEBELOW', (0,0), (-1,-2), 0.3, colors.HexColor('#EEEEEE')),
    ]))
    story.append(tt)
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph(L['closing'], S['CLO']))
    story.append(Spacer(1, 10*mm))

    # ── Signature block ─────────────────────────────────────────────────────────
    gap = 24                      # gap between the two signature lines
    sig_w = (TW - gap) / 2
    sig = Table([
        [Paragraph(L['auth'], S['SIG']), '', Paragraph(L['cust'], S['SIG'])],
        [Spacer(1, 16*mm), '', Spacer(1, 16*mm)],
        [Paragraph(L['company'], S['SIGC']), '', Paragraph('', S['SIGC'])],
    ], colWidths=[sig_w, gap, sig_w])
    sig.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('LINEBELOW', (0,1), (0,1), 0.3, MIDGREY),   # left signature line
        ('LINEBELOW', (2,1), (2,1), 0.3, MIDGREY),   # right signature line
        ('TOPPADDING', (0,2), (-1,2), 3),
    ]))
    story.append(sig)

    decorate = make_page_decorator(lang, LOGO_PATH if logo_w else None, logo_w, logo_h)
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)

    print(f'OK | Grand total: {currency} {grand_total:,.2f} | Total weight: {total_mt_all:,.2f} MT | {output_path}')
    return grand_total, total_mt_all


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--config', required=True)
    ap.add_argument('--output', required=True)
    args = ap.parse_args()
    with open(args.config, encoding='utf-8') as f:
        cfg = json.load(f)
    build_offer(cfg, args.output)
