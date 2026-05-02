# AdLint PRD

Version: 0.3 review draft
Product: Open-source ad compliance and brand-safety preflight for growth teams
Tagline: Preflight risk checks for ads, landing pages, and growth campaigns
before launch.
Status: MVP implemented for local CLI/API use; roadmap items are separated
from the shipped review target below.

## 1. Summary

AdLint helps growth teams, founders, agencies, and builders review ads and
landing pages before launch. It flags risky claims, missing disclosures,
platform-policy concerns, health/privacy review triggers, landing-page
mismatches, and brand-safety risks.

AdLint is decision-support software. It must not claim that an ad is legally
compliant or guaranteed to pass platform review. It classifies creative as
`approved`, `needs_review`, or `high_risk`, then explains the decision with
specific evidence and safer rewrite suggestions.

The current MVP is local-first and policy-as-code-first. It runs as a Python
package with a CLI, FastAPI service, importable analysis engine, YAML policy
files, deterministic rules, transparent scoring, reports, rewrites, seed
evals, documentation, and opt-in run logging.

## 2. Current status

### 2.1 Implemented MVP

The review target includes:

- CLI: `adlint scan <config>` accepts JSON or YAML ad configs, prints JSON or
  Markdown, can load custom policy paths, and can write reports to disk.
- API: FastAPI exposes `/health`, `/analyze`, and `/eval`.
- Library mode: callers can import `adlint.engine.analyze`.
- YAML policies: built-in policy files live in `adlint/policies/`, and users
  can load policy files or directories at runtime.
- Policy filtering: policies can be filtered by module, platform, and industry.
- Deterministic rules: signal matching, negation handling, landing-page offer
  mismatch checks, and health-adjacent tracking-pixel review flags are
  implemented.
- Scoring: risk scores and decisions are computed with transparent severity,
  evidence, regulated-industry, landing-page, privacy, and brand-safety weights.
- Reports: JSON and Markdown reports include policy hits, evidence,
  recommended actions, rewrites, landing-page details, and the decision-support
  disclaimer.
- Rewrites: deterministic safer rewrite suggestions are generated for high-risk
  or review-required hits where feasible.
- Seed evals: `evals/run_eval.py` scores the 50-example
  `evals/datasets/seed_ads.jsonl` dataset.
- Docs: setup, policy design, local model notes, eval status, and legal
  boundary docs exist in the repo.
- Opt-in logging: `logging_enabled` and `log_path` write JSONL run logs only
  when explicitly enabled.

### 2.2 Partial or future work

The following are not part of the implemented MVP review target:

- Web UI for pasting copy, selecting settings, and browsing reports.
- A 200-500 example benchmark with confusion matrices and reviewed failure
  modes.
- `scoring.yml` configurability for thresholds and weights.
- SQLite storage for eval datasets, run metadata, or anonymized logs.
- Playwright or `trafilatura` extraction. The MVP uses a standard-library HTML
  parser and robots-aware URL fetching.
- Verified live Ollama model runs. Optional Ollama integration exists, but the
  MVP does not yet claim benchmarked local model quality.
- Fine-tuning or adapter training.

## 3. Problem

Growth teams ship creative quickly, but compliance and brand risk often appear
late: during ad-platform review, after account-quality issues, during legal
review, or after a landing page has already collected traffic.

This risk is highest in health, wellness, finance, privacy-sensitive,
employment, housing, credit, and creator campaigns. Teams may need to reason
about unsupported claims, missing disclosures, sensitive targeting,
landing-page mismatch, health-data tracking, and unsafe content adjacency.

Most existing tools are opaque, enterprise-priced, or disconnected from daily
creative workflows. AdLint provides an open-source, explainable, local-first
alternative for preflight review.

## 4. Target users

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

## 5. Core value proposition

AdLint analyzes ad copy, optional landing-page content, and campaign metadata,
then returns:

- Decision: `approved`, `needs_review`, or `high_risk`.
- Numeric risk score.
- Enabled policy modules.
- Policy categories triggered.
- Exact evidence from the ad or page.
- Required or recommended mitigation steps.
- Safer rewrites that preserve campaign intent while lowering risk.
- Machine-readable JSON report.
- Human-readable Markdown report.
- Landing-page extraction details and fetch errors when relevant.
- Model status when optional Ollama classification is enabled.

## 6. Product principles

