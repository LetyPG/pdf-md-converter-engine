import logging
from typing import List

from src.core.validation.category_validator import CategoryValidator
from src.core.validation.validators.structural_validator import StructuralValidator
from src.core.validation.validators.rendering_validator import RenderingValidator
from src.core.validation.validators.security_validator import SecurityValidator
from src.core.validation.validators.completeness_validator import CompletenessValidator
from src.adapters.markdown.markdown_validator_adapter import MarkdownValidatorAdapter
from src.core.models.extraction import IntermediateDocumentModel
from src.core.models.markdown import MarkdownResult
from src.core.models.validation import Finding, ValidationReport

logger = logging.getLogger(__name__)

# --- Weighted formula constants (spec: 35/25/25/15) ---
_STRUCTURAL_WEIGHT: float = 0.35
_RENDERING_WEIGHT: float = 0.25
_SECURITY_WEIGHT: float = 0.25
_COMPLETENESS_WEIGHT: float = 0.15

# --- Threshold warning levels ---
_STRUCTURAL_WARN_THRESHOLD: float = 95.0
_COMPLETENESS_WARN_THRESHOLD: float = 95.0


def create_default_validator() -> "QualityValidator":
    """Factory — returns a QualityValidator wired with all concrete sub-validators."""
    parser = MarkdownValidatorAdapter()
    return QualityValidator(
        structural_validator=StructuralValidator(),
        rendering_validator=RenderingValidator(parser),
        security_validator=SecurityValidator(),
        completeness_validator=CompletenessValidator(),
    )


class QualityValidator:
    """Core business logic for Stage 4 of the pipeline.

    Responsibilities:
    - Dispatch IDM + Markdown to each CategoryValidator sub-validator.
    - Compute weighted overall score using the spec formula.
    - Apply failure rules: passed=False when rendering or security < 100.
    - Emit threshold warnings for structural and completeness dimensions.
    - Propagate MarkdownResult warnings into the ValidationReport.

    Constraints:
    - Has zero dependency on any external library (delegated to sub-validators).
    - Does NOT modify Markdown.
    - Does NOT invoke LLMs.
    - Output is deterministic: same inputs → same report.
    """

    def __init__(
        self,
        structural_validator: CategoryValidator,
        rendering_validator: CategoryValidator,
        security_validator: CategoryValidator,
        completeness_validator: CategoryValidator,
    ) -> None:
        """Initialises the validator with all four sub-validators.

        Args:
            structural_validator:   Validates document structure preservation.
            rendering_validator:    Validates Markdown syntax correctness.
            security_validator:     Validates security gate enforcement.
            completeness_validator: Validates content completeness.
        """
        self._structural = structural_validator
        self._rendering = rendering_validator
        self._security = security_validator
        self._completeness = completeness_validator

    def validate(
        self,
        idm: IntermediateDocumentModel,
        markdown_result: MarkdownResult,
    ) -> ValidationReport:
        """Runs the full Quality Validator pipeline.

        Args:
            idm: IntermediateDocumentModel — canonical source of truth.
            markdown_result: MarkdownResult from the Markdown Generator (Stage 3).

        Returns:
            A complete ValidationReport.
        """
        content = markdown_result.content
        findings: List[Finding] = []
        warnings: List[str] = list(markdown_result.warnings)

        structural_score, structural_findings = self._structural.validate(idm, content)
        rendering_score, rendering_findings = self._rendering.validate(idm, content)
        security_score, security_findings = self._security.validate(idm, content)
        completeness_score, completeness_findings = self._completeness.validate(idm, content)

        findings.extend(structural_findings)
        findings.extend(rendering_findings)
        findings.extend(security_findings)
        findings.extend(completeness_findings)

        overall_score = round(
            (structural_score * _STRUCTURAL_WEIGHT)
            + (rendering_score * _RENDERING_WEIGHT)
            + (security_score * _SECURITY_WEIGHT)
            + (completeness_score * _COMPLETENESS_WEIGHT),
            2,
        )

        passed = rendering_score == 100.0 and security_score == 100.0

        if structural_score < _STRUCTURAL_WARN_THRESHOLD:
            warnings.append(
                f"Structural score below threshold: {structural_score:.1f} (threshold: {_STRUCTURAL_WARN_THRESHOLD})"
            )
        if completeness_score < _COMPLETENESS_WARN_THRESHOLD:
            warnings.append(
                f"Completeness score below threshold: {completeness_score:.1f} (threshold: {_COMPLETENESS_WARN_THRESHOLD})"
            )

        logger.info(
            "Validation complete — structural=%.1f rendering=%.1f security=%.1f "
            "completeness=%.1f overall=%.1f passed=%s",
            structural_score, rendering_score, security_score,
            completeness_score, overall_score, passed,
        )

        return ValidationReport(
            structural_score=structural_score,
            rendering_score=rendering_score,
            security_score=security_score,
            completeness_score=completeness_score,
            overall_score=overall_score,
            passed=passed,
            warnings=warnings,
            findings=findings,
        )
