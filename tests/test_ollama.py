from __future__ import annotations

import json
import urllib.request

from adlint.classifiers import ollama
from adlint.models import Submission


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self.payload


def submission() -> Submission:
    return Submission.from_dict(
        {
            "platform": "google",
            "industry": "health",
            "headline": "Clinically proven supplement",
            "body": "Review before launch.",
            "cta": "Learn more",
        }
    )


def test_ollama_missing_model_does_not_call_generate(monkeypatch) -> None:
    calls: list[str] = []

    def fake_urlopen(request: urllib.request.Request, timeout: int):
        calls.append(request.full_url)
        assert request.full_url.endswith("/api/tags")
        return FakeResponse({"models": [{"name": "installed-model"}]})

    monkeypatch.setattr(ollama.urllib.request, "urlopen", fake_urlopen)

    hits, info = ollama.classify_with_ollama(submission(), model="missing-model")

    assert hits == []
    assert calls == ["http://localhost:11434/api/tags"]
    assert info["status"] == "unavailable"
    assert info["reason"] == "model_not_installed"
    assert info["ran"] is False


def test_ollama_blocks_non_local_endpoint_before_network(monkeypatch) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: int):  # pragma: no cover
        raise AssertionError("non-local endpoint should not be opened")

    monkeypatch.setattr(ollama.urllib.request, "urlopen", fake_urlopen)

    hits, info = ollama.classify_with_ollama(
        submission(),
        model="installed-model",
        endpoint="https://example.com/api/generate",
    )

    assert hits == []
    assert info["status"] == "unavailable"
    assert info["reason"] == "non_local_endpoint"
    assert info["ran"] is False


def test_ollama_available_model_calls_generate_with_deterministic_options(monkeypatch) -> None:
    requests: list[tuple[str, dict | None]] = []

    def fake_urlopen(request: urllib.request.Request, timeout: int):
        body = json.loads(request.data.decode("utf-8")) if request.data else None
        requests.append((request.full_url, body))
        if request.full_url.endswith("/api/tags"):
            return FakeResponse({"models": [{"name": "installed-model"}]})
        return FakeResponse(
            {
                "response": json.dumps(
                    {
                        "decision": "high_risk",
                        "evidence": ["Clinically proven supplement"],
                        "recommended_action": "Route for policy review.",
                    }
                )
            }
        )

    monkeypatch.setattr(ollama.urllib.request, "urlopen", fake_urlopen)

    hits, info = ollama.classify_with_ollama(submission(), model="installed-model")

    assert [url for url, _ in requests] == [
        "http://localhost:11434/api/tags",
        "http://localhost:11434/api/generate",
    ]
    assert requests[1][1]["options"] == {"temperature": 0}
    assert info["status"] == "ok"
    assert info["ran"] is True
    assert info["raw_decision"] == "high_risk"
    assert hits[0].policy_id == "model_policy_review"
    assert hits[0].severity == "high"


def test_ollama_invalid_model_response_is_metadata_not_hit(monkeypatch) -> None:
    def fake_urlopen(request: urllib.request.Request, timeout: int):
        if request.full_url.endswith("/api/tags"):
            return FakeResponse({"models": [{"name": "installed-model"}]})
        return FakeResponse({"response": "not json"})

    monkeypatch.setattr(ollama.urllib.request, "urlopen", fake_urlopen)

    hits, info = ollama.classify_with_ollama(submission(), model="installed-model")

    assert hits == []
    assert info["status"] == "invalid_response"
    assert info["reason"] == "invalid_json"
    assert info["ran"] is True
