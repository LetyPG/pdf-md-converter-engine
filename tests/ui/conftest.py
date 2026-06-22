import os
import subprocess
import time
import pytest
import socket

def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

@pytest.fixture(scope="session")
def streamlit_server():
    """Starts the Streamlit app before tests and tears it down after."""
    yield "http://localhost:8501"

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    # pytest-html >= 4.0 uses 'extras' instead of 'extra'
    extras = getattr(report, "extras", [])

    if report.when == "call":
        # Always screenshot 001 as a sanity check, plus ANY test that fails
        should_screenshot = report.failed or ("test_ui_001_landing_page_loads" in item.name)
        
        if should_screenshot:
            # Access to Playwright page fixture
            if "page" in item.funcargs:
                try:
                    page = item.funcargs["page"]
                    screenshot_dir = f"reports/screenshots/{item.name}.png"
                    page.screenshot(path=screenshot_dir)
                    
                    # Convert to base64 for self-contained report
                    import base64
                    with open(screenshot_dir, "rb") as f:
                        b64_image = base64.b64encode(f.read()).decode("utf-8")
                    
                    # Inject the base64 screenshot into the HTML of Pytest
                    import pytest_html
                    extras.append(pytest_html.extras.image(b64_image, mime_type="image/png"))
                except Exception as e:
                    print(f"Warning: Failed to take screenshot: {e}")
        report.extras = extras