# AdLint PRD

Version: 0.2 draft
Product: Open-source ad compliance and brand-safety preflight for growth teams
Tagline: Preflight risk checks for ads, landing pages, and growth campaigns
before launch.

## 1. Summary

AdLint helps growth teams, founders, agencies, and builders review ads and
landing pages before launch. It flags risky claims, missing disclosures,
platform-policy concerns, health/privacy review triggers, landing-page
mismatches, and brand-safety risks.

AdLint is decision-support software. It should not claim that an ad is legally
compliant or guaranteed to pass platform review. It should classify creative as
`approved`, `needs_review`, or `high_risk`, then explain the decision with
specific evidence and safer rewrite suggestions.

The first release should be local-first, policy-as-code-first, and easy to run
from developer and marketing operations workflows.

## 2. Problem

Growth teams ship creative quickly, but compliance and brand risk often appear
late: during ad-platform review, after account-quality issues, during legal
review, or after a landing page has already collected traffic.

This risk is highest in health, wellness, finance, privacy-sensitive,
employment, housing, credit, and creator campaigns. Teams may need to reason
about unsupported claims, missing disclosures, sensitive targeting,
landing-page mismatch, health-data tracking, and unsafe content adjacency.

Most existing tools are opaque, enterprise-priced, or disconnected from daily
creative workflows. AdLint should provide an open-source, explainable,
local-first alternative.

## 3. Target users

Primary users:

- Growth and performance marketers running always-on experimentation.
- Startup founders and heads of growth in regulated or sensitive categories.
- Marketing operations teams and agencies managing campaigns across Google,
  TikTok, LinkedIn, and future platforms.

Secondary users:

- Compliance reviewers and legal operations teams that need structured
  pre-review signals.
- Brand managers concerned with suitability and adjacency.
- Engineers embedding campaign checks into CI, internal tools, or custom UIs.

## 4. Core value proposition

AdLint analyzes ad copy, landing pages, and campaign metadata, then returns:

- Decision: `approved`, `needs_review`, or `high_risk`.
- Numeric risk score.
- Policy categories triggered.
- Exact evidence from the ad or page.
- Required or recommended disclosures and mitigation steps.
- Safer rewrites that preserve campaign intent while lowering risk.
- Machine-readable JSON report.
- Human-readable Markdown report.

## 5. Product principles

- Policy-as-code first: policies live in version-controlled YAML with clear
  IDs, severities, categories, signals, prompts, and recommended actions.
- Explainable by default: every decision traces back to policy IDs, evidence
  strings, sources, severities, and model reasoning where applicable.
- Local-first: the planned MVP should run with Ollama-compatible open-weight
  models such as `gpt-oss-safeguard-20b`, `gpt-oss-20b`, or equivalent local
  models.
- Privacy-conscious: raw submissions are not persisted by default. Health and
  privacy findings are labeled `requires_review`, not definitive violations.
- Composable: CLI, API, and library modes should be first-class so teams can
  plug AdLint into CI, internal tools, and future UIs.

## 6. MVP scope

The MVP focuses on high-signal checks for health, wellness, finance, and
adjacent sensitive categories.

### 6.1 Ad claim risk

AdLint should detect unsupported, absolute, or extreme claims, including:

- Guaranteed outcomes.
- "Clinically proven" or "doctor recommended" language without substantiation.
- Weight-loss, body-image, medical, income, or performance promises.
- Before/after claims.
- Fake urgency or scarcity.
- Absolute claims like "risk-free," "cure," "guaranteed," or "instant."

### 6.2 Platform policy risk

Initial platform modules:

- Google Ads: health, misrepresentation, and restricted-category risk.
- TikTok Ads: misleading content, weight-management claims, and disclosure risk.
- LinkedIn Ads: sensitive targeting, discrimination, and professional claims.

Meta should be represented as `meta_later` in configuration and added after the
core system is working.

### 6.3 Health privacy risk

AdLint should flag health or wellness landing pages that may require review
because they combine sensitive health context with tracking pixels, ad platform
scripts, identifiers, forms, conversion events, or unclear consent paths.

Initial health/privacy modules:

- HIPAA marketing review triggers for covered-entity or business-associate
  contexts.
- Health landing page plus tracking-pixel risk.
- FTC Health Breach Notification Rule indicators for health apps and connected
  devices.
- Washington My Health My Data Act indicators.
- California CCPA sensitive health-data indicators.

All HIPAA/privacy findings must be marked as `requires_review`, not definitive
legal violations.

### 6.4 Brand safety and suitability

AdLint should classify campaign and page context using IAB-style sensitive-topic
categories:

- Adult content.
- Violence.
- Tragedy or conflict.
- Politics.
- Misinformation.
- Sensitive social issues.
- Unsafe or controversial content.

Where helpful, policy IDs should map to IAB Content Taxonomy 2.2 sensitive
topics and simple suitability levels such as `low`, `medium`, `high`, and
`floor`.

### 6.5 Rewrite assistant

For each high-risk policy hit where a rewrite is feasible, AdLint should
suggest safer alternatives that preserve campaign intent while lowering risk.

Examples:

- Replace guaranteed outcomes with qualified claims.
- Add "individual results vary" where appropriate.
- Remove unsupported medical language.
- Suggest a softer CTA.
- Add disclosure reminders for sponsored or affiliate content.

## 7. Non-goals

The MVP will not:

- Guarantee platform approval.
- Provide legal advice.
- Replace legal or compliance teams.
- Store PHI or user-level customer data by default.
- Auto-submit ads to platforms.
- Make live changes in ad accounts.
- Make definitive HIPAA or statutory violation determinations.
- Fine-tune a model before enough labeled data exists.

Fine-tuning should be considered only after a useful labeled dataset exists and
benchmarks show a clear improvement over prompted baselines.

## 8. Example input and output

### 8.1 High-risk example

Input:

```json
{
  "platform": "tiktok",
  "country": "US",
  "industry": "health",
  "target_age_range": "18-45",
  "headline": "Lose 20 pounds in 30 days guaranteed",
  "body": "Our clinically proven supplement melts fat fast. Try it risk-free today.",
  "cta": "Buy now",
  "landing_page_url": "https://example.com",
  "policy_modules": ["health_claims", "platform", "privacy"]
}
```

