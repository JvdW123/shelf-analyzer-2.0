"""
accuracy_tester/diagnostics.py

Component 4 — Diagnostic narrative.

Receives the full scored JSON from Components 2 and 3 plus original GT and
generated row lists, and produces a human-readable diagnostic report.

Two modes:
  - deep=False: Sonnet 4.6, no Extended Thinking (fast + cheap)
  - deep=True:  Opus 4.6, Extended Thinking budget_tokens=8000
"""

from __future__ import annotations

import json

from anthropic import Anthropic

# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

QUICK_MODEL = "claude-sonnet-4-6"
DEEP_MODEL = "claude-opus-4-6"

QUICK_MAX_TOKENS = 4096
DEEP_MAX_TOKENS = 16000

DEEP_THINKING_CONFIG = {
    "type": "enabled",
    "budget_tokens": 8000,
}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

DIAGNOSTIC_SYSTEM_PROMPT = """\
You are a diagnostic engineer specialising in AI-based retail shelf analysis \
pipelines. The pipeline sends shelf photos to Claude Vision, which extracts \
SKU-level data: brand, product name, flavor, facings, price, packaging size, \
shelf level, product type, private label status, and extraction/processing \
methods. You will receive a structured accuracy report. Your job is to \
diagnose why the pipeline is making errors and what should change.

Analyse across exactly these four dimensions:

1. SYSTEMATIC ERROR PATTERNS
- Which fields have the lowest accuracy and what do they have in common?
- Are errors concentrated on specific SKUs, shelf levels, or product types?
- Are missed SKUs clustered (e.g. all on one shelf level) or random?
- Are hallucinated SKUs plausible products or completely fabricated?

2. ROOT CAUSE HYPOTHESES
For each error pattern identify the most likely cause. Be specific — not \
"the prompt could be clearer" but "the prompt does not define what counts \
as one facing for multipacks, causing Claude to count units instead of \
facings." Categorise each cause as one of:
- Photo quality or angle (overview vs. close-up)
- Prompt ambiguity or missing instruction
- Schema definition unclear
- Model limitation (genuinely hard to extract from image)
- Edge case not covered (multipack, promotional pricing, shelf talker \
obscuring label)

3. IMPROVEMENT RECOMMENDATIONS
Rank by expected impact. For each recommendation use this exact format:
Finding: [the error pattern]
Hypothesis: [why it is happening]
Recommendation: [exactly what to change — prompt wording, schema definition, \
photo instructions, or model setting]
How to verify: [which accuracy score should improve and by how much if the \
fix works]

4. NEXT TEST PRIORITIES
Which 2-3 specific shelf types or scenarios should be tested next to confirm \
these hypotheses?

Rules: cite specific fields, SKU counts, and percentages. Do not restate \
numbers without interpreting them. No filler. If accuracy is uniformly high \
with no meaningful patterns, say so in one sentence."""

# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_narrative_prompt(
    scored_result: dict,
    gt_rows: list[dict],
    gen_rows: list[dict],
) -> str:
    """Build the Call 3 prompt from scored results and original row data."""
    result_block = json.dumps(scored_result, indent=2, default=str)
    gt_block = json.dumps(gt_rows, indent=2, default=str)
    gen_block = json.dumps(gen_rows, indent=2, default=str)

    return f"""\
## Accuracy Results (from deterministic scoring + semantic scoring)

{result_block}

---

## Reference Data

### Ground Truth SKUs ({len(gt_rows)} rows)
{gt_block}

### Generated SKUs ({len(gen_rows)} rows)
{gen_block}

---

Produce your diagnostic report following the four dimensions in your \
system prompt.""".strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_narrative_diagnosis(
    scored_result: dict,
    gt_rows: list[dict],
    gen_rows: list[dict],
    api_key: str,
    deep: bool = False,
) -> str:
    """
    Call 3: generate a human-readable diagnostic narrative.

    Args:
        scored_result: Combined dict from scorer + semantic_scorer.
        gt_rows:       Original ground-truth row dicts.
        gen_rows:      Original generated row dicts.
        api_key:       Anthropic API key.
        deep:          If True, use Opus + Extended Thinking; else Sonnet.

    Returns:
        Diagnostic narrative as a plain string.
    """
    client = Anthropic(api_key=api_key, timeout=300.0)
    prompt = _build_narrative_prompt(scored_result, gt_rows, gen_rows)

    if deep:
        response = client.messages.create(
            model=DEEP_MODEL,
            max_tokens=DEEP_MAX_TOKENS,
            thinking=DEEP_THINKING_CONFIG,
            system=DIAGNOSTIC_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text_parts = [
            block.text
            for block in response.content
            if block.type == "text"
        ]
        return "\n\n".join(text_parts)
    else:
        response = client.messages.create(
            model=QUICK_MODEL,
            max_tokens=QUICK_MAX_TOKENS,
            system=DIAGNOSTIC_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
