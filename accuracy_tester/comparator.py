"""
accuracy_tester/comparator.py

Data formatter — prepares Excel row dicts as clean JSON-serialisable lists
for consumption by the Claude semantic scorer (Call 1 in semantic_scorer.py).

All matching and field-comparison logic has been moved to Claude (Call 1).
This module is intentionally minimal: its only job is to strip non-scoring
columns before the rows are serialised and sent to the API.
"""

from __future__ import annotations

from accuracy_tester.excel_reader import (
    METADATA_COLUMNS,
    FORMULA_COLUMNS,
    NON_SCORING_COLUMNS,
)

# Combined set of columns to strip before sending to Claude
_EXCLUDED: frozenset[str] = frozenset(
    METADATA_COLUMNS | FORMULA_COLUMNS | NON_SCORING_COLUMNS
)


def format_rows_for_claude(rows: list[dict]) -> list[dict]:
    """
    Strip non-scoring columns from a list of row dicts.

    Removes metadata columns (country, city, retailer, etc.), formula columns
    (price_per_liter_eur), and non-scoring columns (photo) so Claude only
    receives the fields it needs to evaluate.

    Args:
        rows: Row dicts from excel_reader.read_excel()

    Returns:
        Cleaned list of dicts containing only scoreable fields.
    """
    return [
        {k: v for k, v in row.items() if k not in _EXCLUDED}
        for row in rows
    ]
