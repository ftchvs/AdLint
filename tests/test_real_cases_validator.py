from __future__ import annotations

import importlib.util
import json
from pathlib import Path

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
        "label_basis": "Published enforcement summary",
        "label_confidence": "high",
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


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_validate_dataset_accepts_valid_rows_and_skips_blanks(tmp_path) -> None:
    dataset = tmp_path / "real_cases.jsonl"
    dataset.write_text(
        "\n"
        + json.dumps(_valid_row())
        + "\n\n"
        + json.dumps(_valid_row(id="case-2", label_confidence="medium", expected_decision="approved"))
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
        ({"expected_policy_ids": "financial_services_review"}, "expected_policy_ids must be a list"),
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

    assert validate_real_cases.validate_dataset(dataset) == 13
