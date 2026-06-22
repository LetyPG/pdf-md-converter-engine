import logging
import re
from typing import List, Optional, Tuple

from src.core.extraction.extraction_provider import ExtractionProvider
from src.core.models.extraction import (
    Block,
    BlockType,
    CodeBlock,
    DocumentPage,
    ExtractionStrategy,
    HeadingBlock,
    IntermediateDocumentModel,
    ListBlock,
    ParagraphBlock,
    RawBlock,
    TableBlock,
)
from src.core.models.preprocessor import LayoutType, PreprocessingResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Heading level thresholds — fixed, absolute font size in points (Q1 decision)
# ---------------------------------------------------------------------------
HEADING_H1_THRESHOLD: float = 20.0
HEADING_H2_THRESHOLD: float = 16.0
HEADING_H3_THRESHOLD: float = 13.0

# ---------------------------------------------------------------------------
# Monospace font signals — case-insensitive substring match (Q2 decision)
# ---------------------------------------------------------------------------
MONOSPACE_FONT_SIGNALS: Tuple[str, ...] = (
    "courier",
    "mono",
    "code",
    "fixed",
    "consolas",
    "menlo",
    "inconsolata",
    "fira",
    "terminal",
)

# ---------------------------------------------------------------------------
# List detection patterns
# ---------------------------------------------------------------------------
_UNORDERED_MARKER = re.compile(r"^[\u2022\u00b7\u2013\-\*]\s+")
_ORDERED_MARKER = re.compile(r"^\d+[\.\)]\s+|^[a-zA-Z][\.\)]\s+")

# ---------------------------------------------------------------------------
# Security gate patterns
# ---------------------------------------------------------------------------
_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)
_MD_HYPERLINK_PATTERN = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_RAW_HTML_PATTERN = re.compile(r"<[^>]+>")
_MULTI_SPACE = re.compile(r"  +")


