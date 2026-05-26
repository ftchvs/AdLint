from __future__ import annotations

from adlint.models import PolicyHit, Submission


def build_rewrites(submission: Submission, hits: list[PolicyHit]) -> list[dict[str, str]]:
    rewrites: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for hit in hits:
        if hit.severity not in {"high", "critical"} and not hit.requires_review:
            continue

        rewrite = _rewrite_for_hit(submission, hit)
        key = (rewrite["headline"], rewrite["body"], rewrite["cta"])
        if key in seen:
            continue
        rewrites.append(rewrite)
        seen.add(key)

    return rewrites[:5]


def _rewrite_for_hit(submission: Submission, hit: PolicyHit) -> dict[str, str]:
    if hit.policy_id in {"weight_loss_claim", "tiktok_weight_management_claim"}:
        return {
            "headline": "Support your wellness routine with daily nutrition",
            "body": "Designed to complement healthy habits. Individual results vary.",
            "cta": _soft_cta(submission.cta),
        }
    if hit.policy_id in {"medical_cure_claim"}:
        return {
            "headline": "Explore support for your wellness routine",
            "body": "Learn about options that may support healthy habits. Consult a qualified professional for medical questions.",
            "cta": "Learn more",
        }
    if hit.category == "health_claims" or hit.policy_id.startswith("meta_health_"):
        return {
            "headline": "Support your wellness routine with daily nutrition",
            "body": "Designed to complement healthy habits. Individual results vary.",
            "cta": _soft_cta(submission.cta),
        }
    if hit.category == "privacy":
        return {
            "headline": submission.headline or "Learn more before you sign up",
            "body": "Review how your information is used, including consent choices and privacy details, before continuing.",
            "cta": "Review details",
        }
    if hit.category == "disclosure":
        return {
            "headline": submission.headline or "A recommended resource",
            "body": "This may include a paid partnership or affiliate link. Review the details before choosing what works for you.",
            "cta": _soft_cta(submission.cta),
        }
    if hit.category == "brand_safety":
        return {
            "headline": _fallback_headline(submission),
            "body": "Use neutral language and review placement controls before launch.",
            "cta": _soft_cta(submission.cta),
        }
    return {
        "headline": _fallback_headline(submission),
        "body": _qualified_body(submission.body),
        "cta": _soft_cta(submission.cta),
    }


def _fallback_headline(submission: Submission) -> str:
    if not submission.headline:
        return "Learn more about this option"
    return (
        submission.headline.replace("guaranteed", "designed to help")
        .replace("Guaranteed", "Designed to help")
        .replace("instant", "practical")
        .replace("Instant", "Practical")
    )


def _qualified_body(body: str) -> str:
    if not body:
        return "Review the details and choose what fits your needs. Results vary."
    clean = (
        body.replace("clinically proven", "developed with evidence-informed guidance")
        .replace("Clinically proven", "Developed with evidence-informed guidance")
        .replace("risk-free", "with clear terms")
        .replace("Risk-free", "With clear terms")
    )
    if "results vary" not in clean.lower():
        clean = f"{clean.rstrip()} Results vary."
    return clean


def _soft_cta(cta: str) -> str:
    if not cta:
        return "Learn more"
    lower = cta.lower()
    if lower in {"buy now", "act now", "claim now", "sign up now"}:
        return "Learn more"
    return cta
