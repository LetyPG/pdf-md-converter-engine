import logging

logger = logging.getLogger(__name__)

try:
    from markdown_it import MarkdownIt
    _MARKDOWN_IT_AVAILABLE = True
except ImportError:
    _MARKDOWN_IT_AVAILABLE = False
    logger.warning(
        "markdown-it-py is not installed. MarkdownValidatorAdapter will use "
        "fallback (non-empty) validation. "
        "Add markdown-it-py>=3.0.0 to requirements.txt before Stage 4 implementation."
    )


class MarkdownValidatorAdapter:
    """Adapter that validates Markdown strings using markdown-it-py.

    This is the ONLY file in the codebase that imports markdown-it-py.
    It is called by the Quality Validator (Stage 4) and Output Manager (Stage 5),
    NOT by the MarkdownGenerator itself.

    Stack restriction notice:
        markdown-it-py must be added to requirements.txt (with user approval)
        before Stage 4 implementation begins.
    """

    def validate(self, content: str) -> bool:
        """Returns True if content is non-empty and parseable as Markdown.

        Falls back to a basic non-empty check when markdown-it-py is unavailable.

        Args:
            content: The Markdown string to validate.

        Returns:
            True if valid, False otherwise.
        """
        if not content or not content.strip():
            return False

        if _MARKDOWN_IT_AVAILABLE:
            try:
                md = MarkdownIt()
                tokens = md.parse(content)
                return tokens is not None
            except Exception as exc:
                logger.error("Markdown parsing failed: %s", exc)
                return False

        # Fallback: basic non-empty check
        return len(content.strip()) > 0

    @property
    def is_full_validation_available(self) -> bool:
        """True when markdown-it-py is installed and full parsing is active."""
        return _MARKDOWN_IT_AVAILABLE
