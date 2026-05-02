from __future__ import annotations

import ipaddress
import json
import os
import urllib.request
from typing import Any
from urllib.parse import urlparse, urlunparse

from adlint.models import Evidence, PolicyHit, Submission


DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
ALLOWED_MODEL_DECISIONS = {"approved", "needs_review", "high_risk"}


def classify_with_ollama(
    submission: Submission,
    *,
    model: str | None = None,
    endpoint: str | None = None,
) -> tuple[list[PolicyHit], dict[str, Any]]:
    selected_model = model or os.getenv("ADLINT_OLLAMA_MODEL") or "gpt-oss-safeguard-20b"
    selected_endpoint = endpoint or os.getenv("ADLINT_OLLAMA_URL") or DEFAULT_OLLAMA_URL

    availability = _check_model_available(selected_endpoint, selected_model)
    if availability["status"] != "available":
        return [], {
            "enabled": True,
            "provider": "ollama",
            "model": selected_model,
            "endpoint": selected_endpoint,
            "status": "unavailable",
            "reason": availability["reason"],
            "ran": False,
            **{key: value for key, value in availability.items() if key in {"error", "available_models"}},
        }

    prompt = _build_prompt(submission)
    payload = {
        "model": selected_model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }

    request = urllib.request.Request(
        selected_endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        raw = _open_json(request, timeout=45)
    except Exception as exc:  # pragma: no cover - local runtime dependent
        return [], {
            "enabled": True,
            "provider": "ollama",
            "model": selected_model,
            "endpoint": selected_endpoint,
            "status": "unavailable",
            "reason": "generate_request_failed",
            "ran": False,
            "error": str(exc),
        }

    response_text = raw.get("response", "")
    parsed, error = _parse_model_response(response_text)
    if error:
        return [], {
            "enabled": True,
            "provider": "ollama",
            "model": selected_model,
            "endpoint": selected_endpoint,
            "status": "invalid_response",
            "reason": error,
            "ran": True,
        }

    hits = _hits_from_model_response(parsed)
    return hits, {
        "enabled": True,
        "provider": "ollama",
        "model": selected_model,
        "endpoint": selected_endpoint,
        "status": "ok",
        "ran": True,
        "raw_decision": parsed.get("decision"),
    }


def _check_model_available(endpoint: str, model: str) -> dict[str, Any]:
    parsed = urlparse(endpoint)
    if not _is_local_endpoint(parsed.hostname):
        return {"status": "unavailable", "reason": "non_local_endpoint"}

    tags_url = _tags_url(endpoint)
    request = urllib.request.Request(tags_url, method="GET")
    try:
        payload = _open_json(request, timeout=5)
    except Exception as exc:  # pragma: no cover - local runtime dependent
        return {"status": "unavailable", "reason": "tags_request_failed", "error": str(exc)}

    available_models = sorted(
        {
            str(item.get("name") or item.get("model"))
            for item in payload.get("models", [])
            if isinstance(item, dict) and (item.get("name") or item.get("model"))
        }
    )
    if model not in available_models:
        return {
            "status": "unavailable",
            "reason": "model_not_installed",
            "available_models": available_models,
        }
    return {"status": "available", "reason": "model_installed", "available_models": available_models}


def _tags_url(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    return urlunparse((parsed.scheme or "http", parsed.netloc, "/api/tags", "", "", ""))


def _is_local_endpoint(hostname: str | None) -> bool:
    if hostname is None:
        return False
    if hostname == "localhost":
        return True
    try:
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _open_json(request: urllib.request.Request, *, timeout: int) -> dict[str, Any]:
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


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


def _parse_model_response(response_text: str) -> tuple[dict[str, Any], str | None]:
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError:
        return {}, "invalid_json"
    if not isinstance(parsed, dict):
        return {}, "response_not_object"
    decision = parsed.get("decision")
    if decision not in ALLOWED_MODEL_DECISIONS:
        return {}, "invalid_decision"
    evidence = parsed.get("evidence", [])
    if evidence is not None and not isinstance(evidence, list):
        return {}, "invalid_evidence"
    return parsed, None


def _hits_from_model_response(parsed: dict[str, Any]) -> list[PolicyHit]:
    decision = str(parsed.get("decision", "approved"))
    if decision == "approved":
        return []

    evidence_items = parsed.get("evidence") or ["Model requested additional review."]
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
