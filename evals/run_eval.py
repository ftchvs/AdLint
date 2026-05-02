from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from adlint.engine import analyze
from adlint.policy import load_policies


DECISION_LABELS = ("approved", "needs_review", "high_risk")
DECISION_ORDER = {label: index for index, label in enumerate(DECISION_LABELS)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AdLint evals.")
    parser.add_argument("dataset", help="JSONL dataset with input and expected labels.")
    parser.add_argument("--output", help="Optional JSON metrics output path.")
    parser.add_argument("--markdown-output", help="Optional Markdown metrics output path.")
    parser.add_argument(
        "--min-decision-accuracy",
        type=float,
        default=0.7,
        help="Minimum decision accuracy required for a zero exit code.",
    )
    parser.add_argument(
        "--max-review-notes",
        type=int,
        default=25,
        help="Maximum false-positive and false-negative notes to include.",
    )
    args = parser.parse_args()

    rows = _load_rows(Path(args.dataset))
    policy_categories = _policy_categories()
    results = [_score_row(row, policy_categories=policy_categories) for row in rows]
    metrics = _metrics(results, max_review_notes=args.max_review_notes)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.markdown_output:
        markdown_path = Path(args.markdown_output)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(_markdown_report(metrics), encoding="utf-8")

    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0 if metrics["decision_accuracy"] >= args.min_decision_accuracy else 1


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        if "input" not in row or "expected_decision" not in row:
            raise ValueError(f"Missing input or expected_decision at {path}:{line_number}")
        rows.append(row)
    return rows


def _score_row(
    row: dict[str, Any],
    *,
    policy_categories: dict[str, str] | None = None,
) -> dict[str, Any]:
    result = analyze(row["input"])
    policy_categories = policy_categories or _policy_categories()
    expected_policy_ids = set(row.get("expected_policy_ids", []))
    actual_policy_ids = {hit.policy_id for hit in result.policy_hits}
    expected_categories = _expected_categories(row, expected_policy_ids, policy_categories)
    actual_categories = {hit.category for hit in result.policy_hits}
    actual_policy_categories = {hit.policy_id: hit.category for hit in result.policy_hits}
    policy_evidence = {
        hit.policy_id: [evidence.to_dict() for evidence in hit.evidence]
        for hit in result.policy_hits
    }

    return {
        "id": row.get("id"),
        "expected_decision": row["expected_decision"],
        "actual_decision": result.decision,
        "decision_match": row["expected_decision"] == result.decision,
        "decision_error_type": _decision_error_type(row["expected_decision"], result.decision),
        "expected_policy_ids": sorted(expected_policy_ids),
        "actual_policy_ids": sorted(actual_policy_ids),
        "expected_categories": sorted(expected_categories),
        "actual_categories": sorted(actual_categories),
        "actual_policy_categories": dict(sorted(actual_policy_categories.items())),
        "policy_evidence": dict(sorted(policy_evidence.items())),
        "policy_true_positives": sorted(expected_policy_ids & actual_policy_ids),
        "policy_false_negatives": sorted(expected_policy_ids - actual_policy_ids),
        "policy_false_positives": sorted(actual_policy_ids - expected_policy_ids),
        "category_true_positives": sorted(expected_categories & actual_categories),
        "category_false_negatives": sorted(expected_categories - actual_categories),
        "category_false_positives": sorted(actual_categories - expected_categories),
    }


def _metrics(results: list[dict[str, Any]], *, max_review_notes: int = 25) -> dict[str, Any]:
    total = len(results)
    decision_matches = sum(1 for item in results if item["decision_match"])

    misses_by_decision: dict[str, int] = defaultdict(int)
    for item in results:
        if not item["decision_match"]:
            misses_by_decision[item["expected_decision"]] += 1

    return {
        "total_examples": total,
        "decision_accuracy": round(decision_matches / total, 3) if total else 0.0,
        "confusion_matrix": _confusion_matrix(results),
        "decision_metrics": _decision_metrics(results),
        "misses_by_expected_decision": dict(sorted(misses_by_decision.items())),
        "policy_metrics": _label_metrics(results, "expected_policy_ids", "actual_policy_ids"),
        "category_metrics": _label_metrics(results, "expected_categories", "actual_categories"),
        "review_notes": _review_notes(results, max_notes=max_review_notes),
        "results": results,
    }


def _policy_categories() -> dict[str, str]:
    return {policy.id: policy.category for policy in load_policies()}


def _expected_categories(
    row: dict[str, Any],
    expected_policy_ids: set[str],
    policy_categories: dict[str, str],
) -> set[str]:
    explicit_categories = row.get("expected_categories", [])
    if explicit_categories:
        return {str(category) for category in explicit_categories}
    return {policy_categories.get(policy_id, "unknown") for policy_id in expected_policy_ids}


def _decision_error_type(expected: str, actual: str) -> str | None:
    if expected == actual:
        return None
    expected_order = DECISION_ORDER.get(expected, -1)
    actual_order = DECISION_ORDER.get(actual, -1)
    if expected_order == -1 or actual_order == -1:
        return "mismatch"
    return "overcall" if actual_order > expected_order else "undercall"


def _decision_labels(results: list[dict[str, Any]]) -> list[str]:
    labels = set(DECISION_LABELS)
    for item in results:
        labels.add(item["expected_decision"])
        labels.add(item["actual_decision"])
    return [label for label in DECISION_LABELS if label in labels] + sorted(labels - set(DECISION_LABELS))


def _confusion_matrix(results: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    labels = _decision_labels(results)
    matrix = {expected: {actual: 0 for actual in labels} for expected in labels}
    for item in results:
        matrix[item["expected_decision"]][item["actual_decision"]] += 1
    return matrix


def _decision_metrics(results: list[dict[str, Any]]) -> dict[str, dict[str, float | int]]:
    labels = _decision_labels(results)
    matrix = _confusion_matrix(results)
    metrics: dict[str, dict[str, float | int]] = {}
    for label in labels:
        tp = matrix[label][label]
        expected_count = sum(matrix[label].values())
        actual_count = sum(matrix[expected][label] for expected in labels)
        precision = tp / actual_count if actual_count else 0.0
        recall = tp / expected_count if expected_count else 0.0
        metrics[label] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "expected_count": expected_count,
            "actual_count": actual_count,
            "true_positive_count": tp,
            "false_positive_count": actual_count - tp,
            "false_negative_count": expected_count - tp,
        }
    return metrics


def _label_metrics(
    results: list[dict[str, Any]],
    expected_key: str,
    actual_key: str,
) -> dict[str, dict[str, float | int]]:
    expected_by_label: Counter[str] = Counter()
    actual_by_label: Counter[str] = Counter()
    true_positive_by_label: Counter[str] = Counter()
    false_positive_by_label: Counter[str] = Counter()
    false_negative_by_label: Counter[str] = Counter()

    for item in results:
        expected = set(item[expected_key])
        actual = set(item[actual_key])
        for label in expected:
            expected_by_label[label] += 1
        for label in actual:
            actual_by_label[label] += 1
        for label in expected & actual:
            true_positive_by_label[label] += 1
        for label in actual - expected:
            false_positive_by_label[label] += 1
        for label in expected - actual:
            false_negative_by_label[label] += 1

    label_metrics: dict[str, dict[str, float | int]] = {}
    for label in sorted(set(expected_by_label) | set(actual_by_label)):
        tp = true_positive_by_label[label]
        precision = tp / actual_by_label[label] if actual_by_label[label] else 0.0
        recall = tp / expected_by_label[label] if expected_by_label[label] else 0.0
        label_metrics[label] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "expected_count": expected_by_label[label],
            "actual_count": actual_by_label[label],
            "true_positive_count": tp,
            "false_positive_count": false_positive_by_label[label],
            "false_negative_count": false_negative_by_label[label],
        }
    return label_metrics


