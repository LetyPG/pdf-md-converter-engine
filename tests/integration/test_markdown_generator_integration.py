"""Integration tests for MarkdownGenerator.

Tests the full rendering pipeline using IntermediateDocumentModel instances
built programmatically — no PDF, no PyMuPDF.
Validates the complete end-to-end string output against golden expectations.
"""
from src.core.markdown.markdown_generator import create_default_generator
from src.core.models.extraction import (
    BlockType,
    CodeBlock,
    DiagramBlock,
    DocumentPage,
    ExtractionStrategy,
    FigureBlock,
    HeadingBlock,
    IntermediateDocumentModel,
    ListBlock,
    ParagraphBlock,
    TableBlock,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gen():
    return create_default_generator()


def _page(page_number: int, *blocks) -> DocumentPage:
    return DocumentPage(page_number=page_number, blocks=list(blocks))


def _idm(*pages, strategy=ExtractionStrategy.NATIVE_TEXT) -> IntermediateDocumentModel:
    return IntermediateDocumentModel(strategy_used=strategy, pages=list(pages))


def _h(level, content, bid="b001_001") -> HeadingBlock:
    return HeadingBlock(block_id=bid, type=BlockType.HEADING, page=1, order=1, level=level, content=content)


def _p(content, bid="b001_002") -> ParagraphBlock:
    return ParagraphBlock(block_id=bid, type=BlockType.PARAGRAPH, page=1, order=2, content=content)


def _l(ordered, items, bid="b001_003") -> ListBlock:
    return ListBlock(block_id=bid, type=BlockType.LIST, page=1, order=3, ordered=ordered, items=items)


def _t(headers, rows, bid="b001_004") -> TableBlock:
    return TableBlock(block_id=bid, type=BlockType.TABLE, page=1, order=4, headers=headers, rows=rows)


def _code(content, lang=None, bid="b001_005") -> CodeBlock:
    return CodeBlock(block_id=bid, type=BlockType.CODE, page=1, order=5, language=lang, content=content)


def _fig(caption=None, bid="b001_006") -> FigureBlock:
    return FigureBlock(block_id=bid, type=BlockType.FIGURE, page=1, order=6, caption=caption)


def _diag(bid="b001_007") -> DiagramBlock:
    return DiagramBlock(block_id=bid, type=BlockType.DIAGRAM, page=1, order=7, caption=None)


# ---------------------------------------------------------------------------
# Integration Test: Full document rendering
# ---------------------------------------------------------------------------

def test_integration_full_document_rendering():
    """IDM with heading + paragraph + unordered list renders in correct order."""
    idm = _idm(_page(1, _h(1, "Introduction"), _p("Overview text."), _l(False, ["Item A", "Item B"])))
    result = _gen().generate(idm)

    assert result.content.startswith("# Introduction")
    assert "Overview text." in result.content
    assert "- Item A" in result.content
    assert "- Item B" in result.content

    # Sections are separated by blank lines
    parts = result.content.split("\n\n")
    assert len(parts) == 3


# ---------------------------------------------------------------------------
# Integration Test: Table rendering fidelity
# ---------------------------------------------------------------------------

def test_integration_table_rendering_fidelity():
    """Table renders with correct pipe structure and separator row."""
    idm = _idm(_page(1, _t(["Col1", "Col2"], [["val1", "val2"], ["val3", "val4"]])))
    result = _gen().generate(idm)

    lines = result.content.split("\n")
    assert lines[0] == "| Col1 | Col2 |"
    assert lines[1] == "|---|---|"
    assert lines[2] == "| val1 | val2 |"
    assert lines[3] == "| val3 | val4 |"


# ---------------------------------------------------------------------------
# Integration Test: Code block rendering
# ---------------------------------------------------------------------------

def test_integration_code_block_rendering():
    """Code block is rendered with fenced syntax and language tag."""
    idm = _idm(_page(1, _code("x = 1\nprint(x)", lang="python")))
    result = _gen().generate(idm)

    assert result.content.startswith("```python")
    assert "x = 1" in result.content
    assert result.content.endswith("```")


# ---------------------------------------------------------------------------
# Integration Test: Security gate final pass
# ---------------------------------------------------------------------------

def test_integration_security_gate_final_pass():
    """URL in paragraph content is absent from the final Markdown output."""
    idm = _idm(_page(1, _p("See https://malicious.com for info.")))
    result = _gen().generate(idm)

    assert "https" not in result.content
    assert "malicious" not in result.content


def test_integration_security_gate_strips_image_syntax():
    """Markdown image syntax is stripped from assembled output."""
    idm = _idm(_page(1, _p("Image: ![photo](https://img.example.com/x.jpg)")))
    result = _gen().generate(idm)

    assert "![" not in result.content
    assert "https" not in result.content


# ---------------------------------------------------------------------------
# Integration Test: Multi-page IDM
# ---------------------------------------------------------------------------

def test_integration_multi_page_idm():
    """Blocks from all pages are rendered in page order."""
    idm = _idm(
        _page(1, _h(1, "Chapter One")),
        _page(2, _p("Page two body.")),
        _page(3, _p("Page three body.")),
    )
    result = _gen().generate(idm)

    assert "Chapter One" in result.content
    assert "Page two body." in result.content
    assert "Page three body." in result.content

    chapter_pos = result.content.index("Chapter One")
    page_two_pos = result.content.index("Page two body.")
    page_three_pos = result.content.index("Page three body.")
    assert chapter_pos < page_two_pos < page_three_pos


# ---------------------------------------------------------------------------
# Integration Test: Figure and Diagram placeholders
# ---------------------------------------------------------------------------

def test_integration_figure_and_diagram_placeholders():
    """FigureBlock and DiagramBlock produce expected placeholder strings."""
    idm = _idm(_page(1, _fig(caption="Figure 1"), _diag()))
    result = _gen().generate(idm)

    assert "[Figure omitted: Figure 1]" in result.content
    assert "[Diagram detected but not reconstructed]" in result.content
