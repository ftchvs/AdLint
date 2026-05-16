from __future__ import annotations

import json

from adlint.engine import analyze
from adlint.models import Evidence, PolicyHit


def policy_ids(result) -> set[str]:
    return {hit.policy_id for hit in result.policy_hits}



def test_meta_financial_education_copy_avoids_authorization_overtrigger() -> None:
    result = analyze(
        {
            "platform": "meta",
            "industry": "finance",
            "headline": "Loan planning education webinar",
            "body": "Learn budgeting basics and how loan terms work. No application or quote is offered.",
            "cta": "Register",
        }
    )

    assert "meta_financial_services_authorization_review" not in policy_ids(result)
    assert "meta_special_ad_category_review" not in policy_ids(result)


def test_meta_landing_page_mismatch_stacks_with_platform_review() -> None:
    result = analyze(
        {
            "platform": "meta",
            "industry": "finance",
            "headline": "Credit card application discount",
            "body": "Compare an apply for credit offer before launch.",
            "cta": "Apply",
            "landing_page_html": "<html><body><h1>General budgeting newsletter</h1><p>Weekly savings tips.</p></body></html>",
        }
    )

    ids = policy_ids(result)
    assert "meta_financial_services_authorization_review" in ids
    assert "landing_page_offer_mismatch" in ids
    assert result.decision == "needs_review"


def test_landing_page_mismatch_catches_single_missing_material_offer_term() -> None:
    result = analyze(
        {
            "platform": "linkedin",
            "industry": "saas",
            "headline": "Free trial for campaign QA",
            "body": "Use a launch workflow with a discount for new teams.",
            "cta": "Start trial",
            "landing_page_html": "<html><body><h1>Campaign QA workflow</h1><p>Coordinate briefs and approvals.</p></body></html>",
        }
    )

    hits = {hit.policy_id: hit for hit in result.policy_hits}

    assert result.decision == "needs_review"
    assert "landing_page_offer_mismatch" in hits
    assert "discount" in hits["landing_page_offer_mismatch"].evidence[0].text
    assert "trial" in hits["landing_page_offer_mismatch"].evidence[0].text


def test_landing_page_mismatch_accepts_visible_material_offer_terms() -> None:
    result = analyze(
        {
            "platform": "linkedin",
            "industry": "saas",
            "headline": "Free trial for campaign QA",
            "body": "Use a launch workflow with a discount for new teams.",
            "cta": "Start trial",
            "landing_page_html": "<html><body><h1>Campaign QA free trial</h1><p>New teams can review discount terms before launch.</p></body></html>",
        }
    )

    assert "landing_page_offer_mismatch" not in policy_ids(result)


def test_landing_page_mismatch_catches_missing_percent_off_offer() -> None:
    result = analyze(
        {
            "platform": "tiktok",
            "industry": "general",
            "headline": "Limited time 50% off creator toolkit",
            "body": "Use promo code LAUNCH50 before the sale ends.",
            "cta": "Claim deal",
            "landing_page_html": "<html><body><h1>Creator toolkit</h1><p>Templates for planning your launch.</p></body></html>",
        }
    )

    hit = next(hit for hit in result.policy_hits if hit.policy_id == "landing_page_offer_mismatch")

    assert result.decision == "needs_review"
    assert "50% off" in hit.evidence[0].text
    assert "limited time" in hit.evidence[0].text


def test_landing_page_mismatch_accepts_percent_offer_in_pricing_text() -> None:
    result = analyze(
        {
            "platform": "tiktok",
            "industry": "general",
            "headline": "Limited time 50% off creator toolkit",
            "body": "Use promo code LAUNCH50 before the sale ends.",
            "cta": "Claim deal",
            "landing_page_html": "<html><body><h1>Creator toolkit</h1><p>Limited time 50% off with promo code LAUNCH50.</p></body></html>",
        }
    )

    assert "landing_page_offer_mismatch" not in policy_ids(result)


def test_creative_asset_text_overlay_uses_existing_policy_rules_without_raw_media() -> None:
    result = analyze(
        {
            "platform": "tiktok",
            "industry": "health",
            "headline": "Daily wellness routine",
            "body": "A simple guide for planning healthy habits.",
            "cta": "Learn more",
            "creative_assets": [
                {
                    "asset_id": "hero-image",
                    "asset_type": "image",
                    "path": "/private/campaigns/hero.png",
                    "mime_type": "image/png",
                    "width": 1080,
                    "height": 1080,
                    "text_overlay": "Lose 20 pounds in 30 days guaranteed",
                }
            ],
        }
    )

    hits = {hit.policy_id: hit for hit in result.policy_hits}
    payload = result.to_dict()

    assert result.decision == "high_risk"
    assert {"weight_loss_claim", "guaranteed_outcome", "tiktok_weight_management_claim"} <= policy_ids(result)
    assert hits["weight_loss_claim"].evidence[0].source == "creative_asset_hero_image_text_overlay"
    assert payload["creative_assets"] == [
        {
            "asset_id": "hero_image",
            "asset_type": "image",
            "filename": "hero.png",
            "height": 1080,
            "mime_type": "image/png",
            "text_metadata": {
                "alt_text": False,
                "labels": 0,
                "text_overlay": True,
                "transcript_excerpt": False,
            },
            "width": 1080,
        }
    ]
    assert "/private/campaigns" not in json.dumps(payload)
    assert "Lose 20 pounds" not in json.dumps(payload["creative_assets"])


