# Test Architectural Decisions & Strategy

This document outlines the testing strategy, architectural decisions, and frameworks employed in the PDF-to-MD Engine project. The goal is to ensure stability, maintainability, and Open-Closed Principle (OCP) compliance across all testing layers.

---

### What the tests validate

| Test module | Stage | What it validates |
|---|---|---|
| `tests/unit/core/test_preprocessor.py` | Stage 1 | PDF validation rules: missing file, wrong extension, oversized, encrypted, corrupted |
| `tests/unit/core/test_extraction_engine.py` | Stage 2 | Strategy selection, block classification (H1/H2/H3, paragraph, list, table, code), security gate |
| `tests/unit/core/test_markdown_generator.py` | Stage 3 | Rendering fidelity per block type, formatting compliance, security gate second pass, determinism |
| `tests/unit/core/test_quality_validator.py` | Stage 4 | Overall score formula, failure rules, threshold warnings, per-dimension sub-validators |
| `tests/unit/core/test_output_manager.py` | Stage 5 | Artifact write order, collision handling, manifest self-inclusion, JSON serialization, write verification |
| `tests/integration/test_preprocessor_integration.py` | Stage 1 | End-to-end preprocessing against real synthetic PDFs |
| `tests/integration/test_extraction_engine_integration.py` | Stage 2 | Full extraction pipeline with reading order and security gate |
| `tests/integration/test_markdown_generator_integration.py` | Stage 3 | Full rendering pipeline — multi-page IDMs, all block types, security |
| `tests/integration/test_quality_validator_integration.py` | Stage 4 | Full validation against clean and intentionally broken Markdown |
| `tests/integration/test_output_manager_integration.py` | Stage 5 | Real filesystem writes, artifact existence, collision handling, no-overwrite guarantee |
| `tests/ui/test_ui_e2e.py` | Stage 6 | - End-to-end browser workflows (Uploads, validation, visualizations, and downloads)<br>-Each test is self-contained and cleans up after itself, an validates every US defined for tghe system<br>- Include happy path, negative tests, and NFR validations |

**Current test results:** 133 tests — 100% passing.

---

## 1. Testing Strategy Overview

The testing strategy follows the testing pyramid, prioritizing fast, isolated tests while maintaining confidence through comprehensive end-to-end (E2E) UI verification.

*   **Unit Tests:** Focus on isolated core domain logic (e.g., `QualityValidator`, `MarkdownGenerator`). They use `pytest` and mock external dependencies like `PyMuPDF`.
*   **Integration Tests:** Validate the interaction between adapters and core services. This includes verifying the `PyMuPDFExtractionProvider` extracts text correctly without testing the UI.
*   **End-to-End (E2E) UI Tests:** Utilize Playwright and Streamlit to verify the application from the user's perspective, running through the browser to simulate real workflows.

### Test Data

- A set of PDFs for different complexity levels: `pdf_data/` (for unit/integration tests).
- A synthetic dataset of failing PDFs for Negative test cases: `tests/ui/data/` (for UI E2E tests).

## 2. Frameworks & Tooling

*   **Pytest:** The primary test runner for all levels (unit, integration, and E2E).
*   **Playwright (`pytest-playwright`):** Used exclusively for E2E UI testing against the Streamlit server.
*   **Pytest-HTML:** Used for generating self-contained test execution reports, complete with screenshots of test failures.

## 3. Architectural Decisions

### 3.1. E2E Test Execution Constraints
*   **Decision:** E2E UI tests run against the live `http://localhost:8501` instance instead of spawning a background headless subprocess in `conftest.py`.
*   **Reasoning:** Streamlit's WebSocket server and heavy `stdout` logging frequently caused OS pipe buffer exhaustion (`subprocess.PIPE`), leading to test timeouts and frozen headless browsers during large file uploads. Targeting the active environment ensures test stability.

### 3.2. OCP-Compliant Negative Testing
*   **Decision:** Non-Functional Requirements (NFR) and negative tests use the **Strategy Pattern** for synthetic data generation (`tests/utils/file_factory.py`).
*   **Reasoning:** To test scenarios like "oversized files", "forbidden extensions", or "corrupted PDFs", we dynamically generate synthetic payloads. By implementing `FileGenerationStrategy`, new negative scenarios can be added by creating a new class without modifying the core `FileFactory` logic, strictly adhering to the Open-Closed Principle.

### 3.3. Test Artifacts & Sandboxing
*   **Decision:** All test artifacts (HTML reports, failure screenshots) are localized to the `reports/` directory. All temporary, experimental scripts, and CLI logs are isolated in the `scratch/` directory.
*   **Reasoning:** Prevents repository pollution. Both directories are explicitly ignored by version control (`.gitignore`) to maintain a clean project architecture.

## 4. Key Workflows Tested

1.  **Happy Path Verification:** E2E validation of PDF uploads traversing the entire pipeline (Extraction → Formatting → Validation → Persistence) successfully.
2.  **System Rejection Rules (NFRs):** Validating the UI correctly intercepts and reports structural and NFR-based failures (e.g., `.exe` files, 10.1MB files, zero-text payload images).
3.  **Quality Gate Override:** Verifying that users can acknowledge and bypass the AI-driven Quality Validator using the override UI component when artifacts score below the designated confidence threshold.
