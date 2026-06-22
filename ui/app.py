"""pdfmd_converter — Streamlit UI entry point.

Run with:
    streamlit run ui/app.py
"""
import streamlit as st

st.set_page_config(
    page_title="PDF → Markdown Converter",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Welcome to PDF-to-Markdown Engine")
st.write("Please select a page from the sidebar to begin.")

# If they land on app.py, automatically redirect to 1_home.py
st.switch_page("pages/1_home.py")
