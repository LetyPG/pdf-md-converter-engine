from dataclasses import dataclass, field
from typing import List


@dataclass
class MarkdownResult:
    """Output contract of the Markdown Generator (Stage 3).

    Consumed by the Quality Validator (Stage 4) and Output Manager (Stage 5).

    Attributes:
        content: The full rendered Markdown string. UTF-8, Unix line endings.
        warnings: Warnings propagated from the IDM plus any generator-level warnings.
    """

    content: str
    warnings: List[str] = field(default_factory=list)
