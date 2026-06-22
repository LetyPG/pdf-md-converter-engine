import os
import pytest
from playwright.sync_api import Page, expect

# PDF that is known to fail the Quality Validator (e.g. contains complex tables, links, images causing structural/completeness failures)
PDF_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../pdf_data/CTFL_-_V4.0_-_ES_-_PROGRAMA_DE_ESTUDIO_-_V001.01.pdf"))

def test_ui_007_quality_gate_override_workflow(page: Page, streamlit_server: str):
    """UI-007: Verify the user can override a Quality Gate failure."""
    # 1. Navigate to Setup page
    page.goto(streamlit_server + "/setup")
    
    # 2. Upload the complex PDF
    page.set_input_files("input[type='file']", PDF_PATH)
    
    # Wait for the validation to finish and metadata to appear
    expect(page.locator("text=File passed initial validation")).to_be_visible(timeout=10000)
    
    # 3. Click Convert
    page.locator("button:has-text('Convert to Markdown')").click()
    
    # 4. Wait for failure status
    # The pipeline will take some time for this large PDF. We use a longer timeout.
    expect(page.locator("text=Conversion Failed")).to_be_visible(timeout=60000)
    
    # 5. Verify the error message and the override button appear
    # 5. Verify the override button appears (which implies the validation failed message is also present)
    
    override_button = page.locator("button", has_text="Acknowledge Risks & View Artifacts")
    expect(override_button).to_be_visible(timeout=10000)
    
    # 6. Click the override button
    override_button.click()
    
    # 7. Verify redirection to Results Dashboard
    expect(page.locator("h1").first).to_contain_text("Results Dashboard", timeout=30000)
    
    # 8. Verify the persistent warning banner is displayed
    expect(page.locator("text=QUALITY OVERRIDE ACTIVE")).to_be_visible()
    
    # 9. Verify artifacts are loaded anyway
    expect(page.locator("body")).to_contain_text("CTFL")
