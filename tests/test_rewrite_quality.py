from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
REWRITE_QUALITY_PATH = ROOT / "evals" / "rewrite_quality.py"
REWRITE_QUALITY_SPEC = importlib.util.spec_from_file_location("rewrite_quality", REWRITE_QUALITY_PATH)
assert REWRITE_QUALITY_SPEC is not None
assert REWRITE_QUALITY_SPEC.loader is not None
rewrite_quality = importlib.util.module_from_spec(REWRITE_QUALITY_SPEC)
REWRITE_QUALITY_SPEC.loader.exec_module(rewrite_quality)


def test_rewrite_quality_dataset_reports_quality_separately_from_decision_accuracy() -> None:
    rows = rewrite_quality.load_rows(ROOT / "evals" / "datasets" / "rewrite_quality_v1.jsonl")

    metrics = rewrite_quality.evaluate_rows(rows, dataset_path=ROOT / "evals" / "datasets" / "rewrite_quality_v1.jsonl")

    assert metrics["generator"] == "deterministic"
    assert metrics["baseline"] == "deterministic_rules"
    assert metrics["decision_accuracy"] == {
        "measured": False,
        "reason": "Rewrite quality is evaluated separately from decision accuracy.",
    }
    assert set(metrics["rewrite_quality"]["rubric"]) == {
        "clarity",
        "risk_reduction",
        "policy_fit",
        "intent_preservation",
    }
    assert metrics["rewrite_quality"]["pass_rate"] == 1.0
    assert metrics["rewrite_quality"]["overall_average"] >= 4.0
    assert all(result["passed_min_scores"] for result in metrics["results"])


def test_rewrite_quality_cli_writes_eval_metadata_without_raw_submissions(tmp_path, capsys) -> None:
    output_path = tmp_path / "rewrite-quality.json"
    markdown_path = tmp_path / "rewrite-quality.md"
    storage_path = tmp_path / "rewrite-quality.sqlite3"

    exit_code = rewrite_quality.main(
        [
            str(ROOT / "evals" / "datasets" / "rewrite_quality_v1.jsonl"),
            "--output",
            str(output_path),
            "--markdown-output",
            str(markdown_path),
            "--storage-path",
            str(storage_path),
        ]
    )

    assert exit_code == 0
    stdout_metrics = json.loads(capsys.readouterr().out)
    file_metrics = json.loads(output_path.read_text(encoding="utf-8"))
    assert stdout_metrics == file_metrics
    assert "Decision accuracy: not measured by this eval" in markdown_path.read_text(encoding="utf-8")
    assert file_metrics["storage"] == {"enabled": True, "path": str(storage_path)}

    with sqlite3.connect(storage_path) as connection:
        eval_run_count = connection.execute("SELECT COUNT(*) FROM eval_runs").fetchone()[0]
        eval_result_count = connection.execute("SELECT COUNT(*) FROM eval_results").fetchone()[0]
        analysis_run_count = connection.execute("SELECT COUNT(*) FROM analysis_runs").fetchone()[0]

    assert eval_run_count == 1
    assert eval_result_count == len(rewrite_quality.load_rows(ROOT / "evals" / "datasets" / "rewrite_quality_v1.jsonl"))
    assert analysis_run_count == 0
    raw_database = storage_path.read_bytes()
    for raw_value in (
        "Lose 20 pounds in 30 days guaranteed",
        "Our clinically proven supplement melts fat fast.",
        "<html><script src='https://connect.facebook.net/en_US/fbevents.js'>",
    ):
        assert raw_value.encode("utf-8") not in raw_database


def test_rewrite_quality_loader_reports_annotation_schema_errors(tmp_path) -> None:
    dataset = tmp_path / "bad.jsonl"
    dataset.write_text(json.dumps({"id": "missing-checks", "input": {}}), encoding="utf-8")

    with pytest.raises(ValueError, match=r"Missing quality_checks object at .*bad\.jsonl:1"):
        rewrite_quality.load_rows(dataset)
