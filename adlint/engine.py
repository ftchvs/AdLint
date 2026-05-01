from __future__ import annotations

from adlint.classifiers.ollama import classify_with_ollama
from adlint.models import AnalysisResult, PolicyHit, Submission
from adlint.policy import enabled_modules, filter_policies, load_policies
from adlint.reports import write_reports
from adlint.rewrites.suggestions import build_rewrites
from adlint.rules.engine import dedupe_hits, run_rule_checks
from adlint.scoring.core import decision_for_score, score_hits
from adlint.scrapers.landing_page import extract_landing_page


def analyze(
    config: dict,
    *,
    policy_paths: list[str] | None = None,
    output_dir: str | None = None,
    enable_model: bool | None = None,
    ollama_model: str | None = None,
) -> AnalysisResult:
    submission = Submission.from_dict(config)
    if enable_model is not None:
        submission = Submission(
            platform=submission.platform,
            country=submission.country,
            industry=submission.industry,
            headline=submission.headline,
            body=submission.body,
            cta=submission.cta,
            target_age_range=submission.target_age_range,
            landing_page_url=submission.landing_page_url,
            landing_page_html=submission.landing_page_html,
            policy_modules=submission.policy_modules,
            model_enabled=enable_model,
            logging_enabled=submission.logging_enabled,
        )

    landing_page = extract_landing_page(submission.landing_page_url, submission.landing_page_html)
    policies = filter_policies(load_policies(policy_paths), submission)
    hits = run_rule_checks(submission, landing_page, policies)
    model_info = {"enabled": False, "provider": None, "status": "disabled"}

    if submission.model_enabled:
        model_hits, model_info = classify_with_ollama(submission, model=ollama_model)
        hits = dedupe_hits([*hits, *model_hits])

    risk_score = score_hits(hits, submission)
    decision = decision_for_score(risk_score)
    requires_review = any(hit.requires_review for hit in hits) or decision != "approved"
    recommended_actions = _recommended_actions(hits)

    result = AnalysisResult(
        decision=decision,
        risk_score=risk_score,
        policy_hits=hits,
        requires_review=requires_review,
        recommended_actions=recommended_actions,
        safer_rewrites=build_rewrites(submission, hits),
        landing_page=landing_page,
        enabled_modules=enabled_modules(submission),
        model=model_info,
        logging_enabled=submission.logging_enabled,
    )

    if output_dir:
        result.reports = write_reports(result, output_dir)
    return result


def _recommended_actions(hits: list[PolicyHit]) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()
    for hit in sorted(hits, key=lambda item: _severity_order(item.severity), reverse=True):
        action = hit.recommended_action
        if not action or action in seen:
            continue
        actions.append(action)
        seen.add(action)
    return actions


def _severity_order(severity: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(severity, 0)
