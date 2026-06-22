"""Integration tests for ExtractionEngine + PyMuPdfExtractionProvider.

Uses fitz to programmatically create synthetic golden PDFs — one per scenario.
Pattern mirrors tests/integration/test_preprocessor_integration.py from Stage 1.

Each fixture creates the minimal PDF needed to exercise one specific capability.
"""
import pytest
import fitz

from src.core.extraction.extraction_engine import (
    ExtractionEngine,
    HEADING_H1_THRESHOLD,
    HEADING_H2_THRESHOLD,
)
from src.adapters.pdf.pymupdf_extraction_provider import PyMuPdfExtractionProvider
from src.core.models.extraction import (
    BlockType,
    ExtractionStrategy,
    HeadingBlock,
    ListBlock,
    ParagraphBlock,
    TableBlock,
)
from src.core.models.preprocessor import (
    DocumentProfile,
    LayoutType,
    PageOrientation,
    PreprocessingResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_profile(
    layout_type: LayoutType = LayoutType.SINGLE_COLUMN,
    mixed_layout: bool = False,
    text_layer_present: bool = True,
    likely_scanned: bool = False,
) -> DocumentProfile:
    return DocumentProfile(
        pages=1,
        size_mb=0.1,
        metadata={},
        layout_type=layout_type,
        page_orientation=PageOrientation.PORTRAIT,
        text_layer_present=text_layer_present,
        likely_scanned=likely_scanned,
        mixed_layout=mixed_layout,
    )


def _make_result(profile: DocumentProfile) -> PreprocessingResult:
    return PreprocessingResult(status="accepted", document_profile=profile)


def _engine() -> ExtractionEngine:
    return ExtractionEngine(PyMuPdfExtractionProvider())


# ---------------------------------------------------------------------------
# Golden Fixture: Single-column plain text PDF
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def single_column_pdf(tmp_path_factory):
    """Synthetic PDF: one page, single column, plain body text."""
    path = tmp_path_factory.mktemp("golden") / "single_column.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), "This is a plain paragraph.", fontsize=10)
    doc.save(str(path))
    doc.close()
    return str(path)


# ---------------------------------------------------------------------------
# Golden Fixture: PDF with a heading (large font)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def heading_pdf(tmp_path_factory):
    """Synthetic PDF: one page with a large-font heading."""
    path = tmp_path_factory.mktemp("golden") / "heading.pdf"
    doc = fitz.open()
    page = doc.new_page()
    # Insert heading at H1 threshold font size
    page.insert_text((50, 80), "Document Title", fontsize=HEADING_H1_THRESHOLD)
    page.insert_text((50, 150), "Body paragraph text.", fontsize=10)
    doc.save(str(path))
    doc.close()
    return str(path)


# ---------------------------------------------------------------------------
# Golden Fixture: PDF with bullet list
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def list_pdf(tmp_path_factory):
    """Synthetic PDF: one page with a bullet list using unicode bullet character."""
    path = tmp_path_factory.mktemp("golden") / "list.pdf"
    doc = fitz.open()
    page = doc.new_page()
    list_text = "\u2022 First item\n\u2022 Second item\n\u2022 Third item"
    page.insert_text((50, 100), list_text, fontsize=10)
    doc.save(str(path))
    doc.close()
    return str(path)


# ---------------------------------------------------------------------------
# Golden Fixture: PDF with embedded URL in text
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def url_pdf(tmp_path_factory):
    """Synthetic PDF: one page with a URL embedded in paragraph text."""
    path = tmp_path_factory.mktemp("golden") / "url.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 100), "Visit https://example.com for details.", fontsize=10)
    doc.save(str(path))
    doc.close()
    return str(path)


# ---------------------------------------------------------------------------
# Golden Fixture: Multi-page PDF
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def multipage_pdf(tmp_path_factory):
    """Synthetic PDF: three pages each with distinct text."""
    path = tmp_path_factory.mktemp("golden") / "multipage.pdf"
    doc = fitz.open()
    for i in range(1, 4):
        page = doc.new_page()
        page.insert_text((50, 100), f"Content of page {i}.", fontsize=10)
    doc.save(str(path))
    doc.close()
    return str(path)


# ---------------------------------------------------------------------------
# Integration Test: Single-column extraction
# ---------------------------------------------------------------------------

def test_integration_single_column_extraction(single_column_pdf):
    """IDM is returned with at least one block for a plain single-column PDF."""
    engine = _engine()
    profile = _make_profile()
    result = engine.extract(single_column_pdf, _make_result(profile))

    assert result.strategy_used == ExtractionStrategy.NATIVE_TEXT
    assert len(result.pages) == 1
    assert len(result.pages[0].blocks) >= 1


# ---------------------------------------------------------------------------
# Integration Test: Heading detection
# ---------------------------------------------------------------------------

def test_integration_heading_detection(heading_pdf):
    """A HeadingBlock is present when a large-font title is in the PDF."""
    engine = _engine()
    profile = _make_profile()
    result = engine.extract(heading_pdf, _make_result(profile))

    all_blocks = result.pages[0].blocks
    headings = [b for b in all_blocks if isinstance(b, HeadingBlock)]
    assert len(headings) >= 1
    assert headings[0].level == 1
    assert headings[0].content.strip() != ""


# ---------------------------------------------------------------------------
# Integration Test: List detection
# ---------------------------------------------------------------------------

def test_integration_list_detection(list_pdf):
    """A ListBlock is present when bullet markers are in the PDF text."""
    engine = _engine()
    profile = _make_profile()
    result = engine.extract(list_pdf, _make_result(profile))

    all_blocks = result.pages[0].blocks
    lists = [b for b in all_blocks if isinstance(b, ListBlock)]
    assert len(lists) >= 1
    assert len(lists[0].items) >= 1


# ---------------------------------------------------------------------------
# Integration Test: Security gate removes URL
# ---------------------------------------------------------------------------

def test_integration_security_gate_strips_url(url_pdf):
    """No block in the IDM contains a URL after the security gate is applied."""
    engine = _engine()
    profile = _make_profile()
    result = engine.extract(url_pdf, _make_result(profile))

    for page in result.pages:
        for block in page.blocks:
            content = getattr(block, "content", "")
            assert "https" not in content, f"URL found in block: {block}"
            assert "http" not in content, f"URL found in block: {block}"


# ---------------------------------------------------------------------------
# Integration Test: Multi-page reading order
# ---------------------------------------------------------------------------

def test_integration_multipage_reading_order(multipage_pdf):
    """IDM pages appear in ascending page_number order."""
    engine = _engine()
    profile = _make_profile()
    result = engine.extract(multipage_pdf, _make_result(profile))

    assert len(result.pages) == 3
    page_numbers = [p.page_number for p in result.pages]
    assert page_numbers == [1, 2, 3]


# ---------------------------------------------------------------------------
# Integration Test: Provider close is always called
# ---------------------------------------------------------------------------

def test_integration_provider_close_always_called(single_column_pdf):
    """Provider is closed after extraction completes successfully."""
    provider = PyMuPdfExtractionProvider()
    engine = ExtractionEngine(provider)
    profile = _make_profile()
    engine.extract(single_column_pdf, _make_result(profile))
    # After extract(), doc should be None (closed)
    assert provider._doc is None