def test_creative_asset_empty_metadata_does_not_create_policy_hit() -> None:
    result = analyze(
        {
            "platform": "linkedin",
            "industry": "saas",
            "headline": "Plan campaign launches",
            "body": "Coordinate launch notes.",
            "cta": "Learn more",
            "creative_assets": [{"asset_type": "video", "filename": "launch.mp4", "duration_seconds": 12}],
        }
    )

    assert result.decision == "approved"
    assert result.policy_hits == []




def test_meta_special_ad_category_review_applies_outside_default_verticals() -> None:
    result = analyze(
        {
            "platform": "meta",
            "industry": "health",
            "headline": "Hiring now for clinic coordinators",
            "body": "Apply for this role supporting patient scheduling teams.",
            "cta": "Apply",
        }
    )

    assert "meta_special_ad_category_review" in policy_ids(result)


def test_meta_private_information_request_applies_to_general_campaigns() -> None:
    result = analyze(
        {
            "platform": "meta",
            "industry": "general",
            "headline": "Check eligibility in minutes",
            "body": "Enter your credit score to personalize your results.",
            "cta": "Start",
        }
    )

    assert result.decision == "high_risk"
    assert "meta_private_information_request" in policy_ids(result)


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


def test_model_review_is_metadata_only_by_default(monkeypatch) -> None:
    def fake_classifier(submission, *, model=None, endpoint=None, landing_page=None):
        return [
            PolicyHit(
                policy_id="model_policy_review",
                severity="medium",
                category="model_review",
                evidence=[Evidence(text="model concern", source="model")],
                recommended_action="Review model concern.",
                requires_review=True,
                source="ollama",
            )
        ], {"enabled": True, "provider": "ollama", "status": "ok"}

    monkeypatch.setattr("adlint.engine.classify_with_ollama", fake_classifier)

    result = analyze(
        {
            "platform": "google",
            "industry": "general",
            "headline": "Download campaign checklist",
            "body": "A free worksheet for launch planning.",
            "cta": "Download",
            "model_enabled": True,
        }
    )

    assert result.decision == "approved"
    assert result.policy_hits == []
    assert result.model["affects_score"] is False
    assert [finding["policy_id"] for finding in result.model["findings"]] == ["model_policy_review"]


def test_model_review_can_affect_score_when_explicitly_enabled(monkeypatch) -> None:
    def fake_classifier(submission, *, model=None, endpoint=None, landing_page=None):
        return [
            PolicyHit(
                policy_id="model_policy_review",
                severity="medium",
                category="model_review",
                evidence=[Evidence(text="model concern", source="model")],
                recommended_action="Review model concern.",
                requires_review=True,
                source="ollama",
            )
        ], {"enabled": True, "provider": "ollama", "status": "ok"}

    monkeypatch.setattr("adlint.engine.classify_with_ollama", fake_classifier)

    result = analyze(
        {
            "platform": "google",
            "industry": "general",
            "headline": "Download campaign checklist",
            "body": "A free worksheet for launch planning.",
            "cta": "Download",
            "model_enabled": True,
            "model_affects_score": True,
        }
    )

    assert result.decision == "needs_review"
    assert [hit.policy_id for hit in result.policy_hits] == ["model_policy_review"]
    assert result.model["affects_score"] is True


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


def test_linkedin_soft_professional_outcome_copy_routes_to_review_not_high_risk() -> None:
    result = analyze(
        {
            "platform": "linkedin",
            "industry": "saas",
            "headline": "Productivity system for busy teams",
            "body": "Use the workflow to improve team output and support faster weekly planning.",
            "cta": "View workflow",
        }
    )

    hits = {hit.policy_id: hit for hit in result.policy_hits}
    assert result.decision == "needs_review"
    assert hits["linkedin_professional_claim_review"].severity == "medium"
    assert hits["linkedin_professional_claim_review"].source == "derived_rules"


def test_linkedin_hard_professional_outcome_copy_stays_high_risk() -> None:
    result = analyze(
        {
            "platform": "linkedin",
            "industry": "general",
            "headline": "Double your salary with this system",
            "body": "Use our career workflow and double your salary after a few weeks of outreach.",
            "cta": "Start system",
        }
    )

    hits = {hit.policy_id: hit for hit in result.policy_hits}
    assert result.decision == "high_risk"
    assert hits["linkedin_professional_claim_review"].severity == "high"
    assert hits["linkedin_professional_claim_review"].source == "rules"
