from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional

class LayoutType(Enum):
    SINGLE_COLUMN = "SINGLE_COLUMN"
    MULTI_COLUMN = "MULTI_COLUMN"
    MIXED = "MIXED"
    VERTICAL = "VERTICAL"
    UNKNOWN = "UNKNOWN"

class PageOrientation(Enum):
    PORTRAIT = "PORTRAIT"
    LANDSCAPE = "LANDSCAPE"
    MIXED = "MIXED"
    UNKNOWN = "UNKNOWN"

class RejectionReason(Enum):
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_CORRUPTED = "FILE_CORRUPTED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_UNSUPPORTED = "FILE_UNSUPPORTED"
    PASSWORD_PROTECTED = "PASSWORD_PROTECTED"

@dataclass
class DocumentProfile:
    pages: int
    size_mb: float
    metadata: Dict[str, Any]
    layout_type: LayoutType
    page_orientation: PageOrientation
    text_layer_present: bool
    likely_scanned: bool
    mixed_layout: bool
    warnings: List[str] = field(default_factory=list)
    
    images: Optional[bool] = None
    graphs: Optional[bool] = None
    tables: Optional[bool] = None
    code_blocks: Optional[bool] = None
    hrefs: Optional[bool] = None
    urls: Optional[bool] = None
    emails: Optional[bool] = None

@dataclass
class PreprocessingResult:
    status: str # "accepted" or "rejected"
    document_profile: Optional[DocumentProfile] = None
    reason: Optional[RejectionReason] = None
