from typing import List, Protocol

from src.core.models.extraction import ExtractionStrategy, RawBlock


class ExtractionProvider(Protocol):
    """Protocol defining the contract for PDF extraction adapters.

    The core ExtractionEngine depends exclusively on this Protocol.
    No concrete PDF library is ever imported in the core domain.

    Implementors:
        - PyMuPdfExtractionProvider (src/adapters/pdf/pymupdf_extraction_provider.py)
    """

    def open(self, path: str) -> None:
        """Opens the PDF document for extraction.

        Args:
            path: Absolute path to the PDF file.

        Raises:
            ExtractionProviderError: If the document cannot be opened.
        """
        ...

    def close(self) -> None:
        """Closes and releases the PDF document."""
        ...

    def get_page_count(self) -> int:
        """Returns the total number of pages in the document.

        Returns:
            Total page count as a positive integer.
        """
        ...

    def extract_page_blocks(
        self, page_number: int, strategy: ExtractionStrategy
    ) -> List[RawBlock]:
        """Extracts raw blocks from a single page using the specified strategy.

        The adapter is responsible for:
        - Returning text blocks with font metadata in RawBlock.metadata.
        - Detecting tables via find_tables() and returning them as raw_type="table"
          with headers and rows in RawBlock.metadata.
        - Returning image blocks as raw_type="image" (content will be skipped).
        - Reconstructing column reading order when strategy is MULTI_COLUMN.
        - Evaluating each page independently when strategy is MIXED_LAYOUT.

        Args:
            page_number: 1-indexed page number.
            strategy: Extraction strategy selected by the engine.

        Returns:
            List of RawBlock instances ordered by logical reading position.
        """
        ...
