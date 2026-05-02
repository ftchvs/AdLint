PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin

.PHONY: dev scan eval test install

install: $(BIN)/python

$(BIN)/python: pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install -e ".[dev]"

dev: $(BIN)/python
	$(BIN)/python -m adlint scan examples/high_risk_tiktok_health.json --output-dir reports

scan: $(BIN)/python
	$(BIN)/python -m adlint scan examples/needs_review_google_wellness.json

eval: $(BIN)/python
	$(BIN)/python evals/run_eval.py evals/datasets/seed_ads.jsonl --output evals/results/latest.json

test: $(BIN)/python
	$(BIN)/python -m pytest
