import streamlit as st
from helpers import (kpi_html, kpi_grid, html_table, editable_insight,
                     section, fmt_vnd, fmt_num, C)


def render(data):
    st.markdown("## Branding Campaign — FB/IG")

    br      = data['branding']
    summary = {s['type']: s for s in br['summary']}
    total   = summary.get('Total', {})

    # ── KPI row (no plan comparison) ─────────────────────────────────────────
    kpi_grid(
        kpi_html('Total Branding Spend', fmt_vnd(total.get('spend', 0)), '—', 'accent'),
        kpi_html('Impressions',          fmt_num(total.get('impressions', 0)), '—', 'blue'),
        kpi_html('Total Reach',          fmt_num(total.get('reach', 0)), '—', 'purple'),
        kpi_html('Total Engagement',     fmt_num(total.get('engagement', 0)), '—', 'pink'),
        kpi_html('Avg Frequency',
                 f"{total.get('frequency', 0):.2f}",
                 'Impressions / Reach', 'yellow'),
        cols=5,
    )

    st.markdown("---")

    # ── Campaign Type Breakdown ───────────────────────────────────────────────
    section('Campaign Type Breakdown', 'accent')

    headers = ['Type', 'Spend', 'Impressions', 'Reach', 'Engagement',
               'Video Views', 'Clicks', 'Frequency']
    aligns  = ['left'] + ['right'] * 7
    rows = []
    for label in ['Reach', 'Engagement', 'Profile Visit', 'Total']:
        s = summary.get(label, {})
        rows.append([
            f'<strong>{label}</strong>' if label == 'Total' else label,
            fmt_vnd(s.get('spend', 0)),
            fmt_num(s.get('impressions', 0)),
            fmt_num(s.get('reach', 0)),
            fmt_num(s.get('engagement', 0)),
            fmt_num(s.get('video_views', 0)),
            fmt_num(s.get('clicks', 0)),
            f"{s.get('frequency', 0):.2f}",
        ])
    html_table(headers, rows, aligns)

    st.markdown("---")

    # ── Top 5 Ads — Engagement + CTR/VTR ─────────────────────────────────────
    section('Top 5 Ads — Engagement & Efficiency', 'yellow')

    df_raw = data.get('fb_raw')
    if df_raw is not None and not df_raw.empty and 'Ad Name' in df_raw.columns:
        import pandas as pd

        BRAND_COLORS = {
            'PARADOX': C['purple'], 'HIGHCHIC': C['pink'], 'IAMSAIGON': C['yellow'],
            'CAOSTU': C['accent'],  'FNOS': C['blue'],
        }

        def _top_ads_table(df_subset, n=5):
            """Aggregate df_subset by Ad Name và trả về top n sorted by Results."""
            if df_subset.empty:
                return pd.DataFrame()
            sum_cols   = {c: 'sum'   for c in ['Results', 'ThruPlays', 'Impressions', 'Clicks', 'Spend'] if c in df_subset.columns}
            first_cols = {c: 'first' for c in ['Brand', 'Format'] if c in df_subset.columns}
            agg = df_subset.groupby('Ad Name').agg({**sum_cols, **first_cols}).reset_index()
            agg['VTR'] = agg.apply(
                lambda r: r.get('ThruPlays', 0) / r['Impressions'] * 100
                if r.get('Impressions', 0) > 0 else 0, axis=1
            )
            agg['CTR'] = agg.apply(
                lambda r: r.get('Clicks', 0) / r['Impressions'] * 100
                if r.get('Impressions', 0) > 0 else 0, axis=1
            )
            return agg.sort_values('Results', ascending=False).head(n)

        def _render_top(top_df, show_vtr=True):
            if top_df.empty:
                st.caption('Chưa có dữ liệu.')
                return
            if show_vtr:
                headers = ['#', 'Ad Name', 'Brand', 'Format', 'Engagement', 'VTR', 'CTR', 'Spend']
                aligns  = ['center', 'left', 'left', 'center', 'right', 'right', 'right', 'right']
            else:
                headers = ['#', 'Ad Name', 'Brand', 'Format', 'Profile Visits', 'Impressions', 'CTR', 'Spend']
                aligns  = ['center', 'left', 'left', 'center', 'right', 'right', 'right', 'right']
            rows = []
            for i, (_, row) in enumerate(top_df.iterrows(), 1):
                brand = str(row.get('Brand', '—'))
                bc    = BRAND_COLORS.get(brand, C['blue'])
                name  = str(row.get('Ad Name', ''))
                short = f'<span title="{name}">{name[:52]}…</span>' if len(name) > 52 else name
                if show_vtr:
                    metric2 = f'{row["VTR"]:.1f}%' if row.get('ThruPlays', 0) > 0 \
                              else '<span style="color:#9CA3AF;font-size:11px">—</span>'
                    col5 = fmt_num(row.get('Results', 0))
                else:
                    metric2 = fmt_num(row.get('Impressions', 0))
                    col5    = fmt_num(row.get('Results', 0))
                rows.append([
                    str(i), short,
                    f'<span style="color:{bc};font-weight:500;font-size:11px">{brand}</span>',
                    str(row.get('Format', '—')),
                    col5, metric2,
                    f'{row["CTR"]:.2f}%',
                    fmt_vnd(row.get('Spend', 0)),
                ])
            html_table(headers, rows, aligns)

        if 'Camp Type' in df_raw.columns:
            section('Top 5 — Engagement', 'pink')
            df_eng = df_raw[df_raw['Camp Type'] == 'Engagement'].copy()
            _render_top(_top_ads_table(df_eng), show_vtr=True)

            st.markdown("---")

            section('Top 5 — Profile Visit', 'purple')
            df_pv = df_raw[df_raw['Camp Type'] == 'Profile Visit'].copy()
            _render_top(_top_ads_table(df_pv), show_vtr=False)
        else:
            st.caption('Không đủ dữ liệu để hiển thị top ads.')
    elif br['top_ads']:
        # Fallback to pre-aggregated data
        BRAND_COLORS = {
            'PARADOX': C['purple'], 'HIGHCHIC': C['pink'], 'IAMSAIGON': C['yellow'],
            'CAOSTU': C['accent'],  'FNOS': C['blue'],
        }
        headers_ads = ['#', 'Ad Name', 'Brand', 'Format', 'Engagement', 'VTR', 'Spend']
        aligns_ads  = ['center', 'left', 'left', 'center', 'right', 'right', 'right']
        rows_ads = []
        for i, ad in enumerate(br['top_ads'][:5], 1):
            bc = BRAND_COLORS.get(ad['brand'], C['blue'])
            name = ad['name']
            rows_ads.append([
                f'<strong>{i}</strong>',
                f'<span title="{name}">{name[:50]}…</span>' if len(name) > 50 else name,
                f'<span style="color:{bc};font-weight:600;font-size:11px">{ad["brand"]}</span>',
                ad['format'],
                fmt_num(ad['engagement']),
                f'{ad["vtr"]*100:.1f}%',
                fmt_vnd(ad['spend']),
            ])
        html_table(headers_ads, rows_ads, aligns_ads)

    st.markdown("---")
    editable_insight('branding', _auto_insight(br, summary, total), 'pink')


def _auto_insight(br, summary, total):
    lines = [
        f"Tổng Branding spend: {fmt_vnd(total.get('spend',0))} | "
        f"Impressions: {fmt_num(total.get('impressions',0))} | "
        f"Reach: {fmt_num(total.get('reach',0))} | "
        f"Frequency: {total.get('frequency',0):.2f}",
    ]
    eng = summary.get('Engagement', {})
    if eng.get('spend', 0) > 0:
        lines.append(f"Engagement: {fmt_num(eng.get('engagement',0))} engagements, "
                     f"spend {fmt_vnd(eng.get('spend',0))}")
    if br['top_ads']:
        top = br['top_ads'][0]
        lines.append(f"Ad engage cao nhất: {top['name'][:50]} — {fmt_num(top['engagement'])} engagements")
    return '\n'.join(lines)
