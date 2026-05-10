from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure usefulness of model-added review notes.")
    parser.add_argument("metrics", help="JSON output from evals/run_eval.py --mode all.")
    parser.add_argument(
        "--labels",
        default="evals/datasets/model_review_usefulness_v1.jsonl",
        help="JSONL labels keyed by eval row id.",
    )
    parser.add_argument("--output", help="Optional JSON metrics output path.")
    parser.add_argument("--markdown-output", help="Optional Markdown metrics output path.")
    args = parser.parse_args()

    metrics = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
    labels = _load_labels(Path(args.labels))
    report = measure_usefulness(metrics, labels)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.markdown_output:
        markdown_path = Path(args.markdown_output)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(_markdown_report(report), encoding="utf-8")

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def measure_usefulness(metrics: dict[str, Any], labels: dict[str, dict[str, Any]]) -> dict[str, Any]:
    hybrid_value = metrics.get("hybrid_value", {})
    notes = hybrid_value.get("review_notes", {}).get("model_added_findings", [])
    comparable_rows = int(hybrid_value.get("comparable_rows", 0))
    rows_with_generic_review = int(hybrid_value.get("rows_with_model_added_generic_review", 0))
    model_status_counts = metrics.get("modes", {}).get("hybrid", {}).get("model_status_counts", {})

    labeled_added = []
    unlabeled_added = []
    useful_added = []
    false_review_burden = []

    for note in notes:
        row_id = str(note.get("row_id", ""))
        label = labels.get(row_id)
        if label is None:
            unlabeled_added.append(_note_summary(note, label=None))
            continue
        summary = _note_summary(note, label=label)
        labeled_added.append(summary)
        if _is_useful(note, label):
            useful_added.append(summary)
        else:
            false_review_burden.append(summary)

    labeled_count = len(labeled_added)
    useful_count = len(useful_added)
    false_burden_count = len(false_review_burden)
    invalid_count = int(model_status_counts.get("invalid_response", 0))
    unavailable_count = int(model_status_counts.get("unavailable", 0))
    ok_count = int(model_status_counts.get("ok", 0))
    status_total = sum(int(value) for value in model_status_counts.values())

    return {
        "metric_version": 1,
        "source_dataset": metrics.get("dataset", "<unknown>"),
        "labeled_rows": len(labels),
        "comparable_rows": comparable_rows,
        "model_added_note_rows": len(notes),
        "labeled_model_added_note_rows": labeled_count,
        "unlabeled_model_added_note_rows": len(unlabeled_added),
        "useful_model_added_note_rows": useful_count,
        "false_review_burden_rows": false_burden_count,
        "useful_note_precision": round(useful_count / labeled_count, 3) if labeled_count else 0.0,
        "false_review_burden_rate": round(false_burden_count / labeled_count, 3) if labeled_count else 0.0,
        "generic_review_burden_rate": round(rows_with_generic_review / comparable_rows, 3) if comparable_rows else 0.0,
        "model_invalid_response_rate": round(invalid_count / status_total, 3) if status_total else 0.0,
        "model_unavailable_rate": round(unavailable_count / status_total, 3) if status_total else 0.0,
        "model_ok_rate": round(ok_count / status_total, 3) if status_total else 0.0,
        "model_status_counts": dict(sorted(model_status_counts.items())),
        "examples": {
            "useful_model_added_notes": useful_added[:10],
            "false_review_burden": false_review_burden[:10],
            "unlabeled_model_added_notes": unlabeled_added[:10],
        },
        "limitations": [
            "Usefulness labels judge reviewer value, not legal compliance or platform approval.",
            "Unlabeled model-added notes are excluded from precision until reviewed.",
            "This metric depends on a live local-model run and should be compared by model/version.",
        ],
    }


def _load_labels(path: Path) -> dict[str, dict[str, Any]]:
    labels: dict[str, dict[str, Any]] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        row_id = str(row.get("id", ""))
        if not row_id:
            raise ValueError(f"Missing id at {path}:{line_number}")
        if row_id in labels:
            raise ValueError(f"Duplicate id {row_id!r} at {path}:{line_number}")
        labels[row_id] = row
    return labels


def _is_useful(note: dict[str, Any], label: dict[str, Any]) -> bool:
    added_policy_ids = set(str(item) for item in note.get("added_policy_ids", []))
    useful_policy_ids = set(str(item) for item in label.get("useful_policy_ids", []))
    if added_policy_ids & useful_policy_ids:
        return True
    if "model_policy_review" in added_policy_ids and bool(label.get("acceptable_generic_review")):
        return True
    return False


def _note_summary(note: dict[str, Any], *, label: dict[str, Any] | None) -> dict[str, Any]:
    payload = {
        "row_id": note.get("row_id"),
        "added_policy_ids": note.get("added_policy_ids", []),
        "added_generic_policy_ids": note.get("added_generic_policy_ids", []),
        "added_false_positive_policy_ids": note.get("added_false_positive_policy_ids", []),
    }
    if label is not None:
        payload["expected_review_dimension"] = label.get("expected_review_dimension")
        payload["acceptable_generic_review"] = bool(label.get("acceptable_generic_review"))
        payload["rationale"] = label.get("rationale", "")
    return payload


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Model Review Usefulness Report",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    for label, key in (
        ("Comparable rows", "comparable_rows"),
        ("Labeled rows", "labeled_rows"),
        ("Model-added note rows", "model_added_note_rows"),
        ("Labeled model-added note rows", "labeled_model_added_note_rows"),
        ("Useful model-added note rows", "useful_model_added_note_rows"),
        ("False review burden rows", "false_review_burden_rows"),
        ("Useful note precision", "useful_note_precision"),
        ("False review burden rate", "false_review_burden_rate"),
        ("Generic review burden rate", "generic_review_burden_rate"),
        ("Model invalid-response rate", "model_invalid_response_rate"),
    ):
        lines.append(f"| {label} | {report.get(key, 0)} |")

    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report.get("limitations", []))
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