- Policy-as-code first: policies live in version-controlled YAML with clear
  IDs, severities, categories, signals, prompts, recommended actions, module
  filters, and optional taxonomy mappings.
- Explainable by default: every decision traces back to policy IDs, evidence
  strings, sources, severities, and recommended actions.
- Local-first: the MVP runs locally without hosted services. Optional local
  model calls use an Ollama-compatible endpoint.
- Privacy-conscious: raw submissions are not persisted by default. Health and
  privacy findings are labeled `requires_review`, not definitive legal
  violations.
- Composable: CLI, API, and library modes are first-class so teams can plug
  AdLint into CI, internal tools, and future UIs.

## 7. Implemented MVP scope

The MVP focuses on high-signal checks for health, wellness, finance, SaaS,
creator disclosure, privacy, landing-page mismatch, and brand-safety scenarios.

### 7.1 Ad claim risk

AdLint detects unsupported, absolute, or extreme claims, including:

- Guaranteed outcomes.
- "Clinically proven" or "doctor recommended" language without substantiation.
- Weight-loss, body-image, medical, income, or performance promises.
- Before/after claims.
- Fake urgency or scarcity.
- Absolute claims like "risk-free," "cure," "guaranteed," or "instant."

### 7.2 Platform policy risk

Implemented platform modules:

- Google Ads: health, misrepresentation, restricted-category, and disclosure
  risk.
- TikTok Ads: misleading content, weight-management claims, and disclosure risk.
- LinkedIn Ads: sensitive targeting, discrimination, and professional claims.

Meta remains a future platform module.

### 7.3 Health privacy risk

AdLint flags health or wellness landing pages that may require review because
they combine sensitive health context with tracking pixels, forms, conversion
events, or unclear consent paths.

Implemented health/privacy modules include:

- HIPAA marketing review triggers for covered-entity or business-associate
  contexts.
- Health landing page plus tracking-pixel risk.
- FTC Health Breach Notification Rule indicators for health apps and connected
  devices.
- Washington My Health My Data Act indicators.
- California CCPA sensitive health-data indicators.

All HIPAA/privacy findings must be marked as `requires_review`, not definitive
legal violations.

### 7.4 Brand safety and suitability

AdLint classifies campaign and page context using IAB-style sensitive-topic
categories:

- Adult content.
- Violence.
- Tragedy or conflict.
- Politics.
- Misinformation.
- Sensitive social issues.
- Unsafe or controversial content.

Policy IDs can include IAB Content Taxonomy 2.2 mappings and suitability levels
such as `low`, `medium`, `high`, and `floor`.

### 7.5 Landing-page extraction

The current extractor accepts either `landing_page_html` or a URL. For URLs it
uses robots-aware standard-library fetching for HTML pages. It extracts:

- Page title.
- Headings.
- Visible claim-like text.
- Form labels and inputs.
- Pricing-related text.
- Disclaimer-like text.
- Common tracking scripts.
- Fetch errors.

JavaScript rendering, richer content extraction, and `trafilatura` fallback are
future work.

### 7.6 Rewrite assistant

For high-risk or review-required policy hits where a rewrite is feasible,
AdLint suggests safer alternatives that preserve campaign intent while lowering
risk.

Examples:

- Replace guaranteed outcomes with qualified claims.
- Add "individual results vary" where appropriate.
- Remove unsupported medical language.
- Suggest a softer CTA.
- Add disclosure reminders for sponsored or affiliate content.
- Ask users to review privacy and consent details before continuing.

## 8. Non-goals

The MVP will not:

- Guarantee platform approval.
- Provide legal advice.
- Replace legal or compliance teams.
- Store PHI or user-level customer data by default.
- Auto-submit ads to platforms.
- Make live changes in ad accounts.
- Make definitive HIPAA or statutory violation determinations.
- Claim verified local model quality before live Ollama runs are benchmarked.
- Fine-tune a model before enough labeled data exists.

Fine-tuning should be considered only after a useful labeled dataset exists and
benchmarks show a clear improvement over prompted baselines.

## 9. Example input and output

### 9.1 High-risk example

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

Representative output shape:

