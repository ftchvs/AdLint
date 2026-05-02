from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

import pytest


RUN_EVAL_PATH = Path(__file__).resolve().parents[1] / "evals" / "run_eval.py"
RUN_EVAL_SPEC = importlib.util.spec_from_file_location("run_eval", RUN_EVAL_PATH)
assert RUN_EVAL_SPEC is not None
assert RUN_EVAL_SPEC.loader is not None
run_eval = importlib.util.module_from_spec(RUN_EVAL_SPEC)
RUN_EVAL_SPEC.loader.exec_module(run_eval)


def test_eval_runner_skips_blank_lines_and_preserves_row_ids(tmp_path) -> None:
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text(
        "\n".join(
            [
                "",
                json.dumps(
                    {
                        "id": "approved-saas",
                        "input": {
                            "platform": "linkedin",
                            "industry": "saas",
                            "headline": "Plan campaign launches",
                            "body": "Coordinate launch notes.",
                            "cta": "Learn more",
                        },
                        "expected_decision": "approved",
                    }
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    rows = run_eval._load_rows(dataset)
    metrics = run_eval._metrics([run_eval._score_row(row) for row in rows])

    assert metrics["total_examples"] == 1
    assert metrics["decision_accuracy"] == 1.0
    assert metrics["results"][0]["id"] == "approved-saas"


def test_eval_runner_reports_dataset_schema_errors_with_line_number(tmp_path) -> None:
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text(
        json.dumps({"id": "missing-label", "input": {"headline": "Missing expected decision"}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"Missing input or expected_decision at .*dataset\.jsonl:1"):
        run_eval._load_rows(dataset)


def test_eval_runner_writes_metrics_output_and_returns_success(tmp_path, monkeypatch, capsys) -> None:
    dataset = tmp_path / "dataset.jsonl"
    output_path = tmp_path / "metrics" / "eval.json"
    dataset.write_text(
        json.dumps(
            {
                "id": "brand-review",
                "input": {
                    "platform": "google",
                    "industry": "general",
                    "headline": "Advertise near election analysis",
                    "body": "Sponsor political coverage during ballot season.",
                    "cta": "Request inventory",
                },
                "expected_decision": "needs_review",
                "expected_policy_ids": ["brand_safety_politics"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["run_eval.py", str(dataset), "--output", str(output_path)])

    assert run_eval.main() == 0

    stdout_metrics = json.loads(capsys.readouterr().out)
    file_metrics = json.loads(output_path.read_text(encoding="utf-8"))
    assert stdout_metrics == file_metrics
    assert stdout_metrics["decision_accuracy"] == 1.0
    assert stdout_metrics["policy_metrics"]["brand_safety_politics"]["recall"] == 1.0
