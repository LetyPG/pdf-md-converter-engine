from src.core.models.extraction import ParagraphBlock


class ParagraphRenderer:
    """Renders ParagraphBlock into a plain Markdown paragraph.

    Rule (from output_md_schema.md):
        ParagraphBlock(content="Text.") → "Text."

    Content is returned as-is. Surrounding blank lines are handled
    by the MarkdownGenerator, not the renderer.
    """

    def render(self, block: ParagraphBlock) -> str:
        """Renders the paragraph block.

        Args:
            block: ParagraphBlock instance from the IDM.

        Returns:
            The paragraph text string.
        """
        return block.content
