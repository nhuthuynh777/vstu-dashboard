"""parse_data.py — Parse VSTu bi-weekly xlsx report from raw data sheets."""
import re
from io import BytesIO
import pandas as pd
import openpyxl

THB_TO_VND = 830

BRANDS = [
    'WEARETHEPRIVATE', 'TRAPPER CLUB', 'FVNXYTHINGS', 'IAMSAIGON',
    'AFTERPARTY', 'FLORALPUNK', 'DEARJOSÉ', 'DEARJOSE', 'BLACKDRP',
    'BLACKORP', 'HIGHCHIC', 'PARADOX', 'MOIDIEN', 'MOIDEN', 'CAOSTU',
    'KANTAN', 'FNOS', 'QEM',
]

_PREV_KEYWORDS = ('prev', 'apr', 'old', 'last', 'trước', 'truoc', 'march', 'mar',
                  'jan', 'feb', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')


# ── helpers ──────────────────────────────────────────────────────────────────

def _n(v, default=0):
    if v is None:
        return default
    try:
        return float(str(v).replace(',', '').replace('%', '').strip())
    except (ValueError, TypeError):
        return default


def _s(v):
    return str(v).strip() if v is not None else ''


def extract_brand(name):
    upper = str(name).upper()
    for b in BRANDS:
        if b.upper() in upper:
            b_norm = b.replace('DEARJOSÉ', 'DEARJOSE').replace('BLACKORP', 'BLACKDRP').replace('MOIDEN', 'MOIDIEN')
            return b_norm
    return 'OTHER'


def classify_campaign(campaign_name):
    c = str(campaign_name).lower()
    if 'retarget' in c:                          return 'Retargeting'
    if 'catalogsale' in c or 'catalog' in c:     return 'Catalog Sale'
    if 'reach' in c:                             return 'Reach'
    if 'engagement' in c or 'engag' in c:        return 'Engagement'
    if 'visit profile' in c or 'profile' in c:   return 'Profile Visit'
    return 'Other'


def extract_format(ad_name):
    lower = str(ad_name).lower()
    if 'carousel' in lower:    return 'Carousel'
    if 'video' in lower:       return 'Video'
    if 'photo' in lower:       return 'Photo'
    return 'Other'


def _is_prev_sheet(name):
    n = name.lower()
    return any(kw in n for kw in _PREV_KEYWORDS)


# ── Sheet detection ───────────────────────────────────────────────────────────

def _detect_sheets(wb):
    """
    Auto-detect sheet roles by content, not by name.
    Returns dict: {role: sheet_name}
    """
    roles = {
        'media_plan':    None,
        'fb_current':    None,
        'fb_prev':       None,
        'shopee_current': None,
        'shopee_prev':    None,
    }

    for sname in wb.sheetnames:
        ws = wb[sname]
        rows = list(ws.iter_rows(min_row=1, max_row=12, values_only=True))
        flat = ' '.join(str(v).lower() for r in rows for v in r if v)

        # Media Plan
        if roles['media_plan'] is None:
            if 'media plan' in flat or ('budget' in flat and 'channel' in flat and 'kpi' in flat):
                roles['media_plan'] = sname
                continue

        # FB raw: has "ad name" and "amount spent"
        if 'ad name' in flat and 'amount spent' in flat:
            if _is_prev_sheet(sname):
                if roles['fb_prev'] is None:
                    roles['fb_prev'] = sname
            else:
                if roles['fb_current'] is None:
                    roles['fb_current'] = sname
            continue

        # Shopee: has "gmv" + "expense" (both product & campaign sheets)
        if 'gmv' in flat and 'expense' in flat and ('impression' in flat or 'clicks' in flat):
            if _is_prev_sheet(sname):
                if roles['shopee_prev'] is None:
                    roles['shopee_prev'] = sname
            else:
                if roles['shopee_current'] is None:
                    roles['shopee_current'] = sname

    return roles


# ── Media Plan parser ─────────────────────────────────────────────────────────

def parse_media_plan(wb, sheet_name):
    if not sheet_name:
        return {'total_budget': 0, 'timeline': '', 'channels': {}}

    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    result = {'total_budget': 0, 'timeline': '', 'channels': {}}

    for row in rows[:10]:
        for i, v in enumerate(row):
            if v and 'budget' in str(v).lower() and i < 5:
                nxt = row[i + 1] if i + 1 < len(row) else None
                try:
                    result['total_budget'] = float(str(nxt).replace(',', ''))
                except Exception:
                    pass
            if v and 'timeline' in str(v).lower() and i < 5:
                tl = row[i + 1] if i + 1 < len(row) else None
                if tl:
                    result['timeline'] = str(tl).strip()

    # Channel rows: find header row then read data rows
    header_row = None
    for i, row in enumerate(rows):
        flat = ' '.join(str(v).lower() for v in row if v)
        if 'channel' in flat and 'budget' in flat:
            header_row = i
            break

    if header_row is not None:
        channel_map = {
            'reach':               'IG Reach',
            'engagement':          'IG Engagement',
            'profile visit':       'FB Profile Visit',
            'catalog sale':        'FB Catalog Sale',
            'dymanic retargeting': 'FB Retargeting',
            'dynamic retargeting': 'FB Retargeting',
            'gmv max':             'Shopee GMV Max',
            'shopee':              'Shopee GMV Max',
        }
        for row in rows[header_row + 1: header_row + 15]:
            for i, v in enumerate(row):
                if not v:
                    continue
                vl = str(v).lower().strip()
                for key, label in channel_map.items():
                    if key in vl and label not in result['channels']:
                        budget = _n(row[6]) if len(row) > 6 else 0
                        kpi    = _n(row[11]) if len(row) > 11 else 0
                        gmv    = _n(row[22]) if len(row) > 22 else 0
                        if budget > 0:
                            result['channels'][label] = {
                                'budget': budget, 'kpi': kpi, 'gmv': gmv,
                            }
                        break

    return result


# ── FB raw parser ─────────────────────────────────────────────────────────────

def _parse_fb_sheet(wb, sheet_name):
    """Parse a FB raw sheet into a cleaned DataFrame."""
    if not sheet_name or sheet_name not in wb.sheetnames:
        return pd.DataFrame()

    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))

    # Find header row (has "ad name" and "amount spent")
    header_idx = None
    for i, row in enumerate(rows[:10]):
        flat = ' '.join(str(v).lower() for v in row if v)
        if 'ad name' in flat and 'amount spent' in flat:
            header_idx = i
            break
    if header_idx is None:
        return pd.DataFrame()

    headers = [str(h).strip() if h else f'col_{i}' for i, h in enumerate(rows[header_idx])]
    data = [list(r) for r in rows[header_idx + 1:] if any(v is not None for v in r)]
    df = pd.DataFrame(data, columns=headers)

    col_map = {}
    for col in df.columns:
        cl = col.lower().strip()
        if cl == 'ad name':                                  col_map[col] = 'Ad Name'
        elif cl == 'campaign name':                          col_map[col] = 'Campaign'
        elif cl == 'ad set name':                            col_map[col] = 'Ad Set'
        elif cl == 'ad delivery':                            col_map[col] = 'Status'
        elif 'amount spent' in cl:                           col_map[col] = 'Spend'
        elif cl == 'impressions':                            col_map[col] = 'Impressions'
        elif cl == 'reach':                                  col_map[col] = 'Reach'
        elif cl == 'clicks (all)':                           col_map[col] = 'Clicks'
        elif cl == 'ctr (all)':                              col_map[col] = 'CTR'
        elif cl == 'purchases':                              col_map[col] = 'Purchases'
        elif 'purchases conversion value' in cl:             col_map[col] = 'Revenue'
        elif 'purchase roas' in cl:                          col_map[col] = 'ROAS'
        elif cl == 'adds to cart':                           col_map[col] = 'ATC'
        elif cl == 'checkouts initiated':                    col_map[col] = 'Checkouts'
        elif 'thruplay' in cl and 'cost' not in cl:          col_map[col] = 'ThruPlays'
        elif cl == 'content views':                          col_map[col] = 'Content Views'
        elif 'instagram follows' in cl:                      col_map[col] = 'IG Follows'
        elif cl == 'result indicator':                       col_map[col] = 'Result Type'
        elif cl == 'results':                                col_map[col] = 'Results'

    df = df.rename(columns=col_map)

    num_cols = ['Spend', 'Impressions', 'Reach', 'Clicks', 'Purchases', 'Revenue',
                'ROAS', 'ATC', 'Checkouts', 'ThruPlays', 'Content Views',
                'Results', 'IG Follows', 'CTR']
    for col in num_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    if 'Ad Name' in df.columns:
        df['Brand']      = df['Ad Name'].apply(extract_brand)
        df['Format']     = df['Ad Name'].apply(extract_format)
    if 'Campaign' in df.columns:
        df['Camp Type']  = df['Campaign'].apply(classify_campaign)

    return df


