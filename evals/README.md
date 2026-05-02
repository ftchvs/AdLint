# AdLint Evals

The eval datasets are local, labeled JSONL files used to regression-test the
policy-as-code engine. They are not legal-compliance labels and do not predict
platform approval.

## Datasets

- `datasets/seed_ads.jsonl`: 50-example smoke set.
- `datasets/rule_benchmark_v1.jsonl`: 200-example deterministic benchmark.
- `datasets/real_cases_v1.jsonl`: 13 public-source, paraphrased real-case
  diagnostics. These rows are source-backed examples from FTC, ASA/CAP, and
  DOJ/HUD-style public actions or rulings, rewritten as deterministic local
  inputs. They are not a statistically reliable benchmark.

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

The seed and benchmark datasets are complete-coverage gates for current
policy ids. `real_cases_v1` is included in the inventory, but it remains
diagnostic-only and should not block coverage completeness by itself.

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

Compare rule-only, model-only, and hybrid behavior on the same real-case rows:

```bash
make real-cases-hybrid
```

`real-cases` and `real-cases-hybrid` intentionally use
`--min-decision-accuracy 0` because this dataset is diagnostic. Its value is in
the row-level false-positive and false-negative notes, not in a pass/fail gate.
The initial set is also all high-risk by construction, so decision accuracy is
not a reliability estimate.

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

Real-case rows are stricter. `evals/validate_real_cases.py` requires source and
label metadata:

- `source_type`, `source_org`, `source_url`, and `source_title`.
- `label_basis` and `label_confidence`.
- No live `landing_page_url` inside `input`; use deterministic
  `landing_page_html` or text fields instead.

See `evals/real_cases.md` for the real-case collection protocol.

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
