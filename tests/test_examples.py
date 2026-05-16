from __future__ import annotations

from pathlib import Path

import pytest

from adlint.config import load_config
from adlint.engine import analyze


EXAMPLE_EXPECTATIONS = {
    "approved_saas.json": ("approved", set()),
    "brand_safety_review.json": ("needs_review", {"brand_safety_politics"}),
    "high_risk_tiktok_health.json": (
        "high_risk",
        {"unsupported_health_claim", "weight_loss_claim", "tiktok_weight_management_claim"},
    ),
    "linkedin_sensitive_targeting.json": (
        "high_risk",
        {"linkedin_sensitive_targeting", "linkedin_discrimination_risk"},
    ),
    "meta_approved_saas.json": ("approved", set()),
    "meta_high_risk_health.json": (
        "high_risk",
        {
            "meta_personal_attributes_health",
            "meta_health_appearance_results",
            "unsupported_health_claim",
            "weight_loss_claim",
            "before_after_claim",
        },
    ),
    "meta_needs_review_creator.json": (
        "needs_review",
        {"meta_branded_content_disclosure", "missing_affiliate_or_sponsor_disclosure"},
    ),
    "meta_financial_services_review.json": (
        "needs_review",
        {"meta_financial_services_authorization_review"},
    ),
    "meta_private_health_info_high_risk.json": (
        "high_risk",
        {"meta_private_information_request"},
    ),
    "meta_special_ad_category_review.json": (
        "needs_review",
        {"meta_financial_services_authorization_review", "meta_special_ad_category_review"},
    ),
    "needs_review_google_wellness.json": (
        "needs_review",
        {"tracking_pixel_risk", "health_form_tracking_risk"},
    ),
    "tiktok_asset_text_overlay_review.json": (
        "high_risk",
        {
            "guaranteed_outcome",
            "weight_loss_claim",
            "tiktok_weight_management_claim",
            "tiktok_misleading_content",
        },
    ),
}


@pytest.mark.parametrize("example_path", sorted(Path("examples").glob("*.json")), ids=lambda path: path.name)
def test_documented_example_configs_load_and_scan_without_external_features(example_path) -> None:
    expected_decision, expected_policy_ids = EXAMPLE_EXPECTATIONS[example_path.name]

    result = analyze(load_config(example_path))
    actual_policy_ids = {hit.policy_id for hit in result.policy_hits}

    assert result.decision == expected_decision
    assert expected_policy_ids <= actual_policy_ids
    assert result.logging_enabled is False
    assert result.model == {"enabled": False, "provider": None, "status": "disabled"}
    assert result.reports == {}


def test_all_documented_json_examples_have_expectations() -> None:
    example_names = {path.name for path in Path("examples").glob("*.json")}

    assert example_names == set(EXAMPLE_EXPECTATIONS)


def test_meta_examples_do_not_emit_unexpected_policy_ids() -> None:
    meta_examples = [path for path in Path("examples").glob("meta_*.json")]

    assert meta_examples
    for example_path in meta_examples:
        _, expected_policy_ids = EXAMPLE_EXPECTATIONS[example_path.name]
        result = analyze(load_config(example_path))
        actual_policy_ids = {hit.policy_id for hit in result.policy_hits}

        assert actual_policy_ids == expected_policy_ids, example_path.name
