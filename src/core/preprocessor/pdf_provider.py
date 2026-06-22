from typing import Protocol, Dict, Any, Tuple
from src.core.models.preprocessor import LayoutType, PageOrientation

class PdfProvider(Protocol):
    def open(self, path: str) -> None:
        """Opens the PDF document. Raises an exception if corrupted or not found."""
        ...

    def close(self) -> None:
        """Closes the PDF document."""
        ...

    def is_encrypted(self) -> bool:
        """Returns True if the document is password protected."""
        ...

    def get_page_count(self) -> int:
        """Returns the number of pages."""
        ...

    def get_metadata(self) -> Dict[str, Any]:
        """Returns document metadata."""
        ...

    def analyze_layout_and_orientation(self) -> Tuple[LayoutType, PageOrientation, bool]:
        """Returns LayoutType, PageOrientation, and a boolean indicating if it's mixed layout."""
        ...

    def has_text_layer(self) -> bool:
        """Returns True if the document has embedded text."""
        ...

    def is_likely_scanned(self) -> bool:
        """Returns True if the document appears to be mostly images/scanned."""
        ...

    def detect_elements(self) -> Dict[str, bool]:
        """Detects presence of optional elements (images, graphs, tables, code_blocks, hrefs, urls, emails)."""
        ...
