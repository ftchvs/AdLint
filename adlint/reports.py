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
        "",
        "## Policy Hits",
        "",
    ]

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


def write_reports(result: AnalysisResult, output_dir: str | Path) -> dict[str, str]:
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    json_path = path / "adlint-report.json"
    markdown_path = path / "adlint-report.md"

    json_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(to_markdown(result), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(markdown_path)}
