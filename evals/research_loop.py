from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_EDIT_SURFACES = (
    "Makefile",
    "docs/adlint_research_program.md",
    "docs/eval_report.md",
    "docs/research_loop.md",
    "evals/README.md",
    "evals/research_loop.py",
    "evals/run_eval.py",
    "tests/test_eval_runner.py",
    "tests/test_research_loop.py",
)
PROTECTED_FILE_SETS = (
    "evals/datasets/*.jsonl",
    "evals/generate_*dataset.py",
    "evals/preflight_eval_assets.py",
    "evals/real_cases.md",
    "evals/validate_real_cases.py",
    "docs/legal_disclaimer.md",
)
DEFAULT_DATASETS = (
    ("seed", "evals/datasets/seed_ads.jsonl"),
    ("benchmark", "evals/datasets/rule_benchmark_v1.jsonl"),
    ("real_cases", "evals/datasets/real_cases_v1.jsonl"),
    ("blind_holdout", "evals/datasets/real_world_blind_v1.jsonl"),
)
LOG_DIR = Path("logs/research_loop")


class ResearchLoopError(RuntimeError):
    pass


class ResearchCommand:
    def __init__(self, *, name: str, argv: list[str], kind: str = "baseline") -> None:
        self.name = name
        self.argv = argv
        self.kind = kind

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "argv": self.argv,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run sandboxed AdLint research-loop checks.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    start_parser = subparsers.add_parser("start", help="Plan or run a research-loop baseline capture.")
    start_parser.add_argument("--tag", default=_default_tag(), help="Stable run tag used in logs and branch plans.")
    start_parser.add_argument("--description", default="", help="Short experiment description.")
    start_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the safe plan without creating branches, worktrees, logs, or running baselines.",
    )
    start_parser.add_argument(
        "--worktree",
        action="store_true",
        help="Create an isolated worktree plan target. Baselines still run only when --dry-run is omitted.",
    )
    start_parser.add_argument(
        "--baseline-command",
        action="append",
        default=[],
        help="Extra or replacement compact-summary command as name::command. Repeatable.",
    )
    start_parser.add_argument(
        "--candidate-command",
        action="append",
        default=[],
        help="Post-change compact-summary command as name::command. Repeatable and compared to baselines.",
    )
    start_parser.add_argument(
        "--validation-command",
        action="append",
        default=[],
        help="Validation command as name::command. Repeatable and fails the run on non-zero exit.",
    )
    start_parser.add_argument(
        "--no-default-baselines",
        action="store_true",
        help="Use only --baseline-command values instead of the default four rule-only baselines.",
    )
    start_parser.add_argument(
        "--log-dir",
        default=str(LOG_DIR),
        help="Ignored directory for JSONL research logs.",
    )

    discard_parser = subparsers.add_parser("discard", help="Print or execute a safe discard plan.")
    discard_parser.add_argument("--tag", required=True, help="Run tag to discard.")
    discard_parser.add_argument(
        "--execute",
        action="store_true",
        help="Restore only allowed tracked edit surfaces. Untracked files are left for manual review.",
    )

    args = parser.parse_args()
    repo_path = Path(__file__).resolve().parents[1]

    try:
        if args.command == "start":
            baseline_commands = _commands_from_args(
                args.baseline_command,
                default=[] if args.no_default_baselines else _default_baseline_commands(),
                kind="baseline",
            )
            validation_commands = _commands_from_args(args.validation_command, default=[], kind="validation")
            candidate_commands = _commands_from_args(args.candidate_command, default=[], kind="candidate")
            mode = "dry-run" if args.dry_run else "worktree" if args.worktree else "current-worktree"
            if args.dry_run:
                print(
                    json.dumps(
                        _dry_run_plan(
                            tag=args.tag,
                            description=args.description,
                            mode=mode,
                            baseline_commands=baseline_commands,
                            candidate_commands=candidate_commands,
                            validation_commands=validation_commands,
                            log_dir=Path(args.log_dir),
                            repo_path=repo_path,
                        ),
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 0
            result = _run_start(
                tag=args.tag,
                description=args.description,
                mode=mode,
                baseline_commands=baseline_commands,
                candidate_commands=candidate_commands,
                validation_commands=validation_commands,
                log_dir=Path(args.log_dir),
                repo_path=repo_path,
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0

        if args.command == "discard":
            plan = _discard_plan(tag=args.tag, repo_path=repo_path)
            if args.execute:
                _execute_discard_plan(plan, repo_path=repo_path)
                plan["status"] = "discarded"
            print(json.dumps(plan, indent=2, sort_keys=True))
            return 0
    except ResearchLoopError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1

    raise AssertionError(f"unhandled command {args.command}")


def _default_tag() -> str:
    return datetime.now(timezone.utc).strftime("research-%Y%m%d-%H%M%S")


def _default_baseline_commands() -> list[ResearchCommand]:
    commands: list[ResearchCommand] = []
    for name, dataset in DEFAULT_DATASETS:
        commands.append(
            ResearchCommand(
                name=name,
                kind="baseline",
                argv=[
                    sys.executable,
                    "evals/run_eval.py",
                    dataset,
                    "--summary-only",
                    "--summary-format",
                    "json",
                    "--min-decision-accuracy",
                    "0",
                ],
            )
        )
    return commands


def _commands_from_args(
    specs: list[str],
    *,
    default: list[ResearchCommand],
    kind: str,
) -> list[ResearchCommand]:
    if not specs:
        return default
    commands: list[ResearchCommand] = []
    for index, spec in enumerate(specs, start=1):
        if "::" in spec:
            name, command = spec.split("::", 1)
        else:
            name, command = f"{kind}-{index}", spec
        argv = shlex.split(command)
        if not argv:
            raise ResearchLoopError(f"{name} has an empty command")
        commands.append(ResearchCommand(name=name, argv=argv, kind=kind))
    return commands


def _dry_run_plan(
    *,
    tag: str,
    description: str,
    mode: str,
    baseline_commands: list[ResearchCommand],
    candidate_commands: list[ResearchCommand],
    validation_commands: list[ResearchCommand],
    log_dir: Path,
    repo_path: Path,
) -> dict[str, Any]:
    return {
        "status": "planned",
        "tag": tag,
        "description": description,
        "isolation": {
            "mode": mode,
            "branch": f"codex/research/{tag}",
            "worktree": str(repo_path / ".research-worktrees" / tag),
        },
        "baseline_commands": [command.to_dict() for command in baseline_commands],
        "candidate_commands": [command.to_dict() for command in candidate_commands],
        "validation_commands": [command.to_dict() for command in validation_commands],
        "allowed_edit_surfaces": list(ALLOWED_EDIT_SURFACES),
        "protected_file_sets": list(PROTECTED_FILE_SETS),
        "log_path": str(log_dir / f"{tag}.jsonl"),
    }


def _run_start(
    *,
    tag: str,
    description: str,
    mode: str,
    baseline_commands: list[ResearchCommand],
    candidate_commands: list[ResearchCommand],
    validation_commands: list[ResearchCommand],
    log_dir: Path,
    repo_path: Path,
) -> dict[str, Any]:
    if not baseline_commands:
        raise ResearchLoopError("No baseline commands configured")

    started = time.perf_counter()
    commit_hash = _git_output(["rev-parse", "HEAD"], cwd=repo_path).strip()
    run_repo_path = repo_path
    isolation = {
        "mode": mode,
        "branch": None,
        "worktree": None,
    }
    if mode == "worktree":
        branch = f"codex/research/{tag}"
        run_repo_path = repo_path / ".research-worktrees" / tag
        _create_worktree(repo_path=repo_path, worktree_path=run_repo_path, branch=branch)
        isolation = {
            "mode": mode,
            "branch": branch,
            "worktree": str(run_repo_path),
        }
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{tag}.jsonl"
    start_record = {
        "event": "start",
        "tag": tag,
        "description": description,
        "isolation": isolation,
        "commit_hash": commit_hash,
        "allowed_edit_surfaces": list(ALLOWED_EDIT_SURFACES),
        "protected_file_sets": list(PROTECTED_FILE_SETS),
    }
    _append_jsonl(log_path, start_record)

    baseline_summaries: list[dict[str, Any]] = []
    candidate_summaries: list[dict[str, Any]] = []
    validation_results: list[dict[str, Any]] = []
    try:
        for command in validation_commands:
            result = _run_command(command, cwd=run_repo_path)
            validation_results.append(_command_record(command, result))
            _append_jsonl(log_path, {"event": "validation_result", **validation_results[-1]})

        for command in baseline_commands:
            result = _run_command(command, cwd=run_repo_path)
            summary = _parse_compact_summary(result["stdout"])
            baseline_summaries.append(summary)
            _append_jsonl(
                log_path,
                {
                    "event": "baseline_summary",
                    "command": command.name,
                    "summary": summary,
                },
            )

        for command in candidate_commands:
            result = _run_command(command, cwd=run_repo_path)
            summary = _parse_compact_summary(result["stdout"])
            candidate_summaries.append(summary)
            _append_jsonl(
                log_path,
                {
                    "event": "candidate_summary",
                    "command": command.name,
                    "summary": summary,
                },
            )

        if not baseline_summaries:
            raise ResearchLoopError("No compact eval summary was captured from baseline commands")

        changed_files = _git_changed_files(run_repo_path)
        violations = _file_set_violations(changed_files)
        if violations:
            raise ResearchLoopError(f"Protected or unowned file changes detected: {violations}")

        deltas = _summary_deltas(baseline_summaries, candidate_summaries)
        elapsed = round(time.perf_counter() - started, 3)
        complete_record = {
            "event": "complete",
            "status": "completed",
            "tag": tag,
            "description": description,
            "commit_hash": commit_hash,
            "isolation": isolation,
            "deltas": deltas,
            "changed_files": changed_files,
            "elapsed_seconds": elapsed,
        }
        _append_jsonl(log_path, complete_record)
        return {
            "status": "completed",
            "tag": tag,
            "description": description,
            "mode": mode,
            "commit_hash": commit_hash,
            "isolation": isolation,
            "baseline_summaries": baseline_summaries,
            "candidate_summaries": candidate_summaries,
            "validation_results": validation_results,
            "deltas": deltas,
            "changed_files": changed_files,
            "elapsed_seconds": elapsed,
            "log_path": str(log_path),
        }
    except ResearchLoopError as exc:
        _append_jsonl(
            log_path,
            {
                "event": "complete",
                "status": "failed",
                "tag": tag,
                "error": str(exc),
                "elapsed_seconds": round(time.perf_counter() - started, 3),
            },
        )
        raise


def _run_command(command: ResearchCommand, *, cwd: Path) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(cwd) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    completed = subprocess.run(
        command.argv,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    result = {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    if completed.returncode != 0:
        raise ResearchLoopError(f"{command.name} failed with exit code {completed.returncode}")
    return result


def _create_worktree(*, repo_path: Path, worktree_path: Path, branch: str) -> None:
    if worktree_path.exists():
        raise ResearchLoopError(f"worktree path already exists: {worktree_path}")
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ["git", "worktree", "add", "-b", branch, str(worktree_path), "HEAD"],
        cwd=repo_path,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise ResearchLoopError(f"git worktree add failed with exit code {completed.returncode}: {completed.stderr}")


def _command_record(command: ResearchCommand, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": command.name,
        "kind": command.kind,
        "argv": command.argv,
        "exit_code": result["exit_code"],
    }


def _parse_compact_summary(output: str) -> dict[str, Any]:
    for line in reversed(output.splitlines()):
        candidate = line.strip()
        if not candidate.startswith("{"):
            continue
        try:
            summary = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if _is_compact_summary(summary):
            return summary
    raise ResearchLoopError("No compact eval summary found in command output")


def _is_compact_summary(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if value.get("summary_version") != 1:
        return False
    if value.get("mode") == "all":
        return "dataset" in value and isinstance(value.get("modes"), dict)
    required_keys = {
        "dataset",
        "mode",
        "total_rows",
        "scored_rows",
        "skipped_rows",
        "decision_accuracy",
        "decision_mismatch_count",
        "confusion_matrix_deltas",
        "policy_false_positive_count",
        "policy_false_negative_count",
        "top_review_note_row_ids",
        "model_status_counts",
        "elapsed_seconds",
    }
    return required_keys <= set(value)


def _summary_deltas(
    baseline_summaries: list[dict[str, Any]],
    candidate_summaries: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not candidate_summaries:
        return []

    baseline_by_key = {_summary_key(summary): summary for summary in baseline_summaries}
    deltas: list[dict[str, Any]] = []
    for candidate in sorted(candidate_summaries, key=_summary_key):
        key = _summary_key(candidate)
        baseline = baseline_by_key.get(key)
        if baseline is None:
            continue
        deltas.append(
            {
                "dataset": candidate.get("dataset", "<unknown>"),
                "mode": candidate.get("mode", "<unknown>"),
                "decision_accuracy_delta": round(
                    float(candidate.get("decision_accuracy", 0.0))
                    - float(baseline.get("decision_accuracy", 0.0)),
                    3,
                ),
                "scored_rows_delta": int(candidate.get("scored_rows", 0)) - int(baseline.get("scored_rows", 0)),
                "skipped_rows_delta": int(candidate.get("skipped_rows", 0)) - int(baseline.get("skipped_rows", 0)),
                "policy_false_positive_delta": int(candidate.get("policy_false_positive_count", 0))
                - int(baseline.get("policy_false_positive_count", 0)),
                "policy_false_negative_delta": int(candidate.get("policy_false_negative_count", 0))
                - int(baseline.get("policy_false_negative_count", 0)),
                "confusion_mismatch_delta": _confusion_mismatch_count(candidate)
                - _confusion_mismatch_count(baseline),
            }
        )
    return deltas


def _summary_key(summary: dict[str, Any]) -> tuple[str, str]:
    return (str(summary.get("dataset", "")), str(summary.get("mode", "")))


def _confusion_mismatch_count(summary: dict[str, Any]) -> int:
    return sum(int(item.get("count", 0)) for item in summary.get("confusion_matrix_deltas", []))


def _git_changed_files(repo_path: Path) -> list[str]:
    status = _git_output(["status", "--porcelain=v1"], cwd=repo_path)
    changed: list[str] = []
    for line in status.splitlines():
        if not line:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        changed.append(_normalize_path(path))
    return sorted(changed)


def _file_set_violations(paths: list[str]) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for path in sorted(_normalize_path(item) for item in paths):
        if _matches_any(path, PROTECTED_FILE_SETS):
            violations.append({"path": path, "reason": "protected_file_set"})
            continue
        if not _matches_any(path, ALLOWED_EDIT_SURFACES):
            violations.append({"path": path, "reason": "outside_allowed_edit_surfaces"})
    return violations


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    return any(path == pattern or fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _normalize_path(path: str) -> str:
    return path.removeprefix("./")


def _discard_plan(*, tag: str, repo_path: Path) -> dict[str, Any]:
    changed_files = _git_changed_files(repo_path)
    violations = _file_set_violations(changed_files)
    restore_paths = [
        path
        for path in changed_files
        if _matches_any(path, ALLOWED_EDIT_SURFACES) and not _matches_any(path, PROTECTED_FILE_SETS)
    ]
    return {
        "status": "discard_plan",
        "tag": tag,
        "restore_paths": restore_paths,
        "violations": violations,
        "commands": [
            ["git", "restore", "--staged", "--", *restore_paths],
            ["git", "restore", "--worktree", "--", *restore_paths],
        ]
        if restore_paths
        else [],
    }


def _execute_discard_plan(plan: dict[str, Any], *, repo_path: Path) -> None:
    if plan.get("violations"):
        raise ResearchLoopError(f"Refusing discard while protected or unowned changes exist: {plan['violations']}")
    for command in plan.get("commands", []):
        if len(command) <= 4:
            continue
        completed = subprocess.run(command, cwd=repo_path, text=True, capture_output=True, check=False)
        if completed.returncode != 0:
            raise ResearchLoopError(f"discard command failed with exit code {completed.returncode}: {command}")


def _git_output(args: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise ResearchLoopError(f"git {' '.join(args)} failed with exit code {completed.returncode}")
    return completed.stdout


def _append_jsonl(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
