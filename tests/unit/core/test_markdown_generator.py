"""Unit tests for MarkdownGenerator and all concrete BlockRenderers.

All tests use IDM instances built inline — no PDF, no PyMuPDF, no file I/O.
Pattern mirrors tests/unit/core/test_extraction_engine.py from Stage 2.
"""
import pytest
from typing import Dict

from src.core.markdown.markdown_generator import MarkdownGenerator, create_default_renderers
from src.core.markdown.block_renderer import BlockRenderer
from src.core.markdown.renderers.heading_renderer import HeadingRenderer
from src.core.markdown.renderers.paragraph_renderer import ParagraphRenderer
from src.core.markdown.renderers.list_renderer import ListRenderer
from src.core.markdown.renderers.table_renderer import TableRenderer
from src.core.markdown.renderers.code_block_renderer import CodeBlockRenderer
from src.core.markdown.renderers.quote_renderer import QuoteRenderer
from src.core.markdown.renderers.figure_renderer import FigureRenderer
from src.core.markdown.renderers.diagram_renderer import DiagramRenderer
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
    QuoteBlock,
    TableBlock,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _gen() -> MarkdownGenerator:
    """Returns a MarkdownGenerator wired with all concrete renderers."""
    return MarkdownGenerator(create_default_renderers())


def _idm(*blocks, strategy=ExtractionStrategy.NATIVE_TEXT, warnings=None) -> IntermediateDocumentModel:
    """Builds a single-page IDM from a list of blocks."""
    return IntermediateDocumentModel(
        strategy_used=strategy,
        pages=[DocumentPage(page_number=1, blocks=list(blocks))],
        warnings=warnings or [],
    )


def _heading(level: int, content: str) -> HeadingBlock:
    return HeadingBlock(block_id="b001_001", type=BlockType.HEADING, page=1, order=1, level=level, content=content)


def _paragraph(content: str) -> ParagraphBlock:
    return ParagraphBlock(block_id="b001_001", type=BlockType.PARAGRAPH, page=1, order=1, content=content)


def _list(ordered: bool, items) -> ListBlock:
    return ListBlock(block_id="b001_001", type=BlockType.LIST, page=1, order=1, ordered=ordered, items=items)


def _table(headers, rows) -> TableBlock:
    return TableBlock(block_id="b001_001", type=BlockType.TABLE, page=1, order=1, headers=headers, rows=rows)


def _code(content: str, language=None) -> CodeBlock:
    return CodeBlock(block_id="b001_001", type=BlockType.CODE, page=1, order=1, language=language, content=content)


def _quote(content: str) -> QuoteBlock:
    return QuoteBlock(block_id="b001_001", type=BlockType.QUOTE, page=1, order=1, content=content)


def _figure(caption=None) -> FigureBlock:
    return FigureBlock(block_id="b001_001", type=BlockType.FIGURE, page=1, order=1, caption=caption)


def _diagram() -> DiagramBlock:
    return DiagramBlock(block_id="b001_001", type=BlockType.DIAGRAM, page=1, order=1, caption=None)


# ---------------------------------------------------------------------------
# Heading Renderer Tests
# ---------------------------------------------------------------------------

def test_render_h1_heading():
    result = _gen().generate(_idm(_heading(1, "Title")))
    assert result.content == "# Title"


def test_render_h2_heading():
    result = _gen().generate(_idm(_heading(2, "Section")))
    assert result.content == "## Section"


def test_render_h3_heading():
    result = _gen().generate(_idm(_heading(3, "Subsection")))
    assert result.content == "### Subsection"


def test_heading_level_clamped_to_six():
    """Heading level > 6 is clamped to H6."""
    renderer = HeadingRenderer()
    block = _heading(10, "Deep")
    assert renderer.render(block).startswith("######")


def test_heading_level_clamped_to_one():
    """Heading level < 1 is clamped to H1."""
    renderer = HeadingRenderer()
    block = _heading(0, "Root")
    assert renderer.render(block).startswith("# ")


# ---------------------------------------------------------------------------
# Paragraph Renderer Tests
# ---------------------------------------------------------------------------

def test_render_paragraph():
    result = _gen().generate(_idm(_paragraph("Hello world.")))
    assert result.content == "Hello world."


# ---------------------------------------------------------------------------
# List Renderer Tests
# ---------------------------------------------------------------------------

def test_render_unordered_list():
    result = _gen().generate(_idm(_list(False, ["Alpha", "Beta", "Gamma"])))
    assert result.content == "- Alpha\n- Beta\n- Gamma"


def test_render_ordered_list():
    result = _gen().generate(_idm(_list(True, ["First", "Second"])))
    assert result.content == "1. First\n2. Second"


# ---------------------------------------------------------------------------
# Table Renderer Tests
# ---------------------------------------------------------------------------

