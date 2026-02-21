"""
accuracy_tester/scorer.py

Calculates accuracy scores from a ComparisonResult.

## Scoring rules
- A field is "correct" if FieldResult.match is True
- A field is "skipped" if FieldResult.both_null is True
  (both sides are None/empty — we don't penalise for mutually unknown values)
- A field is "wrong" if match is False (regardless of which side is None)
- Unmatched GT rows count as entirely wrong (all comparable fields = miss)
- Unmatched generated rows are noted but do NOT affect the score (they are
  hallucinated rows, which is a separate concern from field accuracy)

## Output
score() returns a ScoreReport dataclass with:
  - per_column: dict[column_key → ColumnScore]
  - overall_score: float (0–100)
  - matched_count: number of matched row pairs
  - unmatched_gt_count: GT rows with no match
  - unmatched_gen_count: generated rows with no match
  - total_gt_rows: total rows in ground truth
"""

from __future__ import annotations

from dataclasses import dataclass, field

from accuracy_tester.comparator import ComparisonResult


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ColumnScore:
    """Accuracy statistics for a single column."""
    column_key: str
    column_name: str
    correct: int = 0       # matched pairs where field was correct
    wrong: int = 0         # matched pairs where field was wrong
    skipped: int = 0       # both_null cases (excluded from denominator)
    missed: int = 0        # unmatched GT rows (treated as wrong)

    @property
    def total_scored(self) -> int:
        """Denominator: correct + wrong + missed."""
        return self.correct + self.wrong + self.missed

    @property
    def accuracy_pct(self) -> float:
        """Accuracy percentage (0–100). Returns 0 if no scored rows."""
        if self.total_scored == 0:
            return 0.0
        return round(self.correct / self.total_scored * 100, 1)


@dataclass
class ScoreReport:
    """Full accuracy report produced by score()."""
    per_column: dict[str, ColumnScore] = field(default_factory=dict)
    overall_score: float = 0.0
    matched_count: int = 0
    unmatched_gt_count: int = 0
    unmatched_gen_count: int = 0
    total_gt_rows: int = 0

    def as_summary_dict(self) -> dict:
        """Return a flat dict for display or passing to Claude."""
        summary = {
            "overall_accuracy_pct": self.overall_score,
            "matched_rows": self.matched_count,
            "unmatched_gt_rows": self.unmatched_gt_count,
            "unmatched_generated_rows": self.unmatched_gen_count,
            "total_ground_truth_rows": self.total_gt_rows,
            "per_column": {
                k: {
                    "column_name": v.column_name,
                    "accuracy_pct": v.accuracy_pct,
                    "correct": v.correct,
                    "wrong": v.wrong,
                    "missed": v.missed,
                    "skipped_both_null": v.skipped,
                }
                for k, v in self.per_column.items()
            },
        }
        return summary


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------

def score(comparison: ComparisonResult) -> ScoreReport:
    """
    Calculate accuracy scores from a ComparisonResult.

    Args:
        comparison: Output from comparator.compare()

    Returns:
        ScoreReport with per-column and overall accuracy.
    """
    report = ScoreReport(
        matched_count=len(comparison.matched_pairs),
        unmatched_gt_count=len(comparison.unmatched_gt),
        unmatched_gen_count=len(comparison.unmatched_gen),
        total_gt_rows=(
            len(comparison.matched_pairs)
            + len(comparison.unmatched_gt)
        ),
    )

    # Initialise a ColumnScore for each comparable column
    for col_spec in comparison.comparable_columns:
        report.per_column[col_spec["key"]] = ColumnScore(
            column_key=col_spec["key"],
            column_name=col_spec["name"],
        )

    # --- Score matched pairs ---
    for pair in comparison.matched_pairs:
        for key, field_result in pair.fields.items():
            col_score = report.per_column.get(key)
            if col_score is None:
                continue
            if field_result.both_null:
                col_score.skipped += 1
            elif field_result.match:
                col_score.correct += 1
            else:
                col_score.wrong += 1

    # --- Penalise unmatched GT rows: every field counts as missed ---
    for _row in comparison.unmatched_gt:
        for col_score in report.per_column.values():
            col_score.missed += 1

    # --- Calculate overall score ---
    # Weighted average over all columns (equal weight per column)
    scored_columns = [cs for cs in report.per_column.values() if cs.total_scored > 0]
    if scored_columns:
        report.overall_score = round(
            sum(cs.accuracy_pct for cs in scored_columns) / len(scored_columns),
            1,
        )
    else:
        report.overall_score = 0.0

    return report


def get_error_table(comparison: ComparisonResult) -> list[dict]:
    """
    Build a flat list of all field-level errors for display as a table.

    Each entry represents one incorrect field in one matched row pair.
    Returns an empty list if there are no errors.

    Each dict has keys:
        row_key, column_name, ground_truth, generated, match_type, fuzzy_score
    """
    errors = []
    for pair in comparison.matched_pairs:
        for key, field_result in pair.fields.items():
            if not field_result.match and not field_result.both_null:
                errors.append({
                    "row_key": pair.match_key,
                    "match_type": pair.match_type,
                    "fuzzy_score": round(pair.fuzzy_score, 3),
                    "column_name": field_result.column_name,
                    "ground_truth": field_result.ground_truth_value,
                    "generated": field_result.generated_value,
                })
    return errors