```json
{
  "decision": "high_risk",
  "risk_score": 0.9,
  "policy_hits": [
    {
      "policy_id": "unsupported_health_claim",
      "severity": "high",
      "category": "health_claims",
      "evidence": [
        {
          "text": "Our clinically proven supplement melts fat fast. Try it risk-free today.",
          "source": "body"
        }
      ],
      "recommended_action": "Remove or qualify the claim and provide substantiation."
    },
    {
      "policy_id": "weight_loss_claim",
      "severity": "high",
      "category": "health_claims",
      "evidence": [
        {
          "text": "Lose 20 pounds in 30 days guaranteed",
          "source": "headline"
        }
      ],
      "recommended_action": "Avoid absolute body or fat-loss language and route for review."
    }
  ],
  "requires_review": true,
  "recommended_actions": [
    "Remove or qualify the claim and provide substantiation."
  ],
  "safer_rewrites": [
    {
      "headline": "Support your wellness routine with daily nutrition",
      "body": "Designed to complement healthy habits. Individual results vary.",
      "cta": "Learn more"
    }
  ],
  "logging_enabled": false
}
```

### 9.2 Borderline needs-review example

Input:

```json
{
  "platform": "google",
  "country": "US",
  "industry": "wellness",
  "headline": "A calmer routine for better sleep",
  "body": "Join our wellness newsletter for science-backed sleep tips.",
  "cta": "Sign up",
  "landing_page_html": "<html><script src=\"https://connect.facebook.net/en_US/fbevents.js\"></script><body><h1>Sleep tips</h1><form><label>Email signup</label></form></body></html>"
}
```

Representative output shape:

```json
{
  "decision": "needs_review",
  "risk_score": 0.66,
  "policy_hits": [
    {
      "policy_id": "wellness_claim_review",
      "severity": "medium",
      "category": "health_claims",
      "evidence": [
        {
          "text": "Join our wellness newsletter for science-backed sleep tips.",
          "source": "body"
        }
      ],
      "recommended_action": "Clarify what evidence supports the wellness claim."
    },
    {
      "policy_id": "tracking_pixel_risk",
      "severity": "medium",
      "category": "privacy",
      "evidence": [
        {
          "text": "Meta Pixel",
          "source": "landing_page_tracker_1"
        }
      ],
      "recommended_action": "Review consent, tracking, disclosure, and data-sharing paths.",
      "requires_review": true
    }
  ],
  "requires_review": true,
  "safer_rewrites": [
    {
      "headline": "A calmer routine for better sleep",
      "body": "Review how your information is used, including consent choices and privacy details, before continuing.",
      "cta": "Review details"
    }
  ],
  "logging_enabled": false
}
```

## 10. Functional requirements

| ID | Status | Requirement and current behavior |
| --- | --- | --- |
| FR-1 | Implemented | Users can submit ad copy with headline, body, and CTA through CLI, API, or the Python engine. |
| FR-2 | Implemented | Users can provide an optional `landing_page_url` or `landing_page_html`. |
| FR-3 | Partial | The system extracts title, headings, visible claims, forms, pricing text, disclaimers, and trackers from static HTML. JavaScript rendering and richer extraction are future work. |
| FR-4 | Implemented | Users can select `google`, `tiktok`, or `linkedin` policy behavior through platform metadata. Meta is future work. |
| FR-5 | Implemented | Users can select industries such as `health`, `wellness`, `finance`, `saas`, `creator`, or `general`. |
| FR-6 | Implemented | Deterministic rule checks run first using policy signals, regexes, keyword patterns, and heuristics. |
| FR-7 | Partial | Optional Ollama classification exists behind `model_enabled` or `--enable-model`; live model quality is not yet verified. |
| FR-8 | Implemented | The system returns structured JSON and can generate Markdown reports. HTML reports are future work. |
| FR-9 | Implemented | The system maps risky phrases to policy IDs, categories, severities, sources, and recommended actions. |
| FR-10 | Implemented | The system suggests deterministic safer rewrites for high-risk or review-required hits where feasible. |
| FR-11 | Implemented | The system supports custom YAML policy files loaded from built-in policies or configured paths. |
| FR-12 | Implemented | The repo includes a seed eval runner and 50 labeled examples. |
| FR-13 | Partial | The system can call an Ollama-compatible local model, but verified live model runs and benchmarks remain future work. |
| FR-14 | Implemented | Raw submissions are not persisted by default; users can enable JSONL logging for evaluation. |
| FR-15 | Implemented | HIPAA and privacy flags are labeled `requires_review`, not definitive violations. |
| FR-16 | Implemented | Users can enable or disable policy modules through `policy_modules`. |
| FR-17 | Implemented | `make dev`, `make scan`, `make api`, `make eval`, and `make test` provide local run paths. |
| FR-18 | Future | A Web UI will let users paste copy, select settings, and browse/export reports. |
| FR-19 | Future | `scoring.yml` will let teams tune thresholds and weights without code changes. |
| FR-20 | Future | SQLite storage may support eval datasets, run metadata, and anonymized logs. |

