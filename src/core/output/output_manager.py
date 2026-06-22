import dataclasses
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional

from src.core.models.markdown import MarkdownResult
from src.core.models.output import ExecutionMetadata, OutputManifest, OutputResult
from src.core.models.validation import ValidationReport
from src.core.output.filesystem_writer import FilesystemWriter
from src.adapters.filesystem.local_filesystem_writer import LocalFilesystemWriter
from src.shared.exceptions.output_exceptions import (
    ArtifactWriteError,
    CollisionError,
    SerializationError,
)

logger = logging.getLogger(__name__)

_DEFAULT_BASE_DIR: str = "./outputs"
_MAX_COLLISION_SUFFIX: int = 999


def create_default_output_manager(base_output_dir: str = _DEFAULT_BASE_DIR) -> "OutputManager":
    """Factory — returns an OutputManager wired with the local filesystem adapter."""
    return OutputManager(
        writer=LocalFilesystemWriter(),
        base_output_dir=base_output_dir,
    )


class OutputManager:
    """Core business logic for Stage 5 of the pipeline.

    Responsibilities:
    - Resolve (or create) an isolated run directory.
    - Persist all 5 artifacts: document.md, validation.json, execution.json,
      logs.txt, and manifest.json (last).
    - Verify each file exists after writing.
    - Apply collision handling when a run directory already exists.
    - Emit warnings for directory creation and collision resolution.

    Constraints:
    - Has zero dependency on pathlib, os, or open(). All I/O via FilesystemWriter.
    - Does NOT generate Markdown or validation reports.
    - Does NOT modify any artifact.
    - Output structure is deterministic for a given run_id.
    """

    def __init__(
        self,
        writer: FilesystemWriter,
        base_output_dir: str = _DEFAULT_BASE_DIR,
    ) -> None:
        """Initialises the manager with a filesystem writer.

        Args:
            writer: Any object satisfying the FilesystemWriter Protocol.
            base_output_dir: Root output directory. Created if missing.
        """
        self._writer = writer
        self._base = base_output_dir

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def save(
        self,
        markdown_result: MarkdownResult,
        validation_report: ValidationReport,
        metadata: ExecutionMetadata,
        logs: str = "",
    ) -> OutputResult:
        """Persists all pipeline artifacts for one execution run.

        Args:
            markdown_result:   Stage 3 output — the rendered Markdown string.
            validation_report: Stage 4 output — quality scores and findings.
            metadata:          Runtime execution metadata for this run.
            logs:              Execution log string (may be empty).

        Returns:
            OutputResult with run_directory, artifact list, warnings, and success flag.

        Raises:
            ArtifactWriteError: If any file cannot be written or verified.
            SerializationError: If any data contract cannot be serialized to JSON.
            CollisionError:     If all collision suffixes (_001–_999) are exhausted.
        """
        warnings: List[str] = []

        run_dir = self._resolve_run_directory(metadata.run_id, warnings)

        md_filename = self._derive_md_filename(metadata.source_document)

        artifact_filenames: List[str] = []

        self._write_artifact(
            run_dir, md_filename, markdown_result.content, artifact_filenames
        )
        self._write_artifact(
            run_dir, "validation.json",
            self._serialize_validation_report(validation_report),
            artifact_filenames,
        )
        self._write_artifact(
            run_dir, "execution.json",
            self._serialize_execution_metadata(metadata),
            artifact_filenames,
        )
        self._write_artifact(
            run_dir, "logs.txt", logs, artifact_filenames
        )

        # Manifest written last — after all other artifacts are verified.
        # Pre-add "manifest.json" to the list so the manifest JSON lists itself.
        artifact_filenames.append("manifest.json")
        manifest = OutputManifest(
            run_id=metadata.run_id,
            generated_at=self._utcnow_iso(),
            artifacts=list(artifact_filenames),
        )
        manifest_path = self._writer.join(run_dir, "manifest.json")
        self._writer.write_text(manifest_path, self._serialize_manifest(manifest))
        if not self._writer.file_exists(manifest_path):
            raise ArtifactWriteError(
                f"Artifact 'manifest.json' was written but cannot be verified at '{manifest_path}'."
            )

        logger.info("OutputManager: persisted %d artifacts to %s", len(artifact_filenames), run_dir)

        return OutputResult(
            run_directory=run_dir,
            artifacts=artifact_filenames,
            warnings=warnings,
            success=True,
        )

    # ------------------------------------------------------------------
    # Run Directory Resolution
    # ------------------------------------------------------------------

    def _resolve_run_directory(self, run_id: str, warnings: List[str]) -> str:
        """Resolves the run directory path, handling collisions.

        Args:
            run_id:   The run identifier (YYYYMMDD_HHMMSS).
            warnings: Mutable list — warnings are appended here.

        Returns:
            Absolute (or relative) path to the resolved run directory.

        Raises:
            CollisionError: If all _001–_999 suffixes are taken.
        """
        candidate = self._writer.join(self._base, f"run_{run_id}")

        if not self._writer.directory_exists(candidate):
            self._writer.create_directory(candidate)
            warning = f"Output directory created: {candidate}"
            logger.warning(warning)
            warnings.append(warning)
            return candidate

        # Collision — try suffix _001 through _999
        for i in range(1, _MAX_COLLISION_SUFFIX + 1):
            suffixed = f"{candidate}_{i:03d}"
            if not self._writer.directory_exists(suffixed):
                self._writer.create_directory(suffixed)
                warning = f"Collision resolved: {candidate} → {suffixed}"
                logger.warning(warning)
                warnings.append(warning)
                return suffixed

        raise CollisionError(
            f"All collision suffixes exhausted for run_id '{run_id}'. "
            f"Directory '{candidate}' and _001–_{_MAX_COLLISION_SUFFIX:03d} all exist."
        )

    # ------------------------------------------------------------------
    # Artifact Persistence
    # ------------------------------------------------------------------

    def _write_artifact(
        self,
        run_dir: str,
        filename: str,
        content: str,
        artifact_filenames: List[str],
    ) -> None:
        """Writes one artifact and verifies it exists.

        Args:
            run_dir:           Path to the run directory.
            filename:          Artifact filename (no path).
            content:           String content to write.
            artifact_filenames: Mutable list — filename appended on success.

        Raises:
            ArtifactWriteError: If the file does not exist after writing.
        """
        path = self._writer.join(run_dir, filename)
        self._writer.write_text(path, content)
        if not self._writer.file_exists(path):
            raise ArtifactWriteError(
                f"Artifact '{filename}' was written but cannot be verified at '{path}'."
            )
        artifact_filenames.append(filename)
        logger.debug("Artifact written and verified: %s", path)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def _serialize_validation_report(self, report: ValidationReport) -> str:
        """Serializes ValidationReport to a JSON string.

        Enum values (FindingSeverity, FindingCategory) are serialized as
        their .value strings via the custom encoder.

        Raises:
            SerializationError: If serialization fails.
        """
        try:
            data: Dict[str, Any] = {
                "structural_score": report.structural_score,
                "rendering_score": report.rendering_score,
                "security_score": report.security_score,
                "completeness_score": report.completeness_score,
                "overall_score": report.overall_score,
                "passed": report.passed,
                "warnings": report.warnings,
                "findings": [
                    {
                        "severity": f.severity.value,
                        "category": f.category.value,
                        "message": f.message,
                        "location": f.location,
                    }
                    for f in report.findings
                ],
            }
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as exc:
            raise SerializationError(f"Failed to serialize ValidationReport: {exc}") from exc

    def _serialize_execution_metadata(self, metadata: ExecutionMetadata) -> str:
        """Serializes ExecutionMetadata to a JSON string.

        Raises:
            SerializationError: If serialization fails.
        """
        try:
            data = dataclasses.asdict(metadata)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as exc:
            raise SerializationError(f"Failed to serialize ExecutionMetadata: {exc}") from exc

    def _serialize_manifest(self, manifest: OutputManifest) -> str:
        """Serializes OutputManifest to a JSON string.

        Raises:
            SerializationError: If serialization fails.
        """
        try:
            data = dataclasses.asdict(manifest)
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as exc:
            raise SerializationError(f"Failed to serialize OutputManifest: {exc}") from exc

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _derive_md_filename(source_document: str) -> str:
        """Derives the Markdown output filename from the source document name.

        Example: "document.pdf" → "document.md"
        Uses PurePosixPath for cross-platform basename handling without pathlib.Path.
        """
        stem = PurePosixPath(source_document).stem
        if not stem:
            stem = "output"
        return f"{stem}.md"

    @staticmethod
    def _utcnow_iso() -> str:
        """Returns the current UTC datetime as an ISO 8601 string."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