# ── Shopee raw parsers ────────────────────────────────────────────────────────

def _parse_shopee_sheet(wb, sheet_name):
    """
    Parse Shopee raw sheet (campaign-level hoặc product-level đều được).
    Returns cleaned DataFrame (VNĐ) với columns chuẩn hóa.
    """
    if not sheet_name or sheet_name not in wb.sheetnames:
        return pd.DataFrame()

    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))

    # Find header row: has 'gmv' and 'expense'
    header_idx = None
    for i, row in enumerate(rows[:15]):
        flat = ' '.join(str(v).lower() for v in row if v)
        if 'gmv' in flat and 'expense' in flat and ('impression' in flat or 'clicks' in flat):
            header_idx = i
            break
    if header_idx is None:
        return pd.DataFrame()

    # De-duplicate headers before building DataFrame
    raw_headers = [str(h).strip() if h else f'col_{i}' for i, h in enumerate(rows[header_idx])]
    seen = {}
    headers = []
    for h in raw_headers:
        if h in seen:
            seen[h] += 1
            headers.append(f'{h}_{seen[h]}')
        else:
            seen[h] = 0
            headers.append(h)

    data = [list(r) for r in rows[header_idx + 1:] if any(v is not None for v in r)]
    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data, columns=headers)

    # Map to canonical names — use FIRST occurrence of each concept
    col_map = {}
    mapped = set()

    for col in df.columns:
        cl = col.lower().strip().rstrip('_0123456789')
        if ('ad / product name' in cl or 'ad name' == cl) and 'name' not in mapped:
            col_map[col] = 'name'; mapped.add('name')
        elif cl in ('impression', 'impressions') and 'impressions' not in mapped:
            col_map[col] = 'impressions'; mapped.add('impressions')
        elif cl == 'clicks' and 'clicks' not in mapped:
            col_map[col] = 'clicks'; mapped.add('clicks')
        elif cl == 'ctr' and 'ctr' not in mapped:
            col_map[col] = 'ctr'; mapped.add('ctr')
        elif cl == 'items sold' and 'orders' not in mapped:
            col_map[col] = 'orders'; mapped.add('orders')
        elif cl == 'conversions' and 'orders' not in mapped:
            col_map[col] = 'orders'; mapped.add('orders')
        elif cl == 'gmv' and 'gmv_thb' not in mapped:
            col_map[col] = 'gmv_thb'; mapped.add('gmv_thb')
        elif cl == 'expense' and 'spend_thb' not in mapped:
            col_map[col] = 'spend_thb'; mapped.add('spend_thb')
        elif cl == 'roas' and 'roas' not in mapped:
            col_map[col] = 'roas'; mapped.add('roas')
        elif cl in ('status', 'ad status') and 'status' not in mapped:
            col_map[col] = 'status'; mapped.add('status')

    df = df.rename(columns=col_map)

    # Parse numeric columns
    for col in ['impressions', 'clicks', 'orders', 'gmv_thb', 'spend_thb', 'roas']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if 'ctr' in df.columns:
        df['ctr'] = df['ctr'].apply(
            lambda x: _n(str(x).replace('%', '')) / 100
            if isinstance(x, str) and '%' in str(x) else _n(x)
        )

    # Convert THB → VNĐ
    if 'gmv_thb'   in df.columns: df['gmv']   = df['gmv_thb']   * THB_TO_VND
    if 'spend_thb' in df.columns: df['spend'] = df['spend_thb'] * THB_TO_VND

    # Recompute ROAS
    if 'gmv' in df.columns and 'spend' in df.columns:
        df['roas'] = df.apply(lambda r: r['gmv'] / r['spend'] if r['spend'] > 0 else 0, axis=1)

    # Drop empty / sequence-number rows
    if 'name' in df.columns:
        df = df[df['name'].apply(lambda x: bool(_s(x)) and not str(x).replace('.', '').isdigit())]
        df['brand'] = df['name'].apply(extract_brand)

    return df.reset_index(drop=True)


