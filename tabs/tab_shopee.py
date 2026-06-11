import streamlit as st
import plotly.graph_objects as go
from helpers import (kpi_html, kpi_grid, html_table, editable_insight,
                     section, badge, roas_badge, fmt_vnd, fmt_num, C)


_SIGNAL = {
    'good':   (C['green'],  '✅'),
    'ok':     (C['yellow'], '🟡'),
    'bad':    (C['red'],    '🔴'),
}


def _roas_signal(roas):
    if roas >= 5.0:  return _SIGNAL['good']
    if roas >= 3.0:  return _SIGNAL['ok']
    return _SIGNAL['bad']


def render(data):
    st.markdown("## 🛒 Shopee Ads")

    cv = data['conversion']
    so = cv.get('shopee_overall', {})
    camps  = cv.get('shopee_campaigns', [])
    brands = cv.get('shopee_brands', [])
    prods  = cv.get('shopee_top_products', [])

    total_spend  = so.get('spend', 0)
    total_orders = so.get('orders', 0)
    total_gmv    = so.get('gmv', 0)
    total_roas   = so.get('roas', 0)
    aov = total_gmv / total_orders if total_orders else 0

    # ── KPI row ───────────────────────────────────────────────────────────────
    kpi_grid(
        kpi_html('Shopee Spend',   fmt_vnd(total_spend),  '—', 'accent'),
        kpi_html('Orders',         fmt_num(total_orders), '—', 'blue'),
        kpi_html('Total GMV',      fmt_vnd(total_gmv),    '—', 'green'),
        kpi_html('ROAS',           f'{total_roas:.2f}x',
                 '✅ Above 3.0x' if total_roas >= 3.0 else '⚠️ Below 3.0x',
                 'green' if total_roas >= 3.0 else 'yellow'),
        kpi_html('Avg Order Value', fmt_vnd(aov), '—', 'purple'),
        cols=5,
    )

    st.markdown("---")

    # ── Campaign Performance ──────────────────────────────────────────────────
    section('Campaign Performance', 'accent')

    headers = ['Campaign', 'Impressions', 'Clicks', 'CTR', 'Orders', 'CR', 'GMV', 'Spend', 'ROAS', '']
    aligns  = ['left'] + ['right'] * 7 + ['center', 'center']
    rows = []
    for c in camps:
        sig_color, sig_icon = _roas_signal(c['roas'])
        rows.append([
            c['campaign'],
            fmt_num(c['impressions']),
            fmt_num(c['clicks']),
            f'{c["ctr"]*100:.2f}%',
            fmt_num(c['orders']),
            f'{c["cr"]*100:.2f}%',
            fmt_vnd(c['gmv']),
            fmt_vnd(c['spend']),
            roas_badge(c['roas']),
            sig_icon,
        ])
    html_table(headers, rows, aligns)

    st.markdown("---")

    # ── Brand Performance + Chart ─────────────────────────────────────────────
    col1, col2 = st.columns([2, 3])

    with col1:
        section('Brand Performance', 'green')
        total_gmv_brands = sum(b['gmv'] for b in brands)
        headers_b = ['Brand', 'Orders', 'GMV', 'Spend', 'ROAS', 'Share']
        aligns_b  = ['left'] + ['right'] * 4 + ['right']
        rows_b = []
        for b in sorted(brands, key=lambda x: x['gmv'], reverse=True):
            share = b['gmv'] / total_gmv_brands * 100 if total_gmv_brands else 0
            rows_b.append([
                b['brand'],
                fmt_num(b['orders']),
                fmt_vnd(b['gmv']),
                fmt_vnd(b['spend']),
                roas_badge(b['roas']),
                f'{share:.1f}%',
            ])
        html_table(headers_b, rows_b, aligns_b)

    with col2:
        section('GMV by Brand', 'green')
        b_sorted = sorted(brands, key=lambda x: x['gmv'])
        brand_colors = [C['accent'], C['green'], C['blue'], C['purple'],
                        C['pink'], C['yellow'], C['red'], '#888']
        colors_mapped = [brand_colors[i % len(brand_colors)] for i in range(len(b_sorted))]
        fig = go.Figure(go.Bar(
            x=[b['gmv'] for b in b_sorted],
            y=[b['brand'] for b in b_sorted],
            orientation='h',
            marker_color=colors_mapped,
            text=[fmt_vnd(b['gmv']) for b in b_sorted],
            textposition='outside',
        ))
        fig.update_layout(
            height=max(260, len(b_sorted) * 36),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#E8E2D9', size=12),
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=False),
            margin=dict(l=10, r=80, t=10, b=10),
        )
        st.plotly_chart(fig, use_container_width=True, key='shopee_brand_gmv')

    st.markdown("---")

    # ── ROAS by Campaign chart ────────────────────────────────────────────────
    section('ROAS by Campaign', 'yellow')
    camps_with_orders = [c for c in camps if c['orders'] > 0]
    if camps_with_orders:
        c_sorted = sorted(camps_with_orders, key=lambda x: x['roas'])
        roas_colors = [C['green'] if c['roas'] >= 5 else C['yellow'] if c['roas'] >= 3 else C['red']
                       for c in c_sorted]
        fig2 = go.Figure(go.Bar(
            x=[c['roas'] for c in c_sorted],
            y=[c['campaign'][:30] for c in c_sorted],
            orientation='h',
            marker_color=roas_colors,
            text=[f'{c["roas"]:.1f}x' for c in c_sorted],
            textposition='outside',
        ))
        fig2.add_vline(x=3.0, line_dash='dash', line_color=C['green'],
                       annotation_text='3.0x target', annotation_font_color=C['green'])
        fig2.update_layout(
            height=max(200, len(c_sorted) * 40),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#E8E2D9', size=12),
            xaxis=dict(showgrid=False, zeroline=False, title='ROAS'),
            yaxis=dict(showgrid=False),
            margin=dict(l=10, r=60, t=10, b=10),
        )
        st.plotly_chart(fig2, use_container_width=True, key='shopee_roas')

    st.markdown("---")

    # ── Top Products ──────────────────────────────────────────────────────────
    if prods:
        section('Top Products', 'blue')
        headers_p = ['#', 'Product', 'Brand', 'Imp', 'Clicks', 'CTR', 'Items Sold', 'Spend', 'GMV', 'ROAS']
        aligns_p  = ['center', 'left', 'left'] + ['right'] * 7
        rows_p = []
        for i, p in enumerate(prods[:20], 1):
            brand_color = {
                'CAOSTU': C['accent'], 'HIGHCHIC': C['pink'], 'FNOS': C['blue'],
                'IAMSAIGON': C['yellow'], 'PARADOX': C['purple'],
            }.get(p['brand'], '#7A7670')
            rows_p.append([
                f'<strong>{i}</strong>',
                f'<span title="{p["product"]}">{p["product"][:40]}...</span>'
                if len(p['product']) > 40 else p['product'],
                f'<span style="color:{brand_color};font-size:11px;font-weight:600">{p["brand"]}</span>',
                fmt_num(p['impressions']),
                fmt_num(p['clicks']),
                f'{p["ctr"]*100:.2f}%',
                fmt_num(p['orders']),
                fmt_vnd(p['spend']),
                fmt_vnd(p['gmv']),
                roas_badge(p['roas']),
            ])
        html_table(headers_p, rows_p, aligns_p)

    st.markdown("---")
    editable_insight('shopee', _auto_insight(so, camps, brands), 'green')


def _auto_insight(so, camps, brands):
    lines = [
        f"Shopee: {fmt_num(so.get('orders',0))} orders | GMV {fmt_vnd(so.get('gmv',0))} | ROAS {so.get('roas',0):.2f}x",
    ]
    if camps:
        best = max((c for c in camps if c['orders'] > 0), key=lambda x: x['roas'], default=None)
        if best:
            lines.append(f"Campaign ROAS cao nhất: {best['campaign']} — {best['roas']:.1f}x")
    if brands:
        top_brand = max(brands, key=lambda x: x['gmv'])
        lines.append(f"Brand dẫn đầu Shopee: {top_brand['brand']} — GMV {fmt_vnd(top_brand['gmv'])}, ROAS {top_brand['roas']:.2f}x")
    return '\n'.join(lines)
