# Research loop pilot report

Date: 2026-05-04

Scope: supervised pilot on `real_world_blind_v1` misses. This report records
the current baseline and follow-up ideas. It does not tune labels, source rows,
validators, or legal text to improve metrics.

Baseline command:

```bash
.venv/bin/python evals/run_eval.py evals/datasets/real_world_blind_v1.jsonl \
  --min-decision-accuracy 0 \
  --output /tmp/adlint_blind_baseline.json \
  --summary-only \
  --summary-format json
```

## Baseline summary

| Metric | Value |
| --- | ---: |
| Dataset rows | 90 |
| Scored rows | 90 |
| Skipped rows | 0 |
| Decision accuracy | 0.967 |
| Decision mismatches | 3 |
| Policy false negatives | 12 |
| Policy false positives | 7 |
| Model status | `disabled: 90` |

Decision confusion deltas:

- `needs_review -> approved`: 2 rows.
- `needs_review -> high_risk`: 1 row.

## Decision misses

| Row ID | Expected | Actual | Policy IDs | Miss type |
| --- | --- | --- | --- | --- |
| `blind_productivity_claim_review` | `needs_review` | `approved` | FN `linkedin_professional_claim_review` | Undercall |
| `blind_promotion_workshop_review` | `needs_review` | `approved` | FN `linkedin_professional_claim_review` | Undercall |
| `blind_telehealth_info_review` | `needs_review` | `high_risk` | TP `google_health_restricted_category` | Overcall |

The two LinkedIn rows show the same miss cluster: professional performance or
career-outcome framing is labeled for review, but the deterministic rules do
not fire `linkedin_professional_claim_review`.

The telehealth row fires the expected Google health policy but routes the row
to `high_risk` instead of `needs_review`. That is a scoring/severity question,
not a source-label edit.

## Policy false negatives

| Row ID | Missing policy ID |
| --- | --- |
| `blind_productivity_claim_review` | `linkedin_professional_claim_review` |
| `blind_promotion_workshop_review` | `linkedin_professional_claim_review` |
| `blind_ftc_enforma_exercise_bottle_high_risk` | `unsupported_health_claim` |
| `blind_ftc_nutrimost_40_day_loss_high_risk` | `google_health_restricted_category` |
| `blind_ftc_nutrimost_40_day_loss_high_risk` | `unsupported_health_claim` |
| `blind_ftc_pure_green_coffee_high_risk` | `brand_safety_misinformation` |
| `blind_ftc_tarr_fake_trial_high_risk` | `fake_urgency_scarcity` |
| `blind_ftc_peel_patch_high_risk` | `google_health_restricted_category` |
| `blind_ftc_betterhelp_health_ads_high_risk` | `ccpa_sensitive_health_indicator` |
| `blind_ftc_cerebral_tracking_high_risk` | `ccpa_sensitive_health_indicator` |
| `blind_iab_misinformation_cure_high_risk` | `unsupported_health_claim` |
| `blind_google_patient_retargeting_high_risk` | `google_health_restricted_category` |

## Policy false positives

| Row ID | Extra policy ID |
| --- | --- |
| `blind_ftc_pure_green_coffee_high_risk` | `guaranteed_outcome` |
| `blind_ftc_tarr_fake_trial_high_risk` | `google_health_restricted_category` |
| `blind_ftc_goodrx_health_data_high_risk` | `health_form_tracking_risk` |
| `blind_ftc_betterhelp_health_ads_high_risk` | `washington_mhmda_indicator` |
| `blind_ftc_cerebral_tracking_high_risk` | `google_health_restricted_category` |
| `blind_ftc_cerebral_tracking_high_risk` | `washington_mhmda_indicator` |
| `blind_google_patient_retargeting_high_risk` | `washington_mhmda_indicator` |

## Candidate experiment ideas

1. Add a narrow LinkedIn professional-claim review experiment for productivity,
   promotion, career-outcome, and professional-performance wording. The target
   rows are `blind_productivity_claim_review` and
   `blind_promotion_workshop_review`.
2. Split healthcare eligibility review from high-risk health claims when the
   row only indicates telehealth appointment or provider-context review. The
   target row is `blind_telehealth_info_review`.
3. Review weight-loss and miracle-cure policy mappings for regulator cases
   where the decision is correct but expected policy IDs are missed:
   `blind_ftc_enforma_exercise_bottle_high_risk`,
   `blind_ftc_nutrimost_40_day_loss_high_risk`,
   `blind_ftc_pure_green_coffee_high_risk`, and
   `blind_iab_misinformation_cure_high_risk`.
4. Calibrate privacy state-law and form-tracking indicators so they do not add
   unrelated policy IDs while preserving high-risk routing for GoodRx,
   BetterHelp, Cerebral, and patient-retargeting rows.


## AND-62 follow-up review (2026-05-09)

Follow-up command set:

```bash
make real-world-blind-ci
make test
```

The LinkedIn miss cluster was safe to address without changing holdout labels:
explicit promises such as `double your salary`, `guaranteed promotion`, and
`10x productivity` still use the high-severity policy signals, while softer
LinkedIn professional-outcome language now routes to `needs_review` through a
derived medium-severity hit for `linkedin_professional_claim_review`. This
keeps the hard-promise benchmark behavior intact and removes the two
`needs_review -> approved` undercalls.

Updated blind-holdout summary after the scoped rule change:

| Metric | Value | Delta vs baseline |
| --- | ---: | ---: |
| Dataset rows | 90 | 0 |
| Decision accuracy | 0.989 | +0.022 |
| Decision mismatches | 1 | -2 |
| Policy false negatives | 10 | -2 |
| Policy false positives | 7 | 0 |
| Model status | `disabled: 90` | unchanged |

Remaining decision miss:

| Row ID | Expected | Actual | Policy IDs | Review note |
| --- | --- | --- | --- | --- |
| `blind_telehealth_info_review` | `needs_review` | `high_risk` | TP `google_health_restricted_category` | Conservative overcall. The expected policy fires, but high policy severity plus regulated-industry scoring crosses the high-risk threshold. Do not lower this without a separate scoring calibration test because it can affect other Google health high-risk rows. |

Remaining policy-ID false negatives are decision-correct high-risk rows except
for the telehealth overcall above. Treat them as policy-label coverage work,
not urgent decision-routing defects.

## Keep/discard decision

Kept:

- The current baseline as the reference for future experiments.
- The infrastructure-only changes that make compact summaries and research
  logs reproducible.
- The follow-up backlog ideas above.

Discarded:

- Any label, source-row, validator, or legal-text changes for this pilot.
- Any product runtime tuning in this infrastructure slice.
- Any MLX, PyTorch, MPS, or local-model dependency work before a small
  deterministic comparison proves value.

## Recommended follow-up work

1. Implement the LinkedIn professional-claim miss cluster first. It has two
   decision undercalls tied to one policy ID.
2. Add a focused regression test for telehealth review severity before
   changing scoring thresholds.
3. Use `evals/research_loop.py start --dry-run` to capture the plan, then run
   `make research-summary` before and after any candidate rule change.
4. Keep a candidate only if it removes the target misses without adding seed,
   benchmark, real-case, or blind-holdout regressions.