## 11. Policy modules

Current policy files:

```text
adlint/policies/
  brand_custom_template.yml
  brand_safety_iab.yml
  ftc_health_claims.yml
  platform_google_ads.yml
  platform_linkedin_ads.yml
  platform_tiktok_ads.yml
  privacy_consumer_health_data.yml
  privacy_hipaa_marketing.yml
  privacy_tracking_pixels.yml
```

Policy file shape:

```yaml
policies:
  - id: unsupported_health_claim
    severity: high
    category: health_claims
    description: Health or wellness claim likely requiring substantiation.
    modules:
      - health_claims
    platforms:
      - google
      - tiktok
      - linkedin
    industries:
      - health
      - wellness
    signals:
      - guaranteed
      - clinically proven
      - cure
      - lose * pounds
    model_prompt: >
      Determine whether this ad makes a health-related claim that would likely
      require substantiation or compliance review under health marketing rules.
    recommended_action: Remove or qualify the claim and provide substantiation.
    rewrite_strategy: qualify_claim
    requires_review: true
```

Policy entries can include optional brand-safety or suitability taxonomy
mappings where useful:

```yaml
iab_taxonomy:
  content_taxonomy_version: "2.2"
  sensitive_topic: "health"
  suitability_level: medium
```

## 12. Technical architecture

Implemented MVP stack:

- Package: Python package `adlint`.
- CLI: `argparse` command exposed as `adlint`.
- API: FastAPI app with `/health`, `/analyze`, and `/eval`.
- Config: JSON or YAML ad configs plus YAML policy files.
- Policy engine: built-in policies loaded with `importlib.resources`, plus
  custom policy paths.
- Rules: deterministic signal matching, derived landing-page mismatch, and
  derived privacy-tracker checks.
- Landing-page extraction: standard-library URL fetching, robots checks, and
  `HTMLParser` extraction.
- Optional model runtime: Ollama-compatible `/api/generate` calls.
- Scoring: code-defined severity and context weights.
- Output: JSON result objects and Markdown reports.
- Logging: opt-in JSONL run logs.
- Evaluation: seed JSONL dataset and metrics runner.

Roadmap architecture:

- Frontend: lightweight Web UI.
- Scraping: Playwright for JavaScript-enabled pages, with `trafilatura` as a
  static extraction fallback.
- Storage: SQLite for eval datasets, run metadata, and optional anonymized logs.
- Config: future `scoring.yml` for threshold and weight calibration.
- Model validation: verified local Ollama runs with benchmarked rule-only,
  model-only, and hybrid comparisons.

Processing pipeline:

```text
Input (ad + metadata)
  -> Normalize ad and page data
  -> Landing page fetch or HTML parsing
  -> Tracker and pixel detection
  -> Rule-based checks
  -> Optional local model classifier
  -> Risk scoring
  -> Rewrite generation
  -> JSON and Markdown report
  -> Optional JSONL run log
```

## 13. Risk scoring

MVP scoring is simple and transparent:

```text
risk_score =
  max_policy_severity_weight
  + evidence_count_weight
  + regulated_category_weight
  + landing_page_mismatch_weight
  + privacy_tracking_weight
  + brand_safety_weight
```

Current severity weights:

```text
low = 0.2
medium = 0.4
high = 0.7
critical = 0.9
```

Current decision thresholds:

```text
0.00 - 0.34 = approved
0.35 - 0.69 = needs_review
0.70 - 1.00 = high_risk
```

If the highest severity is below `high`, the MVP caps the score at `0.69` so
medium-only findings stay in `needs_review`. Thresholds and weights should
move to a future `scoring.yml` file so teams can calibrate sensitivity by use
case. High-severity health, privacy, and safety categories should favor recall
over precision.

## 14. Evaluation plan

### 14.1 Implemented seed eval

