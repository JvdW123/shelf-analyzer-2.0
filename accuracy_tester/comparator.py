"""
accuracy_tester/comparator.py

Component 2a — Row matching and data formatting.

Provides:
  - format_rows_for_claude()  — strips non-scoring columns before any Claude call
  - match_rows()              — two-pass deterministic matching (exact then fuzzy)
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field

from accuracy_tester.excel_reader import (
    METADATA_COLUMNS,
    FORMULA_COLUMNS,
    NON_SCORING_COLUMNS,
)

_EXCLUDED: frozenset[str] = frozenset(
    METADATA_COLUMNS | FORMULA_COLUMNS | NON_SCORING_COLUMNS
)

_FUZZY_THRESHOLD = 0.85


@dataclass
class MatchResult:
    """Output of the two-pass row matching algorithm."""

    matched_pairs: list[tuple[int, int]] = field(default_factory=list)
    unmatched_gt: list[int] = field(default_factory=list)
    unmatched_gen: list[int] = field(default_factory=list)


def format_rows_for_claude(rows: list[dict]) -> list[dict]:
    """
    Strip non-scoring columns from a list of row dicts.

    Removes metadata columns (country, city, retailer, etc.), formula columns
    (price_per_liter_eur), and non-scoring columns (photo) so Claude only
    receives the fields it needs to evaluate.
    """
    return [
        {k: v for k, v in row.items() if k not in _EXCLUDED}
        for row in rows
    ]


def match_rows(
    gt_keys: list[dict],
    gen_keys: list[dict],
    gt_rows: list[dict],
    gen_rows: list[dict],
) -> MatchResult:
    """
    Two-pass deterministic row matching using normalised keys.

    Pass 1: exact key equality.
    Pass 2: fuzzy matching on remaining rows (difflib.SequenceMatcher >= 0.85).

    Args:
        gt_keys:  [{"row_index": int, "key": str}, ...] from key_normaliser
        gen_keys: [{"row_index": int, "key": str}, ...] from key_normaliser
        gt_rows:  Original ground-truth row dicts (used only for length validation)
        gen_rows: Original generated row dicts (used only for length validation)

    Returns:
        MatchResult with matched_pairs, unmatched_gt, unmatched_gen.
    """
    gt_by_idx = {entry["row_index"]: entry["key"] for entry in gt_keys}
    gen_by_idx = {entry["row_index"]: entry["key"] for entry in gen_keys}

    matched: list[tuple[int, int]] = []
    used_gt: set[int] = set()
    used_gen: set[int] = set()

    # --- Pass 1: exact key match ---
    gen_key_lookup: dict[str, list[int]] = {}
    for gi, gk in gen_by_idx.items():
        gen_key_lookup.setdefault(gk, []).append(gi)

    for gt_idx, gt_key in gt_by_idx.items():
        if gt_key in gen_key_lookup:
            candidates = [c for c in gen_key_lookup[gt_key] if c not in used_gen]
            if candidates:
                gen_idx = candidates[0]
                matched.append((gt_idx, gen_idx))
                used_gt.add(gt_idx)
                used_gen.add(gen_idx)

    # --- Pass 2: fuzzy match on remaining rows ---
    # Known limitation: greedy best-match can mis-pair rows when packaging
    # size is missing or "unknown" in the normalised key, because multiple
    # SKUs from the same brand then have very similar keys.  A future
    # improvement could use the Hungarian algorithm for optimal assignment.
    remaining_gt = [(i, k) for i, k in gt_by_idx.items() if i not in used_gt]
    remaining_gen = [(i, k) for i, k in gen_by_idx.items() if i not in used_gen]

    if remaining_gt and remaining_gen:
        scored_pairs: list[tuple[float, int, int]] = []
        for gt_idx, gt_key in remaining_gt:
            for gen_idx, gen_key in remaining_gen:
                ratio = difflib.SequenceMatcher(
                    None, gt_key, gen_key
                ).ratio()
                if ratio >= _FUZZY_THRESHOLD:
                    scored_pairs.append((ratio, gt_idx, gen_idx))

        scored_pairs.sort(key=lambda t: t[0], reverse=True)

        for _, gt_idx, gen_idx in scored_pairs:
            if gt_idx not in used_gt and gen_idx not in used_gen:
                matched.append((gt_idx, gen_idx))
                used_gt.add(gt_idx)
                used_gen.add(gen_idx)

    all_gt = set(gt_by_idx.keys())
    all_gen = set(gen_by_idx.keys())

    return MatchResult(
        matched_pairs=matched,
        unmatched_gt=sorted(all_gt - used_gt),
        unmatched_gen=sorted(all_gen - used_gen),
    )