# ── Aggregate from raw ────────────────────────────────────────────────────────

def _agg_branding(df_fb):
    """Compute branding summary from raw FB DataFrame."""
    if df_fb.empty or 'Camp Type' not in df_fb.columns:
        return {'summary': [], 'top_ads': []}

    summary = []
    for camp_type, label in [('Reach', 'Reach'), ('Engagement', 'Engagement'), ('Profile Visit', 'Profile Visit')]:
        sub = df_fb[df_fb['Camp Type'] == camp_type]
        reach = sub['Reach'].sum() if 'Reach' in sub.columns else 0
        imps  = sub['Impressions'].sum() if 'Impressions' in sub.columns else 0
        summary.append({
            'type':        label,
            'spend':       sub['Spend'].sum() if 'Spend' in sub.columns else 0,
            'impressions': imps,
            'reach':       reach,
            'engagement':  sub['Results'].sum() if camp_type == 'Engagement' and 'Results' in sub.columns else 0,
            'followers':   sub['IG Follows'].sum() if 'IG Follows' in sub.columns else 0,
            'clicks':      sub['Clicks'].sum() if 'Clicks' in sub.columns else 0,
            'video_views': sub['ThruPlays'].sum() if 'ThruPlays' in sub.columns else 0,
            'frequency':   imps / reach if reach > 0 else 0,
        })

    sub_all = df_fb[df_fb['Camp Type'].isin(['Reach', 'Engagement', 'Profile Visit'])]
    reach_t = sub_all['Reach'].sum() if 'Reach' in sub_all.columns else 0
    imps_t  = sub_all['Impressions'].sum() if 'Impressions' in sub_all.columns else 0
    summary.append({
        'type':        'Total',
        'spend':       sub_all['Spend'].sum() if 'Spend' in sub_all.columns else 0,
        'impressions': imps_t,
        'reach':       reach_t,
        'engagement':  df_fb[df_fb['Camp Type'] == 'Engagement']['Results'].sum()
                       if 'Results' in df_fb.columns else 0,
        'followers':   sub_all['IG Follows'].sum() if 'IG Follows' in sub_all.columns else 0,
        'clicks':      sub_all['Clicks'].sum() if 'Clicks' in sub_all.columns else 0,
        'video_views': sub_all['ThruPlays'].sum() if 'ThruPlays' in sub_all.columns else 0,
        'frequency':   imps_t / reach_t if reach_t > 0 else 0,
    })

    # Top 3 ads by engagement
    top_ads = []
    eng_df = df_fb[df_fb['Camp Type'] == 'Engagement'].copy()
    if not eng_df.empty and 'Ad Name' in eng_df.columns:
        agg_cols = {c: 'sum' for c in ['Results', 'ThruPlays', 'Impressions', 'Spend'] if c in eng_df.columns}
        eng_agg = eng_df.groupby('Ad Name').agg(agg_cols).reset_index()
        eng_agg['vtr'] = eng_agg.apply(
            lambda r: r.get('ThruPlays', 0) / r['Impressions'] if r.get('Impressions', 0) > 0 else 0, axis=1
        )
        for _, row in eng_agg.sort_values('Results', ascending=False).head(3).iterrows():
            top_ads.append({
                'name':       row['Ad Name'],
                'brand':      extract_brand(row['Ad Name']),
                'format':     extract_format(row['Ad Name']),
                'engagement': row.get('Results', 0),
                'vtr':        row.get('vtr', 0),
                'spend':      row.get('Spend', 0),
            })

    return {'summary': summary, 'top_ads': top_ads}


