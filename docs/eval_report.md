# Eval Report

Status: deterministic rule benchmark v1.

AdLint includes four labeled JSONL datasets:

- `evals/datasets/seed_ads.jsonl`: the 58-example smoke set.
- `evals/datasets/rule_benchmark_v1.jsonl`: a 209-example benchmark generated
  from the seed set plus policy-author authored synthetic variants.
- `evals/datasets/real_cases_v1.jsonl`: a 75-example public-source diagnostic
  set balanced across 25 approved, 25 needs-review, and 25 high-risk expected
  decisions. The rows are paraphrased and deterministic; they are not copied
  ad creative.
- `evals/datasets/real_world_blind_v1.jsonl`: a 90-example blind public
  web-source holdout balanced across 30 approved, 30 needs-review, and 30
  high-risk expected decisions. It remains separate from rule tuning until
  after first baseline reporting.

The benchmark covers health, wellness, finance, SaaS, creator disclosure,
privacy, landing-page mismatch, and brand-safety scenarios. It is regression
coverage for the policy-as-code engine, not evidence of legal compliance,
real-world platform approval, or production model quality.

## Reproducible Commands

Rebuild the committed benchmark dataset:

```bash
make benchmark-data
```

Run the 209-example benchmark and write JSON plus Markdown reports:

```bash
make benchmark
```

Refresh or validate the policy coverage inventory:

```bash
make policy-coverage
make policy-coverage-validate
```

`docs/policy_coverage_matrix.md` inventories which policy ids appear across
the seed, benchmark, and real-case datasets. Treat it as coverage tracking,
not a quality or reliability metric.

Landing-page extraction now includes dependency-light parsing of inline JSON
data blobs and common script-assigned text fields, such as `textContent`,
`innerText`, `innerHTML`, `label`, `placeholder`, `price`, and `disclaimer`.
This improves the local evidence available to the rule engine without browser
automation, crawling, external script fetching, or a change to robots handling.
Extraction quality is measured separately from policy decision quality; finding
more page text does not imply that a campaign is legally compliant or approved
by an ad platform.

Run rewrite-quality evaluation separately from decision accuracy:

```bash
make rewrite-quality
```

`evals/rewrite_quality.py` uses `evals/datasets/rewrite_quality_v1.jsonl` to
score deterministic safer rewrites on clarity, risk reduction, policy fit, and
intent preservation. The report includes `rewrite_quality` metrics and marks
`decision_accuracy` as not measured. Deterministic rewrites remain the
baseline before model-generated rewrite evaluation is introduced.

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

Run the CI gate for the same real-case rows:

```bash
make real-cases-ci
```

Validate only the real-case source metadata and 25/25/25 label balance:

```bash
make real-cases-validate
```

Run the same real-case rows in rule-only, model-only, and hybrid modes:

```bash
make real-cases-hybrid
```

Run the required live local-model quality comparison on the balanced real-case
set:

```bash
make real-cases-model-quality
```

Inspect and run the web-sourced blind holdout:

```bash
make real-world-blind-candidates
make real-world-blind-validate
make real-world-blind
make real-world-blind-model-quality
```

CI uses `make pr-preflight`, `make real-cases-ci`, and
`make real-world-blind-ci`. The real-case gate requires 1.000 rule-only
decision accuracy because this curated set should not regress. The blind
holdout gate uses 0.90 rule-only decision accuracy against the current 0.967
post-triage baseline, preserving room for known misses while still catching broad
reliability regressions. Both CI eval targets print compact summaries and
upload full JSON/Markdown reports as workflow artifacts.

Live local-model quality runs remain manual or scheduled diagnostics. They are
not required CI because local inference is slow and the current evidence still
supports deterministic rules as the production baseline.

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
- Per-mode elapsed runtime for eval jobs.
- Review notes for decision mismatches, policy false positives, and policy
  false negatives.
- Row-level expected versus actual decisions, policy ids, categories, and
  evidence for actual policy hits.
- Hybrid value metrics that separate generic `model_policy_review` additions
  from detailed YAML policy-id matches.

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
claim that future ads will pass review with 100% accuracy. If the 209 examples
were a representative random sample, 209/209 correct decisions would imply an
approximate 95% Wilson lower bound of 0.981, but this benchmark is authored
regression coverage rather than a random production sample.

## Real-case Diagnostic Results

`real_cases_v1` is intentionally separate from the synthetic benchmark. It is a
balanced curated diagnostic set, not a random production sample. Its value is
surfacing concrete policy-id misses, over-triggers, and hybrid-model changes
on source-backed cases.

The current adjudicated rule-only run produced:

| Metric | Value |
| --- | ---: |
| Total examples | 75 |
| Expected approved | 25 |
| Expected needs_review | 25 |
| Expected high_risk | 25 |
| Decision mismatches | 0 |
| Decision accuracy | 1.000 |
| Policy false-negative review notes | 0 |
| Policy false-positive review notes | 0 |

