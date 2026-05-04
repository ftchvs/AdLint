# Real-case eval protocol

Real-case evals are a small, curated set of real or near-real advertising
review examples. They exist to expose product and policy failure modes that
synthetic rows miss: messy advertiser language, ambiguous claims, weak
landing-page support, platform-specific context, and reviewer disagreement.

Use this protocol before adding a real-case row or interpreting results from
one. Real-case rows are diagnostic evidence for engineering work. They are not
legal conclusions, platform-approval predictions, or a statistical benchmark.

## Purpose

Real cases should answer concrete questions:

- Did AdLint miss a policy issue that a reviewer expected it to flag?
- Did AdLint over-trigger on benign or adequately qualified copy?
- Did the local model add useful policy signal beyond deterministic rules?
- Did the model add noisy findings or make the final decision worse?
- Is a failure caused by policy coverage, extraction, scoring, prompt output,
  or an incomplete label?

The best real-case rows are those that create a short, inspectable trail from
input to expected label to observed failure.

## Diagnostic, not statistical

Do not report real-case rates as production-quality precision, recall, or
approval-risk estimates while the set is small and hand selected. These rows
are sampled because they are interesting, confusing, or representative of known
customer workflows. That makes them useful for debugging, but biased as a
population sample.

The current `real_cases_v1` set has 75 well-labeled public-source rows balanced
across `approved`, `needs_review`, and `high_risk`. Treat percentages as
diagnostic because the rows are curated rather than randomly sampled. Report
confidence carefully and keep synthetic regression benchmarks separate from
real-case diagnostics.

## Source tiers

Track the source tier for every row so reviewers know how much to trust the
case and what reuse rules apply.

- `tier_1_reviewed_customer_case`: permissioned customer or internal campaign
  case with reviewer notes and provenance.
- `tier_2_public_platform_case`: public ad-library, enforcement, or policy
  example where the source URL and access date are recorded.
- `tier_3_public_marketing_example`: public ad or landing-page copy collected
  for policy-review analysis, without platform outcome labels.
- `tier_4_synthetic_from_real_pattern`: synthetic copy based on a real failure
  pattern, rewritten enough to avoid copying protected text or private data.
- `tier_5_synthetic_control`: fully synthetic control row used to isolate one
  policy behavior near a real-case failure.

Prefer higher tiers for diagnosing production gaps. Use lower tiers when
privacy, copyright, or consent prevents storing the original material.

## Labeling fields

Each real-case row should use the standard eval row schema plus metadata that
explains why the label is trustworthy. Unknown fields are ignored by the
runner, so these can be added without changing execution.

Required fields:

- `id`: stable unique row id, prefixed with a source family when possible.
- `source_type`: source family such as `regulator_case`,
  `advertising_ruling`, `platform_example`, `customer_case`, or
  `synthetic_control`.
- `source_org`: regulator, platform, customer-review queue, or internal team
  that anchors the case.
- `source_url`: public source URL for public cases, or an approved internal
  reference URL for permissioned private cases.
- `source_title`: human-readable source title.
- `input`: ad submission payload accepted by `adlint.engine.analyze`.
- `expected_decision`: one of `approved`, `needs_review`, or `high_risk`.
- `expected_policy_ids`: expected YAML policy ids for the row.
- `source_tier`: one of the source tiers above.
- `label_basis`: short reason the label exists, such as reviewer decision,
  platform policy example, public enforcement context, or synthetic control.
- `label_confidence`: `high`, `medium`, or `low`; use lower confidence when
  the public source does not map cleanly to AdLint's current policy ids.
- `label_rationale`: concise explanation of the expected decision and policy
  ids.
- `provenance`: source URL, internal ticket id, file reference, or redaction
  note. Do not store private customer identifiers in this field.
- `accessed_at`: date the public source was accessed, when applicable.

Recommended fields:

- `policy_areas`: broad areas such as health, privacy, platform policy,
  landing page, disclosure, finance, or brand safety.
- `reviewer_notes`: short notes from human review or adjudication.
- `known_ambiguities`: why a reasonable reviewer or model may disagree.
- `redaction_notes`: what was removed or paraphrased.
- `copyright_status`: `owned`, `permissioned`, `public_excerpt`,
  `paraphrased`, or `synthetic`.
