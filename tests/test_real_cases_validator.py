from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from collections import Counter

import pytest


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "evals" / "validate_real_cases.py"
VALIDATOR_SPEC = importlib.util.spec_from_file_location("validate_real_cases", VALIDATOR_PATH)
assert VALIDATOR_SPEC is not None
assert VALIDATOR_SPEC.loader is not None
validate_real_cases = importlib.util.module_from_spec(VALIDATOR_SPEC)
VALIDATOR_SPEC.loader.exec_module(validate_real_cases)


def _valid_row(**overrides):
    row = {
        "id": "case-1",
        "source_type": "regulatory_action",
        "source_org": "Example Regulator",
        "source_url": "https://example.com/action",
        "source_title": "Example action",
        "source_tier": "tier_3_public_marketing_example",
        "label_basis": "Published enforcement summary",
        "label_confidence": "high",
        "label_rationale": "The source supports a review label for this deterministic local row.",
        "provenance": "https://example.com/action accessed 2026-05-02; paraphrased for eval use.",
        "accessed_at": "2026-05-02",
        "policy_areas": ["finance"],
        "copyright_status": "paraphrased",
        "outcome_source": "policy_example",
        "input": {
            "platform": "google",
            "industry": "finance",
            "headline": "Compare credit options",
            "body": "Review terms before applying.",
            "cta": "Learn more",
        },
        "expected_decision": "needs_review",
        "expected_policy_ids": ["financial_services_review"],
    }
    row.update(overrides)
    return row


def _valid_blind_row(**overrides):
    row = _valid_row(
        id="blind-case-1",
        source_platform="google_ads_transparency",
        source_capture_type="ad_library_entry",
        ad_observed_status="unknown",
        adjudication_status="accepted",
        adjudicator_notes="Accepted as a blind holdout row and not used for rule tuning.",
        rule_tuning_holdout=True,
    )
    row.update(overrides)
    return row


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_validate_dataset_accepts_valid_rows_and_skips_blanks(tmp_path) -> None:
    dataset = tmp_path / "real_cases.jsonl"
    dataset.write_text(
        "\n"
        + json.dumps(_valid_row())
        + "\n\n"
        + json.dumps(
            _valid_row(
                id="case-2",
                label_confidence="medium",
                expected_decision="approved",
                expected_policy_ids=[],
            )
        )
        + "\n",
        encoding="utf-8",
    )

    assert validate_real_cases.validate_dataset(dataset) == 2


def test_cli_prints_ok_line_with_row_count(tmp_path, capsys) -> None:
    dataset = tmp_path / "real_cases.jsonl"
    _write_jsonl(dataset, [_valid_row()])

    assert validate_real_cases.main([str(dataset)]) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == f"OK 1 rows validated: {dataset}\n"


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"source_url": "ftp://example.com/action"}, "source_url must be an http\\(s\\) URL"),
        ({"source_url": "https:///missing-host"}, "source_url must be an http\\(s\\) URL"),
        ({"label_confidence": "certain"}, "label_confidence must be one of"),
        ({"expected_decision": "blocked"}, "expected_decision must be one of"),
        ({"source_tier": "unknown"}, "source_tier must be a known real-case source tier"),
        ({"copyright_status": "unclear"}, "copyright_status must be a known copyright status"),
        ({"outcome_source": "rumor"}, "outcome_source must be a known outcome source"),
        ({"accessed_at": "05/02/2026"}, "accessed_at must use YYYY-MM-DD"),
        ({"case_date": "2026-02-30"}, "case_date must use YYYY-MM-DD"),
        ({"case_date": "2026/05/02"}, "case_date must use YYYY-MM-DD"),
        ({"policy_areas": []}, "policy_areas must be a non-empty list"),
        ({"label_rationale": ""}, "label_rationale must be non-empty text"),
        ({"provenance": ""}, "provenance must be non-empty text"),
        ({"expected_policy_ids": "financial_services_review"}, "expected_policy_ids must be a list"),
        (
            {"expected_decision": "approved", "expected_policy_ids": ["financial_services_review"]},
            "approved rows must not include expected_policy_ids",
        ),
        ({"input": "headline only"}, "input must be a dict"),
        ({"input": {"landing_page_url": "https://example.com"}}, "input must not include live landing_page_url"),
    ],
)
def test_validate_dataset_rejects_invalid_schema_values(tmp_path, overrides, message) -> None:
    dataset = tmp_path / "real_cases.jsonl"
    _write_jsonl(dataset, [_valid_row(**overrides)])

    with pytest.raises(validate_real_cases.ValidationError, match=message):
        validate_real_cases.validate_dataset(dataset)


