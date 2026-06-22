import fitz  # PyMuPDF
from typing import Dict, Any, Tuple
from src.core.models.preprocessor import LayoutType, PageOrientation
from src.shared.exceptions.preprocessor_exceptions import PdfProviderError
import logging

logger = logging.getLogger(__name__)

class PyMuPdfProvider:
    def __init__(self):
        self.doc = None
        self.path = None

    def open(self, path: str) -> None:
        self.path = path
        try:
            self.doc = fitz.open(path)
        except Exception as e:
            logger.error(f"PyMuPDF failed to open {path}: {e}")
            raise PdfProviderError(f"Failed to open PDF: {e}")

    def close(self) -> None:
        if self.doc:
            self.doc.close()
            self.doc = None

    def is_encrypted(self) -> bool:
        if not self.doc:
            raise PdfProviderError("Document not open")
        return self.doc.is_encrypted

    def get_page_count(self) -> int:
        if not self.doc:
            raise PdfProviderError("Document not open")
        return len(self.doc)

    def get_metadata(self) -> Dict[str, Any]:
        if not self.doc:
            raise PdfProviderError("Document not open")
        
        meta = self.doc.metadata
        if not meta:
            return {}
            
        return {
            "title": meta.get("title", ""),
            "author": meta.get("author", ""),
            "subject": meta.get("subject", ""),
            "keywords": meta.get("keywords", "").split(",") if meta.get("keywords") else [],
            "creator": meta.get("creator", ""),
            "producer": meta.get("producer", ""),
            "creation_date": meta.get("creationDate", ""),
            "modification_date": meta.get("modDate", ""),
            "pdf_version": "",  # fitz might not provide this directly in metadata
            "page_count": self.get_page_count()
        }

    def analyze_layout_and_orientation(self) -> Tuple[LayoutType, PageOrientation, bool]:
        if not self.doc:
            raise PdfProviderError("Document not open")
        
        # Heuristics for orientation
        orientations = set()
        for page_num in range(min(10, len(self.doc))): # check up to 10 pages
            page = self.doc[page_num]
            rect = page.rect
            if rect.width > rect.height:
                orientations.add(PageOrientation.LANDSCAPE)
            else:
                orientations.add(PageOrientation.PORTRAIT)
                
        if len(orientations) > 1:
            orientation = PageOrientation.MIXED
        elif orientations:
            orientation = list(orientations)[0]
        else:
            orientation = PageOrientation.UNKNOWN

        # Simplified layout heuristics
        layout = LayoutType.UNKNOWN
        mixed_layout = False
        
        layouts = set()
        for page_num in range(min(5, len(self.doc))): # check up to 5 pages
            page = self.doc[page_num]
            blocks = page.get_text("blocks")
            is_multi = False
            for i in range(len(blocks)):
                for j in range(i+1, len(blocks)):
                    b1 = blocks[i]
                    b2 = blocks[j]
                    # Check vertical overlap
                    if max(b1[1], b2[1]) < min(b1[3], b2[3]):
                        # Check horizontal separation
                        if b1[2] < b2[0] or b2[2] < b1[0]:
                            is_multi = True
                            break
                if is_multi:
                    break
            
            if is_multi:
                layouts.add(LayoutType.MULTI_COLUMN)
            else:
                layouts.add(LayoutType.SINGLE_COLUMN)
                
        if len(layouts) > 1:
            layout = LayoutType.MIXED
            mixed_layout = True
        elif layouts:
            layout = list(layouts)[0]
            
        return layout, orientation, mixed_layout

    def has_text_layer(self) -> bool:
        if not self.doc:
            raise PdfProviderError("Document not open")
            
        # Check first few pages for text
        for page_num in range(min(5, len(self.doc))):
            page = self.doc[page_num]
            text = page.get_text()
            if text.strip():
                return True
        return False

    def is_likely_scanned(self) -> bool:
        if not self.doc:
            raise PdfProviderError("Document not open")
            
        if self.has_text_layer():
            return False
            
        # Check if pages are just large images
        for page_num in range(min(5, len(self.doc))):
            page = self.doc[page_num]
            images = page.get_images()
            if not images:
                return False # No text and no images, maybe empty
        
        return True # No text layer, but has images

    def detect_elements(self) -> Dict[str, bool]:
        if not self.doc:
            raise PdfProviderError("Document not open")
            
        elements = {
            "images": False,
            "graphs": False,
            "tables": False,
            "code_blocks": False,
            "hrefs": False,
            "urls": False,
            "emails": False
        }
        
        for page_num in range(min(5, len(self.doc))):
            page = self.doc[page_num]
            
            if page.get_images():
                elements["images"] = True
                
            links = page.get_links()
            if links:
                for link in links:
                    kind = link.get("kind")
                    uri = link.get("uri", "")
                    if kind == fitz.LINK_URI:
                        elements["hrefs"] = True
                        if uri.startswith("http"):
                            elements["urls"] = True
                        if uri.startswith("mailto:"):
                            elements["emails"] = True
        
        return elements
