from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from adlint.classifiers.ollama import classify_with_ollama
from adlint.engine import analyze
from adlint.models import PolicyHit, Submission
from adlint.policy import load_policies
from adlint.scoring.core import decision_for_score, score_hits
from adlint.scrapers.landing_page import extract_landing_page


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
        "--limit",
        type=_positive_int,
        help="Limit the run to the first N dataset rows. Useful for local model smoke checks.",
    )
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
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Print a compact summary to stdout while preserving full JSON/Markdown outputs.",
    )
    parser.add_argument(
        "--summary-format",
        choices=("json", "text"),
        default="text",
        help="Summary format used with --summary-only. Text is CI-readable; JSON is deterministic and machine-readable.",
    )
    args = parser.parse_args()

    rows = _load_rows(Path(args.dataset))
    if args.limit is not None:
        rows = rows[: args.limit]
    if args.mode == "all":
        all_start = time.perf_counter()
        mode_metrics = {
            mode: _run_eval(
                rows,
                mode=mode,
                ollama_model=args.ollama_model,
                max_review_notes=args.max_review_notes,
            )
            for mode in ("rule-only", "model-only", "hybrid")
        }
        metrics = {
            "mode": "all",
            "modes": mode_metrics,
            "hybrid_value": _hybrid_value_metrics(mode_metrics, max_review_notes=args.max_review_notes),
            "elapsed_seconds": round(time.perf_counter() - all_start, 3),
        }
    else:
        metrics = _run_eval(
            rows,
            mode=args.mode,
            ollama_model=args.ollama_model,
            max_review_notes=args.max_review_notes,
        )
    _attach_dataset(metrics, args.dataset)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.markdown_output:
        markdown_path = Path(args.markdown_output)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(_markdown_report(metrics), encoding="utf-8")

    if args.summary_only:
        print(
            _summary_report(
                metrics,
                json_output=args.output,
                markdown_output=args.markdown_output,
                summary_format=args.summary_format,
            )
        )
    else:
        print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0 if _passes(metrics, min_accuracy=args.min_decision_accuracy, require_model=args.require_model) else 1


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _run_eval(
    rows: list[dict[str, Any]],
    *,
    mode: str = "rule-only",
    ollama_model: str | None = None,
    max_review_notes: int = 25,
) -> dict[str, Any]:
    start = time.perf_counter()
    policy_categories = _policy_categories()
    results = [
        _score_row(row, policy_categories=policy_categories, mode=mode, ollama_model=ollama_model)
        for row in rows
    ]
    metrics = _metrics(results, max_review_notes=max_review_notes)
    metrics["mode"] = mode
    metrics["elapsed_seconds"] = round(time.perf_counter() - start, 3)
    return metrics


def _attach_dataset(metrics: dict[str, Any], dataset: str) -> None:
    metrics["dataset"] = dataset
    if metrics.get("mode") == "all":
        for mode_metrics in metrics.get("modes", {}).values():
            if isinstance(mode_metrics, dict):
                _attach_dataset(mode_metrics, dataset)


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


def _summary_report(
    metrics: dict[str, Any],
    *,
    json_output: str | None = None,
    markdown_output: str | None = None,
    summary_format: str = "json",
) -> str:
    summary = _compact_summary(metrics, json_output=json_output, markdown_output=markdown_output)
    if summary_format == "json":
        return json.dumps(summary, sort_keys=True)

    lines = ["AdLint eval summary"]
    if summary.get("mode") == "all":
        lines.extend(_summary_lines(summary, include_review_rows=False))
        for mode, mode_summary in summary["modes"].items():
            lines.append("")
            lines.extend(f"{mode}.{line}" for line in _summary_lines(mode_summary))
    else:
        lines.extend(_summary_lines(summary))
    outputs = summary.get("outputs", {})
    lines.append(f"json_output: {outputs.get('json') or '<none>'}")
    lines.append(f"markdown_output: {outputs.get('markdown') or '<none>'}")
    return "\n".join(lines)


