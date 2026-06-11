"""parse_data.py — Parse VSTu bi-weekly xlsx report."""
import re
from io import BytesIO
from datetime import datetime
import pandas as pd
import openpyxl


BRANDS = [
    'WEARETHEPRIVATE', 'TRAPPER CLUB', 'FVNXYTHINGS', 'IAMSAIGON',
    'AFTERPARTY', 'FLORALPUNK', 'DEARJOSÉ', 'DEARJOSE', 'BLACKDRP',
    'BLACKORP', 'HIGHCHIC', 'PARADOX', 'MOIDIEN', 'MOIDEN', 'CAOSTU',
    'KANTAN', 'FNOS', 'QEM',
]


# ── helpers ──────────────────────────────────────────────────────────────────

def _v(cell):
    """Safe cell value — return None for empty/whitespace."""
    v = cell.value if hasattr(cell, 'value') else cell
    if v is None:
        return None
    if isinstance(v, str) and not v.strip():
        return None
    return v


def _n(cell, default=0):
    """Numeric cell value."""
    v = _v(cell)
    if v is None:
        return default
    try:
        return float(str(v).replace(',', '').strip())
    except (ValueError, TypeError):
        return default


def _s(cell):
    v = _v(cell)
    return str(v).strip() if v is not None else ''


def find_row(ws, keyword, col_range=8):
    """Find first row where any cell in col_range contains keyword (case-insensitive)."""
    kw = keyword.lower()
    for row in ws.iter_rows():
        for cell in row[:col_range]:
            if cell.value and kw in str(cell.value).lower():
                return cell.row
    return None


def find_col(ws, row_idx, keyword, max_col=30):
    """Find column index in a given row that contains keyword."""
    row = list(ws.iter_rows(min_row=row_idx, max_row=row_idx, values_only=True))[0]
    kw = keyword.lower()
    for i, v in enumerate(row[:max_col]):
        if v and kw in str(v).lower():
            return i + 1  # 1-indexed
    return None


def extract_brand(name):
    upper = str(name).upper()
    for b in BRANDS:
        if b.upper() in upper:
            return b.replace('DEARJOSÉ', 'DEARJOSE').replace('BLACKORP', 'BLACKDRP').replace('MOIDEN', 'MOIDIEN')
    return 'OTHER'


def classify_campaign(campaign_name):
    c = str(campaign_name).lower()
    if 'retarget' in c:
        return 'Retargeting'
    if 'catalogsale' in c or 'catalog' in c:
        return 'Catalog Sale'
    if 'reach' in c:
        return 'Reach'
    if 'engagement' in c or 'engag' in c:
        return 'Engagement'
    if 'visit profile' in c or 'profile' in c:
        return 'Profile Visit'
    return 'Other'


def extract_format(ad_name):
    lower = str(ad_name).lower()
    if 'carousel' in lower:
        return 'Carousel'
    if 'video' in lower:
        return 'Video'
    if 'photo' in lower or 'single photo' in lower or 'multiple photo' in lower:
        return 'Photo'
    return 'Other'


# ── Sheet parsers ─────────────────────────────────────────────────────────────

def parse_media_plan(wb):
    ws = wb['Media Plan  '] if 'Media Plan  ' in wb.sheetnames else wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(values_only=True))

    result = {'total_budget': 0, 'timeline': '', 'channels': {}}

    for row in rows[:10]:
        for i, v in enumerate(row):
            if v and 'budget' in str(v).lower() and i < 5:
                budget_val = row[i + 1] if i + 1 < len(row) else None
                if budget_val and str(budget_val).replace('.', '').isdigit():
                    result['total_budget'] = float(budget_val)
            if v and 'timeline' in str(v).lower() and i < 5:
                tl = row[i + 1] if i + 1 < len(row) else None
                if tl:
                    result['timeline'] = str(tl)

    # Channel rows: R13=IG Reach, R14=IG Engagement, R16=FB Profile Visit
    #               R18=FB Catalog, R19=FB Retargeting, R21=Shopee
    channel_map = {
        'Reach':               (12, 'IG Reach'),       # row 13 → index 12
        'Engagement':          (13, 'IG Engagement'),
        'Profile Visit':       (15, 'FB Profile Visit'),
        'Catalog Sale':        (17, 'FB Catalog Sale'),
        'Dymanic Retargeting': (18, 'FB Retargeting'),
        'GMV Max':             (20, 'Shopee GMV Max'),
    }

    for keyword, (row_idx, label) in channel_map.items():
        if row_idx < len(rows):
            row = rows[row_idx]
            budget = _n(row[6]) if len(row) > 6 else 0
            kpi    = _n(row[11]) if len(row) > 11 else 0
            gmv    = _n(row[22]) if len(row) > 22 else 0
            roas   = _n(row[23]) if len(row) > 23 else 0
            result['channels'][label] = {
                'budget': budget, 'kpi': kpi, 'gmv': gmv, 'roas': roas,
            }

    return result


