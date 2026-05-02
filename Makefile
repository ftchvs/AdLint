PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin
STAMP := $(VENV)/.installed

.PHONY: api dev scan eval benchmark benchmark-data policy-coverage policy-coverage-validate model-benchmark model-smoke real-cases real-cases-hybrid real-cases-validate test install

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

policy-coverage: $(STAMP)
	$(BIN)/python evals/validate_policy_coverage.py --markdown-output docs/policy_coverage_matrix.md

policy-coverage-validate: $(STAMP)
	$(BIN)/python evals/validate_policy_coverage.py --check docs/policy_coverage_matrix.md

model-benchmark: $(STAMP)
	$(BIN)/python evals/run_eval.py evals/datasets/rule_benchmark_v1.jsonl --mode all --output evals/results/model_comparison.json --markdown-output evals/results/model_comparison.md

model-smoke: $(STAMP)
	$(BIN)/python evals/run_eval.py evals/datasets/seed_ads.jsonl --mode all --limit 3 --require-model --min-decision-accuracy 0 --output evals/results/model_smoke.json --markdown-output evals/results/model_smoke.md

real-cases-validate: $(STAMP)
	$(BIN)/python evals/validate_real_cases.py evals/datasets/real_cases_v1.jsonl

real-cases: $(STAMP)
	$(BIN)/python evals/validate_real_cases.py evals/datasets/real_cases_v1.jsonl
	$(BIN)/python evals/run_eval.py evals/datasets/real_cases_v1.jsonl --min-decision-accuracy 0 --output evals/results/real_cases_v1.json --markdown-output evals/results/real_cases_v1.md

real-cases-hybrid: $(STAMP)
	$(BIN)/python evals/validate_real_cases.py evals/datasets/real_cases_v1.jsonl
	$(BIN)/python evals/run_eval.py evals/datasets/real_cases_v1.jsonl --mode all --min-decision-accuracy 0 --output evals/results/real_cases_hybrid.json --markdown-output evals/results/real_cases_hybrid.md

test: $(STAMP)
	$(BIN)/python -m pytest
