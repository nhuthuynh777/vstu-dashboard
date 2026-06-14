import streamlit as st
import plotly.graph_objects as go
from helpers import (kpi_html, kpi_grid, html_table, section,
                     badge, roas_badge, fmt_vnd, fmt_num, C)
import pandas as pd


BRAND_COLORS = {
    'CAOSTU': C['accent'], 'HIGHCHIC': C['pink'], 'FNOS': C['blue'],
    'IAMSAIGON': C['yellow'], 'PARADOX': C['purple'], 'KANTAN': C['green'],
    'WEARETHEPRIVATE': '#888', 'TRAPPER CLUB': '#999',
}


def render(data):
    st.markdown("## Content Performance — Ad Level")

    df = data.get('fb_raw', pd.DataFrame())
    if df.empty or 'Ad Name' not in df.columns:
        st.info("Không có raw FB data.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        all_types = ['All'] + sorted(df['Camp Type'].unique().tolist()) if 'Camp Type' in df.columns else ['All']
        f_type = st.selectbox('Campaign Type', all_types, key='ct_type')
    with col_f2:
        all_brands = ['All'] + sorted(df['Brand'].unique().tolist()) if 'Brand' in df.columns else ['All']
        f_brand = st.selectbox('Brand', all_brands, key='ct_brand')
    with col_f3:
        all_status = ['All'] + sorted(df['Status'].dropna().unique().tolist()) if 'Status' in df.columns else ['All']
        f_status = st.selectbox('Status', all_status, key='ct_status')

    dff = df.copy()
    if f_type   != 'All' and 'Camp Type' in dff.columns: dff = dff[dff['Camp Type'] == f_type]
    if f_brand  != 'All' and 'Brand'     in dff.columns: dff = dff[dff['Brand'] == f_brand]
    if f_status != 'All' and 'Status'    in dff.columns: dff = dff[dff['Status'] == f_status]

    st.markdown(
        f'<div style="color:#64748B;font-size:12px;margin-bottom:12px">'
        f'{len(dff)} ads · {dff["Brand"].nunique() if "Brand" in dff.columns else "—"} brands</div>',
        unsafe_allow_html=True
    )

    # ── KPI summary of filtered set ───────────────────────────────────────────
    kpi_grid(
        kpi_html('Total Spend', fmt_vnd(dff['Spend'].sum() if 'Spend' in dff.columns else 0), '—', 'accent'),
        kpi_html('Impressions', fmt_num(dff['Impressions'].sum() if 'Impressions' in dff.columns else 0), '—', 'blue'),
        kpi_html('Ads Count', fmt_num(dff['Ad Name'].nunique()), '—', 'purple'),
        kpi_html('Avg CTR',
                 f'{dff["CTR"].mean()*100:.2f}%' if 'CTR' in dff.columns and len(dff) else '—',
                 '—', 'yellow'),
        cols=4,
    )

    st.markdown("---")

    # ── Aggregate by Ad Name ──────────────────────────────────────────────────
    section('Ad Performance Table', 'accent')

    agg_cols = {c: 'sum' for c in ['Spend', 'Impressions', 'Reach', 'Clicks', 'Purchases',
                                    'Revenue', 'ATC', 'Checkouts', 'ThruPlays',
                                    'Results', 'IG Follows'] if c in dff.columns}
    first_cols = {c: 'first' for c in ['Brand', 'Format', 'Camp Type', 'Status'] if c in dff.columns}

    agg = dff.groupby('Ad Name').agg({**agg_cols, **first_cols}).reset_index()

    if 'Spend' in agg.columns and 'Impressions' in agg.columns:
        agg['CTR_calc'] = agg.apply(
            lambda r: r['Clicks'] / r['Impressions'] * 100
            if 'Clicks' in agg.columns and r['Impressions'] > 0 else 0, axis=1
        )
    if 'Revenue' in agg.columns and 'Spend' in agg.columns:
        agg['ROAS_calc'] = agg.apply(
            lambda r: r['Revenue'] / r['Spend'] if r['Spend'] > 0 else 0, axis=1
        )

    agg = agg.sort_values('Spend', ascending=False)

    is_conv = f_type in ('Catalog Sale', 'Retargeting')

    headers = ['#', 'Ad Name', 'Brand', 'Format', 'Status',
               'Spend', 'Impressions', 'CTR']
    aligns  = ['center', 'left', 'center', 'center', 'center'] + ['right'] * 3

    if is_conv:
        headers += ['ATC', 'Purchases', 'GMV', 'ROAS']
        aligns  += ['right', 'right', 'right', 'center']
    else:
        headers += ['Results', 'VTR']
        aligns  += ['right', 'right']

    rows = []
    for i, (_, row) in enumerate(agg.head(50).iterrows(), 1):
        name     = str(row.get('Ad Name', ''))
        brand    = str(row.get('Brand', 'OTHER'))
        b_color  = BRAND_COLORS.get(brand, '#64748B')
        fmt_name = f'<span title="{name}">{name[:45]}…</span>' if len(name) > 45 else name
        status   = str(row.get('Status', ''))
        s_color  = C['green'] if 'active' in status.lower() else '#64748B'

        vtr = row.get('ThruPlays', 0) / row.get('Impressions', 1) * 100 if row.get('Impressions', 0) else 0

        base = [
            f'<span style="color:#64748B">{i}</span>',
            fmt_name,
            f'<span style="color:{b_color};font-size:11px;font-weight:600">{brand}</span>',
            str(row.get('Format', '—')),
            f'<span style="color:{s_color};font-size:11px">{status}</span>',
            fmt_vnd(row.get('Spend', 0)),
            fmt_num(row.get('Impressions', 0)),
            f'{row.get("CTR_calc", 0):.2f}%',
        ]
        if is_conv:
            base += [
                fmt_num(row.get('ATC', 0)),
                fmt_num(row.get('Purchases', 0)),
                fmt_vnd(row.get('Revenue', 0)),
                roas_badge(row.get('ROAS_calc', 0)),
            ]
        else:
            base += [
                fmt_num(row.get('Results', 0)),
                f'{vtr:.1f}%',
            ]
        rows.append(base)

    html_table(headers, rows, aligns)

    st.markdown("---")

    # ── Summary by Brand ──────────────────────────────────────────────────────
    col_b, col_f = st.columns(2)
    with col_b:
        section('Summary by Brand', 'green')
        brand_agg = dff.groupby('Brand').agg(
            ads=('Ad Name', 'nunique'),
            spend=('Spend', 'sum'),
            impressions=('Impressions', 'sum'),
        ).reset_index().sort_values('spend', ascending=False)

        headers_b = ['Brand', 'Ads', 'Spend', 'Impressions']
        aligns_b  = ['left', 'right', 'right', 'right']
        rows_b = []
        for _, r in brand_agg.iterrows():
            bc = BRAND_COLORS.get(str(r['Brand']), '#64748B')
            rows_b.append([
                f'<span style="color:{bc};font-weight:600">{r["Brand"]}</span>',
                fmt_num(r['ads']),
                fmt_vnd(r['spend']),
                fmt_num(r['impressions']),
            ])
        html_table(headers_b, rows_b, aligns_b)

    with col_f:
        section('Summary by Format', 'blue')
        if 'Format' in dff.columns:
            fmt_agg = dff.groupby('Format').agg(
                ads=('Ad Name', 'nunique'),
                spend=('Spend', 'sum'),
                impressions=('Impressions', 'sum'),
            ).reset_index().sort_values('spend', ascending=False)

            headers_f = ['Format', 'Ads', 'Spend', 'Impressions']
            aligns_f  = ['left', 'right', 'right', 'right']
            rows_f = []
            for _, r in fmt_agg.iterrows():
                rows_f.append([
                    str(r['Format']),
                    fmt_num(r['ads']),
                    fmt_vnd(r['spend']),
                    fmt_num(r['impressions']),
                ])
            html_table(headers_f, rows_f, aligns_f)
