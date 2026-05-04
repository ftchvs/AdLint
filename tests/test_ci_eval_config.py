from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _make_target_block(makefile: str, target: str) -> str:
    marker = f"\n{target}:"
    start = makefile.index(marker) + 1
    next_target = makefile.find("\n\n", start)
    return makefile[start:] if next_target == -1 else makefile[start:next_target]


def test_ci_eval_targets_use_summary_output_and_nonzero_thresholds() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    real_cases = _make_target_block(makefile, "real-cases-ci")
    assert "--summary-only" in real_cases
    assert "--min-decision-accuracy 1.0" in real_cases

    blind = _make_target_block(makefile, "real-world-blind-ci")
    assert "--summary-only" in blind
    assert "--min-decision-accuracy 0.90" in blind


def test_github_actions_runs_packaging_gates_and_uploads_eval_artifacts() -> None:
    workflow = (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8")

    assert "make pr-preflight" in workflow
    assert "make real-cases-ci" in workflow
    assert "make real-world-blind-ci" in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "evals/results/*.json" in workflow
    assert "evals/results/*.md" in workflow