Current rule-only confusion matrix:

| Expected \ Actual | approved | needs_review | high_risk |
| --- | ---: | ---: | ---: |
| approved | 25 | 0 | 0 |
| needs_review | 0 | 25 | 0 |
| high_risk | 0 | 0 | 25 |

The current decision metric is stronger than the previous all-high-risk
diagnostic set because each decision label is represented equally. It is still
curated public-source coverage, so treat it as production-reliability
diagnostic evidence rather than a statistical estimate of real-world approval
or compliance performance.

The latest full real-case model-quality comparison used the local
`gpt-oss-safeguard:20b` model:

```bash
make real-cases-model-quality
```

It completed all 75 model-required rows with status `ok`:

| Mode | Scored rows | Skipped rows | Decision accuracy | Model status | Runtime |
| --- | ---: | ---: | ---: | --- | ---: |
| rule-only | 75 | 0 | 1.000 | `disabled: 75` | 0.993s |
| model-only | 75 | 0 | 0.493 | `ok: 75` | 599.513s |
| hybrid | 75 | 0 | 1.000 | `ok: 75` | 817.045s |

Model-only undercalled 38 rows: 24 `needs_review` rows were approved and 14
`high_risk` rows were downgraded. It did not overcall any approved rows in the
current dataset.

Hybrid retained the rule-only decision accuracy with zero decision regressions
and zero unavailable model rows. The model added 21 generic
`model_policy_review` findings, but it added 0 detailed expected YAML policy
ids and rescued 0 rule false negatives. Treat this as measured evidence that
the model can add review narration, but not yet detailed policy-id recall.

The full model-quality run took 1417.551 seconds locally. It is a manual or
scheduled quality eval, not a CI gate.

## Web-sourced Blind Holdout Results

`real_world_blind_v1` is the harder generalization check. It is separate from
`real_cases_v1`, uses public web/ad-library/regulator sources, and is marked
as a rule-tuning holdout.

The candidate workflow currently exposes 150 public-source candidates, with
90 accepted into the committed v1 holdout and 60 rejected candidates retained
for auditability. `make real-world-blind-candidates` validates the full pool:
150 total rows, 90 accepted, 60 rejected, and an accepted-row balance of 30
approved, 30 needs-review, and 30 high-risk rows.

Candidate source distribution:

| Status | Source platform | Rows |
| --- | --- | ---: |
| accepted | public_brand_page | 30 |
| accepted | google_ads_transparency | 15 |
| accepted | ftc | 12 |
| accepted | linkedin_ad_library | 11 |
| accepted | meta_ad_library | 9 |
| accepted | tiktok_ccl | 9 |
| accepted | asa | 4 |
| rejected | public_brand_page | 30 |
| rejected | google_ads_transparency | 9 |
| rejected | linkedin_ad_library | 7 |
| rejected | meta_ad_library | 6 |
| rejected | tiktok_ccl | 6 |
| rejected | asa | 2 |

Candidate capture-type distribution:

| Status | Capture type | Rows |
| --- | --- | ---: |
| accepted | ad_library_entry | 44 |
| accepted | public_marketing_page | 30 |
| accepted | regulator_case | 12 |
| accepted | ruling | 4 |
| rejected | public_marketing_page | 30 |
| rejected | ad_library_entry | 28 |
| rejected | ruling | 2 |

The first rule-only blind baseline produced:

| Metric | Value |
| --- | ---: |
| Total examples | 90 |
| Expected approved | 30 |
| Expected needs_review | 30 |
| Expected high_risk | 30 |
| Decision accuracy | 0.933 |
| Decision mismatches | 6 |
| Policy false-negative review notes | 15 |
| Policy false-positive review notes | 7 |

Blind rule-only confusion matrix:

| Expected \ Actual | approved | needs_review | high_risk |
| --- | ---: | ---: | ---: |
| approved | 30 | 0 | 0 |
| needs_review | 5 | 24 | 1 |
| high_risk | 0 | 0 | 30 |

This is the intended behavior for a blind holdout: it exposes misses and
overcalls that were hidden by the curated real-case set. The first misses are
clustered in semantic finance/professional claims, creator-brand disclosure,
sensitive social issue context, and selected expected policy-id mappings.

### Blind Miss Triage

The 2026-05-04 reliability pass reviewed the six decision mismatches from the
original `evals/results/real_world_blind_v1.json` baseline. Three rows were
intentionally consumed from the blind holdout for narrow deterministic signal
updates because the phrases generalize beyond the individual rows:
`projected return`, `brand-tagged`, and `faith leaders`. Future reporting
should keep the original 0.933 baseline separate from this post-triage metric.

