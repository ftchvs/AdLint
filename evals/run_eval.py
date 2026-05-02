from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from adlint.classifiers.ollama import classify_with_ollama
from adlint.engine import analyze
from adlint.models import PolicyHit, Submission
from adlint.policy import load_policies
from adlint.scoring.core import decision_for_score, score_hits


DECISION_LABELS = ("approved", "needs_review", "high_risk")
DECISION_ORDER = {label: index for index, label in enumerate(DECISION_LABELS)}


class _EvalResult:
    def __init__(self, *, decision: str, policy_hits: list[PolicyHit], model: dict[str, Any]) -> None:
        self.decision = decision
        self.policy_hits = policy_hits
        self.model = model


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AdLint evals.")
    parser.add_argument("dataset", help="JSONL dataset with input and expected labels.")
    parser.add_argument(
        "--mode",
        choices=("rule-only", "model-only", "hybrid", "all"),
        default="rule-only",
        help="Evaluation mode. Model-only is eval-only and never used by production scan.",
    )
    parser.add_argument("--output", help="Optional JSON metrics output path.")
    parser.add_argument("--markdown-output", help="Optional Markdown metrics output path.")
    parser.add_argument("--ollama-model", help="Ollama model name for model-only or hybrid evals.")
    parser.add_argument(
        "--require-model",
        action="store_true",
        help="Fail when model-only or hybrid rows cannot run the requested local model.",
    )
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
    if args.mode == "all":
        metrics = {
            "mode": "all",
            "modes": {
                mode: _run_eval(
                    rows,
                    mode=mode,
                    ollama_model=args.ollama_model,
                    max_review_notes=args.max_review_notes,
                )
                for mode in ("rule-only", "model-only", "hybrid")
            },
        }
    else:
        metrics = _run_eval(
            rows,
            mode=args.mode,
            ollama_model=args.ollama_model,
            max_review_notes=args.max_review_notes,
        )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.markdown_output:
        markdown_path = Path(args.markdown_output)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(_markdown_report(metrics), encoding="utf-8")

    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0 if _passes(metrics, min_accuracy=args.min_decision_accuracy, require_model=args.require_model) else 1


def _run_eval(
    rows: list[dict[str, Any]],
    *,
    mode: str = "rule-only",
    ollama_model: str | None = None,
    max_review_notes: int = 25,
) -> dict[str, Any]:
    policy_categories = _policy_categories()
    results = [
        _score_row(row, policy_categories=policy_categories, mode=mode, ollama_model=ollama_model)
        for row in rows
    ]
    metrics = _metrics(results, max_review_notes=max_review_notes)
    metrics["mode"] = mode
    return metrics


def _passes(metrics: dict[str, Any], *, min_accuracy: float, require_model: bool) -> bool:
    if metrics.get("mode") == "all":
        return all(
            _passes(mode_metrics, min_accuracy=min_accuracy, require_model=require_model)
            for mode_metrics in metrics["modes"].values()
        )
    if require_model and metrics.get("model_required_failures"):
        return False
    if metrics["total_examples"] == 0:
        return not require_model
    return metrics["decision_accuracy"] >= min_accuracy


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
    mode: str = "rule-only",
    ollama_model: str | None = None,
) -> dict[str, Any]:
    policy_categories = policy_categories or _policy_categories()
    if mode == "model-only":
        scored = _score_model_only(row, ollama_model=ollama_model)
    else:
        scored = _score_analyze(row, mode=mode, ollama_model=ollama_model)

    if scored.get("skipped"):
        return scored

    result = scored["result"]
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
        "mode": mode,
        "expected_decision": row["expected_decision"],
        "actual_decision": result.decision,
        "decision_match": row["expected_decision"] == result.decision,
        "decision_error_type": _decision_error_type(row["expected_decision"], result.decision),
        "expected_policy_ids": sorted(expected_policy_ids),
        "actual_policy_ids": sorted(actual_policy_ids),
        "expected_categories": sorted(expected_categories),
        "actual_categories": sorted(actual_categories),
        "actual_policy_categories": dict(sorted(actual_policy_categories.items())),
        "model": result.model,
        "policy_evidence": dict(sorted(policy_evidence.items())),
        "policy_true_positives": sorted(expected_policy_ids & actual_policy_ids),
        "policy_false_negatives": sorted(expected_policy_ids - actual_policy_ids),
        "policy_false_positives": sorted(actual_policy_ids - expected_policy_ids),
        "category_true_positives": sorted(expected_categories & actual_categories),
        "category_false_negatives": sorted(expected_categories - actual_categories),
        "category_false_positives": sorted(actual_categories - expected_categories),
    }


