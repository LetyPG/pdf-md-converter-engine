from typing import List, Protocol, Tuple

from src.core.models.extraction import IntermediateDocumentModel
from src.core.models.validation import Finding


class CategoryValidator(Protocol):
    """Protocol for the four quality validation sub-validators.

    The QualityValidator dispatches to each sub-validator and aggregates results.
    Implementors live in src/core/validation/validators/.

    All implementations are core domain — no external library imports,
    except RenderingValidator which is injected with a MarkdownParserProtocol.
    """

    def validate(
        self,
        idm: IntermediateDocumentModel,
        markdown_content: str,
    ) -> Tuple[float, List[Finding]]:
        """Runs the validation checks for one dimension.

        Args:
            idm: The IntermediateDocumentModel — canonical source of truth.
            markdown_content: The rendered Markdown string to validate.

        Returns:
            Tuple of (score 0.0–100.0, list of findings).
        """
        ...


class MarkdownParserProtocol(Protocol):
    """Protocol for the Markdown parser used by RenderingValidator.

    Satisfied structurally by MarkdownValidatorAdapter.
    Defined in the core so RenderingValidator never imports the adapter directly.
    """

    def validate(self, content: str) -> bool:
        """Returns True if content is parseable Markdown."""
        ...
