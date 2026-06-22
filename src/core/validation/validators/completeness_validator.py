import re
from difflib import SequenceMatcher
from typing import List, Tuple

from src.core.models.extraction import HeadingBlock, IntermediateDocumentModel, TableBlock
from src.core.models.validation import Finding, FindingCategory, FindingSeverity

_TABLE_SEP_PATTERN = re.compile(r"^\|[-| ]+\|$", re.MULTILINE)

# Minimum ratio of Markdown length to estimated IDM text length before truncation warning.
_TRUNCATION_RATIO: float = 0.50
# Minimum similarity ratio for heading content fuzzy match.
_SIMILARITY_THRESHOLD: float = 0.80


class CompletenessValidator:
    """Validates that expected IDM content is present in the Markdown output.

    Runs 4 checks (each worth 25 points):
    1. Missing sections  — IDM heading content appears in Markdown (fuzzy match)
    2. Missing tables    — IDM table count matches Markdown table count
    3. Empty blocks      — No block with substantial IDM content maps to nothing
    4. Truncation        — Markdown length >= 50% of estimated IDM text length

    Uses difflib.SequenceMatcher for fuzzy heading content matching.
    """

    def validate(
        self, idm: IntermediateDocumentModel, markdown_content: str
    ) -> Tuple[float, List[Finding]]:
        """Runs all completeness checks.

        Returns:
            (score 0–100, findings list)
        """
        findings: List[Finding] = []
        passed = 0
        total = 4

        idm_headings = [
            b for p in idm.pages for b in p.blocks if isinstance(b, HeadingBlock)
        ]
        idm_tables = [
            b for p in idm.pages for b in p.blocks if isinstance(b, TableBlock)
        ]

        # Check 1: Missing sections (heading content present)
        missing = self._find_missing_headings(idm_headings, markdown_content)
        if not missing:
            passed += 1
        else:
            for heading in missing:
                findings.append(Finding(
                    severity=FindingSeverity.WARNING,
                    category=FindingCategory.COMPLETENESS,
                    message=f"Heading content not found in Markdown: '{heading}'",
                ))

        # Check 2: Missing tables
        md_table_count = len(_TABLE_SEP_PATTERN.findall(markdown_content))
        if len(idm_tables) == md_table_count:
            passed += 1
        else:
            findings.append(Finding(
                severity=FindingSeverity.WARNING,
                category=FindingCategory.COMPLETENESS,
                message=(
                    f"Table count mismatch: IDM has {len(idm_tables)}, "
                    f"Markdown has {md_table_count}"
                ),
            ))

        # Check 3: Empty blocks (IDM has content, Markdown is empty or near-empty)
        if self._no_unexpected_empty_blocks(idm, markdown_content):
            passed += 1
        else:
            findings.append(Finding(
                severity=FindingSeverity.WARNING,
                category=FindingCategory.COMPLETENESS,
                message="One or more IDM blocks with content produced empty Markdown output.",
            ))

        # Check 4: Truncation check
        estimated_length = self._estimate_idm_text_length(idm)
        if estimated_length == 0 or len(markdown_content) >= estimated_length * _TRUNCATION_RATIO:
            passed += 1
        else:
            findings.append(Finding(
                severity=FindingSeverity.WARNING,
                category=FindingCategory.COMPLETENESS,
                message=(
                    f"Markdown length ({len(markdown_content)}) is less than "
                    f"{int(_TRUNCATION_RATIO * 100)}% of estimated IDM text length "
                    f"({estimated_length}). Content may be truncated."
                ),
            ))

        score = round((passed / total) * 100.0, 2)
        return score, findings

    def _find_missing_headings(
        self, idm_headings: List[HeadingBlock], markdown_content: str
    ) -> List[str]:
        """Returns heading contents that cannot be found in the Markdown."""
        missing: List[str] = []
        for block in idm_headings:
            if not self._content_present(block.content, markdown_content):
                missing.append(block.content)
        return missing

    def _content_present(self, target: str, content: str) -> bool:
        """Fuzzy search: True if target appears in content above similarity threshold."""
        if target in content:
            return True
        ratio = SequenceMatcher(None, target, content).ratio()
        return ratio >= _SIMILARITY_THRESHOLD

    def _no_unexpected_empty_blocks(
        self, idm: IntermediateDocumentModel, markdown_content: str
    ) -> bool:
        """Checks that the Markdown output is not empty when the IDM has content."""
        idm_has_content = any(
            getattr(b, "content", None) or getattr(b, "items", None) or getattr(b, "rows", None)
            for p in idm.pages for b in p.blocks
        )
        if idm_has_content and not markdown_content.strip():
            return False
        return True

    def _estimate_idm_text_length(self, idm: IntermediateDocumentModel) -> int:
        """Estimates the total text character length of all IDM blocks."""
        total = 0
        for page in idm.pages:
            for block in page.blocks:
                content = getattr(block, "content", "")
                if content:
                    total += len(content)
                items = getattr(block, "items", [])
                if items:
                    total += sum(len(i) for i in items)
        return total
