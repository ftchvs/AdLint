from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVALS_DIR = ROOT / "evals"
POLICY_COVERAGE_PATH = EVALS_DIR / "policy_coverage.py"
VALIDATOR_PATH = EVALS_DIR / "validate_policy_coverage.py"

if not POLICY_COVERAGE_PATH.exists() or not VALIDATOR_PATH.exists():
    pytest.skip(
        "policy coverage implementation is not available yet",
        allow_module_level=True,
    )

for path in (ROOT, EVALS_DIR):
    path_text = str(path)
    if path_text not in sys.path:
        sys.path.insert(0, path_text)

POLICY_COVERAGE_SPEC = importlib.util.spec_from_file_location("policy_coverage", POLICY_COVERAGE_PATH)
assert POLICY_COVERAGE_SPEC is not None
assert POLICY_COVERAGE_SPEC.loader is not None
policy_coverage = importlib.util.module_from_spec(POLICY_COVERAGE_SPEC)
sys.modules[POLICY_COVERAGE_SPEC.name] = policy_coverage
POLICY_COVERAGE_SPEC.loader.exec_module(policy_coverage)

VALIDATOR_SPEC = importlib.util.spec_from_file_location("validate_policy_coverage", VALIDATOR_PATH)
assert VALIDATOR_SPEC is not None
assert VALIDATOR_SPEC.loader is not None
validate_policy_coverage = importlib.util.module_from_spec(VALIDATOR_SPEC)
sys.modules[VALIDATOR_SPEC.name] = validate_policy_coverage
VALIDATOR_SPEC.loader.exec_module(validate_policy_coverage)


