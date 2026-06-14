import streamlit as st
import plotly.graph_objects as go
from helpers import (kpi_html, kpi_grid, html_table, editable_insight,
                     section, badge, roas_badge, delta_badge, mini_bar_cell,
                     fmt_vnd, fmt_num, C)



def render(data):
    st.markdown("## Shopee Ads")

    cv      = data['conversion']
    so      = cv.get('shopee_overall', {})
    camps   = cv.get('shopee_campaigns', [])
    brands  = cv.get('shopee_brands', [])

    ov      = data['overview']
    sale_prev_map = {s['channel']: s for s in ov.get('sale_prev', [])}
    sp      = sale_prev_map.get('Shopee', {})

    total_spend  = so.get('spend', 0)
    total_orders = so.get('orders', 0)
    total_gmv    = so.get('gmv', 0)
    total_roas   = so.get('roas', 0)
    aov   = total_gmv / total_orders if total_orders else 0
    p_gmv = sp.get('gmv', 0)
    p_sp  = sp.get('spend', 0)

    # ── KPI row with MoM compare ──────────────────────────────────────────────
    kpi_grid(
        kpi_html('Shopee Spend',    fmt_vnd(total_spend),
                 f'Prev: {fmt_vnd(p_sp)} {delta_badge(total_spend, p_sp)}' if p_sp else '—', 'accent'),
        kpi_html('Orders',          fmt_num(total_orders),
                 f'Prev: {fmt_num(sp.get("orders",0))} {delta_badge(total_orders, sp.get("orders",0))}' if sp.get('orders') else '—', 'blue'),
        kpi_html('Total GMV',       fmt_vnd(total_gmv),
                 f'Prev: {fmt_vnd(p_gmv)} {delta_badge(total_gmv, p_gmv)}' if p_gmv else '—', 'green'),
        kpi_html('ROAS',            f'{total_roas:.2f}x',
                 '✅ Above 3.0x' if total_roas >= 3.0 else '⚠️ Below 3.0x',
                 'green' if total_roas >= 3.0 else 'yellow'),
        kpi_html('Avg Order Value', fmt_vnd(aov), '—', 'purple'),
        cols=5,
    )

    st.markdown("---")

    # ── Brand Performance (table full width, then chart below) ────────────────
    section('Brand Performance', 'green')
    total_gmv_brands = sum(b['gmv'] for b in brands)
    headers_b = ['Brand', 'Orders', 'GMV', 'Spend', 'ROAS', 'Share']
    aligns_b  = ['left', 'right', 'right', 'right', 'center', 'left']
    rows_b = []
    for b in sorted(brands, key=lambda x: x['gmv'], reverse=True):
        share = b['gmv'] / total_gmv_brands * 100 if total_gmv_brands else 0
        roas  = b['gmv'] / b['spend'] if b['spend'] > 0 else 0
        rows_b.append([
            b['brand'],
            fmt_num(b['orders']),
            fmt_vnd(b['gmv']),
            fmt_vnd(b['spend']),
            roas_badge(roas),
            mini_bar_cell(share, color=C['accent']),
        ])
    html_table(headers_b, rows_b, aligns_b)

    # GMV by Brand chart — below table, full width
    if brands:
        b_sorted = sorted(brands, key=lambda x: x['gmv'])
        brand_colors = [C['accent'], C['green'], C['blue'], C['purple'],
                        C['pink'], C['yellow'], C['red'], '#94A3B8']
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
            height=max(200, len(b_sorted) * 32),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#0F172A', size=12),
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=False),
            margin=dict(l=10, r=100, t=10, b=10),
        )
        st.plotly_chart(fig, use_container_width=True, key='shopee_brand_gmv')

    st.markdown("---")

    # ── Top Products — MoM Comparison ────────────────────────────────────────
    section('Top Products — MoM Comparison', 'purple')

    prods_cur  = cv.get('shopee_products_cur', [])
    prods_prev = cv.get('shopee_products_prev', [])

    if prods_cur:
        prev_map  = {p['name']: p for p in prods_prev}
        cur_names = {p['name'] for p in prods_cur}

        rising_stars = []
        rows_p, row_bgs = [], []

        for i, p in enumerate(prods_cur[:20], 1):
            name      = str(p.get('name', ''))
            brand     = str(p.get('brand', 'OTHER'))
            gmv_cur   = p.get('gmv', 0)
            roas_cur  = p.get('roas', 0)
            prev      = prev_map.get(name, {})
            gmv_prev  = prev.get('gmv', 0)
            roas_prev = prev.get('roas', 0)

            is_new     = name not in prev_map
            gmv_delta  = (gmv_cur - gmv_prev) / gmv_prev if gmv_prev > 0 else None
            roas_delta = roas_cur - roas_prev if roas_prev > 0 else None

            # Classify & row background
            significant = (gmv_delta is not None and abs(gmv_delta) >= 0.3) or is_new
            if is_new:
                tag    = badge('Mới', 'blue')
                row_bg = 'rgba(219,234,254,0.35)'
            elif gmv_delta is not None and gmv_delta >= 0.3:
                tag    = badge('↑ Rising', 'green')
                row_bg = 'rgba(220,252,231,0.45)'
                rising_stars.append({**p, 'prev_gmv': gmv_prev, 'prev_roas': roas_prev, 'gmv_delta': gmv_delta})
            elif gmv_delta is not None and gmv_delta <= -0.3:
                tag    = badge('↓ Drop', 'red')
                row_bg = 'rgba(254,226,226,0.45)'
            else:
                tag    = '<span style="color:#94A3B8">—</span>'
                row_bg = 'transparent'

            name_cell  = f'<span title="{name}">{name[:48]}…</span>' if len(name) > 48 else name
            gmv_delta_cell  = delta_badge(gmv_cur, gmv_prev) if not is_new else badge('New', 'blue')
            roas_delta_cell = (
                f'<span style="color:{"#16A34A" if roas_delta >= 0 else "#DC2626"};font-size:11px;font-weight:600">'
                f'{"+" if roas_delta >= 0 else ""}{roas_delta:.2f}x</span>'
                if roas_delta is not None else '—'
            )

            rows_p.append([
                f'<span style="color:#64748B">{i}</span>',
                name_cell, brand,
                fmt_vnd(gmv_cur),
                fmt_vnd(gmv_prev) if gmv_prev > 0 else '—',
                gmv_delta_cell,
                roas_badge(roas_cur),
                roas_badge(roas_prev) if roas_prev > 0 else '—',
                roas_delta_cell,
                fmt_num(p.get('orders', 0)),
                tag,
            ])
            row_bgs.append(row_bg)

        # Render table với row highlighting
        headers_p = ['#', 'Product / Campaign', 'Brand',
                     'GMV (Cur)', 'GMV (Prev)', 'Δ GMV',
                     'ROAS (Cur)', 'ROAS (Prev)', 'Δ ROAS',
                     'Orders', 'Status']
        aligns_p  = ['center', 'left', 'left',
                     'right', 'right', 'center',
                     'center', 'center', 'center',
                     'right', 'center']
        ths = ''.join(
            f'<th style="color:#FFF5EC;font-size:10.5px;text-transform:uppercase;letter-spacing:.6px;'
            f'padding:10px 12px;text-align:{aligns_p[j]};border-bottom:none;font-weight:500">{h}</th>'
            for j, h in enumerate(headers_p)
        )
        trs = ''
        for row_data, bg in zip(rows_p, row_bgs):
            trs += f'<tr style="background:{bg}">' + ''.join(
                f'<td style="padding:10px 12px;text-align:{aligns_p[j]};border-bottom:1px solid rgba(0,0,0,0.04)">{cell}</td>'
                for j, cell in enumerate(row_data)
            ) + '</tr>'
        st.markdown(
            f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
            f'<thead><tr style="background:#4A2000">{ths}</tr></thead><tbody>{trs}</tbody></table>',
            unsafe_allow_html=True,
        )

        # Products in prev top 10 not in current
        dropped = [p for p in prods_prev[:10] if p['name'] not in cur_names]

        if rising_stars or dropped:
            st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)
            col_r, col_d = st.columns(2)

            with col_r:
                if rising_stars:
                    section('Rising Stars', 'green')
                    for r in sorted(rising_stars, key=lambda x: x['gmv_delta'], reverse=True)[:3]:
                        pct       = r['gmv_delta'] * 100
                        roas_line = (f' · ROAS {r["prev_roas"]:.2f}x → {r["roas"]:.2f}x'
                                     if r.get('prev_roas', 0) > 0 else '')
                        st.markdown(
                            f'<div style="padding:12px 14px;background:#F0FDF4;border-radius:8px;'
                            f'border-left:3px solid #16A34A;margin-bottom:8px">'
                            f'<div style="font-weight:600;font-size:13px;color:#0F172A">{r["name"][:55]}</div>'
                            f'<div style="font-size:12px;color:#16A34A;margin-top:5px">'
                            f'GMV +{pct:.0f}% · {fmt_vnd(r["prev_gmv"])} → {fmt_vnd(r["gmv"])}{roas_line}'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )

            with col_d:
                if dropped:
                    section('Dropped khỏi Top', 'yellow')
                    for d in dropped[:3]:
                        st.markdown(
                            f'<div style="padding:12px 14px;background:#FFFBEB;border-radius:8px;'
                            f'border-left:3px solid #B45309;margin-bottom:8px">'
                            f'<div style="font-weight:600;font-size:13px;color:#0F172A">{str(d["name"])[:55]}</div>'
                            f'<div style="font-size:12px;color:#92400E;margin-top:5px">'
                            f'Kỳ trước: GMV {fmt_vnd(d["gmv"])} · ROAS {d.get("roas", 0):.2f}x'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )
    else:
        st.caption('Chưa có dữ liệu sản phẩm / campaign Shopee.')

    st.markdown("---")

    # ── Campaign Performance — spending only, sorted by GMV ──────────────────
    section('Campaign Performance', 'accent')
    camps_active = sorted([c for c in camps if c.get('spend', 0) > 0],
                          key=lambda x: x['gmv'], reverse=True)
    if camps_active:
        headers = ['Campaign', 'GMV', 'Spend', 'ROAS', 'Orders', 'Impressions', 'Clicks', 'CTR', 'CR']
        aligns  = ['left'] + ['right'] * 8
        rows = []
        for c in camps_active:
            roas = c['gmv'] / c['spend'] if c['spend'] > 0 else 0
            rows.append([
                c['campaign'],
                fmt_vnd(c['gmv']),
                fmt_vnd(c['spend']),
                roas_badge(roas),
                fmt_num(c['orders']),
                fmt_num(c['impressions']),
                fmt_num(c['clicks']),
                f'{c["ctr"]*100:.2f}%',
                f'{c["cr"]*100:.2f}%',
            ])
        html_table(headers, rows, aligns)
    else:
        st.caption('Chưa có dữ liệu campaign.')

    st.markdown("---")
    editable_insight('shopee', _auto_insight(so, camps_active, brands), 'green')


def _auto_insight(so, camps, brands):
    lines = [
        f"Shopee: {fmt_num(so.get('orders',0))} orders | GMV {fmt_vnd(so.get('gmv',0))} | ROAS {so.get('roas',0):.2f}x",
    ]
    if camps:
        best = camps[0]
        roas = best['gmv'] / best['spend'] if best.get('spend', 0) > 0 else 0
        lines.append(f"Campaign GMV cao nhất: {best['campaign']} — {fmt_vnd(best['gmv'])} | ROAS {roas:.1f}x")
    if brands:
        top = max(brands, key=lambda x: x['gmv'])
        roas = top['gmv'] / top['spend'] if top.get('spend', 0) > 0 else 0
        lines.append(f"Brand dẫn đầu: {top['brand']} — GMV {fmt_vnd(top['gmv'])}, ROAS {roas:.2f}x")
    return '\n'.join(lines)
