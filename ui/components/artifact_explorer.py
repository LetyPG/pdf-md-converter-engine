import os
import streamlit as st
from pathlib import Path

def render_artifact_explorer(artifact_paths: dict[str, str]) -> None:
    """Displays generated files with download buttons."""
    st.subheader("Generated Artifacts")
    
    st.info("Files are saved locally in the `outputs/` directory. You can also download them directly here.")

    for artifact_name, file_path in artifact_paths.items():
        path_obj = Path(file_path)
        if not path_obj.exists():
            st.warning(f"File missing: {path_obj.name}")
            continue
            
        size_kb = path_obj.stat().st_size / 1024
        
        # Determine MIME type
        mime = "text/plain"
        if path_obj.suffix == ".md":
            mime = "text/markdown"
        elif path_obj.suffix == ".json":
            mime = "application/json"

        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"📄 **{path_obj.name}** ({size_kb:.1f} KB)")
        with col2:
            try:
                with open(file_path, "rb") as f:
                    file_data = f.read()
                st.download_button(
                    label=f"Download {artifact_name.capitalize()}",
                    data=file_data,
                    file_name=path_obj.name,
                    mime=mime,
                    key=f"download_{artifact_name}"
                )
            except Exception as e:
                st.error("Failed to load file for download")
