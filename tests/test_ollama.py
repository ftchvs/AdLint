from __future__ import annotations

import json
from typing import Any

from adlint.classifiers.ollama import classify_with_ollama, list_local_models
from adlint.models import LandingPageSnapshot, Submission


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status: int = 200) -> None:
        self.payload = payload
        self.status = status

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_list_local_models_reads_ollama_tags(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        assert request.full_url == "http://localhost:11434/api/tags"
        assert request.get_method() == "GET"
        assert timeout == 10
        return FakeResponse(
            {
                "models": [
                    {"name": "llama3.2:latest"},
                    {"model": "gemma3:4b"},
                    {"name": ""},
                ]
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    assert list_local_models(endpoint="http://localhost:11434/api/chat") == {
        "provider": "ollama",
        "endpoint": "http://localhost:11434/api/chat",
        "default_model": "gpt-oss-safeguard:20b",
        "status": "ok",
        "models": ["llama3.2:latest", "gemma3:4b"],
    }


def test_list_local_models_rejects_non_loopback_endpoint(monkeypatch) -> None:
    def fake_urlopen(request, timeout):  # pragma: no cover - must not be called
        raise AssertionError("non-loopback endpoints must not be requested")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    payload = list_local_models(endpoint="https://example.com/api/chat")

    assert payload["status"] == "unavailable"
    assert payload["models"] == []
    assert "loopback" in payload["reason"]


def test_list_local_models_reports_invalid_tags_response(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse(["bad"])

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    payload = list_local_models(endpoint="http://localhost:11434/api/chat")

    assert payload["status"] == "invalid_response"
    assert payload["models"] == []
    assert "tags response" in payload["reason"]


def test_classify_with_ollama_sends_deterministic_chat_payload(monkeypatch) -> None:
    seen: dict[str, Any] = {}

    def fake_urlopen(request, timeout):
        seen["url"] = request.full_url
        seen["timeout"] = timeout
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({"message": {"content": '{"decision": "approved"}'}})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    hits, info = classify_with_ollama(
        Submission(platform="google", country="US", industry="general", headline="Hello"),
        model="llama3.2:latest",
        endpoint="http://127.0.0.1:11434/api/chat",
    )

    assert hits == []
    assert info["status"] == "ok"
    assert seen["url"] == "http://127.0.0.1:11434/api/chat"
    assert seen["timeout"] == 45
    assert seen["payload"]["model"] == "llama3.2:latest"
    assert seen["payload"]["stream"] is False
    assert seen["payload"]["format"] == "json"
    assert seen["payload"]["options"] == {"temperature": 0}
    assert seen["payload"]["messages"][0]["role"] == "user"


def test_classify_with_ollama_accepts_generation_timeout_override(monkeypatch) -> None:
    seen: dict[str, Any] = {}

    def fake_urlopen(request, timeout):
        seen["timeout"] = timeout
        return FakeResponse({"message": {"content": '{"decision": "approved"}'}})

    monkeypatch.setenv("ADLINT_OLLAMA_TIMEOUT", "120")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    classify_with_ollama(
        Submission(platform="google", country="US", industry="general", headline="Hello"),
        model="llama3.2:latest",
        endpoint="http://127.0.0.1:11434/api/chat",
    )

    assert seen["timeout"] == 120


def test_classify_with_ollama_accepts_num_predict_override(monkeypatch) -> None:
    seen: dict[str, Any] = {}

    def fake_urlopen(request, timeout):
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({"message": {"content": '{"decision": "approved"}'}})

    monkeypatch.setenv("ADLINT_OLLAMA_NUM_PREDICT", "256")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    classify_with_ollama(
        Submission(platform="google", country="US", industry="general", headline="Hello"),
        model="llama3.2:latest",
        endpoint="http://127.0.0.1:11434/api/chat",
    )

    assert seen["payload"]["options"] == {"temperature": 0, "num_predict": 256}


def test_classify_with_ollama_prompt_includes_bounded_landing_page_context(monkeypatch) -> None:
    seen: dict[str, Any] = {}

    def fake_urlopen(request, timeout):
        seen["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({"message": {"content": '{"decision": "approved"}'}})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    classify_with_ollama(
        Submission(
            platform="google",
            country="US",
            industry="health",
            headline="Book appointment",
            body="Discuss symptoms with a provider.",
            cta="Start quiz",
            landing_page_url="https://example.test/quiz",
            landing_page_html="<script>gtag('config','G-123')</script><form><input name='symptoms'></form>",
            policy_modules=("privacy", "platform"),
        ),
        model="llama3.2:latest",
        endpoint="http://127.0.0.1:11434/api/chat",
        landing_page=LandingPageSnapshot(
            url="https://example.test/quiz",
            title="Symptom quiz",
            forms=("Symptoms intake",),
            tracking_scripts=("gtag config",),
        ),
    )

    prompt = seen["payload"]["messages"][0]["content"]
    assert "Landing page URL: https://example.test/quiz" in prompt
    assert "Policy modules: privacy, platform" in prompt
    assert "<untrusted_ad_copy>" in prompt
    assert "<untrusted_landing_page_context>" in prompt
    assert "Trust boundary" in prompt
    assert "Title: Symptom quiz" in prompt
    assert "Form: Symptoms intake" in prompt
    assert "Tracking script: gtag config" in prompt
    assert "gtag" in prompt
    assert "symptoms" in prompt


def test_classify_with_ollama_reports_http_errors_as_unavailable(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse({"message": {"content": '{"decision": "approved"}'}}, status=500)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    hits, info = classify_with_ollama(
        Submission(platform="google", country="US", industry="general"),
        endpoint="http://localhost:11434/api/chat",
    )

    assert hits == []
    assert info["status"] == "unavailable"
    assert "500" in info["error"]


def test_classify_with_ollama_reports_invalid_response_status(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse({"message": {"content": "not json"}})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    hits, info = classify_with_ollama(
        Submission(platform="google", country="US", industry="general"),
        endpoint="http://localhost:11434/api/chat",
    )

    assert hits == []
    assert info["status"] == "invalid_response"
    assert info["raw_decision"] is None
    assert info["ignored"] is True
    assert "valid JSON" in info["validation_error"]


def test_classify_with_ollama_rejects_unknown_decision_without_hits(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse({"message": {"content": '{"decision": "banana", "evidence": []}'}})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    hits, info = classify_with_ollama(
        Submission(platform="google", country="US", industry="general"),
        endpoint="http://localhost:11434/api/chat",
    )

    assert hits == []
    assert info["status"] == "invalid_response"
    assert info["raw_decision"] == "banana"
    assert "decision must be" in info["validation_error"]


def test_classify_with_ollama_rejects_non_string_evidence_without_hits(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeResponse({"message": {"content": '{"decision": "needs_review", "evidence": [{"text": "bad"}]}'}})

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    hits, info = classify_with_ollama(
        Submission(platform="google", country="US", industry="general"),
        endpoint="http://localhost:11434/api/chat",
    )

    assert hits == []
    assert info["status"] == "invalid_response"
    assert "evidence" in info["validation_error"]
