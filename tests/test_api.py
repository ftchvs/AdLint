from __future__ import annotations

import json
from typing import Any

from fastapi.testclient import TestClient

from adlint.api import app


client = TestClient(app)


class FakeOllamaResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.status = 200

    def __enter__(self) -> "FakeOllamaResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def high_risk_payload() -> dict[str, str]:
    return {
        "platform": "tiktok",
        "industry": "health",
        "headline": "Lose 20 pounds in 30 days guaranteed",
        "body": "Our clinically proven supplement melts fat fast.",
        "cta": "Buy now",
    }


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_accepts_valid_payload() -> None:
    response = client.post("/analyze", json=high_risk_payload())

    assert response.status_code == 200
    payload = response.json()
    assert payload["decision"] == "high_risk"
    assert {
        "decision",
        "risk_score",
        "policy_hits",
        "requires_review",
        "recommended_actions",
        "safer_rewrites",
        "landing_page",
        "enabled_modules",
        "model",
        "logging_enabled",
    } <= payload.keys()


def test_models_endpoint_returns_available_ollama_models(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        assert request.full_url == "http://localhost:11434/api/tags"
        return FakeOllamaResponse({"models": [{"name": "llama3.2:latest"}]})

    monkeypatch.delenv("ADLINT_OLLAMA_URL", raising=False)
    monkeypatch.delenv("ADLINT_OLLAMA_MODEL", raising=False)
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    response = client.get("/models")

    assert response.status_code == 200
    assert response.json() == {
        "provider": "ollama",
        "endpoint": "http://localhost:11434/api/chat",
        "default_model": "gpt-oss-safeguard:20b",
        "status": "ok",
        "models": ["llama3.2:latest"],
    }


def test_models_endpoint_returns_unavailable_reason(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        raise OSError("connection refused")

    monkeypatch.delenv("ADLINT_OLLAMA_URL", raising=False)
    monkeypatch.delenv("ADLINT_OLLAMA_MODEL", raising=False)
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    response = client.get("/models")

    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["models"] == []
    assert response.json()["reason"] == "connection refused"


def test_analyze_forwards_model_enabled_and_accepts_model_name(monkeypatch) -> None:
    seen = {}

    def fake_analyze(config, *, enable_model=None, ollama_model=None):
        seen["config"] = config
        seen["enable_model"] = enable_model
        seen["ollama_model"] = ollama_model

        class Result:
            def to_dict(self):
                return {"model": {"enabled": enable_model}}

        return Result()

    monkeypatch.setattr("adlint.api.analyze", fake_analyze)

    response = client.post(
        "/analyze",
        json={**high_risk_payload(), "model_enabled": True, "ollama_model": "llama3.2:latest"},
    )

    assert response.status_code == 200
    assert response.json() == {"model": {"enabled": True}}
    assert seen["enable_model"] is True
    assert seen["ollama_model"] == "llama3.2:latest"


def test_eval_accepts_labeled_examples() -> None:
    response = client.post(
        "/eval",
        json={
            "examples": [
                {
                    "input": {
                        "platform": "linkedin",
                        "industry": "saas",
                        "headline": "Plan campaign launches",
                        "body": "Coordinate launch notes.",
                        "cta": "Learn more",
                    },
                    "expected_decision": "approved",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["decision_accuracy"] == 1.0


def test_eval_accepts_empty_examples() -> None:
    response = client.post("/eval", json={"examples": []})

    assert response.status_code == 200
    assert response.json() == {
        "total_examples": 0,
        "labeled_examples": 0,
        "decision_accuracy": None,
        "results": [],
    }


def test_analyze_rejects_non_object_body() -> None:
    response = client.post("/analyze", json=["not", "an", "object"])

    assert response.status_code == 422


def test_eval_rejects_non_list_examples() -> None:
    response = client.post("/eval", json={"examples": "bad"})

    assert response.status_code == 422


def test_eval_rejects_non_object_example() -> None:
    response = client.post("/eval", json={"examples": ["bad"]})

    assert response.status_code == 422


def test_eval_rejects_non_object_input() -> None:
    response = client.post("/eval", json={"examples": [{"input": "bad"}]})

    assert response.status_code == 422


def test_ui_serves_static_page() -> None:
    response = client.get("/ui/")

    assert response.status_code == 200
    assert "AdLint" in response.text
    assert "decision-support" in response.text
    assert "not legal advice" in response.text


def test_ui_assets_are_served() -> None:
    js_response = client.get("/ui/app.js")
    css_response = client.get("/ui/styles.css")

    assert js_response.status_code == 200
    assert css_response.status_code == 200
    assert 'fetchWithTimeout("/analyze"' in js_response.text
    assert "logging_enabled: true" not in js_response.text
    assert ".result-panel" in css_response.text


def test_analyze_accepts_ui_payload_shape() -> None:
    response = client.post(
        "/analyze",
        json={
            "platform": "google",
            "industry": "wellness",
            "headline": "A calmer routine for better sleep",
            "body": "Join our wellness newsletter for science-backed sleep tips.",
            "cta": "Sign up",
            "policy_modules": ["health_claims", "platform", "privacy", "landing_page"],
            "landing_page_html": "<html><head><title>Sleep newsletter</title></head><body><h1>Simple sleep tips</h1><form><label>Email signup</label><input name='email'></form></body></html>",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert {
        "landing_page",
        "policy_hits",
        "recommended_actions",
        "safer_rewrites",
    } <= payload.keys()
    assert payload["landing_page"]["title"] == "Sleep newsletter"
    assert payload["landing_page"]["forms"] == ["Email signup, email"]


def test_analyze_passes_optional_ollama_model_override(monkeypatch) -> None:
    def fake_classify(submission, *, model=None, endpoint=None, landing_page=None):
        return [], {
            "enabled": True,
            "provider": "ollama",
            "model": model,
            "endpoint": endpoint,
            "status": "unavailable",
            "reason": "model_not_installed",
            "ran": False,
        }

    monkeypatch.setattr("adlint.engine.classify_with_ollama", fake_classify)

    response = client.post(
        "/analyze",
        json={
            **high_risk_payload(),
            "model_enabled": True,
            "ollama_model": "local-test-model",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"]["model"] == "local-test-model"
    assert payload["model"]["status"] == "unavailable"
