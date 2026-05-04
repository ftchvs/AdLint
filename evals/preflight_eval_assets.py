from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, NamedTuple


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_TRACKED_PATHS = (
    "evals/preflight_eval_assets.py",
    "evals/collect_real_world_candidates.py",
    "evals/generate_real_cases_dataset.py",
    "evals/generate_real_world_blind_dataset.py",
    "evals/datasets/real_cases_v1.jsonl",
    "evals/datasets/real_world_blind_v1.jsonl",
)


class GeneratedDataset(NamedTuple):
    dataset: str
    generator: str


GENERATED_DATASETS = (
    GeneratedDataset("evals/datasets/real_cases_v1.jsonl", "evals/generate_real_cases_dataset.py"),
    GeneratedDataset("evals/datasets/real_world_blind_v1.jsonl", "evals/generate_real_world_blind_dataset.py"),
)


class PreflightError(ValueError):
    pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate eval assets before packaging an AdLint PR.")
    parser.add_argument(
        "--repo-root",
        default=str(ROOT),
        help="Repository root to validate. Defaults to the current AdLint checkout.",
    )
    args = parser.parse_args(argv)

    try:
        check_preflight(Path(args.repo_root))
    except PreflightError as exc:
        print(f"ERROR eval PR preflight failed:\n{exc}", file=sys.stderr)
        return 1

    print("OK eval PR preflight passed")
    return 0


def check_preflight(
    repo_root: Path | str = ROOT,
    *,
    required_paths: tuple[str, ...] = REQUIRED_TRACKED_PATHS,
    generated_datasets: tuple[GeneratedDataset, ...] = GENERATED_DATASETS,
) -> None:
    root = Path(repo_root)
    errors: list[str] = []

    missing = [path for path in required_paths if not (root / path).exists()]
    if missing:
        errors.append("missing required file(s): " + ", ".join(missing))

    untracked = _untracked_paths(root, required_paths)
    if untracked:
        errors.append(
            "required file(s) are not tracked by Git: "
            + ", ".join(untracked)
            + ". Stage the generated eval assets before opening the PR."
        )

    for dataset in generated_datasets:
        try:
            _check_generated_dataset(root, dataset)
        except PreflightError as exc:
            errors.append(str(exc))

    if errors:
        raise PreflightError("\n".join(f"- {error}" for error in errors))


def _untracked_paths(repo_root: Path, required_paths: tuple[str, ...]) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "--", *required_paths],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise PreflightError((result.stderr or result.stdout or "git ls-files failed").strip())
    tracked = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return [path for path in required_paths if path not in tracked]


def _check_generated_dataset(repo_root: Path, dataset: GeneratedDataset) -> None:
    dataset_path = repo_root / dataset.dataset
    generator_path = repo_root / dataset.generator
    if not dataset_path.exists() or not generator_path.exists():
        return

    actual_rows = _load_jsonl(dataset_path)
    generated_rows = _load_generated_rows(generator_path)
    if actual_rows != generated_rows:
        raise PreflightError(_dataset_mismatch_message(dataset, actual_rows, generated_rows))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PreflightError(f"{path}: invalid JSON at line {line_number}: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise PreflightError(f"{path}: line {line_number} is not a JSON object")
        rows.append(row)
    return rows


def _load_generated_rows(path: Path) -> list[dict[str, Any]]:
    spec = importlib.util.spec_from_file_location(f"_adlint_preflight_{path.stem}", path)
    if spec is None or spec.loader is None:
        raise PreflightError(f"{path}: could not load generator module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    build_rows = getattr(module, "build_rows", None)
    if build_rows is None:
        raise PreflightError(f"{path}: missing build_rows()")
    rows = build_rows()
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise PreflightError(f"{path}: build_rows() must return a list of row dicts")
    return rows


def _dataset_mismatch_message(
    dataset: GeneratedDataset,
    actual_rows: list[dict[str, Any]],
    generated_rows: list[dict[str, Any]],
) -> str:
    rerun = f"python {dataset.generator}"
    if len(actual_rows) != len(generated_rows):
        return (
            f"{dataset.dataset} is stale: committed row count {len(actual_rows)} "
            f"does not match generated row count {len(generated_rows)}. Rerun `{rerun}`."
        )

    for index, (actual, generated) in enumerate(zip(actual_rows, generated_rows, strict=True), start=1):
        if actual == generated:
            continue
        actual_id = actual.get("id", "<missing>")
        generated_id = generated.get("id", "<missing>")
        changed_keys = sorted({*actual.keys(), *generated.keys()} - {key for key in actual if actual.get(key) == generated.get(key)})
        suffix = f"; changed key(s): {', '.join(changed_keys[:8])}" if changed_keys else ""
        return (
            f"{dataset.dataset} is stale at row {index}: committed id `{actual_id}` "
            f"does not match generated id `{generated_id}`{suffix}. Rerun `{rerun}`."
        )

    return f"{dataset.dataset} is stale. Rerun `{rerun}`."


if __name__ == "__main__":
    raise SystemExit(main())