class ExtractionEngine:
    """Core business logic for Stage 2 of the pipeline.

    Responsibilities:
    - Select extraction strategy from the DocumentProfile.
    - Drive the ExtractionProvider page by page.
    - Classify RawBlocks into typed Block instances.
    - Apply the security gate to all text content.
    - Return a complete IntermediateDocumentModel.

    Constraints:
    - Has zero dependency on any PDF library.
    - Does NOT generate Markdown.
    - Does NOT persist any output.
    - Does NOT invoke LLMs.
    """

    def __init__(self, provider: ExtractionProvider) -> None:
        """Initialises the engine with a concrete extraction provider.

        Args:
            provider: Any object satisfying the ExtractionProvider protocol.
        """
        self._provider = provider

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(
        self,
        pdf_path: str,
        preprocessing_result: PreprocessingResult,
    ) -> IntermediateDocumentModel:
        """Runs the full extraction pipeline for the given PDF.

        Args:
            pdf_path: Path to the PDF file validated by the Preprocessor.
            preprocessing_result: Accepted PreprocessingResult from Stage 1.

        Returns:
            A complete IntermediateDocumentModel ready for the Markdown Generator.
        """
        profile = preprocessing_result.document_profile
        strategy = self._select_strategy(profile)
        logger.info("Extraction strategy selected: %s", strategy.value)

        if strategy == ExtractionStrategy.OCR:
            warning = (
                "OCR strategy selected but not yet implemented. Extraction skipped."
            )
            logger.warning(warning)
            return IntermediateDocumentModel(
                strategy_used=strategy,
                warnings=[warning],
            )

        self._provider.open(pdf_path)
        try:
            pages: List[DocumentPage] = []
            for page_num in range(1, self._provider.get_page_count() + 1):
                raw_blocks = self._provider.extract_page_blocks(page_num, strategy)
                pages.append(self._process_page(raw_blocks, page_num))
            return IntermediateDocumentModel(strategy_used=strategy, pages=pages)
        finally:
            self._provider.close()

    # ------------------------------------------------------------------
    # Strategy Selection
    # ------------------------------------------------------------------

    def _select_strategy(self, profile) -> ExtractionStrategy:
        """Selects the extraction strategy from the document profile.

        Priority order (highest first):
        1. OCR  — no text layer, likely scanned.
        2. MULTI_COLUMN — multi-column layout detected.
        3. MIXED_LAYOUT — mixed layouts across pages.
        4. NATIVE_TEXT — default for standard native-text PDFs.
        """
        if profile.likely_scanned and not profile.text_layer_present:
            return ExtractionStrategy.OCR

        if profile.layout_type == LayoutType.MULTI_COLUMN:
            return ExtractionStrategy.MULTI_COLUMN

        if profile.mixed_layout:
            return ExtractionStrategy.MIXED_LAYOUT

        return ExtractionStrategy.NATIVE_TEXT

    # ------------------------------------------------------------------
    # Page Processing
    # ------------------------------------------------------------------

    def _process_page(
        self, raw_blocks: List[RawBlock], page_num: int
    ) -> DocumentPage:
        """Classifies and sanitizes raw blocks for a single page.

        Args:
            raw_blocks: Ordered list of RawBlock instances from the adapter.
            page_num: 1-indexed page number.

        Returns:
            A DocumentPage with fully classified Block instances.
        """
        classified: List[Block] = []
        order_counter = 1

        for raw in raw_blocks:
            block_id = f"b{page_num:03d}_{order_counter:03d}"
            block = self._classify_block(raw, block_id, page_num, order_counter)
            if block is not None:
                classified.append(block)
                order_counter += 1

        return DocumentPage(page_number=page_num, blocks=classified)

    # ------------------------------------------------------------------
    # Block Classification
    # ------------------------------------------------------------------

    def _classify_block(
        self,
        raw: RawBlock,
        block_id: str,
        page: int,
        order: int,
    ) -> Optional[Block]:
        """Classifies a RawBlock into a typed Block.

        Returns None for raw_types that SHALL NOT be extracted
        (images and graphs, per spec section 'Must Not Extract').
        """
        if raw.raw_type == "image":
            logger.debug("Page %d: image block skipped (not extracted per spec).", page)
            return None

        if raw.raw_type == "table":
            return self._build_table_block(raw, block_id, page, order)

        # raw_type == "text"
        content = self._sanitize(raw.content)
        if not content.strip():
            return None

        font_size: float = float(raw.metadata.get("font_size", 0.0))
        font_name: str = str(raw.metadata.get("font", "")).lower()

        heading_level = self._detect_heading_level(font_size)
        if heading_level is not None:
            return HeadingBlock(
                block_id=block_id,
                type=BlockType.HEADING,
                page=page,
                order=order,
                level=heading_level,
                content=content.strip(),
            )

        if self._is_monospace(font_name):
            return CodeBlock(
                block_id=block_id,
                type=BlockType.CODE,
                page=page,
                order=order,
                language=None,
                content=content,
            )

        is_list, items = self._parse_list_items(raw.content)
        if is_list:
            ordered = bool(_ORDERED_MARKER.match(raw.content.lstrip()))
            return ListBlock(
                block_id=block_id,
                type=BlockType.LIST,
                page=page,
                order=order,
                ordered=ordered,
                items=items,
            )

        return ParagraphBlock(
            block_id=block_id,
            type=BlockType.PARAGRAPH,
            page=page,
            order=order,
            content=content,
        )

    def _build_table_block(
        self, raw: RawBlock, block_id: str, page: int, order: int
    ) -> TableBlock:
        """Builds a TableBlock from a raw table RawBlock.

        The adapter populates metadata["headers"] and metadata["rows"]
        via PyMuPDF's find_tables() API.
        """
        headers: List[str] = [
            self._sanitize(h) for h in raw.metadata.get("headers", [])
        ]
        rows: List[List[str]] = [
            [self._sanitize(cell) for cell in row]
            for row in raw.metadata.get("rows", [])
        ]
        return TableBlock(
            block_id=block_id,
            type=BlockType.TABLE,
            page=page,
            order=order,
            headers=headers,
            rows=rows,
        )

    # ------------------------------------------------------------------
    # Classification Helpers
    # ------------------------------------------------------------------

    def _detect_heading_level(self, font_size: float) -> Optional[int]:
        """Maps font size to heading level using fixed absolute thresholds.

        Thresholds (Q1 decision — deterministic across all documents):
            H1: font_size >= HEADING_H1_THRESHOLD (20 pt)
            H2: font_size >= HEADING_H2_THRESHOLD (16 pt)
            H3: font_size >= HEADING_H3_THRESHOLD (13 pt)

        Returns:
            Heading level int (1–3) or None if below threshold.
        """
        if font_size >= HEADING_H1_THRESHOLD:
            return 1
        if font_size >= HEADING_H2_THRESHOLD:
            return 2
        if font_size >= HEADING_H3_THRESHOLD:
            return 3
        return None

    def _is_monospace(self, font_name: str) -> bool:
        """Returns True if the font name matches a known monospace signal."""
        return any(signal in font_name for signal in MONOSPACE_FONT_SIGNALS)

    def _parse_list_items(self, content: str) -> Tuple[bool, List[str]]:
        """Detects list items by matching leading markers in each line.

        Returns:
            Tuple of (is_list, items). items is empty when is_list is False.
        """
        items: List[str] = []
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if _UNORDERED_MARKER.match(stripped) or _ORDERED_MARKER.match(stripped):
                clean = _UNORDERED_MARKER.sub("", stripped)
                clean = _ORDERED_MARKER.sub("", clean)
                sanitized = self._sanitize(clean.strip())
                if sanitized:
                    items.append(sanitized)

        return (len(items) > 0, items)

    # ------------------------------------------------------------------
    # Security Gate
    # ------------------------------------------------------------------

    def _sanitize(self, content: str) -> str:
        """Strips unsafe references from text content.

        Applied to ALL text content before any Block is created.
        Removal order: Markdown hyperlinks → URLs → emails → raw HTML.

        Security gate enforces (per extraction-engine-spec.md):
        - No URLs (https?://...)
        - No email addresses (user@domain.com)
        - No Markdown hyperlinks ([text](url))
        - No raw HTML tags (<tag>)
        """
        content = _MD_HYPERLINK_PATTERN.sub("", content)
        content = _URL_PATTERN.sub("", content)
        content = _EMAIL_PATTERN.sub("", content)
        content = _RAW_HTML_PATTERN.sub("", content)
        content = _MULTI_SPACE.sub(" ", content)
        return content