def _agg_conversion(df_fb):
    """Compute FB conversion funnel from raw FB DataFrame."""
    if df_fb.empty or 'Camp Type' not in df_fb.columns:
        return []

    result = []
    for camp_type, label in [('Catalog Sale', 'Catalog Sale'), ('Retargeting', 'Retargeting')]:
        sub = df_fb[df_fb['Camp Type'] == camp_type]
        spend     = sub['Spend'].sum() if 'Spend' in sub.columns else 0
        pdp_views = sub['Content Views'].sum() if 'Content Views' in sub.columns else 0
        atc       = sub['ATC'].sum() if 'ATC' in sub.columns else 0
        checkouts = sub['Checkouts'].sum() if 'Checkouts' in sub.columns else 0
        purchases = sub['Purchases'].sum() if 'Purchases' in sub.columns else 0
        revenue   = sub['Revenue'].sum() if 'Revenue' in sub.columns else 0
        imps      = sub['Impressions'].sum() if 'Impressions' in sub.columns else 0
        reach     = sub['Reach'].sum() if 'Reach' in sub.columns else 0
        roas      = revenue / spend if spend > 0 else 0
        cr        = purchases / pdp_views if pdp_views > 0 else 0
        result.append({
            'type':         label,
            'spend':        spend,
            'impressions':  imps,
            'reach':        reach,
            'ctr':          sub['CTR'].mean() if 'CTR' in sub.columns and len(sub) else 0,
            'pdp_views':    pdp_views,
            'a2c_rate':     atc / pdp_views if pdp_views > 0 else 0,
            'atc':          atc,
            'co_rate':      checkouts / atc if atc > 0 else 0,
            'checkouts':    checkouts,
            'pur_rate':     purchases / checkouts if checkouts > 0 else 0,
            'purchases':    purchases,
            'cr':           cr,
            'cost_per_pur': spend / purchases if purchases > 0 else 0,
            'gmv':          revenue,
            'roas':         roas,
        })

    # Total row
    sub_all = df_fb[df_fb['Camp Type'].isin(['Catalog Sale', 'Retargeting'])]
    total_spend = sub_all['Spend'].sum() if 'Spend' in sub_all.columns else 0
    total_pdp   = sub_all['Content Views'].sum() if 'Content Views' in sub_all.columns else 0
    total_atc   = sub_all['ATC'].sum() if 'ATC' in sub_all.columns else 0
    total_co    = sub_all['Checkouts'].sum() if 'Checkouts' in sub_all.columns else 0
    total_pur   = sub_all['Purchases'].sum() if 'Purchases' in sub_all.columns else 0
    total_rev   = sub_all['Revenue'].sum() if 'Revenue' in sub_all.columns else 0
    result.append({
        'type':         'Total',
        'spend':        total_spend,
        'impressions':  sub_all['Impressions'].sum() if 'Impressions' in sub_all.columns else 0,
        'reach':        sub_all['Reach'].sum() if 'Reach' in sub_all.columns else 0,
        'pdp_views':    total_pdp,
        'a2c_rate':     total_atc / total_pdp if total_pdp > 0 else 0,
        'atc':          total_atc,
        'co_rate':      total_co / total_atc if total_atc > 0 else 0,
        'checkouts':    total_co,
        'pur_rate':     total_pur / total_co if total_co > 0 else 0,
        'purchases':    total_pur,
        'cr':           total_pur / total_pdp if total_pdp > 0 else 0,
        'cost_per_pur': total_spend / total_pur if total_pur > 0 else 0,
        'gmv':          total_rev,
        'roas':         total_rev / total_spend if total_spend > 0 else 0,
    })
    return result


