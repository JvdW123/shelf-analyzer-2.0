"""
accuracy_tester/scorer.py

Result parser — parses the structured JSON returned by Claude Call 1
(semantic_scorer.py) into a Python dict, with robust cleaning to handle
markdown fences and any preamble text Claude may occasionally include.
"""

from __future__ import annotations

import json
import re


def parse_semantic_result(raw: str) -> dict:
    """
    Parse the raw string response from Claude Call 1 into a Python dict.

    Handles common Claude response artefacts:
    - Markdown code fences  (```json ... ``` or ``` ... ```)
    - Leading/trailing whitespace and blank lines
    - Preamble text before the first '{'
    - Trailing prose after the closing '}'

    Args:
        raw: Raw string from the Claude API response (text blocks concatenated).

    Returns:
        Parsed dict with keys: section1, section2, section3, section4,
        section5, section6.

    Raises:
        ValueError: If no valid JSON object can be extracted from the response.
    """
    text = raw.strip()

    # Try to strip markdown code fences first (```json\n{...}\n``` pattern)
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()
    else:
        # No fences — find the outermost JSON object by locating the first '{'
        # and the matching last '}', discarding any surrounding prose.
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError(
                f"No JSON object found in Claude response. "
                f"First 300 chars: {raw[:300]!r}"
            )
        text = text[start : end + 1]

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Claude returned invalid JSON after cleaning: {exc}. "
            f"First 500 chars of extracted text: {text[:500]!r}"
        ) from exc


def get_flagged_table(result: dict) -> list[dict]:
    """
    Extract Section 6 as a flat list of dicts for tabular display.

    Args:
        result: Parsed dict from parse_semantic_result().

    Returns:
        List of dicts with keys: sku_id, field, gt_value, generated_value,
        severity. Returns an empty list if section6 is absent or empty.
    """
    return result.get("section6", [])
