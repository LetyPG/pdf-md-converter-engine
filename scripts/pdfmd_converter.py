#!/usr/bin/env python3
"""pdfmd_converter — PDF to Markdown conversion pipeline runner.

Wires all 5 pipeline stages together and executes a single end-to-end conversion:

    Stage 1: Preprocessor          (validates & profiles the PDF)
    Stage 2: Extraction Engine     (extracts IDM from the PDF)
    Stage 3: Markdown Generator    (renders IDM → Markdown string)
    Stage 4: Quality Validator     (scores the Markdown against IDM)
    Stage 5: Output Manager        (persists all artifacts to disk)

Usage:
    python -m scripts.pdfmd_converter <path-to-pdf> [--output <output-dir>]

Example:
    python -m scripts.pdfmd_converter pdf_data/Stakeholder-Report.pdf
    python -m scripts.pdfmd_converter pdf_data/Tokens.pdf --output ./results
"""
import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

# ---------------------------------------------------------------------------
# Logging setup — must be first so all module loggers pick up the config
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("pdf2md.pipeline")

# ---------------------------------------------------------------------------
# Stage imports
# ---------------------------------------------------------------------------
from src.core.preprocessor.preprocessor import Preprocessor
from src.adapters.pdf.pymupdf_provider import PyMuPdfProvider

from src.core.extraction.extraction_engine import ExtractionEngine
from src.adapters.pdf.pymupdf_extraction_provider import PyMuPdfExtractionProvider

from src.core.markdown.markdown_generator import create_default_generator

from src.core.validation.quality_validator import create_default_validator

from src.core.output.output_manager import create_default_output_manager
from src.core.models.output import ExecutionMetadata

_ENGINE_VERSION = "1.0.0"


def _build_run_id(started_at: datetime) -> str:
    return started_at.strftime("%Y%m%d_%H%M%S")


