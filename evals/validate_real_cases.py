from __future__ import annotations

import json
import argparse
import sys
from collections import Counter
from datetime import date
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
    "source_tier",
    "label_basis",
    "label_confidence",
    "label_rationale",
    "provenance",
    "accessed_at",
    "policy_areas",
    "copyright_status",
    "outcome_source",
    "input",
    "expected_decision",
    "expected_policy_ids",
}
LABEL_CONFIDENCES = {"high", "medium", "low"}
EXPECTED_DECISIONS = {"approved", "needs_review", "high_risk"}
SOURCE_TIERS = {
    "tier_1_reviewed_customer_case",
    "tier_2_public_platform_case",
    "tier_3_public_marketing_example",
    "tier_4_synthetic_from_real_pattern",
    "tier_5_synthetic_control",
}
COPYRIGHT_STATUSES = {"owned", "permissioned", "public_excerpt", "paraphrased", "synthetic"}
OUTCOME_SOURCES = {
    "human_review",
    "platform_action",
    "policy_example",
    "public_enforcement",
    "public_ruling",
    "public_marketing_example",
    "internal_adjudication",
    "none",
}
BLIND_REQUIRED_FIELDS = {
    "source_platform",
    "source_capture_type",
    "ad_observed_status",
    "adjudication_status",
    "adjudicator_notes",
    "rule_tuning_holdout",
}
BLIND_SOURCE_PLATFORMS = {
    "ftc",
    "asa",
    "meta_ad_library",
    "google_ads_transparency",
    "tiktok_ccl",
    "linkedin_ad_library",
    "public_brand_page",
}
BLIND_SOURCE_CAPTURE_TYPES = {
    "regulator_case",
    "ruling",
    "ad_library_entry",
    "public_marketing_page",
}
BLIND_AD_OBSERVED_STATUSES = {"active", "inactive", "archived", "unknown"}
BLIND_ADJUDICATION_STATUSES = {"candidate", "accepted", "rejected"}
MAX_RAW_EXCERPT_CHARS = 240
RAW_EXCERPT_FIELDS = {"raw_ad_copy", "source_excerpt", "raw_excerpt"}


class ValidationError(ValueError):
    pass


def validate_dataset(
    path: Path | str = DEFAULT_DATASET_PATH,
    *,
    min_rows: int | None = None,
    required_decision_counts: dict[str, int] | None = None,
    blind: bool = False,
) -> int:
    dataset_path = Path(path)
    seen_ids: set[str] = set()
    seen_source_urls: set[str] = set()
    seen_normalized_headlines: set[str] = set()
    row_count = 0
    decision_counts = {decision: 0 for decision in EXPECTED_DECISIONS}

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
        _validate_row(
            row,
            dataset_path=dataset_path,
            line_number=line_number,
            seen_ids=seen_ids,
            blind=blind,
            seen_source_urls=seen_source_urls,
            seen_normalized_headlines=seen_normalized_headlines,
        )
        decision_counts[str(row["expected_decision"])] += 1

    if min_rows is not None and row_count < min_rows:
        raise ValidationError(f"{dataset_path}: expected at least {min_rows} rows, found {row_count}")

    for label, required_count in (required_decision_counts or {}).items():
        if label not in EXPECTED_DECISIONS:
            raise ValidationError(f"{dataset_path}: unknown required decision label: {label}")
        actual_count = decision_counts.get(label, 0)
        if actual_count != required_count:
            raise ValidationError(
                f"{dataset_path}: expected {required_count} {label} rows, found {actual_count}"
            )

    return row_count


