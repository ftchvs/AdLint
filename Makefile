PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin
STAMP := $(VENV)/.installed

.PHONY: api dev scan eval benchmark benchmark-data test install

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

benchmark-data: $(STAMP)
	$(BIN)/python evals/generate_benchmark_dataset.py

benchmark: $(STAMP)
	$(BIN)/python evals/run_eval.py evals/datasets/rule_benchmark_v1.jsonl --output evals/results/rule_benchmark_v1.json --markdown-output evals/results/rule_benchmark_v1.md

test: $(STAMP)
	$(BIN)/python -m pytest
