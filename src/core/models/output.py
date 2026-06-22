from dataclasses import dataclass, field
from typing import List


@dataclass
class ExecutionMetadata:
    """Runtime metadata for a single conversion execution.

    Matches the spec contract from output-manager-spec.md § Execution Metadata.

    Attributes:
        run_id:           Timestamp-based identifier "YYYYMMDD_HHMMSS" (UTC).
        source_document:  Original PDF filename (basename only).
        started_at:       ISO 8601 UTC timestamp when the pipeline started.
        completed_at:     ISO 8601 UTC timestamp when the pipeline finished.
        duration_ms:      Wall-clock duration in milliseconds.
        engine_version:   Semantic version of the engine (e.g. "1.0.0").
    """

    run_id: str
    source_document: str
    started_at: str
    completed_at: str
    duration_ms: int
    engine_version: str


@dataclass
class OutputManifest:
    """Artifact inventory written as the last file in the run directory.

    Matches the spec manifest contract from output-manager-spec.md § Manifest.

    Attributes:
        run_id:       Same run_id as the corresponding ExecutionMetadata.
        generated_at: ISO 8601 UTC timestamp when the manifest was written.
        artifacts:    List of filenames (not full paths) in the run directory.
    """

    run_id: str
    generated_at: str
    artifacts: List[str] = field(default_factory=list)


@dataclass
class OutputResult:
    """Summary returned by OutputManager.save().

    Consumed by the caller to confirm that all artifacts were persisted.

    Attributes:
        run_directory: Absolute path to the run_YYYYMMDD_HHMMSS/ directory.
        artifacts:     Filenames actually written (matches manifest).
        warnings:      Warnings emitted during persistence (dir creation, collision).
        success:       True when all artifacts were written and verified.
    """

    run_directory: str
    artifacts: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    success: bool = False
