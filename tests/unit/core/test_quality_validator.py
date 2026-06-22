"""Unit tests for QualityValidator and all four CategoryValidator sub-validators.

All tests use IDM + Markdown string pairs built inline.
Sub-validators are mocked for orchestration-level tests.
Pattern mirrors previous stage unit tests.
"""
import pytest
from typing import List, Tuple
from unittest.mock import MagicMock

from src.core.validation.quality_validator import QualityValidator
from src.core.validation.validators.structural_validator import StructuralValidator
from src.core.validation.validators.rendering_validator import RenderingValidator
from src.core.validation.validators.security_validator import SecurityValidator
from src.core.validation.validators.completeness_validator import CompletenessValidator
from src.core.models.extraction import (
    BlockType, DocumentPage, ExtractionStrategy,
    HeadingBlock, IntermediateDocumentModel, ListBlock,
    ParagraphBlock, TableBlock,
)
from src.core.models.markdown import MarkdownResult
from src.core.models.validation import Finding, FindingCategory, FindingSeverity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _idm(*blocks) -> IntermediateDocumentModel:
    return IntermediateDocumentModel(
        strategy_used=ExtractionStrategy.NATIVE_TEXT,
        pages=[DocumentPage(page_number=1, blocks=list(blocks))],
    )


def _empty_idm() -> IntermediateDocumentModel:
    return IntermediateDocumentModel(strategy_used=ExtractionStrategy.NATIVE_TEXT, pages=[])


def _md(content: str, warnings=None) -> MarkdownResult:
    return MarkdownResult(content=content, warnings=warnings or [])


def _h(level: int, content: str) -> HeadingBlock:
    return HeadingBlock(block_id="b001", type=BlockType.HEADING, page=1, order=1, level=level, content=content)


def _p(content: str) -> ParagraphBlock:
    return ParagraphBlock(block_id="b002", type=BlockType.PARAGRAPH, page=1, order=2, content=content)


def _li(ordered: bool, items: list) -> ListBlock:
    return ListBlock(block_id="b003", type=BlockType.LIST, page=1, order=3, ordered=ordered, items=items)


def _table(headers, rows) -> TableBlock:
    return TableBlock(block_id="b004", type=BlockType.TABLE, page=1, order=4, headers=headers, rows=rows)


class MockCategoryValidator:
    """Returns configurable (score, findings) for orchestrator tests."""
    def __init__(self, score: float, findings=None):
        self._score = score
        self._findings = findings or []

    def validate(self, idm, markdown_content) -> Tuple[float, List[Finding]]:
        return self._score, self._findings


def _make_qv(s=100.0, r=100.0, sec=100.0, c=100.0) -> QualityValidator:
    return QualityValidator(
        structural_validator=MockCategoryValidator(s),
        rendering_validator=MockCategoryValidator(r),
        security_validator=MockCategoryValidator(sec),
        completeness_validator=MockCategoryValidator(c),
    )


# ---------------------------------------------------------------------------
# QualityValidator — Orchestration Tests
# ---------------------------------------------------------------------------

def test_overall_score_formula():
    """Overall score uses weighted formula: 35/25/25/15."""
    qv = _make_qv(s=80.0, r=100.0, sec=100.0, c=100.0)
    report = qv.validate(_empty_idm(), _md("content"))
    expected = round(80*0.35 + 100*0.25 + 100*0.25 + 100*0.15, 2)
    assert report.overall_score == expected


def test_passed_true_when_all_100():
    """passed=True when rendering=100 and security=100."""
    report = _make_qv().validate(_empty_idm(), _md("content"))
    assert report.passed is True


def test_passed_false_when_rendering_below_100():
    """passed=False when rendering_score < 100."""
    report = _make_qv(r=80.0).validate(_empty_idm(), _md("content"))
    assert report.passed is False


def test_passed_false_when_security_below_100():
    """passed=False when security_score < 100."""
    report = _make_qv(sec=60.0).validate(_empty_idm(), _md("content"))
    assert report.passed is False


def test_structural_warning_emitted_below_95():
    """Warning is emitted when structural_score < 95."""
    report = _make_qv(s=80.0).validate(_empty_idm(), _md("content"))
    assert any("Structural" in w for w in report.warnings)


def test_completeness_warning_emitted_below_95():
    """Warning is emitted when completeness_score < 95."""
    report = _make_qv(c=70.0).validate(_empty_idm(), _md("content"))
    assert any("Completeness" in w for w in report.warnings)


def test_no_warning_when_scores_at_threshold():
    """No threshold warnings when structural=95 and completeness=95."""
    report = _make_qv(s=95.0, c=95.0).validate(_empty_idm(), _md("content"))
    threshold_warnings = [w for w in report.warnings if "below threshold" in w]
    assert threshold_warnings == []


def test_markdown_result_warnings_propagated():
    """Warnings from MarkdownResult appear in ValidationReport.warnings."""
    report = _make_qv().validate(_empty_idm(), _md("content", warnings=["OCR skipped."]))
    assert "OCR skipped." in report.warnings


# ---------------------------------------------------------------------------
# StructuralValidator Tests
# ---------------------------------------------------------------------------

