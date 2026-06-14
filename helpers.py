"""helpers.py — Shared UI components for VSTu Dashboard."""
import io
import json
import os
from pathlib import Path
import streamlit as st
import plotly.graph_objects as go

_INSIGHT_FILE = Path(__file__).parent / 'insight_notes.json'


def _load_insights():
    try:
        return json.loads(_INSIGHT_FILE.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _save_insight(tab_key, text):
    data = _load_insights()
    data[tab_key] = text
    _INSIGHT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _delete_insight(tab_key):
    data = _load_insights()
    data.pop(tab_key, None)
    _INSIGHT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _get_pin():
    try:
        return st.secrets.get('INSIGHT_PIN', '1234')
    except Exception:
        return os.environ.get('INSIGHT_PIN', '1234')


def drive_download_file():
    """Download data xlsx from Google Drive. Returns bytes or None."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload

        file_id = st.secrets.get('DRIVE_FILE_ID', '')
        if not file_id:
            return None
        creds_info = dict(st.secrets.get('GOOGLE_SERVICE_ACCOUNT', {}))
        if not creds_info:
            return None
        credentials = service_account.Credentials.from_service_account_info(
            creds_info, scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        request = service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = dl.next_chunk()
        return buf.getvalue()
    except Exception:
        return None


def drive_upload_file(file_bytes):
    """Replace data xlsx in Google Drive. Returns True on success."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload

        file_id = st.secrets.get('DRIVE_FILE_ID', '')
        creds_info = dict(st.secrets.get('GOOGLE_SERVICE_ACCOUNT', {}))
        if not file_id or not creds_info:
            return False
        credentials = service_account.Credentials.from_service_account_info(
            creds_info, scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        media = MediaIoBaseUpload(
            io.BytesIO(file_bytes),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        service.files().update(fileId=file_id, media_body=media).execute()
        return True
    except Exception:
        return False


C = dict(accent='#92400E', green='#16A34A', yellow='#B45309',
         pink='#BE185D', blue='#1D4ED8', red='#DC2626', purple='#6D28D9')

CSS = """
<style>
  /* ── Base ─────────────────────────────────────────────────── */
  .stApp { background-color:#F7F6F3; color:#1A1A1A; }
  .block-container { padding-top:1.5rem; padding-bottom:2rem; }

  /* ── KPI Cards ────────────────────────────────────────────── */
  .kpi-card {
    background:#FFFFFF;
    border:0.5px solid rgba(0,0,0,0.08);
    border-radius:12px;
    padding:18px 20px;
    display:flex;
    flex-direction:column;
    box-shadow:0 1px 4px rgba(0,0,0,0.04);
    position:relative;
    overflow:hidden;
  }
  .kpi-grid  { display:grid; gap:12px; align-items:stretch; margin-bottom:18px; }
  .kpi-label { color:#9CA3AF; font-size:10.5px; text-transform:uppercase; letter-spacing:.7px; margin-bottom:6px; font-weight:400; }
  .kpi-value { font-size:22px; font-weight:500; color:#1A1A1A; }
  .kpi-sub   { color:#6B7280; font-size:12px; margin-top:4px; line-height:1.5; font-weight:400; }
  .prog-bg   { background:#EDEBE6; border-radius:3px; height:4px; overflow:hidden; margin-top:10px; }
  .prog-fill { height:100%; border-radius:3px; }

  /* ── Tabs ─────────────────────────────────────────────────── */
  .stTabs [data-baseweb="tab-list"] {
    background:#EDECEA;
    border-radius:12px;
    padding:6px;
    gap:4px;
  }
  .stTabs [data-baseweb="tab"] {
    color:#6B7280;
    border-radius:9px;
    font-size:14px;
    font-weight:400;
    min-height:38px;
    padding-left:18px !important;
    padding-right:18px !important;
  }
  .stTabs [aria-selected="true"] {
    background:#FFFFFF !important;
    color:#4A2000 !important;
    font-weight:500 !important;
    box-shadow:0 2px 8px rgba(0,0,0,0.10) !important;
  }

  /* ── Tables ───────────────────────────────────────────────── */
  table    { width:100%; border-collapse:collapse; font-size:13px; }
  thead tr { background:#4A2000; }
  th {
    color:#FFF5EC;
    font-size:10.5px;
    text-transform:uppercase;
    letter-spacing:.6px;
    padding:10px 12px;
    border-bottom:none;
    font-weight:500;
  }
  td { padding:10px 12px; border-bottom:1px solid rgba(0,0,0,0.04); color:#1A1A1A; font-weight:400; }
  tr:hover td { background:rgba(74,32,0,0.03); }

  /* ── Sidebar footer ───────────────────────────────────────── */
  .sidebar-footer { margin-top:auto; padding-top:20px; }

  /* ── Hide chrome ──────────────────────────────────────────── */
  #MainMenu { visibility:hidden; } footer { visibility:hidden; }
</style>
"""


def kpi(label, value, sub="", color="accent", progress=None):
    prog = ""
    if progress is not None:
        pct = min(progress * 100, 100)
        prog = f'<div class="prog-bg" style="margin-top:8px"><div class="prog-fill" style="width:{pct:.1f}%;background:{C.get(color, C["accent"])}"></div></div>'
    sub_h = f'<div class="kpi-sub" style="margin-top:3px;line-height:1.4">{sub}</div>' if sub else ''
    st.markdown(f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
                f'<div class="kpi-value" style="margin-top:4px">{value}</div>{sub_h}{prog}</div>',
                unsafe_allow_html=True)


def badge(text, color='green'):
    cfg = {'green':  ('#16A34A', 'rgba(22,163,74,.10)'),
           'yellow': ('#B45309', 'rgba(180,83,9,.10)'),
           'red':    ('#DC2626', 'rgba(220,38,38,.10)'),
           'blue':   ('#1D4ED8', 'rgba(29,78,216,.10)')}
    tc, bg = cfg.get(color, cfg['blue'])
    return (f'<span style="background:{bg};color:{tc};padding:2px 9px;'
            f'border-radius:20px;font-size:11px;font-weight:500;'
            f'letter-spacing:.1px;white-space:nowrap">{text}</span>')


def pct_badge(actual, plan, invert=False):
    if not plan:
        return badge('—', 'blue')
    pct = actual / plan * 100
    color = ('green' if pct <= 110 else 'red') if invert else ('green' if pct >= 90 else 'red')
    return badge(f'{pct:.0f}%', color)


def _prog_html(progress, color, plan_label=''):
    if progress is None:
        return ''
    pct    = min(progress * 100, 100)
    fill_c = C.get(color, C['accent'])
    clr    = '#22c55e' if pct >= 90 else ('#f59e0b' if pct >= 50 else '#ef4444')
    label_row = (
        f'<div style="display:flex;justify-content:space-between;'
        f'margin-bottom:4px;font-size:10px;line-height:1.2">'
        f'<span style="color:#9CA3AF;font-weight:400">{plan_label}</span>'
        f'<span style="color:{clr};font-weight:500">{pct:.0f}%</span>'
        f'</div>'
    ) if plan_label else (
        f'<div style="text-align:right;margin-bottom:4px;font-size:10px;'
        f'color:{clr};font-weight:500">{pct:.0f}%</div>'
    )
    return (
        f'<div style="margin-top:auto;padding-top:8px">'
        f'{label_row}'
        f'<div class="prog-bg"><div class="prog-fill" style="width:{pct:.1f}%;background:{fill_c}"></div></div>'
        f'</div>'
    )


def kpi_html(label, value, sub='', color='accent', progress=None, plan_label=''):
    """KPI card — pill indicator thay cho border-top màu."""
    clr = C.get(color, C['accent'])
    # Pill: nếu có progress → badge % nhỏ ở top-right; nếu không → dot màu
    if progress is not None:
        pct     = min(progress * 100, 100)
        pill_c  = '#16A34A' if pct >= 90 else ('#B45309' if pct >= 50 else '#DC2626')
        pill_bg = 'rgba(22,163,74,.10)' if pct >= 90 else ('rgba(180,83,9,.10)' if pct >= 50 else 'rgba(220,38,38,.10)')
        pill    = (f'<span style="position:absolute;top:14px;right:14px;'
                   f'background:{pill_bg};color:{pill_c};'
                   f'font-size:10px;font-weight:500;padding:2px 7px;border-radius:20px;line-height:1.4">'
                   f'{pct:.0f}%</span>')
    else:
        pill = (f'<span style="position:absolute;top:16px;right:16px;'
                f'display:inline-block;width:6px;height:6px;border-radius:50%;'
                f'background:{clr};opacity:0.45"></span>')
    sub_h = f'<div class="kpi-sub" style="margin-top:3px;line-height:1.4">{sub}</div>' if sub else ''
    return (f'<div class="kpi-card">{pill}'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value" style="margin-top:4px">{value}</div>'
            f'{sub_h}{_prog_html(progress, color, plan_label)}</div>')


def kpi2_html(label, v1, v1_sub, v2, v2_sub, color='accent',
              progress=None, plan_label='', progress2=None, plan_label2=''):
    """Card 2-metric HTML — 2 cột ngang, mỗi cột có progress bar riêng."""
    s1 = f'<div class="kpi-sub" style="margin-top:3px;line-height:1.3">{v1_sub}</div>' if v1_sub else ''
    s2 = f'<div class="kpi-sub" style="margin-top:3px;line-height:1.3">{v2_sub}</div>' if v2_sub else ''
    p1 = _prog_html(progress,  color, plan_label)
    p2 = _prog_html(progress2, color, plan_label2)
    clr  = C.get(color, C['accent'])
    dot  = (f'<span style="position:absolute;top:16px;right:16px;'
            f'display:inline-block;width:6px;height:6px;border-radius:50%;'
            f'background:{clr};opacity:0.45"></span>')
    return (
        f'<div class="kpi-card">{dot}'
        f'<div class="kpi-label">{label}</div>'
        f'<div style="display:flex;flex:1;margin-top:6px">'
        f'  <div style="flex:1;min-width:0;padding-right:10px;display:flex;flex-direction:column">'
        f'    <div class="kpi-value" style="font-size:18px">{v1}</div>'
        f'    {s1}{p1}'
        f'  </div>'
        f'  <div style="flex:1;min-width:0;padding-left:10px;border-left:1px solid rgba(0,0,0,0.07);display:flex;flex-direction:column">'
        f'    <div class="kpi-value" style="font-size:18px;color:#6B7280">{v2}</div>'
        f'    {s2}{p2}'
        f'  </div>'
        f'</div>'
        f'</div>'
    )


def kpi_grid(*card_htmls, cols=None):
    """Render list card HTML trong CSS grid — tự equalize height."""
    n = cols or len(card_htmls)
    items = ''.join(card_htmls)
    st.markdown(
        f'<div class="kpi-grid" style="grid-template-columns:repeat({n},1fr)">{items}</div>',
        unsafe_allow_html=True
    )


def insight(html, color='accent'):
    cfg = {'accent': ('#92400E', '#FEF3C7'),
           'green':  ('#16A34A', '#DCFCE7'),
           'yellow': ('#B45309', '#FEF3C7')}
    bc, bg = cfg.get(color, cfg['accent'])
    st.markdown(f'<div style="background:{bg};border-left:3px solid {bc};border-radius:0 8px 8px 0;'
                f'padding:12px 16px;margin-top:14px;font-size:13px;color:#334155;line-height:1.7">{html}</div>',
                unsafe_allow_html=True)


def section(title, dot='accent'):
    dot_c = C.get(dot, C['accent'])
    st.markdown(f'<div style="font-size:13.5px;font-weight:500;color:#1A1A1A;margin:18px 0 10px;'
                f'display:flex;align-items:center;gap:8px">'
                f'<span style="width:7px;height:7px;border-radius:50%;background:{dot_c};'
                f'opacity:0.7;display:inline-block"></span>{title}</div>', unsafe_allow_html=True)


def rank_badge(n):
    if n == 1:
        return ('<span style="background:rgba(245,158,11,.2);color:#f59e0b;width:24px;height:24px;'
                'border-radius:50%;display:inline-flex;align-items:center;justify-content:center;'
                'font-size:11px;font-weight:700">1</span>')
    return (f'<span style="background:#F1F5F9;color:#64748B;width:24px;height:24px;'
            f'border-radius:50%;display:inline-flex;align-items:center;justify-content:center;'
            f'font-size:11px">{n}</span>')


def html_table(headers, rows, aligns=None):
    if aligns is None:
        aligns = ['left'] + ['right'] * (len(headers) - 1)
    ths = ''.join(
        f'<th style="color:#FFF5EC;font-size:10.5px;text-transform:uppercase;letter-spacing:.6px;'
        f'padding:10px 12px;text-align:{aligns[i]};border-bottom:none;font-weight:500">{h}</th>'
        for i, h in enumerate(headers)
    )
    trs = ''.join(
        '<tr>' + ''.join(
            f'<td style="padding:10px 12px;text-align:{aligns[i]};'
            f'border-bottom:1px solid rgba(0,0,0,0.04);font-weight:400">{cell}</td>'
            for i, cell in enumerate(row)
        ) + '</tr>'
        for row in rows
    )
    st.markdown(
        f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
        f'<thead><tr style="background:#4A2000">{ths}</tr></thead>'
        f'<tbody>{trs}</tbody></table>',
        unsafe_allow_html=True,
    )


def pva_table(rows):
    """rows = [(label, plan_val, actual_val, fmt_fn, badge_html)]"""
    ths = ''.join(
        f'<th style="color:#64748B;font-size:11px;text-transform:uppercase;padding:8px 10px;'
        f'text-align:{a};border-bottom:1px solid #E2E8F0">{h}</th>'
        for h, a in [('Metric', 'left'), ('Plan', 'right'), ('Actual', 'right'), ('% vs Plan', 'center')]
    )
    trs = ''
    for label, pv, av, fmt_fn, bdg in rows:
        trs += (f'<tr>'
                f'<td style="padding:9px 10px;border-bottom:1px solid rgba(42,42,42,.5);font-weight:500">{label}</td>'
                f'<td style="padding:9px 10px;border-bottom:1px solid rgba(42,42,42,.5);text-align:right;color:#555">{fmt_fn(pv) if pv else "—"}</td>'
                f'<td style="padding:9px 10px;border-bottom:1px solid rgba(42,42,42,.5);text-align:right;color:#C9A96E;font-weight:600">{fmt_fn(av)}</td>'
                f'<td style="padding:9px 10px;border-bottom:1px solid rgba(42,42,42,.5);text-align:center">{bdg}</td>'
                f'</tr>')
    st.markdown(f'<table style="width:100%;border-collapse:collapse;font-size:13px">'
                f'<thead><tr>{ths}</tr></thead><tbody>{trs}</tbody></table>',
                unsafe_allow_html=True)


def donut(labels, values, colors_list, custom_text=None, show_pct=False, center_text=None):
    """
    show_pct=True  → hiện % trong từng slice (trắng, radial), bỏ custom_text.
    center_text    → text ở giữa donut (thường là tổng).
    """
    if show_pct:
        textinfo = 'percent'
        textpos  = 'inside'
        tfont    = dict(size=12, color='#FFFFFF')
    elif custom_text:
        textinfo = 'text'
        textpos  = 'outside'
        tfont    = dict(size=11, color='#0F172A')
    else:
        textinfo = 'none'
        textpos  = 'none'
        tfont    = dict(size=11, color='#0F172A')

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.62,
        marker=dict(colors=colors_list, line=dict(color='#FFFFFF', width=3)),
        text=custom_text if not show_pct else None,
        textinfo=textinfo,
        textposition=textpos,
        insidetextorientation='radial',
        textfont=tfont,
        hovertemplate='<b>%{label}</b><br>%{text}<br>%{percent}<extra></extra>' if custom_text and not show_pct
                      else '<b>%{label}</b><br>%{value:,.0f} · %{percent}<extra></extra>',
    ))
    annotations = []
    if center_text:
        annotations.append(dict(
            text=center_text, x=0.5, y=0.5,
            font=dict(size=13, color='#0F172A'),
            showarrow=False,
        ))
    fig.update_layout(
        height=260, showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=20, b=20),
        font=dict(color='#0F172A', size=12),
        annotations=annotations,
    )
    return fig


