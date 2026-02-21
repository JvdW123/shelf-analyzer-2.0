"""
accuracy_tester/semantic_scorer.py

Call 1 of the two-call accuracy evaluation pipeline.

Uses Claude Opus 4.6 with Extended Thinking to:
  1. Semantically match SKUs between ground truth and generated output
  2. Score accuracy across all 6 output sections
  3. Return a structured JSON dict

This module always uses Opus + Extended Thinking regardless of any user
settings — the Deep Diagnosis toggle in the UI affects only Call 2
(diagnostics.py).
"""

from __future__ import annotations

import json

from anthropic import Anthropic

from accuracy_tester.comparator import format_rows_for_claude
from accuracy_tester.scorer import parse_semantic_result

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

SCORING_MODEL = "claude-opus-4-6"
SCORING_MAX_TOKENS = 32000
SCORING_THINKING_CONFIG = {
    "type": "enabled",
    "budget_tokens": 16000,
}
SCORING_TIMEOUT = 600.0  # 10 minutes — Extended Thinking can be slow

# ---------------------------------------------------------------------------
# Prompt — static instructions and schema (no f-string so no escaping needed)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are an accuracy evaluation engine for a shelf-analysis AI system.

You will receive:
  - A list of ground truth SKU rows (manually verified product data)
  - A list of AI-generated SKU rows (output from the shelf analysis pipeline)

Your task:
  1. Semantically match each generated SKU to the most likely ground truth SKU
  2. Score accuracy across 6 sections exactly as specified
  3. Return ONLY a valid JSON object — no prose, no markdown fences, no preamble

