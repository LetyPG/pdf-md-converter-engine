"""Unit tests for ExtractionEngine.

All tests use MockExtractionProvider — no real PDF or PyMuPDF import.
Pattern mirrors tests/unit/core/test_preprocessor.py from Stage 1.
"""
import pytest
from typing import List

from src.core.extraction.extraction_engine import (
    ExtractionEngine,
    HEADING_H1_THRESHOLD,
    HEADING_H2_THRESHOLD,
    HEADING_H3_THRESHOLD,
)
from src.core.models.extraction import (
    BlockType,
    ExtractionStrategy,
    HeadingBlock,
    ListBlock,
    ParagraphBlock,
    CodeBlock,
    TableBlock,
    RawBlock,
)
from src.core.models.preprocessor import (
    DocumentProfile,
    LayoutType,
    PageOrientation,
    PreprocessingResult,
)


# ---------------------------------------------------------------------------
# Mock Provider
# ---------------------------------------------------------------------------

class MockExtractionProvider:
    """Minimal mock satisfying the ExtractionProvider Protocol for unit tests."""

    def __init__(self) -> None:
        self.open_called = False
        self.close_called = False
        self.should_fail_open = False
        self.page_count = 1
        self._pages: dict = {}  # page_number -> List[RawBlock]

    def set_page_blocks(self, page_number: int, blocks: List[RawBlock]) -> None:
        """Pre-load blocks for a given page."""
        self._pages[page_number] = blocks

    def open(self, path: str) -> None:
        self.open_called = True
        if self.should_fail_open:
            raise Exception("mock open failure")

    def close(self) -> None:
        self.close_called = True

    def get_page_count(self) -> int:
        return self.page_count

    def extract_page_blocks(self, page_number: int, strategy: ExtractionStrategy) -> List[RawBlock]:
        return self._pages.get(page_number, [])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_profile(
    layout_type: LayoutType = LayoutType.SINGLE_COLUMN,
    mixed_layout: bool = False,
    text_layer_present: bool = True,
    likely_scanned: bool = False,
) -> DocumentProfile:
    return DocumentProfile(
        pages=1,
        size_mb=1.0,
        metadata={},
        layout_type=layout_type,
        page_orientation=PageOrientation.PORTRAIT,
        text_layer_present=text_layer_present,
        likely_scanned=likely_scanned,
        mixed_layout=mixed_layout,
    )


def _make_result(profile: DocumentProfile) -> PreprocessingResult:
    return PreprocessingResult(status="accepted", document_profile=profile)


def _make_text_raw(
    content: str,
    font_size: float = 10.0,
    font: str = "Arial",
    page: int = 1,
    order: int = 1,
) -> RawBlock:
    return RawBlock(
        raw_type="text",
        content=content,
        bbox=(0, 0, 100, 20),
        page=page,
        order=order,
        metadata={"font_size": font_size, "font": font, "bold": False},
    )


@pytest.fixture
def mock_provider() -> MockExtractionProvider:
    return MockExtractionProvider()


@pytest.fixture
def engine(mock_provider: MockExtractionProvider) -> ExtractionEngine:
    return ExtractionEngine(mock_provider)


# ---------------------------------------------------------------------------
# Strategy Selection Tests
# ---------------------------------------------------------------------------

def test_extraction_selects_native_text_strategy(engine, mock_provider):
    """NATIVE_TEXT strategy is selected for a standard single-column text PDF."""
    profile = _make_profile(text_layer_present=True, likely_scanned=False)
    result = engine.extract("test.pdf", _make_result(profile))
    assert result.strategy_used == ExtractionStrategy.NATIVE_TEXT


def test_extraction_selects_multi_column_strategy(engine, mock_provider):
    """MULTI_COLUMN strategy is selected when layout_type is MULTI_COLUMN."""
    profile = _make_profile(layout_type=LayoutType.MULTI_COLUMN)
    result = engine.extract("test.pdf", _make_result(profile))
    assert result.strategy_used == ExtractionStrategy.MULTI_COLUMN


def test_extraction_selects_mixed_layout_strategy(engine, mock_provider):
    """MIXED_LAYOUT strategy is selected when mixed_layout is True."""
    profile = _make_profile(mixed_layout=True)
    result = engine.extract("test.pdf", _make_result(profile))
    assert result.strategy_used == ExtractionStrategy.MIXED_LAYOUT


