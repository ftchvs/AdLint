from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adlint.engine import analyze
from adlint.models import AnalysisResult


BOOL_FIELDS = {
    "logging_enabled",
    "model_affects_score",
    "model_enabled",
    "storage_enabled",
}
LIST_FIELDS = {"policy_modules", "modules"}
PRIVATE_BATCH_FIELDS = {
    "body",
    "cta",
    "headline",
    "landing_page_html",
    "landing_page_url",
}
SUMMARY_COLUMNS = (
    "row_id",
    "row_number",
    "platform",
    "industry",
    "decision",
    "risk_score",
    "requires_review",
    "highest_severity",
    "policy_ids",
    "recommended_actions",
    "model_status",
    "json_report",
    "markdown_report",
)


@dataclass(frozen=True)
class BatchOptions:
    policy_paths: list[str] | None = None
    output_dir: str | None = None
    enable_model: bool | None = None
    model_affects_score: bool = False
    ollama_model: str | None = None
    scoring_config_path: str | None = None


def run_batch(csv_path: str | Path, options: BatchOptions | None = None) -> dict[str, Any]:
    resolved_options = options or BatchOptions()
    source_path = Path(csv_path)
    rows = _load_csv_rows(source_path)
    summaries: list[dict[str, Any]] = []
    decision_counts: Counter[str] = Counter()

    for row_number, row in enumerate(rows, start=1):
        config = _row_to_config(row)
        if resolved_options.model_affects_score:
            config["model_affects_score"] = True
        row_id = _row_id(row, row_number)
        case_output_dir = None
        if resolved_options.output_dir:
            case_output_dir = str(Path(resolved_options.output_dir) / "cases" / _safe_path_name(row_id))

        result = analyze(
            config,
            policy_paths=resolved_options.policy_paths,
            output_dir=case_output_dir,
            enable_model=resolved_options.enable_model,
            ollama_model=resolved_options.ollama_model,
            scoring_config_path=resolved_options.scoring_config_path,
        )
        summary = summarize_result(
            result,
            row_id=row_id,
            row_number=row_number,
            platform=str(config.get("platform", "google")),
            industry=str(config.get("industry", "general")),
        )
        summaries.append(summary)
        decision_counts[result.decision] += 1

    payload = {
        "source": str(source_path),
        "total_rows": len(summaries),
        "decision_counts": dict(sorted(decision_counts.items())),
        "rows": summaries,
        "privacy": {
            "raw_creative_included": False,
            "summary_omits_fields": sorted(PRIVATE_BATCH_FIELDS),
            "case_reports": "local_output_dir_only" if resolved_options.output_dir else "not_written",
        },
    }
    if resolved_options.output_dir:
        payload["reports"] = write_batch_reports(payload, resolved_options.output_dir)
    return payload


def summarize_result(
    result: AnalysisResult,
    *,
    row_id: str,
    row_number: int,
    platform: str,
    industry: str,
) -> dict[str, Any]:
    return {
        "row_id": row_id,
        "row_number": row_number,
        "platform": platform,
        "industry": industry,
        "decision": result.decision,
        "risk_score": round(result.risk_score, 3),
        "requires_review": result.requires_review,
        "highest_severity": _highest_severity(result),
        "policy_ids": [hit.policy_id for hit in result.policy_hits],
        "recommended_actions": result.recommended_actions,
        "model_status": _model_status(result),
        "json_report": result.reports.get("json"),
        "markdown_report": result.reports.get("markdown"),
    }


def write_batch_reports(payload: dict[str, Any], output_dir: str | Path) -> dict[str, str]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    json_path = path / "adlint-batch-summary.json"
    csv_path = path / "adlint-batch-summary.csv"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    csv_path.write_text(to_summary_csv(payload), encoding="utf-8")
    return {"json": str(json_path), "csv": str(csv_path)}


def to_summary_csv(payload: dict[str, Any]) -> str:
    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=SUMMARY_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in payload.get("rows", []):
        writer.writerow(_csv_summary_row(row))
    return buffer.getvalue()


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Batch CSV not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Batch CSV must include a header row.")
        return [{key: value for key, value in row.items() if key} for row in reader]


def _row_to_config(row: dict[str, str]) -> dict[str, Any]:
    config: dict[str, Any] = {}
    for key, value in row.items():
        normalized_key = key.strip()
        if not normalized_key or normalized_key == "id" or value is None:
            continue
        normalized_value = value.strip()
        if not normalized_value:
            continue
        if normalized_key in BOOL_FIELDS:
            config[normalized_key] = _parse_bool(normalized_value)
        elif normalized_key in LIST_FIELDS:
            config[normalized_key] = _parse_list(normalized_value)
        else:
            config[normalized_key] = normalized_value
    return config


def _row_id(row: dict[str, str], row_number: int) -> str:
    raw_id = (row.get("id") or row.get("row_id") or "").strip()
    return raw_id or f"row-{row_number}"


def _safe_path_name(value: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip(".-")
    return safe or "row"


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y"}:
        return True
    if normalized in {"0", "false", "no", "n"}:
        return False
    raise ValueError(f"Expected boolean value, got {value!r}")


def _parse_list(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[;,]", value) if item.strip()]


def _highest_severity(result: AnalysisResult) -> str | None:
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    highest = None
    highest_score = 0
    for hit in result.policy_hits:
        score = order.get(hit.severity, 0)
        if score > highest_score:
            highest = hit.severity
            highest_score = score
    return highest


def _model_status(result: AnalysisResult) -> str:
    return str(result.model.get("status") or "disabled")


def _csv_summary_row(row: dict[str, Any]) -> dict[str, Any]:
    csv_row = dict(row)
    csv_row["requires_review"] = str(row.get("requires_review", False)).lower()
    csv_row["policy_ids"] = ";".join(str(item) for item in row.get("policy_ids", []))
    csv_row["recommended_actions"] = " | ".join(str(item) for item in row.get("recommended_actions", []))
    return csv_row
