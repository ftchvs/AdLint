from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "datasets" / "real_cases_v1.jsonl"
REQUIRED_FIELDS = {
    "id",
    "source_type",
    "source_org",
    "source_url",
    "source_title",
    "label_basis",
    "label_confidence",
    "input",
    "expected_decision",
    "expected_policy_ids",
}
LABEL_CONFIDENCES = {"high", "medium", "low"}
EXPECTED_DECISIONS = {"approved", "needs_review", "high_risk"}


class ValidationError(ValueError):
    pass


def validate_dataset(path: Path | str = DEFAULT_DATASET_PATH) -> int:
    dataset_path = Path(path)
    seen_ids: set[str] = set()
    row_count = 0

    try:
        lines = dataset_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValidationError(f"{dataset_path}: {exc.strerror}") from exc

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        row_count += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValidationError(f"{dataset_path}:{line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise ValidationError(f"{dataset_path}:{line_number}: row must be a JSON object")
        _validate_row(row, dataset_path=dataset_path, line_number=line_number, seen_ids=seen_ids)

    return row_count


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        print("usage: validate_real_cases.py [dataset.jsonl]", file=sys.stderr)
        return 2

    dataset_path = Path(args[0]) if args else DEFAULT_DATASET_PATH
    try:
        row_count = validate_dataset(dataset_path)
    except ValidationError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1

    print(f"OK {row_count} rows validated: {dataset_path}")
    return 0


def _validate_row(
    row: dict[str, Any],
    *,
    dataset_path: Path,
    line_number: int,
    seen_ids: set[str],
) -> None:
    missing = sorted(REQUIRED_FIELDS - row.keys())
    if missing:
        _fail(dataset_path, line_number, f"missing required field(s): {', '.join(missing)}")

    row_id = row["id"]
    row_id_key = json.dumps(row_id, sort_keys=True)
    if row_id_key in seen_ids:
        _fail(dataset_path, line_number, f"duplicate id: {row_id}")
    seen_ids.add(row_id_key)

    if not _is_http_url(row["source_url"]):
        _fail(dataset_path, line_number, "source_url must be an http(s) URL")
    if row["label_confidence"] not in LABEL_CONFIDENCES:
        _fail(dataset_path, line_number, "label_confidence must be one of: high, medium, low")
    if row["expected_decision"] not in EXPECTED_DECISIONS:
        _fail(dataset_path, line_number, "expected_decision must be one of: approved, needs_review, high_risk")
    if not isinstance(row["expected_policy_ids"], list):
        _fail(dataset_path, line_number, "expected_policy_ids must be a list")
    if not isinstance(row["input"], dict):
        _fail(dataset_path, line_number, "input must be a dict")
    if "landing_page_url" in row["input"]:
        _fail(dataset_path, line_number, "input must not include live landing_page_url")


def _is_http_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _fail(dataset_path: Path, line_number: int, message: str) -> None:
    raise ValidationError(f"{dataset_path}:{line_number}: {message}")


if __name__ == "__main__":
    raise SystemExit(main())