def _agg_shopee_brands(df_prod):
    """Aggregate Shopee product data by brand."""
    if df_prod.empty or 'brand' not in df_prod.columns:
        return []
    agg = df_prod.groupby('brand').agg(
        orders=('orders', 'sum'),
        gmv=('gmv', 'sum'),
        spend=('spend', 'sum'),
    ).reset_index()
    agg['roas'] = agg.apply(lambda r: r['gmv'] / r['spend'] if r['spend'] > 0 else 0, axis=1)
    return agg.sort_values('gmv', ascending=False).to_dict('records')


def _agg_sale_summary(df_fb, df_shopeeamp):
    """Compute overall sale performance (for Overview tab)."""
    result = {'channels': [], 'total': {}}

    fb_conv = df_fb[df_fb['Camp Type'].isin(['Catalog Sale', 'Retargeting'])] if not df_fb.empty else pd.DataFrame()
    for camp_type, label in [('Catalog Sale', 'FB Catalog Sale'), ('Retargeting', 'FB Retargeting')]:
        sub = fb_conv[fb_conv['Camp Type'] == camp_type] if not fb_conv.empty else pd.DataFrame()
        result['channels'].append({
            'channel': label,
            'spend':   sub['Spend'].sum() if not sub.empty and 'Spend' in sub.columns else 0,
            'orders':  sub['Purchases'].sum() if not sub.empty and 'Purchases' in sub.columns else 0,
            'gmv':     sub['Revenue'].sum() if not sub.empty and 'Revenue' in sub.columns else 0,
        })

    shopee_spend  = df_shopeeamp['spend'].sum()  if not df_shopeeamp.empty and 'spend'  in df_shopeeamp.columns else 0
    shopee_orders = df_shopeeamp['orders'].sum() if not df_shopeeamp.empty and 'orders' in df_shopeeamp.columns else 0
    shopee_gmv    = df_shopeeamp['gmv'].sum()    if not df_shopeeamp.empty and 'gmv'    in df_shopeeamp.columns else 0
    # Note: df_shopeeamp is the combined Shopee sheet (name col, not campaign col)
    result['channels'].append({
        'channel': 'Shopee', 'spend': shopee_spend,
        'orders': shopee_orders, 'gmv': shopee_gmv,
    })

    for ch in result['channels']:
        ch['roas'] = ch['gmv'] / ch['spend'] if ch['spend'] > 0 else 0

    result['total'] = {
        'spend':  sum(c['spend']  for c in result['channels']),
        'orders': sum(c['orders'] for c in result['channels']),
        'gmv':    sum(c['gmv']    for c in result['channels']),
    }
    total_spend = result['total']['spend']
    result['total']['roas'] = result['total']['gmv'] / total_spend if total_spend > 0 else 0
    return result


