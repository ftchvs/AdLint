.PHONY: dev scan eval test

dev:
	python -m adlint scan examples/high_risk_tiktok_health.json --output-dir reports

scan:
	python -m adlint scan examples/needs_review_google_wellness.json

eval:
	python evals/run_eval.py evals/datasets/seed_ads.jsonl --output evals/results/latest.json

test:
	python -m pytest
