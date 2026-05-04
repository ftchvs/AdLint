from __future__ import annotations

import json

import pytest

from adlint.cli import main
from adlint.engine import analyze
from adlint.models import Evidence, PolicyHit, Submission
from adlint.scoring.config import DEFAULT_SCORING_CONFIG, load_scoring_config
from adlint.scoring.core import decision_for_score, score_hits


def _submission(industry: str = "wellness") -> Submission:
    return Submission(
        platform="google",
        country="US",
        industry=industry,
        headline="A calmer routine for better sleep",
        body="Join our newsletter for science-backed tips.",
        cta="Sign up",
    )


def _hit(
    *,
    severity: str,
    category: str,
    evidence_count: int = 1,
    policy_id: str | None = None,
) -> PolicyHit:
    return PolicyHit(
        policy_id=policy_id or f"{category}_{severity}",
        severity=severity,
        category=category,
        evidence=[
            Evidence(text=f"evidence {index}", source="ad")
            for index in range(evidence_count)
        ],
        recommended_action="Review the claim.",
    )


def test_default_scoring_config_matches_existing_scores() -> None:
    submission = _submission("wellness")
    hits = [
        _hit(severity="medium", category="privacy", evidence_count=5),
        _hit(severity="medium", category="landing_page", evidence_count=1),
    ]

    assert score_hits([], submission) == 0.0
    assert decision_for_score(0.34) == "approved"
    assert decision_for_score(0.35) == "needs_review"
    assert decision_for_score(0.7) == "high_risk"
    assert score_hits(hits, submission) == 0.69
    assert score_hits(hits, submission, DEFAULT_SCORING_CONFIG) == 0.69
    assert decision_for_score(0.69, DEFAULT_SCORING_CONFIG) == "needs_review"


def test_scoring_config_path_overrides_thresholds_and_weights(tmp_path) -> None:
    scoring_path = tmp_path / "scoring.yml"
    scoring_path.write_text(
        """
thresholds:
  needs_review: 0.30
  high_risk: 0.65
  max_without_high_severity: 0.64
weights:
  severity:
    low: 0.10
    medium: 0.35
    high: 0.45
    critical: 0.90
  evidence_count:
    per_item: 0.03
    max: 0.10
  regulated_category: 0.03
  landing_page_mismatch: 0.04
  privacy_tracking: 0.05
  brand_safety: 0.06
regulated_industries:
  - crypto
""".lstrip(),
        encoding="utf-8",
    )
    submission = _submission("crypto")
    hits = [
        _hit(severity="high", category="landing_page", evidence_count=1),
        _hit(severity="high", category="privacy", evidence_count=1),
        _hit(severity="medium", category="brand_safety", evidence_count=0),
    ]

    scoring_config = load_scoring_config(scoring_path)

    assert score_hits(hits, submission, scoring_config) == 0.69
    assert decision_for_score(0.69, scoring_config) == "high_risk"


def test_analyze_accepts_scoring_config_mapping_override() -> None:
    result = analyze(
        {
            "platform": "google",
            "industry": "wellness",
            "headline": "Join our wellness newsletter",
            "body": "Sign up for science-backed sleep tips.",
            "cta": "Sign up",
            "landing_page_html": "<html><script src='https://connect.facebook.net/en_US/fbevents.js'></script><body><h1>Sleep tips</h1><form><label>Email signup</label></form></body></html>",
        },
        scoring_config={
            "thresholds": {
                "needs_review": 0.25,
                "high_risk": 0.95,
                "max_without_high_severity": 0.94,
            },
            "weights": {
                "severity": {"medium": 0.2},
                "evidence_count": {"per_item": 0.0, "max": 0.0},
                "regulated_category": 0.0,
                "privacy_tracking": 0.0,
            },
        },
    )

    assert result.risk_score == 0.2
    assert result.decision == "approved"


def test_cli_scan_accepts_scoring_config_path(tmp_path, capsys) -> None:
    ad_path = tmp_path / "ad.json"
    scoring_path = tmp_path / "scoring.yml"
    ad_path.write_text(
        json.dumps(
            {
                "platform": "google",
                "industry": "wellness",
                "headline": "Join our wellness newsletter",
                "body": "Sign up for science-backed sleep tips.",
                "cta": "Sign up",
                "landing_page_html": "<html><script src='https://connect.facebook.net/en_US/fbevents.js'></script><body><h1>Sleep tips</h1><form><label>Email signup</label></form></body></html>",
            }
        ),
        encoding="utf-8",
    )
    scoring_path.write_text(
        """
thresholds:
  needs_review: 0.25
  high_risk: 0.95
  max_without_high_severity: 0.94
weights:
  severity:
    medium: 0.20
  evidence_count:
    per_item: 0.0
    max: 0.0
  regulated_category: 0.0
  privacy_tracking: 0.0
""".lstrip(),
        encoding="utf-8",
    )

    assert main(["scan", str(ad_path), "--scoring-config", str(scoring_path)]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["risk_score"] == 0.2
    assert output["decision"] == "approved"


def test_invalid_scoring_config_rejects_unknown_weight_key(tmp_path) -> None:
    scoring_path = tmp_path / "scoring.yml"
    scoring_path.write_text("weights:\n  surprise: 0.2\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unknown .* weights key 'surprise'"):
        load_scoring_config(scoring_path)


def test_invalid_scoring_config_rejects_bad_threshold_type(tmp_path) -> None:
    scoring_path = tmp_path / "scoring.yml"
    scoring_path.write_text("thresholds:\n  high_risk: strict\n", encoding="utf-8")

    with pytest.raises(ValueError, match="thresholds.high_risk must be a number"):
        load_scoring_config(scoring_path)


def test_invalid_scoring_config_rejects_unordered_severity_weights(tmp_path) -> None:
    scoring_path = tmp_path / "scoring.yml"
    scoring_path.write_text(
        "weights:\n  severity:\n    medium: 0.8\n    high: 0.7\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="weights.severity.medium must be less"):
        load_scoring_config(scoring_path)
