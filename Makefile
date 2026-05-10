PYTHON ?= python3
VENV := .venv
BIN := $(VENV)/bin
STAMP := $(VENV)/.installed
MODEL_EVAL_FLAGS ?= --ollama-model gpt-oss-safeguard:20b
ADLINT_OLLAMA_TIMEOUT ?= 180
ADLINT_OLLAMA_NUM_PREDICT ?= 1024

.PHONY: api dev scan eval benchmark benchmark-data policy-coverage policy-coverage-validate rewrite-quality model-benchmark model-smoke model-usefulness pr-preflight real-cases real-cases-ci real-cases-hybrid real-cases-model-quality real-cases-validate real-world-blind-candidates real-world-blind-ci real-world-blind-validate real-world-blind real-world-blind-model-quality research-summary test install

install: $(STAMP)

$(STAMP): pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install -e ".[dev]"
	touch $(STAMP)

dev: $(STAMP)
	$(BIN)/python -m adlint scan examples/high_risk_tiktok_health.json --output-dir reports

api: $(STAMP)
	ADLINT_OLLAMA_TIMEOUT=$(ADLINT_OLLAMA_TIMEOUT) ADLINT_OLLAMA_NUM_PREDICT=$(ADLINT_OLLAMA_NUM_PREDICT) $(BIN)/uvicorn adlint.api:app --reload

scan: $(STAMP)
	$(BIN)/python -m adlint scan examples/needs_review_google_wellness.json

eval: $(STAMP)
	$(BIN)/python evals/run_eval.py evals/datasets/seed_ads.jsonl --output evals/results/latest.json

research-summary: $(STAMP)
	$(BIN)/python evals/run_eval.py evals/datasets/seed_ads.jsonl --summary-only --summary-format json --min-decision-accuracy 0
	$(BIN)/python evals/run_eval.py evals/datasets/rule_benchmark_v1.jsonl --summary-only --summary-format json --min-decision-accuracy 0
	$(BIN)/python evals/run_eval.py evals/datasets/real_cases_v1.jsonl --summary-only --summary-format json --min-decision-accuracy 0
	$(BIN)/python evals/run_eval.py evals/datasets/real_world_blind_v1.jsonl --summary-only --summary-format json --min-decision-accuracy 0

benchmark-data: $(STAMP)
	$(BIN)/python evals/generate_benchmark_dataset.py

benchmark: $(STAMP)
	$(BIN)/python evals/run_eval.py evals/datasets/rule_benchmark_v1.jsonl --output evals/results/rule_benchmark_v1.json --markdown-output evals/results/rule_benchmark_v1.md

policy-coverage: $(STAMP)
	$(BIN)/python evals/validate_policy_coverage.py --markdown-output docs/policy_coverage_matrix.md

policy-coverage-validate: $(STAMP)
	$(BIN)/python evals/validate_policy_coverage.py --check docs/policy_coverage_matrix.md

rewrite-quality: $(STAMP)
	$(BIN)/python evals/rewrite_quality.py evals/datasets/rewrite_quality_v1.jsonl --output evals/results/rewrite_quality_v1.json --markdown-output evals/results/rewrite_quality_v1.md

model-benchmark: $(STAMP)
	$(BIN)/python evals/run_eval.py evals/datasets/rule_benchmark_v1.jsonl --mode all --output evals/results/model_comparison.json --markdown-output evals/results/model_comparison.md

model-usefulness: $(STAMP)
	$(BIN)/python evals/model_review_usefulness.py evals/results/model_comparison.json --output evals/results/model_review_usefulness.json --markdown-output evals/results/model_review_usefulness.md

model-smoke: $(STAMP)
	$(BIN)/python evals/run_eval.py evals/datasets/seed_ads.jsonl --mode all --limit 3 --require-model --min-decision-accuracy 0 --output evals/results/model_smoke.json --markdown-output evals/results/model_smoke.md

pr-preflight: $(STAMP)
	$(BIN)/python evals/preflight_eval_assets.py

real-cases-validate: $(STAMP)
	$(BIN)/python evals/validate_real_cases.py evals/datasets/real_cases_v1.jsonl --min-rows 75 --require-decision-count approved=25 --require-decision-count needs_review=25 --require-decision-count high_risk=25

