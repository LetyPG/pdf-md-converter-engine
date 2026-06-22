import re
from typing import List, Tuple

from src.core.models.extraction import IntermediateDocumentModel
from src.core.models.validation import Finding, FindingCategory, FindingSeverity

_URL_PATTERN = re.compile(r"https?://", re.IGNORECASE)
_HYPERLINK_PATTERN = re.compile(r"\[[^\]]*\]\([^)]*\)")
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_HTML_PATTERN = re.compile(r"<[^>]+>")
_IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\(")


class SecurityValidator:
    """Validates that all security gate rules were enforced in the Markdown output.

    Runs 5 binary checks (each worth 20 points):
    1. URL removal     — no https?:// present
    2. Hyperlink removal — no [text](url) constructs
    3. Email removal   — no user@domain.com present
    4. HTML removal    — no <tag> present
    5. Image removal   — no ![alt](url) present

    Any violation causes security_score < 100 → artifact FAILS.
    Uses re only — no external library.
    """

    def validate(
        self, idm: IntermediateDocumentModel, markdown_content: str
    ) -> Tuple[float, List[Finding]]:
        """Runs all security checks.

        Returns:
            (score 0–100, findings list)
        """
        findings: List[Finding] = []
        passed = 0
        total = 5

        checks = [
            (_URL_PATTERN,       "URL detected in Markdown output."),
            (_HYPERLINK_PATTERN, "Markdown hyperlink detected in output."),
            (_EMAIL_PATTERN,     "Email address detected in Markdown output."),
            (_HTML_PATTERN,      "Raw HTML tag detected in Markdown output."),
            (_IMAGE_PATTERN,     "Markdown image syntax detected in output."),
        ]

        for pattern, message in checks:
            match = pattern.search(markdown_content)
            if match is None:
                passed += 1
            else:
                findings.append(Finding(
                    severity=FindingSeverity.ERROR,
                    category=FindingCategory.SECURITY,
                    message=message,
                    location=f"near: {repr(markdown_content[max(0, match.start()-10):match.end()+10])}",
                ))

        score = round((passed / total) * 100.0, 2)
        return score, findings