def test_validate_dataset_requires_all_fields(tmp_path) -> None:
    dataset = tmp_path / "real_cases.jsonl"
    row = _valid_row()
    del row["source_title"]
    _write_jsonl(dataset, [row])

    with pytest.raises(validate_real_cases.ValidationError, match=r"missing required field\(s\): source_title"):
        validate_real_cases.validate_dataset(dataset)


def test_validate_dataset_fails_duplicate_ids(tmp_path) -> None:
    dataset = tmp_path / "real_cases.jsonl"
    _write_jsonl(dataset, [_valid_row(), _valid_row(source_url="https://example.com/other")])

    with pytest.raises(validate_real_cases.ValidationError, match="duplicate id: case-1"):
        validate_real_cases.validate_dataset(dataset)


def test_validate_dataset_enforces_minimum_rows(tmp_path) -> None:
    dataset = tmp_path / "real_cases.jsonl"
    _write_jsonl(dataset, [_valid_row()])

    with pytest.raises(validate_real_cases.ValidationError, match="expected at least 2 rows, found 1"):
        validate_real_cases.validate_dataset(dataset, min_rows=2)


def test_validate_dataset_enforces_required_decision_counts(tmp_path) -> None:
    dataset = tmp_path / "real_cases.jsonl"
    _write_jsonl(
        dataset,
        [
            _valid_row(id="approved", expected_decision="approved", expected_policy_ids=[]),
            _valid_row(id="review", expected_decision="needs_review"),
        ],
    )

    with pytest.raises(validate_real_cases.ValidationError, match="expected 1 high_risk rows, found 0"):
        validate_real_cases.validate_dataset(
            dataset,
            required_decision_counts={"approved": 1, "needs_review": 1, "high_risk": 1},
        )


def test_cli_accepts_balance_flags(tmp_path, capsys) -> None:
    dataset = tmp_path / "real_cases.jsonl"
    _write_jsonl(
        dataset,
        [
            _valid_row(id="approved", expected_decision="approved", expected_policy_ids=[]),
            _valid_row(id="review", expected_decision="needs_review"),
            _valid_row(id="risk", expected_decision="high_risk"),
        ],
    )

    assert validate_real_cases.main(
        [
            str(dataset),
            "--min-rows",
            "3",
            "--require-decision-count",
            "approved=1",
            "--require-decision-count",
            "needs_review=1",
            "--require-decision-count",
            "high_risk=1",
        ]
    ) == 0

    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == f"OK 3 rows validated: {dataset}\n"


