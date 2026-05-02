from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from adlint.engine import analyze


app = FastAPI(
    title="AdLint API",
    version="0.1.0",
    description="Local-first ad compliance and brand-safety preflight API.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze")
def analyze_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    return analyze(payload).to_dict()


@app.post("/eval")
def eval_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    examples = payload.get("examples", [])
    if not isinstance(examples, list):
        raise ValueError("examples must be a list")

    results: list[dict[str, Any]] = []
    for index, item in enumerate(examples, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"example {index} must be an object")
        input_payload = item.get("input", item)
        expected_decision = item.get("expected_decision")
        result = analyze(input_payload)
        row = {
            "index": index,
            "decision": result.decision,
            "risk_score": result.risk_score,
            "policy_ids": [hit.policy_id for hit in result.policy_hits],
        }
        if expected_decision is not None:
            row["expected_decision"] = expected_decision
            row["decision_match"] = result.decision == expected_decision
        results.append(row)

    labeled = [item for item in results if "decision_match" in item]
    decision_accuracy = None
    if labeled:
        decision_accuracy = round(
            sum(1 for item in labeled if item["decision_match"]) / len(labeled),
            3,
        )

    return {
        "total_examples": len(results),
        "labeled_examples": len(labeled),
        "decision_accuracy": decision_accuracy,
        "results": results,
    }
