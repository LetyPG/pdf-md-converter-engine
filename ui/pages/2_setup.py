import streamlit as st
import time
from ui.services.conversion_service import ConversionService

st.set_page_config(page_title="Setup Conversion", page_icon="⚙️", layout="centered")

st.title("⚙️ Conversion Setup")

# Configuration
output_dir = st.text_input("Output Directory", value="./outputs", help="Base directory where the run_YYYYMMDD_HHMMSS folder will be created.")

# File Upload
st.subheader("Select PDF Document")

# Hide the '+' (Add files) button that Streamlit shows even when accept_multiple_files=False
st.markdown(
    """
    <style>
    /* Hide the Add Files button */
    button[aria-label="Add files"] {
        display: none !important;
    }
    /* Amplify the remove file (x) button and move it to the right-middle for better UX */
    button[aria-label^="Remove"] {
        position: absolute !important;
        right: 15px !important;
        top: 50% !important;
        transform: translateY(-50%) scale(1.6) !important;
        background-color: #ff4b4b40 !important;
        border-radius: 50% !important;
        z-index: 9999 !important;
        margin: 0 !important;
    }
    /* Amplify the sidebar text font size */
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebarNav"] span {
        font-size: 1.15rem !important;
    }
    /* Hide the default limit text entirely and inject custom uppercase note */
    [data-testid="stFileUploaderDropzoneInstructions"] {
        font-size: 0 !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"] > * {
        display: none !important;
    }
    [data-testid="stFileUploaderDropzoneInstructions"]::after {
        content: "Please make sure that the PDF size keeps the system processing requirement";
        display: block !important;
        font-size: 0.8rem !important;
        color: rgba(49, 51, 63, 0.6) !important;
        margin-top: 5px !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.info("The system currently processes one document per execution. Batch processing is not allowed.")
uploaded_file = st.file_uploader("Upload a PDF file (max 10MB)", type=["pdf"], accept_multiple_files=False)

if uploaded_file is not None:
    # Client-side validation
    is_valid, error_msg = ConversionService.validate_upload(uploaded_file)
    
    if not is_valid:
        st.error(f"❌ Validation Error: {error_msg}")
        st.button("Convert to Markdown", disabled=True)
    else:
        st.success("✅ File passed initial validation.")
        
        # Display Metadata
        with st.expander("File Metadata", expanded=True):
            st.code(f"""
File Name: {uploaded_file.name}
File Size: {uploaded_file.size / 1024 / 1024:.2f} MB
MIME Type: {uploaded_file.type}
            """.strip())
        
        # Conversion Trigger
        if st.button("Convert to Markdown", type="primary", use_container_width=True):
            if "conversion_attempt" in st.session_state:
                del st.session_state["conversion_attempt"]
                
            with st.status("Executing Pipeline...", expanded=True) as status:
                st.write("✓ PDF Validation")
                st.write("✓ Extraction")
                st.write("✓ IDM Generation")
                st.write("✓ Markdown Generation")
                st.write("✓ Artifact Validation")
                st.write("✓ Output Persistence")
                
                # Execute conversion
                result = ConversionService.execute_conversion(uploaded_file, output_dir)
                st.session_state["conversion_attempt"] = result
                
                if result.success:
                    status.update(label="Conversion Complete!", state="complete", expanded=False)
                    st.session_state["result"] = result
                    del st.session_state["conversion_attempt"]
                    time.sleep(0.5)
                    st.switch_page("pages/3_results.py")
                else:
                    status.update(label="Conversion Failed", state="error", expanded=True)
                    
        # Check if we have an attempt that failed
        if "conversion_attempt" in st.session_state and not st.session_state["conversion_attempt"].success:
            result = st.session_state["conversion_attempt"]
            st.error(result.error_message)
            
            if getattr(result, "is_quality_failure", False):
                st.warning("⚠️ Proceeding may cause issues in downstream AI agents or RAG pipelines. Are you sure you want to view these artifacts?")
                if st.button("Acknowledge Risks & View Artifacts", type="secondary"):
                    st.session_state["result"] = result
                    del st.session_state["conversion_attempt"]
                    st.switch_page("pages/3_results.py")