def test_blind_validation_accepts_required_holdout_metadata(tmp_path) -> None:
    dataset = tmp_path / "blind.jsonl"
    _write_jsonl(dataset, [_valid_blind_row()])

    assert validate_real_cases.validate_dataset(dataset, blind=True) == 1


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"source_platform": "reddit"}, "source_platform must be a known blind source platform"),
        ({"source_capture_type": "blog"}, "source_capture_type must be a known blind capture type"),
        ({"ad_observed_status": "served"}, "ad_observed_status must be one of"),
        ({"adjudication_status": "maybe"}, "adjudication_status must be one of"),
        ({"adjudicator_notes": ""}, "accepted blind rows must include adjudicator_notes"),
        ({"rule_tuning_holdout": False}, "accepted blind rows must set rule_tuning_holdout to true"),
        ({"raw_ad_copy": "x" * 241}, "raw_ad_copy must be 240 characters or fewer"),
        ({"source_excerpt": "x" * 241}, "source_excerpt must be 240 characters or fewer"),
        ({"raw_landing_page_html": "<html></html>"}, "blind rows must not include raw_landing_page_html"),
    ],
)
def test_blind_validation_rejects_invalid_holdout_metadata(tmp_path, overrides, message) -> None:
    dataset = tmp_path / "blind.jsonl"
    _write_jsonl(dataset, [_valid_blind_row(**overrides)])

    with pytest.raises(validate_real_cases.ValidationError, match=message):
        validate_real_cases.validate_dataset(dataset, blind=True)


def test_blind_validation_rejects_missing_blind_fields(tmp_path) -> None:
    dataset = tmp_path / "blind.jsonl"
    row = _valid_blind_row()
    del row["source_platform"]
    _write_jsonl(dataset, [row])

    with pytest.raises(validate_real_cases.ValidationError, match=r"missing blind field\(s\): source_platform"):
        validate_real_cases.validate_dataset(dataset, blind=True)


def test_blind_validation_rejects_duplicate_source_urls(tmp_path) -> None:
    dataset = tmp_path / "blind.jsonl"
    _write_jsonl(
        dataset,
        [
            _valid_blind_row(id="blind-1"),
            _valid_blind_row(id="blind-2", input={**_valid_blind_row()["input"], "headline": "Different headline"}),
        ],
    )

    with pytest.raises(validate_real_cases.ValidationError, match="duplicate source_url"):
        validate_real_cases.validate_dataset(dataset, blind=True)


def test_blind_validation_rejects_duplicate_normalized_headlines(tmp_path) -> None:
    dataset = tmp_path / "blind.jsonl"
    _write_jsonl(
        dataset,
        [
            _valid_blind_row(id="blind-1"),
            _valid_blind_row(
                id="blind-2",
                source_url="https://example.com/other",
                input={**_valid_blind_row()["input"], "headline": "Compare credit options!"},
            ),
        ],
    )

    with pytest.raises(validate_real_cases.ValidationError, match="duplicate normalized headline"):
        validate_real_cases.validate_dataset(dataset, blind=True)


def test_cli_reports_validation_errors_to_stderr(tmp_path, capsys) -> None:
    dataset = tmp_path / "real_cases.jsonl"
    _write_jsonl(dataset, [_valid_row(expected_decision="escalate")])

    assert validate_real_cases.main([str(dataset)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "ERROR" in captured.err
    assert "expected_decision must be one of" in captured.err


def test_committed_real_case_dataset_validates() -> None:
    dataset = ROOT / "evals" / "datasets" / "real_cases_v1.jsonl"

    assert validate_real_cases.validate_dataset(
        dataset,
        min_rows=75,
        required_decision_counts={"approved": 25, "needs_review": 25, "high_risk": 25},
    ) == 75

    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert Counter(row["expected_decision"] for row in rows) == {
        "approved": 25,
        "needs_review": 25,
        "high_risk": 25,
    }


def test_committed_real_world_blind_dataset_validates() -> None:
    dataset = ROOT / "evals" / "datasets" / "real_world_blind_v1.jsonl"

    assert validate_real_cases.validate_dataset(
        dataset,
        min_rows=90,
        required_decision_counts={"approved": 30, "needs_review": 30, "high_risk": 30},
        blind=True,
    ) == 90

    rows = [json.loads(line) for line in dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert Counter(row["expected_decision"] for row in rows) == {
        "approved": 30,
        "needs_review": 30,
        "high_risk": 30,
    }
    assert all(row["rule_tuning_holdout"] is True for row in rows)
