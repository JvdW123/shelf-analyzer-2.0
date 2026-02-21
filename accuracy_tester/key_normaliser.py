"""
accuracy_tester/key_normaliser.py

Component 1 — Sonnet key normalisation.

Sends both ground-truth and generated row lists to Claude Sonnet 4.6 and asks
it to produce a normalised string key (brand | product_name | packaging_size)
for every SKU in both datasets.  The keys are used downstream by comparator.py
for deterministic row matching.
"""

from __future__ import annotations

import json
import re

from anthropic import Anthropic

from accuracy_tester.comparator import format_rows_for_claude

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
You are a data-normalisation engine.  You receive two lists of SKU rows \
(ground truth and generated) from a retail shelf-analysis pipeline.  Your \
only job is to produce a normalised string key for every row so that the \
same physical product gets the same key in both lists."""

_USER_PROMPT_TEMPLATE = """\
## Ground Truth SKUs ({gt_count} rows)

{gt_json}

## Generated SKUs ({gen_count} rows)

{gen_json}

---

## Instructions

For every SKU in **both** datasets, produce a normalised string key with the
format:  brand | product_name | packaging_size

Normalisation rules (apply identically to both datasets):
- Lowercase everything
- Strip all punctuation (hyphens, apostrophes, commas, periods, etc.)
- Expand common abbreviations: jc → juice, sm → smoothie
- Standardise size format: remove spaces between number and unit (e.g. \
"330 ml" → "330ml", "1 L" → "1000ml", "1l" → "1000ml")
- Use "unknown" for any missing or null value
- Consistency is more important than perfection — apply the same rules to \
both sides

Return **only** a JSON object with this exact schema (no markdown fences, \
no prose):

{{"gt_keys": [{{"row_index": 0, "key": "brand | product_name | 330ml"}}], \
"gen_keys": [{{"row_index": 0, "key": "brand | product_name | 330ml"}}]}}

Every row must appear exactly once.  row_index is the 0-based position in \
the list above."""


# ---------------------------------------------------------------------------
# JSON cleaning
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

def normalise_keys(
    gt_rows: list[dict],
    gen_rows: list[dict],
    api_key: str,
) -> dict:
    """
    Call 1: ask Sonnet to produce normalised keys for every SKU in both
    datasets.

    Returns:
        {"gt_keys": [{"row_index": int, "key": str}, ...],
         "gen_keys": [{"row_index": int, "key": str}, ...]}
    """
    client = Anthropic(api_key=api_key, timeout=_TIMEOUT)

    clean_gt = format_rows_for_claude(gt_rows)
    clean_gen = format_rows_for_claude(gen_rows)

    prompt = _USER_PROMPT_TEMPLATE.format(
        gt_count=len(clean_gt),
        gen_count=len(clean_gen),
        gt_json=json.dumps(clean_gt, indent=2, default=str),
        gen_json=json.dumps(clean_gen, indent=2, default=str),
    )

    response = client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw_text = response.content[0].text
    return _clean_json(raw_text)