Expected output shape:

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
        },
        {
          "text": "clinically proven supplement",
          "source": "body"
        }
      ],
      "recommended_action": "Remove or qualify the claim and provide substantiation."
    },
    {
      "policy_id": "weight_loss_claim",
      "severity": "high",
      "category": "platform_policy",
      "evidence": [
        {
          "text": "melts fat fast",
          "source": "body"
        }
      ],
      "recommended_action": "Avoid absolute body or fat-loss language."
    }
  ],
  "requires_review": true,
  "recommended_actions": [
    "Remove guaranteed weight-loss claim.",
    "Add substantiation or soften clinical claim.",
    "Avoid absolute fat-loss language."
  ],
  "safer_rewrites": [
    {
      "headline": "Support your wellness routine with daily nutrition",
      "body": "Designed to complement healthy habits. Individual results vary.",
      "cta": "Learn more"
    }
  ]
}
```

### 8.2 Borderline needs-review example

Input:

```json
{
  "platform": "google",
  "country": "US",
  "industry": "wellness",
  "headline": "A calmer routine for better sleep",
  "body": "Join our wellness newsletter for science-backed sleep tips.",
  "cta": "Sign up",
  "landing_page_url": "https://example.com/sleep-newsletter"
}
```

Expected output shape:

```json
{
  "decision": "needs_review",
  "risk_score": 0.52,
  "policy_hits": [
    {
      "policy_id": "wellness_claim_review",
      "severity": "medium",
      "category": "health_claims",
      "evidence": [
        {
          "text": "science-backed sleep tips",
          "source": "body"
        }
      ],
      "recommended_action": "Clarify substantiation for the wellness claim."
    },
    {
      "policy_id": "tracking_pixel_risk",
      "severity": "medium",
      "category": "privacy",
      "evidence": [
        {
          "text": "Meta Pixel detected on a health-adjacent signup page",
          "source": "landing_page"
        }
      ],
      "recommended_action": "Review consent, tracking, and disclosure paths."
    }
  ],
  "requires_review": true,
  "safer_rewrites": [
    {
      "headline": "Simple ideas for a calmer evening routine",
      "body": "Get practical wellness tips for building healthier habits. Results vary.",
      "cta": "Sign up"
    }
  ]
}
```

## 9. Functional requirements

### Submission and ingestion

- FR-1: User can submit ad copy with headline, body, and CTA through planned
  CLI, API, or UI surfaces.
- FR-2: User can provide an optional landing page URL.
- FR-3: System extracts page title, headings, visible claims, forms, pricing
  text, disclaimers, and tracking scripts where robots and security constraints
  allow.

### Configuration

- FR-4: User can select platform: `google`, `tiktok`, `linkedin`, or
  `meta_later`.
- FR-5: User can select industry: `health`, `wellness`, `finance`, `saas`,
  `creator`, or `general`.
- FR-11: System supports custom policy files in YAML, loaded from
  `adlint/policies/` or a configured path at runtime.
- FR-16: User can enable or disable specific policy modules through config.

### Evaluation pipeline

- FR-6: System runs deterministic rule checks first using regexes, keyword
  patterns, and simple heuristics.
- FR-7: System runs model-based classification for nuanced or ambiguous cases
  using `gpt-oss-safeguard-20b` or an equivalent local classifier.
- FR-9: System identifies exact risky phrases and maps them to policy IDs,
  categories, severities, sources, and recommended actions.
- FR-15: HIPAA and privacy flags are labeled `requires_review` with a short
  explanation, not as definitive violations.

### Outputs

- FR-8: System returns a structured JSON object and optional Markdown or HTML
  human-readable report.
- FR-10: System suggests safer rewrites, with at least one rewrite per
  high-risk policy hit where feasible.
- FR-12: System includes an eval runner that can score model and rule outputs
  against labeled examples.
- FR-14: System does not persist raw submissions by default. Users can
  optionally enable logging for evaluation.

### Runtime and deployment

- FR-13: System can run locally using Ollama-compatible open-weight models, with
  documentation for loading `gpt-oss-safeguard-20b` or fallback models.
- FR-17: System provides a planned single-command local run path such as
  `docker compose up` or `make dev`, plus planned CLI command
  `adlint scan <config>`.

## 10. Policy modules

Initial policy files:

```text
adlint/policies/
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

Policy file shape:

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

Policy entries should support optional mappings to brand-safety or suitability
taxonomies where useful:

```yaml
iab_taxonomy:
  content_taxonomy_version: "2.2"
  sensitive_topic: "health"
  suitability_level: medium
```

## 11. Technical architecture

Recommended MVP stack:

- Frontend: lightweight Next.js, Streamlit, or Gradio dashboard in a later
  phase.
- Backend: Python FastAPI service exposing planned `/analyze` and `/eval`
  endpoints.
- CLI: planned `adlint scan <config>` command.
- Local model runtime: Ollama or equivalent.
- Classification model: `gpt-oss-safeguard-20b` or equivalent local policy
  classifier.
- Rewrite model: `gpt-oss-20b` or equivalent local reasoning model.
- Scraping: Playwright for JavaScript-enabled pages, with `trafilatura` as a
  static extraction fallback.
- Storage: SQLite for eval datasets, run metadata, and optional anonymized
  logs.
- Config: environment variables plus YAML policy files.
- Output: JSON plus Markdown report with sections for overview, policy hits,
  evidence, rewrites, privacy, and tracking.

Processing pipeline:

```text
Input (ad + metadata)
  -> Normalize ad and page data
  -> Landing page fetch and extraction
  -> Tracker and pixel detection
  -> Rule-based checks
  -> Policy classifier
  -> Risk scoring
  -> Rewrite generation
  -> JSON and Markdown report
```

## 12. Risk scoring

MVP scoring should be simple and transparent so users can tune it:

```text
risk_score =
  max_policy_severity_weight
  + evidence_count_weight
  + regulated_category_weight
  + landing_page_mismatch_weight
  + privacy_tracking_weight
```