def _compact_summary(
    metrics: dict[str, Any],
    *,
    json_output: str | None = None,
    markdown_output: str | None = None,
) -> dict[str, Any]:
    if metrics.get("mode") == "all":
        return {
            "summary_version": 1,
            "dataset": metrics.get("dataset", "<unknown>"),
            "mode": "all",
            "elapsed_seconds": metrics.get("elapsed_seconds", 0),
            "modes": {
                mode: _compact_summary(mode_metrics)
                for mode, mode_metrics in sorted(metrics.get("modes", {}).items())
            },
            "outputs": {
                "json": json_output,
                "markdown": markdown_output,
            },
        }

    review_notes = metrics.get("review_notes", {})
    return {
        "summary_version": 1,
        "dataset": metrics.get("dataset", "<unknown>"),
        "mode": metrics.get("mode", "rule-only"),
        "total_rows": int(metrics.get("input_examples", 0)),
        "scored_rows": int(metrics.get("total_examples", 0)),
        "skipped_rows": int(metrics.get("skipped_examples", 0)),
        "decision_accuracy": float(metrics.get("decision_accuracy", 0.0)),
        "decision_mismatch_count": _decision_mismatch_count(metrics),
        "confusion_matrix_deltas": _confusion_matrix_deltas(metrics),
        "policy_false_positive_count": _policy_metric_count(metrics, "false_positive_count"),
        "policy_false_negative_count": _policy_metric_count(metrics, "false_negative_count"),
        "top_review_note_row_ids": {
            "decision_mismatches": _review_note_row_ids(review_notes.get("decision_mismatches", [])),
            "policy_false_positives": _review_note_row_ids(review_notes.get("false_positives", [])),
            "policy_false_negatives": _review_note_row_ids(review_notes.get("false_negatives", [])),
        },
        "model_status_counts": dict(sorted(metrics.get("model_status_counts", {}).items())),
        "elapsed_seconds": metrics.get("elapsed_seconds", 0),
        "outputs": {
            "json": json_output,
            "markdown": markdown_output,
        },
    }


def _summary_lines(summary: dict[str, Any], *, include_review_rows: bool = True) -> list[str]:
    lines = [
        f"dataset: {summary.get('dataset', '<unknown>')}",
        f"mode: {summary.get('mode', 'rule-only')}",
        f"total_rows: {summary.get('total_rows', 0)}",
        f"scored_rows: {summary.get('scored_rows', 0)}",
        f"skipped_rows: {summary.get('skipped_rows', 0)}",
        f"decision_accuracy: {float(summary.get('decision_accuracy', 0.0)):.3f}",
        f"decision_mismatches: {summary.get('decision_mismatch_count', 0)}",
        f"policy_false_negatives: {summary.get('policy_false_negative_count', 0)}",
        f"policy_false_positives: {summary.get('policy_false_positive_count', 0)}",
        f"model_status_counts: {summary.get('model_status_counts', {})}",
        f"elapsed_seconds: {summary.get('elapsed_seconds', 0)}",
    ]
    if include_review_rows:
        rows = summary.get("top_review_note_row_ids", {})
        lines.append(f"top_decision_mismatch_rows: {rows.get('decision_mismatches', [])}")
        lines.append(f"top_policy_false_negative_rows: {rows.get('policy_false_negatives', [])}")
        lines.append(f"top_policy_false_positive_rows: {rows.get('policy_false_positives', [])}")
    return lines


def _confusion_matrix_deltas(metrics: dict[str, Any]) -> list[dict[str, int | str]]:
    matrix = metrics.get("confusion_matrix", {})
    if not isinstance(matrix, dict):
        return []
    labels = _ordered_summary_labels(matrix)
    deltas: list[dict[str, int | str]] = []
    for expected in labels:
        actual_counts = matrix.get(expected, {})
        if not isinstance(actual_counts, dict):
            continue
        for actual in labels:
            if actual == expected:
                continue
            count = int(actual_counts.get(actual, 0))
            if count:
                deltas.append({"expected": expected, "actual": actual, "count": count})
    return deltas


def _ordered_summary_labels(matrix: dict[str, Any]) -> list[str]:
    labels = set(matrix)
    for actual_counts in matrix.values():
        if isinstance(actual_counts, dict):
            labels.update(actual_counts)
    return [label for label in DECISION_LABELS if label in labels] + sorted(labels - set(DECISION_LABELS))


def _review_note_row_ids(notes: list[dict[str, Any]], *, limit: int = 5) -> list[str]:
    row_ids: list[str] = []
    seen: set[str] = set()
    for note in notes:
        row_id = str(note.get("row_id", ""))
        if not row_id or row_id in seen:
            continue
        seen.add(row_id)
        row_ids.append(row_id)
        if len(row_ids) >= limit:
            break
    return row_ids