def parse_overview(wb):
    ws = wb['Overview Report']
    rows = list(ws.iter_rows(values_only=True))

    result = {
        'date_range': '',
        'overall':    [],
        'sale_current': [],
        'sale_prev':    [],
        'comment':      '',
        'total_current': {},
        'total_prev':    {},
    }

    # Date range from R3
    for row in rows[:5]:
        for v in row:
            if v and ('01/' in str(v) or '05/' in str(v)):
                result['date_range'] = str(v).strip()

    # Overall Media Campaign Report — rows 9-18
    # R10: FB Reach, R11: IG Engagement, R13: FB Profile Visit
    # R15: FB Catalog, R16: FB Retargeting, R17: Shopee, R18: Total
    channel_rows = {
        9:  'FB Reach', 10: 'IG Engagement', 12: 'FB Profile Visit',
        14: 'FB Catalog Sale', 15: 'FB Retargeting', 16: 'Shopee GMV Max',
    }
    for idx, label in channel_rows.items():
        if idx < len(rows):
            r = rows[idx]
            result['overall'].append({
                'channel':       label,
                'budget_plan':   _n(r[3]),
                'budget_actual': _n(r[4]),
                'budget_pct':    _n(r[5]),
                'kpi_plan':      _n(r[6]),
                'kpi_actual':    _n(r[7]),
                'kpi_pct':       _n(r[8]),
                'cpr_plan':      _n(r[9]),
                'cpr_actual':    _n(r[10]),
                'ctr_plan':      _n(r[12]),
                'ctr_actual':    _n(r[13]),
            })

    # Total row R18
    if 17 < len(rows):
        r = rows[17]
        result['total_current'] = {
            'budget_plan': _n(r[3]), 'budget_actual': _n(r[4]),
            'budget_pct':  _n(r[5]),
        }

    # Sale Performance current — R34-R37 (index 33-36)
    sale_labels = {33: 'FB Catalog Sale', 34: 'FB Retargeting', 35: 'Shopee'}
    for idx, label in sale_labels.items():
        if idx < len(rows):
            r = rows[idx]
            result['sale_current'].append({
                'channel': label,
                'spend':   _n(r[3]),
                'orders':  _n(r[4]),
                'gmv':     _n(r[5]),
                'roas':    _n(r[6]),
            })
    if 36 < len(rows):
        r = rows[36]
        result['total_current']['spend']  = _n(r[3])
        result['total_current']['orders'] = _n(r[4])
        result['total_current']['gmv']    = _n(r[5])
        result['total_current']['roas']   = _n(r[6])

    # Sale Performance previous — R42-R45 (index 41-44)
    for idx, label in {41: 'FB Catalog Sale', 42: 'FB Retargeting', 43: 'Shopee'}.items():
        if idx < len(rows):
            r = rows[idx]
            result['sale_prev'].append({
                'channel': label,
                'spend':   _n(r[3]),
                'orders':  _n(r[4]),
                'gmv':     _n(r[5]),
                'roas':    _n(r[6]),
            })
    if 44 < len(rows):
        r = rows[44]
        result['total_prev'] = {
            'spend': _n(r[3]), 'orders': _n(r[4]),
            'gmv':   _n(r[5]), 'roas':   _n(r[6]),
        }

    # Comment — find row with 'Comment'
    comment_row = find_row(ws, 'Comment')
    if comment_row:
        comment_lines = []
        for r in ws.iter_rows(min_row=comment_row + 1, max_row=comment_row + 10, values_only=True):
            for v in r:
                if v and str(v).strip():
                    comment_lines.append(str(v).strip())
                    break
        result['comment'] = '\n'.join(comment_lines)

    return result


