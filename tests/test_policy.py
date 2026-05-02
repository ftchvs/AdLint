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
    recommended_action: Qualify the custom claim.
    requires_review: true
"""


def test_load_policies_accepts_custom_file(tmp_path) -> None:
    policy_path = tmp_path / "custom.yml"
    policy_path.write_text(CUSTOM_POLICY, encoding="utf-8")

    policies = load_policies([policy_path])

    assert [policy.id for policy in policies] == ["custom_health_claim"]
    assert policies[0].requires_review is True


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