def _score_analyze(row: dict[str, Any], *, mode: str, ollama_model: str | None) -> dict[str, Any]:
    result = analyze(
        row["input"],
        enable_model=True if mode == "hybrid" else False,
        ollama_model=ollama_model,
    )
    return {"result": result}


def _score_model_only(row: dict[str, Any], *, ollama_model: str | None) -> dict[str, Any]:
    submission = Submission.from_dict(row["input"])
    model_hits, model_info = classify_with_ollama(submission, model=ollama_model)
    if model_info.get("status") != "ok":
        return {
            "id": row.get("id"),
            "mode": "model-only",
            "skipped": True,
            "skip_reason": model_info.get("reason") or model_info.get("status"),
            "model": model_info,
        }

    risk_score = score_hits(model_hits, submission)
    return {
        "result": _EvalResult(
            decision=decision_for_score(risk_score),
            policy_hits=model_hits,
            model=model_info,
        )
    }


def _metrics(results: list[dict[str, Any]], *, max_review_notes: int = 25) -> dict[str, Any]:
    scored_results = [item for item in results if not item.get("skipped")]
    skipped_results = [item for item in results if item.get("skipped")]
    total = len(scored_results)
    decision_matches = sum(1 for item in scored_results if item["decision_match"])

    misses_by_decision: dict[str, int] = defaultdict(int)
    for item in scored_results:
        if not item["decision_match"]:
            misses_by_decision[item["expected_decision"]] += 1

    return {
        "input_examples": len(results),
        "total_examples": total,
        "skipped_examples": len(skipped_results),
        "decision_accuracy": round(decision_matches / total, 3) if total else 0.0,
        "confusion_matrix": _confusion_matrix(scored_results),
        "decision_metrics": _decision_metrics(scored_results),
        "misses_by_expected_decision": dict(sorted(misses_by_decision.items())),
        "policy_metrics": _label_metrics(scored_results, "expected_policy_ids", "actual_policy_ids"),
        "category_metrics": _label_metrics(scored_results, "expected_categories", "actual_categories"),
        "model_status_counts": _model_status_counts(results),
        "model_required_failures": _model_required_failures(results),
        "review_notes": _review_notes(scored_results, max_notes=max_review_notes),
        "results": results,
    }


def _policy_categories() -> dict[str, str]:
    return {policy.id: policy.category for policy in load_policies()}


def _model_status_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in results:
        model_info = item.get("model")
        if not model_info:
            continue
        counts[str(model_info.get("status", "unknown"))] += 1
    return dict(sorted(counts.items()))


def _model_required_failures(results: list[dict[str, Any]]) -> int:
    failures = 0
    for item in results:
        model_info = item.get("model")
        if not model_info:
            continue
        status = model_info.get("status")
        if status not in {"ok", "disabled"}:
            failures += 1
    return failures


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
    if metrics.get("mode") == "all":
        lines = ["# AdLint Eval Report", ""]
        for mode, mode_metrics in metrics["modes"].items():
            lines.extend([f"## {mode}", ""])
            lines.extend(_markdown_report(mode_metrics).splitlines()[2:])
            lines.append("")
        return "\n".join(lines)

    lines = [
        "# AdLint Eval Report",
        "",
        f"- Mode: {metrics.get('mode', 'rule-only')}",
        f"- Input examples: {metrics['input_examples']}",
        f"- Total examples: {metrics['total_examples']}",
        f"- Skipped examples: {metrics['skipped_examples']}",
        f"- Decision accuracy: {metrics['decision_accuracy']:.3f}",
        f"- Model status counts: {metrics['model_status_counts']}",
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
