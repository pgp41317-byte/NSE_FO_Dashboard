import streamlit as st
import streamlit.components.v1 as components
from streamlit_autorefresh import st_autorefresh
import subprocess
import sys
import os
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

HTML_1 = os.path.join(BASE_DIR, "nifty_dashboard_live.html")
HTML_2 = os.path.join(BASE_DIR, "nifty_intelligence.html")

st.set_page_config(
    page_title="NIFTY Live Terminal",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.stApp {
    background-color: #050b12;
}
header, footer {
    visibility: hidden;
}
.block-container {
    padding: 0rem;
    max-width: 100%;
}
</style>
""", unsafe_allow_html=True)

# Refresh Streamlit app every 60 seconds
st_autorefresh(interval=60 * 1000, key="auto_refresh")

# Run main.py to regenerate BOTH HTML files
with st.spinner("Refreshing live market data..."):
    try:
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        time.sleep(15)

        process.terminate()

    except Exception as e:
        st.error(f"Refresh failed: {e}")

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