def _review_notes(results: list[dict[str, Any]], *, max_notes: int = 25) -> dict[str, list[dict[str, Any]]]:
    decision_mismatches: list[dict[str, Any]] = []
    false_positives: list[dict[str, Any]] = []
    false_negatives: list[dict[str, Any]] = []

    for item in results:
        if not item["decision_match"] and len(decision_mismatches) < max_notes:
            decision_mismatches.append(
                {
                    "type": "decision_mismatch",
                    "row_id": item["id"],
                    "expected_decision": item["expected_decision"],
                    "actual_decision": item["actual_decision"],
                    "decision_error_type": item["decision_error_type"],
                    "note": "Review whether scoring thresholds or the benchmark decision label need adjustment.",
                }
            )

        for policy_id in item["policy_false_positives"]:
            if len(false_positives) >= max_notes:
                break
            false_positives.append(
                {
                    "type": "policy_false_positive",
                    "row_id": item["id"],
                    "policy_id": policy_id,
                    "category": item["actual_policy_categories"].get(policy_id, "unknown"),
                    "evidence": item["policy_evidence"].get(policy_id, []),
                    "note": "Actual hit is not in expected_policy_ids; review whether the rule is overbroad or the benchmark label is incomplete.",
                }
            )

        for policy_id in item["policy_false_negatives"]:
            if len(false_negatives) >= max_notes:
                break
            false_negatives.append(
                {
                    "type": "policy_false_negative",
                    "row_id": item["id"],
                    "policy_id": policy_id,
                    "note": "Expected policy did not fire; review whether the rule needs a signal or the benchmark label is too broad.",
                }
            )

    return {
        "decision_mismatches": decision_mismatches,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def _markdown_report(metrics: dict[str, Any]) -> str:
    lines = [
        "# AdLint Eval Report",
        "",
        f"- Total examples: {metrics['total_examples']}",
        f"- Decision accuracy: {metrics['decision_accuracy']:.3f}",
        "",
        "## Confusion Matrix",
        "",
    ]
    labels = list(metrics["confusion_matrix"].keys())
    lines.append("| Expected \\ Actual | " + " | ".join(labels) + " |")
    lines.append("| --- | " + " | ".join("---" for _ in labels) + " |")
    for expected, actual_counts in metrics["confusion_matrix"].items():
        counts = [str(actual_counts.get(actual, 0)) for actual in labels]
        lines.append("| " + expected + " | " + " | ".join(counts) + " |")

    lines.extend(["", "## Review Notes", ""])
    notes = metrics["review_notes"]
    for heading, key in (
        ("Decision Mismatches", "decision_mismatches"),
        ("False Positives", "false_positives"),
        ("False Negatives", "false_negatives"),
    ):
        lines.extend([f"### {heading}", ""])
        if not notes[key]:
            lines.append("- None in the included note window.")
            lines.append("")
            continue
        for note in notes[key]:
            label = note.get("policy_id") or note.get("decision_error_type")
            lines.append(f"- `{note['row_id']}` `{label}`: {note['note']}")
        lines.append("")

    lines.extend(
        [
            "This benchmark is decision-support regression coverage for AdLint's policy-as-code engine.",
            "It is not a legal compliance certification or platform approval guarantee.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
