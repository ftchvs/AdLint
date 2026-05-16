from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from adlint.engine import analyze
from adlint.reports import to_markdown


BOOLEAN_FIELDS = {"model_enabled", "model_affects_score", "logging_enabled", "storage_enabled"}
LIST_FIELDS = {"policy_modules", "modules"}
JSON_FIELDS = {"creative_assets", "assets"}
PRIVATE_BATCH_FIELDS = {
    "body",
    "cta",
    "creative_assets",
    "headline",
    "landing_page_html",
    "landing_page_url",
}
SUMMARY_FIELDS = (
    "id",
    "decision",
    "risk_score",
    "requires_review",
    "policy_ids",
    "asset_count",
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
    output_dir = Path(resolved_options.output_dir) if resolved_options.output_dir else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    for index, raw_row in enumerate(rows, start=1):
        row_id = _row_id(raw_row, index)
        config = _row_to_config(raw_row)
        if resolved_options.model_affects_score:
            config["model_affects_score"] = True

        result = analyze(
            config,
            policy_paths=resolved_options.policy_paths,
            enable_model=resolved_options.enable_model,
            ollama_model=resolved_options.ollama_model,
            scoring_config_path=resolved_options.scoring_config_path,
        )
        report_paths = _write_row_reports(result, output_dir, row_id) if output_dir else {}
        policy_ids = [hit.policy_id for hit in result.policy_hits]
        results.append(
            {
                "id": row_id,
                "decision": result.decision,
                "risk_score": round(result.risk_score, 4),
                "requires_review": result.requires_review,
                "asset_count": len(result.creative_assets),
                "policy_ids": policy_ids,
                "reports": report_paths,
            }
        )

    summary = _batch_summary(results, source_path=source_path, output_dir=output_dir)
    if output_dir:
        summary["reports"] = _write_batch_reports(summary, output_dir)
    return summary


def summary_to_markdown(summary: dict[str, Any]) -> str:
    lines = [
        "# AdLint Batch Summary",
        "",
        f"- Total rows: `{summary['total_rows']}`",
        f"- Approved: `{summary['decision_counts'].get('approved', 0)}`",
        f"- Needs review: `{summary['decision_counts'].get('needs_review', 0)}`",
        f"- High risk: `{summary['decision_counts'].get('high_risk', 0)}`",
        "",
        "## Rows",
        "",
        "| ID | Decision | Risk score | Review | Policy hits |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in summary["rows"]:
        policy_ids = ", ".join(row["policy_ids"]) if row["policy_ids"] else "none"
        lines.append(
            "| {id} | `{decision}` | {risk_score:.2f} | `{requires_review}` | {policy_ids} |".format(
                id=row["id"],
                decision=row["decision"],
                risk_score=row["risk_score"],
                requires_review=str(row["requires_review"]).lower(),
                policy_ids=policy_ids,
            )
        )
    lines.extend(
        [
            "",
            "Batch summaries intentionally omit raw ad copy. Per-row reports contain the evidence snippets needed for local review.",
            "",
        ]
    )
    return "\n".join(lines)


def to_summary_csv(summary: dict[str, Any]) -> str:
    from io import StringIO

    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=SUMMARY_FIELDS)
    writer.writeheader()
    for row in summary.get("rows", []):
        reports = row.get("reports", {})
        writer.writerow(
            {
                "id": row["id"],
                "decision": row["decision"],
                "risk_score": f"{row['risk_score']:.4f}",
                "requires_review": str(row["requires_review"]).lower(),
                "policy_ids": ";".join(row["policy_ids"]),
                "asset_count": str(row.get("asset_count", 0)),
                "json_report": reports.get("json", ""),
                "markdown_report": reports.get("markdown", ""),
            }
        )
    return buffer.getvalue()


def _load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Batch CSV must include a header row.")
        return [dict(row) for row in reader]


def _row_to_config(row: dict[str, str]) -> dict[str, Any]:
    config: dict[str, Any] = {}
    for key, raw_value in row.items():
        if key is None:
            continue
        clean_key = key.strip()
        if not clean_key or clean_key in {"id", "row_id", "name"}:
            continue
        value = (raw_value or "").strip()
        if value == "":
            continue
        if clean_key in BOOLEAN_FIELDS:
            config[clean_key] = _parse_bool(value)
        elif clean_key in JSON_FIELDS:
            config[clean_key] = json.loads(value)
        elif clean_key in LIST_FIELDS:
            config["policy_modules"] = _parse_list(value)
        else:
            config[clean_key] = value
    return config


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid boolean value in batch CSV: {value}")


def _parse_list(value: str) -> list[str]:
    if value.strip().startswith("["):
        parsed = json.loads(value)
        if not isinstance(parsed, list):
            raise ValueError("CSV list fields must be JSON arrays or delimiter-separated strings.")
        return [str(item).strip() for item in parsed if str(item).strip()]
    return [item.strip() for item in re.split(r"[|;,]", value) if item.strip()]


def _row_id(row: dict[str, str], index: int) -> str:
    for field in ("id", "row_id", "name"):
        value = (row.get(field) or "").strip()
        if value:
            return _safe_id(value)
    return f"row-{index:03d}"


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-._")
    return cleaned or "row"


def _write_row_reports(result: Any, output_dir: Path, row_id: str) -> dict[str, str]:
    json_path = output_dir / f"{row_id}.json"
    markdown_path = output_dir / f"{row_id}.md"
    json_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(to_markdown(result), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(markdown_path)}


def _batch_summary(rows: list[dict[str, Any]], *, source_path: Path, output_dir: Path | None) -> dict[str, Any]:
    decisions = Counter(row["decision"] for row in rows)
    policy_counts = Counter(policy_id for row in rows for policy_id in row["policy_ids"])
    return {
        "summary_version": 1,
        "source": str(source_path),
        "total_rows": len(rows),
        "decision_counts": dict(sorted(decisions.items())),
        "policy_counts": dict(sorted(policy_counts.items())),
        "privacy": {
            "raw_creative_included": False,
            "summary_omits_fields": sorted(PRIVATE_BATCH_FIELDS),
            "row_reports": "local_output_dir_only" if output_dir else "not_written",
        },
        "rows": rows,
    }


def _write_batch_reports(summary: dict[str, Any], output_dir: Path) -> dict[str, str]:
    json_path = output_dir / "adlint-batch-summary.json"
    markdown_path = output_dir / "adlint-batch-summary.md"
    csv_path = output_dir / "adlint-batch-summary.csv"

    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(summary_to_markdown(summary), encoding="utf-8")
    csv_path.write_text(to_summary_csv(summary), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(markdown_path), "csv": str(csv_path)}