- `outcome_source`: `human_review`, `platform_action`, `policy_example`,
  `internal_adjudication`, or `none`.

The validator enforces the minimum metadata and deterministic-input contract:

```bash
make real-cases-validate
```

Real-case rows must not include live `landing_page_url` fields. Use
`landing_page_html` snippets or plain copy fields so the same row scores the
same way offline.

## Blind candidate-pool validation

The blind candidate pool keeps both accepted and rejected rows so reviewers can
audit how the 90-row holdout was selected from the 150-row public-source pool.
Run:

```bash
make real-world-blind-candidates
```

The candidate check enforces 150 total rows, 90 accepted rows, 60 rejected
rows, and a 30/30/30 accepted decision balance. Accepted rows keep strict id,
source URL, and normalized-headline duplicate checks because they become the
committed holdout. Rejected rows still need valid blind metadata and rejection
notes, but they may share normalized headlines with accepted rows because the
current rejected set intentionally includes clone rows used to document source
family pruning and final label balancing.

## Copyright and provenance rules

Keep real-case storage conservative:

- Do not commit private customer data, personal data, account ids, tracking
  ids, screenshots, or full landing-page captures unless the repo is approved
  for that material.
- Prefer short excerpts, structured summaries, and paraphrases over full copy
  from third-party sources.
- Record where the case came from and when it was accessed. Public pages can
  change or disappear.
- If a case is based on a customer or internal workflow, store a stable internal
  reference instead of names, emails, budgets, audiences, or identifiers.
- If a synthetic row is based on a real issue, say so in `source_tier`,
  `label_basis`, and `redaction_notes`.
- Do not use a row when provenance is unclear or when reuse rights are unknown.

## Interpreting failures

Start from the row-level evidence before changing policies or prompts.

- Decision undercall: expected risk is higher than actual risk. Check whether
  the expected policy id is missing, whether scoring weight is too low, or
  whether the input lacks the evidence the reviewer used.
- Decision overcall: actual risk is higher than expected risk. Check for broad
  keyword matches, negation, educational context, disclaimers, or policy ids
  that should be advisory instead of decisive.
- Policy false negative: an expected policy id is absent. Decide whether the
  rule needs coverage, the model should rescue it, or the label used the wrong
  policy id.
- Policy false positive: an unexpected policy id is present. Decide whether the
  rule is overbroad, the label is incomplete, or the case should expect
  multiple policies.
- Category mismatch: inspect whether policy ids map to the intended category
  before treating this as model or rule quality evidence.
- Model unavailable: do not count this as model quality. Count it separately as
  runtime availability or configuration evidence.

Failures should produce one of three outcomes: improve the rule or model path,
fix or clarify the label, or document an intentional product limitation.

## Measuring hybrid model value

Run real cases in `all` mode when model availability matters so rule-only,
model-only, and hybrid outputs are comparable. Interpret the hybrid section by
row and by aggregate counts, not only by decision accuracy.

Track these categories explicitly:

- Rescues: rows where rule-only missed the expected decision or policy and
  hybrid matched it. These are the strongest evidence that the model adds
  value.
- Regressions: rows where rule-only matched and hybrid became wrong. These are
  high-priority failures because the model degraded deterministic behavior.
- Model-added true expected policy hits: policy ids added by hybrid that are in
  `expected_policy_ids`. These show useful model recall even when the final
  decision does not change.
- Model-added false positives: policy ids added by hybrid that are not in
  `expected_policy_ids`. Review these for prompt noise, overly generic model
  policies, or incomplete labels.
- Unavailable model rows: rows where model status is unavailable, invalid, or
  otherwise not `ok`. Keep these out of model-quality claims and report them as
  environment coverage.

Use `decision_improvement_count`, `decision_regression_count`,
`model_rescued_policy_false_negative_count`,
`model_added_expected_policy_hit_count`,
`model_added_false_positive_policy_hit_count`, and
`model_unavailable_rows` as the first-pass hybrid summary. Then inspect the
review notes before deciding whether a row proves model value or label noise.
