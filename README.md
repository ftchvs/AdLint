# AdLint

**Preflight risk checks for ads, landing pages, and growth campaigns before
launch.**

> Status: runnable CLI MVP. This repository ships a local-first Python package,
> deterministic policy engine, YAML policy files, JSON and Markdown reports,
> examples, tests, and a seed eval runner. API and web UI surfaces remain future
> phases.

AdLint is an open-source ad compliance and brand-safety engine for growth teams
working in regulated or sensitive categories. It is designed to review ad copy,
landing pages, and campaign metadata before launch, then return an explainable
risk decision with evidence, mitigation steps, and safer rewrites.

AdLint is decision-support software, not legal advice. It should not claim that
an ad is legally compliant or guaranteed to pass platform review. Its job is to
surface risk early, make review faster, and help teams fix risky language before
campaigns go live.

## Why this exists

Growth teams ship fast, but campaign risk is often discovered late: during ad
platform review, after account-quality issues, or in legal review. The risk is
especially high in health, wellness, finance, privacy-sensitive, employment,
housing, credit, and creator campaigns.

Many existing review tools are enterprise-only, opaque, or disconnected from
creative and build workflows. AdLint aims to be local-first, explainable, and
easy to plug into developer and marketing operations workflows.

## Planned capabilities

AdLint is intended to evaluate:

- Ad copy, including headline, body, CTA, platform, industry, and audience
  metadata.
- Landing pages, including titles, headings, visible claims, forms, pricing
  text, disclaimers, and tracking scripts.
- Policy-as-code rules defined in YAML.
- Model-based classifiers for ambiguous or nuanced policy calls.
- Brand-safety and suitability categories based on IAB-style sensitive-topic
  groupings.

The planned output includes:

- Decision: `approved`, `needs_review`, or `high_risk`.
- Numeric risk score.
- Policy categories triggered.
- Exact evidence from ad copy or landing-page content.
- Recommended disclosures, mitigation steps, or review actions.
- Safer rewrite suggestions that preserve campaign intent.
- Machine-readable JSON and human-readable Markdown reports.

## Target users

- Growth and performance marketers running always-on experiments.
- Startup founders and heads of growth in regulated or sensitive categories.
- Marketing operations teams and agencies managing multi-platform campaigns.
- Compliance reviewers and legal operations teams that need structured
  pre-review signals.
- Brand managers concerned with suitability, adjacency, and reputation risk.
- Engineers embedding campaign checks into CI, internal tools, or custom UIs.

## MVP focus

The MVP should focus on high-signal checks for health, wellness, finance, and
adjacent sensitive categories.

### Ad claim risk

Detect unsupported, absolute, or high-risk claims such as guaranteed outcomes,
clinical proof language, rapid weight-loss promises, income promises, or
medicalized claims that likely need substantiation or review.

### Platform policy risk

Provide initial modules for:

- Google Ads health and misrepresentation risk.
- TikTok misleading and weight-management ad risk.
- LinkedIn sensitive targeting and discrimination risk.

Meta support is planned for a later phase after the core policy engine works.

### Health privacy risk

Flag health-related landing pages and flows that may require review because
they combine sensitive health context with tracking pixels, ad platforms,
identifiers, forms, or conversion events.

Privacy findings should be labeled `requires_review`. AdLint should not make a
definitive HIPAA, FTC, Washington My Health My Data Act, or CCPA violation
determination.

### Brand safety and suitability

Classify pages and campaign context into sensitive-topic groupings such as
adult content, violence, politics, tragedy, misinformation, and sensitive social
issues. Attach a simple suitability level so teams can route risk consistently.

### Rewrite assistance

