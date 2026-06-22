"""Unit tests for OutputManager.

All tests use MockFilesystemWriter — no real disk I/O.
Pattern mirrors previous stage unit tests.
"""
import json
import pytest
from typing import Dict, List, Optional, Set

from src.core.output.output_manager import OutputManager
from src.core.models.extraction import ExtractionStrategy
from src.core.models.markdown import MarkdownResult
from src.core.models.output import ExecutionMetadata, OutputResult
from src.core.models.validation import Finding, FindingCategory, FindingSeverity, ValidationReport
from src.shared.exceptions.output_exceptions import ArtifactWriteError, CollisionError


# ---------------------------------------------------------------------------
# Mock Filesystem Writer
# ---------------------------------------------------------------------------

class MockFilesystemWriter:
    """Simulates filesystem operations in memory for unit tests."""

    def __init__(self, existing_dirs: Optional[Set[str]] = None) -> None:
        self.created_dirs: List[str] = []
        self.written_files: Dict[str, str] = {}   # path -> content
        self.write_order: List[str] = []           # basenames in write order
        self._existing_dirs: Set[str] = existing_dirs or set()
        self._fail_verify: bool = False             # simulate write-then-vanish

    def create_directory(self, path: str) -> None:
        self.created_dirs.append(path)
        self._existing_dirs.add(path)

    def directory_exists(self, path: str) -> bool:
        return path in self._existing_dirs

    def write_text(self, path: str, content: str) -> None:
        self.written_files[path] = content
        self.write_order.append(path.split("/")[-1])

    def file_exists(self, path: str) -> bool:
        if self._fail_verify:
            return False
        return path in self.written_files

    def join(self, base: str, *parts: str) -> str:
        return "/".join([base.rstrip("/")] + list(parts))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _metadata(run_id: str = "20260619_154502", source: str = "document.pdf") -> ExecutionMetadata:
    return ExecutionMetadata(
        run_id=run_id,
        source_document=source,
        started_at="2026-06-19T15:45:02Z",
        completed_at="2026-06-19T15:45:08Z",
        duration_ms=6000,
        engine_version="1.0.0",
    )


def _report(passed: bool = True) -> ValidationReport:
    return ValidationReport(
        structural_score=100.0,
        rendering_score=100.0,
        security_score=100.0,
        completeness_score=100.0,
        overall_score=100.0,
        passed=passed,
        warnings=[],
        findings=[],
    )


def _md(content: str = "# Title\n\nBody.") -> MarkdownResult:
    return MarkdownResult(content=content)


def _engine(writer: MockFilesystemWriter, base: str = "./outputs") -> OutputManager:
    return OutputManager(writer=writer, base_output_dir=base)


# ---------------------------------------------------------------------------
# Run Directory Tests
# ---------------------------------------------------------------------------

def test_save_creates_run_directory():
    """save() creates a run directory using the run_id."""
    writer = MockFilesystemWriter()
    result = _engine(writer).save(_md(), _report(), _metadata("20260619_154502"))
    assert any("run_20260619_154502" in d for d in writer.created_dirs)


def test_output_dir_created_warning_emitted():
    """First-time directory creation emits a warning in OutputResult."""
    writer = MockFilesystemWriter()
    result = _engine(writer).save(_md(), _report(), _metadata())
    assert any("Output directory created" in w for w in result.warnings)


def test_collision_resolution_appends_suffix():
    """Existing run dir triggers _001 suffix."""
    existing = {"./outputs/run_20260619_154502"}
    writer = MockFilesystemWriter(existing_dirs=existing)
    result = _engine(writer).save(_md(), _report(), _metadata("20260619_154502"))
    assert any("_001" in d for d in writer.created_dirs)


def test_collision_warning_emitted():
    """Collision resolution emits a warning."""
    existing = {"./outputs/run_20260619_154502"}
    writer = MockFilesystemWriter(existing_dirs=existing)
    result = _engine(writer).save(_md(), _report(), _metadata("20260619_154502"))
    assert any("Collision resolved" in w for w in result.warnings)


def test_collision_error_when_all_suffixes_taken():
    """CollisionError raised when run dir and all _001–_999 suffixes exist."""
    base = "./outputs"
    run_id = "20260619_154502"
    existing = {f"{base}/run_{run_id}"}
    for i in range(1, 1000):
        existing.add(f"{base}/run_{run_id}_{i:03d}")
    writer = MockFilesystemWriter(existing_dirs=existing)
    with pytest.raises(CollisionError):
        _engine(writer).save(_md(), _report(), _metadata(run_id))