| Row | Classification | Decision |
| --- | --- | --- |
| `blind_projection_return_review` | rule gap | Added `projected return` to `google_financial_claim_review`; after triage it routes to `needs_review`. |
| `blind_productivity_claim_review` | label/adjudication issue | Left unchanged; `improve team output` is weaker than the current LinkedIn professional-claim policy signals. |
| `blind_promotion_workshop_review` | label/adjudication issue | Left unchanged; promotion-prep copy lacks an outcome promise under the current deterministic policy. |
| `blind_telehealth_info_review` | acceptable limitation | Left unchanged; the expected policy id fires, but Google health-restricted category remains conservatively high severity. |
| `blind_creator_brand_tag_review` | rule gap | Added `brand-tagged` to `tiktok_disclosure_risk`; after triage it routes to `needs_review`. |
| `blind_religion_context_event_review` | rule gap | Added `faith leaders` to `brand_safety_sensitive_social_issue`; after triage it routes to `needs_review`. |

Before and after rule-only metrics:

| Metric | Original blind baseline | Post-triage run |
| --- | ---: | ---: |
| Decision accuracy | 0.933 | 0.967 |
| Decision mismatches | 6 | 3 |
| Policy false-negative review notes | 15 | 12 |
| Policy false-positive review notes | 7 | 7 |

Post-triage confusion matrix:

| Expected \ Actual | approved | needs_review | high_risk |
| --- | ---: | ---: | ---: |
| approved | 30 | 0 | 0 |
| needs_review | 2 | 27 | 1 |
| high_risk | 0 | 0 | 30 |

The first live blind model-quality run used `gpt-oss-safeguard:20b` and
completed all 90 model-required rows with status `ok`:

| Mode | Scored rows | Skipped rows | Decision accuracy | Model status | Runtime |
| --- | ---: | ---: | ---: | --- | ---: |
| rule-only | 90 | 0 | 0.933 | `disabled: 90` | 1.272s |
| model-only | 90 | 0 | 0.522 | `ok: 90` | 1050.946s |
| hybrid | 90 | 0 | 0.933 | `ok: 90` | 960.596s |

Model-only undercalled 43 rows and overcalled 0 rows. Hybrid made no decision
changes against rule-only, rescued 0 rule false negatives, and added 24
generic `model_policy_review` findings with 0 detailed expected YAML policy-id
hits. The full all-mode run took 2012.816 seconds locally.

A separate model smoke check verifies the configured local Ollama model on the
first three seed rows and fails if any model-required row cannot run. Run it
before full live model-quality jobs. The latest default smoke run completed
with model status `ok` for all model-required rows:

| Smoke mode | Scored rows | Skipped rows | Decision accuracy | Model status |
| --- | ---: | ---: | ---: | --- |
| rule-only | 3 | 0 | 1.000 | `disabled: 3` |
| model-only | 3 | 0 | 0.333 | `ok: 3` |
| hybrid | 3 | 0 | 1.000 | `ok: 3` |

The run took 81.508 seconds. Hybrid made no decision changes, the model added
2 generic `model_policy_review` findings, and it added 0 detailed expected YAML
policy ids or rescued rule false negatives.

Alternative local model/tuning checks do not justify expanding model influence:

| Configuration | Runtime | Model-only rows | Model-only accuracy | Hybrid accuracy | Model status | Generic review additions | Detailed policy-id additions | Rescued rule false negatives |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| `gpt-oss-safeguard:20b` default smoke | 81.508s | 3 | 0.333 | 1.000 | `ok: 3` | 2 | 0 | 0 |
| `gpt-oss-safeguard:20b`, `ADLINT_OLLAMA_NUM_PREDICT=128` smoke | 28.081s | 0 | 0.000 | 1.000 | `invalid_response: 3` | 3 | 0 | 0 |
| `qwen3.5:35b-a3b` blind diagnostic | 2749.144s | 0 | 0.000 | 0.656 | `invalid_response: 90` | 90 | 0 | 0 |

`ADLINT_OLLAMA_NUM_PREDICT=128` is faster but currently breaks structured JSON
parsing, so it should not become the default tuned setting. The installed
`qwen3.5:35b-a3b` model produced invalid structured responses on the full blind
diagnostic and a later smoke attempt was stopped after more than four minutes
without completed output. The recommended default remains
`gpt-oss-safeguard:20b` with normal generation settings, and deterministic
rules remain the production baseline.

These diagnostics prove local model availability, not replacement quality. They
also show why model-only should not replace deterministic rules yet: the local
model still undercalls rows and maps concerns to `model_policy_review` rather
than the detailed YAML policy ids.

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
- The decision benchmark does not score rewrite quality or reviewer usefulness.
  Use `make rewrite-quality` for the separate sampled rewrite rubric.
- Script-contained landing-page extraction increases observable local evidence
  only. Treat parse or fetch errors as landing-context diagnostics, not policy
  decisions or compliance approvals.
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
