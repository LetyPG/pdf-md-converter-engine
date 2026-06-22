import json
import logging
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

# The ONLY engine import allowed in the UI
from scripts.pdfmd_converter import run_pipeline

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """Artifact payload returned to the UI after execution."""
    success: bool
    run_directory: str
    run_id: str
    source_document: str
    duration_ms: int
    markdown_content: str
    validation_data: dict
    execution_data: dict
    manifest_data: dict
    logs_content: str
    artifact_paths: dict[str, str]
    error_message: Optional[str] = None
    is_quality_failure: bool = False


class ConversionService:
    """Bridge between the Streamlit UI and the core engine.

    The UI layers call this service; this service calls the engine's public
    pipeline runner and reads back the generated artifacts.
    """

    MAX_FILE_SIZE_MB = 10.0
    MAX_FILE_SIZE_BYTES = int(MAX_FILE_SIZE_MB * 1024 * 1024)

    @staticmethod
    def validate_upload(file: UploadedFile) -> Tuple[bool, str]:
        """Client-side pre-validation matching engine preconditions.

        Args:
            file: Streamlit UploadedFile object.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file.name.lower().endswith(".pdf"):
            return False, "Selected file is not a PDF."
        
        if file.size > ConversionService.MAX_FILE_SIZE_BYTES:
            return False, f"File size ({file.size / 1024 / 1024:.1f} MB) exceeds limit of {ConversionService.MAX_FILE_SIZE_MB} MB."

        return True, ""

    @staticmethod
    def execute_conversion(file: UploadedFile, output_dir: str = "./outputs") -> ConversionResult:
        """Executes the pipeline and returns parsed artifacts.

        Args:
            file: Validated UploadedFile.
            output_dir: Target base output directory.

        Returns:
            ConversionResult containing all artifact contents.
        """
        # Engine expects a real file path, not an in-memory buffer.
        # We write the upload to a temp file, preserving the original filename
        # so the engine generates the correct Markdown filename.
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_pdf_path = Path(tmp_dir) / file.name
            tmp_pdf_path.write_bytes(file.getvalue())

            try:
                # Invoke the engine
                exit_code, err_msg = run_pipeline(str(tmp_pdf_path), output_dir)
                
                if exit_code not in (0, 2):
                    return ConversionResult(
                        success=False,
                        run_directory="",
                        run_id="",
                        source_document=file.name,
                        duration_ms=0,
                        markdown_content="",
                        validation_data={},
                        execution_data={},
                        manifest_data={},
                        logs_content="",
                        artifact_paths={},
                        error_message=err_msg
                    )

                # Read artifacts from the most recent run directory for this source doc
                result = ConversionService._load_artifacts(file.name, output_dir)
                
                if exit_code == 2:
                    result.success = False
                    result.is_quality_failure = True
                    result.error_message = err_msg
                    
                return result

            except Exception as e:
                logger.exception("Conversion failed exceptionally.")
                return ConversionResult(
                    success=False,
                    run_directory="",
                    run_id="",
                    source_document=file.name,
                    duration_ms=0,
                    markdown_content="",
                    validation_data={},
                    execution_data={},
                    manifest_data={},
                    logs_content="",
                    artifact_paths={},
                    error_message=f"System error: {str(e)}"
                )

    @staticmethod
    def _load_artifacts(source_filename: str, output_dir: str) -> ConversionResult:
        """Finds the run directory and parses all 5 artifacts."""
        md_filename = Path(source_filename).stem + ".md"
        base = Path(output_dir)

        # Find the most recently created run directory containing this MD file
        run_dirs = sorted([d for d in base.iterdir() if d.is_dir() and d.name.startswith("run_")],
                          key=lambda d: d.stat().st_mtime, reverse=True)
        
        target_run_dir = None
        for d in run_dirs:
            if (d / md_filename).exists():
                target_run_dir = d
                break

        if not target_run_dir:
            raise FileNotFoundError(f"Could not locate output directory for {source_filename}")

        # Paths
        paths = {
            "markdown": str(target_run_dir / md_filename),
            "validation": str(target_run_dir / "validation.json"),
            "execution": str(target_run_dir / "execution.json"),
            "logs": str(target_run_dir / "logs.txt"),
            "manifest": str(target_run_dir / "manifest.json")
        }

        # Load content
        execution_data = json.loads(Path(paths["execution"]).read_text(encoding="utf-8"))
        
        return ConversionResult(
            success=True,
            run_directory=str(target_run_dir),
            run_id=execution_data.get("run_id", ""),
            source_document=source_filename,
            duration_ms=execution_data.get("duration_ms", 0),
            markdown_content=Path(paths["markdown"]).read_text(encoding="utf-8"),
            validation_data=json.loads(Path(paths["validation"]).read_text(encoding="utf-8")),
            execution_data=execution_data,
            manifest_data=json.loads(Path(paths["manifest"]).read_text(encoding="utf-8")),
            logs_content=Path(paths["logs"]).read_text(encoding="utf-8"),
            artifact_paths=paths,
            error_message=None
        )
