import re
from typing import List, Tuple

from src.core.models.extraction import IntermediateDocumentModel
from src.core.models.validation import Finding, FindingCategory, FindingSeverity
from src.core.validation.category_validator import MarkdownParserProtocol

_TABLE_ROW_PATTERN = re.compile(r"^\|.+\|$", re.MULTILINE)
_TABLE_SEP_PATTERN = re.compile(r"^\|[-| ]+\|$", re.MULTILINE)
_CODE_FENCE_PATTERN = re.compile(r"^```", re.MULTILINE)
_TRAILING_WHITESPACE_PATTERN = re.compile(r"[ \t]+$", re.MULTILINE)


class RenderingValidator:
    """Validates Markdown syntax correctness.

    Runs 4 checks (each worth 25 points):
    1. Parser acceptance (via injected MarkdownParserProtocol)
    2. Formatting compliance (no trailing whitespace, unix line endings)
    3. Table validity (separator row + consistent column count)
    4. Code block validity (balanced fence markers)

    Any failed check causes rendering_score < 100 → artifact FAILS.
    """

    def __init__(self, parser: MarkdownParserProtocol) -> None:
        """Initialises with an injected Markdown parser.

        Args:
            parser: Any object satisfying MarkdownParserProtocol.
                    In production: MarkdownValidatorAdapter.
        """
        self._parser = parser

    def validate(
        self, idm: IntermediateDocumentModel, markdown_content: str
    ) -> Tuple[float, List[Finding]]:
        """Runs all rendering checks.

        Returns:
            (score 0–100, findings list)
        """
        findings: List[Finding] = []
        passed = 0
        total = 4

        # Check 1: Parser acceptance
        if self._parser.validate(markdown_content):
            passed += 1
        else:
            findings.append(Finding(
                severity=FindingSeverity.ERROR,
                category=FindingCategory.RENDERING,
                message="Markdown content failed parser acceptance check.",
            ))

        # Check 2: Formatting compliance
        has_trailing = bool(_TRAILING_WHITESPACE_PATTERN.search(markdown_content))
        has_crlf = "\r\n" in markdown_content or "\r" in markdown_content
        if not has_trailing and not has_crlf:
            passed += 1
        else:
            if has_trailing:
                findings.append(Finding(
                    severity=FindingSeverity.ERROR,
                    category=FindingCategory.RENDERING,
                    message="Markdown contains trailing whitespace on one or more lines.",
                ))
            if has_crlf:
                findings.append(Finding(
                    severity=FindingSeverity.ERROR,
                    category=FindingCategory.RENDERING,
                    message="Markdown contains non-Unix (CRLF/CR) line endings.",
                ))

        # Check 3: Table validity
        if self._tables_are_valid(markdown_content):
            passed += 1
        else:
            findings.append(Finding(
                severity=FindingSeverity.ERROR,
                category=FindingCategory.RENDERING,
                message="One or more tables have inconsistent column counts or missing separator rows.",
            ))

        # Check 4: Code block validity (balanced fences)
        fence_count = len(_CODE_FENCE_PATTERN.findall(markdown_content))
        if fence_count % 2 == 0:
            passed += 1
        else:
            findings.append(Finding(
                severity=FindingSeverity.ERROR,
                category=FindingCategory.RENDERING,
                message=f"Unbalanced code fence markers: {fence_count} found (expected even count).",
            ))

        score = round((passed / total) * 100.0, 2)
        return score, findings

    def _tables_are_valid(self, content: str) -> bool:
        """Validates that each table has a separator row and consistent column counts."""
        lines = content.split("\n")
        table_lines: List[str] = []
        in_table = False

        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                table_lines.append(stripped)
                in_table = True
            else:
                if in_table and table_lines:
                    if not self._validate_table_block(table_lines):
                        return False
                    table_lines = []
                in_table = False

        if in_table and table_lines:
            if not self._validate_table_block(table_lines):
                return False

        return True

    def _validate_table_block(self, table_lines: List[str]) -> bool:
        """Validates a single table: needs separator row + consistent column count."""
        if len(table_lines) < 2:
            return False

        col_count = table_lines[0].count("|") - 1
        has_separator = False

        for line in table_lines[1:]:
            if re.match(r"^\|[-| ]+\|$", line):
                has_separator = True
            if line.count("|") - 1 != col_count:
                return False

        return has_separator
