from __future__ import annotations

from adlint.models import Submission
from adlint.policy import filter_policies, load_policies


CUSTOM_POLICY = """
policies:
  - id: custom_health_claim
    severity: high
    category: health_claims
    modules: [health_claims]
    platforms: [google]
    industries: [health]
    signals:
      - clinical guarantee
    source_url: https://example.com/policy
    source_note: Example policy source
    recommended_action: Qualify the custom claim.
    requires_review: true
"""


def test_load_policies_accepts_custom_file(tmp_path) -> None:
    policy_path = tmp_path / "custom.yml"
    policy_path.write_text(CUSTOM_POLICY, encoding="utf-8")

    policies = load_policies([policy_path])

    assert [policy.id for policy in policies] == ["custom_health_claim"]
    assert policies[0].requires_review is True
    assert policies[0].source_url == "https://example.com/policy"
    assert policies[0].source_note == "Example policy source"


def test_load_policies_preserves_optional_source_metadata(tmp_path) -> None:
    policy_path = tmp_path / "custom.yml"
    policy_path.write_text(
        """
policies:
  - id: sourced_policy
    severity: medium
    category: platform_policy
    source_url: https://example.com/policy
    source_note: Example policy source
    signals: [review me]
    recommended_action: Review the claim.
""",
        encoding="utf-8",
    )

    policies = load_policies([policy_path])

    assert policies[0].source_url == "https://example.com/policy"
    assert policies[0].source_note == "Example policy source"


def test_load_policies_accepts_custom_directory(tmp_path) -> None:
    policy_dir = tmp_path / "policies"
    policy_dir.mkdir()
    (policy_dir / "custom.yaml").write_text(CUSTOM_POLICY, encoding="utf-8")

    policies = load_policies([policy_dir])

    assert [policy.id for policy in policies] == ["custom_health_claim"]


def test_filter_policies_applies_platform_and_industry_filters(tmp_path) -> None:
    policy_path = tmp_path / "custom.yml"
    policy_path.write_text(CUSTOM_POLICY, encoding="utf-8")
    policies = load_policies([policy_path])

    matching = Submission.from_dict(
        {
            "platform": "google",
            "industry": "health",
            "headline": "Clinical guarantee",
            "policy_modules": ["health_claims"],
        }
    )
    wrong_platform = Submission.from_dict(
        {
            "platform": "linkedin",
            "industry": "health",
            "headline": "Clinical guarantee",
            "policy_modules": ["health_claims"],
        }
    )
    wrong_industry = Submission.from_dict(
        {
            "platform": "google",
            "industry": "saas",
            "headline": "Clinical guarantee",
            "policy_modules": ["health_claims"],
        }
    )

    assert [policy.id for policy in filter_policies(policies, matching)] == ["custom_health_claim"]
    assert filter_policies(policies, wrong_platform) == []
    assert filter_policies(policies, wrong_industry) == []


def test_filter_policies_all_platform_includes_platform_scoped_policies(tmp_path) -> None:
    policy_path = tmp_path / "custom.yml"
    policy_path.write_text(CUSTOM_POLICY, encoding="utf-8")
    policies = load_policies([policy_path])
    all_platforms = Submission.from_dict(
        {
            "platform": "all",
            "industry": "health",
            "headline": "Clinical guarantee",
            "policy_modules": ["health_claims"],
        }
    )

    assert [policy.id for policy in filter_policies(policies, all_platforms)] == ["custom_health_claim"]


def test_bundled_meta_ads_policy_module_is_platform_scoped() -> None:
    meta_policy_ids = {
        "meta_personal_attributes_health",
        "meta_personal_attributes_finance",
        "meta_health_appearance_results",
        "meta_health_wellness_age_targeting_review",
        "meta_financial_services_authorization_review",
        "meta_special_ad_category_review",
        "meta_private_information_request",
        "meta_branded_content_disclosure",
    }

    policies = {policy.id: policy for policy in load_policies()}

    assert meta_policy_ids <= set(policies)
    for policy_id in meta_policy_ids:
        policy = policies[policy_id]
        assert policy.category == "platform_policy"
        assert policy.modules == ("platform",)
        assert policy.platforms == ("meta",)
        assert policy.signals


def test_meta_cross_vertical_rules_are_not_industry_gated() -> None:
    policies = {policy.id: policy for policy in load_policies()}

    assert policies["meta_special_ad_category_review"].industries == ()
    assert policies["meta_private_information_request"].industries == ()


def test_bundled_policies_include_public_source_metadata() -> None:
    missing = [
        policy.id
        for policy in load_policies()
        if not policy.source_url or not policy.source_note
    ]

    assert missing == []