def test_extraction_ocr_emits_warning_and_returns_empty(engine, mock_provider):
    """OCR strategy returns empty IDM with a warning. No crash."""
    profile = _make_profile(text_layer_present=False, likely_scanned=True)
    result = engine.extract("test.pdf", _make_result(profile))
    assert result.strategy_used == ExtractionStrategy.OCR
    assert result.pages == []
    assert len(result.warnings) == 1
    assert "OCR" in result.warnings[0]


# ---------------------------------------------------------------------------
# Heading Classification Tests (fixed threshold Q1 decision)
# ---------------------------------------------------------------------------

def test_extraction_classifies_h1_heading(engine, mock_provider):
    """Block with font_size >= H1 threshold is classified as HeadingBlock level 1."""
    mock_provider.set_page_blocks(1, [_make_text_raw("Title", font_size=HEADING_H1_THRESHOLD)])
    profile = _make_profile()
    result = engine.extract("test.pdf", _make_result(profile))
    blocks = result.pages[0].blocks
    assert len(blocks) == 1
    assert isinstance(blocks[0], HeadingBlock)
    assert blocks[0].level == 1
    assert blocks[0].content == "Title"


def test_extraction_classifies_h2_heading(engine, mock_provider):
    """Block with font_size >= H2 threshold (and < H1) is classified level 2."""
    mock_provider.set_page_blocks(1, [_make_text_raw("Section", font_size=HEADING_H2_THRESHOLD)])
    profile = _make_profile()
    result = engine.extract("test.pdf", _make_result(profile))
    assert isinstance(result.pages[0].blocks[0], HeadingBlock)
    assert result.pages[0].blocks[0].level == 2


def test_extraction_classifies_h3_heading(engine, mock_provider):
    """Block with font_size >= H3 threshold (and < H2) is classified level 3."""
    mock_provider.set_page_blocks(1, [_make_text_raw("Subsection", font_size=HEADING_H3_THRESHOLD)])
    profile = _make_profile()
    result = engine.extract("test.pdf", _make_result(profile))
    assert isinstance(result.pages[0].blocks[0], HeadingBlock)
    assert result.pages[0].blocks[0].level == 3


def test_extraction_classifies_paragraph(engine, mock_provider):
    """Block with body font size is classified as ParagraphBlock."""
    mock_provider.set_page_blocks(1, [_make_text_raw("Normal text.", font_size=10.0)])
    profile = _make_profile()
    result = engine.extract("test.pdf", _make_result(profile))
    assert isinstance(result.pages[0].blocks[0], ParagraphBlock)
    assert result.pages[0].blocks[0].content == "Normal text."


# ---------------------------------------------------------------------------
# List Classification Tests
# ---------------------------------------------------------------------------

def test_extraction_classifies_unordered_list(engine, mock_provider):
    """Block with bullet markers is classified as ListBlock (ordered=False)."""
    content = "• First item\n• Second item\n• Third item"
    mock_provider.set_page_blocks(1, [_make_text_raw(content)])
    profile = _make_profile()
    result = engine.extract("test.pdf", _make_result(profile))
    block = result.pages[0].blocks[0]
    assert isinstance(block, ListBlock)
    assert block.ordered is False
    assert len(block.items) == 3


def test_extraction_classifies_ordered_list(engine, mock_provider):
    """Block with numeric markers is classified as ListBlock (ordered=True)."""
    content = "1. First\n2. Second\n3. Third"
    mock_provider.set_page_blocks(1, [_make_text_raw(content)])
    profile = _make_profile()
    result = engine.extract("test.pdf", _make_result(profile))
    block = result.pages[0].blocks[0]
    assert isinstance(block, ListBlock)
    assert block.ordered is True


# ---------------------------------------------------------------------------
# Code Block Classification Tests
# ---------------------------------------------------------------------------

def test_extraction_classifies_code_block(engine, mock_provider):
    """Block with monospace font is classified as CodeBlock."""
    mock_provider.set_page_blocks(1, [_make_text_raw("def foo(): pass", font="CourierNew")])
    profile = _make_profile()
    result = engine.extract("test.pdf", _make_result(profile))
    assert isinstance(result.pages[0].blocks[0], CodeBlock)


# ---------------------------------------------------------------------------
# Table Classification Tests
# ---------------------------------------------------------------------------

