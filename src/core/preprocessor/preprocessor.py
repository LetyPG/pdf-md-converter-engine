from typing import Optional
from src.core.models.preprocessor import (
    DocumentProfile, 
    PreprocessingResult, 
    RejectionReason,
    LayoutType,
    PageOrientation
)
from src.core.preprocessor.pdf_provider import PdfProvider
from src.shared.utils import file_utils
import logging

logger = logging.getLogger(__name__)

class Preprocessor:
    def __init__(self, pdf_provider: PdfProvider):
        self.pdf_provider = pdf_provider

    def process(self, pdf_path: str) -> PreprocessingResult:
        # 1. Input Validation
        if not file_utils.file_exists(pdf_path):
            return PreprocessingResult(status="rejected", reason=RejectionReason.FILE_NOT_FOUND)

        ext = file_utils.get_file_extension(pdf_path)
        if ext != "pdf":
            return PreprocessingResult(status="rejected", reason=RejectionReason.FILE_UNSUPPORTED)

        size_mb = file_utils.get_file_size_mb(pdf_path)
        if size_mb > 10.0:
            return PreprocessingResult(status="rejected", reason=RejectionReason.FILE_TOO_LARGE)

        # Use provider to open and check further
        try:
            self.pdf_provider.open(pdf_path)
        except Exception as e:
            logger.error(f"Failed to open PDF: {e}")
            return PreprocessingResult(status="rejected", reason=RejectionReason.FILE_CORRUPTED)

        try:
            if self.pdf_provider.is_encrypted():
                return PreprocessingResult(status="rejected", reason=RejectionReason.PASSWORD_PROTECTED)

            # 2. Document Profiling
            pages = self.pdf_provider.get_page_count()
            metadata = self.pdf_provider.get_metadata()
            layout_type, page_orientation, mixed_layout = self.pdf_provider.analyze_layout_and_orientation()
            text_layer_present = self.pdf_provider.has_text_layer()
            likely_scanned = self.pdf_provider.is_likely_scanned()
            elements = self.pdf_provider.detect_elements()

            warnings = []
            if pages > 300:
                warnings.append("Document exceeds 300 pages.")
            if layout_type == LayoutType.UNKNOWN:
                warnings.append("Layout type could not be reliably determined.")
            if mixed_layout:
                warnings.append("Document has a mixed layout.")
            if likely_scanned:
                warnings.append("Document appears to be scanned.")
            if layout_type == LayoutType.VERTICAL:
                warnings.append("Vertical text layout detected.")

            profile = DocumentProfile(
                pages=pages,
                size_mb=round(size_mb, 2),
                metadata=metadata,
                layout_type=layout_type,
                page_orientation=page_orientation,
                text_layer_present=text_layer_present,
                likely_scanned=likely_scanned,
                mixed_layout=mixed_layout,
                warnings=warnings,
                images=elements.get("images"),
                graphs=elements.get("graphs"),
                tables=elements.get("tables"),
                code_blocks=elements.get("code_blocks"),
                hrefs=elements.get("hrefs"),
                urls=elements.get("urls"),
                emails=elements.get("emails")
            )

            return PreprocessingResult(status="accepted", document_profile=profile)

        finally:
            self.pdf_provider.close()
