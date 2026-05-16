from __future__ import annotations

import json
from pathlib import Path

from adlint.models import AnalysisResult


def to_markdown(result: AnalysisResult) -> str:
    lines = [
        "# AdLint Report",
        "",
        f"- Decision: `{result.decision}`",
        f"- Risk score: `{result.risk_score:.2f}`",
        f"- Requires review: `{str(result.requires_review).lower()}`",
        f"- Model status: `{_model_status(result.model)}`",
        "",
        "## Launch Readiness",
        "",
        f"- Status: {_readiness_status(result)}",
        f"- Summary: {_readiness_summary(result)}",
        "- Priority fixes:",
    ]
    lines.extend(_priority_fix_lines(result))
    lines.extend(
        [
            "",
            "## Policy Hits",
            "",
        ]
    )

    if not result.policy_hits:
        lines.append("No policy hits detected.")
    for hit in result.policy_hits:
        lines.extend(
            [
                f"### {hit.policy_id}",
                "",
                f"- Severity: `{hit.severity}`",
                f"- Category: `{hit.category}`",
                f"- Recommended action: {hit.recommended_action}",
            ]
        )
        source = _policy_source_markdown(hit.policy_source)
        if source:
            lines.append(f"- Policy source: {source}")
        if hit.requires_review:
            lines.append("- Review label: `requires_review`")
        lines.append("- Evidence:")
        for evidence in hit.evidence:
            lines.append(f"  - `{evidence.source}`: {evidence.text}")
        lines.append("")

    lines.extend(["## Recommended Actions", ""])
    if result.recommended_actions:
        for action in result.recommended_actions:
            lines.append(f"- {action}")
    else:
        lines.append("- No additional actions.")

    lines.extend(["", "## Safer Rewrites", ""])
    if result.safer_rewrites:
        for index, rewrite in enumerate(result.safer_rewrites, start=1):
            lines.extend(
                [
                    f"### Option {index}",
                    "",
                    f"- Headline: {rewrite['headline']}",
                    f"- Body: {rewrite['body']}",
                    f"- CTA: {rewrite['cta']}",
                    "",
                ]
            )
    else:
        lines.append("No rewrite suggested.")

    if result.landing_page.url or result.landing_page.title or result.landing_page.fetch_error:
        lines.extend(["", "## Landing Page", ""])
        page = result.landing_page
        if page.url:
            lines.append(f"- URL: {page.url}")
        if page.title:
            lines.append(f"- Title: {page.title}")
        _append_landing_page_list(lines, "Headings", page.headings)
        _append_landing_page_list(lines, "Visible claims", page.visible_claims)
        _append_landing_page_list(lines, "Forms", page.forms)
        _append_landing_page_list(lines, "Pricing", page.pricing_text)
        _append_landing_page_list(lines, "Disclaimers", page.disclaimers)
        if page.tracking_scripts:
            lines.append(f"- Trackers: {', '.join(page.tracking_scripts)}")
        if page.fetch_error:
            lines.append(f"- Fetch error: {page.fetch_error}")

    lines.extend(
        [
            "",
            "## Decision-Support Disclaimer",
            "",
            "AdLint is a preflight decision-support tool. It does not provide legal advice, guarantee platform approval, or make definitive statutory violation determinations.",
            "",
        ]
    )
    return "\n".join(lines)


def _append_landing_page_list(lines: list[str], label: str, values: tuple[str, ...]) -> None:
    if not values:
        return
    lines.append(f"- {label}:")
    for value in values:
        lines.append(f"  - {value}")


def _model_status(model: dict[str, object]) -> str:
    status = str(model.get("status") or "disabled")
    selected_model = model.get("model") or model.get("name")
    if selected_model:
        return f"{status} ({selected_model})"
    return status


def _readiness_status(result: AnalysisResult) -> str:
    if result.decision == "high_risk":
        return "Do not launch before fixes."
    if result.decision == "needs_review":
        return "Needs review before launch."
    return "Ready for configured preflight review."


def _readiness_summary(result: AnalysisResult) -> str:
    if result.decision == "high_risk":
        return "High-risk policy findings were detected by the configured rules."
    if result.decision == "needs_review":
        return "Review-labeled or medium-risk findings need a human check."
    return "No policy hits were detected by the configured deterministic rules."


def _priority_fix_lines(result: AnalysisResult) -> list[str]:
    if not result.recommended_actions:
        return ["  - No priority fixes from the configured rules."]
    return [f"  - {action}" for action in result.recommended_actions[:3]]


def _policy_source_markdown(policy_source: dict[str, str]) -> str:
    if not policy_source:
        return ""
    url = policy_source.get("url", "")
    note = policy_source.get("note", "")
    if url and note:
        return f"[{note}]({url})"
    if url:
        return url
    return note


def write_reports(result: AnalysisResult, output_dir: str | Path) -> dict[str, str]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    json_path = path / "adlint-report.json"
    markdown_path = path / "adlint-report.md"

    json_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(to_markdown(result), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(markdown_path)}