def test_structural_heading_count_match():
    """Matching heading counts yield 100% structural score for that check."""
    sv = StructuralValidator()
    idm = _idm(_h(1, "Title"))
    score, findings = sv.validate(idm, "# Title\n\nBody text.")
    heading_findings = [f for f in findings if "Heading count" in f.message]
    assert heading_findings == []


def test_structural_heading_count_mismatch():
    """Missing heading in Markdown produces a WARNING finding."""
    sv = StructuralValidator()
    idm = _idm(_h(1, "Title"), _h(2, "Section"))
    score, findings = sv.validate(idm, "# Title")
    assert any("Heading count" in f.message for f in findings)


def test_structural_list_count_match():
    """Matching list block count passes the list check."""
    sv = StructuralValidator()
    idm = _idm(_li(False, ["A", "B"]))
    score, findings = sv.validate(idm, "- A\n- B")
    assert not any("List count" in f.message for f in findings)


def test_structural_table_count_match():
    """Matching table block count passes the table check."""
    sv = StructuralValidator()
    idm = _idm(_table(["H1", "H2"], [["r1", "r2"]]))
    md = "| H1 | H2 |\n|---|---|\n| r1 | r2 |"
    score, findings = sv.validate(idm, md)
    assert not any("Table count" in f.message for f in findings)


# ---------------------------------------------------------------------------
# RenderingValidator Tests
# ---------------------------------------------------------------------------

class MockParser:
    def __init__(self, result: bool):
        self._result = result
    def validate(self, content: str) -> bool:
        return self._result


def test_rendering_passes_valid_markdown():
    """Valid Markdown with passing parser → rendering score = 100."""
    rv = RenderingValidator(MockParser(True))
    score, findings = rv.validate(_empty_idm(), "# Title\n\nParagraph text.")
    assert score == 100.0
    assert findings == []


def test_rendering_fails_unclosed_code_block():
    """Unclosed code fence produces ERROR finding."""
    rv = RenderingValidator(MockParser(True))
    score, findings = rv.validate(_empty_idm(), "```python\ncode without close")
    error_findings = [f for f in findings if f.severity == FindingSeverity.ERROR and "fence" in f.message.lower()]
    assert len(error_findings) >= 1
    assert score < 100.0


def test_rendering_fails_trailing_whitespace():
    """Line with trailing whitespace produces ERROR finding."""
    rv = RenderingValidator(MockParser(True))
    score, findings = rv.validate(_empty_idm(), "Text with trailing spaces   ")
    assert any("trailing whitespace" in f.message.lower() for f in findings)
    assert score < 100.0


def test_rendering_fails_when_parser_rejects():
    """Parser rejection produces ERROR finding and score < 100."""
    rv = RenderingValidator(MockParser(False))
    score, findings = rv.validate(_empty_idm(), "content")
    assert any("parser" in f.message.lower() for f in findings)
    assert score < 100.0


# ---------------------------------------------------------------------------
# SecurityValidator Tests
# ---------------------------------------------------------------------------

def test_security_passes_clean_markdown():
    """Clean Markdown with no unsafe content → security score = 100."""
    sv = SecurityValidator()
    score, findings = sv.validate(_empty_idm(), "# Title\n\nClean paragraph.")
    assert score == 100.0
    assert findings == []


def test_security_fails_on_url():
    """URL present → ERROR finding, security_score < 100."""
    sv = SecurityValidator()
    score, findings = sv.validate(_empty_idm(), "Visit https://example.com for details.")
    assert any("URL" in f.message for f in findings)
    assert score < 100.0


def test_security_fails_on_email():
    """Email address present → ERROR finding."""
    sv = SecurityValidator()
    score, findings = sv.validate(_empty_idm(), "Contact user@example.com")
    assert any("Email" in f.message for f in findings)


def test_security_fails_on_html():
    """Raw HTML present → ERROR finding."""
    sv = SecurityValidator()
    score, findings = sv.validate(_empty_idm(), "<script>alert()</script>")
    assert any("HTML" in f.message for f in findings)


def test_security_fails_on_image_syntax():
    """Markdown image syntax present → ERROR finding."""
    sv = SecurityValidator()
    score, findings = sv.validate(_empty_idm(), "![alt](https://img.com/a.png)")
    assert any("image" in f.message.lower() for f in findings)


# ---------------------------------------------------------------------------
# CompletenessValidator Tests
# ---------------------------------------------------------------------------

def test_completeness_passes_when_all_headings_present():
    """All IDM heading content found in Markdown → no missing section finding."""
    cv = CompletenessValidator()
    idm = _idm(_h(1, "Introduction"))
    score, findings = cv.validate(idm, "# Introduction\n\nBody text.")
    missing = [f for f in findings if "Heading content not found" in f.message]
    assert missing == []


def test_completeness_fails_missing_heading_content():
    """IDM heading content absent from Markdown → WARNING finding."""
    cv = CompletenessValidator()
    idm = _idm(_h(1, "Introduction"), _h(2, "Missing Section"))
    score, findings = cv.validate(idm, "# Introduction\n\nBody only.")
    assert any("Missing Section" in f.message for f in findings)
