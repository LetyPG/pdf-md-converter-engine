from src.core.models.extraction import HeadingBlock


class HeadingRenderer:
    """Renders HeadingBlock into ATX-style Markdown headings.

    Rule (from output_md_schema.md):
        HeadingBlock(level=2, content="Requirements") → "## Requirements"

    Level is clamped to 1–6 (defensive against invalid IDM data).
    """

    def render(self, block: HeadingBlock) -> str:
        """Renders the heading block.

        Args:
            block: HeadingBlock instance from the IDM.

        Returns:
            ATX heading string, e.g. "## Section Title".
        """
        level = max(1, min(6, block.level))
        return f"{'#' * level} {block.content}"
