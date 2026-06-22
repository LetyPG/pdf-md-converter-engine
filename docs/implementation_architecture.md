# Purpose

Define the implementation architecture constraints that contributors and implementation agents SHALL follow when building the runtime engine.

This document constrains code organization while allowing implementation flexibility.

## Architectural Style
The runtime SHALL follow a Pipeline Architecture:
```txt
Preprocessor
↓
Extraction Engine
↓
Markdown Generator
↓
Quality Validator
↓
Output Manager
```
Each stage SHALL operate independently and communicate only through defined contracts.

---
## Implementation Directory Structure

## Project Structure

```
pdf-to-md-engine-converter/
│
├── src/
│   ├── core/                   ← Business logic (no external library imports)
│   │   ├── models/             ← Typed data contracts between stages
│   │   ├── preprocessor/       ← Stage 1: PDF validation and profiling
│   │   ├── extraction/         ← Stage 2: IDM construction
│   │   ├── markdown/           ← Stage 3: Markdown rendering
│   │   ├── validation/         ← Stage 4: Quality scoring
│   │   └── output/             ← Stage 5: Artifact persistence
│   │
│   ├── adapters/               ← External library wrappers
│   │   ├── pdf/                ← PyMuPDF adapter
│   │   ├── markdown/           ← markdown-it-py adapter
│   │   └── filesystem/         ← pathlib adapter
│   │
│   └── shared/                 ← Cross-cutting utilities
│       ├── exceptions/
│       ├── logging/
│       └── utils/
│
├── scripts/
│   └── pdfmd_converter.py      ← Pipeline entry point for CLI
├── ui/                         ← Stage 6: Streamlit presentation layer
│   ├── assets/
│   ├── components/
│   ├── pages/
│   ├── services/
│   └── app.py    
│
├── tests/
│   ├── unit/
│   │   └── core/               ← Isolated tests per stage
│   ├── integration/            ← Cross-stage and filesystem tests
│   ├── ui/                     ← UI E2E tests
│   └── utils/                  ← Synthetic Data Generator (negative and non functional requirements)
│
├── pdf_data/                   ← Sample PDFs for local testing
├── outputs/                    ← Generated artifacts (git-ignored)
├── requirements.txt
├── pytest.ini                  ← Pytest configuration
├── .gitignore
└── README.md
```
---
## Core Principles
* Separation of concerns* 
* Deterministic execution.
* Local-first execution.
* Framework independence.
* Testability.
* Replaceable adapters.
* Explicit contracts.
---
## Layering Rules
### Core Domain
The core domain SHALL contain business logic.
The core SHALL NOT depend on:

* CLI frameworks;
* UI frameworks;
* filesystem implementations;
* PDF libraries;
* Markdown libraries.
---
### Adapters
Adapters SHALL isolate external dependencies.
Examples:
* PyMuPDF;
* Marker;
* markdown-it-py;
* filesystem access.

Adapters MAY be replaced without changing the core domain.
---
### Interfaces
Interfaces SHALL expose the system externally.
Examples:
* CLI;
* optional UI;
* future APIs.
Interfaces SHALL orchestrate execution only.

---
## Communication Contracts
Pipeline stages SHALL exchange typed models.
Stages SHALL NOT exchange untyped dictionaries as their primary contract.

---
## Dependency Rules
**Allowed direction:**
Interfaces → Core → Adapters
**Forbidden dependencies:**
* Core → Interfaces
* Core → Frameworks
* Markdown Generator → PDF adapters
* Output Manager → Extraction Engine internals
---
## Error Handling
The system SHALL distinguish:
* Fatal errors;
* Recoverable warnings;
* Validation findings.
Warnings SHALL propagate through the pipeline.
Fatal errors SHALL terminate execution gracefully.

---
## Testing Strategy
Each pipeline stage SHALL support:
* Unit tests;
* Golden dataset tests.
Cross-stage execution SHALL support:
* Integration tests;
* End-to-end tests.
---

## Recommended Patterns
**Mandatory:** Pipeline Pattern.
**Recommended:** Adapter Pattern; Strategy Pattern.
**Discouraged:** 
* Global state;
* Service locators;
* Dependency injection containers;
* Event buses;
* Overengineered abstractions.
---
## Coding principles
* SOLID were applied, example:
   * Single Responsibility Principle (SRP): Class `Preprocessor` is responsible for preprocessing the PDF file.
   * Open/Closed Principle (OCP): Class `MarkdownGenerator` can be extended to support new Markdown formats without modifying the class.
   * Liskov Substitution Principle (LSP): Class `PdfProvider` can be replaced with any other `PdfProvider` implementation without affecting the core domain.
   * Interface Segregation Principle (ISP): Class `MarkdownParserProtocol` can be replaced with any other `MarkdownParser` implementation without affecting the core domain.
   * Dependency Inversion Principle (DIP): Class `Preprocessor` depends on the `PdfProvider` interface, not on the concrete implementation of the `PdfProvider` class.

