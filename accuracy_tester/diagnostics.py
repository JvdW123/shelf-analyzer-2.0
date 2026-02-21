"""
accuracy_tester/diagnostics.py

Call 2 of the two-call accuracy evaluation pipeline.

Receives the structured JSON produced by Call 1 (semantic_scorer.py) and
generates a human-readable diagnostic narrative covering:
  - Error pattern summary
  - Root cause hypotheses
  - Improvement recommendations
  - Overall health assessment

Two modes — controlled by the Deep Diagnosis toggle in the UI:
  - Quick (default): claude-sonnet-4-6, no extended thinking — fast + cheap
  - Deep:            claude-opus-4-6, extended thinking (8000 token budget)

Note: Call 1 (semantic matching + scoring) always uses Opus + Extended Thinking
regardless of this setting. The Deep toggle here applies only to this narrative
call.
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

_SYSTEM_PROMPT = """\
You are a senior machine-learning diagnostic engineer specialising in \
document-understanding and structured data extraction systems. \
You help teams understand why an AI shelf-analysis pipeline makes \
systematic errors and how to fix them.

Your analysis must be:
- Evidence-based: cite specific examples from the scored results
- Pattern-oriented: group errors by type rather than listing them one by one
- Actionable: every finding should end with a concrete improvement suggestion
  (prompt change, schema clarification, model setting, etc.)
- Concise: no padding or filler text
"""

# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_narrative_prompt(semantic_result: dict) -> str:
    """Build the Call 2 prompt from the structured scoring JSON."""
    result_block = json.dumps(semantic_result, indent=2, default=str)

    return f"""\
You are reviewing the accuracy results of an AI shelf-analysis pipeline \
that reads supermarket shelf photos and outputs structured product data.

## Accuracy Results (from semantic scoring — Call 1)

{result_block}

---

## Your Task

Produce a structured diagnostic report with the following sections:

### A. Error Pattern Summary
List the top error patterns across all 6 sections. For each pattern, state:
- Which section and field(s) are affected
- How many errors relate to this pattern
- Representative ground truth value vs generated value examples

### B. Root Cause Hypotheses
For each major pattern, hypothesise the most likely root cause:
- Prompt ambiguity — what wording might be misleading?
- Image quality / visibility limitations
- Schema gap — is the allowed-values list incomplete or unclear?
- Model reasoning limitation

### C. Improvement Recommendations
For each root cause, give a specific actionable recommendation:
- Exact prompt wording to add or change
- Schema or allowed-values change
- Photo capture guidance for the field team
- Other pipeline change

### D. Overall Health Assessment
One paragraph: is this pipeline ready for production use? \
What are the 1–2 highest-priority fixes?""".strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_narrative_diagnosis(
    semantic_result: dict,
    api_key: str,
    deep: bool = False,
) -> str:
    """
    Call 2: generate a human-readable narrative from the structured scoring JSON.

    Args:
        semantic_result: Parsed dict from semantic_scorer.run_semantic_scoring()
        api_key:         Anthropic API key (from st.secrets)
        deep:            If True, use Opus + Extended Thinking; else use Sonnet.

    Returns:
        Diagnostic narrative as a plain string.
    """
    client = Anthropic(api_key=api_key, timeout=300.0)
    prompt = _build_narrative_prompt(semantic_result)

    if deep:
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
    else:
        response = client.messages.create(
            model=QUICK_MODEL,
            max_tokens=QUICK_MAX_TOKENS,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