def chart_legend(labels, value_strs, colors_list, pct_values=None):
    items = []
    for i, (l, v, c) in enumerate(zip(labels, value_strs, colors_list)):
        pct_str = f'<span style="color:#94A3B8;font-size:11px"> · {pct_values[i]:.1f}%</span>' \
                  if pct_values else ''
        items.append(
            f'<span style="display:inline-flex;align-items:center;gap:5px">'
            f'<span style="width:10px;height:10px;border-radius:50%;flex-shrink:0;background:{c}"></span>'
            f'<span style="color:#0F172A;font-weight:500">{l}</span>'
            f'<span style="color:#64748B"> · {v}</span>{pct_str}'
            f'</span>'
        )
    st.markdown(
        f'<div style="display:flex;gap:12px;flex-wrap:wrap;justify-content:center;'
        f'font-size:12px;margin-top:12px;line-height:1.8">'
        + ''.join(items) + '</div>',
        unsafe_allow_html=True,
    )


def kpi2(label, v1, v1_sub, v2, v2_sub, color="accent", progress=None):
    """Card với 2 chỉ số — fixed height 158px cùng kpi()."""
    prog = ""
    if progress is not None:
        pct = min(progress * 100, 100)
        prog = f'<div class="prog-bg" style="margin-top:6px"><div class="prog-fill" style="width:{pct:.1f}%;background:{C.get(color, C["accent"])}"></div></div>'
    s1 = f'<div class="kpi-sub" style="margin:1px 0 4px;line-height:1.3">{v1_sub}</div>' if v1_sub else '<div style="margin-bottom:4px"></div>'
    s2 = f'<div class="kpi-sub" style="margin-top:1px;line-height:1.3">{v2_sub}</div>' if v2_sub else ''
    st.markdown(
        f'<div class="kpi-card kpi-{color}">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value" style="font-size:17px;margin-top:3px">{v1}</div>'
        f'{s1}'
        f'<div class="kpi-value" style="font-size:17px;color:#64748B">{v2}</div>'
        f'{s2}{prog}</div>',
        unsafe_allow_html=True
    )


