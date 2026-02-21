"""
accuracy_tester/diagnostics.py

Claude diagnostic calls for the Accuracy Tester.

Two modes — chosen via the UI toggle:
  - Quick Diagnosis  → claude-sonnet-4-6, no extended thinking, fast + cheap
  - Deep Diagnosis   → claude-opus-4-6, extended thinking enabled, thorough

Neither call involves images. Both receive:
  - The accuracy score report (overall + per-column)
  - The full error table (every wrong field in every matched row)
  - A list of unmatched rows (missed or hallucinated SKUs)
  - The ground truth Excel data (as structured text)
  - The generated Excel data (as structured text)

The prompt asks Claude to:
  1. Identify the most common error patterns across fields
  2. Hypothesise WHY those errors are happening (prompt issue? image quality?
     ambiguous products? schema gaps?)
  3. Give concrete, actionable improvement suggestions

Cost notes:
  - Sonnet: fast, cheap — good for iterating
  - Opus extended thinking: expensive — only on manual trigger
"""

from __future__ import annotations

import json
import streamlit as st
from anthropic import Anthropic

from accuracy_tester.scorer import ScoreReport
from accuracy_tester.comparator import ComparisonResult

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

QUICK_MODEL = "claude-sonnet-4-6"
DEEP_MODEL = "claude-opus-4-6"

DEEP_THINKING_CONFIG = {
    "type": "enabled",
    "budget_tokens": 8000,
}

QUICK_MAX_TOKENS = 4096
DEEP_MAX_TOKENS = 16000

# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are a senior machine-learning diagnostic engineer specialising in \
document-understanding and structured data extraction systems. \
You help teams understand why an AI shelf-analysis pipeline makes \
systematic errors and how to fix them.

Your analysis must be:
- Evidence-based: cite specific examples from the error table
- Pattern-oriented: group errors by type rather than listing them one by one
- Actionable: every finding should end with a concrete improvement suggestion
  (prompt change, schema clarification, model setting, etc.)
- Concise: no padding or filler text
"""


def _build_diagnostic_prompt(
    score_report: ScoreReport,
    comparison: ComparisonResult,
    error_table: list[dict],
) -> str:
    """Assemble the diagnostic prompt sent to Claude."""
    summary = score_report.as_summary_dict()

    # Serialise score summary
    score_block = json.dumps(summary, indent=2, default=str)

    # Serialise error table (cap at 200 rows to avoid token bloat)
    error_sample = error_table[:200]
    error_block = json.dumps(error_sample, indent=2, default=str)

    # Unmatched rows
    unmatched_gt_block = json.dumps(
        [
            {k: v for k, v in row.items() if v is not None}
            for row in comparison.unmatched_gt[:50]
        ],
        indent=2,
        default=str,
    )
    unmatched_gen_block = json.dumps(
        [
            {k: v for k, v in row.items() if v is not None}
            for row in comparison.unmatched_gen[:50]
        ],
        indent=2,
        default=str,
    )

    prompt = f"""
You are reviewing the accuracy of an AI shelf-analysis pipeline that reads \
supermarket shelf photos and outputs structured product data.

## 1. Accuracy Score Summary
{score_block}

## 2. Field-Level Error Table
Each entry is one wrong field in one matched SKU row.
(Showing up to 200 errors out of {len(error_table)} total.)
{error_block}

## 3. Unmatched Ground-Truth Rows (SKUs in GT but NOT found by the pipeline)
These represent missed detections — the pipeline failed to identify these products.
{unmatched_gt_block}

## 4. Unmatched Generated Rows (SKUs found by pipeline but NOT in ground truth)
These represent hallucinations or duplicates — the pipeline invented these rows.
{unmatched_gen_block}

---

## Your Task

Please provide a structured diagnostic report with the following sections:

### A. Error Pattern Summary
List the top error patterns you see (e.g. "Brand names frequently truncated", \
"Facings systematically undercounted", "HPP treatment always null when ground truth \
has a value"). For each pattern, state:
- What field(s) are affected
- How many errors relate to this pattern
- Example GT value vs. generated value

### B. Root Cause Hypotheses
For each major pattern, hypothesise the most likely root cause:
- Is this a prompt ambiguity? (What in the prompt might be misleading?)
- Is this an image quality / visibility issue?
- Is this a schema gap? (Is the allowed value list incomplete or unclear?)
- Is this a model reasoning limitation?

### C. Improvement Recommendations
For each root cause, give a specific, actionable recommendation:
- Exact prompt wording to add/change
- Schema or allowed-values change
- Photo capture guidance for the field team
- Other pipeline change

### D. Overall Health Assessment
One paragraph: is this pipeline ready for production use, or does it need \
significant improvement? What are the 1-2 highest-priority fixes?
""".strip()

    return prompt


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_quick_diagnosis(
    score_report: ScoreReport,
    comparison: ComparisonResult,
    error_table: list[dict],
    api_key: str,
) -> str:
    """
    Run a quick diagnosis using claude-sonnet-4-6 (no extended thinking).

    Args:
        score_report: Output from scorer.score()
        comparison:   Output from comparator.compare()
        error_table:  Output from scorer.get_error_table()
        api_key:      Anthropic API key (from st.secrets)

    Returns:
        Diagnostic text as a string.
    """
    client = Anthropic(api_key=api_key, timeout=120.0)
    prompt = _build_diagnostic_prompt(score_report, comparison, error_table)

    response = client.messages.create(
        model=QUICK_MODEL,
        max_tokens=QUICK_MAX_TOKENS,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


def run_deep_diagnosis(
    score_report: ScoreReport,
    comparison: ComparisonResult,
    error_table: list[dict],
    api_key: str,
) -> str:
    """
    Run a deep diagnosis using claude-opus-4-6 with Extended Thinking.

    This call is expensive — only trigger when the user explicitly requests it.

    Args:
        score_report: Output from scorer.score()
        comparison:   Output from comparator.compare()
        error_table:  Output from scorer.get_error_table()
        api_key:      Anthropic API key (from st.secrets)

    Returns:
        Diagnostic text as a string (thinking blocks are discarded).
    """
    client = Anthropic(api_key=api_key, timeout=300.0)
    prompt = _build_diagnostic_prompt(score_report, comparison, error_table)

    response = client.messages.create(
        model=DEEP_MODEL,
        max_tokens=DEEP_MAX_TOKENS,
        thinking=DEEP_THINKING_CONFIG,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    # Discard thinking blocks — return only the final text response
    text_parts = [
        block.text
        for block in response.content
        if block.type == "text"
    ]
    return "\n\n".join(text_parts)
