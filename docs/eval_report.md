# Eval Report

Status: deterministic rule benchmark v1.

AdLint includes two labeled JSONL datasets:

- `evals/datasets/seed_ads.jsonl`: the original 50-example smoke set.
- `evals/datasets/rule_benchmark_v1.jsonl`: a 200-example benchmark generated
  from the seed set plus policy-author authored synthetic variants.

The benchmark covers health, wellness, finance, SaaS, creator disclosure,
privacy, landing-page mismatch, and brand-safety scenarios. It is regression
coverage for the policy-as-code engine, not evidence of legal compliance,
real-world platform approval, or production model quality.

## Reproducible Commands

Rebuild the committed benchmark dataset:

```bash
make benchmark-data
```

Run the 200-example benchmark and write JSON plus Markdown reports:

```bash
make benchmark
```

Run the original seed smoke eval:

```bash
make eval
```

Direct command used by the benchmark target:

```bash
.venv/bin/python evals/run_eval.py evals/datasets/rule_benchmark_v1.jsonl \
  --output evals/results/rule_benchmark_v1.json \
  --markdown-output evals/results/rule_benchmark_v1.md
```

## Metrics Reported

`evals/run_eval.py` reports:

- `decision_accuracy`.
- A decision confusion matrix for `approved`, `needs_review`, and `high_risk`.
- Per-decision precision and recall.
- Per-policy precision and recall with true-positive, false-positive, and
  false-negative counts.
- Per-category precision and recall, counted once per category per row.
- Review notes for decision mismatches, policy false positives, and policy
  false negatives.
- Row-level expected versus actual decisions, policy ids, categories, and
  evidence for actual policy hits.

## Current Benchmark Results

Current `rule_benchmark_v1` results from the local deterministic rule runner:

| Metric | Value |
| --- | ---: |
| Total examples | 200 |
| Decision accuracy | 1.000 |
| Expected approved | 51 |
| Expected needs_review | 48 |
| Expected high_risk | 101 |
| Policy false-positive review notes | 8 |
| Policy false-negative review notes | 0 |

Current confusion matrix:

| Expected \ Actual | approved | needs_review | high_risk |
| --- | ---: | ---: | ---: |
| approved | 51 | 0 | 0 |
| needs_review | 0 | 48 | 0 |
| high_risk | 0 | 0 | 101 |

Known policy-label review notes include broad `guaranteed_outcome` matches in
finance or professional-outcome copy, `brand_safety_misinformation` matches
when phrases such as "miracle cure" appear in health or creator examples, and
sensitive-social-issue matches on some LinkedIn targeting examples.

## Limitations

- The benchmark is policy-author authored and synthetic. Treat it as regression
  coverage for deterministic rules, not representative market data.
- The benchmark labels are useful for engineering tradeoffs, but they do not
  determine whether a campaign is legally compliant or guaranteed to pass an ad
  platform review.
- Precision and recall are measured against benchmark labels only. They are
  not estimates of real-world compliance-review performance.
- The current benchmark does not score rewrite quality, reviewer usefulness, or
  landing-page extraction quality beyond the policy hits produced from the
  extracted text.
- Optional model-assisted classification must be benchmarked separately when a
  local Ollama-compatible model is actually available.

## Known Failure Modes

- Broad keyword policies can over-trigger when a risky phrase appears in a
  negated, educational, or blocking-control context.
- Some phrases are intentionally multi-policy. For example, a health "miracle
  cure" claim can trigger both health-claim and misinformation review.
- Disclosure rules detect words like `sponsored` or `affiliate`; they do not
  judge whether disclosure placement is adequate.
- Negation handling is narrow and currently depends on nearby words such as
  `without`, `not`, or `no`.
- Landing-page mismatch detection is term based and can miss semantic matches
  or over-trigger when safe landing-page copy uses different wording.
- The benchmark does not include image creative, OCR, hosted model calls, or
  fine-tuned adapters.
