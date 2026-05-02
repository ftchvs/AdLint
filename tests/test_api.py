from __future__ import annotations

from fastapi.testclient import TestClient

from adlint.api import app


client = TestClient(app)


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
