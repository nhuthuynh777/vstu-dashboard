import streamlit as st
import plotly.graph_objects as go
from helpers import (kpi_html, kpi_grid, html_table, pva_table, editable_insight,
                     section, badge, spend_badge, roas_badge, delta_badge,
                     fmt_vnd, fmt_num, fmt_pct, donut, chart_legend, C)


def render(data):
    st.markdown("## 📊 Campaign Overview")

    ov   = data['overview']
    plan = data['plan']
    tc   = ov['total_current']
    tp   = ov['total_prev']

    total_spend  = tc.get('spend', 0)
    total_gmv    = tc.get('gmv', 0)
    total_orders = tc.get('orders', 0)
    total_roas   = tc.get('roas', 0)
    total_budget = plan.get('total_budget', 0)
    prev_gmv     = tp.get('gmv', 0)
    prev_roas    = tp.get('roas', 0)

    # ── KPI row ───────────────────────────────────────────────────────────────
    spend_pct = total_spend / total_budget if total_budget else 0

    fb_orders    = sum(s['orders'] for s in ov['sale_current'] if 'FB' in s['channel'])
    shopee_orders = sum(s['orders'] for s in ov['sale_current'] if 'Shopee' in s['channel'])

    kpi_grid(
        kpi_html('Total Spend', fmt_vnd(total_spend),
                 f'Plan: {fmt_vnd(total_budget)}',
                 'accent', spend_pct, f'Plan {fmt_vnd(total_budget)}'),
        kpi_html('Total GMV', fmt_vnd(total_gmv),
                 f'Plan: {fmt_vnd(sum(c.get("gmv",0) for c in plan["channels"].values()))}',
                 'green'),
        kpi_html('Overall ROAS', f'{total_roas:.2f}x',
                 'Target: 3.0x' + (' ⚠️' if total_roas < 3.0 else ' ✅'),
                 'yellow' if total_roas < 3.0 else 'green'),
        kpi_html('Total Orders', fmt_num(total_orders),
                 f'FB: {fmt_num(fb_orders)} · Shopee: {fmt_num(shopee_orders)}',
                 'blue'),
        kpi_html('vs Last Period', delta_badge(total_gmv, prev_gmv),
                 f'Prev GMV: {fmt_vnd(prev_gmv)}',
                 'purple'),
        cols=5,
    )

    st.markdown("---")

    # ── Bảng 1: Plan vs Actual full breakdown ─────────────────────────────────
    section('Plan vs Actual — Full Breakdown', 'accent')

    ch_plan = plan.get('channels', {})
    headers = ['Channel', 'Budget Plan', 'Actual Spend', '% Spend',
               'KPI Plan', 'KPI Actual', '% KPI', 'ROAS']
    aligns  = ['left', 'right', 'right', 'center', 'right', 'right', 'center', 'center']
    rows_html = []
    for item in ov['overall']:
        ch = item['channel']
        plan_ch = ch_plan.get(ch, {})
        bp  = item['budget_plan']
        ba  = item['budget_actual']
        kp  = item['kpi_plan']
        ka  = item['kpi_actual']
        bp_pct = ba / bp if bp else 0
        kp_pct = ka / kp if kp else 0
        rows_html.append([
            f'<span style="color:#E8E2D9">{ch}</span>',
            fmt_vnd(bp), fmt_vnd(ba), spend_badge(bp_pct),
            fmt_num(kp), fmt_num(ka), spend_badge(kp_pct),
            roas_badge(plan_ch.get('roas', 0)) if plan_ch.get('roas', 0) else '—',
        ])
    html_table(headers, rows_html, aligns)

    st.markdown("---")

    # ── Bảng 2: Sale Performance MoM ─────────────────────────────────────────
    section('Sale Performance — MoM Comparison', 'green')

    sale_prev_map = {s['channel']: s for s in ov['sale_prev']}
    headers2 = ['Channel',
                'Spend (T5)', 'Orders (T5)', 'GMV (T5)', 'ROAS (T5)',
                'Spend (T4)', 'GMV (T4)', 'ROAS (T4)',
                'Δ GMV', 'Δ ROAS']
    aligns2 = ['left'] + ['right'] * 3 + ['center'] + ['right'] * 2 + ['center'] * 3

    rows2 = []
    for s in ov['sale_current']:
        p = sale_prev_map.get(s['channel'], {})
        rows2.append([
            s['channel'],
            fmt_vnd(s['spend']), fmt_num(s['orders']),
            fmt_vnd(s['gmv']),   roas_badge(s['roas']),
            fmt_vnd(p.get('spend', 0)),
            fmt_vnd(p.get('gmv', 0)),
            roas_badge(p.get('roas', 0)),
            delta_badge(s['gmv'],  p.get('gmv', 0)),
            delta_badge(s['roas'], p.get('roas', 0)),
        ])
    # Total row
    rows2.append([
        '<strong>Total</strong>',
        fmt_vnd(tc.get('spend', 0)), fmt_num(tc.get('orders', 0)),
        fmt_vnd(tc.get('gmv', 0)),   roas_badge(tc.get('roas', 0)),
        fmt_vnd(tp.get('spend', 0)),
        fmt_vnd(tp.get('gmv', 0)),
        roas_badge(tp.get('roas', 0)),
        delta_badge(tc.get('gmv', 0),  tp.get('gmv', 0)),
        delta_badge(tc.get('roas', 0), tp.get('roas', 0)),
    ])
    html_table(headers2, rows2, aligns2)

    st.markdown("---")

    # ── Charts ────────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        section('Budget Allocation', 'accent')
        ch_labels, ch_values, ch_colors = [], [], []
        color_list = [C['accent'], C['pink'], C['blue'], C['purple'], C['green'], C['yellow']]
        for i, (name, ch) in enumerate(ch_plan.items()):
            if ch['budget'] > 0:
                ch_labels.append(name)
                ch_values.append(ch['budget'])
                ch_colors.append(color_list[i % len(color_list)])
        if ch_values:
            st.plotly_chart(donut(ch_labels, ch_values, ch_colors),
                            use_container_width=True, key='ov_donut')
            chart_legend(ch_labels, [fmt_vnd(v) for v in ch_values], ch_colors)

    with col2:
        section('Budget % Achieved by Channel', 'yellow')
        channels_plot = [i['channel'] for i in ov['overall']]
        pcts_plot     = [i['budget_actual'] / i['budget_plan'] * 100
                         if i['budget_plan'] else 0 for i in ov['overall']]
        bar_colors = [C['green'] if p >= 90 else C['yellow'] if p >= 50 else C['red']
                      for p in pcts_plot]
        fig = go.Figure(go.Bar(
            x=pcts_plot, y=channels_plot, orientation='h',
            marker_color=bar_colors,
            text=[f'{p:.0f}%' for p in pcts_plot],
            textposition='outside',
        ))
        fig.update_layout(
            height=320,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#E8E2D9', size=12),
            xaxis=dict(showgrid=False, zeroline=False, title='% vs Plan'),
            yaxis=dict(showgrid=False),
            margin=dict(l=10, r=60, t=20, b=20),
        )
        fig.add_vline(x=90, line_dash='dash', line_color='rgba(76,175,125,.5)')
        st.plotly_chart(fig, use_container_width=True, key='ov_bar_pct')

    st.markdown("---")

    # ── Insight ───────────────────────────────────────────────────────────────
    auto = _auto_insight(ov, tc, tp, total_roas)
    editable_insight('overview', auto, 'accent')


def _auto_insight(ov, tc, tp, roas):
    gmv_delta = (tc.get('gmv', 0) - tp.get('gmv', 0)) / tp.get('gmv', 1) * 100 if tp.get('gmv') else 0
    lines = [
        f"Tổng chi: {fmt_vnd(tc.get('spend',0))} | GMV: {fmt_vnd(tc.get('gmv',0))} | ROAS: {roas:.2f}x",
        f"So với kỳ trước: GMV {'tăng' if gmv_delta >= 0 else 'giảm'} {abs(gmv_delta):.1f}% "
        f"({fmt_vnd(tp.get('gmv',0))} → {fmt_vnd(tc.get('gmv',0))})",
    ]
    if roas < 3.0:
        lines.append(f"⚠️ ROAS tổng {roas:.2f}x dưới target 3.0x — cần review allocation ngân sách.")
    return '\n'.join(lines)
