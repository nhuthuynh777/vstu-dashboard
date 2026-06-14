"""VSTu Paid Media Dashboard"""
import streamlit as st
from helpers import CSS, _get_pin, drive_list_files, drive_download_by_id, drive_upload_named
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

    # 1. Drive file list (nếu đã config secrets)
    drive_files = drive_list_files()

    if drive_files:
        file_names    = [f['name'] for f in drive_files]
        st.markdown('<div style="font-size:11px;color:#9CA3AF;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Kỳ báo cáo</div>', unsafe_allow_html=True)
        selected_name = st.selectbox("Kỳ báo cáo", file_names, key='drive_select', label_visibility='collapsed')
        selected_id   = next(f['id'] for f in drive_files if f['name'] == selected_name)
        if st.button("Load từ Drive", use_container_width=True, key='btn_load'):
            with st.spinner("Đang tải..."):
                data_bytes = drive_download_by_id(selected_id)
                st.session_state['_data_bytes'] = data_bytes
                st.session_state['_data_name']  = selected_name
                st.cache_data.clear()
        elif '_data_bytes' in st.session_state:
            data_bytes    = st.session_state['_data_bytes']
            selected_name = st.session_state.get('_data_name', '')
    else:
        if '_data_bytes' in st.session_state:
            data_bytes    = st.session_state['_data_bytes']
            selected_name = st.session_state.get('_data_name', '')

    # 2. Upload trực tiếp — PIN protected
    st.markdown('<hr style="border:none;border-top:0.5px solid rgba(0,0,0,0.08);margin:16px 0">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;color:#9CA3AF;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px">Upload report</div>', unsafe_allow_html=True)

    if not st.session_state.get('_upload_auth'):
        pin_input = st.text_input('PIN', placeholder='Nhập PIN để upload...',
                                  type='password', key='_upload_pin',
                                  label_visibility='collapsed')
        if st.button('Xác nhận PIN', key='_upload_pin_btn', use_container_width=True):
            if pin_input == _get_pin():
                st.session_state['_upload_auth'] = True
                st.rerun()
            else:
                st.error('PIN không đúng.')
    else:
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
            if drive_files:
                with st.spinner("Lưu lên Drive..."):
                    drive_upload_named(raw, uploaded.name)

        if st.button('Khoá upload', key='_upload_logout', use_container_width=True):
            st.session_state['_upload_auth'] = False
            st.rerun()

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
