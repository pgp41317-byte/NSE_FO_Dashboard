import streamlit as st
import subprocess
import os
import streamlit.components.v1 as components

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HTML_1 = os.path.join(BASE_DIR, "nifty_dashboard_live.html")
HTML_2 = os.path.join(BASE_DIR, "nifty_intelligence.html")

st.set_page_config(
    page_title="NIFTY Terminal",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.stApp {
    background-color: #050b12;
    color: white;
}
header, footer {
    visibility: hidden;
}
.block-container {
    padding-top: 0rem;
    padding-left: 0rem;
    padding-right: 0rem;
    max-width: 100%;
}
</style>
""", unsafe_allow_html=True)

# Auto refresh every 60 seconds
st.markdown(
    """
    <meta http-equiv="refresh" content="60">
    """,
    unsafe_allow_html=True
)

# Generate fresh HTML on every reload
subprocess.run(["python", "main.py"], cwd=BASE_DIR)

tab1, tab2 = st.tabs(["📈 NIFTY MC TERMINAL", "🧠 STOCK INTELLIGENCE"])

with tab1:
    if os.path.exists(HTML_1):
        with open(HTML_1, "r", encoding="utf-8", errors="ignore") as f:
            components.html(f.read(), height=1400, scrolling=True)
    else:
        st.error("nifty_dashboard_live.html not found")

with tab2:
    if os.path.exists(HTML_2):
        with open(HTML_2, "r", encoding="utf-8", errors="ignore") as f:
            components.html(f.read(), height=1400, scrolling=True)
    else:
        st.error("nifty_intelligence.html not found")