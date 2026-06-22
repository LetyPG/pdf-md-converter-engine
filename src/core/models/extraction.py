from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class BlockType(Enum):
    """Semantic type of an extracted document block."""

    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    CODE = "code"
    QUOTE = "quote"
    FIGURE = "figure"
    DIAGRAM = "diagram"


class ExtractionStrategy(Enum):
    """Strategy used by the Extraction Engine to process a document."""

    NATIVE_TEXT = "NATIVE_TEXT"
    OCR = "OCR"
    MULTI_COLUMN = "MULTI_COLUMN"
    MIXED_LAYOUT = "MIXED_LAYOUT"


@dataclass
class RawBlock:
    """Internal transfer object between adapter and core engine.

    The adapter produces RawBlock instances. The core engine classifies
    them into typed Block instances. This type belongs to the core domain
    because it is part of the provider contract.

    Attributes:
        raw_type: Adapter-level block type — "text", "image", or "table".
        content: Raw text content of the block.
        bbox: Bounding box as (x0, y0, x1, y1) in PDF coordinate space.
        page: 1-indexed page number.
        order: Sequential reading position within the page.
        metadata: Adapter-specific properties (font_size, font, bold, headers, rows, …).
    """

    raw_type: str
    content: str
    bbox: Tuple[float, float, float, float]
    page: int
    order: int
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Typed block dataclasses
# ---------------------------------------------------------------------------

@dataclass
class HeadingBlock:
    """A heading block with a semantic level (1–3)."""

    block_id: str
    type: BlockType
    page: int
    order: int
    level: int
    content: str


@dataclass
class ParagraphBlock:
    """A standard text paragraph block."""

    block_id: str
    type: BlockType
    page: int
    order: int
    content: str


@dataclass
class ListBlock:
    """An ordered or unordered list block."""

    block_id: str
    type: BlockType
    page: int
    order: int
    ordered: bool
    items: List[str]


@dataclass
class TableBlock:
    """A structured table block with headers and rows."""

    block_id: str
    type: BlockType
    page: int
    order: int
    headers: List[str]
    rows: List[List[str]]


@dataclass
class CodeBlock:
    """A code or pre-formatted text block."""

    block_id: str
    type: BlockType
    page: int
    order: int
    language: Optional[str]
    content: str


@dataclass
class QuoteBlock:
    """A blockquote block.

    NOTE: Detection is deferred. The type is defined so the contract is complete
    and downstream renderers can implement it, but the ExtractionEngine does not
    emit QuoteBlock instances in the current phase.
    """

    block_id: str
    type: BlockType
    page: int
    order: int
    content: str


@dataclass
class FigureBlock:
    """A figure placeholder block. Raw image content is NOT extracted."""

    block_id: str
    type: BlockType
    page: int
    order: int
    caption: Optional[str]


@dataclass
class DiagramBlock:
    """A diagram placeholder block. Raw image content is NOT extracted."""

    block_id: str
    type: BlockType
    page: int
    order: int
    caption: Optional[str]


Block = Union[
    HeadingBlock,
    ParagraphBlock,
    ListBlock,
    TableBlock,
    CodeBlock,
    QuoteBlock,
    FigureBlock,
    DiagramBlock,
]

# ---------------------------------------------------------------------------
# IDM container
# ---------------------------------------------------------------------------

@dataclass
class DocumentPage:
    """A single page in the Intermediate Document Model."""

    page_number: int
    blocks: List[Block] = field(default_factory=list)


@dataclass
class IntermediateDocumentModel:
    """Complete output of the Extraction Engine.

    Consumed exclusively by the Markdown Generator (Stage 3).
    """

    strategy_used: ExtractionStrategy
    pages: List[DocumentPage] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
