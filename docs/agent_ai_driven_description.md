# AI-Native Development: 
## How `pdf-to-md-engine-converter` Was Built

> **Document type:** Engineering narrative  
> **Audience:** Engineers, AI practitioners, and contributors interested in AI-native software development methodology  
> **Location:** `docs/agent_ai_driven_description.md`

---

## Introduction

`pdf-to-md-engine-converter` was built using an **AI-native development methodology** — a structured approach where an AI coding agent (Antigravity, powered by Google DeepMind) acts as the primary implementer, guided by a layered set of human-authored documents instead of informal verbal instructions.

Rather than asking an AI to "write code" and then reviewing the output, this methodology inverts the workflow: humans define intent, constraints, and decisions through structured documents first. The agent reads those documents as its primary source of truth and implements against them — producing code, tests, and architecture that is traceable back to a deliberate design.

This document explains how that process worked: what documents were created, what decisions they encode, how the agent interpreted them, and how the resulting implementation reflects those decisions.

---

## The Three-Layer Knowledge Architecture

The project's `agent-ai-driven/` directory contains the totality of the agent's operational context. It is organized into three layers, each with a distinct purpose and stability level:

```
agent-ai-driven/
├── specs/          ← WHAT each component must do
│   ├── system-spec.md
│   ├── preprocesor-spec.md
│   ├── extraction-engine-spec.md
│   ├── markdwon-generator-spec.md
│   ├── quality-validator-spec.md
│   ├── output-manager-spec.md
│   └── schemas/
│       └── output_md_schema.md
└── context/        ← WHY the system exists and HOW decisions must be made
    ├── product-context.md
    ├── user-scenarios.md
    └── architecture-decisions.md
```

| Layer | Document | Stability | Purpose for the Agent |
|---|---|---|---|
| **Context** | `product-context.md` | Very High | Why the product exists; non-negotiable boundaries |
| **Context** | `architecture-decisions.md` | High | Decisions that define the identity of the system |
| **Context** | `user-scenarios.md` | Medium-High | Behavioral expectations from the user's point of view |
| **Specs** | `system-spec.md` | Medium | Global constraints and technology stack |
| **Specs** | `*-spec.md` (×5) | Medium | Per-component behavioral contracts |

A fourth layer exists in `docs/`:

| Layer | Document | Purpose |
|---|---|---|
| **Architecture** | `implementation_architecture.md` | HOW the code must be structured |

---

## Layer 1 — Product Context: Why the System Exists

**File:** `agent-ai-driven/context/product-context.md`

This was the first document the agent read. Its role is to prevent the most common failure mode of AI-generated code: building something technically correct but fundamentally misaligned with the product's purpose.

### What it defines

The product context establishes that this system is a **lightweight local knowledge preparation tool** — not a cloud service, not an AI system, not a summarizer. Its position in the value chain is explicit:

```
PDF → Markdown Asset → Human / RAG / Agent
```

The converter's responsibility ends at producing trustworthy Markdown. Everything after (chunking, embedding, retrieval, summarization) belongs to downstream systems.

### Core principles encoded

```yaml
local_first: true
privacy_preserving: true
deterministic: true
open_source: true
llm_free_runtime: true
human_inspectable_outputs: true
```

### How it constrained the agent

These principles directly prevented certain implementation choices:

- The agent never proposed using an LLM to parse or enhance Markdown
- The agent never proposed external API calls
- The agent ensured every stage produces output that can be read and audited by a human
- When the user asked about optional features, the agent applied the scope boundary defined here to assess whether a feature belonged in this system

---

## Layer 2 — Architecture Decisions: What Cannot Change

**File:** `agent-ai-driven/context/architecture-decisions.md`

Architecture Decision Records (ADRs) are the system's long-term memory. They record not just what was decided, but why — so that future contributors (human or agent) cannot silently reverse a decision that was deliberately made.

Nine ADRs were defined before implementation began:

| ADR | Decision | Reason |
|---|---|---|
| **ADR-001** | No Runtime LLMs | Determinism, privacy, reproducibility, latency |
| **ADR-002** | Human-readable Markdown | Artifacts must be inspectable and version-controllable |
| **ADR-003** | CLI-first interfaces | Enables automation and scripting |
| **ADR-004** | Embeddable Python package | Users embed the tool in their own agent projects |
| **ADR-005** | Local-first execution | Sensitive documents must never leave the user's machine |
| **ADR-006** | Independently testable stages | Each stage must evolve and be verified in isolation |
| **ADR-007** | Intermediate Document Model (IDM) | Decouples extraction from rendering |
| **ADR-008** | Converter scope boundary | Prevents scope creep into chunking, embedding, retrieval |
| **ADR-009** | Linear pipeline architecture | Sequential, deterministic stages with explicit boundaries |

