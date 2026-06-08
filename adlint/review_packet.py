from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


PACKET_VERSION = 1
PRIVATE_MANIFEST_FIELDS = (
    "body",
    "cta",
    "creative_assets",
    "headline",
    "landing_page_html",
    "landing_page_url",
    "raw_media",
)


def build_review_packet(source_dir: str | Path, output_dir: str | Path) -> dict[str, Any]:
    source = Path(source_dir)
    output = Path(output_dir)
    if not source.exists() or not source.is_dir():
        raise ValueError(f"Review packet source must be an existing directory: {source}")

    output.mkdir(parents=True, exist_ok=True)
    reports_dir = output / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    if (source / "adlint-batch-summary.json").exists():
        manifest = _manifest_from_batch(source, output, reports_dir)
    elif (source / "adlint-report.json").exists():
        manifest = _manifest_from_single_report(source, output, reports_dir)
    else:
        raise ValueError(
            "Review packet source must contain adlint-batch-summary.json or adlint-report.json."
        )

    manifest_path = output / "manifest.json"
    markdown_path = output / "review-packet.md"
    manifest["packet"] |= {
        "manifest": str(manifest_path.relative_to(output)),
        "markdown": str(markdown_path.relative_to(output)),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(packet_to_markdown(manifest), encoding="utf-8")
    return {
        "manifest": str(manifest_path),
        "markdown": str(markdown_path),
        "row_reports": [
            str(output / row["reports"]["markdown"])
            for row in manifest["rows"]
            if row.get("reports", {}).get("markdown")
        ],
    }


def packet_to_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    lines = [
        "# AdLint Review Packet",
        "",
        f"- Packet version: `{manifest['packet']['version']}`",
        f"- Source type: `{manifest['source']['type']}`",
        f"- Total rows: `{summary['total_rows']}`",
        f"- Approved: `{summary['decision_counts'].get('approved', 0)}`",
        f"- Needs review: `{summary['decision_counts'].get('needs_review', 0)}`",
        f"- High risk: `{summary['decision_counts'].get('high_risk', 0)}`",
        "",
        "## Rows",
        "",
        "| ID | Decision | Risk score | Review | Policy hits | Markdown report |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for row in manifest["rows"]:
        policy_ids = ", ".join(row["policy_ids"]) if row["policy_ids"] else "none"
        report = row.get("reports", {}).get("markdown", "")
        report_link = f"[{report}]({report})" if report else ""
        lines.append(
            "| {id} | `{decision}` | {risk_score:.2f} | `{requires_review}` | {policy_ids} | {report} |".format(
                id=row["id"],
                decision=row["decision"],
                risk_score=row["risk_score"],
                requires_review=str(row["requires_review"]).lower(),
                policy_ids=policy_ids,
                report=report_link,
            )
        )

    lines.extend(
        [
            "",
            "## Policy Sources",
            "",
        ]
    )
    sources = manifest.get("policy_sources", [])
    if not sources:
        lines.append("- No policy sources in this packet.")
    for source in sources:
        url = source.get("url", "")
        note = source.get("note") or url or "Policy source"
        policy_ids = ", ".join(source.get("policy_ids", []))
        if url:
            lines.append(f"- [{note}]({url}) - {policy_ids}")
        else:
            lines.append(f"- {note} - {policy_ids}")

    lines.extend(
        [
            "",
            "## Privacy Boundary",
            "",
            "- The packet manifest omits raw ad copy, raw landing-page HTML, landing-page URLs, raw creative paths, and raw media.",
            "- Per-row Markdown reports are copied for local reviewer handoff and retain only the evidence snippets produced by AdLint.",
            "- AdLint is decision-support software, not legal advice or a platform approval guarantee.",
            "",
        ]
    )
    return "\n".join(lines)


def _manifest_from_batch(source: Path, output: Path, reports_dir: Path) -> dict[str, Any]:
    summary_path = source / "adlint-batch-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    policy_sources_by_key: dict[tuple[str, str], dict[str, Any]] = {}

    for row in summary.get("rows", []):
        row_id = str(row["id"])
        report_json = _resolve_report_path(source, row.get("reports", {}).get("json"))
        report_markdown = _resolve_report_path(source, row.get("reports", {}).get("markdown"))
        report_payload = _load_report_payload(report_json)
        copied_markdown = _copy_markdown_report(report_markdown, reports_dir, row_id)
        policy_ids = [str(policy_id) for policy_id in row.get("policy_ids", [])]
        _collect_policy_sources(policy_sources_by_key, report_payload.get("policy_hits", []))
        rows.append(
            {
                "id": row_id,
                "decision": row["decision"],
                "risk_score": float(row["risk_score"]),
                "requires_review": bool(row["requires_review"]),
                "policy_ids": policy_ids,
                "asset_count": int(row.get("asset_count", 0)),
                "reports": {"markdown": str(copied_markdown.relative_to(output))},
            }
        )

    copied_summary = _copy_if_exists(source / "adlint-batch-summary.md", output / "adlint-batch-summary.md")
    manifest = _base_manifest(source_type="batch_archive", row_count=len(rows))
    manifest["source"] |= {
        "summary": summary_path.name,
        "batch_summary_markdown": copied_summary.name if copied_summary else None,
    }
    manifest["summary"] = {
        "total_rows": int(summary.get("total_rows", len(rows))),
        "decision_counts": dict(sorted(summary.get("decision_counts", {}).items())),
        "policy_counts": dict(sorted(summary.get("policy_counts", {}).items())),
    }
    manifest["rows"] = rows
    manifest["policy_sources"] = _policy_source_list(policy_sources_by_key)
    return manifest


def _manifest_from_single_report(source: Path, output: Path, reports_dir: Path) -> dict[str, Any]:
    report_json = source / "adlint-report.json"
    report_markdown = source / "adlint-report.md"
    payload = json.loads(report_json.read_text(encoding="utf-8"))
    row_id = "adlint-report"
    copied_markdown = _copy_markdown_report(report_markdown, reports_dir, row_id)
    policy_hits = payload.get("policy_hits", [])
    policy_ids = [str(hit["policy_id"]) for hit in policy_hits]
    policy_sources_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    _collect_policy_sources(policy_sources_by_key, policy_hits)

    manifest = _base_manifest(source_type="single_report", row_count=1)
    manifest["source"] |= {"report": report_json.name}
    manifest["summary"] = {
        "total_rows": 1,
        "decision_counts": dict(Counter([payload["decision"]])),
        "policy_counts": dict(sorted(Counter(policy_ids).items())),
    }
    manifest["rows"] = [
        {
            "id": row_id,
            "decision": payload["decision"],
            "risk_score": float(payload["risk_score"]),
            "requires_review": bool(payload["requires_review"]),
            "policy_ids": policy_ids,
            "asset_count": len(payload.get("creative_assets", [])),
            "reports": {"markdown": str(copied_markdown.relative_to(output))},
        }
    ]
    manifest["policy_sources"] = _policy_source_list(policy_sources_by_key)
    return manifest


def _base_manifest(*, source_type: str, row_count: int) -> dict[str, Any]:
    return {
        "packet": {
            "version": PACKET_VERSION,
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        },
        "source": {"type": source_type},
        "summary": {"total_rows": row_count, "decision_counts": {}, "policy_counts": {}},
        "privacy": {
            "raw_creative_included": False,
            "manifest_omits_fields": list(PRIVATE_MANIFEST_FIELDS),
            "raw_media_copied": False,
        },
        "rows": [],
        "policy_sources": [],
    }


def _resolve_report_path(source: Path, raw_path: Any) -> Path | None:
    if not raw_path:
        return None
    path = Path(str(raw_path))
    if path.is_absolute():
        return path
    return source / path


def _load_report_payload(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _copy_markdown_report(path: Path | None, reports_dir: Path, row_id: str) -> Path:
    if path is None or not path.exists():
        raise ValueError(f"Missing Markdown report for review packet row: {row_id}")
    destination = reports_dir / f"{_safe_filename(row_id)}.md"
    shutil.copyfile(path, destination)
    return destination


def _copy_if_exists(source: Path, destination: Path) -> Path | None:
    if not source.exists():
        return None
    shutil.copyfile(source, destination)
    return destination


def _collect_policy_sources(
    policy_sources_by_key: dict[tuple[str, str], dict[str, Any]],
    policy_hits: list[dict[str, Any]],
) -> None:
    for hit in policy_hits:
        source = hit.get("policy_source") or {}
        url = str(source.get("url", ""))
        note = str(source.get("note", ""))
        if not url and not note:
            continue
        key = (url, note)
        entry = policy_sources_by_key.setdefault(key, {"url": url, "note": note, "policy_ids": set()})
        entry["policy_ids"].add(str(hit.get("policy_id", "")))


def _policy_source_list(policy_sources_by_key: dict[tuple[str, str], dict[str, Any]]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for _key, source in sorted(policy_sources_by_key.items(), key=lambda item: (item[0][1], item[0][0])):
        sources.append(
            {
                "url": source["url"],
                "note": source["note"],
                "policy_ids": sorted(policy_id for policy_id in source["policy_ids"] if policy_id),
            }
        )
    return sources


def _safe_filename(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in "-._" else "-" for char in value.strip())
    return cleaned.strip("-._") or "row"
