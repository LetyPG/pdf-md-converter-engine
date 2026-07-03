# Governance & Contributing Guide

Welcome to PDF-to-MD Converter.

This document defines how the project is governed, how contributions are reviewed, the expected standards of conduct, and the security principles that guide development.

The goal is to maintain a collaborative, professional, and sustainable open-source project focused on transforming structured PDF documents into AI-optimized Markdown artifacts for local AI workflows.

---

# Project Mission

PDF-to-MD Converter exists to provide a lightweight, deterministic, and local-first solution for converting structured PDF reference documents into Markdown suitable for AI-assisted development, agent workflows, and knowledge preparation.

The project prioritizes:

* Simplicity
* Deterministic execution
* Local-first operation
* Security-conscious processing
* AI-friendly outputs
* Maintainable architecture

---

# Governance Model

The project follows a Maintainer-Led Governance model.

Maintainers are responsible for:

* Reviewing pull requests
* Managing releases
* Approving architectural changes
* Maintaining project documentation
* Ensuring alignment with project principles

Contributors are encouraged to propose improvements, but acceptance is based on technical merit, maintainability, project scope, and architectural consistency.

---

# Architectural Principles

All contributions should respect the following principles.

## Local First

The project must operate without requiring cloud services.

Contributions introducing mandatory external infrastructure may be rejected.

---

## Deterministic Processing

Given the same input, the system should produce predictable and reproducible outputs.

Non-deterministic behavior should be avoided whenever possible.

---

## Minimal Dependencies

Dependencies should be carefully evaluated.

Every new dependency increases:

* maintenance burden;
* security surface;
* installation complexity.

---

## No Runtime LLM Dependency

The project is designed as a document preparation utility.

Runtime execution must not depend on external LLM services.

---

## Security by Design

Document processing must prioritize safety and validation over convenience.

---

# How to Contribute

Contributions are welcome from:

* Developers
* QA Engineers
* Technical Writers
* Architects
* AI Practitioners
* Open Source Contributors

Examples include:

* Bug fixes
* Documentation improvements
* Test enhancements
* Validation improvements
* Performance optimizations
* Parser improvements
* New supported workflows

---

# Development Workflow

## 1. Fork the Repository

Create a personal fork of the project.

## 2. Create a Branch

**Branch Source**
As a branch source to create a new branch, use the branch `contribution`

Recommended naming conventions:

feature/<description>

bugfix/<description>

docs/<description>

Example:

feature/artifact-validator

---

## 3. Implement Changes

Keep changes focused.

Avoid mixing unrelated improvements in a single pull request.

---

## 4. Add Tests

New functionality should include tests whenever practical.

Bug fixes should include regression tests whenever possible.

---

## 5. Submit a Pull Request

Pull requests should include:

* Description of changes
* Motivation
* Testing evidence
* Documentation updates if required

---

# Pull Request Requirements

A pull request should:

* Build successfully
* Pass all automated tests
* Maintain existing functionality
* Include appropriate documentation
* Preserve deterministic execution
* Respect project architecture
* Avoid introducing security regressions

Maintainers may request revisions before approval.

---

# Architecture Changes

Major architectural changes should be discussed before implementation.

Examples include:

* New processing pipelines
* Changes to validation philosophy
* Changes to document models
* External service integrations
* Significant dependency additions

Maintainers may request an ADR (Architecture Decision Record) before approving such changes.

---

# Community Standards

All participants are expected to behave professionally and respectfully.

The project values:

* Constructive feedback
* Technical discussion
* Evidence-based decisions
* Collaborative problem solving

Disagreements are normal.

Personal attacks are not.

---

# Unacceptable Behavior

The following behaviors are not tolerated:

* Harassment
* Discrimination
* Personal attacks
* Threats
* Intimidation
* Trolling
* Offensive or abusive language
* Publishing private information without consent

Maintainers may remove content or restrict participation when necessary.

---

# Security Principles

The project processes potentially untrusted documents.

Security is therefore a core concern.

Contributors should follow secure development practices and consider the impact of every change on document processing safety.

---

# Security Expectations

Contributors should:

* Validate inputs
* Handle malformed files safely
* Avoid unsafe parsing techniques
* Minimize dependency risk
* Follow least-complexity solutions
* Preserve validation mechanisms

---

# Vulnerability Reporting

Please do not publicly disclose security vulnerabilities before maintainers have an opportunity to investigate.

Security reports should include:

* Affected version
* Reproduction steps
* Potential impact
* Supporting evidence

Maintainers will review reports and determine appropriate remediation.

---

# Supported Scope

This project is primarily intended for:

* Technical specifications
* Architecture documentation
* Requirements documents
* Standards
* Process documentation
* Knowledge base preparation

The project is not intended to be:

* A malware analysis platform
* An OCR platform
* A document forensics tool
* A universal PDF conversion engine

---

# Decision-Making Philosophy

When multiple solutions exist, preference should be given to the option that best preserves:

1. Simplicity
2. Determinism
3. Security
4. Maintainability
5. Local-first execution

Features that significantly increase complexity without proportional value may be rejected.

---

# Final Note

By contributing to this project, you agree to follow this guide, respect fellow contributors, and help maintain a secure, professional, and sustainable open-source project.

Thank you for contributing to PDF-to-MD Converter.
