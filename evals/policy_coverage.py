from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Iterable, Sequence

import yaml

from adlint.policy import DEFAULT_MODULES


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_PATHS = (
    REPO_ROOT / "evals" / "datasets" / "seed_ads.jsonl",
    REPO_ROOT / "evals" / "datasets" / "rule_benchmark_v1.jsonl",
    REPO_ROOT / "evals" / "datasets" / "real_cases_v1.jsonl",
)
REQUIRED_COMPLETE_DATASET_NAMES = {
    "seed_ads.jsonl",
    "rule_benchmark_v1.jsonl",
}


class PolicyCoverageError(ValueError):
    pass


class ValidationError(PolicyCoverageError):
    pass


@dataclass(frozen=True)
class CoverageValidationError:
    message: str
    dataset_path: Path | None = None
    line_number: int | None = None
    row_id: str | None = None
    policy_id: str | None = None

    def __str__(self) -> str:
        prefix_parts: list[str] = []
        if self.dataset_path is not None:
            location = str(self.dataset_path)
            if self.line_number is not None:
                location = f"{location}:{self.line_number}"
            prefix_parts.append(location)
        if self.row_id is not None:
            prefix_parts.append(f"row id {self.row_id}")
        if self.policy_id is not None:
            prefix_parts.append(f"policy id {self.policy_id}")
        if prefix_parts:
            return f"{': '.join(prefix_parts)}: {self.message}"
        return self.message


@dataclass(frozen=True)
class PolicyInventoryItem:
    id: str
    category: str
    modules: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()
    industries: tuple[str, ...] = ()
    source_path: str = ""


@dataclass(frozen=True)
class DatasetCoverage:
    path: Path
    row_count: int = 0
    policy_counts: Counter[str] = field(default_factory=Counter)
    required_complete: bool = False

    @property
    def label(self) -> str:
        return self.path.stem


@dataclass(frozen=True)
class CoverageRow:
    policy: PolicyInventoryItem
    counts: dict[str, int]
    total: int


@dataclass(frozen=True)
class PolicyCoverageReport:
    policies: tuple[PolicyInventoryItem, ...]
    datasets: tuple[DatasetCoverage, ...]
    errors: tuple[CoverageValidationError, ...]

    @property
    def is_valid(self) -> bool:
        return not self.errors

    @property
    def total_row_count(self) -> int:
        return sum(dataset.row_count for dataset in self.datasets)

    @property
    def total_policy_count(self) -> int:
        return len(self.policies)

    @property
    def rows(self) -> tuple[CoverageRow, ...]:
        rows: list[CoverageRow] = []
        for policy in self.policies:
            counts = {
                dataset.path.name: dataset.policy_counts.get(policy.id, 0)
                for dataset in self.datasets
            }
            rows.append(CoverageRow(policy=policy, counts=counts, total=sum(counts.values())))
        return tuple(rows)


