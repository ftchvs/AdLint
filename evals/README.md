# AdLint Evals

The eval datasets are local, labeled JSONL files used to regression-test the
policy-as-code engine. They are not legal-compliance labels and do not predict
platform approval.

## Datasets

- `datasets/seed_ads.jsonl`: 54-example smoke set.
- `datasets/rule_benchmark_v1.jsonl`: 200-example deterministic benchmark.
- `datasets/real_cases_v1.jsonl`: 75 public-source, paraphrased real-case
  diagnostics balanced across 25 `approved`, 25 `needs_review`, and 25
  `high_risk` expected decisions. These rows come from public marketing pages,
  public policy examples, FTC/ASA/CAP/HHS/DOJ-style sources, and platform or
  taxonomy guidance rewritten as deterministic local inputs.
- `datasets/real_world_blind_v1.jsonl`: 90 accepted public web-source blind
  holdout rows balanced across 30 `approved`, 30 `needs_review`, and 30
  `high_risk` expected decisions. These rows remain separate from rule tuning
  until after baseline reporting.
- `datasets/rewrite_quality_v1.jsonl`: sampled rewrite-quality annotations
  for deterministic safer rewrites. Rows include rubric checks and minimum
  scores for clarity, risk reduction, policy fit, and intent preservation.

Regenerate `rule_benchmark_v1.jsonl`:

```bash
make benchmark-data
```

Run the benchmark:

```bash
make benchmark
```

Validate or refresh policy coverage inventory:

```bash
make policy-coverage-validate
make policy-coverage
```

Run rewrite-quality evaluation separately from decision accuracy:

```bash
make rewrite-quality
```

`evals/rewrite_quality.py` reports a top-level `rewrite_quality` section and
sets `decision_accuracy.measured` to `false`. The default generator is
`deterministic`; model-generated rewrites are intentionally not evaluated until
deterministic rewrites remain a stable baseline.

Rewrite limitations:

- Deterministic rewrites are conservative templates, not final marketing copy.
- The rubric checks reviewer usefulness, not legal compliance or platform
  approval.
- Generic rewrites may preserve less brand voice than a human editor would.
- Model rewrite quality is intentionally out of scope until a model generator
  can beat the deterministic baseline on the same rubric.

Examples in `rewrite_quality_v1` cover a quantified weight-loss claim that
should become qualified wellness/nutrition copy, a health-form tracking row
that should shift to consent and privacy review language, and a cure claim
that should become general wellness support with professional-consult wording.

Run compact research-loop summaries:

```bash
make research-summary
```

The target prints deterministic JSON summaries for the seed, benchmark,
real-case, and blind-holdout datasets. These summaries include row counts,
decision accuracy, decision mismatches, confusion deltas, policy false
positive/negative counts, top review-note row IDs, model status counts, and
elapsed seconds.

The seed and benchmark datasets are complete-coverage gates for current
policy ids. `real_cases_v1` is included in the inventory, but it remains
diagnostic-only and should not block coverage completeness by itself.

Before packaging an eval PR, run the generated-asset preflight:

```bash
make pr-preflight
```

The preflight checks that the real-case generators, blind candidate helper,
and committed datasets are tracked in Git. It also verifies that
`real_cases_v1.jsonl` matches `generate_real_cases_dataset.build_rows()` and
that `real_world_blind_v1.jsonl` matches
`generate_real_world_blind_dataset.build_rows()`.

Compare rule-only, model-only, and hybrid modes:

```bash
make model-benchmark
```

Run a short required-model smoke check against the configured local model:

```bash
make model-smoke
```

This target uses the first three seed rows with `--require-model` and
`--min-decision-accuracy 0`. It checks runtime availability and structured
model responses, not full benchmark quality.

If no requested local model is installed, model-only rows are skipped and
hybrid rows keep the rule-only decision with model status metadata.

Validate and run the real-case diagnostic set:

```bash
make real-cases
```

Run the CI gate for the same rows:

```bash
make real-cases-ci
```

This gate requires 1.000 rule-only decision accuracy. The rows are curated and
source-backed, so CI should catch any deterministic regression immediately.

Validate only the 75-row balance and required source metadata:

