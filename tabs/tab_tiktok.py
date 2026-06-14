import streamlit as st
from helpers import (kpi_html, kpi_grid, html_table, editable_insight,
                     section, fmt_vnd, fmt_num, C)


def render(data):
    st.markdown("## TikTok Ads")

    tt      = data.get('tiktok', {})
    total   = tt.get('total', {})
    plan_ch = data.get('plan', {}).get('channels', {}).get('TikTok', {})
    has_raw = bool(total)

    plan_budget = plan_ch.get('budget', 0)
    plan_kpi    = plan_ch.get('kpi', 0)

    if not has_raw and not plan_budget:
        st.markdown("""
        <div style='background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;
        padding:48px;text-align:center;margin-top:24px;'>
            <div style='font-size:18px;color:#0F172A;margin-bottom:8px;'>TikTok Ads</div>
            <div style='color:#64748B;font-size:13px;'>
                Thêm sheet <strong>raw tiktok</strong> vào file Excel để xem dữ liệu.<br>
                Hoặc thêm TikTok vào Media Plan để xem kế hoạch ngân sách.
            </div>
        </div>""", unsafe_allow_html=True)
        return

    # ── KPI Cards ────────────────────────────────────────────────────────────
    actual_spend = total.get('spend', 0)
    spend_pct    = actual_spend / plan_budget if plan_budget > 0 else None

    kpi_grid(
        kpi_html('TikTok Spend',
                 fmt_vnd(actual_spend),
                 f'Plan: {fmt_vnd(plan_budget)}' if plan_budget else '—',
                 'accent',
                 progress=spend_pct,
                 plan_label=f'{spend_pct*100:.0f}% vs plan' if spend_pct is not None else None),
        kpi_html('Impressions',
                 fmt_num(total.get('impressions', 0)),
                 '—', 'blue'),
        kpi_html('Video Views',
                 fmt_num(total.get('video_views', 0)),
                 f"VVR: {total.get('vvr', 0)*100:.1f}%" if has_raw else '—',
                 'purple'),
        kpi_html('Reach',
                 fmt_num(total.get('reach', 0)) if has_raw else '—',
                 '—', 'pink'),
        kpi_html('Clicks',
                 fmt_num(total.get('clicks', 0)) if has_raw else '—',
                 f"CTR: {total.get('ctr', 0)*100:.2f}%" if has_raw else '—',
                 'yellow'),
        cols=5,
    )

    if not has_raw:
        st.info('Chưa có raw data TikTok — hiển thị kế hoạch ngân sách từ Media Plan.')
        return

    st.markdown("---")

    # ── Campaign Breakdown ────────────────────────────────────────────────────
    by_format = tt.get('by_format', [])
    if by_format:
        section('Campaign / Format Breakdown', 'accent')
        headers = ['Type', 'Spend', 'Impressions', 'Video Views', 'VVR', 'Reach', 'Clicks']
        aligns  = ['left'] + ['right'] * 6
        rows = []
        for f in by_format:
            rows.append([
                f['type'],
                fmt_vnd(f.get('spend', 0)),
                fmt_num(f.get('impressions', 0)),
                fmt_num(f.get('video_views', 0)),
                f"{f.get('vvr', 0)*100:.1f}%",
                fmt_num(f.get('reach', 0)),
                fmt_num(f.get('clicks', 0)),
            ])
        # Total row
        tot_imp = sum(f.get('impressions', 0) for f in by_format)
        tot_vv  = sum(f.get('video_views', 0) for f in by_format)
        rows.append([
            '<strong>Total</strong>',
            f'<strong>{fmt_vnd(sum(f.get("spend",0) for f in by_format))}</strong>',
            f'<strong>{fmt_num(tot_imp)}</strong>',
            f'<strong>{fmt_num(tot_vv)}</strong>',
            f'<strong>{tot_vv/tot_imp*100:.1f}%</strong>' if tot_imp > 0 else '—',
            f'<strong>{fmt_num(sum(f.get("reach",0) for f in by_format))}</strong>',
            f'<strong>{fmt_num(sum(f.get("clicks",0) for f in by_format))}</strong>',
        ])
        html_table(headers, rows, aligns)
        st.markdown("---")

    # ── Top Ads ───────────────────────────────────────────────────────────────
    top_ads = tt.get('top_ads', [])
    df_raw  = data.get('tiktok_raw')

    if df_raw is not None and not df_raw.empty and 'Ad Name' in df_raw.columns:
        import pandas as pd

        BRAND_COLORS = {
            'PARADOX': C['purple'], 'HIGHCHIC': C['pink'], 'IAMSAIGON': C['yellow'],
            'CAOSTU': C['accent'],  'FNOS': C['blue'],
        }

        section('Top 10 — Video Views', 'purple')

        sort_col = 'VideoViews' if 'VideoViews' in df_raw.columns else 'Impressions'
        sum_cols = {c: 'sum'   for c in ['VideoViews', 'Impressions', 'Clicks', 'Spend', 'Reach'] if c in df_raw.columns}
        agg = df_raw.groupby('Ad Name').agg({
            **sum_cols,
            **{c: 'first' for c in ['Brand', 'Format', 'Camp Type'] if c in df_raw.columns},
        }).reset_index()

        if 'VideoViews' in agg.columns and 'Impressions' in agg.columns:
            agg['VVR'] = agg.apply(
                lambda r: r['VideoViews'] / r['Impressions'] * 100
                if r['Impressions'] > 0 else 0, axis=1
            )
        if 'Clicks' in agg.columns and 'Impressions' in agg.columns:
            agg['CTR'] = agg.apply(
                lambda r: r['Clicks'] / r['Impressions'] * 100
                if r['Impressions'] > 0 else 0, axis=1
            )

        top_df = agg.sort_values(sort_col, ascending=False).head(10)

        has_vv = 'VideoViews' in top_df.columns
        headers = ['#', 'Ad Name', 'Brand', 'Format',
                   'Video Views' if has_vv else 'Impressions',
                   'VVR' if has_vv else 'CTR', 'CTR', 'Spend']
        aligns  = ['center', 'left', 'left', 'center', 'right', 'right', 'right', 'right']
        rows = []
        for i, (_, row) in enumerate(top_df.iterrows(), 1):
            brand = str(row.get('Brand', '—'))
            bc    = BRAND_COLORS.get(brand, C['blue'])
            name  = str(row.get('Ad Name', ''))
            short = f'<span title="{name}">{name[:52]}…</span>' if len(name) > 52 else name
            vv_val = fmt_num(row.get('VideoViews', 0)) if has_vv else fmt_num(row.get('Impressions', 0))
            vvr    = f"{row.get('VVR', 0):.1f}%" if has_vv else f"{row.get('CTR', 0):.2f}%"
            rows.append([
                str(i), short,
                f'<span style="color:{bc};font-weight:500;font-size:11px">{brand}</span>',
                str(row.get('Format', row.get('Camp Type', '—'))),
                vv_val, vvr,
                f"{row.get('CTR', 0):.2f}%",
                fmt_vnd(row.get('Spend', 0)),
            ])
        html_table(headers, rows, aligns)

    elif top_ads:
        section('Top Ads — Video Views', 'purple')
        headers = ['#', 'Ad Name', 'Brand', 'Video Views', 'VVR', 'Spend']
        aligns  = ['center', 'left', 'left', 'right', 'right', 'right']
        rows = []
        BRAND_COLORS = {
            'PARADOX': C['purple'], 'HIGHCHIC': C['pink'], 'IAMSAIGON': C['yellow'],
            'CAOSTU': C['accent'],  'FNOS': C['blue'],
        }
        for i, ad in enumerate(top_ads[:10], 1):
            brand = str(ad.get('Brand', '—'))
            bc    = BRAND_COLORS.get(brand, C['blue'])
            name  = str(ad.get('Ad Name', ''))
            imp   = ad.get('Impressions', 0)
            vv    = ad.get('VideoViews', 0)
            vvr   = vv / imp * 100 if imp > 0 else 0
            rows.append([
                str(i),
                f'<span title="{name}">{name[:52]}…</span>' if len(name) > 52 else name,
                f'<span style="color:{bc};font-weight:500;font-size:11px">{brand}</span>',
                fmt_num(vv),
                f'{vvr:.1f}%',
                fmt_vnd(ad.get('Spend', 0)),
            ])
        html_table(headers, rows, aligns)

    st.markdown("---")
    editable_insight('tiktok', _auto_insight(total, by_format), 'purple')


def _auto_insight(total, by_format):
    lines = []
    if total.get('spend', 0) > 0:
        lines.append(
            f"TikTok Spend: {fmt_vnd(total['spend'])} | "
            f"Impressions: {fmt_num(total.get('impressions',0))} | "
            f"Video Views: {fmt_num(total.get('video_views',0))} | "
            f"VVR: {total.get('vvr',0)*100:.1f}%"
        )
    if by_format:
        top = by_format[0]
        lines.append(f"Format chi nhiều nhất: {top['type']} — {fmt_vnd(top['spend'])}")
    return '\n'.join(lines) if lines else 'Chưa có dữ liệu TikTok.'