### How ADRs constrained implementation

**ADR-001 (No LLMs)** was the most operationally significant. Every spec for every stage includes the constraint `invoke_llms: false`. When implementing the Extraction Engine (Stage 2), the agent used font-size heuristics and PyMuPDF's native table detection — not model inference — to classify blocks.

**ADR-007 (IDM)** determined one of the most visible architectural choices: all data from the Extraction Engine flows through a typed `IntermediateDocumentModel` before reaching the Markdown Generator. This model became the canonical source of truth for Stage 4 (Quality Validator), allowing it to independently score the output without re-reading the PDF.

**ADR-009 (Pipeline)** is visible in the structure of `src/core/`: each stage has its own module (`preprocessor/`, `extraction/`, `markdown/`, `validation/`, `output/`), each communicating only through typed models (`PreprocessingResult` → `IntermediateDocumentModel` → `MarkdownResult` → `ValidationReport` → `OutputResult`).

**ADR-008 (Scope boundary)** prevented the agent from adding convenience features like automatic chunking or embedding in the Output Manager, even though these would be technically straightforward to implement.

---

## Layer 3 — User Scenarios: Behavioral Expectations

**File:** `agent-ai-driven/context/user-scenarios.md`

Six user scenarios were written in Gherkin-style acceptance criteria format:

| Scenario | Core behavior validated |
|---|---|
| **US-001** | CLI conversion of a valid PDF → Markdown + validation report |
| **US-002** | RAG-ready Markdown preserving headings, lists, tables |
| **US-003** | Agent knowledge assets with security gates enforced |
| **US-004** | Programmatic (library) invocation with warning propagation |
| **US-005** | Multi-column reading order reconstruction |
| **US-006** | URL, hyperlink, email, HTML, and image syntax removal |
| **US-007** | User Validation Override by preference |

### How scenarios shaped implementation

**US-006 (Security gates)** drove one of the most deliberate design choices: the security gate is applied **twice** in the pipeline:

1. **Stage 2 (Extraction Engine):** unsafe content is stripped before the IDM is assembled
2. **Stage 3 (Markdown Generator):** a second pass is applied to the final assembled Markdown string

This dual-layer design emerged from the scenario's requirement: unsafe references must be absent from the final artifact regardless of how they entered the extraction phase.

**US-004 (Library invocation)** ensured the pipeline runner was designed so that `run_pipeline()` is a callable function returning exit codes, not a script that terminates the process mid-execution. Warnings do not raise exceptions; they propagate through the pipeline as structured data on each stage's output model.

---

## Layer 4 — Component Specifications: What Each Stage Must Do

**Directory:** `agent-ai-driven/specs/`

Each pipeline stage has its own specification. These are the documents the agent read immediately before implementing each component — they define what the stage must do, what it must not do, its input/output contracts, its scoring or validation logic, its failure rules, and its allowed technology stack.

### `system-spec.md` — Global constraints

Established the boundaries that apply across all stages:
- Supported PDF types (native text, up to 10 MB)
- Unsupported scenarios (scanned images, password-protected, >10 MB)
- Technology stack (`PyMuPDF`, `markdown-it-py`, `pytest`)
- Stack restriction rule: new libraries require explicit user approval before being added to `requirements.txt`

This last rule was enforced in practice: when Stage 4 required `markdown-it-py`, the agent identified it, presented the request to the user, and waited for approval before modifying `requirements.txt` or installing the library.

### `preprocesor-spec.md` — Stage 1

Defined a validation-and-profiling stage with five rejection reasons (`FILE_NOT_FOUND`, `FILE_UNSUPPORTED`, `FILE_TOO_LARGE`, `PASSWORD_PROTECTED`, `FILE_CORRUPTED`) and a `DocumentProfile` output containing layout type, orientation, page count, and element counts.

**Key decision in the spec:** layout detection uses fixed thresholds (column gap heuristics via PyMuPDF) rather than ML-based classification — preserving determinism per ADR-001.

### `extraction-engine-spec.md` — Stage 2

Defined three extraction strategies (`NATIVE_TEXT`, `MULTI_COLUMN`, `MIXED_LAYOUT`) selected based on the `DocumentProfile` from Stage 1. Table detection uses `page.find_tables()` from PyMuPDF rather than regex or ML.

