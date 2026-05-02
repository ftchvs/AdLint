# Eval Report

Status: deterministic rule benchmark v1.

AdLint includes three labeled JSONL datasets:

- `evals/datasets/seed_ads.jsonl`: the original 50-example smoke set.
- `evals/datasets/rule_benchmark_v1.jsonl`: a 200-example benchmark generated
  from the seed set plus policy-author authored synthetic variants.
- `evals/datasets/real_cases_v1.jsonl`: a 13-example public-source diagnostic
  set derived from FTC, ASA/CAP, and DOJ/HUD-style public cases. The rows are
  paraphrased and deterministic; they are not copied ad creative.

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

Run rule-only, model-only, and hybrid comparison. This remains safe when no
local model is installed; model-only rows are skipped and hybrid remains
rule-based with model status metadata:

```bash
make model-benchmark
```

Run a short required-model smoke check before a full model benchmark:

```bash
make model-smoke
```

Validate and run the public-source real-case diagnostic set:

```bash
make real-cases
```

Run the same real-case rows in rule-only, model-only, and hybrid modes:

```bash
make real-cases-hybrid
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
| Expected needs_review | 50 |
| Expected high_risk | 99 |
| Policy false-positive review notes | 0 |
| Policy false-negative review notes | 0 |

Current confusion matrix:

| Expected \ Actual | approved | needs_review | high_risk |
| --- | ---: | ---: | ---: |
| approved | 51 | 0 | 0 |
| needs_review | 0 | 50 | 0 |
| high_risk | 0 | 0 | 99 |

Current category-level precision and recall:

| Category | Precision | Recall | False positives | False negatives |
| --- | ---: | ---: | ---: | ---: |
| brand_safety | 1.000 | 1.000 | 0 | 0 |
| disclosure | 1.000 | 1.000 | 0 | 0 |
| health_claims | 1.000 | 1.000 | 0 | 0 |
| landing_page | 1.000 | 1.000 | 0 | 0 |
| misrepresentation | 1.000 | 1.000 | 0 | 0 |
| platform_policy | 1.000 | 1.000 | 0 | 0 |
| privacy | 1.000 | 1.000 | 0 | 0 |

Interpretation: the 1.000 score is strong evidence that the deterministic
rules and current benchmark labels are internally consistent. It is not a
claim that future ads will pass review with 100% accuracy. If the 200 examples
were a representative random sample, 200/200 correct decisions would imply an
approximate 95% Wilson lower bound of 0.981, but this benchmark is authored
regression coverage rather than a random production sample.

## Real-case Diagnostic Results

`real_cases_v1` is intentionally separate from the synthetic benchmark. It is
too small and too biased toward known high-risk public actions to estimate
production reliability. Its value is surfacing concrete policy-id misses,
over-triggers, and hybrid-model changes on source-backed cases.

The current adjudicated rule-only run produced:

| Metric | Value |
| --- | ---: |
| Total examples | 13 |
| Expected high_risk | 13 |
| Decision mismatches | 0 |
| Decision accuracy | 1.000 |
| Policy false-negative review notes | 0 |
| Policy false-positive review notes | 0 |

The current decision metric is not strong reliability evidence because every
seeded real-case row is high-risk by design. The useful signal is at policy
level: the previously surfaced real-case policy false positives and false
negatives have been adjudicated into either tighter rules or corrected
expected labels. Keep the real-case set diagnostic for now, and grow it to
balanced approved, needs-review, and high-risk cases before treating rates as
reliable.

If treated as a representative random sample, 13/13 correct decisions would
only imply an approximate 95% Wilson lower bound of 0.772. Because the set is
hand selected and all rows are high-risk, that bound is illustrative only; the
real-case set is useful for failure discovery, not reliability estimation.

The latest full all-modes comparison was run with an intentionally unavailable
loopback model endpoint:

```bash
ADLINT_OLLAMA_URL=http://127.0.0.1:9/api/chat make model-benchmark
```

Rule-only and hybrid modes both completed 200 scored examples with 1.000
decision accuracy. Model-only scored 0 examples and skipped all 200 rows
because the local Ollama-compatible endpoint was unavailable. Treat that as a
runtime availability result, not model-quality evidence.

A separate model smoke check now verifies the configured local Ollama model on
the first three seed rows and fails if any model-required row cannot run. The
latest smoke run completed with model status `ok` for all model-required rows:

| Smoke mode | Scored rows | Skipped rows | Decision accuracy | Model status |
| --- | ---: | ---: | ---: | --- |
| rule-only | 3 | 0 | 1.000 | `disabled: 3` |
| model-only | 3 | 0 | 0.667 | `ok: 3` |
| hybrid | 3 | 0 | 1.000 | `ok: 3` |

This proves local model availability. It also shows why model-only should not
replace deterministic rules yet: the local model still undercalled one health
review row in the smoke subset and maps concerns to `model_policy_review`
rather than the detailed YAML policy ids.

The current benchmark test now fails if the adjudicated rule benchmark or
real-case set produces policy false-positive or false-negative review notes.

For a paper-style summary of the benchmark design and result interpretation,
see `docs/research_paper.md`. For the compiled LaTeX paper with charts,
tables, and architecture diagrams, see `docs/adlint_hybrid_eval_paper.tex`.

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
  local Ollama-compatible model is actually available. The comparison command
  reports unavailable or skipped model rows instead of treating them as quality
  evidence.

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