real-cases: $(STAMP)
	$(BIN)/python evals/validate_real_cases.py evals/datasets/real_cases_v1.jsonl --min-rows 75 --require-decision-count approved=25 --require-decision-count needs_review=25 --require-decision-count high_risk=25
	$(BIN)/python evals/run_eval.py evals/datasets/real_cases_v1.jsonl --min-decision-accuracy 0 --output evals/results/real_cases_v1.json --markdown-output evals/results/real_cases_v1.md

real-cases-ci: $(STAMP)
	$(BIN)/python evals/validate_real_cases.py evals/datasets/real_cases_v1.jsonl --min-rows 75 --require-decision-count approved=25 --require-decision-count needs_review=25 --require-decision-count high_risk=25
	$(BIN)/python evals/run_eval.py evals/datasets/real_cases_v1.jsonl --min-decision-accuracy 1.0 --summary-only --output evals/results/real_cases_v1.json --markdown-output evals/results/real_cases_v1.md

real-cases-hybrid: $(STAMP)
	$(BIN)/python evals/validate_real_cases.py evals/datasets/real_cases_v1.jsonl --min-rows 75 --require-decision-count approved=25 --require-decision-count needs_review=25 --require-decision-count high_risk=25
	$(BIN)/python evals/run_eval.py evals/datasets/real_cases_v1.jsonl --mode all --min-decision-accuracy 0 --output evals/results/real_cases_hybrid.json --markdown-output evals/results/real_cases_hybrid.md

real-cases-model-quality: $(STAMP)
	$(BIN)/python evals/validate_real_cases.py evals/datasets/real_cases_v1.jsonl --min-rows 75 --require-decision-count approved=25 --require-decision-count needs_review=25 --require-decision-count high_risk=25
	ADLINT_OLLAMA_TIMEOUT=300 $(BIN)/python evals/run_eval.py evals/datasets/real_cases_v1.jsonl --mode all --require-model --min-decision-accuracy 0 $(MODEL_EVAL_FLAGS) --output evals/results/real_cases_model_quality.json --markdown-output evals/results/real_cases_model_quality.md

real-world-blind-candidates: $(STAMP)
	$(BIN)/python evals/collect_real_world_candidates.py --format summary

real-world-blind-validate: $(STAMP)
	$(BIN)/python evals/validate_real_cases.py evals/datasets/real_world_blind_v1.jsonl --blind --min-rows 90 --require-decision-count approved=30 --require-decision-count needs_review=30 --require-decision-count high_risk=30

real-world-blind: $(STAMP)
	$(BIN)/python evals/validate_real_cases.py evals/datasets/real_world_blind_v1.jsonl --blind --min-rows 90 --require-decision-count approved=30 --require-decision-count needs_review=30 --require-decision-count high_risk=30
	$(BIN)/python evals/run_eval.py evals/datasets/real_world_blind_v1.jsonl --min-decision-accuracy 0 --output evals/results/real_world_blind_v1.json --markdown-output evals/results/real_world_blind_v1.md

real-world-blind-ci: $(STAMP)
	$(BIN)/python evals/validate_real_cases.py evals/datasets/real_world_blind_v1.jsonl --blind --min-rows 90 --require-decision-count approved=30 --require-decision-count needs_review=30 --require-decision-count high_risk=30
	$(BIN)/python evals/run_eval.py evals/datasets/real_world_blind_v1.jsonl --min-decision-accuracy 0.90 --summary-only --output evals/results/real_world_blind_v1.json --markdown-output evals/results/real_world_blind_v1.md

real-world-blind-model-quality: $(STAMP)
	$(BIN)/python evals/validate_real_cases.py evals/datasets/real_world_blind_v1.jsonl --blind --min-rows 90 --require-decision-count approved=30 --require-decision-count needs_review=30 --require-decision-count high_risk=30
	ADLINT_OLLAMA_TIMEOUT=300 $(BIN)/python evals/run_eval.py evals/datasets/real_world_blind_v1.jsonl --mode all --require-model --min-decision-accuracy 0 $(MODEL_EVAL_FLAGS) --output evals/results/real_world_blind_model_quality.json --markdown-output evals/results/real_world_blind_model_quality.md

test: $(STAMP)
	$(BIN)/python -m pytest
