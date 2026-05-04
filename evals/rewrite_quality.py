from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from adlint.engine import analyze
from adlint.storage import record_eval_run


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "evals" / "datasets" / "rewrite_quality_v1.jsonl"
DIMENSIONS = ("clarity", "risk_reduction", "policy_fit", "intent_preservation")
RUBRIC: dict[str, str] = {
    "clarity": "Rewrite is readable, specific, and complete enough for a reviewer to judge.",
    "risk_reduction": "Rewrite removes or qualifies the risky claim, urgency, privacy, or disclosure issue.",
    "policy_fit": "Rewrite fits the policy category and includes required qualifiers, disclosures, or consent language.",
    "intent_preservation": "Rewrite keeps the advertiser's benign intent without keeping the unsafe execution.",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate deterministic safer-rewrite quality.")
    parser.add_argument(
        "dataset",
        nargs="?",
        default=str(DEFAULT_DATASET),
        help="JSONL rewrite-quality dataset. Defaults to evals/datasets/rewrite_quality_v1.jsonl.",
    )
    parser.add_argument(
        "--generator",
        choices=("deterministic",),
        default="deterministic",
        help="Rewrite generator to evaluate. Deterministic rewrites are the baseline.",
    )
    parser.add_argument("--output", help="Optional JSON metrics output path.")
    parser.add_argument("--markdown-output", help="Optional Markdown metrics output path.")
    parser.add_argument("--storage-path", help="Optional SQLite metadata database for eval results.")
    parser.add_argument(
        "--min-overall-score",
        type=float,
        default=3.0,
        help="Minimum average rewrite-quality score required for a zero exit code.",
    )
    args = parser.parse_args(argv)

    dataset_path = Path(args.dataset)
    rows = load_rows(dataset_path)
    metrics = evaluate_rows(rows, dataset_path=dataset_path, generator=args.generator)

    if args.storage_path:
        metrics["storage"] = {
            "enabled": True,
            "path": record_eval_run(
                path=args.storage_path,
                evaluator=str(metrics["evaluator"]),
                dataset_path=str(dataset_path),
                generator=args.generator,
                total_examples=int(metrics["input_examples"]),
                aggregate=metrics["rewrite_quality"],
                results=metrics["results"],
            ),
        }
    else:
        metrics["storage"] = {"enabled": False}

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.markdown_output:
        markdown_path = Path(args.markdown_output)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(markdown_report(metrics), encoding="utf-8")

    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0 if metrics["rewrite_quality"]["overall_average"] >= args.min_overall_score else 1


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        row_id = row.get("id")
        if not row_id or not isinstance(row_id, str):
            raise ValueError(f"Missing string id at {path}:{line_number}")
        if row_id in seen_ids:
            raise ValueError(f"Duplicate id {row_id!r} at {path}:{line_number}")
        if not isinstance(row.get("input"), dict):
            raise ValueError(f"Missing input object at {path}:{line_number}")
        if not isinstance(row.get("quality_checks"), dict):
            raise ValueError(f"Missing quality_checks object at {path}:{line_number}")
        if not isinstance(row.get("min_scores"), dict):
            raise ValueError(f"Missing min_scores object at {path}:{line_number}")
        seen_ids.add(row_id)
        rows.append(row)
    return rows


def evaluate_rows(
    rows: list[dict[str, Any]],
    *,
    dataset_path: Path | None = None,
    generator: str = "deterministic",
) -> dict[str, Any]:
    results = [_score_row(row, generator=generator) for row in rows]
    rewrite_quality = _aggregate_quality(results)
    return {
        "evaluator": "rewrite_quality_v1",
        "dataset": str(dataset_path) if dataset_path else "<in-memory>",
        "generator": generator,
        "baseline": "deterministic_rules",
        "input_examples": len(rows),
        "decision_accuracy": {
            "measured": False,
            "reason": "Rewrite quality is evaluated separately from decision accuracy.",
        },
        "model_rewrites": {
            "enabled": False,
            "reason": "Deterministic rewrites remain the baseline before model-generated rewrites are introduced.",
        },
        "rewrite_quality": rewrite_quality,
        "results": results,
    }


def markdown_report(metrics: dict[str, Any]) -> str:
    quality = metrics["rewrite_quality"]
    lines = [
        "# AdLint Rewrite Quality Report",
        "",
        f"- Generator: `{metrics['generator']}`",
        f"- Baseline: `{metrics['baseline']}`",
        "- Decision accuracy: not measured by this eval",
        f"- Input examples: {metrics['input_examples']}",
        f"- Overall rewrite quality: {quality['overall_average']:.3f}",
        f"- Pass rate: {quality['pass_rate']:.3f}",
        "",
        "## Rubric",
        "",
    ]
    for dimension in DIMENSIONS:
        lines.append(f"- `{dimension}`: {RUBRIC[dimension]}")

    lines.extend(["", "## Dimension Averages", "", "| Dimension | Score |", "| --- | ---: |"])
    for dimension, score in quality["dimension_averages"].items():
        lines.append(f"| {dimension} | {score:.3f} |")

    lines.extend(["", "## Row Results", ""])
    for result in metrics["results"]:
        status = "pass" if result["passed_min_scores"] else "review"
        lines.append(
            f"- `{result['id']}` `{status}`: overall {result['overall_score']:.3f}, "
            f"rewrites {result['rewrite_count']}."
        )
    lines.extend(
        [
            "",
            "Rewrite quality is reviewer-rubric coverage for safer copy suggestions.",
            "It is reported separately from decision accuracy and is not a platform approval guarantee.",
            "",
        ]
    )
    return "\n".join(lines)


def _score_row(row: dict[str, Any], *, generator: str) -> dict[str, Any]:
    result = analyze(row["input"], enable_model=False)
    actual_policy_ids = sorted({hit.policy_id for hit in result.policy_hits})
    scored_rewrites = [
        _score_rewrite(rewrite, row, actual_policy_ids=actual_policy_ids, index=index)
        for index, rewrite in enumerate(result.safer_rewrites)
    ]
    if scored_rewrites:
        selected = max(scored_rewrites, key=lambda item: (item["overall_score"], -item["selected_rewrite_index"]))
    else:
        selected = {
            "selected_rewrite_index": None,
            "scores": {dimension: 0 for dimension in DIMENSIONS},
            "overall_score": 0.0,
            "failure_codes": ["missing_rewrite"],
        }

    min_scores = {dimension: float(row["min_scores"].get(dimension, 1)) for dimension in DIMENSIONS}
    failure_codes = list(selected["failure_codes"])
    for dimension, minimum in min_scores.items():
        if float(selected["scores"][dimension]) < minimum:
            failure_codes.append(f"{dimension}_below_min")

    expected_policy_ids = sorted(str(policy_id) for policy_id in row.get("expected_policy_ids", []))
    return {
        "id": row["id"],
        "generator": generator,
        "rewrite_count": len(result.safer_rewrites),
        "selected_rewrite_index": selected["selected_rewrite_index"],
        "actual_policy_ids": actual_policy_ids,
        "expected_policy_ids": expected_policy_ids,
        "expected_policy_ids_match": set(expected_policy_ids).issubset(actual_policy_ids),
        "scores": selected["scores"],
        "overall_score": selected["overall_score"],
        "min_scores": min_scores,
        "passed_min_scores": not failure_codes,
        "failure_codes": sorted(set(failure_codes)),
    }


def _score_rewrite(
    rewrite: dict[str, str],
    row: dict[str, Any],
    *,
    actual_policy_ids: list[str],
    index: int,
) -> dict[str, Any]:
    checks = row["quality_checks"]
    text = _rewrite_text(rewrite)
    scores = {
        "clarity": _score_clarity(rewrite, checks),
        "risk_reduction": _score_risk_reduction(text, checks),
        "policy_fit": _score_policy_fit(text, checks, row, actual_policy_ids),
        "intent_preservation": _score_intent_preservation(text, rewrite, checks),
    }
    failure_codes = _rewrite_failure_codes(text, rewrite, checks)
    return {
        "selected_rewrite_index": index,
        "scores": scores,
        "overall_score": round(sum(scores.values()) / len(DIMENSIONS), 3),
        "failure_codes": failure_codes,
    }


def _score_clarity(rewrite: dict[str, str], checks: dict[str, Any]) -> int:
    score = 5
    for field in ("headline", "body", "cta"):
        if not rewrite.get(field, "").strip():
            score -= 2
    max_total_chars = int(checks.get("max_total_chars", 280))
    if len(_rewrite_text(rewrite)) > max_total_chars:
        score -= 1
    if len(rewrite.get("body", "")) > int(checks.get("max_body_chars", 180)):
        score -= 1
    return _bounded_score(score)


def _score_risk_reduction(text: str, checks: dict[str, Any]) -> int:
    forbidden_terms = _terms(checks, "forbidden_terms")
    risk_terms = _terms(checks, "risk_reduction_terms")
    score = 5
    if forbidden_terms:
        score -= 2 * sum(1 for term in forbidden_terms if _contains(text, term))
    if risk_terms:
        score -= sum(1 for term in risk_terms if not _contains(text, term))
    if not forbidden_terms and not risk_terms:
        score = 4
    return _bounded_score(score)


def _score_policy_fit(
    text: str,
    checks: dict[str, Any],
    row: dict[str, Any],
    actual_policy_ids: list[str],
) -> int:
    required_terms = _terms(checks, "required_terms")
    score = 5
    score -= sum(1 for term in required_terms if not _contains(text, term))
    expected_policy_ids = {str(policy_id) for policy_id in row.get("expected_policy_ids", [])}
    if expected_policy_ids and not expected_policy_ids.issubset(set(actual_policy_ids)):
        score -= 1
    if not required_terms:
        score = min(score, 4)
    return _bounded_score(score)


def _score_intent_preservation(text: str, rewrite: dict[str, str], checks: dict[str, Any]) -> int:
    intent_terms = _terms(checks, "intent_terms")
    if intent_terms:
        matches = sum(1 for term in intent_terms if _contains(text, term))
        score = 3 + min(matches, 2)
        if matches == 0:
            score = 2
    else:
        score = 4
    if rewrite.get("cta", "").strip().lower() in {"buy now", "act now", "claim now", "sign up now"}:
        score -= 1
    return _bounded_score(score)


def _rewrite_failure_codes(text: str, rewrite: dict[str, str], checks: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    if any(not rewrite.get(field, "").strip() for field in ("headline", "body", "cta")):
        codes.append("missing_rewrite_field")
    if any(_contains(text, term) for term in _terms(checks, "forbidden_terms")):
        codes.append("forbidden_terms_present")
    if any(not _contains(text, term) for term in _terms(checks, "required_terms")):
        codes.append("required_terms_missing")
    if _terms(checks, "intent_terms") and not any(_contains(text, term) for term in _terms(checks, "intent_terms")):
        codes.append("intent_not_preserved")
    return codes


def _aggregate_quality(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    dimension_averages = {
        dimension: round(sum(float(result["scores"][dimension]) for result in results) / total, 3) if total else 0.0
        for dimension in DIMENSIONS
    }
    overall_average = round(sum(float(result["overall_score"]) for result in results) / total, 3) if total else 0.0
    pass_rate = round(sum(1 for result in results if result["passed_min_scores"]) / total, 3) if total else 0.0
    return {
        "rubric": RUBRIC,
        "dimensions": list(DIMENSIONS),
        "total_examples": total,
        "rows_with_rewrites": sum(1 for result in results if result["rewrite_count"] > 0),
        "overall_average": overall_average,
        "pass_rate": pass_rate,
        "dimension_averages": dimension_averages,
    }


def _rewrite_text(rewrite: dict[str, str]) -> str:
    return " ".join(str(rewrite.get(field, "")) for field in ("headline", "body", "cta")).strip()


def _terms(checks: dict[str, Any], key: str) -> list[str]:
    return [str(term) for term in checks.get(key, [])]


def _contains(text: str, term: str) -> bool:
    return term.lower() in text.lower()


def _bounded_score(score: int) -> int:
    return max(1, min(5, score))


if __name__ == "__main__":
    raise SystemExit(main())