def _review_note_counts(metrics: dict[str, Any]) -> dict[str, int]:
    return {
        "decision_mismatches": _decision_mismatch_count(metrics),
        "policy_false_negatives": _policy_metric_count(metrics, "false_negative_count"),
        "policy_false_positives": _policy_metric_count(metrics, "false_positive_count"),
    }


def _decision_mismatch_count(metrics: dict[str, Any]) -> int:
    matrix = metrics.get("confusion_matrix", {})
    mismatches = 0
    for expected, actual_counts in matrix.items():
        if not isinstance(actual_counts, dict):
            continue
        for actual, count in actual_counts.items():
            if actual != expected:
                mismatches += int(count)
    return mismatches


def _policy_metric_count(metrics: dict[str, Any], key: str) -> int:
    total = 0
    for values in metrics.get("policy_metrics", {}).values():
        if isinstance(values, dict):
            total += int(values.get(key, 0))
    return total


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
    input_payload = dict(row["input"])
    if mode == "hybrid":
        input_payload["model_affects_score"] = True
    result = analyze(
        input_payload,
        enable_model=True if mode == "hybrid" else False,
        ollama_model=ollama_model,
    )
    return {"result": result}


def _score_model_only(row: dict[str, Any], *, ollama_model: str | None) -> dict[str, Any]:
    submission = Submission.from_dict(row["input"])
    landing_page = extract_landing_page(submission.landing_page_url, submission.landing_page_html)
    model_hits, model_info = classify_with_ollama(
        submission,
        model=ollama_model,
        landing_page=landing_page,
    )
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


