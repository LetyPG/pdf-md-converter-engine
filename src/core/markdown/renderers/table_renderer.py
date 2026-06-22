from typing import List

from src.core.models.extraction import TableBlock


class TableRenderer:
    """Renders TableBlock into GFM pipe-table syntax.

    Rule (from output_md_schema.md):
        headers=["A","B"], rows=[["1","2"]] →
        | A | B |
        |---|---|
        | 1 | 2 |

    Column order matches the IDM (spec requirement).
    Rows shorter than the header count are padded with empty strings.
    Separator uses "---" per column — deterministic, no padding alignment.
    """

    def render(self, block: TableBlock) -> str:
        """Renders the table block.

        Args:
            block: TableBlock instance from the IDM.

        Returns:
            GFM pipe-table string. Returns empty string if headers are absent.
        """
        if not block.headers:
            return ""

        col_count = len(block.headers)
        header_row = "| " + " | ".join(block.headers) + " |"
        separator_row = "|" + "|".join(["---"] * col_count) + "|"

        data_rows: List[str] = []
        for row in block.rows:
            padded: List[str] = list(row) + [""] * (col_count - len(row))
            data_rows.append("| " + " | ".join(padded[:col_count]) + " |")

        return "\n".join([header_row, separator_row] + data_rows)
