import os
import pytest
from playwright.sync_api import Page, expect
from pathlib import Path

# Need a sample PDF for uploads
PDF_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../pdf_data/Test_Planning_Guide.pdf"))

def test_ui_001_landing_page_loads(page: Page, streamlit_server: str):
    """UI-001: Verify application startup and landing page."""
    page.goto(streamlit_server)
    
    # Verify title
    expect(page).to_have_title("PDF → Markdown Converter")
    
    # Verify we are on the Home page (it redirects from app.py)
    expect(page.locator("h1").first).to_contain_text("PDF to Markdown Engine")
    
    # Verify preconditions table exists
    expect(page.locator("text=PDF Processing Rules")).to_be_visible()

def test_ui_002_pdf_upload_shows_metadata(page: Page, streamlit_server: str):
    """UI-002: Verify PDF selection and metadata display."""
    page.goto(streamlit_server + "/setup")
    
    # Find the file input and upload
    # Streamlit file uploaders use a hidden input with specific data-testid
    page.set_input_files("input[type='file']", PDF_PATH)
    
    # Wait for the validation success message
    expect(page.locator("text=File passed initial validation")).to_be_visible(timeout=10000)
    
    # Verify metadata is displayed (File Name should be visible)
    expect(page.locator("text=Test_Planning_Guide.pdf")).to_be_visible()

def test_ui_003_invalid_file_rejected(page: Page, streamlit_server: str):
    """UI-003: Verify invalid file rejection."""
    page.goto(streamlit_server + "/setup")
    
    # Create a dummy txt file to upload
    dummy_txt = Path("dummy.txt")
    dummy_txt.write_text("Not a PDF")
    
    try:
        page.set_input_files("input[type='file']", str(dummy_txt.absolute()))
        
        # Verify error message (Streamlit native rejection for wrong mime type)
        expect(page.locator("span[role='alert']:has-text('not allowed')")).to_be_visible(timeout=5000)
        
        # The convert button should not exist (Streamlit doesn't render it if upload is invalid/None)
        button = page.locator("button:has-text('Convert to Markdown')")
        expect(button).not_to_be_visible()
    finally:
        if dummy_txt.exists():
            dummy_txt.unlink()

def test_ui_004_conversion_workflow(page: Page, streamlit_server: str):
    """UI-004: Verify successful conversion workflow."""
    page.goto(streamlit_server + "/setup")
    
    # Upload
    page.set_input_files("input[type='file']", PDF_PATH)
    expect(page.locator("text=File passed initial validation")).to_be_visible(timeout=10000)
    
    # Click convert
    page.locator("button:has-text('Convert to Markdown')").click()
    
    # Wait for redirect to Results page
    # Look for the Results Dashboard header
    expect(page.locator("h1").first).to_contain_text("Results Dashboard", timeout=30000)
    
    # Verify summary shows the source document
    expect(page.locator("text=Test_Planning_Guide.pdf")).to_be_visible()

def test_ui_005_artifact_visualization(page: Page, streamlit_server: str):
    """UI-005: Verify artifact visualization on results page."""
    # We must run the conversion first to get to the results page with data
    page.goto(streamlit_server + "/setup")
    page.set_input_files("input[type='file']", PDF_PATH)
    page.locator("button:has-text('Convert to Markdown')").click()
    
    expect(page.locator("h1").first).to_contain_text("Results Dashboard", timeout=30000)
    
    # Check Markdown Preview section
    expect(page.locator("text=Markdown Preview")).to_be_visible()
    
    # Check Validation Panel section
    expect(page.locator("text=Quality Validation")).to_be_visible()
    expect(page.locator("text=Overall Score")).to_be_visible()
    
    # Check Artifact Explorer section
    expect(page.locator("text=Generated Artifacts")).to_be_visible()

def test_ui_006_artifact_downloads(page: Page, streamlit_server: str):
    """UI-006: Verify artifact download buttons are present."""
    # Run conversion
    page.goto(streamlit_server + "/setup")
    page.set_input_files("input[type='file']", PDF_PATH)
    page.locator("button:has-text('Convert to Markdown')").click()
    
    expect(page.locator("h1").first).to_contain_text("Results Dashboard", timeout=30000)
    
    # Verify all 5 download buttons exist
    expect(page.locator("button:has-text('Download Markdown')")).to_be_visible()
    expect(page.locator("button:has-text('Download Validation')")).to_be_visible()
    expect(page.locator("button:has-text('Download Execution')")).to_be_visible()
    expect(page.locator("button:has-text('Download Logs')")).to_be_visible()
    expect(page.locator("button:has-text('Download Manifest')")).to_be_visible()