def _hybrid_value_metrics(
    modes: dict[str, dict[str, Any]],
    *,
    max_review_notes: int = 25,
) -> dict[str, Any]:
    rule_results = _results_by_id(modes.get("rule-only", {}))
    model_results = _results_by_id(modes.get("model-only", {}))
    hybrid_results = _results_by_id(modes.get("hybrid", {}))
    row_ids = sorted(set(rule_results) & set(hybrid_results))

    decision_improvements: list[dict[str, Any]] = []
    decision_regressions: list[dict[str, Any]] = []
    model_added_notes: list[dict[str, Any]] = []
    model_removed_notes: list[dict[str, Any]] = []

    model_ok_rows = 0
    model_unavailable_rows = 0
    decision_changed_count = 0
    model_added_policy_hit_count = 0
    model_added_expected_policy_hit_count = 0
    model_added_false_positive_policy_hit_count = 0
    model_added_generic_policy_review_count = 0
    model_added_detailed_policy_hit_count = 0
    model_added_detailed_expected_policy_hit_count = 0
    model_added_detailed_false_positive_policy_hit_count = 0
    model_removed_policy_hit_count = 0
    model_rescued_policy_false_negative_count = 0
    rows_with_model_added_findings = 0
    rows_with_model_added_expected_findings = 0
    rows_with_model_added_false_positives = 0
    rows_with_model_added_generic_review = 0
    rows_with_model_added_detailed_findings = 0

    for row_id in row_ids:
        rule = rule_results[row_id]
        hybrid = hybrid_results[row_id]
        model_status = str(hybrid.get("model", {}).get("status", "unknown"))
        if model_status == "ok":
            model_ok_rows += 1
        elif model_status not in {"disabled", "unknown"}:
            model_unavailable_rows += 1

        if rule["actual_decision"] != hybrid["actual_decision"]:
            decision_changed_count += 1
        if not rule["decision_match"] and hybrid["decision_match"]:
            decision_improvements.append(_decision_delta_note(row_id, rule, hybrid))
        if rule["decision_match"] and not hybrid["decision_match"]:
            decision_regressions.append(_decision_delta_note(row_id, rule, hybrid))

        rule_policy_ids = set(rule["actual_policy_ids"])
        hybrid_policy_ids = set(hybrid["actual_policy_ids"])
        expected_policy_ids = set(hybrid["expected_policy_ids"])
        added_policy_ids = sorted(hybrid_policy_ids - rule_policy_ids)
        removed_policy_ids = sorted(rule_policy_ids - hybrid_policy_ids)
        added_expected_policy_ids = sorted(set(added_policy_ids) & expected_policy_ids)
        added_false_positive_policy_ids = sorted(set(added_policy_ids) - expected_policy_ids)
        added_generic_policy_ids = sorted(policy_id for policy_id in added_policy_ids if policy_id == "model_policy_review")
        added_detailed_policy_ids = sorted(policy_id for policy_id in added_policy_ids if policy_id != "model_policy_review")
        added_detailed_expected_policy_ids = sorted(set(added_detailed_policy_ids) & expected_policy_ids)
        added_detailed_false_positive_policy_ids = sorted(set(added_detailed_policy_ids) - expected_policy_ids)
        rescued_policy_ids = sorted((expected_policy_ids - rule_policy_ids) & hybrid_policy_ids)

        model_added_policy_hit_count += len(added_policy_ids)
        model_added_expected_policy_hit_count += len(added_expected_policy_ids)
        model_added_false_positive_policy_hit_count += len(added_false_positive_policy_ids)
        model_added_generic_policy_review_count += len(added_generic_policy_ids)
        model_added_detailed_policy_hit_count += len(added_detailed_policy_ids)
        model_added_detailed_expected_policy_hit_count += len(added_detailed_expected_policy_ids)
        model_added_detailed_false_positive_policy_hit_count += len(added_detailed_false_positive_policy_ids)
        model_removed_policy_hit_count += len(removed_policy_ids)
        model_rescued_policy_false_negative_count += len(rescued_policy_ids)

        if added_policy_ids:
            rows_with_model_added_findings += 1
            if added_generic_policy_ids:
                rows_with_model_added_generic_review += 1
            if added_detailed_policy_ids:
                rows_with_model_added_detailed_findings += 1
            if added_expected_policy_ids:
                rows_with_model_added_expected_findings += 1
            if added_false_positive_policy_ids:
                rows_with_model_added_false_positives += 1
            if len(model_added_notes) < max_review_notes:
                model_added_notes.append(
                    {
                        "row_id": row_id,
                        "model_status": model_status,
                        "rule_decision": rule["actual_decision"],
                        "hybrid_decision": hybrid["actual_decision"],
                        "added_policy_ids": added_policy_ids,
                        "added_generic_policy_ids": added_generic_policy_ids,
                        "added_detailed_policy_ids": added_detailed_policy_ids,
                        "added_expected_policy_ids": added_expected_policy_ids,
                        "added_false_positive_policy_ids": added_false_positive_policy_ids,
                        "added_detailed_expected_policy_ids": added_detailed_expected_policy_ids,
                        "added_detailed_false_positive_policy_ids": added_detailed_false_positive_policy_ids,
                    }
                )
        if removed_policy_ids and len(model_removed_notes) < max_review_notes:
            model_removed_notes.append(
                {
                    "row_id": row_id,
                    "rule_decision": rule["actual_decision"],
                    "hybrid_decision": hybrid["actual_decision"],
                    "removed_policy_ids": removed_policy_ids,
                }
            )

    model_only_scored = [item for item in model_results.values() if not item.get("skipped")]
    model_only_undercalls = sum(1 for item in model_only_scored if item.get("decision_error_type") == "undercall")
    model_only_overcalls = sum(1 for item in model_only_scored if item.get("decision_error_type") == "overcall")

    return {
        "comparable_rows": len(row_ids),
        "rule_decision_accuracy": modes.get("rule-only", {}).get("decision_accuracy", 0.0),
        "model_only_decision_accuracy": modes.get("model-only", {}).get("decision_accuracy", 0.0),
        "hybrid_decision_accuracy": modes.get("hybrid", {}).get("decision_accuracy", 0.0),
        "hybrid_vs_rule_decision_accuracy_delta": round(
            float(modes.get("hybrid", {}).get("decision_accuracy", 0.0))
            - float(modes.get("rule-only", {}).get("decision_accuracy", 0.0)),
            3,
        ),
        "model_ok_rows": model_ok_rows,
        "model_unavailable_rows": model_unavailable_rows,
        "decision_changed_count": decision_changed_count,
        "decision_improvement_count": len(decision_improvements),
        "decision_regression_count": len(decision_regressions),
        "model_only_undercall_count": model_only_undercalls,
        "model_only_overcall_count": model_only_overcalls,
        "rows_with_model_added_findings": rows_with_model_added_findings,
        "rows_with_model_added_expected_findings": rows_with_model_added_expected_findings,
        "rows_with_model_added_false_positives": rows_with_model_added_false_positives,
        "rows_with_model_added_generic_review": rows_with_model_added_generic_review,
        "rows_with_model_added_detailed_findings": rows_with_model_added_detailed_findings,
        "model_added_policy_hit_count": model_added_policy_hit_count,
        "model_added_expected_policy_hit_count": model_added_expected_policy_hit_count,
        "model_added_false_positive_policy_hit_count": model_added_false_positive_policy_hit_count,
        "model_added_generic_policy_review_count": model_added_generic_policy_review_count,
        "model_added_detailed_policy_hit_count": model_added_detailed_policy_hit_count,
        "model_added_detailed_expected_policy_hit_count": model_added_detailed_expected_policy_hit_count,
        "model_added_detailed_false_positive_policy_hit_count": model_added_detailed_false_positive_policy_hit_count,
        "model_removed_policy_hit_count": model_removed_policy_hit_count,
        "model_rescued_policy_false_negative_count": model_rescued_policy_false_negative_count,
        "review_notes": {
            "decision_improvements": decision_improvements[:max_review_notes],
            "decision_regressions": decision_regressions[:max_review_notes],
            "model_added_findings": model_added_notes,
            "model_removed_findings": model_removed_notes,
        },
    }


