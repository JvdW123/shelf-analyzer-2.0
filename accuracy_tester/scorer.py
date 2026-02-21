"""
accuracy_tester/scorer.py

Component 2b — Deterministic field scoring (pure Python, no LLM calls).

Scores Sections 1-4 and builds Section 6 from matched/unmatched row data.
Also provides merge_section6() to combine critical errors from this module
with warning-level flagged rows from the semantic scorer.
"""

from __future__ import annotations

from accuracy_tester.comparator import MatchResult


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_str(val) -> str | None:
    """Normalise a value to a stripped lowercase string, or None."""
    if val is None:
        return None
    s = str(val).strip()
    if s.lower() in ("", "nan", "none", "null"):
        return None
    return s.lower()


def _safe_num(val) -> float | None:
    """Coerce a value to float, or None."""
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _sku_identifier(row: dict) -> str:
    """Build a human-readable SKU identifier from a row dict."""
    brand = row.get("brand") or "?"
    name = row.get("product_name") or "?"
    size = row.get("packaging_size_ml")
    size_str = str(size) if size is not None else "?"
    return f"{brand} | {name} | {size_str}ml"


def _score_field(
    matched_pairs: list[tuple[int, int]],
    gt_rows: list[dict],
    gen_rows: list[dict],
    field_key: str,
    compare_fn,
) -> dict:
    """
    Score a single field across all matched pairs.

    Returns {"correct": int, "incorrect": int, "accuracy_pct": float}
    and a list of error dicts for Section 6.
    """
    correct = 0
    incorrect = 0
    errors: list[dict] = []

    for gt_idx, gen_idx in matched_pairs:
        gt_val = gt_rows[gt_idx].get(field_key)
        gen_val = gen_rows[gen_idx].get(field_key)

        if compare_fn(gt_val, gen_val):
            correct += 1
        else:
            incorrect += 1
            errors.append({
                "sku_identifier": _sku_identifier(gt_rows[gt_idx]),
                "field": field_key,
                "gt_value": str(gt_val) if gt_val is not None else "null",
                "generated_value": str(gen_val) if gen_val is not None else "null",
                "severity": "critical",
            })

    total = correct + incorrect
    pct = round(correct / total * 100, 1) if total > 0 else 0.0
    return {"correct": correct, "incorrect": incorrect, "accuracy_pct": pct}, errors


# ---------------------------------------------------------------------------
# Comparison functions
# ---------------------------------------------------------------------------

def _cmp_integer(gt, gen) -> bool:
    a = _safe_num(gt)
    b = _safe_num(gen)
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return int(a) == int(b)


def _cmp_price(gt, gen) -> bool:
    a = _safe_num(gt)
    b = _safe_num(gen)
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) <= 0.01


def _cmp_case_insensitive(gt, gen) -> bool:
    a = _safe_str(gt)
    b = _safe_str(gen)
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return a == b


def _cmp_private_label(gt, gen) -> bool:
    """Both sides agree on whether the value contains 'private label'."""
    a = _safe_str(gt) or ""
    b = _safe_str(gen) or ""
    return ("private label" in a) == ("private label" in b)


def _cmp_branded_private_label(gt, gen) -> bool:
    """Both sides agree on whether the value contains 'branded private label'."""
    a = _safe_str(gt) or ""
    b = _safe_str(gen) or ""
    return ("branded private label" in a) == ("branded private label" in b)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_all_sections(
    match_result: MatchResult,
    gt_rows: list[dict],
    gen_rows: list[dict],
) -> dict:
    """
    Score Sections 1-4 and build Section 6 (critical errors only).

    All scoring is deterministic Python — no LLM calls.

    Returns:
        Dict with keys: section1, section2, section3, section4, section6.
    """
    pairs = match_result.matched_pairs
    section6: list[dict] = []

    # --- Section 1: Completeness ---
    missed_skus = [
        {
            "brand": gt_rows[i].get("brand"),
            "product_name": gt_rows[i].get("product_name"),
            "packaging_size_ml": gt_rows[i].get("packaging_size_ml"),
        }
        for i in match_result.unmatched_gt
    ]
    hallucinated_skus = [
        {
            "brand": gen_rows[i].get("brand"),
            "product_name": gen_rows[i].get("product_name"),
            "packaging_size_ml": gen_rows[i].get("packaging_size_ml"),
        }
        for i in match_result.unmatched_gen
    ]
    total_gt = len(gt_rows)
    matched_count = len(pairs)
    completeness_pct = round(matched_count / total_gt * 100, 1) if total_gt > 0 else 0.0

    section1 = {
        "missed_skus": missed_skus,
        "hallucinated_skus": hallucinated_skus,
        "matched_count": matched_count,
        "total_gt_count": total_gt,
        "completeness_score_pct": completeness_pct,
    }

    # --- Section 2: Critical fields ---
    s2_fields = [
        ("shelf_level", _cmp_integer),
        ("shelf_levels", _cmp_integer),
        ("facings", _cmp_integer),
        ("price_local", _cmp_price),
        ("packaging_size_ml", _cmp_integer),
    ]
    section2 = {}
    for field_key, cmp_fn in s2_fields:
        scores, errors = _score_field(pairs, gt_rows, gen_rows, field_key, cmp_fn)
        section2[field_key] = scores
        section6.extend(errors)

    # --- Section 3: Classification fields ---
    s3_product_type, s3_pt_errors = _score_field(
        pairs, gt_rows, gen_rows, "product_type", _cmp_case_insensitive
    )
    section6.extend(s3_pt_errors)

    s3_pl_scores, s3_pl_errors = _score_field(
        pairs, gt_rows, gen_rows, "branded_private_label", _cmp_private_label
    )
    section6.extend(s3_pl_errors)

    s3_bpl_scores, s3_bpl_errors = _score_field(
        pairs, gt_rows, gen_rows, "branded_private_label", _cmp_branded_private_label
    )
    section6.extend(s3_bpl_errors)

    section3 = {
        "product_type": s3_product_type,
        "is_private_label": s3_pl_scores,
        "is_branded_private_label": s3_bpl_scores,
    }

    # --- Section 4: Extraction method fields ---
    s4_fields = [
        "juice_extraction_method",
        "processing_method",
        "hpp_treatment",
        "packaging_type",
    ]
    section4 = {}
    for field_key in s4_fields:
        scores, errors = _score_field(
            pairs, gt_rows, gen_rows, field_key, _cmp_case_insensitive
        )
        section4[field_key] = scores
        section6.extend(errors)

    return {
        "section1": section1,
        "section2": section2,
        "section3": section3,
        "section4": section4,
        "section6": section6,
    }


def merge_section6(
    scored_result: dict,
    semantic_flagged_rows: list[dict],
) -> dict:
    """
    Merge Section 6 critical errors (from score_all_sections) with
    warning-level flagged rows (from semantic_scorer).

    Appends semantic flagged rows with severity="warning" to the existing
    Section 6 list and returns the updated scored_result dict.

    Args:
        scored_result:         Dict returned by score_all_sections().
        semantic_flagged_rows: List of flagged row dicts from
                               score_semantic_fields()["flagged_rows"].

    Returns:
        The scored_result dict with section6 updated in-place.
    """
    warning_rows = [
        {**row, "severity": "warning"}
        for row in semantic_flagged_rows
    ]
    scored_result["section6"] = scored_result.get("section6", []) + warning_rows
    return scored_result
