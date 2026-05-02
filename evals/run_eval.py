from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from adlint.engine import analyze


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AdLint seed evals.")
    parser.add_argument("dataset", help="JSONL dataset with input and expected labels.")
    parser.add_argument("--output", help="Optional JSON metrics output path.")
    args = parser.parse_args()

    rows = _load_rows(Path(args.dataset))
    results = [_score_row(row) for row in rows]
    metrics = _metrics(results)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0 if metrics["decision_accuracy"] >= 0.7 else 1


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


def _score_row(row: dict[str, Any]) -> dict[str, Any]:
    result = analyze(row["input"])
    actual_policy_ids = {hit.policy_id for hit in result.policy_hits}
    expected_policy_ids = set(row.get("expected_policy_ids", []))
    return {
        "id": row.get("id"),
        "expected_decision": row["expected_decision"],
        "actual_decision": result.decision,
        "decision_match": row["expected_decision"] == result.decision,
        "expected_policy_ids": sorted(expected_policy_ids),
        "actual_policy_ids": sorted(actual_policy_ids),
        "policy_true_positives": sorted(expected_policy_ids & actual_policy_ids),
        "policy_false_negatives": sorted(expected_policy_ids - actual_policy_ids),
        "policy_false_positives": sorted(actual_policy_ids - expected_policy_ids),
    }


def _metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    decision_matches = sum(1 for item in results if item["decision_match"])
    expected_by_policy: Counter[str] = Counter()
    actual_by_policy: Counter[str] = Counter()
    true_positive_by_policy: Counter[str] = Counter()

    for item in results:
        expected = set(item["expected_policy_ids"])
        actual = set(item["actual_policy_ids"])
        for policy_id in expected:
            expected_by_policy[policy_id] += 1
        for policy_id in actual:
            actual_by_policy[policy_id] += 1
        for policy_id in expected & actual:
            true_positive_by_policy[policy_id] += 1

    policy_metrics: dict[str, dict[str, float]] = {}
    for policy_id in sorted(set(expected_by_policy) | set(actual_by_policy)):
        tp = true_positive_by_policy[policy_id]
        precision = tp / actual_by_policy[policy_id] if actual_by_policy[policy_id] else 0.0
        recall = tp / expected_by_policy[policy_id] if expected_by_policy[policy_id] else 0.0
        policy_metrics[policy_id] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "expected_count": expected_by_policy[policy_id],
            "actual_count": actual_by_policy[policy_id],
        }

    misses_by_decision: dict[str, int] = defaultdict(int)
    for item in results:
        if not item["decision_match"]:
            misses_by_decision[item["expected_decision"]] += 1

    return {
        "total_examples": total,
        "decision_accuracy": round(decision_matches / total, 3) if total else 0.0,
        "misses_by_expected_decision": dict(sorted(misses_by_decision.items())),
        "policy_metrics": policy_metrics,
        "results": results,
    }


if __name__ == "__main__":
    raise SystemExit(main())
