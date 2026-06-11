import streamlit as st


def render(data):
    st.markdown("## 🎵 TikTok Ads")
    st.markdown("""
    <div style='background:#141414;border:1px solid #2A2A2A;border-radius:12px;
    padding:48px;text-align:center;margin-top:24px;'>
        <div style='font-size:40px;margin-bottom:12px;'>🎵</div>
        <div style='font-size:18px;color:#E8E2D9;margin-bottom:8px;'>TikTok Ads — Coming Soon</div>
        <div style='color:#7A7670;font-size:13px;'>Sẽ bổ sung khi có dữ liệu TikTok Ads</div>
    </div>""", unsafe_allow_html=True)
