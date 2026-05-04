from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RESEARCH_LOOP_PATH = ROOT / "evals" / "research_loop.py"
RESEARCH_LOOP_SPEC = importlib.util.spec_from_file_location("research_loop", RESEARCH_LOOP_PATH)
assert RESEARCH_LOOP_SPEC is not None
assert RESEARCH_LOOP_SPEC.loader is not None
research_loop = importlib.util.module_from_spec(RESEARCH_LOOP_SPEC)
RESEARCH_LOOP_SPEC.loader.exec_module(research_loop)


def test_research_loop_dry_run_outputs_safe_plan_without_writing_log(tmp_path, monkeypatch, capsys) -> None:
    log_dir = tmp_path / "research-logs"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "research_loop.py",
            "start",
            "--tag",
            "and-48-smoke",
            "--description",
            "Inspect blind holdout misses.",
            "--dry-run",
            "--log-dir",
            str(log_dir),
        ],
    )

    assert research_loop.main() == 0

    plan = json.loads(capsys.readouterr().out)
    assert plan["status"] == "planned"
    assert plan["tag"] == "and-48-smoke"
    assert plan["description"] == "Inspect blind holdout misses."
    assert plan["isolation"]["mode"] == "dry-run"
    assert "docs/adlint_research_program.md" in plan["allowed_edit_surfaces"]
    assert "evals/datasets/*.jsonl" in plan["protected_file_sets"]
    assert not log_dir.exists()


def test_research_loop_rejects_protected_and_unowned_changes() -> None:
    violations = research_loop._file_set_violations(
        [
            "docs/adlint_research_program.md",
            "evals/datasets/seed_ads.jsonl",
            "adlint/engine.py",
        ]
    )

    assert violations == [
        {
            "path": "adlint/engine.py",
            "reason": "outside_allowed_edit_surfaces",
        },
        {
            "path": "evals/datasets/seed_ads.jsonl",
            "reason": "protected_file_set",
        },
    ]


def test_research_loop_reports_missing_compact_baseline_summary() -> None:
    with pytest.raises(research_loop.ResearchLoopError, match="No compact eval summary"):
        research_loop._parse_compact_summary("validation ok\n")


def test_research_loop_raises_on_nonzero_validation_failure(tmp_path) -> None:
    command = research_loop.ResearchCommand(
        name="failing-validation",
        argv=[sys.executable, "-c", "import sys; sys.exit(7)"],
        kind="validation",
    )

    with pytest.raises(research_loop.ResearchLoopError, match="failing-validation failed with exit code 7"):
        research_loop._run_command(command, cwd=tmp_path)


def test_research_loop_records_baseline_summary_to_untracked_log(tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# test repo\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=AdLint Test",
            "-c",
            "user.email=adlint@example.test",
            "commit",
            "-m",
            "init",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    summary = {
        "summary_version": 1,
        "dataset": "evals/datasets/seed_ads.jsonl",
        "mode": "rule-only",
        "total_rows": 1,
        "scored_rows": 1,
        "skipped_rows": 0,
        "decision_accuracy": 1.0,
        "decision_mismatch_count": 0,
        "confusion_matrix_deltas": [],
        "policy_false_positive_count": 0,
        "policy_false_negative_count": 0,
        "top_review_note_row_ids": {
            "decision_mismatches": [],
            "policy_false_positives": [],
            "policy_false_negatives": [],
        },
        "model_status_counts": {},
        "elapsed_seconds": 0.01,
    }
    command = research_loop.ResearchCommand(
        name="seed",
        argv=[sys.executable, "-c", f"print({json.dumps(json.dumps(summary))})"],
        kind="baseline",
    )

    result = research_loop._run_start(
        tag="and-48-log",
        description="Capture a compact baseline.",
        mode="current-worktree",
        baseline_commands=[command],
        candidate_commands=[],
        validation_commands=[],
        log_dir=tmp_path / "logs",
        repo_path=repo,
    )

    log_path = Path(result["log_path"])
    assert result["status"] == "completed"
    assert result["baseline_summaries"][0]["dataset"] == "evals/datasets/seed_ads.jsonl"
    assert log_path.exists()
    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert [record["event"] for record in records] == ["start", "baseline_summary", "complete"]
    assert records[-1]["status"] == "completed"


def test_research_loop_computes_candidate_summary_deltas() -> None:
    baseline = {
        "dataset": "evals/datasets/real_world_blind_v1.jsonl",
        "mode": "rule-only",
        "decision_accuracy": 0.933,
        "scored_rows": 90,
        "skipped_rows": 0,
        "policy_false_positive_count": 7,
        "policy_false_negative_count": 15,
        "confusion_matrix_deltas": [
            {"expected": "needs_review", "actual": "approved", "count": 5},
            {"expected": "needs_review", "actual": "high_risk", "count": 1},
        ],
    }
    candidate = {
        "dataset": "evals/datasets/real_world_blind_v1.jsonl",
        "mode": "rule-only",
        "decision_accuracy": 0.967,
        "scored_rows": 90,
        "skipped_rows": 0,
        "policy_false_positive_count": 7,
        "policy_false_negative_count": 12,
        "confusion_matrix_deltas": [
            {"expected": "needs_review", "actual": "approved", "count": 2},
            {"expected": "needs_review", "actual": "high_risk", "count": 1},
        ],
    }

    assert research_loop._summary_deltas([baseline], [candidate]) == [
        {
            "dataset": "evals/datasets/real_world_blind_v1.jsonl",
            "mode": "rule-only",
            "decision_accuracy_delta": 0.034,
            "scored_rows_delta": 0,
            "skipped_rows_delta": 0,
            "policy_false_positive_delta": 0,
            "policy_false_negative_delta": -3,
            "confusion_mismatch_delta": -3,
        }
    ]