def _mom_from_raw(df_fb_prev, df_shopee_prev):
    """Compute previous period totals for MoM comparison."""
    if df_fb_prev.empty and df_shopee_prev.empty:
        return {}

    fb_conv = df_fb_prev[df_fb_prev['Camp Type'].isin(['Catalog Sale', 'Retargeting'])] \
              if not df_fb_prev.empty and 'Camp Type' in df_fb_prev.columns else pd.DataFrame()
    channels = []
    for camp_type, label in [('Catalog Sale', 'FB Catalog Sale'), ('Retargeting', 'FB Retargeting')]:
        sub = fb_conv[fb_conv['Camp Type'] == camp_type] if not fb_conv.empty else pd.DataFrame()
        channels.append({
            'channel': label,
            'spend':  sub['Spend'].sum()    if not sub.empty and 'Spend'    in sub.columns else 0,
            'orders': sub['Purchases'].sum() if not sub.empty and 'Purchases' in sub.columns else 0,
            'gmv':    sub['Revenue'].sum()  if not sub.empty and 'Revenue'  in sub.columns else 0,
        })

    sp = df_shopee_prev['spend'].sum()  if not df_shopee_prev.empty and 'spend'  in df_shopee_prev.columns else 0
    or_ = df_shopee_prev['orders'].sum() if not df_shopee_prev.empty and 'orders' in df_shopee_prev.columns else 0
    gm = df_shopee_prev['gmv'].sum()    if not df_shopee_prev.empty and 'gmv'    in df_shopee_prev.columns else 0
    channels.append({'channel': 'Shopee', 'spend': sp, 'orders': or_, 'gmv': gm})

    for ch in channels:
        ch['roas'] = ch['gmv'] / ch['spend'] if ch['spend'] > 0 else 0

    total_spend = sum(c['spend'] for c in channels)
    total = {
        'spend':  total_spend,
        'orders': sum(c['orders'] for c in channels),
        'gmv':    sum(c['gmv']    for c in channels),
        'roas':   sum(c['gmv'] for c in channels) / total_spend if total_spend > 0 else 0,
    }
    return {'channels': channels, 'total': total}


