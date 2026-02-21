"""
accuracy_tester/comparator.py

Pure Python row-matching and field-level diff engine.
No LLM calls — all logic is deterministic.

## Row matching strategy
Each row is identified by a composite key:
    brand  +  product_name  +  packaging_size_ml

Matching proceeds in two passes:
  1. Exact key match (fast path)
  2. Fuzzy key match using difflib.SequenceMatcher for rows that did not
     find an exact partner (handles minor spelling differences between
     what was typed in ground truth vs. what Claude returned)

A fuzzy match is accepted when similarity >= FUZZY_THRESHOLD (0.80).

## Field comparison
- Text fields: case-insensitive, whitespace-stripped string equality
- Numeric fields (int/float): exact equality after normalisation
  (both None → match; one None → mismatch)
- None vs None is always a match (both unknown = consistent)

## Output
compare() returns a ComparisonResult dataclass containing:
  - matched_pairs: list of (gt_row, gen_row, {key: FieldResult})
  - unmatched_gt: rows in ground truth with no match in generated output
  - unmatched_gen: rows in generated output with no match in ground truth
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Optional

from accuracy_tester.excel_reader import get_comparable_columns

# Minimum similarity ratio to accept a fuzzy match
FUZZY_THRESHOLD: float = 0.80

# Keys used to build the composite matching key
MATCH_KEY_FIELDS: tuple[str, ...] = ("brand", "product_name", "packaging_size_ml")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class FieldResult:
    """Comparison result for a single cell."""
    column_key: str
    column_name: str
    ground_truth_value: object
    generated_value: object
    match: bool        # True if values are considered equal
    both_null: bool    # True if both sides are None/empty


@dataclass
class RowPair:
    """A matched pair of rows with field-level results."""
    match_key: str                          # The composite key used for matching
    match_type: str                         # "exact" or "fuzzy"
    fuzzy_score: float                      # 1.0 for exact matches
    ground_truth_row: dict
    generated_row: dict
    fields: dict[str, FieldResult] = field(default_factory=dict)


@dataclass
class ComparisonResult:
    """Full output of the comparison engine."""
    matched_pairs: list[RowPair] = field(default_factory=list)
    unmatched_gt: list[dict] = field(default_factory=list)   # in GT, not in generated
    unmatched_gen: list[dict] = field(default_factory=list)  # in generated, not in GT
    comparable_columns: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Key building
# ---------------------------------------------------------------------------

def _build_key(row: dict) -> str:
    """
    Build a normalised composite key string for a row.
    Uses brand + product_name + packaging_size_ml.
    None values become empty string so they still participate in matching.
    """
    parts = []
    for f in MATCH_KEY_FIELDS:
        val = row.get(f)
        if val is None:
            parts.append("")
        else:
            parts.append(str(val).strip().lower())
    return " | ".join(parts)


def _fuzzy_similarity(a: str, b: str) -> float:
    """Return similarity ratio between two strings (0.0–1.0)."""
    return difflib.SequenceMatcher(None, a, b).ratio()


# ---------------------------------------------------------------------------
# Field comparison
# ---------------------------------------------------------------------------

def _normalise_value(value: object, col_type: str) -> object:
    """Normalise a cell value for comparison."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    if col_type == "text":
        return str(value).strip().lower()
    if col_type == "integer":
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    if col_type == "float":
        try:
            return round(float(value), 4)
        except (ValueError, TypeError):
            return None
    return value


def _compare_field(gt_val: object, gen_val: object, col_spec: dict) -> FieldResult:
    """Compare a single field value from ground truth vs. generated output."""
    col_type = col_spec["type"]
    gt_norm = _normalise_value(gt_val, col_type)
    gen_norm = _normalise_value(gen_val, col_type)

    both_null = gt_norm is None and gen_norm is None
    match = both_null or (gt_norm == gen_norm)

    return FieldResult(
        column_key=col_spec["key"],
        column_name=col_spec["name"],
        ground_truth_value=gt_val,
        generated_value=gen_val,
        match=match,
        both_null=both_null,
    )