def _results_by_id(metrics: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("id")): item
        for item in metrics.get("results", [])
        if item.get("id") is not None and not item.get("skipped")
    }


def _decision_delta_note(row_id: str, rule: dict[str, Any], hybrid: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_id": row_id,
        "expected_decision": hybrid["expected_decision"],
        "rule_decision": rule["actual_decision"],
        "hybrid_decision": hybrid["actual_decision"],
        "rule_error_type": rule["decision_error_type"],
        "hybrid_error_type": hybrid["decision_error_type"],
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
        if metrics.get("hybrid_value"):
            lines.extend(_markdown_hybrid_value(metrics["hybrid_value"]))
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


def _markdown_hybrid_value(value: dict[str, Any]) -> list[str]:
    lines = [
        "## Hybrid Value",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for label, key in (
        ("Comparable rows", "comparable_rows"),
        ("Rule decision accuracy", "rule_decision_accuracy"),
        ("Model-only decision accuracy", "model_only_decision_accuracy"),
        ("Hybrid decision accuracy", "hybrid_decision_accuracy"),
        ("Hybrid minus rule accuracy delta", "hybrid_vs_rule_decision_accuracy_delta"),
        ("Model OK rows", "model_ok_rows"),
        ("Model unavailable rows", "model_unavailable_rows"),
        ("Decision improvements", "decision_improvement_count"),
        ("Decision regressions", "decision_regression_count"),
        ("Model-only undercalls", "model_only_undercall_count"),
        ("Model-only overcalls", "model_only_overcall_count"),
        ("Rows with model-added findings", "rows_with_model_added_findings"),
        ("Rows with generic model review", "rows_with_model_added_generic_review"),
        ("Rows with detailed model-added findings", "rows_with_model_added_detailed_findings"),
        ("Model-added expected policy hits", "model_added_expected_policy_hit_count"),
        ("Model-added false-positive policy hits", "model_added_false_positive_policy_hit_count"),
        ("Generic model review additions", "model_added_generic_policy_review_count"),
        ("Detailed model-added policy hits", "model_added_detailed_policy_hit_count"),
        ("Detailed model-added expected policy hits", "model_added_detailed_expected_policy_hit_count"),
        ("Detailed model-added false-positive policy hits", "model_added_detailed_false_positive_policy_hit_count"),
        ("Model-rescued policy false negatives", "model_rescued_policy_false_negative_count"),
    ):
        lines.append(f"| {label} | {value.get(key, 0)} |")

    lines.extend(["", "### Model-added finding notes", ""])
    added_notes = value.get("review_notes", {}).get("model_added_findings", [])
    if not added_notes:
        lines.append("- None in the included note window.")
    for note in added_notes:
        added = ", ".join(note.get("added_policy_ids", [])) or "none"
        detailed = ", ".join(note.get("added_detailed_policy_ids", [])) or "none"
        false_positive = ", ".join(note.get("added_false_positive_policy_ids", [])) or "none"
        lines.append(
            f"- `{note['row_id']}` added `{added}`; "
            f"detailed `{detailed}`; "
            f"not in labels: `{false_positive}`; model status `{note.get('model_status', 'unknown')}`."
        )
    lines.append("")
    return lines


if __name__ == "__main__":
    raise SystemExit(main())
