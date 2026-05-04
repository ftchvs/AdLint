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
    markdown = markdown_report.read_text(encoding="utf-8")
    assert "- Model status: `disabled`" in markdown
    assert "Decision-Support Disclaimer" in markdown


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


def test_ollama_model_without_model_enabled_does_not_call_classifier(monkeypatch) -> None:
    def fail_classifier(*args, **kwargs):  # pragma: no cover - must not be called
        raise AssertionError("classifier should only run when model_enabled is true")

    monkeypatch.setattr("adlint.engine.classify_with_ollama", fail_classifier)

    result = analyze(
        {
            "platform": "google",
            "industry": "general",
            "headline": "Download campaign checklist",
            "body": "A free worksheet for launch planning.",
            "cta": "Download",
            "model_enabled": False,
        },
        ollama_model="llama3.2:latest",
    )

    assert result.model == {"enabled": False, "provider": None, "status": "disabled"}


def test_clinically_backed_health_claim_requires_substantiation_review() -> None:
    result = analyze(
        {
            "platform": "google",
            "industry": "health",
            "headline": "Clinically backed weight loss pen treatment",
            "body": "Access once-weekly prescription weight loss treatment after an online clinic appointment.",
            "cta": "Start consultation",
        }
    )

    assert "unsupported_health_claim" in policy_ids(result)


def test_generic_clinical_operations_copy_does_not_create_health_claim_review() -> None:
    result = analyze(
        {
            "platform": "linkedin",
            "industry": "health",
            "headline": "Clinical workflow software",
            "body": "Coordinate provider approvals and appointment notes.",
            "cta": "Request demo",
        }
    )

    assert "unsupported_health_claim" not in policy_ids(result)
    assert "hipaa_marketing_review" in policy_ids(result)


def test_hipaa_marketing_review_requires_patient_or_data_context() -> None:
    result = analyze(
        {
            "platform": "google",
            "industry": "health",
            "headline": "Weekly weight loss injection appointments",
            "body": "Medical clinic appointment for prescription weight loss treatment.",
            "cta": "Start consultation",
        }
    )

    assert "google_health_restricted_category" in policy_ids(result)
    assert "hipaa_marketing_review" not in policy_ids(result)


def test_hipaa_tracking_review_requires_healthcare_context_beside_tracker() -> None:
    fertility_app = analyze(
        {
            "platform": "google",
            "industry": "health",
            "headline": "Fertility health app reminders",
            "body": "Sync your data and reproductive health insights.",
            "cta": "Sync your data",
            "landing_page_html": "<html><script src='https://www.googletagmanager.com/gtm.js'></script><body><h1>Reproductive health reminders</h1></body></html>",
        }
    )
    telehealth_intake = analyze(
        {
            "platform": "tiktok",
            "industry": "health",
            "headline": "ADHD telehealth treatment appointment",
            "body": "Optimize ads from completed intake forms for patients seeking medical treatment.",
            "cta": "Book appointment",
            "landing_page_html": "<html><script src='https://analytics.tiktok.com/i18n/pixel/events.js'></script><body><h1>Clinic appointment</h1><form><label>Intake form</label></form></body></html>",
        }
    )

    assert "hipaa_tracking_technology_review" not in policy_ids(fertility_app)
    assert "hipaa_tracking_technology_review" in policy_ids(telehealth_intake)


def test_health_breach_indicator_requires_app_device_or_consumer_health_context() -> None:
    health_data_only = analyze(
        {
            "platform": "tiktok",
            "industry": "health",
            "headline": "Online therapy matched to your symptoms",
            "body": "Use health data from a mental health quiz to personalize therapy subscription ads.",
            "cta": "Take quiz",
        }
    )
    health_app = analyze(
        {
            "platform": "google",
            "industry": "health",
            "headline": "Health app prescription discounts",
            "body": "Use health data to retarget prescription savings reminders.",
            "cta": "Get coupon",
        }
    )

    assert "ftc_health_breach_notification_indicator" not in policy_ids(health_data_only)
    assert "ftc_health_breach_notification_indicator" in policy_ids(health_app)


def test_projected_return_finance_copy_routes_to_google_financial_review() -> None:
    result = analyze(
        {
            "platform": "google",
            "industry": "finance",
            "headline": "Projected return planning workbook",
            "body": "Compare projected return scenarios for a new savings plan without committing today.",
            "cta": "Open workbook",
        }
    )

    assert result.decision == "needs_review"
    assert "google_financial_claim_review" in policy_ids(result)


def test_tiktok_brand_tagged_creator_copy_routes_to_disclosure_review() -> None:
    result = analyze(
        {
            "platform": "tiktok",
            "industry": "creator",
            "headline": "Brand-tagged morning routine story",
            "body": "A creator tags the brand while showing a morning routine and product setup.",
            "cta": "Watch story",
        }
    )

    assert result.decision == "needs_review"
    assert "tiktok_disclosure_risk" in policy_ids(result)


def test_faith_leader_event_context_routes_to_sensitive_social_issue_review() -> None:
    result = analyze(
        {
            "platform": "google",
            "industry": "general",
            "headline": "Community event for faith leaders",
            "body": "Promote a public community event for faith leaders and local organizers.",
            "cta": "Register",
        }
    )

    assert result.decision == "needs_review"
    assert "brand_safety_sensitive_social_issue" in policy_ids(result)
