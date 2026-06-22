from src.core.models.extraction import QuoteBlock


class QuoteRenderer:
    """Renders QuoteBlock into Markdown blockquote syntax.

    Rule (from output_md_schema.md):
        QuoteBlock(content="...") → "> ..."

    Each line of multi-line content is prefixed with "> ".

    NOTE: QuoteBlock emission is deferred in the ExtractionEngine (Stage 2).
    This renderer is provided so the contract is complete and the
    generator can render QuoteBlocks if they are added in future phases.
    """

    def render(self, block: QuoteBlock) -> str:
        """Renders the quote block.

        Args:
            block: QuoteBlock instance from the IDM.

        Returns:
            Blockquote string with each line prefixed by "> ".
        """
        lines = block.content.split("\n")
        return "\n".join(f"> {line}" for line in lines)