def parse_branding(wb):
    ws = wb['Branding Campaign']
    rows = list(ws.iter_rows(values_only=True))

    result = {'summary': [], 'top_ads': [], 'comment': ''}

    # R6-R9: Reach, Engagement, Profile Visit, Total (index 5-8)
    labels = {5: 'Reach', 6: 'Engagement', 7: 'Profile Visit', 8: 'Total'}
    for idx, label in labels.items():
        if idx < len(rows):
            r = rows[idx]
            result['summary'].append({
                'type':        label,
                'spend':       _n(r[2]),
                'impressions': _n(r[3]),
                'reach':       _n(r[4]),
                'engagement':  _n(r[5]),
                'followers':   _n(r[6]),
                'clicks':      _n(r[7]),
                'video_views': _n(r[8]),
                'frequency':   _n(r[9]),
            })

    # Top ads: R42-R44 (index 41-43) — 3 ads across columns (col 0, 3, 7)
    if len(rows) > 43:
        for col_start in [0, 3, 7]:
            name_row = rows[41]
            eng_row  = rows[42]
            vtr_row  = rows[43]
            name = _s(name_row[col_start]) if col_start < len(name_row) else ''
            eng  = _n(eng_row[col_start + 1]) if col_start + 1 < len(eng_row) else 0
            vtr  = _n(vtr_row[col_start + 1]) if col_start + 1 < len(vtr_row) else 0
            if name:
                result['top_ads'].append({
                    'name':        name,
                    'brand':       extract_brand(name),
                    'format':      extract_format(name),
                    'engagement':  eng,
                    'vtr':         vtr,
                })

    # Comment
    comment_row = find_row(ws, 'Comment')
    if comment_row:
        r = list(ws.iter_rows(min_row=comment_row, max_row=comment_row, values_only=True))[0]
        for v in r:
            if v and 'comment' not in str(v).lower():
                result['comment'] = str(v).strip()
                break
        if not result['comment']:
            nxt = list(ws.iter_rows(min_row=comment_row, max_row=comment_row, values_only=True))
            if nxt:
                for v in nxt[0]:
                    if v:
                        result['comment'] = str(v).strip()
                        break

    return result


