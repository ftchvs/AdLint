from __future__ import annotations

from adlint.models import PolicyHit, Submission
from adlint.scoring.config import DEFAULT_SCORING_CONFIG, ScoringConfig


def score_hits(
    hits: list[PolicyHit],
    submission: Submission,
    scoring_config: ScoringConfig | None = None,
) -> float:
    if not hits:
        return 0.0

    config = scoring_config or DEFAULT_SCORING_CONFIG
    max_severity = max(
        config.severity_weights.get(hit.severity, config.severity_weights["low"])
        for hit in hits
    )
    evidence_count = sum(len(hit.evidence) for hit in hits)
    evidence_weight = min(
        config.evidence_count.max,
        evidence_count * config.evidence_count.per_item,
    )
    regulated_weight = (
        config.weights.regulated_category
        if submission.industry in config.regulated_industries
        else 0.0
    )
    mismatch_weight = (
        config.weights.landing_page_mismatch
        if any(hit.category == "landing_page" for hit in hits)
        else 0.0
    )
    privacy_weight = (
        config.weights.privacy_tracking
        if any(hit.category == "privacy" for hit in hits)
        else 0.0
    )
    brand_safety_weight = (
        config.weights.brand_safety
        if any(hit.category == "brand_safety" for hit in hits)
        else 0.0
    )

    raw_score = min(
        1.0,
        max_severity
        + evidence_weight
        + regulated_weight
        + mismatch_weight
        + privacy_weight
        + brand_safety_weight,
    )
    if max_severity < config.severity_weights["high"]:
        raw_score = min(raw_score, config.thresholds.max_without_high_severity)
    return round(raw_score, 2)


def decision_for_score(score: float, scoring_config: ScoringConfig | None = None) -> str:
    config = scoring_config or DEFAULT_SCORING_CONFIG
    if score >= config.thresholds.high_risk:
        return "high_risk"
    if score >= config.thresholds.needs_review:
        return "needs_review"
    return "approved"
