from src.core.models.extraction import DiagramBlock


class DiagramRenderer:
    """Renders DiagramBlock into a fixed placeholder string.

    Rule (from output_md_schema.md):
        DiagramBlock → "[Diagram detected but not reconstructed]"
    """

    def render(self, block: DiagramBlock) -> str:
        """Renders the diagram block as a fixed placeholder.

        Args:
            block: DiagramBlock instance from the IDM.

        Returns:
            Fixed placeholder string per spec.
        """
        return "[Diagram detected but not reconstructed]"