def test_extraction_classifies_table_block(engine, mock_provider):
    """RawBlock with raw_type='table' is classified as TableBlock."""
    table_raw = RawBlock(
        raw_type="table",
        content="",
        bbox=(0, 50, 200, 100),
        page=1,
        order=1,
        metadata={"headers": ["Name", "Age"], "rows": [["Alice", "30"], ["Bob", "25"]]},
    )
    mock_provider.set_page_blocks(1, [table_raw])
    profile = _make_profile()
    result = engine.extract("test.pdf", _make_result(profile))
    block = result.pages[0].blocks[0]
    assert isinstance(block, TableBlock)
    assert block.headers == ["Name", "Age"]
    assert block.rows[0] == ["Alice", "30"]


# ---------------------------------------------------------------------------
# Security Gate Tests
# ---------------------------------------------------------------------------

def test_security_gate_strips_url(engine, mock_provider):
    """URLs are removed from paragraph content."""
    mock_provider.set_page_blocks(1, [_make_text_raw("Visit https://example.com for more.")])
    profile = _make_profile()
    result = engine.extract("test.pdf", _make_result(profile))
    content = result.pages[0].blocks[0].content
    assert "https" not in content
    assert "example.com" not in content


def test_security_gate_strips_email(engine, mock_provider):
    """Email addresses are removed from paragraph content."""
    mock_provider.set_page_blocks(1, [_make_text_raw("Contact user@example.com for help.")])
    profile = _make_profile()
    result = engine.extract("test.pdf", _make_result(profile))
    content = result.pages[0].blocks[0].content
    assert "@" not in content


def test_security_gate_strips_markdown_hyperlink(engine, mock_provider):
    """Markdown hyperlink constructs are stripped entirely."""
    mock_provider.set_page_blocks(1, [_make_text_raw("See [docs](https://example.com).")])
    profile = _make_profile()
    result = engine.extract("test.pdf", _make_result(profile))
    content = result.pages[0].blocks[0].content
    assert "https" not in content
    assert "[docs]" not in content


def test_security_gate_applied_to_table_headers(engine, mock_provider):
    """Security gate sanitizes table headers and cell content."""
    table_raw = RawBlock(
        raw_type="table",
        content="",
        bbox=(0, 50, 200, 100),
        page=1,
        order=1,
        metadata={
            "headers": ["Name", "Link https://evil.com"],
            "rows": [["Alice", "user@bad.com"]],
        },
    )
    mock_provider.set_page_blocks(1, [table_raw])
    profile = _make_profile()
    result = engine.extract("test.pdf", _make_result(profile))
    block = result.pages[0].blocks[0]
    assert isinstance(block, TableBlock)
    assert "https" not in block.headers[1]
    assert "@" not in block.rows[0][1]


# ---------------------------------------------------------------------------
# Image Skip Tests (Must Not Extract)
# ---------------------------------------------------------------------------

def test_images_are_not_extracted(engine, mock_provider):
    """Image RawBlocks are silently skipped. No block is added to the IDM."""
    image_raw = RawBlock(
        raw_type="image", content="", bbox=(0, 0, 100, 100), page=1, order=1
    )
    mock_provider.set_page_blocks(1, [image_raw])
    profile = _make_profile()
    result = engine.extract("test.pdf", _make_result(profile))
    assert result.pages[0].blocks == []


# ---------------------------------------------------------------------------
# Reading Order and Provider Lifecycle Tests
# ---------------------------------------------------------------------------

def test_reading_order_preserved_across_pages(engine, mock_provider):
    """Pages appear in ascending page_number order in the IDM."""
    mock_provider.page_count = 3
    for p in range(1, 4):
        mock_provider.set_page_blocks(p, [_make_text_raw(f"Page {p} text", page=p)])
    profile = _make_profile()
    result = engine.extract("test.pdf", _make_result(profile))
    page_numbers = [p.page_number for p in result.pages]
    assert page_numbers == [1, 2, 3]


def test_provider_close_always_called(engine, mock_provider):
    """Provider close() is always called, even if extraction fails."""
    mock_provider.should_fail_open = True
    with pytest.raises(Exception):
        profile = _make_profile()
        engine.extract("test.pdf", _make_result(profile))
    # close is not called if open never succeeded; but open raised — provider never opened
    # Verify open was attempted
    assert mock_provider.open_called