def _detect_date_range(df_fb):
    """Extract date range from FB raw data."""
    if df_fb.empty:
        return {'raw': ''}
    for col in df_fb.columns:
        if 'reporting starts' in col.lower() or col.lower() == 'reporting starts':
            vals = df_fb[col].dropna()
            if len(vals):
                start = str(vals.iloc[0])[:10]
                end   = str(df_fb[df_fb.columns[df_fb.columns.str.lower().str.contains('end')]
                                  .tolist()[0] if any(df_fb.columns.str.lower().str.contains('end')) else col]
                            .dropna().iloc[-1])[:10] if len(vals) > 1 else start
                return {'raw': f'{start} – {end}'}
    return {'raw': ''}


# ── Main entry point ─────────────────────────────────────────────────────────

def parse_all(file_bytes):
    wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    roles = _detect_sheets(wb)

    plan         = parse_media_plan(wb, roles['media_plan'])
    df_fb        = _parse_fb_sheet(wb, roles['fb_current'])
    df_fb_prev   = _parse_fb_sheet(wb, roles['fb_prev'])
    df_shopee    = _parse_shopee_sheet(wb, roles['shopee_current'])
    df_shopee_p  = df_shopee   # same sheet, brand col already extracted
    df_shopeep = _parse_shopee_sheet(wb, roles['shopee_prev'])

    branding   = _agg_branding(df_fb)
    fb_conv    = _agg_conversion(df_fb)
    sale       = _agg_sale_summary(df_fb, df_shopee)
    sale_prev  = _mom_from_raw(df_fb_prev, df_shopeep)

    # Shopee campaign list — each row is one ad/campaign
    shopee_campaigns = []
    if not df_shopee.empty and 'name' in df_shopee.columns:
        for _, row in df_shopee.iterrows():
            shopee_campaigns.append({
                'campaign':    str(row.get('name', '')),
                'impressions': row.get('impressions', 0),
                'clicks':      row.get('clicks', 0),
                'ctr':         row.get('ctr', 0),
                'orders':      row.get('orders', 0),
                'cr':          row.get('orders', 0) / row.get('clicks', 1) if row.get('clicks') else 0,
                'gmv':         row.get('gmv', 0),
                'spend':       row.get('spend', 0),
                'roas':        row.get('roas', 0),
            })

    # Shopee top products
    shopee_top_products = []
    if not df_shopee_p.empty and 'product' in df_shopee_p.columns:
        for _, row in df_shopee_p.sort_values('gmv', ascending=False).head(25).iterrows():
            shopee_top_products.append({
                'product':     str(row.get('product', '')),
                'brand':       str(row.get('brand', 'OTHER')),
                'impressions': row.get('impressions', 0),
                'clicks':      row.get('clicks', 0),
                'ctr':         row.get('ctr', 0),
                'orders':      row.get('orders', 0),
                'spend':       row.get('spend', 0),
                'gmv':         row.get('gmv', 0),
                'roas':        row.get('roas', 0),
            })

    shopee_brands = _agg_shopee_brands(df_shopee_p)

    # MoM funnel rates from FB raw
    mom_funnel = {}
    if not df_fb.empty and not df_fb_prev.empty:
        def _funnel_rates(df):
            sub = df[df['Camp Type'].isin(['Catalog Sale', 'Retargeting'])] \
                  if 'Camp Type' in df.columns else pd.DataFrame()
            pdp = sub['Content Views'].sum() if 'Content Views' in sub.columns else 0
            atc = sub['ATC'].sum()           if 'ATC'           in sub.columns else 0
            co  = sub['Checkouts'].sum()     if 'Checkouts'     in sub.columns else 0
            pur = sub['Purchases'].sum()     if 'Purchases'     in sub.columns else 0
            return {
                'a2c':      atc / pdp if pdp > 0 else 0,
                'checkout': co  / atc if atc > 0 else 0,
                'purchase': pur / co  if co  > 0 else 0,
                'cr':       pur / pdp if pdp > 0 else 0,
            }
        mom_funnel = {
            't_current': _funnel_rates(df_fb),
            't_prev':    _funnel_rates(df_fb_prev),
        }

    return {
        'plan':     plan,
        'overview': {
            'sale_current': sale['channels'],
            'sale_prev':    sale_prev.get('channels', []),
            'total_current': sale['total'],
            'total_prev':    sale_prev.get('total', {}),
            'date_range':    '',
            'overall':       _build_overall_table(plan, sale, branding, fb_conv),
        },
        'branding':   branding,
        'conversion': {
            'fb':              fb_conv,
            'shopee_overall':  {
                'spend':  df_shopee['spend'].sum()  if not df_shopee.empty and 'spend'  in df_shopee.columns else 0,
                'orders': df_shopee['orders'].sum() if not df_shopee.empty and 'orders' in df_shopee.columns else 0,
                'gmv':    df_shopee['gmv'].sum()    if not df_shopee.empty and 'gmv'    in df_shopee.columns else 0,
                'roas':   0,
                'clicks': df_shopee['clicks'].sum() if not df_shopee.empty and 'clicks' in df_shopee.columns else 0,
                'impressions': df_shopee['impressions'].sum() if not df_shopee.empty and 'impressions' in df_shopee.columns else 0,
                'ctr':    0,
            },
            'mom':             mom_funnel,
            'by_promotion':    [],
            'by_brand':        [],
            'shopee_campaigns':    shopee_campaigns,
            'shopee_top_products': shopee_top_products,
            'shopee_brands':       shopee_brands,
        },
        'fb_raw':     df_fb,
        'date_range': _detect_date_range(df_fb),
        '_roles':     roles,
        '_sheets':    wb.sheetnames,
    }


