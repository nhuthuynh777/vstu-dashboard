"""VSTu Paid Media Dashboard"""
import streamlit as st
from helpers import CSS, _get_pin, drive_is_configured, drive_list_files, drive_download_by_id, drive_upload_named
from parse_data import parse_all

st.set_page_config(
    page_title="VSTu Media Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

from tabs import tab_overview, tab_branding, tab_conversion, tab_shopee, tab_tiktok, tab_content

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="padding:4px 0 16px">'
        '<div style="font-size:15px;font-weight:500;color:#1A1A1A">VSTu Analytics</div>'
        '<div style="font-size:12px;color:#9CA3AF;margin-top:2px">Paid Media Dashboard</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr style="border:none;border-top:0.5px solid rgba(0,0,0,0.08);margin:0 0 16px">', unsafe_allow_html=True)

    data_bytes    = None
    selected_name = None

    drive_configured = drive_is_configured()
    drive_files      = drive_list_files()  # sorted createdTime desc

    if drive_configured and not drive_files:
        st.warning("⚠️ Drive configured nhưng không tìm thấy file — kiểm tra folder đã share với service account chưa.", icon="⚠️")

    # Auto-load most recent file from Drive when session is fresh (F5 / new visitor)
    if drive_files and '_data_bytes' not in st.session_state:
        latest = drive_files[0]
        with st.spinner("Đang tải kỳ báo cáo mới nhất..."):
            _auto = drive_download_by_id(latest['id'])
            if _auto:
                st.session_state['_data_bytes'] = _auto
                st.session_state['_data_name']  = latest['name']

    # 1. Dropdown chọn kỳ (chỉ hiện khi có file trên Drive)
    if drive_files:
        file_names = [f['name'] for f in drive_files]
        st.markdown('<div style="font-size:11px;color:#9CA3AF;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Kỳ báo cáo</div>', unsafe_allow_html=True)
        current_name  = st.session_state.get('_data_name', file_names[0])
        default_idx   = file_names.index(current_name) if current_name in file_names else 0
        selected_name = st.selectbox("Kỳ báo cáo", file_names, index=default_idx,
                                     key='drive_select', label_visibility='collapsed')
        selected_id   = next(f['id'] for f in drive_files if f['name'] == selected_name)

        # Load khi user chọn kỳ khác
        if selected_name != st.session_state.get('_data_name'):
            with st.spinner("Đang tải..."):
                _bytes = drive_download_by_id(selected_id)
                if _bytes:
                    st.session_state['_data_bytes'] = _bytes
                    st.session_state['_data_name']  = selected_name
                    st.cache_data.clear()
                    st.rerun()

    # Lấy data từ session
    if '_data_bytes' in st.session_state:
        data_bytes    = st.session_state['_data_bytes']
        selected_name = st.session_state.get('_data_name', selected_name or '')

    # 2. Upload trực tiếp (session only) hoặc hướng dẫn upload lên Drive
    st.markdown('<hr style="border:none;border-top:0.5px solid rgba(0,0,0,0.08);margin:16px 0">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;color:#9CA3AF;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">Upload report</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Chọn file (.xlsx)", type=['xlsx'], key='_file_upload',
        label_visibility='collapsed',
    )
    if uploaded:
        raw           = uploaded.read()
        data_bytes    = raw
        selected_name = uploaded.name
        st.session_state['_data_bytes'] = raw
        st.session_state['_data_name']  = uploaded.name
        st.cache_data.clear()

    if not drive_files:
        st.markdown(
            '<div style="font-size:11px;color:#9CA3AF;margin-top:8px;line-height:1.5">'
            '💡 Để không phải upload lại sau F5:<br>'
            'Upload file xlsx lên <a href="https://drive.google.com/drive/folders/1OL2FEbbNyRacgBzmtUgGHoxoHqxsn126" '
            'target="_blank" style="color:#6366f1">Google Drive folder</a> này.'
            '</div>',
            unsafe_allow_html=True,
        )

    # File info
    if selected_name:
        st.markdown(
            f'<div style="margin-top:14px;padding:10px 12px;background:#F7F6F3;'
            f'border-radius:8px;border:0.5px solid rgba(0,0,0,0.07)">'
            f'<div style="font-size:10px;color:#9CA3AF;text-transform:uppercase;letter-spacing:.4px;margin-bottom:3px">File đang load</div>'
            f'<div style="font-size:12px;color:#1A1A1A;font-weight:400;word-break:break-all">{selected_name}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Sidebar footer — navigation info
    st.markdown(
        '<div class="sidebar-footer">'
        '<hr style="border:none;border-top:0.5px solid rgba(0,0,0,0.08);margin:20px 0 12px">'
        '<div style="font-size:11px;color:#9CA3AF">Overview · Branding · Conversion</div>'
        '<div style="font-size:11px;color:#9CA3AF;margin-top:2px">Shopee · TikTok · Content</div>'
        '<div style="font-size:10px;color:#CBD5E1;margin-top:8px">VSTu Paid Media · Internal</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── Main content ──────────────────────────────────────────────────────────────
if not data_bytes:
    st.markdown("""
    <div style='background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;
    padding:64px;text-align:center;margin-top:48px;box-shadow:0 1px 3px rgba(0,0,0,.06)'>
        <div style='font-size:48px;margin-bottom:16px;'>📊</div>
        <div style='font-size:22px;color:#0F172A;font-weight:600;margin-bottom:8px;'>VSTu Paid Media Dashboard</div>
        <div style='color:#64748B;font-size:14px;margin-bottom:4px;'>
            Upload file báo cáo (.xlsx) ở sidebar để bắt đầu
        </div>
        <div style='color:#94A3B8;font-size:13px;'>Media report · Bi-weekly hoặc Monthly</div>
    </div>""", unsafe_allow_html=True)
    st.stop()


with st.spinner("Đang đọc data..."):
    data = parse_all(data_bytes)

# Header
timeline = data.get('date_range', {}).get('raw', '')
if timeline:
    st.markdown(
        f'<div style="color:#94A3B8;font-size:13px;margin-bottom:8px">'
        f'📅 <strong style="color:#0F172A">{timeline}</strong>'
        f'{"  ·  " + selected_name if selected_name else ""}</div>',
        unsafe_allow_html=True,
    )

# ── Sheet debug (sidebar) ─────────────────────────────────────────────────────
with st.sidebar:
    with st.expander("🔍 Sheet detection", expanded=False):
        import openpyxl as _oxl
        from io import BytesIO as _BIO
        roles    = data.get('_roles', {})
        sheets   = data.get('_sheets', [])
        assigned = set(v for v in roles.values() if v)
        st.caption(f"All sheets: {sheets}")
        for k, v in roles.items():
            st.caption(f"{k} → {v or '(none)'}")
        st.caption("── Unassigned (first row headers) ──")
        _wb = _oxl.load_workbook(_BIO(st.session_state.get('_data_bytes', b'')), data_only=True)
        for sn in sheets:
            if sn not in assigned:
                _ws  = _wb[sn]
                row1 = [str(c.value) for c in next(_ws.iter_rows(max_row=1)) if c.value]
                st.caption(f"{sn!r}: {row1[:6]}")

# ── Tabs ──────────────────────────────────────────────────────────────────────
t1, t2, t3, t4, t5, t6 = st.tabs([
    "Overview", "Branding", "FB Conversion",
    "Shopee", "TikTok", "Content",
])

with t1: tab_overview.render(data)
with t2: tab_branding.render(data)
with t3: tab_conversion.render(data)
with t4: tab_shopee.render(data)
with t5: tab_tiktok.render(data)
with t6: tab_content.render(data)
