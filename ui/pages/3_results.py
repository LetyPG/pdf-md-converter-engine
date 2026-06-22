import streamlit as st

from ui.components.markdown_preview import render_markdown_preview
from ui.components.validation_panel import render_validation_panel
from ui.components.artifact_explorer import render_artifact_explorer

st.set_page_config(page_title="Results Dashboard", page_icon="📊", layout="wide")

st.title("📊 Results Dashboard")

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

if "result" not in st.session_state or st.session_state["result"] is None:
    st.warning("No conversion results available. Please run a conversion first.")
    if st.button("Go to Setup"):
        st.switch_page("pages/2_setup.py")
    st.stop()

result = st.session_state["result"]

if getattr(result, "is_quality_failure", False):
    st.error("⚠️ **QUALITY OVERRIDE ACTIVE**: This artifact failed the Quality Gate. It may contain formatting errors or security violations. Use in downstream pipelines with caution.", icon="🚨")

# Conversion Summary
with st.container():
    st.subheader("Conversion Summary")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Source File", result.source_document)
    col2.metric("Duration", f"{result.duration_ms} ms")
    col3.metric("Run ID", result.run_id)
    col4.metric("Output Directory", result.run_directory)

st.divider()

# Validation Panel
render_validation_panel(result.validation_data)

st.divider()

col_left, col_right = st.columns([2, 1], gap="large")

with col_left:
    # Markdown Preview
    render_markdown_preview(result.markdown_content)

with col_right:
    # Artifact Explorer
    render_artifact_explorer(result.artifact_paths)
    
    st.divider()
    
    # Run another
    st.write("### Start Over")
    if st.button("Run Another Conversion", type="primary", use_container_width=True):
        st.session_state["result"] = None
        st.switch_page("pages/2_setup.py")
