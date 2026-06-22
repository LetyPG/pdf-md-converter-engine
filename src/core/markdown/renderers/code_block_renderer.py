from src.core.models.extraction import CodeBlock


class CodeBlockRenderer:
    """Renders CodeBlock into fenced Markdown code blocks.

    Rules (from output_md_schema.md):
        With language:   ```python\\ncode\\n```
        Without language: ```\\ncode\\n```
    """

    def render(self, block: CodeBlock) -> str:
        """Renders the code block.

        Args:
            block: CodeBlock instance from the IDM.

        Returns:
            Fenced code block string with optional language tag.
        """
        lang = block.language or ""
        return f"```{lang}\n{block.content}\n```"