def ad_name_cell(name, short):
    return (f'<span title="{name}" style="display:block;line-height:1.4">{short}</span>')


def date_range_banner(dr):
    if not dr or not dr.get('start'):
        return
    s = dr['start'].strftime('%d/%m/%Y')
    e = dr['end'].strftime('%d/%m/%Y')
    days = dr.get('days', '—')
    st.markdown(
        f'<div style="color:#64748B;font-size:13px;margin-bottom:16px">'
        f'📅 Dữ liệu: <strong style="color:#0F172A">{s} – {e}</strong> · {days} ngày</div>',
        unsafe_allow_html=True
    )


def editable_insight(tab_key, auto_text, color='accent'):
    """
    Insight panel có thể chỉnh sửa với PIN protection.
    auto_text: plain text (newlines ok) — mặc định auto-generated.
    Text tùy chỉnh lưu trong insight_notes.json, override auto khi tồn tại.
    """
    dot_c = C.get(color, C['accent'])
    cfg = {
        'accent': ('#C9A96E', 'rgba(201,169,110,.10)'),
        'green':  ('#4CAF7D', 'rgba(76,175,125,.10)'),
        'yellow': ('#E8A838', 'rgba(232,168,56,.10)'),
        'blue':   ('#5B8DB8', 'rgba(91,141,184,.10)'),
        'pink':   ('#C97B8A', 'rgba(201,123,138,.10)'),
    }
    bc, bg = cfg.get(color, cfg['accent'])

    edit_key   = f'_ie_editing_{tab_key}'
    pin_ok_key = f'_ie_pinok_{tab_key}'

    saved    = _load_insights().get(tab_key)
    cur_text = saved if saved else auto_text
    is_custom = bool(saved)

    # Section header
    st.markdown(
        f'<div style="font-size:14px;font-weight:600;color:#0F172A;margin:28px 0 10px;'
        f'display:flex;align-items:center;gap:8px">'
        f'<span style="width:8px;height:8px;border-radius:50%;background:{dot_c};'
        f'display:inline-block"></span>📝 Nhận xét tổng hợp</div>',
        unsafe_allow_html=True
    )

    # Render insight box (plain text, newlines → <br>)
    display_text = cur_text if cur_text else '_(Chưa có nhận xét — click Edit để thêm)_'
    escaped = (display_text
               .replace('&', '&amp;')
               .replace('<', '&lt;')
               .replace('>', '&gt;')
               .replace('\n', '<br>'))
    st.markdown(
        f'<div style="background:{bg};border-left:3px solid {bc};border-radius:0 8px 8px 0;'
        f'padding:14px 18px;font-size:13px;color:#0F172A;line-height:1.8">{escaped}</div>',
        unsafe_allow_html=True
    )

    # Source label + edit button (cùng hàng, nút rõ hơn)
    lbl = '✏️ Đã chỉnh sửa thủ công' if is_custom else '🤖 Auto-generated'
    col_src, col_btn = st.columns([5, 1])
    with col_src:
        st.caption(lbl)
    with col_btn:
        if st.button('✏️ Sửa nhận xét', key=f'ie_open_{tab_key}', use_container_width=True):
            st.session_state[edit_key]   = True
            st.session_state[pin_ok_key] = False
            st.rerun()

    if not st.session_state.get(edit_key):
        return

    st.markdown('<div style="height:4px"></div>', unsafe_allow_html=True)

    if not st.session_state.get(pin_ok_key):
        # PIN verification
        c_lbl, c_pin, c_ok, c_x = st.columns([1, 4, 1, 1])
        with c_lbl:
            st.markdown('<div style="padding-top:8px;font-size:13px;color:#64748B">🔑 PIN:</div>',
                        unsafe_allow_html=True)
        with c_pin:
            pin_val = st.text_input('', placeholder='Nhập PIN...', type='password',
                                    key=f'ie_pin_{tab_key}', label_visibility='collapsed')
        with c_ok:
            if st.button('✓ OK', key=f'ie_pin_ok_{tab_key}'):
                if pin_val == _get_pin():
                    st.session_state[pin_ok_key] = True
                    st.rerun()
                else:
                    st.error('PIN không đúng.')
        with c_x:
            if st.button('✕', key=f'ie_pin_cancel_{tab_key}'):
                st.session_state[edit_key] = False
                st.rerun()
        return

    # Authenticated — edit mode
    new_text = st.text_area('', value=cur_text, height=150,
                             key=f'ie_ta_{tab_key}', label_visibility='collapsed')
    c_save, c_reset, c_cancel = st.columns([1, 2, 4])
    with c_save:
        if st.button('💾 Lưu', key=f'ie_save_{tab_key}'):
            _save_insight(tab_key, new_text)
            st.session_state[edit_key]   = False
            st.session_state[pin_ok_key] = False
            st.rerun()
    with c_reset:
        if st.button('↩️ Reset về auto', key=f'ie_reset_{tab_key}'):
            _delete_insight(tab_key)
            st.session_state[edit_key]   = False
            st.session_state[pin_ok_key] = False
            st.rerun()
    with c_cancel:
        if st.button('✕ Hủy', key=f'ie_cancel_{tab_key}'):
            st.session_state[edit_key]   = False
            st.session_state[pin_ok_key] = False
            st.rerun()