def parse_conversion(wb):
    ws = wb['Conversion Campaign']
    rows = list(ws.iter_rows(values_only=True))

    result = {
        'fb': [], 'shopee_overall': {},
        'mom': {}, 'by_promotion': [], 'by_brand': [],
        'shopee_campaigns': [], 'shopee_top_products': [],
        'shopee_brands': [], 'comment': '',
    }

    # FB Conversion — R8-R10 (index 7-9): Catalog, Retargeting, Total
    fb_labels = {7: 'Catalog Sale', 8: 'Retargeting', 9: 'Total'}
    for idx, label in fb_labels.items():
        if idx < len(rows):
            r = rows[idx]
            result['fb'].append({
                'type':         label,
                'spend':        _n(r[2]),
                'impressions':  _n(r[3]),
                'reach':        _n(r[4]),
                'ctr':          _n(r[5]),
                'pdp_views':    _n(r[6]),
                'a2c_rate':     _n(r[7]),
                'atc':          _n(r[8]),
                'co_rate':      _n(r[9]),
                'checkouts':    _n(r[10]),
                'pur_rate':     _n(r[11]),
                'purchases':    _n(r[12]),
                'cr':           _n(r[13]),
                'cost_per_pur': _n(r[14]),
            })
    # Compute GMV + ROAS from sale_current in overview (passed separately)
    # We'll wire this in app.py after parse_all

    # Shopee overall — R13 (index 12)
    if 12 < len(rows):
        r = rows[12]
        result['shopee_overall'] = {
            'spend': _n(r[2]), 'impressions': _n(r[3]),
            'clicks': _n(r[4]), 'ctr': _n(r[5]),
            'orders': _n(r[6]), 'gmv': _n(r[7]), 'roas': _n(r[8]),
        }

    # MoM comparison — R17-R19 (index 16-18)
    if 18 < len(rows):
        t5 = rows[16]
        t4 = rows[17]
        result['mom'] = {
            't5': {'a2c': _n(t5[1]), 'checkout': _n(t5[2]), 'purchase': _n(t5[3]), 'cr': _n(t5[4])},
            't4': {'a2c': _n(t4[1]), 'checkout': _n(t4[2]), 'purchase': _n(t4[3]), 'cr': _n(t4[4])},
        }

    # Product by promotion — R28-R29 (index 27-28) dynamic
    promo_row = find_row(ws, 'Overall Performance by promotion')
    if promo_row:
        for r in ws.iter_rows(min_row=promo_row + 2, max_row=promo_row + 15, values_only=True):
            name = _s(r[0])
            if not name or name.lower() in ('campaign',):
                continue
            result['by_promotion'].append({
                'campaign':    name,
                'pdp_views':   _n(r[1]),
                'atc_rate':    _n(r[2]),
                'atc':         _n(r[3]),
                'co_rate':     _n(r[4]),
                'checkouts':   _n(r[5]),
                'pur_rate':    _n(r[6]),
                'purchases':   _n(r[7]),
                'gmv':         _n(r[8]),
                'status':      _s(r[9]),
            })

    # Product by brand — dynamic
    brand_row = find_row(ws, 'Overall Performance by brand')
    if brand_row:
        for r in ws.iter_rows(min_row=brand_row + 2, max_row=brand_row + 20, values_only=True):
            name = _s(r[0])
            if not name or name.lower() in ('brand', ''):
                continue
            result['by_brand'].append({
                'brand':     name,
                'pdp_views': _n(r[1]),
                'atc_rate':  _n(r[2]),
                'atc':       _n(r[3]),
                'co_rate':   _n(r[4]),
                'checkouts': _n(r[5]),
                'pur_rate':  _n(r[6]),
                'purchases': _n(r[7]),
                'gmv':       _n(r[8]),
                'status':    _s(r[9]),
            })

    # Shopee Campaigns — dynamic
    camp_row = find_row(ws, 'Shopee Campaign - Campaign Performa')
    if not camp_row:
        camp_row = find_row(ws, 'Campaign Performance')
    if camp_row:
        for r in ws.iter_rows(min_row=camp_row + 2, max_row=camp_row + 20, values_only=True):
            name = _s(r[0])
            if not name or name.lower() in ('campaign', 'total', ''):
                continue
            if 'top product' in name.lower() or 'ad / product' in name.lower():
                break
            result['shopee_campaigns'].append({
                'campaign':   name,
                'impressions': _n(r[1]),
                'clicks':      _n(r[2]),
                'ctr':         _n(r[3]),
                'orders':      _n(r[4]),
                'cr':          _n(r[5]),
                'gmv':         _n(r[6]),
                'spend':       _n(r[7]),
                'roas':        _n(r[8]),
            })

    # Shopee Top Products — dynamic
    top_row = find_row(ws, 'Top Product Perfo')
    if not top_row:
        top_row = find_row(ws, 'Top Product')
    if top_row:
        for r in ws.iter_rows(min_row=top_row + 2, max_row=top_row + 30, values_only=True):
            name = _s(r[0])
            if not name or name.lower() in ('ad / product name', ''):
                continue
            result['shopee_top_products'].append({
                'product':     name,
                'brand':       extract_brand(name),
                'impressions': _n(r[1]),
                'clicks':      _n(r[2]),
                'ctr':         _n(r[3]),
                'orders':      _n(r[4]),
                'spend':       _n(r[5]),
                'gmv':         _n(r[6]),
                'roas':        _n(r[7]),
            })

    # Shopee Brand Performance — dynamic
    brand_shopee_row = find_row(ws, 'Brand Performance - Shopee')
    if not brand_shopee_row:
        brand_shopee_row = find_row(ws, 'Brand Performance')
    if brand_shopee_row:
        for r in ws.iter_rows(min_row=brand_shopee_row + 2, max_row=brand_shopee_row + 20, values_only=True):
            name = _s(r[0])
            if not name or name.lower() in ('brand', 'total', ''):
                continue
            if '\n' in name or 'comment' in name.lower() or len(name) > 30:
                break
            result['shopee_brands'].append({
                'brand':  name,
                'orders': _n(r[1]),
                'gmv':    _n(r[2]),
                'spend':  _n(r[3]),
                'roas':   _n(r[4]),
            })

    return result


