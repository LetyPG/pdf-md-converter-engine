import logging
from typing import Any, Dict, List, Tuple

import fitz  # PyMuPDF

from src.core.models.extraction import ExtractionStrategy, RawBlock
from src.shared.exceptions.extraction_exceptions import ExtractionProviderError

logger = logging.getLogger(__name__)

# Horizontal split fraction for multi-column detection (left/right boundary).
_COLUMN_SPLIT_RATIO: float = 0.5


class PyMuPdfExtractionProvider:
    """Adapter implementing ExtractionProvider using PyMuPDF (fitz).

    This is the ONLY file in the codebase that imports fitz.
    The core ExtractionEngine depends on the ExtractionProvider Protocol only.

    Table detection uses page.find_tables() (PyMuPDF >= 1.23, Q2 decision).
    Multi-column reading order is reconstructed by horizontal position splitting.
    """

    def __init__(self) -> None:
        """Initialises the provider with no open document."""
        self._doc: Any = None
        self._path: str = ""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def open(self, path: str) -> None:
        """Opens the PDF for extraction.

        Args:
            path: Absolute path to the PDF file.

        Raises:
            ExtractionProviderError: If fitz cannot open the document.
        """
        self._path = path
        try:
            self._doc = fitz.open(path)
        except Exception as exc:
            logger.error("PyMuPDF failed to open %s: %s", path, exc)
            raise ExtractionProviderError(f"Failed to open PDF: {exc}") from exc

    def close(self) -> None:
        """Closes and releases the PDF document."""
        if self._doc:
            self._doc.close()
            self._doc = None

    def get_page_count(self) -> int:
        """Returns the total number of pages.

        Raises:
            ExtractionProviderError: If no document is open.
        """
        self._assert_open()
        return len(self._doc)

    # ------------------------------------------------------------------
    # Block Extraction
    # ------------------------------------------------------------------

    def extract_page_blocks(
        self, page_number: int, strategy: ExtractionStrategy
    ) -> List[RawBlock]:
        """Extracts raw blocks from a single page.

        Workflow:
        1. Detect tables via find_tables() and record their bounding boxes.
        2. Extract text/image blocks via get_text("dict").
        3. Skip text blocks that overlap with detected table regions.
        4. Merge text blocks and table blocks, sorted by reading position.
        5. If strategy is MULTI_COLUMN, reconstruct column reading order.

        Args:
            page_number: 1-indexed page number.
            strategy: Extraction strategy selected by the engine.

        Returns:
            Ordered list of RawBlock instances.
        """
        self._assert_open()
        page = self._doc[page_number - 1]

        table_blocks = self._extract_tables(page, page_number)
        table_bboxes = [tb.bbox for tb in table_blocks]

        text_blocks = self._extract_text_blocks(page, page_number, table_bboxes)

        all_blocks = text_blocks + table_blocks

        if strategy == ExtractionStrategy.MULTI_COLUMN:
            all_blocks = self._reconstruct_multi_column_order(all_blocks, page)
        else:
            all_blocks = sorted(all_blocks, key=lambda b: (b.bbox[1], b.bbox[0]))

        # Re-assign sequential order after sorting
        for idx, block in enumerate(all_blocks, start=1):
            block.order = idx

        return all_blocks

    # ------------------------------------------------------------------
    # Table Extraction
    # ------------------------------------------------------------------

    def _extract_tables(self, page: Any, page_number: int) -> List[RawBlock]:
        """Extracts tables using PyMuPDF find_tables() (>= 1.23).

        Each detected table is returned as a RawBlock with raw_type="table".
        Headers and rows are stored in metadata for the engine to consume.
        """
        table_blocks: List[RawBlock] = []
        try:
            tabs = page.find_tables()
        except Exception as exc:
            logger.warning("find_tables() failed on page %d: %s", page_number, exc)
            return []

        for order, tab in enumerate(tabs, start=1):
            try:
                extracted = tab.extract()
                if not extracted:
                    continue

                headers: List[str] = []
                rows: List[List[str]] = []

                if tab.header and tab.header.names:
                    headers = [str(h) if h else "" for h in tab.header.names]
                    rows = [
                        [str(cell) if cell else "" for cell in row]
                        for row in extracted
                    ]
                else:
                    # No explicit header row: treat first row as headers
                    if extracted:
                        headers = [str(c) if c else "" for c in extracted[0]]
                        rows = [
                            [str(cell) if cell else "" for cell in row]
                            for row in extracted[1:]
                        ]

                bbox: Tuple[float, float, float, float] = (
                    tab.bbox[0],
                    tab.bbox[1],
                    tab.bbox[2],
                    tab.bbox[3],
                )

                table_blocks.append(
                    RawBlock(
                        raw_type="table",
                        content="",
                        bbox=bbox,
                        page=page_number,
                        order=order,
                        metadata={"headers": headers, "rows": rows},
                    )
                )
            except Exception as exc:
                logger.warning(
                    "Skipping table on page %d due to extraction error: %s",
                    page_number,
                    exc,
                )

        return table_blocks

    # ------------------------------------------------------------------
    # Text Block Extraction
    # ------------------------------------------------------------------

    def _extract_text_blocks(
        self,
        page: Any,
        page_number: int,
        table_bboxes: List[Tuple[float, float, float, float]],
    ) -> List[RawBlock]:
        """Extracts text and image blocks, skipping table regions.

        Uses page.get_text("dict") which provides per-span font metadata.
        Text blocks overlapping a table bounding box are skipped.
        """
        raw_dict = page.get_text("dict")
        text_blocks: List[RawBlock] = []
        order = 1

        for block in raw_dict.get("blocks", []):
            block_type: int = block.get("type", -1)
            bbox: Tuple[float, float, float, float] = tuple(block.get("bbox", (0, 0, 0, 0)))

            if self._overlaps_table(bbox, table_bboxes):
                continue

            if block_type == 1:
                # Image block — pass through as raw_type="image" (engine will skip)
                text_blocks.append(
                    RawBlock(
                        raw_type="image",
                        content="",
                        bbox=bbox,
                        page=page_number,
                        order=order,
                        metadata={},
                    )
                )
                order += 1
                continue

            if block_type != 0:
                continue

            content, font_size, font_name, bold = self._extract_block_text(block)
            if not content.strip():
                continue

            text_blocks.append(
                RawBlock(
                    raw_type="text",
                    content=content,
                    bbox=bbox,
                    page=page_number,
                    order=order,
                    metadata={
                        "font_size": font_size,
                        "font": font_name,
                        "bold": bold,
                    },
                )
            )
            order += 1

        return text_blocks

    def _extract_block_text(
        self, block: Dict[str, Any]
    ) -> Tuple[str, float, str, bool]:
        """Extracts aggregated text and dominant font metadata from a block.

        Returns:
            Tuple of (content, dominant_font_size, dominant_font_name, is_bold).
        """
        lines_text: List[str] = []
        font_sizes: List[float] = []
        font_names: List[str] = []
        bold_flags: List[bool] = []

        for line in block.get("lines", []):
            span_texts: List[str] = []
            for span in line.get("spans", []):
                text = span.get("text", "")
                if text.strip():
                    span_texts.append(text)
                    font_sizes.append(float(span.get("size", 0.0)))
                    font_names.append(str(span.get("font", "")))
                    # fitz flags: bit 4 = bold
                    bold_flags.append(bool(span.get("flags", 0) & 2**4))
            if span_texts:
                lines_text.append("".join(span_texts))

        content = "\n".join(lines_text)
        dominant_size = max(font_sizes) if font_sizes else 0.0
        dominant_font = font_names[0] if font_names else ""
        is_bold = any(bold_flags)

        return content, dominant_size, dominant_font, is_bold

    # ------------------------------------------------------------------
    # Multi-Column Reading Order Reconstruction
    # ------------------------------------------------------------------

    def _reconstruct_multi_column_order(
        self, blocks: List[RawBlock], page: Any
    ) -> List[RawBlock]:
        """Reconstructs logical reading order for multi-column pages.

        Strategy:
        1. Split page width at the midpoint.
        2. Assign blocks to left or right column by x0 position.
        3. Sort each column by y0 (top-to-bottom).
        4. Concatenate: left column first, then right column.

        Args:
            blocks: Unsorted list of RawBlock instances for the page.
            page: The fitz Page object (used to get page width).

        Returns:
            Reordered list of RawBlock instances.
        """
        page_width: float = page.rect.width
        midpoint: float = page_width * _COLUMN_SPLIT_RATIO

        left_col = [b for b in blocks if b.bbox[0] < midpoint]
        right_col = [b for b in blocks if b.bbox[0] >= midpoint]

        left_col.sort(key=lambda b: b.bbox[1])
        right_col.sort(key=lambda b: b.bbox[1])

        return left_col + right_col

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def _overlaps_table(
        self,
        bbox: Tuple[float, float, float, float],
        table_bboxes: List[Tuple[float, float, float, float]],
    ) -> bool:
        """Returns True if bbox overlaps with any table bounding box.

        Used to prevent double-extraction of text already captured as a table.
        """
        x0, y0, x1, y1 = bbox
        for tx0, ty0, tx1, ty1 in table_bboxes:
            if x0 < tx1 and x1 > tx0 and y0 < ty1 and y1 > ty0:
                return True
        return False

    def _assert_open(self) -> None:
        """Raises ExtractionProviderError if no document is currently open."""
        if not self._doc:
            raise ExtractionProviderError("No document is open.")
