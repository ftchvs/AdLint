# AdLint: Local-first policy-as-code preflight evaluation for ads

## Abstract

AdLint is a local-first ad preflight system for campaign copy, landing-page
signals, privacy risk, disclosure checks, and brand-safety review. This short
paper reports the current deterministic evaluation of AdLint's policy-as-code
engine on a 200-example synthetic benchmark. The benchmark reaches 1.000
decision accuracy across `approved`, `needs_review`, and `high_risk` labels,
with no decision mismatches and no policy false negatives in the included
review window. The main observed limitation is precision at the policy-label
level: 8 policy false-positive review notes remain, mostly from intentionally
broad phrase rules.

## 1. Introduction

Paid growth teams often need to review sensitive campaign claims before launch,
especially in health, wellness, financial, creator, privacy, and brand-safety
contexts. Hosted review systems can introduce data-handling concerns, while
general-purpose model checks are difficult to reproduce and audit.

AdLint takes a conservative local-first approach. Deterministic YAML policies
and Python scoring logic produce explainable decisions with policy ids,
evidence snippets, recommended actions, and safer rewrite suggestions. Optional
Ollama-compatible model review can add decision-support metadata, but the
deterministic policy engine remains the reproducible baseline.

## 2. Method

The evaluation uses three local JSONL datasets:

- `evals/datasets/seed_ads.jsonl`: a 50-example smoke dataset.
- `evals/datasets/rule_benchmark_v1.jsonl`: a 200-example benchmark generated
  from the seed set plus policy-author authored synthetic variants.
- `evals/datasets/real_cases_v1.jsonl`: a 13-example public-source diagnostic
  set derived from FTC, ASA/CAP, and DOJ/HUD-style public cases. These rows are
  paraphrased from public claim patterns and stored with source metadata.

Each row includes an input submission, an expected decision, and expected
policy ids. The runner evaluates decision accuracy, confusion matrices,
per-decision precision and recall, per-policy precision and recall,
per-category precision and recall, row-level evidence, and review notes for
false positives or false negatives.

The primary command for the deterministic benchmark is:

```bash
make benchmark
```

The model comparison command is:

```bash
make model-benchmark
```

The short required-model smoke command is:

```bash
make model-smoke
```

The real-case diagnostic command is:

```bash
make real-cases
```

The latest model comparison was run against an intentionally unavailable
loopback endpoint so unavailable-model behavior completed quickly and
reproducibly:

```bash
ADLINT_OLLAMA_URL=http://127.0.0.1:9/api/chat make model-benchmark
```

## 3. Results

The 200-example rule-only benchmark completed without skipped examples.

| Metric | Value |
| --- | ---: |
| Total examples | 200 |
| Decision accuracy | 1.000 |
| Decision mismatches | 0 |
| Policy false-positive review notes | 8 |
| Policy false-negative review notes | 0 |
| Expected approved | 51 |
| Expected needs_review | 48 |
| Expected high_risk | 101 |

The decision confusion matrix was diagonal:

| Expected \ Actual | approved | needs_review | high_risk |
| --- | ---: | ---: | ---: |
| approved | 51 | 0 | 0 |
| needs_review | 0 | 48 | 0 |
| high_risk | 0 | 0 | 101 |

Category-level recall was 1.000 for all tracked categories. Precision was
1.000 for landing-page, misrepresentation, platform-policy, and privacy
categories. Brand safety reached 0.885 precision, disclosure reached 0.929,
and health claims reached 0.929.

The all-modes comparison showed that rule-only and hybrid modes both scored
200 examples with 1.000 decision accuracy. Model-only skipped all 200 rows
because the local model endpoint was unavailable. Hybrid retained rule-based
decisions and attached unavailable-model metadata.

A separate local smoke run should be used before interpreting model quality. It
requires the configured Ollama model to return status `ok` on a small subset
before teams spend time on the full 200-row model comparison.

The latest smoke run reached status `ok` for all three model-required rows.
Hybrid decision accuracy stayed at 1.000 on the subset, while model-only
decision accuracy was 0.667. This supports the current architecture: use the
model as extra review signal, not as a replacement for deterministic policy
checks.

The initial real-case diagnostic run scored 13 public-source, paraphrased
cases. All 13 rows were expected high risk and rule-only produced high-risk
decisions for all 13. This is not a reliability estimate because the sample is
small and intentionally high-risk. It is, however, useful failure discovery:
the run surfaced 2 policy false-negative review notes and 11 policy
false-positive review notes, mostly around broad privacy and health-review
signals.

## 4. Discussion

The synthetic benchmark supports AdLint's current role as deterministic
regression coverage for the policy-as-code engine. Decision-level behavior is
stable on the synthetic benchmark, and the absence of false negatives is useful
for a preflight tool where missing high-risk content is more costly than
sending extra items to human review.

The real-case diagnostic set adds a different value: it prevents the project
from overfitting to synthetic examples. Its current result suggests that
decision routing is conservative on sourced high-risk cases, but policy-id
quality still needs adjudication. The next useful expansion is not
fine-tuning; it is 50 to 100 sourced cases with balanced decisions, label
confidence, and reviewer notes so rule-only, model-only, and hybrid value can
be compared without relying on hand-picked high-risk examples.

The remaining policy false positives are understandable from the rule design.
`guaranteed_outcome` intentionally captures broad guarantee language, even
when it appears in finance or professional-outcome examples. Brand-safety
misinformation rules can also fire on health phrases such as "miracle cure,"
which may be defensible as multi-policy risk but should be reviewed as label
coverage improves.

The model path should not be treated as validated by this run. The current
comparison only proves graceful unavailable-model handling. A future model
study should run against a pinned local model, record model status `ok`, and
compare model-only and hybrid outputs against the deterministic baseline.

## 5. Limitations

The benchmark is synthetic and policy-author authored. It is useful for
engineering regression testing, not for estimating real-world platform-review
approval rates or legal compliance. The current dataset does not include image
creative, OCR, hosted landing-page crawling at scale, reviewer usefulness, or
rewrite quality scoring.

## 6. Conclusion

AdLint currently has a reproducible local benchmark for deterministic ad
preflight checks. The rule-only engine reaches perfect decision accuracy on the
200-example synthetic benchmark while surfacing 8 policy-label false positives
for review. The next research step is to expand human-reviewed examples and
run a pinned local-model comparison only when the model endpoint is available.
