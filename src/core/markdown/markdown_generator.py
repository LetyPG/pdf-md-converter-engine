import logging
import re
from typing import Dict, List

from src.core.markdown.block_renderer import BlockRenderer
from src.core.markdown.renderers.code_block_renderer import CodeBlockRenderer
from src.core.markdown.renderers.diagram_renderer import DiagramRenderer
from src.core.markdown.renderers.figure_renderer import FigureRenderer
from src.core.markdown.renderers.heading_renderer import HeadingRenderer
from src.core.markdown.renderers.list_renderer import ListRenderer
from src.core.markdown.renderers.paragraph_renderer import ParagraphRenderer
from src.core.markdown.renderers.quote_renderer import QuoteRenderer
from src.core.markdown.renderers.table_renderer import TableRenderer
from src.core.models.extraction import BlockType, IntermediateDocumentModel
from src.core.models.markdown import MarkdownResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Security gate patterns — second layer applied on assembled output
# ---------------------------------------------------------------------------
_MD_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_MD_HYPERLINK_PATTERN = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_RAW_HTML_PATTERN = re.compile(r"<[^>]+>")
_MULTI_SPACE = re.compile(r"  +")


def create_default_renderers() -> Dict[BlockType, BlockRenderer]:
    """Returns a dict of all registered renderers keyed by BlockType.

    Used by create_default_generator() and integration tests.
    """
    return {
        BlockType.HEADING: HeadingRenderer(),
        BlockType.PARAGRAPH: ParagraphRenderer(),
        BlockType.LIST: ListRenderer(),
        BlockType.TABLE: TableRenderer(),
        BlockType.CODE: CodeBlockRenderer(),
        BlockType.QUOTE: QuoteRenderer(),
        BlockType.FIGURE: FigureRenderer(),
        BlockType.DIAGRAM: DiagramRenderer(),
    }


def create_default_generator() -> "MarkdownGenerator":
    """Factory — returns a MarkdownGenerator wired with all concrete renderers."""
    return MarkdownGenerator(create_default_renderers())


class MarkdownGenerator:
    """Core business logic for Stage 3 of the pipeline.

    Responsibilities:
    - Dispatch each IDM block to its registered BlockRenderer.
    - Join rendered segments with a single blank line between them.
    - Apply formatting normalization (trailing whitespace, line endings).
    - Apply a second security gate on the assembled Markdown string.
    - Propagate IDM warnings and append any generator-level warnings.

    Constraints:
    - Has zero dependency on any Markdown library.
    - Does NOT perform extraction.
    - Does NOT persist outputs.
    - Does NOT invoke LLMs.
    - Output is deterministic: same IDM → same Markdown string, always.
    """

    def __init__(self, renderers: Dict[BlockType, BlockRenderer]) -> None:
        """Initialises the generator with a map of block renderers.

        Args:
            renderers: Dict mapping each BlockType to its BlockRenderer.
                       Use create_default_generator() for the full set.
        """
        self._renderers = renderers

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, idm: IntermediateDocumentModel) -> MarkdownResult:
        """Renders the IDM into a Markdown string.

        Args:
            idm: Complete IntermediateDocumentModel from the Extraction Engine.

        Returns:
            MarkdownResult with the rendered content and propagated warnings.
        """
        segments: List[str] = []
        warnings: List[str] = list(idm.warnings)

        for page in idm.pages:
            for block in page.blocks:
                renderer = self._renderers.get(block.type)
                if renderer is None:
                    warning = (
                        f"No renderer registered for block type: {block.type.value}. "
                        f"Block {block.block_id} skipped."
                    )
                    logger.warning(warning)
                    warnings.append(warning)
                    continue

                try:
                    segment = renderer.render(block)
                    if segment:
                        segments.append(segment)
                except Exception as exc:  # noqa: BLE001
                    warning = f"Renderer failed for block {block.block_id}: {exc}"
                    logger.warning(warning)
                    warnings.append(warning)

        content = "\n\n".join(segments)
        content = self._normalize_formatting(content)
        content = self._apply_security_gate(content)

        return MarkdownResult(content=content, warnings=warnings)

    # ------------------------------------------------------------------
    # Formatting Normalization
    # ------------------------------------------------------------------

    def _normalize_formatting(self, content: str) -> str:
        """Applies output formatting constraints from the spec.

        - Normalizes CRLF and CR line endings to LF (unix_line_endings).
        - Strips trailing whitespace from every line (no_trailing_whitespace).
        """
        content = content.replace("\r\n", "\n").replace("\r", "\n")
        lines = [line.rstrip() for line in content.split("\n")]
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Security Gate (second layer)
    # ------------------------------------------------------------------

    def _apply_security_gate(self, content: str) -> str:
        """Applies a second security gate pass on the assembled Markdown string.

        Defensive layer — catches any unsafe content that survived through the IDM.
        Also enforces constraints specific to Markdown output (image syntax, raw HTML).

        Removal order:
        1. Markdown image syntax  (![alt](url)  → stripped entirely)
        2. Markdown hyperlinks    ([text](url)  → stripped entirely)
        3. URLs                   (https://...  → stripped entirely)
        4. Email addresses        (user@dom.com → stripped entirely)
        5. Raw HTML tags          (<tag>        → "[HTML omitted]")
        """
        content = _MD_IMAGE_PATTERN.sub("", content)
        content = _MD_HYPERLINK_PATTERN.sub("", content)
        content = _URL_PATTERN.sub("", content)
        content = _EMAIL_PATTERN.sub("", content)
        content = _RAW_HTML_PATTERN.sub("[HTML omitted]", content)
        content = _MULTI_SPACE.sub(" ", content)
        return content
