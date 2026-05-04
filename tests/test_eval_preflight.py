from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT_PATH = ROOT / "evals" / "preflight_eval_assets.py"
PREFLIGHT_SPEC = importlib.util.spec_from_file_location("preflight_eval_assets", PREFLIGHT_PATH)
assert PREFLIGHT_SPEC is not None
assert PREFLIGHT_SPEC.loader is not None
preflight_eval_assets = importlib.util.module_from_spec(PREFLIGHT_SPEC)
PREFLIGHT_SPEC.loader.exec_module(preflight_eval_assets)


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True, text=True)


def _write_generator(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "from __future__ import annotations\n\n"
        "def build_rows():\n"
        f"    return {rows!r}\n",
        encoding="utf-8",
    )


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def test_preflight_rejects_untracked_required_file(tmp_path) -> None:
    _init_repo(tmp_path)
    required = tmp_path / "evals" / "generated.py"
    required.parent.mkdir(parents=True, exist_ok=True)
    required.write_text("print('exists but is not tracked')\n", encoding="utf-8")

    with pytest.raises(preflight_eval_assets.PreflightError, match="not tracked by Git"):
        preflight_eval_assets.check_preflight(
            tmp_path,
            required_paths=("evals/generated.py",),
            generated_datasets=(),
        )


def test_preflight_rejects_missing_required_file(tmp_path) -> None:
    _init_repo(tmp_path)

    with pytest.raises(preflight_eval_assets.PreflightError, match="missing required file"):
        preflight_eval_assets.check_preflight(
            tmp_path,
            required_paths=("evals/missing.py",),
            generated_datasets=(),
        )


def test_preflight_rejects_stale_generated_dataset(tmp_path) -> None:
    _init_repo(tmp_path)
    generator = tmp_path / "evals" / "generate_rows.py"
    dataset = tmp_path / "evals" / "datasets" / "rows.jsonl"
    generated_rows = [{"id": "fresh", "expected_decision": "approved", "input": {}}]
    committed_rows = [{"id": "stale", "expected_decision": "approved", "input": {}}]
    _write_generator(generator, generated_rows)
    _write_jsonl(dataset, committed_rows)
    subprocess.run(["git", "add", "evals/generate_rows.py", "evals/datasets/rows.jsonl"], cwd=tmp_path, check=True)

    with pytest.raises(preflight_eval_assets.PreflightError, match="is stale at row 1"):
        preflight_eval_assets.check_preflight(
            tmp_path,
            required_paths=("evals/generate_rows.py", "evals/datasets/rows.jsonl"),
            generated_datasets=(
                preflight_eval_assets.GeneratedDataset("evals/datasets/rows.jsonl", "evals/generate_rows.py"),
            ),
        )


def test_preflight_accepts_tracked_fresh_generated_dataset(tmp_path) -> None:
    _init_repo(tmp_path)
    generator = tmp_path / "evals" / "generate_rows.py"
    dataset = tmp_path / "evals" / "datasets" / "rows.jsonl"
    rows = [{"id": "fresh", "expected_decision": "approved", "input": {}}]
    _write_generator(generator, rows)
    _write_jsonl(dataset, rows)
    subprocess.run(["git", "add", "evals/generate_rows.py", "evals/datasets/rows.jsonl"], cwd=tmp_path, check=True)

    preflight_eval_assets.check_preflight(
        tmp_path,
        required_paths=("evals/generate_rows.py", "evals/datasets/rows.jsonl"),
        generated_datasets=(
            preflight_eval_assets.GeneratedDataset("evals/datasets/rows.jsonl", "evals/generate_rows.py"),
        ),
    )
