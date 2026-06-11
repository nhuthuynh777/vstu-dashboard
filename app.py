"""VSTu Paid Media Dashboard"""
import streamlit as st
from helpers import CSS, _get_pin, drive_list_files, drive_download_by_id, drive_upload_named
from parse_data import parse_all

st.set_page_config(
    page_title="VSTu Media Dashboard",
    page_icon="🖤",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CSS, unsafe_allow_html=True)

# ── Import tabs ───────────────────────────────────────────────────────────────
from tabs import tab_overview, tab_branding, tab_conversion, tab_shopee, tab_tiktok, tab_content

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🖤 VSTu Analytics")
    st.markdown("Paid Media Dashboard")
    st.markdown("---")

    data_bytes = None
    selected_name = None

    # 1. Try Drive file list
    drive_files = drive_list_files()

    if drive_files:
        file_names = [f['name'] for f in drive_files]
        selected_name = st.selectbox("📅 Chọn kỳ báo cáo", file_names, key='drive_select')
        selected_id   = next(f['id'] for f in drive_files if f['name'] == selected_name)

        if st.button("📥 Load", use_container_width=True, key='btn_load'):
            with st.spinner("Đang tải từ Drive..."):
                data_bytes = drive_download_by_id(selected_id)
                st.session_state['_data_bytes'] = data_bytes
                st.session_state['_data_name']  = selected_name
                st.cache_data.clear()
                st.rerun()
        elif '_data_bytes' in st.session_state:
            data_bytes    = st.session_state['_data_bytes']
            selected_name = st.session_state.get('_data_name', '')
    else:
        # Fallback: direct upload (no Drive configured)
        if '_data_bytes' in st.session_state:
            data_bytes    = st.session_state['_data_bytes']
            selected_name = st.session_state.get('_data_name', '')

    # 2. Upload panel (PIN-protected)
    st.markdown("---")
    with st.expander("📂 Upload report mới", expanded=not bool(data_bytes)):
        if not st.session_state.get('_upload_auth'):
            c_pin, c_btn = st.columns([3, 1])
            with c_pin:
                pin_input = st.text_input('', placeholder='Nhập PIN...', type='password',
                                          key='_upload_pin', label_visibility='collapsed')
            with c_btn:
                if st.button('🔓', key='_upload_pin_btn', use_container_width=True):
                    if pin_input == _get_pin():
                        st.session_state['_upload_auth'] = True
                        st.rerun()
                    else:
                        st.error('PIN không đúng.')
        else:
            uploaded = st.file_uploader(
                "Chọn file báo cáo (.xlsx)",
                type=['xlsx'],
                key='_file_upload',
            )
            if uploaded:
                raw = uploaded.read()
                st.session_state['_data_bytes'] = raw
                st.session_state['_data_name']  = uploaded.name
                data_bytes    = raw
                selected_name = uploaded.name

                # Auto-upload to Drive if configured
                if drive_files is not None:
                    with st.spinner("Đang lưu lên Drive..."):
                        ok = drive_upload_named(raw, uploaded.name)
                        if ok:
                            st.success("Đã lưu lên Drive!")
                        else:
                            st.warning("Không lưu được lên Drive — kiểm tra secrets.")
                st.cache_data.clear()
                st.rerun()

            if st.button("🔒 Logout", key='_upload_logout'):
                st.session_state['_upload_auth'] = False
                st.rerun()

    if selected_name:
        st.markdown("---")
        st.caption(f"📄 {selected_name}")


# ── Main content ──────────────────────────────────────────────────────────────
if not data_bytes:
    st.markdown("""
    <div style='background:#141414;border:1px solid #2A2A2A;border-radius:12px;
    padding:64px;text-align:center;margin-top:48px;'>
        <div style='font-size:48px;margin-bottom:16px;'>🖤</div>
        <div style='font-size:22px;color:#E8E2D9;margin-bottom:8px;'>VSTu Paid Media Dashboard</div>
        <div style='color:#7A7670;font-size:14px;margin-bottom:4px;'>
            Upload file báo cáo (.xlsx) ở sidebar để bắt đầu
        </div>
        <div style='color:#555;font-size:13px;'>
            Media report · Bi-weekly hoặc Monthly
        </div>
    </div>""", unsafe_allow_html=True)
    st.stop()


@st.cache_data(show_spinner="Đang đọc data...", ttl=3600)
def _parse(raw: bytes):
    return parse_all(raw)


data = _parse(data_bytes)

# Header
dr = data.get('date_range', {})
timeline = dr.get('raw', '')
if timeline:
    st.markdown(
        f'<div style="color:#7A7670;font-size:13px;margin-bottom:8px">'
        f'📅 <strong style="color:#E8E2D9">{timeline}</strong>'
        f'{"  ·  " + selected_name if selected_name else ""}</div>',
        unsafe_allow_html=True
    )

# ── Tabs ──────────────────────────────────────────────────────────────────────
t1, t2, t3, t4, t5, t6 = st.tabs([
    "📊 Overview",
    "🎨 Branding",
    "🎯 FB Conversion",
    "🛒 Shopee",
    "🎵 TikTok",
    "📋 Content",
])

with t1: tab_overview.render(data)
with t2: tab_branding.render(data)
with t3: tab_conversion.render(data)
with t4: tab_shopee.render(data)
with t5: tab_tiktok.render(data)
with t6: tab_content.render(data)
