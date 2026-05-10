# AdLint Report

- Decision: `high_risk`
- Risk score: `0.90`
- Requires review: `true`
- Model status: `disabled`

## Policy Hits

### unsupported_health_claim

- Severity: `high`
- Category: `health_claims`
- Recommended action: Remove or qualify the claim and provide substantiation.
- Evidence:
  - `body`: Our clinically proven supplement helps you lose 20 pounds and melts fat.

### weight_loss_claim

- Severity: `high`
- Category: `health_claims`
- Recommended action: Avoid absolute body or fat-loss language and route for review.
- Evidence:
  - `body`: Our clinically proven supplement helps you lose 20 pounds and melts fat.

### before_after_claim

- Severity: `medium`
- Category: `health_claims`
- Recommended action: Add context, substantiation, and typical-results disclosure.
- Evidence:
  - `headline`: Are you overweight? See a before and after transformation

### meta_personal_attributes_health

- Severity: `high`
- Category: `platform_policy`
- Recommended action: Reframe the ad around the product or service benefit without implying personal health attributes.
- Evidence:
  - `headline`: Are you overweight? See a before and after transformation

### meta_health_appearance_results

- Severity: `high`
- Category: `platform_policy`
- Recommended action: Avoid transformation framing and use qualified wellness-support language.
- Evidence:
  - `headline`: Are you overweight? See a before and after transformation
  - `body`: Our clinically proven supplement helps you lose 20 pounds and melts fat.

## Recommended Actions

- Remove or qualify the claim and provide substantiation.
- Avoid absolute body or fat-loss language and route for review.
- Reframe the ad around the product or service benefit without implying personal health attributes.
- Avoid transformation framing and use qualified wellness-support language.
- Add context, substantiation, and typical-results disclosure.

## Safer Rewrites

### Option 1

- Headline: Are you overweight? See a before and after transformation
- Body: Our developed with evidence-informed guidance supplement helps you lose 20 pounds and melts fat. Results vary.
- CTA: Learn more

### Option 2

- Headline: Support your wellness routine with daily nutrition
- Body: Designed to complement healthy habits. Individual results vary.
- CTA: Learn more


## Decision-Support Disclaimer

AdLint is a preflight decision-support tool. It does not provide legal advice, guarantee platform approval, or make definitive statutory violation determinations.
