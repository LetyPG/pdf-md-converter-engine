from src.core.models.extraction import FigureBlock


class FigureRenderer:
    """Renders FigureBlock into a placeholder string.

    Rules (from output_md_schema.md):
        With caption:    "[Figure omitted: Figure 3]"
        Without caption: "[Figure omitted]"
    """

    def render(self, block: FigureBlock) -> str:
        """Renders the figure block as a placeholder.

        Args:
            block: FigureBlock instance from the IDM.

        Returns:
            Placeholder string indicating a figure was present but not embedded.
        """
        if block.caption:
            return f"[Figure omitted: {block.caption}]"
        return "[Figure omitted]"