def test_render_table():
    result = _gen().generate(_idm(_table(["Name", "Age"], [["Alice", "30"], ["Bob", "25"]])))
    lines = result.content.split("\n")
    assert lines[0] == "| Name | Age |"
    assert lines[1] == "|---|---|"
    assert lines[2] == "| Alice | 30 |"
    assert lines[3] == "| Bob | 25 |"


def test_render_table_empty_cell():
    """Empty cells render as empty string between pipes."""
    result = _gen().generate(_idm(_table(["A", "B"], [["value", ""]])))
    assert "| value | |" in result.content


def test_render_table_no_headers_returns_empty():
    """Table with no headers renders as empty string (block is skipped)."""
    renderer = TableRenderer()
    block = _table([], [])
    assert renderer.render(block) == ""


# ---------------------------------------------------------------------------
# Code Block Renderer Tests
# ---------------------------------------------------------------------------

def test_render_code_with_language():
    result = _gen().generate(_idm(_code("print('hi')", language="python")))
    assert result.content == "```python\nprint('hi')\n```"


def test_render_code_no_language():
    result = _gen().generate(_idm(_code("SELECT 1")))
    assert result.content == "```\nSELECT 1\n```"


# ---------------------------------------------------------------------------
# Figure and Diagram Renderer Tests
# ---------------------------------------------------------------------------

def test_render_figure_with_caption():
    result = _gen().generate(_idm(_figure(caption="Figure 3")))
    assert result.content == "[Figure omitted: Figure 3]"


def test_render_figure_no_caption():
    result = _gen().generate(_idm(_figure()))
    assert result.content == "[Figure omitted]"


def test_render_diagram():
    result = _gen().generate(_idm(_diagram()))
    assert result.content == "[Diagram detected but not reconstructed]"


# ---------------------------------------------------------------------------
# Formatting Constraint Tests
# ---------------------------------------------------------------------------

def test_blocks_separated_by_one_blank_line():
    """Multiple blocks are joined by exactly one blank line (\n\n)."""
    idm = _idm(_heading(1, "Title"), _paragraph("Body text."))
    result = _gen().generate(idm)
    assert result.content == "# Title\n\nBody text."


def test_no_trailing_whitespace():
    """No line in the output ends with whitespace."""
    idm = _idm(_paragraph("Some text.   "))
    result = _gen().generate(idm)
    for line in result.content.split("\n"):
        assert line == line.rstrip(), f"Trailing whitespace found: {repr(line)}"


def test_unix_line_endings():
    """Output contains no CRLF sequences."""
    idm = _idm(_paragraph("Text"))
    result = _gen().generate(idm)
    assert "\r\n" not in result.content
    assert "\r" not in result.content


def test_output_is_deterministic():
    """Calling generate() twice with the same IDM returns identical output."""
    idm = _idm(_heading(1, "Title"), _paragraph("Body."))
    gen = _gen()
    assert gen.generate(idm).content == gen.generate(idm).content


# ---------------------------------------------------------------------------
# Security Gate Tests (second layer)
# ---------------------------------------------------------------------------

def test_second_security_gate_strips_url():
    """URLs surviving to the generator layer are stripped from output."""
    idm = _idm(_paragraph("Visit https://example.com today."))
    result = _gen().generate(idm)
    assert "https" not in result.content


def test_second_security_gate_strips_image_syntax():
    """Markdown image syntax is stripped entirely from output."""
    idm = _idm(_paragraph("Here is an image ![alt text](https://img.com/a.png)."))
    result = _gen().generate(idm)
    assert "![" not in result.content
    assert "https" not in result.content


def test_second_security_gate_raw_html_replaced():
    """Raw HTML tags are replaced with [HTML omitted] placeholder."""
    idm = _idm(_paragraph("<script>alert()</script>"))
    result = _gen().generate(idm)
    assert "<script>" not in result.content
    assert "[HTML omitted]" in result.content


# ---------------------------------------------------------------------------
# Warning Propagation Tests
# ---------------------------------------------------------------------------

def test_idm_warnings_propagated():
    """Warnings from the IDM are included in MarkdownResult.warnings."""
    idm = IntermediateDocumentModel(
        strategy_used=ExtractionStrategy.NATIVE_TEXT,
        pages=[],
        warnings=["OCR strategy selected but not yet implemented."],
    )
    result = _gen().generate(idm)
    assert any("OCR" in w for w in result.warnings)


def test_unknown_block_type_emits_warning_and_skips():
    """Unregistered block type is skipped with a warning. No crash."""
    # Register only HeadingRenderer — PARAGRAPH has no renderer
    gen = MarkdownGenerator({BlockType.HEADING: HeadingRenderer()})
    idm = _idm(_heading(1, "Title"), _paragraph("Body."))
    result = gen.generate(idm)
    assert "# Title" in result.content
    assert "Body." not in result.content
    assert any("paragraph" in w.lower() for w in result.warnings)
