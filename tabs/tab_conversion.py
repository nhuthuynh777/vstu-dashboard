import streamlit as st
import plotly.graph_objects as go
from helpers import (kpi_html, kpi_grid, html_table, editable_insight,
                     section, badge, roas_badge, delta_badge,
                     fmt_vnd, fmt_num, fmt_pct, C)


def render(data):
    st.markdown("## 🎯 FB Conversion")

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

    # ── Funnel Catalog vs Retargeting ─────────────────────────────────────────
    section('Conversion Funnel — Catalog vs Retargeting', 'accent')

    funnel_steps = [
        ('Impressions',    'impressions', '—',        '—'),
        ('Reach',          'reach',       '—',        '—'),
        ('PDP Views (CV)', 'pdp_views',   '—',        '—'),
        ('Add to Cart',    'atc',         'a2c_rate',  'A2C Rate'),
        ('Checkout',       'checkouts',   'co_rate',   'CO Rate'),
        ('Purchase',       'purchases',   'pur_rate',  'Pur Rate'),
    ]

    headers = ['Step', 'Catalog Sale', 'Rate', 'Retargeting', 'Rate', 'Winner']
    aligns  = ['left', 'right', 'center', 'right', 'center', 'center']
    rows = []
    for label, val_key, rate_key, rate_label in funnel_steps:
        cv_val  = cat.get(val_key, 0)
        ret_val = ret.get(val_key, 0)
        cv_rate  = f'{cat.get(rate_key, 0)*100:.2f}%' if rate_key != '—' else '—'
        ret_rate = f'{ret.get(rate_key, 0)*100:.2f}%' if rate_key != '—' else '—'

        if rate_key != '—' and cv_val > 0 and ret_val > 0:
            winner = f'<span style="color:{C["green"]}">Retarget ✅</span>' \
                     if ret.get(rate_key, 0) > cat.get(rate_key, 0) \
                     else f'<span style="color:{C["accent"]}">Catalog ✅</span>'
        else:
            winner = '—'

        rows.append([label, fmt_num(cv_val), cv_rate, fmt_num(ret_val), ret_rate, winner])

    # GMV + ROAS rows
    rows.append(['GMV', fmt_vnd(cat.get('gmv', 0)), '—', fmt_vnd(ret.get('gmv', 0)), '—',
                 f'<span style="color:{C["green"]}">Retarget</span>' if ret.get('gmv',0) > cat.get('gmv',0) else '—'])
    cat_roas = cat.get('gmv', 0) / cat.get('spend', 1) if cat.get('spend') else 0
    ret_roas = ret.get('gmv', 0) / ret.get('spend', 1) if ret.get('spend') else 0
    rows.append(['ROAS', f'{cat_roas:.2f}x', '—', f'{ret_roas:.2f}x', '—',
                 roas_badge(max(cat_roas, ret_roas))])
    rows.append(['Cost/Purchase',
                 fmt_vnd(cat.get('cost_per_pur', 0)), '—',
                 fmt_vnd(ret.get('cost_per_pur', 0)), '—',
                 f'<span style="color:{C["green"]}">Retarget</span>' if ret.get('cost_per_pur',0) < cat.get('cost_per_pur',0) else '—'])

    html_table(headers, rows, aligns)

    st.markdown("---")

    # ── MoM Funnel Rates ─────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        section('Funnel Rates MoM', 'yellow')
        mom = cv.get('mom', {})
        t5  = mom.get('t5', {})
        t4  = mom.get('t4', {})

        metrics = [
            ('% A2C (CV→ATC)',         'a2c',      False),
            ('% Checkout (ATC→CO)',    'checkout',  False),
            ('% Purchase (CO→Pur)',    'purchase',  False),
            ('CR (Purchase/CV)',        'cr',        False),
        ]
        pva_rows = []
        for label, key, invert in metrics:
            v5 = t5.get(key, 0)
            v4 = t4.get(key, 0)
            delta = v5 - v4
            sign  = '+' if delta >= 0 else ''
            color = 'green' if (delta >= 0) != invert else 'red'
            pva_rows.append([
                label,
                f'{v4*100:.2f}%',
                f'{v5*100:.2f}%',
                badge(f'{sign}{delta*100:.2f}%', color),
            ])

        headers_mom = ['Metric', 'T4', 'T5', 'Δ']
        aligns_mom  = ['left', 'right', 'right', 'center']
        st.markdown(
            '<table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr>'
            + ''.join(f'<th style="color:#7A7670;font-size:11px;text-transform:uppercase;padding:8px 10px;text-align:{a};border-bottom:1px solid #2A2A2A">{h}</th>'
                      for h, a in zip(headers_mom, aligns_mom))
            + '</tr></thead><tbody>'
            + ''.join(
                '<tr>' + ''.join(
                    f'<td style="padding:9px 10px;text-align:{aligns_mom[i]};border-bottom:1px solid rgba(42,42,42,.5)">{cell}</td>'
                    for i, cell in enumerate(row)
                ) + '</tr>'
                for row in pva_rows
            )
            + '</tbody></table>',
            unsafe_allow_html=True
        )

    # ── Funnel chart ─────────────────────────────────────────────────────────
    with col2:
        section('Funnel Visualization', 'blue')
        cat_funnel = [cat.get('pdp_views', 0), cat.get('atc', 0),
                      cat.get('checkouts', 0), cat.get('purchases', 0)]
        ret_funnel = [ret.get('pdp_views', 0), ret.get('atc', 0),
                      ret.get('checkouts', 0), ret.get('purchases', 0)]
        stages = ['PDP Views', 'Add to Cart', 'Checkout', 'Purchase']
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Catalog Sale', x=stages, y=cat_funnel,
                             marker_color=C['accent'],
                             text=[fmt_num(v) for v in cat_funnel],
                             textposition='outside'))
        fig.add_trace(go.Bar(name='Retargeting', x=stages, y=ret_funnel,
                             marker_color=C['green'],
                             text=[fmt_num(v) for v in ret_funnel],
                             textposition='outside'))
        fig.update_layout(
            height=280, barmode='group',
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#E8E2D9', size=11),
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=False),
            margin=dict(l=10, r=10, t=20, b=10),
            legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(size=11)),
        )
        st.plotly_chart(fig, use_container_width=True, key='cv_funnel')

    st.markdown("---")

    # ── Product by Promotion ──────────────────────────────────────────────────
    if cv.get('by_promotion'):
        section('Product Performance by Promotion', 'purple')
        headers_p = ['Campaign', 'CV', 'ATC Rate', 'ATC', 'CO Rate', 'CO', 'Pur Rate', 'Purchases', 'GMV', 'Status']
        aligns_p  = ['left'] + ['right'] * 7 + ['right', 'center']
        rows_p = []
        for p in cv['by_promotion']:
            status_color = C['green'] if p['status'].lower() == 'active' else C['red']
            rows_p.append([
                p['campaign'],
                fmt_num(p['pdp_views']),
                f'{p["atc_rate"]*100:.1f}%',
                fmt_num(p['atc']),
                f'{p["co_rate"]*100:.1f}%',
                fmt_num(p['checkouts']),
                f'{p["pur_rate"]*100:.1f}%' if p['pur_rate'] else '—',
                fmt_num(p['purchases']),
                fmt_vnd(p['gmv']),
                f'<span style="color:{status_color}">{p["status"]}</span>',
            ])
        html_table(headers_p, rows_p, aligns_p)

    st.markdown("---")

    # ── Product by Brand (FB) ─────────────────────────────────────────────────
    if cv.get('by_brand'):
        section('Product Performance by Brand — FB', 'blue')
        headers_b = ['Brand', 'PDP Views', 'ATC Rate', 'ATC', 'CO Rate', 'CO', 'Pur Rate', 'Purchases', 'GMV', 'Status']
        aligns_b  = ['left'] + ['right'] * 7 + ['right', 'center']
        rows_b = []
        for b in cv['by_brand']:
            status_color = C['green'] if b['status'].lower() == 'active' else C['red']
            rows_b.append([
                b['brand'],
                fmt_num(b['pdp_views']),
                f'{b["atc_rate"]*100:.1f}%',
                fmt_num(b['atc']),
                f'{b["co_rate"]*100:.1f}%',
                fmt_num(b['checkouts']),
                f'{b["pur_rate"]*100:.1f}%' if b['pur_rate'] else '—',
                fmt_num(b['purchases']),
                fmt_vnd(b['gmv']),
                f'<span style="color:{status_color}">{b["status"]}</span>',
            ])
        html_table(headers_b, rows_b, aligns_b)

    st.markdown("---")
    editable_insight('conversion', _auto_insight(cat, ret, tot, total_roas), 'blue')


def _auto_insight(cat, ret, tot, roas):
    lines = [
        f"FB Conversion: spend {fmt_vnd(tot.get('spend',0))} | {fmt_num(tot.get('purchases',0))} purchases | ROAS {roas:.2f}x",
        f"Catalog Sale: {fmt_num(cat.get('purchases',0))} pur | GMV {fmt_vnd(cat.get('gmv',0))} | ROAS {cat.get('gmv',0)/cat.get('spend',1):.2f}x" if cat.get('spend') else '',
        f"Retargeting: {fmt_num(ret.get('purchases',0))} pur | GMV {fmt_vnd(ret.get('gmv',0))} | ROAS {ret.get('gmv',0)/ret.get('spend',1):.2f}x" if ret.get('spend') else '',
    ]
    return '\n'.join(l for l in lines if l)
