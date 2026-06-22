from abc import ABC, abstractmethod
from pathlib import Path
import fitz  # PyMuPDF

class FileGenerationStrategy(ABC):
    """Abstract base class for all synthetic file generators."""
    @abstractmethod
    def generate(self, target_dir: Path) -> Path:
        pass

class OversizedFileStrategy(FileGenerationStrategy):
    def __init__(self, size_mb: int = 11):
        self.size_mb = size_mb
        
    def generate(self, target_dir: Path) -> Path:
        file_path = target_dir / f"oversized_{self.size_mb}mb.pdf"
        with open(file_path, "wb") as f:
            f.seek(int(self.size_mb * 1024 * 1024) - 1)
            f.write(b"\0")
        return file_path

class InvalidExtensionStrategy(FileGenerationStrategy):
    def __init__(self, extension: str = ".exe"):
        self.extension = extension
        
    def generate(self, target_dir: Path) -> Path:
        file_path = target_dir / f"malicious_payload{self.extension}"
        file_path.write_text("DUMMY_CONTENT")
        return file_path

class CorruptedPDFStrategy(FileGenerationStrategy):
    def generate(self, target_dir: Path) -> Path:
        file_path = target_dir / "corrupted.pdf"
        file_path.write_bytes(b"%PDF-1.7\n%%EOF_CORRUPTED")
        return file_path

class ImageOnlyPDFStrategy(FileGenerationStrategy):
    def generate(self, target_dir: Path) -> Path:
        file_path = target_dir / "image_only.pdf"
        doc = fitz.open()
        page = doc.new_page()
        # Create a dummy image (pixmap)
        pix = fitz.Pixmap(fitz.csRGB, (0, 0, 100, 100), False)
        pix.clear_with(255)
        page.insert_image(page.rect, pixmap=pix)
        doc.save(file_path)
        doc.close()
        return file_path

class ForbiddenContentPDFStrategy(FileGenerationStrategy):
    def __init__(self, forbidden_text: str):
        self.forbidden_text = forbidden_text

    def generate(self, target_dir: Path) -> Path:
        # e.g., "http://malware.com" or "test@email.com"
        safe_name = "".join(c if c.isalnum() else "_" for c in self.forbidden_text)
        file_path = target_dir / f"forbidden_{safe_name}.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), self.forbidden_text, fontsize=11)
        doc.save(file_path)
        doc.close()
        return file_path

class FileFactory:
    """Factory executing the provided strategy (OCP compliant)."""
    @staticmethod
    def create(strategy: FileGenerationStrategy, target_dir: Path) -> Path:
        return strategy.generate(target_dir)