Suggested severity weights:

```text
low = 0.2
medium = 0.4
high = 0.7
critical = 0.9
```

Suggested decision thresholds:

```text
0.00 - 0.34 = approved
0.35 - 0.69 = needs_review
0.70 - 1.00 = high_risk
```

Thresholds should be configurable in a future `scoring.yml` file so teams can
calibrate sensitivity by use case. High-severity health, privacy, and safety
categories should favor recall over precision.

## 13. Evaluation plan

Create 200-500 labeled examples over time across several axes.

Decision labels:

- `approved`
- `needs_review`
- `high_risk`

Policy labels:

- `unsupported_claim`
- `misleading_claim`
- `missing_disclosure`
- `sensitive_targeting`
- `health_privacy_risk`
- `tracking_pixel_risk`
- `landing_page_mismatch`
- `brand_safety_risk`

Metrics:

- Accuracy for overall decision.
- Precision by policy category.
- Recall by policy category, with emphasis on high-severity health, privacy,
  and safety categories.
- False positive rate.
- Manually reviewed false negatives.
- Rewrite quality review for clarity, risk reduction, and intent preservation.

The repo should eventually include `docs/eval_report.md` with benchmark
results, limitations, representative examples, and known failure modes.

## 14. Phase plan

### Phase 1: Core engine MVP

- Python package structure.
- Planned `adlint scan <config>` CLI command.
- Policy YAML loader.
- Deterministic rule engine.
- Ollama-compatible model calls.
- Risk scoring.
- JSON and Markdown reports.
- Approximately 50 curated sample ads focused on health and wellness.

### Phase 2: Web UI

- Paste ad copy and metadata.
- Add landing page URL.
- Select platform and industry.
- View detailed report and rewrites.
- Export Markdown and JSON.
- Copy safer rewrites.

### Phase 3: Evals and benchmark

- 200-500 labeled examples.
- Confusion matrix.
- Rule-only vs. model-only vs. hybrid comparison.
- Public benchmark report in `docs/eval_report.md`.

### Phase 4: Optional fine-tuning

- LoRA or adapter-based classifier trained on collected labeled examples.
- Comparison against prompted `gpt-oss-safeguard-20b` baseline.
- Published adapter and model card only if quality improves.

## 15. Suggested repository structure

```text
adlint/
  README.md
  PRD.md
  app/
  api/
  adlint/
    classifiers/
    policies/
    rules/
    scrapers/
    scoring/
    rewrites/
  evals/
    datasets/
    results/
    run_eval.py
  examples/
  docs/
    prd.md
    policy_design.md
    legal_disclaimer.md
    eval_report.md
  docker-compose.yml
  pyproject.toml
```

## 16. Success criteria

MVP is successful if:

- A user can analyze an ad and landing page in under 60 seconds on a local
  Apple Silicon workstation with adequate memory.
- Output points to specific evidence strings and sources, not generic warnings.
- Health and wellness examples produce useful review flags aligned with the
  decision-support framing.
- Landing page extraction identifies visible claims and common trackers.
- Repo includes reproducible local setup with a single-command run path.
- README includes example inputs and outputs, eval status, and limitations.
- At least one external team can adopt AdLint without direct maintainer support.

## 17. Source references

- OpenAI gpt-oss-safeguard:
  https://openai.com/index/introducing-gpt-oss-safeguard/
- OpenAI gpt-oss:
  https://openai.com/index/introducing-gpt-oss/
- HHS HIPAA marketing guidance:
  https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/marketing/index.html
- HHS tracking technologies guidance:
  https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/hipaa-online-tracking/index.html
- FTC health products compliance guidance:
  https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance
- FTC Health Breach Notification Rule:
  https://www.ftc.gov/tips-advice/business-center/guidance/complying-ftcs-health-breach-notification-rule
- Washington My Health My Data Act guidance:
  https://www.atg.wa.gov/protecting-washingtonians-personal-health-data-and-privacy
- California CCPA:
  https://oag.ca.gov/privacy/ccpa
- IAB Content Taxonomy:
  https://iabtechlab.com/standards/content-taxonomy/