Suggest lower-risk variations that preserve the campaign's intent. Rewrites may
soften claims, add qualification, remove unsupported medical language, or
recommend disclosure language.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/adlint scan examples/high_risk_tiktok_health.json --output-dir reports
```

Or run the bundled example without installing the console script:

```bash
.venv/bin/python -m adlint scan examples/high_risk_tiktok_health.json --format markdown
```

Single-command local path:

```bash
make dev
```

Docker path:

```bash
docker compose up
```

## CLI interface

The CLI shape is:

```bash
adlint scan <config>
```

The first implementation pass includes the Python package, CLI command, policy
loader, deterministic rule engine, transparent scoring, rewrite suggestions,
report writer, seed evals, and sample data.

Planned input shape:

```json
{
  "platform": "tiktok",
  "country": "US",
  "industry": "health",
  "headline": "Lose 20 pounds in 30 days guaranteed",
  "body": "Our clinically proven supplement melts fat fast.",
  "cta": "Buy now",
  "landing_page_url": "https://example.com",
  "policy_modules": ["health_claims", "platform", "privacy"]
}
```

Planned output shape:

```json
{
  "decision": "high_risk",
  "risk_score": 0.91,
  "policy_hits": [
    {
      "policy_id": "unsupported_health_claim",
      "severity": "high",
      "category": "health_claims",
      "evidence": [
        {
          "text": "Lose 20 pounds in 30 days guaranteed",
          "source": "headline"
        }
      ],
      "recommended_action": "Remove or qualify the claim and provide substantiation."
    }
  ],
  "requires_review": true,
  "recommended_actions": [
    "Remove guaranteed weight-loss claim.",
    "Add substantiation or soften clinical claim."
  ],
  "safer_rewrites": [
    {
      "headline": "Support your wellness routine with daily nutrition",
      "body": "Designed to complement healthy habits. Individual results vary.",
      "cta": "Learn more"
    }
  ],
  "reports": {
    "json": "reports/adlint-report.json",
    "markdown": "reports/adlint-report.md"
  }
}
```

## Policy files

Bundled YAML policy files live under `adlint/policies/`:

- `ftc_health_claims.yml`
- `platform_google_ads.yml`
- `platform_tiktok_ads.yml`
- `platform_linkedin_ads.yml`
- `privacy_hipaa_marketing.yml`
- `privacy_tracking_pixels.yml`
- `privacy_consumer_health_data.yml`
- `brand_safety_iab.yml`
- `brand_custom_template.yml`

Custom policies can be loaded with:

```bash
adlint scan examples/high_risk_tiktok_health.json --policy-path ./my-policies
```

## Local model pass

Rules run without a model. To add a local Ollama-compatible classifier:

```bash
ollama pull gpt-oss-safeguard-20b
ADLINT_OLLAMA_MODEL=gpt-oss-safeguard-20b adlint scan examples/high_risk_tiktok_health.json --enable-model
```

If the model endpoint is unavailable, AdLint still returns rule-based findings
and marks the model status as `unavailable`.

## Evals and tests

```bash
make test
make eval
```

The seed eval set includes 50 curated examples across health, wellness,
finance, SaaS, creator disclosure, privacy, landing-page mismatch, and
brand-safety scenarios. It is a starting point, not a real-world benchmark.

## Example: high risk

Input:

```json
{
  "platform": "tiktok",
  "industry": "health",
  "headline": "Lose 20 pounds in 30 days guaranteed",
  "body": "Our clinically proven supplement melts fat fast.",
  "cta": "Buy now"
}
```

Expected planned decision:

```json
{
  "decision": "high_risk",
  "risk_score": 0.91,
  "policy_hits": [
    "unsupported_health_claim",
    "guaranteed_outcome",
    "weight_loss_claim"
  ],
  "evidence": [
    "Lose 20 pounds in 30 days guaranteed",
    "clinically proven supplement",
    "melts fat fast"
  ],
  "recommended_actions": [
    "Remove guaranteed outcome language.",
    "Qualify or substantiate clinical and weight-loss claims."
  ]
}
```

## Example: needs review

Input:

```json
{
  "platform": "google",
  "industry": "wellness",
  "headline": "A calmer routine for better sleep",
  "body": "Join our wellness newsletter for science-backed tips.",
  "cta": "Sign up",
  "landing_page_url": "https://example.com/sleep-newsletter"
}
```

Expected planned decision:

```json
{
  "decision": "needs_review",
  "risk_score": 0.52,
  "policy_hits": [
    "wellness_claim_review",
    "tracking_pixel_risk"
  ],
  "evidence": [
    "science-backed tips",
    "Meta Pixel detected on a health-adjacent signup page"
  ],
  "recommended_actions": [
    "Clarify what evidence supports the wellness claim.",
    "Review consent, tracking, and disclosure paths before launch."
  ]
}
```

## Policy-as-code design

Initial policy files are planned under `adlint/policies/`:

```text
ftc_health_claims.yml
platform_google_ads.yml
platform_tiktok_ads.yml
platform_linkedin_ads.yml
privacy_hipaa_marketing.yml
privacy_tracking_pixels.yml
privacy_consumer_health_data.yml
brand_safety_iab.yml
brand_custom_template.yml
```

Planned policy entry shape:

```yaml
id: unsupported_health_claim
severity: high
category: health_claims
description: Health or wellness claim likely requiring substantiation.
signals:
  - guaranteed
  - clinically proven
  - cure
  - lose * pounds
model_prompt: >
  Determine whether this ad makes a health-related claim that would likely
  require substantiation or compliance review under health marketing rules.
recommended_action: Remove or qualify the claim and provide substantiation.
example_positive:
  - "Lose 20 pounds in 30 days guaranteed."
example_negative:
  - "Support your wellness routine with daily nutrition. Results vary."
```

## Roadmap

1. CLI MVP: Python package, planned `adlint scan <config>` command, policy YAML
   loader, rule engine, scoring, JSON report, and Markdown report.
2. Policy modules: health claims, platform policies, privacy/tracking, and
   brand safety.
3. Local model integration: Ollama-compatible classification and rewrite calls
   using `gpt-oss-safeguard-20b`, `gpt-oss-20b`, or equivalent local models.
4. Evals: curated examples, labeled datasets, confusion matrix, and
   `docs/eval_report.md`.
5. Web UI: paste ad copy, add landing page URL, select platform and industry,
   view report, and export JSON or Markdown.
6. Optional fine-tuning: train and publish an adapter only after real evals show
   that it improves quality over prompted baselines.

## Non-goals

AdLint does not aim to:

- Guarantee platform approval.
- Provide legal advice or replace counsel.
- Make definitive HIPAA or statutory violation determinations.
- Store PHI or user-level customer data by default.
- Submit ads to platforms or mutate live ad accounts.
- Fine-tune models before enough labeled examples exist.

## References

- [OpenAI gpt-oss-safeguard](https://openai.com/index/introducing-gpt-oss-safeguard/)
- [OpenAI gpt-oss](https://openai.com/index/introducing-gpt-oss/)
- [HHS tracking technologies guidance](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/hipaa-online-tracking/index.html)
- [FTC health products compliance guidance](https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance)
- [FTC Health Breach Notification Rule](https://www.ftc.gov/tips-advice/business-center/guidance/complying-ftcs-health-breach-notification-rule)
- [Washington My Health My Data Act guidance](https://www.atg.wa.gov/protecting-washingtonians-personal-health-data-and-privacy)
- [California CCPA](https://oag.ca.gov/privacy/ccpa)
- [IAB Content Taxonomy](https://iabtechlab.com/standards/content-taxonomy/)
