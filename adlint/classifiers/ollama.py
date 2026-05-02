from __future__ import annotations

import ipaddress
import json
import os
import urllib.parse
import urllib.request
from typing import Any

from adlint.models import Evidence, PolicyHit, Submission


DEFAULT_OLLAMA_MODEL = "gpt-oss-safeguard:20b"
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/chat"


def list_local_models(*, endpoint: str | None = None) -> dict[str, Any]:
    selected_endpoint = _selected_endpoint(endpoint)
    info: dict[str, Any] = {
        "provider": "ollama",
        "endpoint": selected_endpoint,
        "default_model": _selected_model(None),
        "status": "unavailable",
        "models": [],
    }

    try:
        _validate_loopback_endpoint(selected_endpoint)
        request = urllib.request.Request(_tags_endpoint(selected_endpoint), method="GET")
        with urllib.request.urlopen(request, timeout=10) as response:
            _raise_for_status(response)
            raw = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # pragma: no cover - local runtime dependent
        info["reason"] = str(exc)
        return info

    if not isinstance(raw, dict):
        info["status"] = "invalid_response"
        info["reason"] = "Ollama tags response must be an object"
        return info

    info["status"] = "ok"
    info["models"] = _model_names(raw)
    return info


def classify_with_ollama(
    submission: Submission,
    *,
    model: str | None = None,
    endpoint: str | None = None,
) -> tuple[list[PolicyHit], dict[str, Any]]:
    selected_model = _selected_model(model)
    selected_endpoint = _selected_endpoint(endpoint)
    prompt = _build_prompt(submission)
    payload = _generation_payload(selected_endpoint, selected_model, prompt)

    try:
        _validate_loopback_endpoint(selected_endpoint)
        request = urllib.request.Request(
            selected_endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=45) as response:
            _raise_for_status(response)
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

    response_text = _response_text(raw)
    parsed, is_valid_response = _parse_model_response(response_text)
    hits = _hits_from_model_response(parsed)
    return hits, {
        "enabled": True,
        "provider": "ollama",
        "model": selected_model,
        "endpoint": selected_endpoint,
        "status": "ok" if is_valid_response else "invalid_response",
        "raw_decision": parsed.get("decision"),
    }


def _selected_model(model: str | None) -> str:
    return model or os.getenv("ADLINT_OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL


def _selected_endpoint(endpoint: str | None) -> str:
    return endpoint or os.getenv("ADLINT_OLLAMA_URL") or DEFAULT_OLLAMA_URL


def _validate_loopback_endpoint(endpoint: str) -> None:
    parsed = urllib.parse.urlparse(endpoint)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Ollama endpoint must use http or https")
    host = parsed.hostname
    if not host:
        raise ValueError("Ollama endpoint must include a host")
    if host.lower() == "localhost":
        return
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError("Ollama endpoint must use a loopback host") from exc
    if not address.is_loopback:
        raise ValueError("Ollama endpoint must use a loopback host")


def _tags_endpoint(endpoint: str) -> str:
    parsed = urllib.parse.urlparse(endpoint)
    return urllib.parse.urlunparse(parsed._replace(path="/api/tags", query="", fragment=""))


def _raise_for_status(response: Any) -> None:
    status = int(getattr(response, "status", 200))
    if status < 200 or status >= 300:
        raise RuntimeError(f"Ollama request failed with status {status}")


def _generation_payload(endpoint: str, model: str, prompt: str) -> dict[str, Any]:
    common: dict[str, Any] = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }
    if urllib.parse.urlparse(endpoint).path.endswith("/api/generate"):
        return {**common, "prompt": prompt}
    return {**common, "messages": [{"role": "user", "content": prompt}]}


def _response_text(raw: dict[str, Any]) -> str:
    message = raw.get("message")
    if isinstance(message, dict):
        return str(message.get("content", ""))
    return str(raw.get("response", ""))


def _model_names(raw: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in raw.get("models", []):
        if isinstance(item, str):
            name = item
        elif isinstance(item, dict):
            name = item.get("name") or item.get("model") or ""
        else:
            name = ""
        if name:
            names.append(str(name))
    return names


def _build_prompt(submission: Submission) -> str:
    landing_page_html = _clip(submission.landing_page_html or "", max_chars=3000)
    modules = ", ".join(submission.policy_modules) if submission.policy_modules else "default"
    return f"""
You are an ad policy preflight classifier. Return strict JSON with:
decision: approved | needs_review | high_risk
categories: array of policy categories
evidence: array of short exact phrases
recommended_action: short action

This is decision-support only, not legal advice.
Use the ad copy and landing-page context. In health-adjacent campaigns, treat
appointments, symptoms, providers, clinics, telehealth, prescriptions, intake
forms, sensitive health data, third-party trackers, and pixel scripts as
review signals. Do not approve when a health-adjacent landing page combines a
form or health-data language with third-party tracking.

Platform: {submission.platform}
Country: {submission.country}
Industry: {submission.industry}
Policy modules: {modules}
Headline: {submission.headline}
Body: {submission.body}
CTA: {submission.cta}
Target age range: {submission.target_age_range or ""}
Landing page URL: {submission.landing_page_url or ""}
Landing page HTML excerpt: {landing_page_html}
""".strip()


def _clip(value: str, *, max_chars: int) -> str:
    text = value.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...[truncated]"


def _parse_model_response(response_text: str) -> tuple[dict[str, Any], bool]:
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError:
        return {"decision": "needs_review", "evidence": [response_text[:200]], "categories": ["model_review"]}, False
    if not isinstance(parsed, dict):
        return {"decision": "needs_review", "evidence": [response_text[:200]], "categories": ["model_review"]}, False
    return parsed, True


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
