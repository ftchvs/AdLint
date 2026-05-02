# AdLint Evals

The eval datasets are local, labeled JSONL files used to regression-test the
policy-as-code engine. They are not legal-compliance labels and do not predict
platform approval.

## Datasets

- `datasets/seed_ads.jsonl`: 50-example smoke set.
- `datasets/rule_benchmark_v1.jsonl`: 200-example deterministic benchmark.

Regenerate `rule_benchmark_v1.jsonl`:

```bash
make benchmark-data
```

Run the benchmark:

```bash
make benchmark
```

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

## Labeling Rules

- Labels should describe deterministic preflight-review expectations, not legal
  conclusions.
- Prefer current YAML policy ids from `adlint/policies/`.
- Keep examples local and deterministic. Do not add rows that require live
  network `landing_page_url` fetches.
- Use false-positive and false-negative review notes to document rule behavior
  that needs human review.
- Do not claim model quality from rule-only benchmark results.
