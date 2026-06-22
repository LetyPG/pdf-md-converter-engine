"""Integration tests for QualityValidator.

Uses IntermediateDocumentModel + MarkdownResult pairs built programmatically.
Validates the full validation pipeline end-to-end.
"""
from src.core.validation.quality_validator import create_default_validator
from src.core.models.extraction import (
    BlockType, CodeBlock, DocumentPage, ExtractionStrategy,
    HeadingBlock, IntermediateDocumentModel, ListBlock,
    ParagraphBlock, TableBlock,
)
from src.core.models.markdown import MarkdownResult
from src.core.models.validation import FindingSeverity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _v():
    return create_default_validator()


def _idm(*blocks) -> IntermediateDocumentModel:
    return IntermediateDocumentModel(
        strategy_used=ExtractionStrategy.NATIVE_TEXT,
        pages=[DocumentPage(page_number=1, blocks=list(blocks))],
    )


def _md(content: str) -> MarkdownResult:
    return MarkdownResult(content=content)


def _h(level, content) -> HeadingBlock:
    return HeadingBlock(block_id="b001", type=BlockType.HEADING, page=1, order=1, level=level, content=content)


def _p(content) -> ParagraphBlock:
    return ParagraphBlock(block_id="b002", type=BlockType.PARAGRAPH, page=1, order=2, content=content)


def _table(headers, rows) -> TableBlock:
    return TableBlock(block_id="b003", type=BlockType.TABLE, page=1, order=3, headers=headers, rows=rows)


# ---------------------------------------------------------------------------
# Integration Test: Clean document passes
# ---------------------------------------------------------------------------

def test_integration_clean_document_passes():
    """Valid IDM + clean matching Markdown → passed=True, no ERROR findings."""
    idm = _idm(_h(1, "Introduction"), _p("This is the introduction."))
    markdown = "# Introduction\n\nThis is the introduction."
    report = _v().validate(idm, _md(markdown))

    assert report.passed is True
    error_findings = [f for f in report.findings if f.severity == FindingSeverity.ERROR]
    assert error_findings == []


# ---------------------------------------------------------------------------
# Integration Test: Security violation fails
# ---------------------------------------------------------------------------

def test_integration_security_violation_fails():
    """Markdown with URL → passed=False, security_score < 100."""
    idm = _idm(_p("Safe text."))
    markdown = "Visit https://example.com for more."
    report = _v().validate(idm, _md(markdown))

    assert report.passed is False
    assert report.security_score < 100.0


# ---------------------------------------------------------------------------
# Integration Test: Rendering violation fails
# ---------------------------------------------------------------------------

def test_integration_rendering_violation_fails():
    """Markdown with unclosed code block → passed=False, rendering_score < 100."""
    idm = _idm(_p("Code example."))
    markdown = "```python\nprint('unclosed')"
    report = _v().validate(idm, _md(markdown))

    assert report.passed is False
    assert report.rendering_score < 100.0


# ---------------------------------------------------------------------------
# Integration Test: Structural mismatch produces warning finding
# ---------------------------------------------------------------------------

def test_integration_structural_mismatch_warns():
    """IDM has 2 headings but Markdown has 1 → structural WARNING finding present."""
    idm = _idm(_h(1, "Chapter One"), _h(2, "Section One"))
    markdown = "# Chapter One\n\nOnly one heading."
    report = _v().validate(idm, _md(markdown))

    structural_warnings = [
        f for f in report.findings
        if f.severity == FindingSeverity.WARNING and "Heading count" in f.message
    ]
    assert len(structural_warnings) >= 1


# ---------------------------------------------------------------------------
# Integration Test: Overall score is computed correctly
# ---------------------------------------------------------------------------

def test_integration_overall_score_computed():
    """Overall score is always between 0 and 100."""
    idm = _idm(_h(1, "Title"), _p("Body."))
    markdown = "# Title\n\nBody."
    report = _v().validate(idm, _md(markdown))

    assert 0.0 <= report.overall_score <= 100.0


# ---------------------------------------------------------------------------
# Integration Test: Findings list is populated on violation
# ---------------------------------------------------------------------------

def test_integration_report_findings_populated():
    """A security violation populates the findings list with at least one ERROR."""
    idm = _idm(_p("Contact info."))
    markdown = "Contact admin@example.com for support."
    report = _v().validate(idm, _md(markdown))

    error_findings = [f for f in report.findings if f.severity == FindingSeverity.ERROR]
    assert len(error_findings) >= 1