def validate_candidate_pool(rows: list[dict[str, Any]]) -> dict[str, Any]:
    seen_ids: set[str] = set()
    seen_source_urls: set[str] = set()
    accepted_source_urls: set[str] = set()
    accepted_normalized_headlines: set[str] = set()
    status_counts: Counter[str] = Counter()
    accepted_decision_counts: Counter[str] = Counter()
    distributions: dict[str, dict[str, Counter[str]]] = {
        "accepted": {"source_platform": Counter(), "source_capture_type": Counter()},
        "rejected": {"source_platform": Counter(), "source_capture_type": Counter()},
    }
    dataset_path = Path("<real-world-blind-candidate-pool>")

    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            _fail(dataset_path, index, "row must be a JSON object")

        _validate_row(
            row,
            dataset_path=dataset_path,
            line_number=index,
            seen_ids=seen_ids,
            blind=False,
        )
        _validate_blind_common_metadata(row, dataset_path=dataset_path, line_number=index)

        status = str(row["adjudication_status"])
        status_counts[status] += 1
        if row["source_url"] in seen_source_urls:
            _fail(dataset_path, index, f"duplicate source_url: {row['source_url']}")
        seen_source_urls.add(row["source_url"])

        if status == "accepted":
            _validate_accepted_candidate_row(
                row,
                dataset_path=dataset_path,
                line_number=index,
                seen_source_urls=accepted_source_urls,
                seen_normalized_headlines=accepted_normalized_headlines,
            )
            accepted_decision_counts[str(row["expected_decision"])] += 1
        elif status == "rejected":
            if not isinstance(row["rule_tuning_holdout"], bool):
                _fail(dataset_path, index, "rejected blind rows must set rule_tuning_holdout to a boolean")
        else:
            _fail(dataset_path, index, "candidate pool rows must be accepted or rejected")

        if status in distributions:
            distributions[status]["source_platform"][str(row["source_platform"])] += 1
            distributions[status]["source_capture_type"][str(row["source_capture_type"])] += 1

    if len(rows) != 150:
        raise ValidationError(f"{dataset_path}: expected 150 candidate rows, found {len(rows)}")
    if status_counts.get("accepted", 0) != 90:
        raise ValidationError(
            f"{dataset_path}: expected 90 accepted candidate rows, found {status_counts.get('accepted', 0)}"
        )
    if status_counts.get("rejected", 0) != 60:
        raise ValidationError(
            f"{dataset_path}: expected 60 rejected candidate rows, found {status_counts.get('rejected', 0)}"
        )

    for decision in EXPECTED_DECISIONS:
        actual_count = accepted_decision_counts.get(decision, 0)
        if actual_count != 30:
            raise ValidationError(
                f"{dataset_path}: expected 30 accepted {decision} rows, found {actual_count}"
            )

    return {
        "total_rows": len(rows),
        "status_counts": _sorted_counter(status_counts),
        "accepted_decision_counts": _sorted_counter(accepted_decision_counts),
        "distributions": {
            status: {
                field_name: _sorted_counter(counter)
                for field_name, counter in fields.items()
            }
            for status, fields in distributions.items()
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate AdLint real-case eval metadata.")
    parser.add_argument("dataset", nargs="?", default=str(DEFAULT_DATASET_PATH), help="real-case JSONL dataset")
    parser.add_argument("--min-rows", type=_positive_int, help="minimum row count")
    parser.add_argument(
        "--require-decision-count",
        action="append",
        default=[],
        metavar="LABEL=N",
        help="require an exact expected_decision count; may be repeated",
    )
    parser.add_argument(
        "--blind",
        action="store_true",
        help="enforce web-sourced blind holdout metadata and duplicate checks",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    try:
        required_counts = _parse_required_decision_counts(args.require_decision_count)
        row_count = validate_dataset(
            args.dataset,
            min_rows=args.min_rows,
            required_decision_counts=required_counts,
            blind=args.blind,
        )
    except ValidationError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1

    print(f"OK {row_count} rows validated: {Path(args.dataset)}")
    return 0


def _validate_row(
    row: dict[str, Any],
    *,
    dataset_path: Path,
    line_number: int,
    seen_ids: set[str],
    blind: bool = False,
    seen_source_urls: set[str] | None = None,
    seen_normalized_headlines: set[str] | None = None,
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
    if row["source_tier"] not in SOURCE_TIERS:
        _fail(dataset_path, line_number, "source_tier must be a known real-case source tier")
    if row["copyright_status"] not in COPYRIGHT_STATUSES:
        _fail(dataset_path, line_number, "copyright_status must be a known copyright status")
    if row["outcome_source"] not in OUTCOME_SOURCES:
        _fail(dataset_path, line_number, "outcome_source must be a known outcome source")
    if not _is_iso_date(row["accessed_at"]):
        _fail(dataset_path, line_number, "accessed_at must use YYYY-MM-DD")
    if "case_date" in row and not _is_iso_date(row["case_date"]):
        _fail(dataset_path, line_number, "case_date must use YYYY-MM-DD")
    if not isinstance(row["policy_areas"], list) or not row["policy_areas"]:
        _fail(dataset_path, line_number, "policy_areas must be a non-empty list")
    if not _non_empty_text(row["label_rationale"]):
        _fail(dataset_path, line_number, "label_rationale must be non-empty text")
    if not _non_empty_text(row["provenance"]):
        _fail(dataset_path, line_number, "provenance must be non-empty text")
    if not isinstance(row["expected_policy_ids"], list):
        _fail(dataset_path, line_number, "expected_policy_ids must be a list")
    if row["expected_decision"] == "approved" and row["expected_policy_ids"]:
        _fail(dataset_path, line_number, "approved rows must not include expected_policy_ids")
    if not isinstance(row["input"], dict):
        _fail(dataset_path, line_number, "input must be a dict")
    if "landing_page_url" in row["input"]:
        _fail(dataset_path, line_number, "input must not include live landing_page_url")
    if blind:
        _validate_blind_row(
            row,
            dataset_path=dataset_path,
            line_number=line_number,
            seen_source_urls=seen_source_urls if seen_source_urls is not None else set(),
            seen_normalized_headlines=(
                seen_normalized_headlines if seen_normalized_headlines is not None else set()
            ),
        )


def _validate_blind_row(
    row: dict[str, Any],
    *,
    dataset_path: Path,
    line_number: int,
    seen_source_urls: set[str],
    seen_normalized_headlines: set[str],
) -> None:
    _validate_blind_common_metadata(row, dataset_path=dataset_path, line_number=line_number)

    if row["source_url"] in seen_source_urls:
        _fail(dataset_path, line_number, f"duplicate source_url: {row['source_url']}")
    seen_source_urls.add(row["source_url"])

    headline = row["input"].get("headline")
    normalized_headline = _normalize_for_duplicate_check(headline)
    if not normalized_headline:
        _fail(dataset_path, line_number, "blind input headline must be non-empty text")
    if normalized_headline in seen_normalized_headlines:
        _fail(dataset_path, line_number, f"duplicate normalized headline: {headline}")
    seen_normalized_headlines.add(normalized_headline)

    if row["adjudication_status"] == "accepted":
        if row["rule_tuning_holdout"] is not True:
            _fail(dataset_path, line_number, "accepted blind rows must set rule_tuning_holdout to true")


def _validate_blind_common_metadata(
    row: dict[str, Any],
    *,
    dataset_path: Path,
    line_number: int,
) -> None:
    missing = sorted(BLIND_REQUIRED_FIELDS - row.keys())
    if missing:
        _fail(dataset_path, line_number, f"missing blind field(s): {', '.join(missing)}")

    if row["source_platform"] not in BLIND_SOURCE_PLATFORMS:
        _fail(dataset_path, line_number, "source_platform must be a known blind source platform")
    if row["source_capture_type"] not in BLIND_SOURCE_CAPTURE_TYPES:
        _fail(dataset_path, line_number, "source_capture_type must be a known blind capture type")
    if row["ad_observed_status"] not in BLIND_AD_OBSERVED_STATUSES:
        _fail(dataset_path, line_number, "ad_observed_status must be one of: active, inactive, archived, unknown")
    if row["adjudication_status"] not in BLIND_ADJUDICATION_STATUSES:
        _fail(dataset_path, line_number, "adjudication_status must be one of: candidate, accepted, rejected")

    headline = row["input"].get("headline")
    normalized_headline = _normalize_for_duplicate_check(headline)
    if not normalized_headline:
        _fail(dataset_path, line_number, "blind input headline must be non-empty text")

    if not _non_empty_text(row["adjudicator_notes"]):
        if row["adjudication_status"] == "accepted":
            _fail(dataset_path, line_number, "accepted blind rows must include adjudicator_notes")
        _fail(dataset_path, line_number, "blind rows must include adjudicator_notes")

    for field_name in RAW_EXCERPT_FIELDS:
        value = row.get(field_name)
        if isinstance(value, str) and len(value) > MAX_RAW_EXCERPT_CHARS:
            _fail(
                dataset_path,
                line_number,
                f"{field_name} must be {MAX_RAW_EXCERPT_CHARS} characters or fewer",
            )

    for forbidden_field in ("raw_landing_page_html", "screenshot_url", "account_id", "targeting_details"):
        if forbidden_field in row:
            _fail(dataset_path, line_number, f"blind rows must not include {forbidden_field}")


def _validate_accepted_candidate_row(
    row: dict[str, Any],
    *,
    dataset_path: Path,
    line_number: int,
    seen_source_urls: set[str],
    seen_normalized_headlines: set[str],
) -> None:
    if row["rule_tuning_holdout"] is not True:
        _fail(dataset_path, line_number, "accepted blind rows must set rule_tuning_holdout to true")

    if row["source_url"] in seen_source_urls:
        _fail(dataset_path, line_number, f"duplicate accepted source_url: {row['source_url']}")
    seen_source_urls.add(row["source_url"])

    headline = row["input"].get("headline")
    normalized_headline = _normalize_for_duplicate_check(headline)
    if normalized_headline in seen_normalized_headlines:
        _fail(dataset_path, line_number, f"duplicate accepted normalized headline: {headline}")
    seen_normalized_headlines.add(normalized_headline)


def _is_http_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_iso_date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    if len(value) != 10:
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalize_for_duplicate_check(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


def _parse_required_decision_counts(raw_values: list[str]) -> dict[str, int]:
    parsed: dict[str, int] = {}
    for raw_value in raw_values:
        if "=" not in raw_value:
            raise ValidationError("--require-decision-count must use LABEL=N")
        label, count_text = raw_value.split("=", 1)
        label = label.strip()
        if label not in EXPECTED_DECISIONS:
            raise ValidationError(f"unknown required decision label: {label}")
        try:
            count = int(count_text)
        except ValueError as exc:
            raise ValidationError(f"invalid decision count for {label}: {count_text}") from exc
        if count < 0:
            raise ValidationError(f"decision count for {label} must be non-negative")
        parsed[label] = count
    return parsed


def _sorted_counter(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _fail(dataset_path: Path, line_number: int, message: str) -> None:
    raise ValidationError(f"{dataset_path}:{line_number}: {message}")


if __name__ == "__main__":
    raise SystemExit(main())
