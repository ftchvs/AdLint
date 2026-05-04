# AdLint: Local-first policy-as-code preflight evaluation for ads

## Abstract

AdLint is a local-first ad preflight system for campaign copy, landing-page
signals, privacy risk, disclosure checks, and brand-safety review. This short
paper reports the current deterministic evaluation of AdLint's policy-as-code
engine on a 200-example synthetic benchmark. The benchmark reaches 1.000
decision accuracy across `approved`, `needs_review`, and `high_risk` labels,
with no decision mismatches and no policy false-positive or false-negative
review notes in the included review window. The main observed limitation is
external validity: the synthetic benchmark is regression coverage, not a
population-level reliability estimate.

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

- `evals/datasets/seed_ads.jsonl`: a 54-example smoke dataset.
- `evals/datasets/rule_benchmark_v1.jsonl`: a 200-example benchmark generated
  from the seed set plus policy-author authored synthetic variants.
- `evals/datasets/real_cases_v1.jsonl`: a 75-example public-source diagnostic
  set balanced across 25 approved, 25 needs-review, and 25 high-risk expected
  decisions. These rows are paraphrased from public sources and stored with
  source metadata.

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

The live local-model quality command for the balanced real-case set is:

```bash
make real-cases-model-quality
```

Fallback behavior can still be reproduced with an intentionally unavailable
loopback endpoint:

```bash
ADLINT_OLLAMA_URL=http://127.0.0.1:9/api/chat make model-benchmark
```

The latest live model-quality comparison used the local
`gpt-oss-safeguard:20b` model on the balanced 75-row real-case set:

```bash
make real-cases-model-quality
```

## 3. Results

The 200-example rule-only benchmark completed without skipped examples.

| Metric | Value |
| --- | ---: |
| Total examples | 200 |
| Decision accuracy | 1.000 |
| Decision mismatches | 0 |
| Policy false-positive review notes | 0 |
| Policy false-negative review notes | 0 |
| Expected approved | 51 |
| Expected needs_review | 50 |
| Expected high_risk | 99 |

The decision confusion matrix was diagonal:

| Expected \ Actual | approved | needs_review | high_risk |
| --- | ---: | ---: | ---: |
| approved | 51 | 0 | 0 |
| needs_review | 0 | 50 | 0 |
| high_risk | 0 | 0 | 99 |

Category-level precision and recall were 1.000 for all tracked categories in
the adjudicated benchmark.

The 1.000 benchmark score should be read as internal regression evidence, not
as external reliability. If the 200 examples were a representative random
sample, 200/200 correct decisions would imply an approximate 95% Wilson lower
bound of 0.981. They are not random; they are authored policy coverage.

The all-modes fallback comparison showed that rule-only and hybrid modes both
scored 200 examples with 1.000 decision accuracy. Model-only skipped all 200
rows because the local model endpoint was unavailable. Hybrid retained
rule-based decisions and attached unavailable-model metadata.

A separate local smoke run should be used before interpreting model quality. It
requires the configured Ollama model to return status `ok` on a small subset
before teams spend time on the full 200-row model comparison.

The latest default smoke run reached status `ok` for all three model-required
rows. Hybrid decision accuracy stayed at 1.000 on the subset, while model-only
decision accuracy was 0.333. This supports the current architecture: use the
model as extra review signal, not as a replacement for deterministic policy
checks. A capped-generation smoke with `ADLINT_OLLAMA_NUM_PREDICT=128` was
faster but produced `invalid_response` for all three model-required rows, so it
is not a recommended default.

The current adjudicated real-case diagnostic run scored 75 public-source,
paraphrased cases balanced across 25 approved, 25 needs-review, and 25
high-risk expected decisions. Rule-only produced a diagonal confusion matrix
with no decision mismatches and no policy false-positive or false-negative
review notes. This is stronger diagnostic evidence than the previous
all-high-risk set, but it is still curated public-source coverage rather than
a random production sample.

The live `gpt-oss-safeguard:20b` run completed all 75 model-required rows with
status `ok`. Model-only decision accuracy was 0.493, with 38 undercalls and no
overcalls. Hybrid retained 1.000 decision accuracy with no decision
regressions. The model added 21 generic `model_policy_review` findings, but it
added zero detailed expected YAML policy ids, so current model value is review
narration rather than reliable policy-id recall.

## 4. Discussion

The synthetic benchmark supports AdLint's current role as deterministic
regression coverage for the policy-as-code engine. Decision-level behavior is
stable on the synthetic benchmark, and the absence of false negatives is useful
for a preflight tool where missing high-risk content is more costly than
sending extra items to human review.

The real-case diagnostic set adds a different value: it prevents the project
from overfitting to synthetic examples. Its current result suggests that
decision routing is internally consistent on sourced public examples across
all three decision labels. The next useful expansion is not fine-tuning; it is
continued adjudication of model-added value so rule-only, model-only, and
hybrid behavior can be compared beyond generic review burden.

The model path should be treated separately from deterministic reliability.
The live real-case model-quality run completed all 75 model-required rows with
status `ok`. Model-only decision accuracy was 0.493, with 38 undercalls and no
overcalls. Hybrid decision accuracy stayed at 1.000 with zero decision
regressions. The model added 21 generic `model_policy_review` findings, but it
added 0 detailed expected YAML policy ids and rescued 0 rule false negatives.

## 5. Limitations

The benchmark is synthetic and policy-author authored. It is useful for
engineering regression testing, not for estimating real-world platform-review
approval rates or legal compliance. The current dataset does not include image
creative, OCR, hosted landing-page crawling at scale, reviewer usefulness, or
rewrite quality scoring.

## 6. Conclusion

AdLint currently has a reproducible local benchmark for deterministic ad
preflight checks and a balanced 75-row public-source diagnostic set. The
rule-only engine reaches perfect decision accuracy on both current eval
surfaces with no current policy-label review notes. The next research step is
to keep separating deterministic reliability from measured local-model value.
