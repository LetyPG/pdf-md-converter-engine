import streamlit as st

def render_markdown_preview(content: str) -> None:
    """Renders the generated Markdown content in a scrollable view."""
    st.subheader("Markdown Preview")
    
    char_count = len(content)
    line_count = len(content.splitlines())
    st.caption(f"Length: {char_count:,} characters | {line_count:,} lines")

    # Scrollable container for preview
    with st.container(height=600):
        st.markdown(content)
    
    # Raw text expander for copy/pasting without rendering artifacts
    with st.expander("View raw Markdown syntax"):
        st.code(content, language="markdown")
