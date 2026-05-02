from __future__ import annotations

import json

from adlint.engine import analyze


def policy_ids(result) -> set[str]:
    return {hit.policy_id for hit in result.policy_hits}


def test_high_risk_health_claims_and_tiktok_policy() -> None:
    result = analyze(
        {
            "platform": "tiktok",
            "industry": "health",
            "headline": "Lose 20 pounds in 30 days guaranteed",
            "body": "Our clinically proven supplement melts fat fast.",
            "cta": "Buy now",
        }
    )

    assert result.decision == "high_risk"
    assert result.risk_score >= 0.7
    assert {"unsupported_health_claim", "weight_loss_claim", "tiktok_weight_management_claim"} <= policy_ids(result)
    assert result.safer_rewrites


def test_privacy_tracking_is_review_label_not_definitive_violation() -> None:
    result = analyze(
        {
            "platform": "google",
            "industry": "wellness",
            "headline": "A calmer routine for better sleep",
            "body": "Join our wellness newsletter for science-backed sleep tips.",
            "cta": "Sign up",
            "landing_page_html": "<html><script src='https://connect.facebook.net/en_US/fbevents.js'></script><body><h1>Sleep tips</h1><form><label>Email signup</label></form></body></html>",
        }
    )

    hits = {hit.policy_id: hit for hit in result.policy_hits}
    assert result.requires_review is True
    assert hits["tracking_pixel_risk"].requires_review is True
    assert "definitive" not in hits["tracking_pixel_risk"].recommended_action.lower()


def test_policy_module_filter_limits_surface() -> None:
    result = analyze(
        {
            "platform": "google",
            "industry": "health",
            "headline": "Lose 20 pounds guaranteed near election coverage",
            "body": "Political inventory for a wellness offer.",
            "cta": "Buy now",
            "policy_modules": ["brand_safety"],
        }
    )

    assert "brand_safety_politics" in policy_ids(result)
    assert "weight_loss_claim" not in policy_ids(result)


def test_report_writer_outputs_json_and_markdown(tmp_path) -> None:
    result = analyze(
        {
            "platform": "linkedin",
            "industry": "saas",
            "headline": "Plan campaign launches in one shared workspace",
            "body": "Coordinate briefs, approvals, and launch notes with your marketing team.",
            "cta": "Learn more",
        },
        output_dir=str(tmp_path),
    )

    json_report = tmp_path / "adlint-report.json"
    markdown_report = tmp_path / "adlint-report.md"
    assert json_report.exists()
    assert markdown_report.exists()
    assert json.loads(json_report.read_text(encoding="utf-8"))["decision"] == result.decision
    assert "Decision-Support Disclaimer" in markdown_report.read_text(encoding="utf-8")


def test_logging_is_opt_in(tmp_path) -> None:
    log_path = tmp_path / "runs.jsonl"
    result = analyze(
        {
            "platform": "google",
            "industry": "general",
            "headline": "Download campaign checklist",
            "body": "A free worksheet for launch planning.",
            "cta": "Download",
            "logging_enabled": True,
            "log_path": str(log_path),
        }
    )

    assert result.reports["log"] == str(log_path)
    logged = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])
    assert logged["input"]["headline"] == "Download campaign checklist"


def test_logging_stays_disabled_without_opt_in(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = analyze(
        {
            "platform": "google",
            "industry": "general",
            "headline": "Download campaign checklist",
            "body": "A free worksheet for launch planning.",
            "cta": "Download",
        }
    )

    assert result.logging_enabled is False
    assert result.reports == {}
    assert not (tmp_path / "logs" / "adlint-runs.jsonl").exists()