# ---------------------------------------------------------------------------
# Main comparison function
# ---------------------------------------------------------------------------

def compare(
    ground_truth: list[dict],
    generated: list[dict],
) -> ComparisonResult:
    """
    Match rows between ground_truth and generated lists, then compare
    every comparable field.

    Args:
        ground_truth: Rows from the manually verified Excel (from excel_reader.read_excel)
        generated:    Rows from the pipeline-generated Excel

    Returns:
        ComparisonResult with matched pairs and any unmatched rows.
    """
    comparable_cols = get_comparable_columns()
    result = ComparisonResult(comparable_columns=comparable_cols)

    # Build key maps
    gt_key_map: dict[str, dict] = {}      # key → row (first occurrence wins)
    gen_key_map: dict[str, dict] = {}

    for row in ground_truth:
        k = _build_key(row)
        if k not in gt_key_map:
            gt_key_map[k] = row

    for row in generated:
        k = _build_key(row)
        if k not in gen_key_map:
            gen_key_map[k] = row

    gt_keys = list(gt_key_map.keys())
    gen_keys = list(gen_key_map.keys())

    matched_gt_keys: set[str] = set()
    matched_gen_keys: set[str] = set()

    # --- Pass 1: exact matches ---
    for gt_key in gt_keys:
        if gt_key in gen_key_map:
            pair = _build_row_pair(
                gt_key, gt_key_map[gt_key], gen_key_map[gt_key],
                match_type="exact", fuzzy_score=1.0,
                comparable_cols=comparable_cols,
            )
            result.matched_pairs.append(pair)
            matched_gt_keys.add(gt_key)
            matched_gen_keys.add(gt_key)

    # --- Pass 2: fuzzy matches for unmatched rows ---
    unmatched_gt_keys = [k for k in gt_keys if k not in matched_gt_keys]
    unmatched_gen_keys = [k for k in gen_keys if k not in matched_gen_keys]

    for gt_key in unmatched_gt_keys:
        best_key: Optional[str] = None
        best_score: float = 0.0

        for gen_key in unmatched_gen_keys:
            if gen_key in matched_gen_keys:
                continue
            score = _fuzzy_similarity(gt_key, gen_key)
            if score > best_score:
                best_score = score
                best_key = gen_key

        if best_key is not None and best_score >= FUZZY_THRESHOLD:
            pair = _build_row_pair(
                gt_key, gt_key_map[gt_key], gen_key_map[best_key],
                match_type="fuzzy", fuzzy_score=best_score,
                comparable_cols=comparable_cols,
            )
            result.matched_pairs.append(pair)
            matched_gt_keys.add(gt_key)
            matched_gen_keys.add(best_key)

    # --- Collect unmatched rows ---
    for gt_key in gt_keys:
        if gt_key not in matched_gt_keys:
            result.unmatched_gt.append(gt_key_map[gt_key])

    for gen_key in gen_keys:
        if gen_key not in matched_gen_keys:
            result.unmatched_gen.append(gen_key_map[gen_key])

    return result


def _build_row_pair(
    match_key: str,
    gt_row: dict,
    gen_row: dict,
    match_type: str,
    fuzzy_score: float,
    comparable_cols: list[dict],
) -> RowPair:
    """Build a RowPair by comparing all comparable fields."""
    pair = RowPair(
        match_key=match_key,
        match_type=match_type,
        fuzzy_score=fuzzy_score,
        ground_truth_row=gt_row,
        generated_row=gen_row,
    )
    for col_spec in comparable_cols:
        key = col_spec["key"]
        field_result = _compare_field(
            gt_val=gt_row.get(key),
            gen_val=gen_row.get(key),
            col_spec=col_spec,
        )
        pair.fields[key] = field_result

    return pair
