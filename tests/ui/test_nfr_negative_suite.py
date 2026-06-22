import pytest
from playwright.sync_api import expect
from tests.utils.file_factory import (
    FileFactory,
    OversizedFileStrategy,
    InvalidExtensionStrategy,
    ImageOnlyPDFStrategy,
    ForbiddenContentPDFStrategy,
    CorruptedPDFStrategy
)

# Define all our negative scenarios in one place
NEGATIVE_SCENARIOS = [
    # (Strategy, Expected Error Text Substring)
    (OversizedFileStrategy(10.1), "File size (10.1 MB) exceeds limit"),
    (InvalidExtensionStrategy(".exe"), "are not allowed"),
    (InvalidExtensionStrategy(".sh"), "are not allowed"),
    (InvalidExtensionStrategy(".png"), "are not allowed"),
    (ImageOnlyPDFStrategy(), "Quality Validation Failed"), 
    (CorruptedPDFStrategy(), "RejectionReason.FILE_CORRUPTED"),
    (ForbiddenContentPDFStrategy("http://malicious.com"), "Quality Validation Failed"),
    (ForbiddenContentPDFStrategy("user@email.com"), "Quality Validation Failed"),
]

@pytest.fixture
def tmp_output_dir(tmp_path):
    """Pytest native fixture providing a temporary directory per test."""
    return tmp_path

@pytest.mark.parametrize("strategy, expected_error", NEGATIVE_SCENARIOS, ids=lambda x: type(x).__name__ if not isinstance(x, str) else x)
def test_system_rejection_rules(page, streamlit_server, tmp_output_dir, strategy, expected_error):
    # 1. Arrange: Generate synthetic file dynamically
    invalid_file = FileFactory.create(strategy, tmp_output_dir)
    
    # 2. Act: Upload the file
    page.goto(streamlit_server + "/setup") 
    
    # Upload the synthetic file using the hidden file input (give more time for large files)
    page.locator("input[type='file']").set_input_files(str(invalid_file), timeout=60000)
    
    # 3. Trigger the conversion only if the file passes client-side validation
    needs_conversion = not isinstance(strategy, (OversizedFileStrategy, InvalidExtensionStrategy))
    if needs_conversion:
        page.locator("button", has_text="Convert to Markdown").click()
    
    # 4. Assert: System does not crash and displays correct error
    # Because Streamlit might take a few seconds to process, we wait up to 15s.
    expect(page.locator("body")).to_contain_text(expected_error, timeout=15000)
