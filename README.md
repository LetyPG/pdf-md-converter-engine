# pdf-to-md-engine-converter
[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=fff)](#)[![PyPI](https://img.shields.io/badge/PyPI-3775A9?logo=pypi&logoColor=fff)](#)[![Markdown](https://img.shields.io/badge/Markdown-%23000000.svg?logo=markdown&logoColor=white)](#)[![GNOME Terminal](https://img.shields.io/badge/GNOME%20Terminal-241F31?logo=gnometerminal&logoColor=fff)](#)[![PowerShell](https://custom-icon-badges.demolab.com/badge/PowerShell-5391FE?logo=powershell-white&logoColor=fff)](#)[![Git](https://img.shields.io/badge/Git-F05032?logo=git&logoColor=fff)](#)[![GitHub](https://img.shields.io/badge/GitHub-%23121011.svg?logo=github&logoColor=white)](#)[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?logo=github-actions&logoColor=white)](#)[![Pytest](https://img.shields.io/badge/Pytest-fff?logo=pytest&logoColor=000)](#)[![Playwright](https://custom-icon-badges.demolab.com/badge/Playwright-2EAD33?logo=playwright&logoColor=fff)](#)

**Open-source · Local-first · Deterministic · LLM-free**

A local utility that converts PDF documents into high-fidelity Markdown assets — deterministically, privately, and without any cloud dependency or LLM at runtime.

The generated Markdown is designed to serve as a reusable knowledge artifact for AI workflows: RAG pipelines, agent memory systems, skill repositories, documentation pipelines, and local AI projects.

---
# Design Documents

All major design decisions, architecture choices, and evolution trade-offs are recorded in the `docs/` directory.

- [System Requirements and User Scenarios](docs/user_scenarios.md)
- [Problem Origins](docs/problem_origin.md)
- [Implementation Architecture](docs/implementation_architecture.md)
- [Test Architectural Decisions](docs/test_architectural_decisions.md)
- [UI Description](docs/ui_description.md)
- [Agent Native Workflow Description](docs/agent_ai_driven_description.md)

---
## Problem Origins of the Project

PDF-to-MD Converter is a lightweight local knowledge-preparation utility that transforms well-structured PDF reference documents into AI-optimized Markdown artifacts, reducing token consumption, improving retrieval accuracy, and enabling efficient agent-driven workflows without requiring vector databases or external infrastructure.

**Problem origins details refer to [docs/problem_origins.md](docs/problem_origin.md)**

---
## Product Vision

PDF documents are the most common format for technical knowledge, but they are not directly consumable by AI systems, agent frameworks, or version control workflows. This tool bridges that gap by converting PDFs into clean, structured, human-readable Markdown — entirely on the user's machine.

The converter's responsibility is precisely bounded:

```
PDF → Markdown Asset → Human / RAG / Agent
```

It produces a trustworthy Markdown artifact. What happens after — chunking, embedding, retrieval, summarization — belongs to downstream systems.

The tool can operate as:

- A **standalone CLI utility** for one-off conversions
- A **developer tool** integrated into documentation or CI workflows
- A **Python library** embedded into local agent or RAG projects
- A **preprocessing component** in local AI knowledge pipelines

**System Requirements and User Scenarios details refer to [docs/user_scenarios.md](docs/user_scenarios.md)**

---
## AI Native Development

The project was built using an **AI-native development methodology** — a structured approach where an AI coding agent (Antigravity, powered by Google DeepMind) acts as the primary implementer, guided by a layered set of human-authored documents instead of informal verbal instructions.

**AI Native Development details refer to [docs/agent_ai_driven_description.md](docs/agent_ai_driven_description.md)**

---
## Preconditions for PDF Processing

Before submitting a PDF, ensure the following conditions are met:

| Condition | Requirement |
|---|---|
| **File format** | Must be a `.pdf` file |
| **File size** | Must be ≤ 10 MB |
| **Text layer** | PDF must contain native embedded text (not image-only/scanned) |
| **Encryption** | Must NOT be password-protected or encrypted |
| **Corruption** | File must be readable and not corrupted |
| **Batch mode** | Only one PDF per invocation is supported in the current version |
---

## Pipeline Architecture

The conversion runs as a linear 5-stage pipeline. Each stage communicates only through typed data contracts:

```
PDF file
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 1: Preprocessor                                          │
│  Validates the PDF and builds a DocumentProfile.                │
│  Rejects: missing file, wrong format, >10MB, encrypted,        │
│  corrupted.                                                     │
└─────────────────────────┬───────────────────────────────────────┘
                          │ PreprocessingResult
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 2: Extraction Engine                                     │
│  Selects strategy (NATIVE_TEXT / MULTI_COLUMN / MIXED_LAYOUT)  │
│  and extracts blocks into an Intermediate Document Model (IDM). │
│  Applies first security gate.                                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ IntermediateDocumentModel
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 3: Markdown Generator                                    │
│  Renders IDM blocks into a Markdown string using the Strategy   │
│  Pattern. Applies second security gate pass.                    │
└─────────────────────────┬───────────────────────────────────────┘
                          │ MarkdownResult
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 4: Quality Validator                ← strategic component│
│  Scores the Markdown against the IDM across 4 dimensions:       │
│  Structural · Rendering · Security · Completeness.             │
│  Enforces hard failure rules.                                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ ValidationReport
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│  Stage 5: Output Manager                                        │
│  Persists all artifacts to an isolated run directory.           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
outputs/run_YYYYMMDD_HHMMSS/
  ├── <source>.md
  ├── validation.json
  ├── execution.json
  ├── logs.txt
  └── manifest.json
```
**Implementation Details and Decisions refer to [docs/implementation_architecture.md](docs/implementation_architecture.md).**

### Why the Quality Validator is part of the pipeline

The Quality Validator was added as a **strategic component** — not just a testing utility, but a first-class runtime stage. It measures four dimensions of the generated artifact:

| Dimension | Weight | Failure rule |
|---|---|---|
| Structural | 35% | Warning when score < 95 |
| Rendering | 25% | **Pipeline FAILS when score < 100** |
| Security | 25% | **Pipeline FAILS when score < 100** |
| Completeness | 15% | Warning when score < 95 |

This design decision enforces that **every artifact produced by the converter is measurably trustworthy** before it is persisted — quality is not an afterthought verified externally, but an in-process gate.

---

## Quick Start 

### 1. Clone the repository

```bash
git clone https://github.com/your-org/pdf-to-md-engine-converter.git
cd pdf-to-md-engine-converter
```

### 2. Create and activate a virtual environment

> **Recommended:** Always use a virtual environment to avoid dependency conflicts.

```bash
python3 -m venv venv
source venv/bin/activate        # Linux / macOS
# venv\Scripts\activate         # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

**Option A: Web User Interface (Recommended)**

Start the interactive Streamlit dashboard:

```bash
python -m streamlit run ui/app.py
```
This will open your default web browser to `http://localhost:8501`.

**UI User Guide refer to [docs/ui_description.md](docs/ui_description.md)**

**Option B: Command Line Interface**

Convert a single PDF directly from the terminal:

```bash
# Default behaviour
python -m scripts.pdfmd_converter <path-to-pdf> 
# Custom output direvctory
python -m scripts.pdfmd_converter <path-to-pdf> --output <custom-dir>
# Ignore quality gate failure
python -m scripts.pdfmd_converter <path-to-pdf> --output <custom-dir> --ignore-quality-gate
```

**CLI Options:**
- `<path-to-pdf>`: Required. The PDF file to convert.
- `--output`: Optional. Custom directory for artifacts (default: `./outputs`).
- `--ignore-quality-gate`: Optional. Bypasses a Quality Gate failure, returning a successful exit code (0) even if the generated artifacts fail validation. Use with caution.

**Using the sample PDFs included in the repository:**

```bash
# Convert a simple PDF to Markdown
python -m scripts.pdfmd_converter pdf_data/Test_Planning_Guide.pdf

# Convert a complex PDF to Markdown and ignore quality gate failure
python -m scripts.pdfmd_converter pdf_data/CTFL_-_V4.0_-_ES_-_PROGRAMA_DE_ESTUDIO_-_V001.01.pdf --ignore-quality-gate
```

### 5. Check the output

For CLI and UI the default output directory is `outputs`.
- A subdirectory is created for each run in the `outputs` directory.
- The subdirectory name is `run_YYYYMMDD_HHMMSS` where `YYYYMMDD_HHMMSS` is the timestamp of the run.
>If the output directory is set up differently by user preference, the new directory name will be displayed in the UI and in the terminal output of the CLI.

```bash
ls outputs/run_*/
```

Each run produces:

| File | Contents |
|---|---|
| `<source>.md` | The converted Markdown document |
| `validation.json` | Quality scores and findings from Stage 4 |
| `execution.json` | Runtime metadata (duration, engine version, timestamps) |
| `logs.txt` | Execution log for the entire pipeline run |
| `manifest.json` | Inventory of all artifacts in the run directory |

---

## Running the Tests

You must be inside the virtual environment to run the tests.
You can run tests while the application is running. To do that, run the application in one terminal and the tests in another.

**Test Architecture and Strategy details refer to [docs/test_architectural_decisions.md](docs/test_architectural_decisions.md)**

### Test Data

- A set of PDFs for different complexity levels: `pdf_data/` (for unit/integration tests).
- A synthetic dataset of failing PDFs for Negative test cases: `tests/ui/data/` (for UI E2E tests).

```bash
# All tests run inside the virtual environment. Activate it first.
source venv/bin/activate
# All tests (unit + integration + ui)
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# UI E2E tests only (Playwright headless)
# Include HTML reports for UI tests
pytest tests/ui/ -v
```
---

## Dependencies

```
PyMuPDF>=1.24.0       # PDF parsing and layout analysis (Stage 1 & 2)
markdown-it-py>=3.0.0 # Markdown parser acceptance check (Stage 4)
streamlit>=1.35.0     # Presentation layer (Stage 6)
plotly>=5.0.0         # Validation score visualization
pytest>=8.0.0         # Test runner
playwright            # Browser automation for E2E tests
pytest-playwright     # Pytest integration for Playwright
```

All runtime stages are LLM-free. No API keys, no cloud services, no external network requests are required.

### Resource Consumption

The app is designed to be highly efficient and extremely lightweight. Because one of its core architectural decisions was to be **LLM-free at runtime** and purely deterministic, its resource consumption is minimal. 

Here is a breakdown of the typical resource footprint you can expect when running this application locally:

### 1. Memory (RAM)
* **Base Usage:** The Streamlit server (`python -m streamlit run`) typically idles at around **100 MB to 150 MB** of RAM.
<details><summary>Memory Usage Details</summary>
* **During Processing:** PyMuPDF loads the document into memory during extraction. Because the system has a hard limit rejecting files larger than **10 MB**, the memory spike is tightly capped. Even during heavy extraction of a maximum-sized PDF, the peak memory usage rarely exceeds **200 MB to 300 MB**. 
* **Total Expected Memory:** You can run this comfortably on a machine with just 4GB to 8GB of RAM.
</details>

### 2. Processing Power (CPU)
* **Idle:** 0% CPU usage.
<details><summary>CPU Usage Details</summary>
* **During Conversion:** Processing is fast and relies entirely on deterministic algorithms (calculating font sizes, identifying table geometries). Converting a complex 50-page PDF usually takes less than **1 to 2 seconds**. It will briefly use a single CPU core to 100% during that one second, and then return to 0%.
* **GPU Requirement:** **Zero.** No GPU or Neural Processing Unit (NPU) is required because there is no Machine Learning model or LLM running inference locally.
</details>

### 3. Disk Space
* **Installation:** The Python environment and its dependencies (`PyMuPDF`, `streamlit`, `markdown-it-py`, and test packages like `playwright`) consume roughly **200 MB to 500 MB** of disk space (Playwright browsers take up the bulk of this if you run the E2E tests).
<details><summary>Disk Space Usage Details</summary>
* **Storage Growth:** The output artifacts are tiny text files. A generated Markdown file and its accompanying JSON reports usually combine to less than **500 KB** per run. 
</details>

<details><summary>Network Bandwidth</summary>
* **Zero.** Once the Python libraries are installed, the application is **100% local-first**. It does not phone home, it does not send your PDFs to a cloud server, and it does not use API calls to external services.
</details>

### Summary
You can comfortably run this application in the background on almost any modern hardware (including standard business laptops or small Raspberry Pi / Docker containers) without noticing any impact on your system's performance!

---

## Limitations of the Current Version

| Limitation | Details |
|---|---|
| **Single PDF per run** | Batch processing is not yet supported |
| **No OCR** | Scanned or image-only PDFs are rejected |
| **No image extraction** | Images are not embedded in the Markdown output |
| **No diagram reconstruction** | Complex diagrams produce a placeholder string |
| **No URL preservation** | All URLs removed by the security gate |
| **No hyperlink preservation** | All hyperlinks removed by the security gate |
| **English-optimized extraction** | Non-Latin character sets may have reduced fidelity |
| **No streaming output** | The full pipeline runs synchronously before writing any output |

---

## Contributing

Contributions are welcome. Please read the architecture constraints and decisions in the `docs/` directory and [GOVERNACE_CONTRIBUTING.md](GOVERNACE_CONTRIBUTING.md) before opening a pull request.

Key rules for contributors:

- Core domain (`src/core/`) must have **zero external library imports**
- Every external dependency must be isolated in an adapter (`src/adapters/`)
- New libraries require explicit approval — add to `requirements.txt` only after discussion
- Every new module requires unit tests in `tests/unit/` and integration tests in `tests/integration/`
- All tests must pass before a PR is merged

---

## License

Copyright 2026 Leticia Perez Gainza
Licensed under the Apache License 2.0. 

See [LICENSE](LICENSE) for details.