def _build_overall_table(plan, sale, branding, fb_conv):
    """Build plan vs actual rows for Overview tab."""
    rows = []
    ch_plan = plan.get('channels', {})
    br_sum  = {s['type']: s for s in branding.get('summary', [])}
    fb_dict = {f['type']: f for f in fb_conv}

    mapping = [
        ('FB Reach',        'IG Reach',         br_sum.get('Reach', {}),         None),
        ('IG Engagement',   'IG Engagement',     br_sum.get('Engagement', {}),    None),
        ('FB Profile Visit','FB Profile Visit',  br_sum.get('Profile Visit', {}), None),
        ('FB Catalog Sale', 'FB Catalog Sale',   fb_dict.get('Catalog Sale', {}), fb_dict.get('Catalog Sale', {})),
        ('FB Retargeting',  'FB Retargeting',    fb_dict.get('Retargeting', {}),  fb_dict.get('Retargeting', {})),
        ('Shopee GMV Max',  'Shopee GMV Max',    {}, None),
    ]

    # Wire Shopee from sale channels
    shopee_sale = next((c for c in sale['channels'] if c['channel'] == 'Shopee'), {})

    for label, plan_key, actual_data, conv_data in mapping:
        p = ch_plan.get(plan_key, {})
        if label == 'Shopee GMV Max':
            actual_spend = shopee_sale.get('spend', 0)
            actual_kpi   = shopee_sale.get('orders', 0)
            kpi_plan     = p.get('kpi', 0)
        elif label in ('FB Catalog Sale', 'FB Retargeting'):
            actual_spend = actual_data.get('spend', 0)
            actual_kpi   = actual_data.get('purchases', 0)
            kpi_plan     = p.get('kpi', 0)
        else:
            actual_spend = actual_data.get('spend', 0)
            actual_kpi   = actual_data.get('impressions', actual_data.get('reach', actual_data.get('clicks', 0)))
            kpi_plan     = p.get('kpi', 0)

        rows.append({
            'channel':        label,
            'budget_plan':    p.get('budget', 0),
            'budget_actual':  actual_spend,
            'budget_pct':     actual_spend / p.get('budget', 1) if p.get('budget') else 0,
            'kpi_plan':       kpi_plan,
            'kpi_actual':     actual_kpi,
            'kpi_pct':        actual_kpi / kpi_plan if kpi_plan > 0 else 0,
            'cpr_plan':       0,
            'cpr_actual':     0,
        })
    return rows