def load_bundled_policy_inventory(
    policy_dir: str | Path | None = None,
) -> tuple[PolicyInventoryItem, ...]:
    policy_root = (
        Path(policy_dir)
        if policy_dir is not None
        else resources.files("adlint").joinpath("policies")
    )
    policy_files = sorted(
        item
        for item in policy_root.iterdir()
        if item.is_file() and item.name.endswith(".yml")
    )

    policies: list[PolicyInventoryItem] = []
    policy_sources: dict[str, list[str]] = {}
    for policy_file in policy_files:
        raw = yaml.safe_load(policy_file.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or not isinstance(raw.get("policies"), list):
            raise PolicyCoverageError(f"{policy_file}: policy file must contain a policies list")

        for item in raw["policies"]:
            if not isinstance(item, dict):
                raise PolicyCoverageError(f"{policy_file}: policy item must be a mapping")
            policy_id = str(item.get("id", ""))
            if not policy_id:
                raise PolicyCoverageError(f"{policy_file}: policy item must include an id")
            source_path = _display_path(Path(str(policy_file)))
            policy_sources.setdefault(policy_id, []).append(source_path)
            policies.append(
                PolicyInventoryItem(
                    id=policy_id,
                    category=str(item.get("category", "")),
                    modules=_string_tuple(item.get("modules", ()), lower=True),
                    platforms=_string_tuple(item.get("platforms", ()), lower=True),
                    industries=_string_tuple(item.get("industries", ()), lower=True),
                    source_path=source_path,
                )
            )

    duplicates = {
        policy_id: sources
        for policy_id, sources in sorted(policy_sources.items())
        if len(sources) > 1
    }
    if duplicates:
        duplicate_details = "; ".join(
            f"{policy_id} in {', '.join(sources)}" for policy_id, sources in duplicates.items()
        )
        raise PolicyCoverageError(f"duplicate bundled policy id(s): {duplicate_details}")

    return tuple(sorted(policies, key=lambda policy: policy.id))


def build_policy_coverage_report(
    dataset_paths: Sequence[str | Path] = DEFAULT_DATASET_PATHS,
    *,
    policy_dir: str | Path | None = None,
    required_complete_dataset_names: Iterable[str] = REQUIRED_COMPLETE_DATASET_NAMES,
) -> PolicyCoverageReport:
    policies = (
        load_bundled_policy_inventory()
        if policy_dir is None
        else load_bundled_policy_inventory(policy_dir)
    )
    policies_by_id = {policy.id: policy for policy in policies}
    all_errors: list[CoverageValidationError] = []
    datasets: list[DatasetCoverage] = []
    required_names = set(required_complete_dataset_names)

    for raw_path in dataset_paths:
        dataset_path = Path(raw_path)
        dataset, errors = _read_dataset_coverage(dataset_path, policies_by_id, required_names)
        all_errors.extend(errors)
        if dataset.required_complete:
            all_errors.extend(_missing_required_coverage_errors(dataset, policies))
        datasets.append(dataset)

    return PolicyCoverageReport(
        policies=policies,
        datasets=tuple(datasets),
        errors=tuple(all_errors),
    )


def build_coverage_report(
    *,
    policy_dir: str | Path | None = None,
    dataset_paths: Sequence[str | Path] = DEFAULT_DATASET_PATHS,
    required_dataset_names: Iterable[str] = REQUIRED_COMPLETE_DATASET_NAMES,
) -> PolicyCoverageReport:
    return build_policy_coverage_report(
        dataset_paths=dataset_paths,
        policy_dir=policy_dir,
        required_complete_dataset_names=required_dataset_names,
    )


def render_markdown(report: PolicyCoverageReport) -> str:
    return render_policy_coverage_markdown(report)


def render_policy_coverage_markdown(report: PolicyCoverageReport) -> str:
    status = "OK" if report.is_valid else f"ERROR ({len(report.errors)} error(s))"
    lines = [
        "# Policy Coverage Matrix",
        "",
        f"Validation status: {status}",
        f"Total bundled policy count: {len(report.policies)}",
        f"Total dataset row count: {report.total_row_count}",
        "",
        "## Dataset Row Counts",
        "",
        "| Dataset | Rows | Coverage requirement |",
        "| --- | ---: | --- |",
    ]

    for dataset in sorted(report.datasets, key=lambda item: item.path.name):
        requirement = "required complete" if dataset.required_complete else "diagnostic only"
        lines.append(
            f"| {_markdown_escape(_display_path(dataset.path))} | {dataset.row_count} | {requirement} |"
        )

    if report.errors:
        lines.extend(["", "## Validation Errors", ""])
        for error in report.errors:
            lines.append(f"- {_markdown_escape(str(error))}")

    dataset_columns = list(report.datasets)
    lines.extend(
        [
            "",
            "## Coverage",
            "",
            _coverage_table_header(dataset_columns),
            _coverage_table_separator(dataset_columns),
        ]
    )

    for policy in report.policies:
        dataset_counts = [
            dataset.policy_counts.get(policy.id, 0) for dataset in dataset_columns
        ]
        total_count = sum(dataset_counts)
        row = [
            policy.id,
            policy.category,
            _join_filter(policy.modules),
            _join_filter(policy.platforms),
            _join_filter(policy.industries),
            *(str(count) for count in dataset_counts),
            str(total_count),
        ]
        lines.append("| " + " | ".join(_markdown_escape(value) for value in row) + " |")

    return "\n".join(lines) + "\n"


def _read_dataset_coverage(
    dataset_path: Path,
    policies_by_id: dict[str, PolicyInventoryItem],
    required_complete_dataset_names: set[str],
) -> tuple[DatasetCoverage, tuple[CoverageValidationError, ...]]:
    errors: list[CoverageValidationError] = []
    counts: Counter[str] = Counter()
    row_count = 0
    required_complete = dataset_path.name in required_complete_dataset_names

    try:
        lines = dataset_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return (
            DatasetCoverage(
                path=dataset_path,
                row_count=0,
                policy_counts=counts,
                required_complete=required_complete,
            ),
            (
                CoverageValidationError(
                    message=exc.strerror or str(exc),
                    dataset_path=dataset_path,
                ),
            ),
        )

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        row_count += 1
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(
                CoverageValidationError(
                    message=f"invalid JSON: {exc.msg}",
                    dataset_path=dataset_path,
                    line_number=line_number,
                )
            )
            continue

        if not isinstance(row, dict):
            errors.append(
                CoverageValidationError(
                    message="row must be a JSON object",
                    dataset_path=dataset_path,
                    line_number=line_number,
                )
            )
            continue

        row_id = _row_id(row)
        expected_policy_ids = row.get("expected_policy_ids")
        if not isinstance(expected_policy_ids, list):
            errors.append(
                CoverageValidationError(
                    message="expected_policy_ids must be a list",
                    dataset_path=dataset_path,
                    line_number=line_number,
                    row_id=row_id,
                )
            )
            continue

        input_metadata = row.get("input")
        if not isinstance(input_metadata, dict):
            errors.append(
                CoverageValidationError(
                    message="input must be a JSON object",
                    dataset_path=dataset_path,
                    line_number=line_number,
                    row_id=row_id,
                )
            )
            continue

        unique_policy_ids = []
        seen_in_row: set[str] = set()
        for raw_policy_id in expected_policy_ids:
            if not isinstance(raw_policy_id, str):
                errors.append(
                    CoverageValidationError(
                        message="expected_policy_ids entries must be strings",
                        dataset_path=dataset_path,
                        line_number=line_number,
                        row_id=row_id,
                        policy_id=str(raw_policy_id),
                    )
                )
                continue
            if raw_policy_id in seen_in_row:
                continue
            seen_in_row.add(raw_policy_id)
            unique_policy_ids.append(raw_policy_id)

        for policy_id in unique_policy_ids:
            policy = policies_by_id.get(policy_id)
            if policy is None:
                errors.append(
                    CoverageValidationError(
                        message="unknown expected_policy_id",
                        dataset_path=dataset_path,
                        line_number=line_number,
                        row_id=row_id,
                        policy_id=policy_id,
                    )
                )
                continue
            counts[policy_id] += 1
            errors.extend(
                _compatibility_errors(
                    dataset_path=dataset_path,
                    line_number=line_number,
                    row_id=row_id,
                    input_metadata=input_metadata,
                    policy=policy,
                )
            )

    return (
        DatasetCoverage(
            path=dataset_path,
            row_count=row_count,
            policy_counts=counts,
            required_complete=required_complete,
        ),
        tuple(errors),
    )


def _missing_required_coverage_errors(
    dataset: DatasetCoverage,
    policies: Iterable[PolicyInventoryItem],
) -> tuple[CoverageValidationError, ...]:
    return tuple(
        CoverageValidationError(
            message="missing required coverage in required-complete dataset",
            dataset_path=dataset.path,
            policy_id=policy.id,
        )
        for policy in policies
        if dataset.policy_counts.get(policy.id, 0) == 0
    )


def _compatibility_errors(
    *,
    dataset_path: Path,
    line_number: int,
    row_id: str | None,
    input_metadata: dict[str, Any],
    policy: PolicyInventoryItem,
) -> tuple[CoverageValidationError, ...]:
    errors: list[CoverageValidationError] = []

    platform = _optional_lower_string(input_metadata.get("platform"))
    if policy.platforms and platform not in policy.platforms:
        errors.append(
            CoverageValidationError(
                message=(
                    "input platform "
                    f"{platform or '<missing>'} is incompatible with policy platforms "
                    f"{_join_filter(policy.platforms)}"
                ),
                dataset_path=dataset_path,
                line_number=line_number,
                row_id=row_id,
                policy_id=policy.id,
            )
        )

    industry = _optional_lower_string(input_metadata.get("industry"))
    if policy.industries and industry not in policy.industries:
        errors.append(
            CoverageValidationError(
                message=(
                    "input industry "
                    f"{industry or '<missing>'} is incompatible with policy industries "
                    f"{_join_filter(policy.industries)}"
                ),
                dataset_path=dataset_path,
                line_number=line_number,
                row_id=row_id,
                policy_id=policy.id,
            )
        )

    enabled_modules = _enabled_modules(input_metadata)
    if policy.modules and not set(enabled_modules).intersection(policy.modules):
        errors.append(
            CoverageValidationError(
                message=(
                    "input policy_modules/modules "
                    f"{_join_filter(enabled_modules)} do not enable policy modules "
                    f"{_join_filter(policy.modules)}"
                ),
                dataset_path=dataset_path,
                line_number=line_number,
                row_id=row_id,
                policy_id=policy.id,
            )
        )

    return tuple(errors)


def _enabled_modules(input_metadata: dict[str, Any]) -> tuple[str, ...]:
    modules = input_metadata.get("policy_modules") or input_metadata.get("modules")
    if not modules:
        return tuple(DEFAULT_MODULES)
    return _string_tuple(modules, lower=True)


def _string_tuple(value: Any, *, lower: bool = False) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        items = (value,)
    else:
        try:
            items = tuple(str(item) for item in value)
        except TypeError:
            items = (str(value),)
    if lower:
        return tuple(item.lower() for item in items)
    return items


def _optional_lower_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value).lower()


def _row_id(row: dict[str, Any]) -> str | None:
    if "id" not in row:
        return None
    return str(row["id"])


def _join_filter(values: Sequence[str]) -> str:
    return ", ".join(values) if values else "all"


def _coverage_table_header(datasets: Sequence[DatasetCoverage]) -> str:
    columns = [
        "Policy ID",
        "Category",
        "Modules",
        "Platform filters",
        "Industry filters",
        *(f"{dataset.label} count" for dataset in datasets),
        "Total count",
    ]
    return "| " + " | ".join(columns) + " |"


def _coverage_table_separator(datasets: Sequence[DatasetCoverage]) -> str:
    separators = ["---", "---", "---", "---", "---"]
    separators.extend("---:" for _ in datasets)
    separators.append("---:")
    return "| " + " | ".join(separators) + " |"


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def _markdown_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")