```bash
make real-cases-validate
```

Compare rule-only, model-only, and hybrid behavior on the same real-case rows:

```bash
make real-cases-hybrid
```

Run the required live local-model quality comparison against the balanced
real-case set:

```bash
make real-cases-model-quality
```

`MODEL_EVAL_FLAGS` defaults to `--ollama-model gpt-oss-safeguard:20b` and can
be overridden when testing another installed Ollama-compatible model.
The target sets `ADLINT_OLLAMA_TIMEOUT=300` because local model inference can
be slow on political or other sensitive-context rows.

Inspect the 150-row public-source candidate pool and run the blind holdout:

```bash
make real-world-blind-candidates
make real-world-blind-validate
make real-world-blind
make real-world-blind-model-quality
```

Run the CI gate for the blind holdout:

```bash
make real-world-blind-ci
```

This gate uses a conservative 0.90 rule-only decision-accuracy threshold. The
current baseline is below perfect by design, so the holdout continues to expose
generalization misses without forcing rule tuning directly against it.

The blind model-quality target uses the same default
`MODEL_EVAL_FLAGS=--ollama-model gpt-oss-safeguard:20b` and writes ignored
JSON/Markdown artifacts under `evals/results/`.
If a non-default local model times out while generating verbose JSON, rerun the
direct `evals/run_eval.py` command with `ADLINT_OLLAMA_NUM_PREDICT=256` to cap
the model response without changing the dataset or decision thresholds.

Local model-quality targets intentionally remain manual/scheduled diagnostics.
Deterministic rules stay the production baseline unless measured quality
improves enough to change that contract.

## Row Schema

Required fields:

- `id`: stable unique row id.
- `input`: ad submission payload accepted by `adlint.engine.analyze`.
- `expected_decision`: one of `approved`, `needs_review`, or `high_risk`.
- `expected_policy_ids`: expected YAML policy ids for the row.

Optional fields:

- `expected_categories`: category labels when a row uses a policy id that is
  not available in the current YAML policy files.
- Metadata fields such as `coverage_tags`, `label_basis`, or
  `label_rationale` may be added later. The runner ignores unknown fields.

Rewrite-quality rows use a separate annotation format:

- `id`: stable row id.
- `input`: ad submission payload accepted by `adlint.engine.analyze`.
- `expected_policy_ids`: expected policy ids that should drive the rewrite.
- `quality_checks`: reviewer checks including `forbidden_terms`,
  `required_terms`, `risk_reduction_terms`, `intent_terms`, and optional length
  bounds.
- `min_scores`: minimum 1-5 scores for `clarity`, `risk_reduction`,
  `policy_fit`, and `intent_preservation`.
- `reviewer_rationale`: short human note explaining what a good rewrite should
  preserve or remove.

Real-case rows are stricter. `evals/validate_real_cases.py` requires source and
label metadata:

- `source_type`, `source_org`, `source_url`, and `source_title`.
- `label_basis` and `label_confidence`.
- `source_tier`, `label_rationale`, `provenance`, `accessed_at`,
  `policy_areas`, `copyright_status`, and `outcome_source`.
- No live `landing_page_url` inside `input`; use deterministic
  `landing_page_html` or text fields instead.

See `evals/real_cases.md` for the real-case collection protocol.

Blind holdout rows add `source_platform`, `source_capture_type`,
`ad_observed_status`, `adjudication_status`, `adjudicator_notes`, and
`rule_tuning_holdout`. The validator also rejects duplicate source URLs,
duplicate normalized headlines, live landing-page URLs, long raw copied ad
excerpts, screenshots, account ids, and targeting details.

## Labeling Rules

- Labels should describe deterministic preflight-review expectations, not legal
  conclusions.
- Prefer current YAML policy ids from `adlint/policies/`.
- Keep examples local and deterministic. Do not add rows that require live
  network `landing_page_url` fetches.
- Use false-positive and false-negative review notes to document rule behavior
  that needs human review.
- Do not claim model quality from rule-only benchmark results.
- Keep synthetic regression benchmarks separate from real-case diagnostics.
- Keep `real_world_blind_v1` separate from rule tuning until the first
  rule-only and live-model baselines are recorded.
