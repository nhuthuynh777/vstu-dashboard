import streamlit as st
import plotly.graph_objects as go
from helpers import (kpi_html, kpi_grid, html_table, editable_insight,
                     section, badge, roas_badge, fmt_vnd, fmt_num, C)


def render(data):
    st.markdown("## FB Conversion")

    cv = data['conversion']
    fb = {f['type']: f for f in cv['fb']}
    cat = fb.get('Catalog Sale', {})
    ret = fb.get('Retargeting', {})
    tot = fb.get('Total', {})

    total_spend = tot.get('spend', 0)
    total_gmv   = cat.get('gmv', 0) + ret.get('gmv', 0)
    total_pur   = tot.get('purchases', 0)
    total_roas  = total_gmv / total_spend if total_spend else 0
    total_cr    = tot.get('cr', 0)

    # ── KPI ──────────────────────────────────────────────────────────────────
    kpi_grid(
        kpi_html('FB Conversion Spend', fmt_vnd(total_spend), '—', 'accent'),
        kpi_html('Total Purchases', fmt_num(total_pur), '—', 'green'),
        kpi_html('Total GMV', fmt_vnd(total_gmv), '—', 'blue'),
        kpi_html('Avg ROAS', f'{total_roas:.2f}x',
                 'Target: 3.0x' + (' ⚠️' if total_roas < 3.0 else ' ✅'),
                 'yellow' if total_roas < 3.0 else 'green'),
        kpi_html('CR (Purchase/CV)',
                 f'{total_cr*100:.3f}%' if total_cr < 0.1 else f'{total_cr:.3f}%',
                 '—', 'purple'),
        cols=5,
    )

    st.markdown("---")

    # ── Conversion Funnel — rows=campaign type, cols=metrics ─────────────────
    section('Conversion Funnel — Catalog vs Retargeting', 'accent')

    cat_roas = cat.get('gmv', 0) / cat.get('spend', 1) if cat.get('spend') else 0
    ret_roas = ret.get('gmv', 0) / ret.get('spend', 1) if ret.get('spend') else 0

    headers = ['Campaign', 'Spend', 'Impressions', 'Reach',
               'PDP Views', 'ATC', 'A2C Rate',
               'Checkout', 'CO Rate', 'Purchase', 'Pur Rate',
               'GMV', 'ROAS', 'CR', 'CPA']
    aligns  = ['left'] + ['right'] * 14

    rows = []
    for label, d in [('Prospecting (Catalog)', cat), ('Retargeting', ret), ('Total', tot)]:
        spend = d.get('spend', 0)
        gmv   = d.get('gmv', 0)
        roas  = gmv / spend if spend else 0
        rows.append([
            f'<strong>{label}</strong>' if label == 'Total' else label,
            fmt_vnd(spend),
            fmt_num(d.get('impressions', 0)),
            fmt_num(d.get('reach', 0)),
            fmt_num(d.get('pdp_views', 0)),
            fmt_num(d.get('atc', 0)),
            f"{d.get('a2c_rate', 0)*100:.1f}%",
            fmt_num(d.get('checkouts', 0)),
            f"{d.get('co_rate', 0)*100:.1f}%",
            fmt_num(d.get('purchases', 0)),
            f"{d.get('pur_rate', 0)*100:.1f}%",
            fmt_vnd(gmv),
            roas_badge(roas),
            f"{d.get('cr', 0)*100:.3f}%",
            fmt_vnd(d.get('cost_per_pur', 0)),
        ])
    html_table(headers, rows, aligns)

    st.markdown("---")

    # ── Funnel Visualization (full width) ────────────────────────────────────
    section('Funnel Visualization', 'blue')
    stages     = ['PDP Views', 'Add to Cart', 'Checkout', 'Purchase']
    cat_funnel = [cat.get('pdp_views', 0), cat.get('atc', 0),
                  cat.get('checkouts', 0), cat.get('purchases', 0)]
    ret_funnel = [ret.get('pdp_views', 0), ret.get('atc', 0),
                  ret.get('checkouts', 0), ret.get('purchases', 0)]
    fig = go.Figure()
    fig.add_trace(go.Bar(name='Prospecting (Catalog)', x=stages, y=cat_funnel,
                         marker_color=C['accent'],
                         text=[fmt_num(v) for v in cat_funnel],
                         textposition='outside'))
    fig.add_trace(go.Bar(name='Retargeting', x=stages, y=ret_funnel,
                         marker_color=C['green'],
                         text=[fmt_num(v) for v in ret_funnel],
                         textposition='outside'))
    fig.update_layout(
        height=300, barmode='group',
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#1A1A1A', size=12),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=False, visible=False),
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=12), orientation='h',
                    yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    st.plotly_chart(fig, use_container_width=True, key='cv_funnel')

    st.markdown("---")

    # ── Funnel Rates MoM — card layout ───────────────────────────────────────
    section('Funnel Rates — MoM Comparison', 'yellow')

    # Period label inputs
    cp1, cp2, _ = st.columns([1, 1, 4])
    with cp1:
        lbl_prev = st.text_input('Kỳ trước', value='T4', key='mom_lbl_prev',
                                 placeholder='vd: T4, Apr 2026')
    with cp2:
        lbl_cur  = st.text_input('Kỳ hiện tại', value='T5', key='mom_lbl_cur',
                                 placeholder='vd: T5, May 2026')

    mom   = cv.get('mom', {})
    t_cur = mom.get('t_current', {})
    t_prv = mom.get('t_prev', {})

    _mom_metrics = [
        ('A2C Rate',       'CV → ATC',      'a2c',      'yellow'),
        ('Checkout Rate',  'ATC → CO',       'checkout', 'blue'),
        ('Purchase Rate',  'CO → Purchase',  'purchase', 'green'),
        ('Overall CR',     'Purchase / CV',  'cr',       'purple'),
    ]

    cards = []
    for label, desc, key, color in _mom_metrics:
        v_c = t_cur.get(key, 0)
        v_p = t_prv.get(key, 0)
        d   = v_c - v_p
        sign   = '+' if d >= 0 else ''
        arrow  = '▲' if d >= 0 else '▼'
        d_clr  = '#16A34A' if d >= 0 else '#DC2626'
        delta_html = (f'  ·  <span style="color:{d_clr};font-weight:500">'
                      f'{arrow} {sign}{d*100:.2f}pp</span>') if v_p > 0 else ''
        sub = (f'<span style="color:#9CA3AF">{lbl_prev}:</span> {v_p*100:.2f}%{delta_html}')
        heading = (f'{label} '
                   f'<span style="color:#9CA3AF;font-size:10px;font-weight:400">{desc}</span>')
        cards.append(kpi_html(heading, f'{v_c*100:.2f}%', sub, color))

    kpi_grid(*cards, cols=4)

    st.markdown("---")

    # ── Performance by Brand & Promotion Campaign ─────────────────────────────
    df_raw = data.get('fb_raw')
    if df_raw is not None and not df_raw.empty:
        import pandas as pd
        conv_mask = df_raw['Camp Type'].isin(['Catalog Sale', 'Retargeting']) \
                    if 'Camp Type' in df_raw.columns else pd.Series([True] * len(df_raw))
        df_conv = df_raw[conv_mask].copy()
        agg_cols = {c: 'sum' for c in
                    ['Spend', 'Impressions', 'Content Views', 'ATC', 'Checkouts', 'Purchases', 'Revenue']
                    if c in df_conv.columns}

        if not df_conv.empty and 'Brand' in df_conv.columns:
            # Split: brand ads vs OTHER (promotion campaigns)
            df_brand = df_conv[df_conv['Brand'] != 'OTHER'].copy()
            df_promo = df_conv[df_conv['Brand'] == 'OTHER'].copy()

            def _conv_table(df_g, group_col, h_label):
                if df_g.empty or group_col not in df_g.columns:
                    return
                agg = df_g.groupby(group_col).agg(agg_cols).reset_index()
                agg['ROAS'] = agg.apply(
                    lambda r: r.get('Revenue', 0) / r['Spend'] if r['Spend'] > 0 else 0, axis=1)
                agg = agg.sort_values('Revenue', ascending=False)
                h = [h_label, 'Spend', 'PDP Views', 'ATC', 'Checkout', 'Purchase', 'GMV', 'ROAS']
                a = ['left'] + ['right'] * 7
                rows_out = []
                for _, r in agg.iterrows():
                    rows_out.append([
                        str(r[group_col]),
                        fmt_vnd(r.get('Spend', 0)),
                        fmt_num(r.get('Content Views', 0)),
                        fmt_num(r.get('ATC', 0)),
                        fmt_num(r.get('Checkouts', 0)),
                        fmt_num(r.get('Purchases', 0)),
                        fmt_vnd(r.get('Revenue', 0)),
                        roas_badge(r['ROAS']),
                    ])
                html_table(h, rows_out, a)

            # Brand performance
            section('Performance by Brand — FB Conversion', 'purple')
            _conv_table(df_brand, 'Brand', 'Brand')

            st.markdown("---")

            # Promotion campaign performance (OTHER brand = no brand tag in ad name)
            section('Performance by Promotion Campaign — FB Conversion', 'blue')
            st.caption('Ads không có brand tag — phân loại theo promotion name từ ad name')
            _conv_table(df_promo, 'Promotion', 'Promotion') if 'Promotion' in df_promo.columns else None

    st.markdown("---")
    editable_insight('conversion', _auto_insight(cat, ret, tot, total_roas), 'blue')


def _auto_insight(cat, ret, tot, roas):
    lines = [
        f"FB Conversion: spend {fmt_vnd(tot.get('spend',0))} | {fmt_num(tot.get('purchases',0))} purchases | ROAS {roas:.2f}x",
        f"Prospecting: {fmt_num(cat.get('purchases',0))} pur | GMV {fmt_vnd(cat.get('gmv',0))}" if cat.get('spend') else '',
        f"Retargeting: {fmt_num(ret.get('purchases',0))} pur | GMV {fmt_vnd(ret.get('gmv',0))}" if ret.get('spend') else '',
    ]
    return '\n'.join(l for l in lines if l)