# ---------------------------------------------------------------------------
# Artifact Write Tests
# ---------------------------------------------------------------------------

def test_save_writes_markdown_artifact():
    """document.md is written with MarkdownResult.content."""
    writer = MockFilesystemWriter()
    _engine(writer).save(_md("# Hello"), _report(), _metadata())
    md_path = [p for p in writer.written_files if p.endswith(".md")]
    assert len(md_path) == 1
    assert writer.written_files[md_path[0]] == "# Hello"


def test_save_writes_validation_json():
    """validation.json is written with score fields."""
    writer = MockFilesystemWriter()
    _engine(writer).save(_md(), _report(), _metadata())
    val_path = [p for p in writer.written_files if p.endswith("validation.json")]
    assert len(val_path) == 1
    data = json.loads(writer.written_files[val_path[0]])
    assert "structural_score" in data
    assert "overall_score" in data
    assert "passed" in data


def test_save_writes_execution_json():
    """execution.json contains run_id and source_document."""
    writer = MockFilesystemWriter()
    _engine(writer).save(_md(), _report(), _metadata("20260619_000000", "report.pdf"))
    exec_path = [p for p in writer.written_files if p.endswith("execution.json")]
    assert len(exec_path) == 1
    data = json.loads(writer.written_files[exec_path[0]])
    assert data["run_id"] == "20260619_000000"
    assert data["source_document"] == "report.pdf"


def test_save_writes_logs_txt():
    """logs.txt is written with the provided log content."""
    writer = MockFilesystemWriter()
    _engine(writer).save(_md(), _report(), _metadata(), logs="INFO: pipeline complete.")
    log_path = [p for p in writer.written_files if p.endswith("logs.txt")]
    assert len(log_path) == 1
    assert "INFO: pipeline complete." in writer.written_files[log_path[0]]


def test_save_writes_manifest_last():
    """manifest.json is the last file written."""
    writer = MockFilesystemWriter()
    _engine(writer).save(_md(), _report(), _metadata())
    assert writer.write_order[-1] == "manifest.json"


def test_manifest_lists_all_artifacts():
    """Manifest artifacts list contains all 5 filenames."""
    writer = MockFilesystemWriter()
    _engine(writer).save(_md(), _report(), _metadata())
    manifest_path = [p for p in writer.written_files if p.endswith("manifest.json")]
    data = json.loads(writer.written_files[manifest_path[0]])
    assert len(data["artifacts"]) == 5
    assert "manifest.json" in data["artifacts"]
    assert "validation.json" in data["artifacts"]
    assert "execution.json" in data["artifacts"]
    assert "logs.txt" in data["artifacts"]


def test_markdown_filename_derived_from_source_stem():
    """Source document stem determines Markdown filename (report.pdf → report.md)."""
    writer = MockFilesystemWriter()
    _engine(writer).save(_md(), _report(), _metadata(source="report.pdf"))
    md_path = [p for p in writer.written_files if p.endswith(".md")]
    assert len(md_path) == 1
    assert "report.md" in md_path[0]


def test_artifact_write_failure_raises():
    """ArtifactWriteError raised if file_exists returns False after write."""
    writer = MockFilesystemWriter()
    writer._fail_verify = True
    with pytest.raises(ArtifactWriteError):
        _engine(writer).save(_md(), _report(), _metadata())


def test_output_result_success_true_on_clean_run():
    """OutputResult.success is True when all artifacts are written and verified."""
    writer = MockFilesystemWriter()
    result = _engine(writer).save(_md(), _report(), _metadata())
    assert result.success is True


def test_validation_report_findings_serialized():
    """Findings in validation.json have severity and category as strings."""
    report = ValidationReport(
        structural_score=80.0,
        rendering_score=100.0,
        security_score=100.0,
        completeness_score=100.0,
        overall_score=93.0,
        passed=True,
        warnings=[],
        findings=[
            Finding(
                severity=FindingSeverity.WARNING,
                category=FindingCategory.STRUCTURE,
                message="Heading count mismatch",
                location="Page 3",
            )
        ],
    )
    writer = MockFilesystemWriter()
    _engine(writer).save(_md(), report, _metadata())
    val_path = [p for p in writer.written_files if p.endswith("validation.json")][0]
    data = json.loads(writer.written_files[val_path])
    finding = data["findings"][0]
    assert finding["severity"] == "WARNING"
    assert finding["category"] == "STRUCTURE"
    assert finding["message"] == "Heading count mismatch"
    assert finding["location"] == "Page 3"