The repo includes a 50-example seed dataset at
`evals/datasets/seed_ads.jsonl`. It covers health, wellness, finance, SaaS,
creator disclosure, privacy, landing-page mismatch, and brand-safety scenarios.

Run:

```bash
make eval
```

The current eval runner reports:

- Total examples.
- Decision accuracy.
- Misses by expected decision.
- Per-policy precision and recall.
- Per-row policy true positives, false negatives, and false positives.

### 14.2 Future benchmark

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

Future benchmark reports should include:

- Accuracy for overall decision.
- Precision by policy category.
- Recall by policy category, with emphasis on high-severity health, privacy,
  and safety categories.
- False positive rate.
- Manually reviewed false negatives.
- Rule-only versus model-only versus hybrid comparisons.
- Rewrite quality review for clarity, risk reduction, and intent preservation.
- Representative examples and known failure modes.

## 15. Phase plan

### Phase 1: Core engine MVP - implemented

- Python package structure.
- `adlint scan <config>` CLI command.
- FastAPI `/analyze` and `/eval` endpoints.
- Policy YAML loader.
- Deterministic rule engine.
- Optional Ollama-compatible model calls.
- Risk scoring.
- JSON and Markdown reports.
- Deterministic safer rewrites.
- 50 curated seed eval examples.
- Documentation and legal boundary notes.
- Opt-in JSONL logging.

### Phase 2: Review hardening - current

- Keep README and PRD aligned with the actual MVP.
- Validate local install, tests, CLI examples, API examples, and eval command.
- Preserve the decision-support and legal-boundary language throughout docs.
- Avoid claiming live model quality, production storage, or Web UI behavior.

### Phase 3: Web UI

- Paste ad copy and metadata.
- Add landing page URL or HTML.
- Select platform, industry, and policy modules.
- View detailed report and rewrites.
- Export Markdown and JSON.
- Copy safer rewrites.

### Phase 4: Evals and benchmark

- 200-500 labeled examples.
- Confusion matrix.
- False positive and false negative review notes.
- Rule-only vs. model-only vs. hybrid comparison.
- Public benchmark report in `docs/eval_report.md`.

### Phase 5: Optional model validation and fine-tuning

- Verify live Ollama model runs on supported local models.
- Compare model-assisted classification against deterministic rules.
- Consider LoRA or adapter-based classifier training only after benchmark
  evidence shows a clear need.
- Publish an adapter and model card only if quality improves.

## 16. Suggested repository structure

Current repository structure:

```text
AdLint/
  README.md
  PRD.md
  Makefile
  api/
    main.py
  adlint/
    classifiers/
    policies/
    rewrites/
    rules/
    scoring/
    scrapers/
    api.py
    audit_log.py
    cli.py
    config.py
    engine.py
    models.py
    policy.py
    reports.py
  docs/
    eval_report.md
    legal_disclaimer.md
    local_models.md
    policy_design.md
  evals/
    datasets/
    run_eval.py
  examples/
  tests/
  docker-compose.yml
  pyproject.toml
```

Future directories may include Web UI code, SQLite-backed storage migrations,
and persisted eval results.

## 17. Success criteria

### 17.1 MVP review criteria

The MVP is ready for review if:

- A user can run the CLI against example configs.
- The API can analyze payloads and score eval examples.
- Output points to specific evidence strings and sources, not generic warnings.
- Health and wellness examples produce useful review flags aligned with the
  decision-support framing.
- Privacy and HIPAA-related outputs use `requires_review` language rather than
  definitive violation language.
- Landing-page extraction identifies static visible claims and common trackers.
- Reports include JSON, Markdown, rewrites, and the legal disclaimer.
- Raw submissions are not logged unless `logging_enabled` is true.
- Seed evals and tests are reproducible from documented commands.

### 17.2 Longer-term success criteria

AdLint becomes successful beyond the MVP if:

- A user can analyze an ad and landing page in under 60 seconds on a local
  Apple Silicon workstation with adequate memory.
- The Web UI makes the main review workflow accessible to non-engineers.
- A 200-500 example benchmark shows stable recall for high-severity health,
  privacy, and safety categories.
- Teams can tune scoring with `scoring.yml` without editing code.
- Local model use is benchmarked and documented with clear limitations.
- At least one external team can adopt AdLint without direct maintainer support.

## 18. Source references

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