**Key decision in the spec:** heading level classification uses fixed font-size thresholds:
- H1: font size ≥ 18pt
- H2: font size ≥ 14pt  
- H3: font size ≥ 12pt

This choice was made explicitly over a relative/adaptive approach — a simpler, more deterministic, and more predictable threshold system.

### `markdwon-generator-spec.md` — Stage 3

Specified the Strategy Pattern for block rendering: each `BlockType` maps to a dedicated `BlockRenderer` class (`HeadingRenderer`, `ParagraphRenderer`, `ListRenderer`, `TableRenderer`, `CodeBlockRenderer`, `FigureRenderer`, `DiagramRenderer`, `QuoteRenderer`).

The spec also defined exact rendering rules via `schemas/output_md_schema.md`:
- GFM pipe tables with `|---|` separator rows
- Fenced code blocks with language tags
- Figure/diagram placeholders instead of image embedding
- Exactly one blank line (`\n\n`) between blocks
- Unix line endings, no trailing whitespace

**The agent used the schema document as a precise rendering contract**, building one test per rendering rule to verify compliance deterministically.

### `quality-validator-spec.md` — Stage 4

Defined four validation dimensions with a weighted scoring formula:

```
Overall = (Structural × 0.35) + (Rendering × 0.25) + (Security × 0.25) + (Completeness × 0.15)
```

And two hard failure rules:
- `rendering_score < 100` → artifact fails
- `security_score < 100` → artifact fails

These failure rules became the `passed` field on `ValidationReport` and were enforced by the `QualityValidator` orchestrator, not by individual sub-validators — keeping failure logic centralized.

### `output-manager-spec.md` — Stage 5

Defined the deterministic directory structure, naming convention (`run_YYYYMMDD_HHMMSS` in UTC), collision handling (`_001`–`_999` suffix), and the requirement to write `manifest.json` last — after all other artifacts are verified to exist.

**A subtle detail driven by the spec:** the manifest must list itself in its `artifacts` array. This required pre-adding `"manifest.json"` to the filename list before serializing the manifest JSON.

---

## Test Results at Completion

Every stage's implementation was verified with a dedicated test suite before the next stage began:

| Stage | Unit Tests | Integration & E2E | Pass Rate |
|---|---|---|---|
| Stage 1 — Preprocessor | 6 | 3 | 100% |
| Stage 2 — Extraction Engine | 19 | 6 | 100% |
| Stage 3 — Markdown Generator | 25 | 7 | 100% |
| Stage 4 — Quality Validator | 23 | 6 | 100% |
| Stage 5 — Output Manager | 15 | 7 | 100% |
| Stage 6 — User Interface | 0 | 16 | 100% |
| **Total** | **88** | **45** | **133/133 — 100%** |

---

## End-to-End Validation

The complete pipeline was verified against two real PDFs from `pdf_data/`:

| PDF | Overall Score | Passed |
|---|---|---|
| `Test_Planning_Guide.pdf` | 100.0 | ✅ |
| `CTFL_-_V4.0_-_ES_-_PROGRAMA_DE_ESTUDIO_-_V001.01.pdf` | 89.2 | ✅ |

Both runs produced all five artifacts in isolated run directories:

```
outputs/
├── run_YYYYMMDD_HHMMSS/
│   ├── <source>.md
│   ├── validation.json
│   ├── execution.json
│   ├── logs.txt
│   └── manifest.json
```
---

## Key Takeaways on the AI-Native Approach

### What made it effective

1. **Specs as contracts, not instructions.** The agent was never told "write a function that does X." It was told "this component SHALL do X and SHALL NOT do Y" — a behavioral contract that left the implementation mechanism to the agent while binding it to the outcome.

2. **ADRs as invariants.** By encoding decisions with their rationale, the ADRs allowed the agent to apply them to new situations autonomously. When Stage 4 required a library that could have been imported in the core, the agent correctly identified the violation and isolated it to an adapter — not because it was told to, but because it had internalized the layering rule.

3. **Layered context prevents drift.** Without product context and ADRs, an AI agent optimizes for technical elegance, not product identity. The context layer was what prevented the agent from suggesting "helpful" features like auto-chunking or embedding.

4. **Spec-first test derivation.** Tests were not written to cover code; they were derived from spec requirements. Each spec section with a `SHALL` statement became at least one test case.

### What this approach requires from humans

- Deliberate upfront authoring of context and decision documents
- Explicit scope boundaries (what the system is NOT)
- Approval gates for infrastructure changes (e.g. new dependencies)
- Review of the agent's proposed design questions before implementation begins
