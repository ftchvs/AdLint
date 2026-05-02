from __future__ import annotations

import re
from collections import defaultdict

from adlint.models import Evidence, LandingPageSnapshot, Policy, PolicyHit, Submission


MAX_EVIDENCE_PER_POLICY = 5


def run_rule_checks(
    submission: Submission,
    landing_page: LandingPageSnapshot,
    policies: list[Policy],
) -> list[PolicyHit]:
    fields = submission.ad_fields() | landing_page.text_fields()
    hits: list[PolicyHit] = []

    for policy in policies:
        evidence = _match_policy(policy, fields)
        if not evidence:
            continue

        hits.append(
            PolicyHit(
                policy_id=policy.id,
                severity=policy.severity,
                category=policy.category,
                evidence=evidence[:MAX_EVIDENCE_PER_POLICY],
                recommended_action=policy.recommended_action,
                requires_review=policy.requires_review,
                description=policy.description,
                iab_taxonomy=policy.iab_taxonomy,
            )
        )

    hits.extend(_derived_landing_page_hits(submission, landing_page, policies))
    hits.extend(_derived_privacy_hits(submission, landing_page, policies))
    return dedupe_hits(hits)


def dedupe_hits(hits: list[PolicyHit]) -> list[PolicyHit]:
    by_policy: dict[str, PolicyHit] = {}
    for hit in hits:
        existing = by_policy.get(hit.policy_id)
        if existing is None:
            by_policy[hit.policy_id] = hit
            continue

        seen = {(item.text, item.source) for item in existing.evidence}
        for item in hit.evidence:
            if (item.text, item.source) not in seen:
                existing.evidence.append(item)
                seen.add((item.text, item.source))
        existing.requires_review = existing.requires_review or hit.requires_review

    return list(by_policy.values())


def _match_policy(policy: Policy, fields: dict[str, str]) -> list[Evidence]:
    evidence: list[Evidence] = []
    seen: set[tuple[str, str]] = set()

    for signal in policy.signals:
        pattern = _signal_to_regex(signal)
        for source, text in fields.items():
            if not text:
                continue
            match = pattern.search(text)
            if not match:
                continue
            if _is_negated_match(text, match.start(), match.end()):
                continue
            snippet = _snippet(text, match.start(), match.end())
            key = (snippet, source)
            if key in seen:
                continue
            evidence.append(Evidence(text=snippet, source=source))
            seen.add(key)

    return evidence


def _derived_landing_page_hits(
    submission: Submission,
    landing_page: LandingPageSnapshot,
    policies: list[Policy],
) -> list[PolicyHit]:
    if not landing_page.url and not submission.landing_page_html:
        return []
    if not landing_page.title and not landing_page.headings and not landing_page.visible_claims:
        return []

    mismatch_policy = next((item for item in policies if item.id == "landing_page_offer_mismatch"), None)
    if mismatch_policy is None:
        return []

    ad_claim_terms = _important_terms(" ".join([submission.headline, submission.body]))
    page_terms = _important_terms(
        " ".join(
            [
                landing_page.title or "",
                *landing_page.headings,
                *landing_page.visible_claims,
                *landing_page.disclaimers,
            ]
        )
    )
    if not ad_claim_terms:
        return []

    missing_terms = sorted(ad_claim_terms - page_terms)
    if len(missing_terms) < 2:
        return []

    evidence = [
        Evidence(
            text=f"Ad emphasizes terms not found in extracted landing-page copy: {', '.join(missing_terms[:5])}",
            source="landing_page",
        )
    ]
    return [
        PolicyHit(
            policy_id=mismatch_policy.id,
            severity=mismatch_policy.severity,
            category=mismatch_policy.category,
            evidence=evidence,
            recommended_action=mismatch_policy.recommended_action,
            requires_review=mismatch_policy.requires_review,
            description=mismatch_policy.description,
        )
    ]


def _derived_privacy_hits(
    submission: Submission,
    landing_page: LandingPageSnapshot,
    policies: list[Policy],
) -> list[PolicyHit]:
    if submission.industry not in {"health", "wellness"}:
        return []
    if not landing_page.tracking_scripts:
        return []

    policy = next((item for item in policies if item.id == "tracking_pixel_risk"), None)
    if policy is None:
        return []

    tracker_counts: dict[str, int] = defaultdict(int)
    for tracker in landing_page.tracking_scripts:
        tracker_counts[tracker] += 1
    tracker_summary = ", ".join(f"{name} x{count}" for name, count in sorted(tracker_counts.items()))

    return [
        PolicyHit(
            policy_id=policy.id,
            severity=policy.severity,
            category=policy.category,
            evidence=[
                Evidence(
                    text=f"{tracker_summary} detected on a health-adjacent landing page",
                    source="landing_page",
                )
            ],
            recommended_action=policy.recommended_action,
            requires_review=True,
            description=policy.description,
        )
    ]


def _signal_to_regex(signal: str) -> re.Pattern[str]:
    escaped = re.escape(signal.strip().lower())
    escaped = escaped.replace(r"\*", r"[\w\s$.,%-]{0,40}")
    return re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)


def _snippet(text: str, start: int, end: int) -> str:
    clean = " ".join(text.split())
    if len(clean) <= 140:
        return clean

    prefix = max(0, start - 50)
    suffix = min(len(text), end + 50)
    snippet = " ".join(text[prefix:suffix].split())
    return snippet[:137] + "..." if len(snippet) > 140 else snippet


def _is_negated_match(text: str, start: int, end: int) -> bool:
    before = text[max(0, start - 40) : start].lower()
    after = text[end : min(len(text), end + 40)].lower()
    previous_words = before.split()[-5:]
    if any(negator in previous_words for negator in ("without", "not", "no")):
        return True
    return "collection" in after and any(word in previous_words for word in ("without", "no"))


def _important_terms(text: str) -> set[str]:
    normalized = re.sub(r"[^a-zA-Z0-9\s-]", " ", text.lower())
    stopwords = {
        "and",
        "are",
        "for",
        "from",
        "now",
        "our",
        "the",
        "this",
        "today",
        "with",
        "your",
    }
    terms = {item for item in normalized.split() if len(item) > 4 and item not in stopwords}
    interesting = {
        "guaranteed",
        "clinical",
        "clinically",
        "doctor",
        "supplement",
        "weight",
        "pounds",
        "credit",
        "salary",
        "privacy",
        "appointment",
        "trial",
        "discount",
        "proven",
    }
    return {term for term in terms if term in interesting}