def fmt_vnd(v):
    v = float(v or 0)
    if abs(v) >= 1_000_000_000: return f'{v/1_000_000_000:.1f}B₫'
    if abs(v) >= 1_000_000:     return f'{v/1_000_000:.1f}M₫'
    if abs(v) >= 1_000:         return f'{v/1_000:.1f}K₫'
    return f'{v:,.0f}₫'


def fmt_num(v):
    v = float(v or 0)
    if abs(v) >= 1_000_000: return f'{v/1_000_000:.1f}M'
    if abs(v) >= 1_000:     return f'{v/1_000:.1f}K'
    return f'{v:,.0f}'


def fmt_pct(v):
    return f'{float(v or 0)*100:.1f}%' if abs(float(v or 0)) < 10 else f'{float(v or 0):.1f}%'


def delta_badge(current, prev):
    """Badge so sánh MoM — green nếu tăng, red nếu giảm."""
    if not prev:
        return badge('—', 'blue')
    d     = (current - prev) / abs(prev) * 100
    color = 'green' if d >= 0 else 'red'
    sign  = '+' if d >= 0 else ''
    return badge(f'{sign}{d:.1f}%', color)


def roas_badge(roas):
    roas = float(roas or 0)
    if roas >= 3.0: return badge(f'{roas:.2f}x', 'green')
    if roas >= 1.0: return badge(f'{roas:.2f}x', 'yellow')
    return badge(f'{roas:.2f}x', 'red')


