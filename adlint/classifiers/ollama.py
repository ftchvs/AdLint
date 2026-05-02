from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

from adlint.models import Evidence, PolicyHit, Submission


DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"


def classify_with_ollama(
    submission: Submission,
    *,
    model: str | None = None,
    endpoint: str | None = None,
) -> tuple[list[PolicyHit], dict[str, Any]]:
    selected_model = model or os.getenv("ADLINT_OLLAMA_MODEL") or "gpt-oss-safeguard-20b"
    selected_endpoint = endpoint or os.getenv("ADLINT_OLLAMA_URL") or DEFAULT_OLLAMA_URL
    prompt = _build_prompt(submission)
    payload = {
        "model": selected_model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }

    request = urllib.request.Request(
        selected_endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # pragma: no cover - local runtime dependent
        return [], {
            "enabled": True,
            "provider": "ollama",
            "model": selected_model,
            "endpoint": selected_endpoint,
            "status": "unavailable",
            "error": str(exc),
        }

    response_text = raw.get("response", "")
    parsed = _parse_model_response(response_text)
    hits = _hits_from_model_response(parsed)
    return hits, {
        "enabled": True,
        "provider": "ollama",
        "model": selected_model,
        "endpoint": selected_endpoint,
        "status": "ok",
        "raw_decision": parsed.get("decision"),
    }


def _build_prompt(submission: Submission) -> str:
    return f"""
You are an ad policy preflight classifier. Return strict JSON with:
decision: approved | needs_review | high_risk
categories: array of policy categories
evidence: array of short exact phrases
recommended_action: short action

This is decision-support only, not legal advice.

Platform: {submission.platform}
Country: {submission.country}
Industry: {submission.industry}
Headline: {submission.headline}
Body: {submission.body}
CTA: {submission.cta}
""".strip()


def _parse_model_response(response_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError:
        return {"decision": "needs_review", "evidence": [response_text[:200]], "categories": ["model_review"]}
    return parsed if isinstance(parsed, dict) else {}


def _hits_from_model_response(parsed: dict[str, Any]) -> list[PolicyHit]:
    decision = str(parsed.get("decision", "approved"))
    if decision == "approved":
        return []

    evidence_items = parsed.get("evidence") or ["Model requested additional review."]
    if not isinstance(evidence_items, list):
        evidence_items = [str(evidence_items)]

    severity = "high" if decision == "high_risk" else "medium"
    action = str(parsed.get("recommended_action") or "Route this ad for policy review.")
    return [
        PolicyHit(
            policy_id="model_policy_review",
            severity=severity,
            category="model_review",
            evidence=[Evidence(text=str(item), source="model") for item in evidence_items[:5]],
            recommended_action=action,
            requires_review=True,
            description="Local model classifier requested additional review.",
            source="ollama",
        )
    ]
