"""
accuracy_tester/semantic_scorer.py

Component 3 — Semantic quality scoring via Claude Sonnet 4.6.

Sends only the matched pairs to Sonnet for soft text fields (brand,
product_name, flavor) and returns per-field semantic scores plus a list
of flagged rows with severe deviations.
"""

from __future__ import annotations

import json
import re

from anthropic import Anthropic

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 8192
_TIMEOUT = 120.0

# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a semantic similarity scoring engine for a retail shelf-analysis \
pipeline.  You compare AI-generated product text fields against manually \
verified ground truth and score how close they are."""

_USER_PROMPT_TEMPLATE = """\
## Matched SKU Pairs ({pair_count} pairs)

For each pair below, the "gt" object is the ground truth and the "gen" \
object is the AI-generated output.

{pairs_json}

---

## Instructions

For each matched pair, score semantic closeness **0-100** for these three \
fields:
- **brand**: How closely does the generated brand match the ground truth?
- **product_name**: How closely does the generated product name match?
- **flavor**: How closely does the generated flavor match?

Scoring guidance:
- 100 = identical or trivially different (capitalisation, punctuation)
- 80-99 = clearly the same product, minor wording difference
- 50-79 = partially correct (e.g. right brand family, wrong sub-brand)
- 1-49 = substantially wrong
- 0 = completely absent or completely wrong

Flag rows where deviation is **severe** (any of):
- Flavor completely missing when obvious from product name
- Brand completely wrong or absent
- Product name bears no resemblance to ground truth

Average each field's score across all pairs to get per-field percentages.
Overall semantic score = average of the three per-field scores.

Return **only** a JSON object with this exact schema (no markdown fences, \
no prose):

{{"product_name_score_pct": 85.0, "flavor_score_pct": 90.0, \
"brand_score_pct": 95.0, "overall_semantic_score_pct": 90.0, \
"flagged_rows": [{{"sku_identifier": "brand | product | 330ml", \
"field": "flavor", "gt_value": "mango", "generated_value": "null", \
"reason": "flavor missing"}}]}}"""


# ---------------------------------------------------------------------------
# JSON cleaning (same pattern as key_normaliser)
# ---------------------------------------------------------------------------

def _clean_json(raw: str) -> dict:
    """Extract and parse a JSON object from a Claude response string."""
    text = raw.strip()

    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(
                f"No JSON object found in Claude response.\n"
                f"Raw response:\n{raw}"
            )
        text = text[start : end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON after cleaning: {exc}\n"
            f"Raw response:\n{raw}"
        ) from exc


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_semantic_fields(
    matched_pairs: list[tuple[int, int]],
    gt_rows: list[dict],
    gen_rows: list[dict],
    api_key: str,
) -> dict:
    """
    Call 2: semantic quality scoring for soft text fields via Sonnet.

    Args:
        matched_pairs: List of (gt_index, gen_index) tuples from comparator.
        gt_rows:       Ground-truth row dicts.
        gen_rows:      Generated row dicts.
        api_key:       Anthropic API key.

    Returns:
        {"product_name_score_pct": float,
         "flavor_score_pct": float,
         "brand_score_pct": float,
         "overall_semantic_score_pct": float,
         "flagged_rows": [...]}
    """
    _SOFT_FIELDS = ["brand", "product_name", "flavor"]

    pairs_data = []
    for gt_idx, gen_idx in matched_pairs:
        gt_row = gt_rows[gt_idx]
        gen_row = gen_rows[gen_idx]
        pair = {
            "gt": {f: gt_row.get(f) for f in _SOFT_FIELDS},
            "gen": {f: gen_row.get(f) for f in _SOFT_FIELDS},
            "sku_identifier": _sku_identifier(gt_row),
        }
        pairs_data.append(pair)

    client = Anthropic(api_key=api_key, timeout=_TIMEOUT)

    prompt = _USER_PROMPT_TEMPLATE.format(
        pair_count=len(pairs_data),
        pairs_json=json.dumps(pairs_data, indent=2, default=str),
    )

    response = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text
    return _clean_json(raw_text)


def _sku_identifier(row: dict) -> str:
    """Build a human-readable SKU identifier from a row dict."""
    brand = row.get("brand") or "?"
    name = row.get("product_name") or "?"
    size = row.get("packaging_size_ml")
    size_str = str(size) if size is not None else "?"
    return f"{brand} | {name} | {size_str}ml"
