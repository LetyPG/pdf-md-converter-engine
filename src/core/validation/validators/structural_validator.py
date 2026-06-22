import re
from typing import List, Tuple

from src.core.models.extraction import HeadingBlock, IntermediateDocumentModel, ListBlock, TableBlock
from src.core.models.validation import Finding, FindingCategory, FindingSeverity

_HEADING_PATTERN = re.compile(r"^#{1,6}\s", re.MULTILINE)
_LIST_ITEM_PATTERN = re.compile(r"^(?:- |\d+\. )", re.MULTILINE)
_TABLE_SEP_PATTERN = re.compile(r"^\|[-| ]+\|", re.MULTILINE)


class StructuralValidator:
    """Validates document structure preservation against the IDM.

    Runs 5 checks (each worth 20 points):
    1. Heading count match
    2. Heading hierarchy preservation
    3. List count match
    4. Table count match
    5. Heading content ordering
    """

    def validate(
        self, idm: IntermediateDocumentModel, markdown_content: str
    ) -> Tuple[float, List[Finding]]:
        """Runs all structural checks.

        Returns:
            (score 0–100, findings list)
        """
        findings: List[Finding] = []
        passed = 0
        total = 5

        idm_headings = [
            b for p in idm.pages for b in p.blocks if isinstance(b, HeadingBlock)
        ]
        idm_lists = [
            b for p in idm.pages for b in p.blocks if isinstance(b, ListBlock)
        ]
        idm_tables = [
            b for p in idm.pages for b in p.blocks if isinstance(b, TableBlock)
        ]

        md_headings = _HEADING_PATTERN.findall(markdown_content)
        md_list_items = _LIST_ITEM_PATTERN.findall(markdown_content)
        md_tables = _TABLE_SEP_PATTERN.findall(markdown_content)

        # Check 1: Heading count
        if len(idm_headings) == len(md_headings):
            passed += 1
        else:
            findings.append(Finding(
                severity=FindingSeverity.WARNING,
                category=FindingCategory.STRUCTURE,
                message=(
                    f"Heading count mismatch: IDM has {len(idm_headings)}, "
                    f"Markdown has {len(md_headings)}"
                ),
            ))

        # Check 2: Heading hierarchy (level sequence)
        idm_levels = [b.level for b in idm_headings]
        md_levels = [len(h.rstrip()) for h in md_headings]
        if idm_levels == md_levels:
            passed += 1
        else:
            findings.append(Finding(
                severity=FindingSeverity.WARNING,
                category=FindingCategory.STRUCTURE,
                message="Heading hierarchy does not match IDM level sequence.",
            ))

        # Check 3: List block count
        idm_list_count = len(idm_lists)
        md_list_count = len(self._count_list_groups(markdown_content))
        if idm_list_count == md_list_count:
            passed += 1
        else:
            findings.append(Finding(
                severity=FindingSeverity.WARNING,
                category=FindingCategory.STRUCTURE,
                message=(
                    f"List count mismatch: IDM has {idm_list_count}, "
                    f"Markdown has {md_list_count} list group(s)"
                ),
            ))

        # Check 4: Table count
        if len(idm_tables) == len(md_tables):
            passed += 1
        else:
            findings.append(Finding(
                severity=FindingSeverity.WARNING,
                category=FindingCategory.STRUCTURE,
                message=(
                    f"Table count mismatch: IDM has {len(idm_tables)}, "
                    f"Markdown has {len(md_tables)}"
                ),
            ))

        # Check 5: Heading content ordering
        if self._heading_order_preserved(idm_headings, markdown_content):
            passed += 1
        else:
            findings.append(Finding(
                severity=FindingSeverity.WARNING,
                category=FindingCategory.STRUCTURE,
                message="Heading reading order is not preserved in Markdown output.",
            ))

        score = round((passed / total) * 100.0, 2)
        return score, findings

    def _count_list_groups(self, content: str) -> List[List[str]]:
        """Groups consecutive list-item lines into list blocks."""
        groups: List[List[str]] = []
        current: List[str] = []
        for line in content.split("\n"):
            if _LIST_ITEM_PATTERN.match(line):
                current.append(line)
            else:
                if current:
                    groups.append(current)
                    current = []
        if current:
            groups.append(current)
        return groups

    def _heading_order_preserved(
        self, idm_headings: List[HeadingBlock], markdown_content: str
    ) -> bool:
        """Checks that IDM headings appear in the same relative order in Markdown."""
        if not idm_headings:
            return True
        positions: List[int] = []
        for block in idm_headings:
            idx = markdown_content.find(block.content)
            if idx == -1:
                return False
            positions.append(idx)
        return positions == sorted(positions)
