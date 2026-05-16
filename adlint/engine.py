from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping

from adlint.audit_log import write_run_log
from adlint.classifiers.ollama import classify_with_ollama
from adlint.models import AnalysisResult, PolicyHit, Submission
from adlint.policy import enabled_modules, filter_policies, load_policies
from adlint.reports import write_reports
from adlint.rewrites.suggestions import build_rewrites
from adlint.rules.engine import dedupe_hits, run_rule_checks
from adlint.scoring.config import ScoringConfig, load_scoring_config, scoring_config_from_dict
from adlint.scoring.core import decision_for_score, score_hits
from adlint.scrapers.landing_page import extract_landing_page


def analyze(
    config: dict,
    *,
    policy_paths: list[str] | None = None,
    output_dir: str | None = None,
    enable_model: bool | None = None,
    ollama_model: str | None = None,
    scoring_config: ScoringConfig | Mapping[str, Any] | None = None,
    scoring_config_path: str | Path | None = None,
) -> AnalysisResult:
    resolved_scoring_config = _resolve_scoring_config(scoring_config, scoring_config_path)
    submission = Submission.from_dict(config)
    if enable_model is not None:
        submission = replace(submission, model_enabled=enable_model)

    landing_page = extract_landing_page(submission.landing_page_url, submission.landing_page_html)
    policies = filter_policies(load_policies(policy_paths), submission)
    hits = run_rule_checks(submission, landing_page, policies)
    model_info = {"enabled": False, "provider": None, "status": "disabled"}

    if submission.model_enabled:
        model_hits, model_info = classify_with_ollama(
            submission,
            model=ollama_model,
            landing_page=landing_page,
        )
        model_info["affects_score"] = submission.model_affects_score
        model_info["findings"] = [hit.to_dict() for hit in model_hits]
        if submission.model_affects_score:
            hits = dedupe_hits([*hits, *model_hits])

    risk_score = score_hits(hits, submission, resolved_scoring_config)
    decision = decision_for_score(risk_score, resolved_scoring_config)
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
        creative_assets=submission.creative_assets,
    )

    if output_dir:
        result.reports = write_reports(result, output_dir)
    if submission.logging_enabled:
        result.reports["log"] = write_run_log(submission, result, submission.log_path)
    if submission.storage_enabled:
        from adlint.storage import record_analysis_run

        result.reports["storage"] = record_analysis_run(submission, result, submission.storage_path)
    return result


def _resolve_scoring_config(
    scoring_config: ScoringConfig | Mapping[str, Any] | None,
    scoring_config_path: str | Path | None,
) -> ScoringConfig | None:
    if scoring_config is not None and scoring_config_path is not None:
        raise ValueError("Pass scoring_config or scoring_config_path, not both.")
    if scoring_config_path is not None:
        return load_scoring_config(scoring_config_path)
    if scoring_config is None:
        return None
    if isinstance(scoring_config, ScoringConfig):
        return scoring_config
    if isinstance(scoring_config, Mapping):
        return scoring_config_from_dict(scoring_config, source="scoring_config")
    raise TypeError("scoring_config must be a ScoringConfig or mapping.")


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