The JSON must conform exactly to the schema specified in the user message.
Do not wrap the JSON in ```json fences. Output raw JSON only.
"""

_SCORING_INSTRUCTIONS = """
---

## Matching and Scoring Rules

### SKU Matching
- Match each generated SKU to the most semantically similar ground truth SKU
- Primary signals: brand + product_name + packaging_size_ml
- Accept minor spelling differences, abbreviations, and capitalisation differences
- Each SKU can only be matched once (1-to-1 matching)
- Unmatched ground truth SKUs = missed (pipeline failed to find them)
- Unmatched generated SKUs = hallucinated (pipeline invented them)

### Section 2 — Critical Fields (score per matched pair)
- `shelf_level`: maps to the `shelf_level` column — exact text match (case-insensitive)
- `number_of_shelf_levels`: maps to the `shelf_levels` column — exact integer match
- `facings`: exact integer match
- `price`: maps to the `price_local` column — correct if within ±0.01 of ground truth value
- `packaging_size_ml`: exact integer match

### Section 3 — Classification Fields
- `is_private_label`: infer from `branded_private_label` text.
  True if value semantically means private label (e.g. "Private Label", "Own Brand",
  "Store Brand", "PL"). Compare the GT inference vs the generated inference — score
  as correct if both sides agree.
- `is_branded_private_label`: True if value semantically means branded private label
  (e.g. "Branded Private Label", "B-PL", "Branded Own Label"). Compare GT vs generated.
- `product_type`: semantic match — score correct if the meaning is equivalent
  (e.g. "NFC Juice" ≈ "Not From Concentrate Juice"). Flag as incorrect only if
  the product category is completely wrong.

### Section 4 — Extraction Method Fields (exact categorical match)
- `extraction_method`: maps to `juice_extraction_method` column
- `processing_method`: exact categorical match
- `hpp_treatment`: exact categorical match
- `packaging_type`: exact categorical match

### Section 5 — Semantic Field Quality (soft text scoring)
Score 0–100 per matched pair for each of:
- `product_name`: how closely does the generated name match the ground truth name?
- `flavor`: how closely does the generated flavor match? Severe deviation = flavor
  completely absent when the product name makes it obvious, or completely wrong flavor.
- `brand`: how closely does the generated brand match? Severe deviation = brand
  completely absent or completely wrong.
Average each score across all matched pairs to get per-field scores.
Overall semantic score = average of the three per-field scores.

### Section 6 — Flagged Rows
Include one entry per (SKU, field) pair where at least one of the following is true:
- Any Section 2 field is incorrect → severity = "critical"
- Any Section 3 field is incorrect → severity = "critical"
- Any Section 4 field is incorrect → severity = "critical"
- Any Section 5 field has a severe semantic deviation (score < 40) → severity = "warning"

---

## Required JSON Output

Return ONLY the following JSON object. Fill all counts and scores with real values.
Do NOT include any text before or after the JSON.

{
  "section1": {
    "missed_skus": [
      {"sku_id": "<brand>|<product_name>|<packaging_size_ml>", "brand": "string", "product_name": "string", "packaging_size_ml": null}
    ],
    "hallucinated_skus": [
      {"sku_id": "<brand>|<product_name>|<packaging_size_ml>", "brand": "string", "product_name": "string", "packaging_size_ml": null}
    ],
    "matched_count": 0,
    "total_gt_count": 0,
    "completeness_score_pct": 0.0
  },
  "section2": {
    "shelf_level":            {"correct": 0, "incorrect": 0, "accuracy_pct": 0.0},
    "number_of_shelf_levels": {"correct": 0, "incorrect": 0, "accuracy_pct": 0.0},
    "facings":                {"correct": 0, "incorrect": 0, "accuracy_pct": 0.0},
    "price":                  {"correct": 0, "incorrect": 0, "accuracy_pct": 0.0},
    "packaging_size_ml":      {"correct": 0, "incorrect": 0, "accuracy_pct": 0.0}
  },
  "section3": {
    "is_private_label":         {"correct": 0, "incorrect": 0, "accuracy_pct": 0.0},
    "is_branded_private_label": {"correct": 0, "incorrect": 0, "accuracy_pct": 0.0},
    "product_type": {
      "correct": 0, "incorrect": 0, "accuracy_pct": 0.0,
      "flagged": [
        {"sku_id": "string", "gt_value": "string", "generated_value": "string", "reason": "string"}
      ]
    }
  },
  "section4": {
    "extraction_method": {"correct": 0, "incorrect": 0, "accuracy_pct": 0.0},
    "processing_method": {"correct": 0, "incorrect": 0, "accuracy_pct": 0.0},
    "hpp_treatment":     {"correct": 0, "incorrect": 0, "accuracy_pct": 0.0},
    "packaging_type":    {"correct": 0, "incorrect": 0, "accuracy_pct": 0.0}
  },
  "section5": {
    "overall_semantic_score_pct": 0.0,
    "product_name_score_pct": 0.0,
    "flavor_score_pct": 0.0,
    "brand_score_pct": 0.0,
    "flagged_rows": [
      {"sku_id": "string", "field": "string", "gt_value": "string", "generated_value": "string", "reason": "string"}
    ]
  },
  "section6": [
    {"sku_id": "string", "field": "string", "gt_value": "string", "generated_value": "string", "severity": "critical"}
  ]
}
"""


def _build_scoring_prompt(gt_rows: list[dict], gen_rows: list[dict]) -> str:
    """Build the full scoring prompt by combining data with static instructions."""
    gt_json = json.dumps(gt_rows, indent=2, default=str)
    gen_json = json.dumps(gen_rows, indent=2, default=str)

    data_section = (
        f"## Ground Truth SKUs ({len(gt_rows)} rows)\n"
        f"{gt_json}\n\n"
        f"## Generated SKUs ({len(gen_rows)} rows)\n"
        f"{gen_json}\n"
    )
    return data_section + _SCORING_INSTRUCTIONS


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_semantic_scoring(
    gt_rows: list[dict],
    gen_rows: list[dict],
    api_key: str,
) -> dict:
    """
    Call 1: semantic matching and 6-section scoring via Opus Extended Thinking.

    Args:
        gt_rows:  Ground truth rows from excel_reader.read_excel()
        gen_rows: Generated rows from excel_reader.read_excel()
        api_key:  Anthropic API key

    Returns:
        Parsed dict with keys: section1, section2, section3, section4, section5, section6

    Raises:
        ValueError: If Claude returns malformed JSON.
        anthropic.APIError: On API-level failures.
    """
    client = Anthropic(api_key=api_key, timeout=SCORING_TIMEOUT)

    clean_gt = format_rows_for_claude(gt_rows)
    clean_gen = format_rows_for_claude(gen_rows)
    prompt = _build_scoring_prompt(clean_gt, clean_gen)

    response = client.messages.create(
        model=SCORING_MODEL,
        max_tokens=SCORING_MAX_TOKENS,
        thinking=SCORING_THINKING_CONFIG,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    # Discard thinking blocks — extract only the final text response
    text_parts = [
        block.text
        for block in response.content
        if block.type == "text"
    ]
    raw_text = "\n".join(text_parts)
    return parse_semantic_result(raw_text)
