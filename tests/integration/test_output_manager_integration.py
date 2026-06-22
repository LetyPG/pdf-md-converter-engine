"""Integration tests for OutputManager.

Uses pytest's tmp_path fixture — real filesystem writes, no mocks.
Validates end-to-end artifact persistence and directory structure.
"""
import json
import pytest
from pathlib import Path

from src.core.output.output_manager import create_default_output_manager
from src.core.models.markdown import MarkdownResult
from src.core.models.output import ExecutionMetadata
from src.core.models.validation import ValidationReport, Finding, FindingSeverity, FindingCategory


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _metadata(run_id: str = "20260619_000000", source: str = "document.pdf") -> ExecutionMetadata:
    return ExecutionMetadata(
        run_id=run_id,
        source_document=source,
        started_at="2026-06-19T00:00:00Z",
        completed_at="2026-06-19T00:00:06Z",
        duration_ms=6000,
        engine_version="1.0.0",
    )


def _report() -> ValidationReport:
    return ValidationReport(
        structural_score=100.0,
        rendering_score=100.0,
        security_score=100.0,
        completeness_score=100.0,
        overall_score=100.0,
        passed=True,
        warnings=[],
        findings=[],
    )


def _md(content: str = "# Title\n\nBody.") -> MarkdownResult:
    return MarkdownResult(content=content)


# ---------------------------------------------------------------------------
# Integration Test: Run directory created
# ---------------------------------------------------------------------------

def test_integration_run_directory_created(tmp_path):
    """A run_YYYYMMDD_HHMMSS directory is created inside the output base."""
    manager = create_default_output_manager(base_output_dir=str(tmp_path))
    result = manager.save(_md(), _report(), _metadata("20260619_120000"))

    run_dir = Path(result.run_directory)
    assert run_dir.is_dir()
    assert "run_20260619_120000" in run_dir.name


# ---------------------------------------------------------------------------
# Integration Test: All 5 artifacts exist
# ---------------------------------------------------------------------------

def test_integration_all_artifacts_exist(tmp_path):
    """All 5 artifacts are present in the run directory after save."""
    manager = create_default_output_manager(base_output_dir=str(tmp_path))
    result = manager.save(_md(), _report(), _metadata())

    run_dir = Path(result.run_directory)
    assert (run_dir / "document.md").is_file()
    assert (run_dir / "validation.json").is_file()
    assert (run_dir / "execution.json").is_file()
    assert (run_dir / "logs.txt").is_file()
    assert (run_dir / "manifest.json").is_file()


# ---------------------------------------------------------------------------
# Integration Test: Markdown content fidelity
# ---------------------------------------------------------------------------

def test_integration_markdown_content_correct(tmp_path):
    """document.md contains exactly the MarkdownResult.content string."""
    manager = create_default_output_manager(base_output_dir=str(tmp_path))
    content = "# Document Title\n\nSome paragraph text."
    result = manager.save(_md(content), _report(), _metadata())

    md_file = Path(result.run_directory) / "document.md"
    assert md_file.read_text(encoding="utf-8") == content


# ---------------------------------------------------------------------------
# Integration Test: Validation JSON is valid and contains expected keys
# ---------------------------------------------------------------------------

def test_integration_validation_json_valid(tmp_path):
    """validation.json is valid JSON with required score keys."""
    report = ValidationReport(
        structural_score=95.0,
        rendering_score=100.0,
        security_score=100.0,
        completeness_score=90.0,
        overall_score=96.25,
        passed=True,
        warnings=["Completeness score below threshold: 90.0"],
        findings=[
            Finding(
                severity=FindingSeverity.WARNING,
                category=FindingCategory.COMPLETENESS,
                message="Missing section detected.",
                location="Page 5",
            )
        ],
    )
    manager = create_default_output_manager(base_output_dir=str(tmp_path))
    result = manager.save(_md(), report, _metadata())

    val_file = Path(result.run_directory) / "validation.json"
    data = json.loads(val_file.read_text(encoding="utf-8"))

    assert data["structural_score"] == 95.0
    assert data["rendering_score"] == 100.0
    assert data["security_score"] == 100.0
    assert data["passed"] is True
    assert len(data["findings"]) == 1
    assert data["findings"][0]["severity"] == "WARNING"


# ---------------------------------------------------------------------------
# Integration Test: Manifest lists 5 artifacts
# ---------------------------------------------------------------------------

def test_integration_manifest_lists_five_artifacts(tmp_path):
    """manifest.json artifacts array contains exactly 5 filenames."""
    manager = create_default_output_manager(base_output_dir=str(tmp_path))
    result = manager.save(_md(), _report(), _metadata())

    manifest_file = Path(result.run_directory) / "manifest.json"
    data = json.loads(manifest_file.read_text(encoding="utf-8"))

    assert len(data["artifacts"]) == 5
    assert set(data["artifacts"]) == {
        "document.md", "validation.json", "execution.json", "logs.txt", "manifest.json"
    }


# ---------------------------------------------------------------------------
# Integration Test: Collision handling produces unique directory
# ---------------------------------------------------------------------------

def test_integration_collision_handling(tmp_path):
    """Second save with same run_id produces a _001-suffixed directory."""
    manager = create_default_output_manager(base_output_dir=str(tmp_path))
    result_1 = manager.save(_md("First run."), _report(), _metadata("20260619_090000"))
    result_2 = manager.save(_md("Second run."), _report(), _metadata("20260619_090000"))

    assert result_1.run_directory != result_2.run_directory
    assert "_001" in Path(result_2.run_directory).name


# ---------------------------------------------------------------------------
# Integration Test: No overwrite — first run's content is unchanged
# ---------------------------------------------------------------------------

def test_integration_no_overwrite(tmp_path):
    """First run's document.md is not modified after a second save with the same run_id."""
    manager = create_default_output_manager(base_output_dir=str(tmp_path))
    result_1 = manager.save(_md("Original content."), _report(), _metadata("20260619_090000"))
    result_2 = manager.save(_md("New content."), _report(), _metadata("20260619_090000"))

    original_md = Path(result_1.run_directory) / "document.md"
    assert original_md.read_text(encoding="utf-8") == "Original content."