def parse_fb_raw(wb):
    """Parse Raw data facebook - content sheet into DataFrame."""
    sheet_name = next((s for s in wb.sheetnames if 'raw data facebook - content' in s.lower()), None)
    if not sheet_name:
        return pd.DataFrame()

    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return pd.DataFrame()

    headers = [str(h).strip() if h else f'col_{i}' for i, h in enumerate(rows[0])]
    data = []
    for row in rows[1:]:
        if any(v is not None for v in row):
            data.append(list(row))

    df = pd.DataFrame(data, columns=headers)

    col_map = {}
    for col in df.columns:
        cl = col.lower()
        if 'ad name' == cl:                              col_map[col] = 'Ad Name'
        elif 'campaign name' == cl:                      col_map[col] = 'Campaign'
        elif 'ad set name' == cl:                        col_map[col] = 'Ad Set'
        elif 'ad delivery' == cl:                        col_map[col] = 'Status'
        elif 'amount spent' in cl:                       col_map[col] = 'Spend'
        elif 'impressions' == cl:                        col_map[col] = 'Impressions'
        elif 'reach' == cl:                              col_map[col] = 'Reach'
        elif 'clicks (all)' == cl:                       col_map[col] = 'Clicks'
        elif 'ctr (all)' == cl:                          col_map[col] = 'CTR'
        elif 'purchases' == cl:                          col_map[col] = 'Purchases'
        elif 'purchases conversion value' in cl:         col_map[col] = 'Revenue'
        elif 'purchase roas' in cl:                      col_map[col] = 'ROAS'
        elif 'adds to cart' == cl:                       col_map[col] = 'ATC'
        elif 'checkouts initiated' == cl:                col_map[col] = 'Checkouts'
        elif 'thruplay' in cl and 'cost' not in cl:      col_map[col] = 'ThruPlays'
        elif 'content views' == cl:                      col_map[col] = 'Content Views'
        elif 'instagram follows' in cl:                  col_map[col] = 'IG Follows'
        elif 'result indicator' == cl:                   col_map[col] = 'Result Type'
        elif 'results' == cl:                            col_map[col] = 'Results'

    df = df.rename(columns=col_map)

    for col in ['Spend', 'Impressions', 'Reach', 'Clicks', 'Purchases', 'Revenue',
                'ROAS', 'ATC', 'Checkouts', 'ThruPlays', 'Content Views', 'Results',
                'IG Follows', 'CTR']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if 'Ad Name' in df.columns:
        df['Brand']  = df['Ad Name'].apply(extract_brand)
        df['Format'] = df['Ad Name'].apply(extract_format)
    if 'Campaign' in df.columns:
        df['Camp Type'] = df['Campaign'].apply(classify_campaign)

    return df


def detect_date_range(wb):
    ws = wb['Overview Report']
    for row in ws.iter_rows(max_row=10, values_only=True):
        for v in row:
            if v and isinstance(v, str):
                m = re.search(r'(\d{1,2})[./](\d{1,2})', v)
                if m:
                    return {'raw': v.strip()}
    return {'raw': ''}


def parse_all(file_bytes):
    wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    plan       = parse_media_plan(wb)
    overview   = parse_overview(wb)
    branding   = parse_branding(wb)
    conversion = parse_conversion(wb)
    fb_raw     = parse_fb_raw(wb)
    date_range = detect_date_range(wb)

    # Wire FB GMV/ROAS from sale_current into conversion
    for item in overview['sale_current']:
        if item['channel'] == 'FB Catalog Sale':
            conversion['fb'][0]['gmv']  = item['gmv']
            conversion['fb'][0]['roas'] = item['roas']
        elif item['channel'] == 'FB Retargeting':
            conversion['fb'][1]['gmv']  = item['gmv']
            conversion['fb'][1]['roas'] = item['roas']

    return {
        'plan':       plan,
        'overview':   overview,
        'branding':   branding,
        'conversion': conversion,
        'fb_raw':     fb_raw,
        'date_range': date_range,
        '_sheets':    wb.sheetnames,
    }
