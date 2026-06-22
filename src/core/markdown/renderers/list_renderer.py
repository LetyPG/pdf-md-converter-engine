from typing import List

from src.core.models.extraction import ListBlock


class ListRenderer:
    """Renders ListBlock into Markdown list syntax.

    Rules (from output_md_schema.md):
        Unordered: "- item" per line
        Ordered:   "1. item", "2. item" … (1-indexed)
    """

    def render(self, block: ListBlock) -> str:
        """Renders the list block.

        Args:
            block: ListBlock instance from the IDM.

        Returns:
            Markdown list string with one item per line.
        """
        lines: List[str] = []
        for idx, item in enumerate(block.items, start=1):
            if block.ordered:
                lines.append(f"{idx}. {item}")
            else:
                lines.append(f"- {item}")
        return "\n".join(lines)