def run_pipeline(pdf_path: str, output_dir: str, ignore_quality_gate: bool = False) -> Tuple[int, str]:
    """Executes the full 5-stage pipeline.

    Args:
        pdf_path:   Absolute or relative path to the input PDF.
        output_dir: Root output directory for artifacts.
        ignore_quality_gate: If True, returns success (0) even if Quality Gate fails.

    Returns:
        Tuple of (exit_code, error_message). (0, "") on success.
    """
    started_at = datetime.now(timezone.utc)
    run_id = _build_run_id(started_at)
    source_doc = Path(pdf_path).name

    log_lines: list[str] = []

    def log(msg: str, level: str = "INFO") -> None:
        line = f"[{level}] {msg}"
        log_lines.append(line)
        getattr(logger, level.lower(), logger.info)(msg)

    log(f"=== pdf2md pipeline started ===")
    log(f"run_id        : {run_id}")
    log(f"source        : {pdf_path}")
    log(f"output_dir    : {output_dir}")
    log(f"engine_version: {_ENGINE_VERSION}")

    # ------------------------------------------------------------------
    # Stage 1: Preprocessor
    # ------------------------------------------------------------------
    log("--- Stage 1: Preprocessor ---")
    t0 = time.perf_counter()
    preprocessor = Preprocessor(PyMuPdfProvider())
    preprocessing_result = preprocessor.process(pdf_path)
    log(f"Status: {preprocessing_result.status}")

    if preprocessing_result.status != "accepted":
        reason = preprocessing_result.reason
        log(f"Pipeline halted: PDF rejected ({reason})", "ERROR")
        return 1, f"Preprocessing Failed: The document was rejected because: {reason}. Please ensure the PDF is valid, not encrypted, and under 10MB."

    profile = preprocessing_result.document_profile
    log(f"Pages         : {profile.pages}")
    log(f"Size (MB)     : {profile.size_mb}")
    log(f"Layout        : {profile.layout_type.value}")
    log(f"Text layer    : {profile.text_layer_present}")
    log(f"Likely scanned: {profile.likely_scanned}")
    for w in (profile.warnings or []):
        log(f"[WARN] {w}", "WARNING")
    log(f"Stage 1 completed in {time.perf_counter() - t0:.2f}s")

    # ------------------------------------------------------------------
    # Stage 2: Extraction Engine
    # ------------------------------------------------------------------
    log("--- Stage 2: Extraction Engine ---")
    t0 = time.perf_counter()
    extraction_engine = ExtractionEngine(PyMuPdfExtractionProvider())
    idm = extraction_engine.extract(pdf_path, preprocessing_result)
    log(f"Strategy used : {idm.strategy_used.value}")
    log(f"Pages in IDM  : {len(idm.pages)}")
    total_blocks = sum(len(p.blocks) for p in idm.pages)
    log(f"Total blocks  : {total_blocks}")
    for w in idm.warnings:
        log(f"[WARN] {w}", "WARNING")
    log(f"Stage 2 completed in {time.perf_counter() - t0:.2f}s")

    # ------------------------------------------------------------------
    # Stage 3: Markdown Generator
    # ------------------------------------------------------------------
    log("--- Stage 3: Markdown Generator ---")
    t0 = time.perf_counter()
    generator = create_default_generator()
    markdown_result = generator.generate(idm)
    log(f"Markdown length: {len(markdown_result.content)} chars")
    for w in markdown_result.warnings:
        log(f"[WARN] {w}", "WARNING")
    log(f"Stage 3 completed in {time.perf_counter() - t0:.2f}s")

    # ------------------------------------------------------------------
    # Stage 4: Quality Validator
    # ------------------------------------------------------------------
    log("--- Stage 4: Quality Validator ---")
    t0 = time.perf_counter()
    validator = create_default_validator()
    report = validator.validate(idm, markdown_result)
    log(f"Structural    : {report.structural_score:.1f}")
    log(f"Rendering     : {report.rendering_score:.1f}")
    log(f"Security      : {report.security_score:.1f}")
    log(f"Completeness  : {report.completeness_score:.1f}")
    log(f"Overall       : {report.overall_score:.1f}")
    log(f"Passed        : {report.passed}")
    for w in report.warnings:
        log(f"[WARN] {w}", "WARNING")
    for f in report.findings:
        log(f"[{f.severity.value}] [{f.category.value}] {f.message}", "WARNING")
    log(f"Stage 4 completed in {time.perf_counter() - t0:.2f}s")

    # ------------------------------------------------------------------
    # Stage 5: Output Manager
    # ------------------------------------------------------------------
    log("--- Stage 5: Output Manager ---")
    t0 = time.perf_counter()
    completed_at = datetime.now(timezone.utc)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    metadata = ExecutionMetadata(
        run_id=run_id,
        source_document=source_doc,
        started_at=started_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        completed_at=completed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        duration_ms=duration_ms,
        engine_version=_ENGINE_VERSION,
    )

    output_manager = create_default_output_manager(base_output_dir=output_dir)
    output_result = output_manager.save(
        markdown_result=markdown_result,
        validation_report=report,
        metadata=metadata,
        logs="\n".join(log_lines),
    )
    log(f"Run directory : {output_result.run_directory}")
    log(f"Artifacts     : {output_result.artifacts}")
    log(f"Stage 5 completed in {time.perf_counter() - t0:.2f}s")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    log("=== Pipeline complete ===")
    log(f"Validation passed: {report.passed}")
    if not report.passed:
        log("Artifact did NOT pass quality gate.", "WARNING")
        
        # Compile a summary of why it failed
        hard_fails = [f"[{f.category.value}] {f.message}" for f in report.findings if f.severity.value == "ERROR"]
        error_details = "\n- ".join(hard_fails)
        
        if ignore_quality_gate:
            log("QUALITY OVERRIDE ACTIVE: Bypassing quality gate failure due to --ignore-quality-gate flag.", "WARNING")
            return 0, ""
        else:
            err_msg = f"Quality Validation Failed (Score: {report.overall_score:.1f}/100).\nThe generated artifact did not meet strict quality or security standards.\n\nCritical Findings:\n- {error_details}\n\nThis file cannot be processed safely or accurately."
            return 2, err_msg
    return 0, ""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="pdfmd_converter — PDF to Markdown conversion pipeline"
    )
    parser.add_argument("pdf", help="Path to the input PDF file")
    parser.add_argument(
        "--output", default="./outputs", help="Output directory (default: ./outputs)"
    )
    parser.add_argument(
        "--ignore-quality-gate",
        action="store_true",
        help="Force a successful exit code (0) even if the generated artifact fails the Quality Gate validation. Use with caution."
    )
    args = parser.parse_args()

    exit_code, err_msg = run_pipeline(
        pdf_path=os.path.abspath(args.pdf),
        output_dir=args.output,
        ignore_quality_gate=args.ignore_quality_gate,
    )
    
    if exit_code != 0:
        print(f"\nPipeline Failed:\n{err_msg}", file=sys.stderr)
        
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
