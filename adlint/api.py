from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from adlint.classifiers.ollama import list_local_models
from adlint.engine import analyze


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    platform: str = "google"
    country: str = "US"
    industry: str = "general"
    headline: str = ""
    body: str = ""
    cta: str = ""
    target_age_range: str | None = None
    landing_page_url: str | None = None
    landing_page_html: str | None = None
    policy_modules: list[str] = Field(default_factory=list)
    modules: list[str] | None = None
    model_enabled: bool = False
    model_affects_score: bool = False
    ollama_model: str | None = None
    logging_enabled: bool = False
    log_path: str | None = None
    storage_enabled: bool = False
    storage_path: str | None = None

    def to_analyze_config(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class EvalRequest(BaseModel):
    examples: list[dict[str, Any]] = Field(default_factory=list)


app = FastAPI(
    title="AdLint API",
    version="0.1.0",
    description="Local-first ad compliance and brand-safety preflight API.",
)
STATIC_DIR = Path(__file__).with_name("static")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/models")
def models_endpoint() -> dict[str, Any]:
    return list_local_models()


@app.post("/analyze")
def analyze_endpoint(payload: AnalyzeRequest) -> dict[str, Any]:
    return analyze(
        payload.to_analyze_config(),
        enable_model=payload.model_enabled,
        ollama_model=payload.ollama_model,
    ).to_dict()


@app.post("/eval")
def eval_endpoint(payload: EvalRequest) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for index, item in enumerate(payload.examples, start=1):
        input_payload = item.get("input", item)
        if not isinstance(input_payload, dict):
            raise HTTPException(
                status_code=422,
                detail=f"example {index} input must be an object",
            )
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


app.mount("/ui", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
