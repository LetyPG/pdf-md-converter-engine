# Pull Request Template

## Type of Change

* [ ] Bug fix (non-breaking change that fixes an issue)
* [ ] New feature (non-breaking change that adds functionality)
* [ ] Refactor / QA Automation (test improvements, automation, or infrastructure changes)
* [ ] Documentation update
* [ ] Performance improvement
* [ ] Security improvement
* [ ] Breaking change

---

## Description

Provide a brief summary of the change and its purpose.

Related Issue:

Fixes #

---

## Validation Evidence

Describe how the change was verified.

Examples:

* Unit tests
* Integration tests
* Manual verification
* Local execution
* Screenshots

---

## Quality Checklist

### Code Quality

* [ ] My code follows the project's coding standards.
* [ ] I reviewed my own code before submitting.
* [ ] I removed unused code, imports, and dependencies.

### PDF-to-MD Specific Validation

- [ ] Markdown generation was validated.
- [ ] Artifact validation passes successfully.
- [ ] No data loss was identified during conversion.
- [ ] Processing remains local-first.
- [ ] Output remains AI-friendly and token-efficient.

### Testing

* [ ] I executed the test suite locally and all tests passed.
* [ ] I added or updated tests covering my changes.
* [ ] Existing tests continue to pass.

### Documentation

* [ ] I updated documentation when necessary.
* [ ] User-facing behavior changes are documented.

### Architecture

* [ ] This change respects the project's architectural principles.
* [ ] No mandatory cloud dependency was introduced.
* [ ] No runtime LLM dependency was introduced.
* [ ] Deterministic execution behavior has been preserved.

### Security

* [ ] The change does not introduce known security risks.
* [ ] Any new dependency was evaluated for necessity and security impact.

---

## Screenshots (Optional)

Attach screenshots if the change affects the UI.

---

## Additional Notes

Include any relevant information for reviewers.
