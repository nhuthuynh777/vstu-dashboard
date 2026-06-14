import re
import streamlit as st
import plotly.graph_objects as go
from helpers import (kpi_html, kpi_grid, html_table, editable_insight,
                     section, badge, spend_badge, roas_badge, delta_badge,
                     fmt_vnd, fmt_num, donut, chart_legend, C)


def render(data):
    st.markdown("## Campaign Overview")

    ov   = data['overview']
    plan = data['plan']
    tc   = ov['total_current']
    tp   = ov['total_prev']
    ch_plan = plan.get('channels', {})

    # ── Derived values ────────────────────────────────────────────────────────
    total_spend  = tc.get('spend_all', tc.get('spend', 0))
    total_gmv    = tc.get('gmv', 0)
    total_orders = tc.get('orders', 0)
    total_roas   = tc.get('roas', 0)
    prev_gmv     = tp.get('gmv', 0)

    total_budget = plan.get('total_budget', 0)
    plan_gmv = sum(c.get('gmv', 0) for c in ch_plan.values())
    # Plan orders = plan GMV / actual AOV (media plan không có cột purchases riêng)
    actual_aov  = total_gmv / total_orders if total_orders else 0
    plan_orders = round(plan_gmv / actual_aov) if plan_gmv and actual_aov else 0

    spend_pct  = total_spend  / total_budget if total_budget  else None
    gmv_pct    = total_gmv    / plan_gmv     if plan_gmv      else None
    orders_pct = total_orders / plan_orders  if plan_orders   else None
    roas_target = 3.0
    roas_pct    = total_roas  / roas_target

    # ── KPI row ───────────────────────────────────────────────────────────────
    kpi_grid(
        kpi_html('Total Spend', fmt_vnd(total_spend),
                 f'Plan: {fmt_vnd(total_budget)}' if total_budget else 'No plan',
                 'accent', spend_pct,
                 f'Plan {fmt_vnd(total_budget)}' if total_budget else ''),
        kpi_html('Total GMV', fmt_vnd(total_gmv),
                 f'Plan: {fmt_vnd(plan_gmv)}' if plan_gmv else 'No plan',
                 'green', gmv_pct,
                 f'Plan {fmt_vnd(plan_gmv)}' if plan_gmv else ''),
        kpi_html('Overall ROAS', f'{total_roas:.2f}x',
                 f'Target: {roas_target:.1f}x{"  ✅" if total_roas >= roas_target else "  ⚠️"}',
                 'green' if total_roas >= roas_target else 'yellow',
                 roas_pct, f'Target {roas_target:.1f}x'),
        kpi_html('Total Orders', fmt_num(total_orders),
                 f'Plan: {fmt_num(plan_orders)}' if plan_orders else 'No plan',
                 'blue', orders_pct,
                 f'Plan {fmt_num(plan_orders)}' if plan_orders else ''),
        kpi_html('vs Last Period', delta_badge(total_gmv, prev_gmv),
                 f'Prev GMV: {fmt_vnd(prev_gmv)}', 'purple'),
        cols=5,
    )

    st.markdown("---")

    # ── Bảng 1: Plan vs Actual full breakdown ─────────────────────────────────
    section('Plan vs Actual — Full Breakdown', 'accent')

    headers = ['Channel', 'Budget Plan', 'Actual Spend', '% Spend',
               'KPI Plan', 'KPI Actual', '% KPI', 'ROAS']
    aligns  = ['left', 'right', 'right', 'center', 'right', 'right', 'center', 'center']
    rows_html = []
    for item in ov['overall']:
        ch     = item['channel']
        bp     = item['budget_plan']
        ba     = item['budget_actual']
        kp     = item['kpi_plan']
        ka     = item['kpi_actual']
        roas_a = item.get('roas_actual', 0)
        rows_html.append([
            f'<span style="color:#0F172A">{ch}</span>',
            fmt_vnd(bp), fmt_vnd(ba), spend_badge(ba / bp if bp else 0),
            fmt_num(kp), fmt_num(ka), spend_badge(ka / kp if kp else 0),
            roas_badge(roas_a) if roas_a > 0 else '—',
        ])
    html_table(headers, rows_html, aligns)

    st.markdown("---")

    # ── Bảng 2: Sale Performance MoM — interleaved layout ────────────────────
    section('Sale Performance — MoM Comparison', 'green')

    # Derive period labels from date_range (e.g. "2026-05-01 – ..." → T5 / T4)
    dr_raw = data.get('date_range', {}).get('raw', '')
    _m = re.search(r'\d{4}-(\d{2})-\d{2}', str(dr_raw))
    if _m:
        _cur_m  = int(_m.group(1))
        _prev_m = _cur_m - 1 if _cur_m > 1 else 12
        lbl_cur, lbl_prev = f'T{_cur_m}', f'T{_prev_m}'
    else:
        lbl_cur, lbl_prev = 'Hiện tại', 'Trước'

    sale_prev_map = {s['channel']: s for s in ov['sale_prev']}
    headers2 = [
        'Channel',
        f'GMV ({lbl_cur})', f'GMV ({lbl_prev})', 'Δ GMV',
        f'Spend ({lbl_cur})', f'Spend ({lbl_prev})', 'Δ Spend',
        f'ROAS ({lbl_cur})', f'ROAS ({lbl_prev})',
    ]
    aligns2 = ['left',
               'right', 'right', 'center',
               'right', 'right', 'center',
               'center', 'center']

    rows2 = []
    for s in ov['sale_current']:
        p = sale_prev_map.get(s['channel'], {})
        rows2.append([
            s['channel'],
            fmt_vnd(s['gmv']),          fmt_vnd(p.get('gmv', 0)),   delta_badge(s['gmv'],   p.get('gmv', 0)),
            fmt_vnd(s['spend']),        fmt_vnd(p.get('spend', 0)), delta_badge(s['spend'], p.get('spend', 0)),
            roas_badge(s['roas']),      roas_badge(p.get('roas', 0)),
        ])

    prev_spend_all = tp.get('spend_all', tp.get('spend', 0))
    rows2.append([
        '<strong>Total</strong>',
        fmt_vnd(tc.get('gmv', 0)),       fmt_vnd(tp.get('gmv', 0)),       delta_badge(tc.get('gmv', 0),   tp.get('gmv', 0)),
        fmt_vnd(total_spend),            fmt_vnd(prev_spend_all),          delta_badge(total_spend,        prev_spend_all),
        roas_badge(tc.get('roas', 0)),   roas_badge(tp.get('roas', 0)),
    ])
    html_table(headers2, rows2, aligns2)

    st.markdown("---")

    # ── Charts ────────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        section('Budget Allocation (Plan)', 'accent')
        ch_labels, ch_values, ch_colors = [], [], []
        color_list = [C['accent'], C['pink'], C['blue'], C['purple'], C['green'], C['yellow']]
        for i, (name, ch) in enumerate(ch_plan.items()):
            if ch.get('budget', 0) > 0:
                ch_labels.append(name)
                ch_values.append(ch['budget'])
                ch_colors.append(color_list[i % len(color_list)])
        if ch_values:
            total_bud = sum(ch_values)
            pcts_bud  = [v / total_bud * 100 for v in ch_values]
            center_bud = f'<b>{fmt_vnd(total_bud)}</b><br><span style="font-size:10px;color:#64748B">Total Budget</span>'
            st.plotly_chart(
                donut(ch_labels, ch_values, ch_colors, show_pct=True, center_text=center_bud),
                use_container_width=True, key='ov_budget_donut',
            )
            chart_legend(ch_labels, [fmt_vnd(v) for v in ch_values], ch_colors, pct_values=pcts_bud)

    with col2:
        section('GMV Contribution by Channel', 'green')
        gmv_color_map = {
            'FB Catalog Sale': C['pink'],
            'FB Retargeting':  C['blue'],
            'Shopee':          C['accent'],
        }
        gmv_labels = [s['channel'] for s in ov['sale_current'] if s.get('gmv', 0) > 0]
        gmv_values = [s['gmv']     for s in ov['sale_current'] if s.get('gmv', 0) > 0]
        gmv_colors = [gmv_color_map.get(ch, C['purple']) for ch in gmv_labels]
        if gmv_values:
            total_gmv_chart = sum(gmv_values)
            pcts_gmv        = [v / total_gmv_chart * 100 for v in gmv_values]
            center_gmv = f'<b>{fmt_vnd(total_gmv_chart)}</b><br><span style="font-size:10px;color:#64748B">Total GMV</span>'
            st.plotly_chart(
                donut(gmv_labels, gmv_values, gmv_colors, show_pct=True, center_text=center_gmv),
                use_container_width=True, key='ov_gmv_donut',
            )
            chart_legend(gmv_labels, [fmt_vnd(v) for v in gmv_values], gmv_colors, pct_values=pcts_gmv)
        else:
            st.caption('Chưa có dữ liệu GMV.')

    st.markdown("---")

    # ── Insight ───────────────────────────────────────────────────────────────
    auto = _auto_insight(ov, tc, tp, total_roas, total_spend, total_budget)
    editable_insight('overview', auto, 'accent')


def _auto_insight(ov, tc, tp, roas, total_spend, total_budget):
    gmv_delta = (tc.get('gmv', 0) - tp.get('gmv', 0)) / tp.get('gmv', 1) * 100 if tp.get('gmv') else 0
    spend_pct_str = f' ({total_spend/total_budget*100:.0f}% plan)' if total_budget else ''
    lines = [
        f"Tổng chi: {fmt_vnd(total_spend)}{spend_pct_str} | GMV: {fmt_vnd(tc.get('gmv',0))} | ROAS: {roas:.2f}x",
        f"So với kỳ trước: GMV {'tăng' if gmv_delta >= 0 else 'giảm'} {abs(gmv_delta):.1f}% "
        f"({fmt_vnd(tp.get('gmv',0))} → {fmt_vnd(tc.get('gmv',0))})",
    ]
    if roas < 3.0:
        lines.append(f"⚠️ ROAS tổng {roas:.2f}x dưới target 3.0x — cần review allocation ngân sách.")
    return '\n'.join(lines)
