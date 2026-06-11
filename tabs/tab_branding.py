import streamlit as st
from helpers import (kpi_html, kpi_grid, html_table, pva_table, editable_insight,
                     section, badge, spend_badge, fmt_vnd, fmt_num, fmt_pct, C)


def render(data):
    st.markdown("## 🎨 Branding Campaign — FB/IG")

    br   = data['branding']
    plan = data['plan']
    ch   = plan.get('channels', {})

    summary = {s['type']: s for s in br['summary']}
    total   = summary.get('Total', {})

    # ── KPI row ───────────────────────────────────────────────────────────────
    kpi_grid(
        kpi_html('Total Branding Spend', fmt_vnd(total.get('spend', 0)),
                 f"Plan: {fmt_vnd(ch.get('IG Reach',{}).get('budget',0) + ch.get('IG Engagement',{}).get('budget',0))}",
                 'accent'),
        kpi_html('Impressions', fmt_num(total.get('impressions', 0)), '—', 'blue'),
        kpi_html('Total Reach', fmt_num(total.get('reach', 0)), '—', 'purple'),
        kpi_html('Total Engagement', fmt_num(total.get('engagement', 0)), '—', 'pink'),
        cols=4,
    )

    st.markdown("---")

    # ── Summary table ─────────────────────────────────────────────────────────
    section('Campaign Type Breakdown', 'accent')

    headers = ['Type', 'Spend', 'Impressions', 'Reach', 'Engagement',
               'Followers', 'Clicks', 'Video Views', 'Frequency']
    aligns  = ['left'] + ['right'] * 8
    rows = []
    for label in ['Reach', 'Engagement', 'Profile Visit', 'Total']:
        s = summary.get(label, {})
        rows.append([
            f'<strong>{label}</strong>' if label == 'Total' else label,
            fmt_vnd(s.get('spend', 0)),
            fmt_num(s.get('impressions', 0)),
            fmt_num(s.get('reach', 0)),
            fmt_num(s.get('engagement', 0)),
            fmt_num(s.get('followers', 0)),
            fmt_num(s.get('clicks', 0)),
            fmt_num(s.get('video_views', 0)),
            f"{s.get('frequency', 0):.2f}",
        ])
    html_table(headers, rows, aligns)

    st.markdown("---")

    # ── Plan vs Actual per type ───────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)

    def _pva(col, title, type_key, plan_key, kpi_label, dot):
        with col:
            section(title, dot)
            s = summary.get(type_key, {})
            p = ch.get(plan_key, {})
            pva_table([
                ('Budget',       p.get('budget', 0), s.get('spend', 0),      fmt_vnd, spend_badge(s.get('spend',0)/p.get('budget',1) if p.get('budget') else 0)),
                (kpi_label,      p.get('kpi', 0),    s.get('impressions', 0), fmt_num, spend_badge(s.get('impressions',0)/p.get('kpi',1) if p.get('kpi') else 0)),
                ('Reach',        0,                  s.get('reach', 0),       fmt_num, badge('—', 'blue')),
                ('Video Views',  0,                  s.get('video_views', 0), fmt_num, badge('—', 'blue')),
            ])

    _pva(col1, 'Reach',        'Reach',         'IG Reach',         'Impressions', 'blue')
    _pva(col2, 'Engagement',   'Engagement',    'IG Engagement',    'Engagement',  'pink')
    _pva(col3, 'Profile Visit','Profile Visit', 'FB Profile Visit', 'Clicks',      'purple')

    st.markdown("---")

    # ── Top Ads ───────────────────────────────────────────────────────────────
    if br['top_ads']:
        section('Top Ads — Engagement', 'yellow')
        headers_ads = ['#', 'Ad Name', 'Brand', 'Format', 'Engagement', 'VTR']
        aligns_ads  = ['center', 'left', 'left', 'center', 'right', 'right']
        rows_ads = []
        for i, ad in enumerate(br['top_ads'], 1):
            brand_color = {
                'PARADOX': C['purple'], 'HIGHCHIC': C['pink'], 'IAMSAIGON': C['yellow'],
                'CAOSTU': C['accent'], 'FNOS': C['blue'],
            }.get(ad['brand'], C['blue'])
            rows_ads.append([
                f'<strong>{i}</strong>',
                f'<span title="{ad["name"]}" style="line-height:1.4">{ad["name"][:45]}...</span>'
                if len(ad["name"]) > 45 else ad["name"],
                f'<span style="color:{brand_color};font-weight:600">{ad["brand"]}</span>',
                ad['format'],
                fmt_num(ad['engagement']),
                f'{ad["vtr"]*100:.1f}%' if ad['vtr'] < 1 else f'{ad["vtr"]:.1f}%',
            ])
        html_table(headers_ads, rows_ads, aligns_ads)

    st.markdown("---")
    editable_insight('branding', _auto_insight(br, summary), 'pink')


def _auto_insight(br, summary):
    total = summary.get('Total', {})
    lines = [
        f"Tổng Branding spend: {fmt_vnd(total.get('spend',0))} | "
        f"Impressions: {fmt_num(total.get('impressions',0))} | "
        f"Reach: {fmt_num(total.get('reach',0))}",
    ]
    if br['top_ads']:
        top = max(br['top_ads'], key=lambda x: x['engagement'])
        lines.append(f"Top ad engagement: {top['name'][:50]} — {fmt_num(top['engagement'])} engagements")
    return '\n'.join(lines)