def _write_policy_dir(tmp_path: Path, policies: list[dict[str, Any]]) -> Path:
    policy_dir = tmp_path / "policies"
    policy_dir.mkdir()
    lines = ["policies:"]
    for item in policies:
        lines.extend(
            [
                f"  - id: {item['id']}",
                f"    severity: {item.get('severity', 'medium')}",
                f"    category: {item.get('category', 'test_policy')}",
                f"    modules: {_yaml_list(item.get('modules', ['platform']))}",
            ]
        )
        if "platforms" in item:
            lines.append(f"    platforms: {_yaml_list(item['platforms'])}")
        if "industries" in item:
            lines.append(f"    industries: {_yaml_list(item['industries'])}")
        lines.extend(
            [
                "    signals: [test signal]",
                "    recommended_action: Review the test policy.",
            ]
        )
    (policy_dir / "test_policies.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return policy_dir


def _yaml_list(values: list[str]) -> str:
    return "[" + ", ".join(values) + "]"


def _row(
    *,
    row_id: str = "row-1",
    platform: str = "google",
    industry: str = "health",
    expected_policy_ids: list[str] | None = None,
    actual_policy_ids: list[str] | None = None,
    policy_modules: list[str] | None = None,
) -> dict[str, Any]:
    input_payload: dict[str, Any] = {
        "platform": platform,
        "industry": industry,
        "headline": "Test headline",
        "body": "Test body",
        "cta": "Learn more",
    }
    if policy_modules is not None:
        input_payload["policy_modules"] = policy_modules

    row: dict[str, Any] = {
        "id": row_id,
        "input": input_payload,
        "expected_decision": "needs_review",
        "expected_policy_ids": expected_policy_ids or [],
    }
    if actual_policy_ids is not None:
        row["actual_policy_ids"] = actual_policy_ids
        row["policy_hits"] = [{"policy_id": policy_id} for policy_id in actual_policy_ids]
    return row


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    return path


def _build_tmp_report(
    tmp_path: Path,
    *,
    policies: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    dataset_name: str = "dataset.jsonl",
) -> tuple[Any, Path]:
    policy_dir = _write_policy_dir(tmp_path, policies)
    dataset = _write_jsonl(tmp_path / dataset_name, rows)
    return (
        policy_coverage.build_policy_coverage_report(
            dataset_paths=[dataset],
            policy_dir=policy_dir,
        ),
        dataset,
    )


def _error_text(report: Any) -> str:
    return "\n".join(str(error) for error in report.errors)


def _policy_totals(report: Any) -> dict[str, int]:
    return {
        policy.id: sum(dataset.policy_counts.get(policy.id, 0) for dataset in report.datasets)
        for policy in report.policies
    }


def test_matrix_counts_use_expected_policy_ids_only(tmp_path) -> None:
    report, _dataset = _build_tmp_report(
        tmp_path,
        policies=[
            {"id": "expected_policy"},
            {"id": "actual_only_policy"},
        ],
        rows=[
            _row(
                expected_policy_ids=["expected_policy"],
                actual_policy_ids=["actual_only_policy"],
            )
        ],
    )

    assert report.is_valid
    assert _policy_totals(report) == {
        "expected_policy": 1,
        "actual_only_policy": 0,
    }


def test_unknown_policy_id_reports_dataset_line_row_and_policy_id(tmp_path) -> None:
    report, dataset = _build_tmp_report(
        tmp_path,
        policies=[{"id": "known_policy"}],
        rows=[_row(row_id="bad-row", expected_policy_ids=["unknown_policy"])],
    )

    message = _error_text(report)
    assert not report.is_valid
    assert f"{dataset}:1" in message
    assert "row id bad-row" in message
    assert "policy id unknown_policy" in message
    assert "unknown expected_policy_id" in message


@pytest.mark.parametrize("dataset_name", ["seed_ads.jsonl", "rule_benchmark_v1.jsonl"])
def test_missing_required_dataset_coverage_fails(tmp_path, dataset_name) -> None:
    report, dataset = _build_tmp_report(
        tmp_path,
        policies=[
            {"id": "covered_policy"},
            {"id": "missing_policy"},
        ],
        rows=[_row(expected_policy_ids=["covered_policy"])],
        dataset_name=dataset_name,
    )

    message = _error_text(report)
    assert not report.is_valid
    assert str(dataset) in message
    assert "missing required coverage" in message
    assert "missing_policy" in message


def test_platform_incompatibility_fails(tmp_path) -> None:
    report, dataset = _build_tmp_report(
        tmp_path,
        policies=[{"id": "google_only_policy", "platforms": ["google"]}],
        rows=[_row(platform="tiktok", expected_policy_ids=["google_only_policy"])],
    )

    message = _error_text(report)
    assert not report.is_valid
    assert f"{dataset}:1" in message
    assert "policy id google_only_policy" in message
    assert "input platform tiktok" in message
    assert "policy platforms google" in message


def test_industry_incompatibility_fails(tmp_path) -> None:
    report, dataset = _build_tmp_report(
        tmp_path,
        policies=[{"id": "finance_only_policy", "industries": ["finance"]}],
        rows=[_row(industry="health", expected_policy_ids=["finance_only_policy"])],
    )

    message = _error_text(report)
    assert not report.is_valid
    assert f"{dataset}:1" in message
    assert "policy id finance_only_policy" in message
    assert "input industry health" in message
    assert "policy industries finance" in message


def test_policy_module_incompatibility_uses_default_modules_when_omitted(tmp_path) -> None:
    report, dataset = _build_tmp_report(
        tmp_path,
        policies=[{"id": "custom_module_policy", "modules": ["custom_module"]}],
        rows=[_row(expected_policy_ids=["custom_module_policy"])],
    )

    message = _error_text(report)
    assert not report.is_valid
    assert f"{dataset}:1" in message
    assert "policy id custom_module_policy" in message
    assert "input policy" in message
    assert "policy modules custom_module" in message
    assert "health_claims" in message
    assert "platform" in message


def test_committed_adlint_datasets_validate_successfully() -> None:
    report = policy_coverage.build_policy_coverage_report()

    assert report.is_valid, _error_text(report)
    assert {dataset.path.name for dataset in report.datasets} >= {
        "seed_ads.jsonl",
        "rule_benchmark_v1.jsonl",
    }


def test_policy_coverage_matrix_doc_matches_generated_output() -> None:
    doc_path = ROOT / "docs" / "policy_coverage_matrix.md"
    if not doc_path.exists():
        pytest.skip("docs/policy_coverage_matrix.md does not exist yet")

    generated = policy_coverage.render_policy_coverage_markdown(
        policy_coverage.build_policy_coverage_report()
    )

    assert doc_path.read_text(encoding="utf-8") == generated


def test_cli_check_reports_stale_matrix(tmp_path, capsys) -> None:
    stale = tmp_path / "policy_coverage_matrix.md"
    stale.write_text("stale\n", encoding="utf-8")

    assert validate_policy_coverage.main(["--check", str(stale)]) == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "policy coverage matrix is stale" in captured.err
