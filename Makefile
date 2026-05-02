PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin
STAMP := $(VENV)/.installed

.PHONY: api dev scan eval test install

install: $(STAMP)

$(STAMP): pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install -e ".[dev]"
	touch $(STAMP)

dev: $(STAMP)
	$(BIN)/python -m adlint scan examples/high_risk_tiktok_health.json --output-dir reports

api: $(STAMP)
	$(BIN)/uvicorn adlint.api:app --reload

scan: $(STAMP)
	$(BIN)/python -m adlint scan examples/needs_review_google_wellness.json

eval: $(STAMP)
	$(BIN)/python evals/run_eval.py evals/datasets/seed_ads.jsonl --output evals/results/latest.json

test: $(STAMP)
	$(BIN)/python -m pytest