* Keep it simple, stupid (KISS): Example Class `ValidationRunner` is responsible for running validations on the generated Markdown.
* Don't repeat yourself (DRY): Examples:
   * **Core Domain:** The `MarkdownGenerator` avoids repeating massive `if/elif` chains by using the Strategy Pattern. It maps `BlockType` enums directly to `BlockRenderer` implementations, meaning the Intermediate Document Model traversal logic is written exactly once.
   * **Testing Framework:** In `tests/ui/test_nfr_negative_suite.py`, the Playwright UI upload and assertion logic is written exactly once. Distinct negative scenarios (oversized files, invalid extensions, corrupted PDFs) are injected dynamically via `@pytest.mark.parametrize` and the `FileFactory` strategy pattern, eliminating dozens of lines of duplicated UI automation code.

## Code Conventions
* Language: Python 3.10+
* Type hinting: MANDATORY
* Naming:
    * snake_case for functions and variables
    * CamelCase for classes
    * UPPER_CASE for constants
    * Kebab-case for packages (dist/ only)
    * snake_case for files
    * Kebab-case for directories
* Docstrings: MANDATORY
* Tests: MANDATORY
   * Add try and catch block for unhandled errors.
   * Test names camel_case
   * for unittest refrence the specific module, for integration test, indicate the  modules involved in the test, for end-to-end test, indicate the aceptance criteria which is been evaluated.  
   * Each module MUST have tests in tests/unit/test_*.py
   * Integration tests SHALL be located in tests/integration/test_*_integration.py
   * golden/ contains ground truth for regression testing

---
## Extensibility Rules
New capabilities SHALL integrate through adapters or new pipeline stages.
Existing contracts SHALL remain backward compatible whenever possible.
Scope expansion SHALL NOT violate established ADRs.

---
## The Implementation Architecture Document as AI Coding Standards

**File:** `docs/implementation_architecture.md`

While specs define *what* stages must do, the implementation architecture defines *how the code must be organized*. This document was provided to the agent as its coding standard — read once at the start and referenced throughout.

### Core layering rule

```
Interfaces → Core → Adapters
```

The core domain may never import from adapters. Adapters may never be imported by the core directly — only through Protocols (Python structural typing).

**In practice this means:**
- `src/core/extraction/extraction_engine.py` imports `PdfExtractionProvider` (a Protocol defined in core)
- `src/adapters/pdf/pymupdf_extraction_provider.py` implements that Protocol
- The core never imports `fitz` (PyMuPDF) — only the adapter does

The same pattern appears in Stage 4's `RenderingValidator`: it receives a `MarkdownParserProtocol`, not a `MarkdownValidatorAdapter` — keeping `markdown-it-py` isolated to the adapter layer.

### Dependency inversion in practice

Every external library is behind an adapter:

| External Library | Adapter | Protocol in Core |
|---|---|---|
| `PyMuPDF` (fitz) | `PyMuPdfProvider` | `PdfProvider` |
| `PyMuPDF` (tables) | `PyMuPdfExtractionProvider` | `PdfExtractionProvider` |
| `markdown-it-py` | `MarkdownValidatorAdapter` | `MarkdownParserProtocol` |
| `pathlib` (OS) | `LocalFilesystemWriter` | `FilesystemWriter` |

This means every core component can be tested without any external library — using mock implementations of the Protocols.

### Mandatory patterns

The architecture document declared three patterns as required:

1. **Pipeline Pattern** — enforced by the linear `scripts/pdfmd_converter.py` runner
2. **Adapter Pattern** — enforced at every external dependency boundary
3. **Strategy Pattern** — used in Stage 3's `BlockRenderer` registry and Stage 4's `CategoryValidator` injections

---

## How the Agent Used These Documents

The agent's workflow for each pipeline stage followed a consistent sequence:

```
1. Read the component spec (WHAT it must do)
2. Read the implementation architecture (HOW the code must be structured)
3. Read the ADRs (WHAT cannot change)
4. Identify open design questions → propose alternatives to the user
5. Receive user decisions → proceed with the agreed approach
6. Implement in this order:
   a. Typed model (src/core/models/)
   b. Protocol(s) (src/core/)
   c. Core logic (src/core/<stage>/)
   d. Adapter(s) (src/adapters/)
   e. Unit tests (tests/unit/core/)
   f. Integration tests (tests/integration/)
7. Run tests in venv: venv/bin/python -m pytest tests/ -v
8. Fix failures — never adjust tests to pass; adjust implementation
```

### Design question resolution examples

Before coding each stage, the agent surfaced ambiguous decisions and presented the alternatives with a recommended choice grounded in the existing implementation context:

- **Heading detection:** fixed thresholds vs. adaptive (relative to page median) → **fixed thresholds** chosen for determinism (ADR-001)
- **Table detection:** custom regex vs. `page.find_tables()` from PyMuPDF → **PyMuPDF native** chosen for reliability
- **Golden datasets:** real PDFs vs. synthetic PDFs → **synthetic PDFs** chosen for reproducibility and version-control compatibility

