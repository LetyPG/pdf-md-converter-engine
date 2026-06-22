import pytest
from playwright.sync_api import Page, expect
import time

# Test the simple upload functionality to detect any issue in the UI
def test_simple_upload(page: Page):
    page.goto("http://localhost:8501/setup")
    open("test.exe", "w").write("dummy")
    page.locator("input[type='file']").set_input_files("test.exe")
    expect(page.locator("body")).to_contain_text("are not allowed", timeout=5000)