def spend_badge(pct):
    """pct là tỷ lệ actual/plan (0–1)."""
    pct = float(pct or 0) * 100
    if pct >= 90: return badge(f'{pct:.0f}%', 'green')
    if pct >= 50: return badge(f'{pct:.0f}%', 'yellow')
    return badge(f'{pct:.0f}%', 'red')


def mini_bar_cell(pct, color=None, max_pct=100):
    """Inline mini bar + % label — dùng trong cột Share của bảng."""
    bar_c = color or C['accent']
    w     = min(max(float(pct or 0), 0), 100) / max_pct * 100
    return (
        f'<div style="display:flex;align-items:center;gap:8px;min-width:90px">'
        f'<div style="flex:1;background:#EDEBE6;border-radius:3px;height:5px;overflow:hidden;min-width:40px">'
        f'<div style="width:{w:.1f}%;background:{bar_c};height:100%;border-radius:3px"></div>'
        f'</div>'
        f'<span style="font-size:11px;color:#6B7280;min-width:34px;text-align:right;font-weight:400">'
        f'{float(pct or 0):.1f}%</span>'
        f'</div>'
    )


def drive_list_files():
    """List all xlsx files in Drive folder. Returns list of {id, name}."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        folder_id = st.secrets.get('DRIVE_FOLDER_ID', '')
        creds_info = dict(st.secrets.get('GOOGLE_SERVICE_ACCOUNT', {}))
        if not folder_id or not creds_info:
            return []
        credentials = service_account.Credentials.from_service_account_info(
            creds_info, scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='{mime}' and trashed=false",
            orderBy='createdTime desc',
            fields='files(id,name)',
        ).execute()
        return results.get('files', [])
    except Exception:
        return []


def drive_download_by_id(file_id):
    """Download file by ID. Returns bytes or None."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload

        creds_info = dict(st.secrets.get('GOOGLE_SERVICE_ACCOUNT', {}))
        credentials = service_account.Credentials.from_service_account_info(
            creds_info, scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        request = service.files().get_media(fileId=file_id)
        buf = io.BytesIO()
        dl = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = dl.next_chunk()
        return buf.getvalue()
    except Exception:
        return None


def drive_upload_named(file_bytes, file_name):
    """Upload file to Drive folder with specific name."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseUpload

        folder_id = st.secrets.get('DRIVE_FOLDER_ID', '')
        creds_info = dict(st.secrets.get('GOOGLE_SERVICE_ACCOUNT', {}))
        if not folder_id or not creds_info:
            return False
        credentials = service_account.Credentials.from_service_account_info(
            creds_info, scopes=['https://www.googleapis.com/auth/drive']
        )
        service = build('drive', 'v3', credentials=credentials)
        mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        meta = {'name': file_name, 'parents': [folder_id]}
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime)
        service.files().create(body=meta, media_body=media).execute()
        return True
    except Exception:
        return False
