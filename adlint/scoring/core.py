from __future__ import annotations

from adlint.models import PolicyHit, Submission


SEVERITY_WEIGHTS = {
    "low": 0.2,
    "medium": 0.4,
    "high": 0.7,
    "critical": 0.9,
}

REGULATED_INDUSTRIES = {"health", "wellness", "finance"}


def score_hits(hits: list[PolicyHit], submission: Submission) -> float:
    if not hits:
        return 0.0

    max_severity = max(SEVERITY_WEIGHTS.get(hit.severity, 0.2) for hit in hits)
    evidence_count = sum(len(hit.evidence) for hit in hits)
    evidence_weight = min(0.12, evidence_count * 0.02)
    regulated_weight = 0.08 if submission.industry in REGULATED_INDUSTRIES else 0.0
    mismatch_weight = 0.08 if any(hit.category == "landing_page" for hit in hits) else 0.0
    privacy_weight = 0.1 if any(hit.category == "privacy" for hit in hits) else 0.0
    brand_safety_weight = 0.05 if any(hit.category == "brand_safety" for hit in hits) else 0.0

    return round(
        min(
            1.0,
            max_severity
            + evidence_weight
            + regulated_weight
            + mismatch_weight
            + privacy_weight
            + brand_safety_weight,
        ),
        2,
    )


def decision_for_score(score: float) -> str:
    if score >= 0.7:
        return "high_risk"
    if score >= 0.35:
        return "needs_review"
    return "approved"
