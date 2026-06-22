from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class FindingSeverity(Enum):
    """Severity level of a validation finding."""

    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class FindingCategory(Enum):
    """Validation category a finding belongs to."""

    STRUCTURE = "STRUCTURE"
    RENDERING = "RENDERING"
    SECURITY = "SECURITY"
    COMPLETENESS = "COMPLETENESS"


@dataclass
class Finding:
    """A single validation finding produced by a sub-validator.

    Attributes:
        severity: INFO, WARNING, or ERROR.
        category: Which validation dimension raised the finding.
        message: Human-readable description of the finding.
        location: Optional location hint (e.g. "Page 3", "Block b002_001").
    """

    severity: FindingSeverity
    category: FindingCategory
    message: str
    location: Optional[str] = None


@dataclass
class ValidationReport:
    """Complete output of the Quality Validator (Stage 4).

    Consumed by the Output Manager (Stage 5).

    Attributes:
        structural_score:    0–100. Warning emitted when < 95.
        rendering_score:     0–100. Artifact FAILS when < 100.
        security_score:      0–100. Artifact FAILS when < 100.
        completeness_score:  0–100. Warning emitted when < 95.
        overall_score:       Weighted formula result (35/25/25/15).
        passed:              False when rendering_score < 100 OR security_score < 100.
        warnings:            Threshold warnings + propagated MarkdownResult warnings.
        findings:            All findings from all sub-validators.
    """

    structural_score: float
    rendering_score: float
    security_score: float
    completeness_score: float
    overall_score: float
    passed: bool
    warnings: List[str] = field(default_factory=list)
    findings: List[Finding] = field(default_factory=list)
