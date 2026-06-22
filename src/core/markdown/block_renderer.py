from typing import Protocol

from src.core.models.extraction import Block


class BlockRenderer(Protocol):
    """Protocol for concrete block renderers.

    Each BlockType has exactly one renderer. The MarkdownGenerator
    dispatches to the correct renderer via Dict[BlockType, BlockRenderer].

    Implementors live in src/core/markdown/renderers/.
    All renderers are core domain — no external library imports.
    """

    def render(self, block: Block) -> str:
        """Renders a single IDM block into a Markdown string segment.

        Args:
            block: A typed Block instance from the IntermediateDocumentModel.

        Returns:
            A Markdown string segment. Must not include surrounding blank lines —
            the generator handles inter-block spacing.
        """
        ...
