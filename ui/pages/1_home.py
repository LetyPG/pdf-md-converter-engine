import streamlit as st

st.set_page_config(
    page_title="PDF → Markdown Converter",
    page_icon="📄",
    layout="centered"
)

st.title("📄 PDF to Markdown Engine")

# Apply consistent sidebar styling
st.markdown(
    """
    <style>
    /* Amplify the sidebar text font size */
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebarNav"] span {
        font-size: 1.15rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("### `PDF → Markdown Asset → Human / RAG / Agent`")
st.markdown("A local, deterministic utility for converting technical PDFs into structured, high-fidelity Markdown artifacts without relying on cloud services or runtime LLMs.")

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("Key Benefits")
    st.markdown("""
    - **Local-first execution:** No data leaves your machine
    - **No cloud dependency:** Completely offline capable
    - **Structured generation:** Headings, lists, and tables preserved
    - **AI-ready assets:** Clean Markdown ideal for RAG ingestion
    - **Deterministic processing:** Same input always yields same output
    """)

with col2:
    st.subheader("PDF Processing Rules")
    st.markdown("""
    | Requirement | Rule |
    |---|---|
    | **File Type** | PDF only |
    | **Max Size** | 10 MB |
    | **Text Layer** | Embedded text required (No OCR) |
    | **Encryption** | Not allowed |
    | **Corruption** | Must be a valid PDF |
    | **Batch mode** | Not supported in UI |
    """)

st.divider()

# Navigation button
if st.button("Start Conversion →", type="primary", use_container_width=True):
    st.switch_page("pages/2_setup.py")
