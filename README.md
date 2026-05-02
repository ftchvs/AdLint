# AdLint

**Local-first preflight risk checks for ads, landing pages, and growth
campaigns before launch.**

AdLint is a runnable Python CLI/API MVP for deterministic ad policy,
brand-safety, privacy, and disclosure checks. It reviews ad copy and optional
landing-page content, then returns an explainable decision, risk score,
evidence, recommended actions, and safer rewrite suggestions.

AdLint is decision-support software, not legal advice. It does not guarantee
platform approval or make definitive statutory violation determinations.

## What runs today

- Python package with the `adlint scan` CLI.
- FastAPI app with `GET /health`, `GET /models`, `POST /analyze`, and
  `POST /eval`.
- One-page Web UI at `/ui/` for the main local review workflow, including
  model selection and a Local model toggle that defaults on.
- YAML policy files under `adlint/policies/`, plus custom policy paths.
- Deterministic rule engine with policy-module, platform, and industry filters.
- Transparent score thresholds for `approved`, `needs_review`, and `high_risk`.
- JSON stdout, Markdown stdout, and paired JSON/Markdown report files.
- Safer rewrite suggestions for high-risk and review-required findings.
- Opt-in JSONL run logging for local evaluation workflows.
- Seed, benchmark, and public-source real-case eval runners.
- Tests covering the CLI, API, policy loading, reports, documented examples,
  eval runner, and opt-in logging behavior.
- Makefile and Docker Compose paths for local development.

## Not in this MVP yet

- A statistically reliable real-case benchmark; the current public-source set
  is diagnostic and intentionally small.
- `scoring.yml` configurability; scoring weights currently live in Python.
- SQLite or other durable storage; raw submissions are not persisted by
  default.
- Playwright or trafilatura extraction. The current landing-page extractor is
  a small stdlib HTML parser that can read inline HTML, local files, or
  fetchable HTML URLs.
- Verified live Ollama model quality or fine-tuning. Local model support is
  available for decision support, but deterministic rules are the baseline.

## Quick start

Requirements: Python 3.11 or newer. Docker is optional.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
adlint scan examples/high_risk_tiktok_health.json --output-dir reports
```

Without activating the virtual environment:

```bash
.venv/bin/python -m adlint scan examples/high_risk_tiktok_health.json \
  --format markdown
```

Makefile shortcuts:

```bash
make dev   # install and run the high-risk example, writing reports/
make scan  # install and run the wellness example
make api   # start uvicorn with adlint.api:app
make eval  # run the seed evals and write evals/results/latest.json
make benchmark    # run the 200-row synthetic policy regression benchmark
make real-cases   # run sourced public-case diagnostics
make test  # run pytest
```

Docker Compose runs the bundled scan example and writes reports:

```bash
docker compose up
```

## CLI

```bash
adlint scan <config>
```

`<config>` can be JSON or YAML. Supported options:

- `--format json|markdown` controls stdout output. The default is JSON.
- `--output-dir <dir>` writes `adlint-report.json` and `adlint-report.md`.
- `--policy-path <path>` loads a policy YAML file or directory. Pass it more
  than once to combine paths.
- `--enable-model` calls the local Ollama-compatible classifier in addition to
  deterministic rules.
- `--ollama-model <name>` overrides `ADLINT_OLLAMA_MODEL`.

Example config:

```json
{
  "platform": "tiktok",
  "country": "US",
  "industry": "health",
  "headline": "Lose 20 pounds in 30 days guaranteed",
  "body": "Our clinically proven supplement melts fat fast.",
  "cta": "Buy now",
  "landing_page_html": "<html><body><h1>Fast results</h1></body></html>",
  "policy_modules": ["health_claims", "platform", "privacy"]
}
```

Optional input fields include `target_age_range`, `landing_page_url`,
`model_enabled`, `ollama_model`, `logging_enabled`, and `log_path`.

## API

Start the API:

```bash
make api
```

Open the local UI:

```text
http://127.0.0.1:8000/ui/
```

Endpoints:

- `GET /health` returns service status.
- `GET /models` returns local model configuration and available model choices
  for the Web UI.
- `POST /analyze` accepts the same payload shape as the CLI config and returns
  the full analysis result.
- `POST /eval` accepts `{"examples": [...]}` where each example can include an
  `input` object and optional `expected_decision`.

The Web UI sends `model_enabled: true` by default unless the user turns off the
Local model toggle. It also sends `ollama_model` when a specific model is
selected. API callers can omit `model_enabled` or set it to `false` for a
rule-only run, or set `ollama_model` to override `ADLINT_OLLAMA_MODEL` for that
request.

Minimal request:

```bash
curl -s http://127.0.0.1:8000/analyze \
  -H 'content-type: application/json' \
  -d '{
    "platform": "google",
    "industry": "wellness",
    "headline": "A calmer routine for better sleep",
    "body": "Join our wellness newsletter for science-backed tips.",
    "cta": "Sign up"
  }'
```

## Output

Analysis results include:

- `decision`: `approved`, `needs_review`, or `high_risk`.
- `risk_score`: numeric score from `0.0` to `1.0`.
- `policy_hits`: policy IDs, severity, category, evidence, and actions.
- `requires_review`: true when a finding or score needs human review.
- `recommended_actions`: de-duplicated action list.
- `safer_rewrites`: deterministic rewrite suggestions.
- `landing_page`: extracted title, headings, claims, forms, pricing,
  disclaimers, trackers, or fetch errors.
- `enabled_modules`, `model`, `logging_enabled`, and optional `reports`.

Report files use fixed names:

```text
adlint-report.json
adlint-report.md
```

## Policies

Bundled policies live in `adlint/policies/`:

- `ftc_health_claims.yml`
- `platform_google_ads.yml`
- `platform_tiktok_ads.yml`
- `platform_linkedin_ads.yml`
- `privacy_hipaa_marketing.yml`
- `privacy_tracking_pixels.yml`
- `privacy_consumer_health_data.yml`
- `brand_safety_iab.yml`
- `brand_custom_template.yml`

Default modules are `health_claims`, `platform`, `privacy`, `brand_safety`,
`disclosure`, and `landing_page`. Pass `policy_modules` in a config to narrow
the rule surface.

Policy files use a top-level `policies` list:

```yaml
policies:
  - id: unsupported_health_claim
    severity: high
    category: health_claims
    description: Health or wellness claim likely requiring substantiation.
    modules: [health_claims]
    industries: [health, wellness]
    signals:
      - clinically proven
      - medical breakthrough
    recommended_action: Remove or qualify the claim and provide substantiation.
    requires_review: true
    rewrite_strategy: qualify_claim
```

## Evals and logging

Run the seed evals:

```bash
make eval
```

The seed dataset has 50 examples across health, wellness, finance, SaaS,
creator disclosure, privacy, landing-page mismatch, and brand-safety cases. It
is a development sanity check, not a production benchmark.

Run the larger deterministic benchmark:

```bash
make benchmark
```

Run the public-source real-case diagnostics:

```bash
make real-cases
```

`real_cases_v1` contains 13 paraphrased, source-backed rows from public FTC,
ASA/CAP, and DOJ/HUD-style cases. It is intentionally diagnostic: all current
rows are high-risk, so decision accuracy is not a reliability estimate. Use the
policy false-positive and false-negative notes to decide what rules, labels, or
model-rescue behavior to improve next.

Raw submissions are not persisted by default. To opt into JSONL logging, set:

```json
{
  "logging_enabled": true,
  "log_path": "logs/adlint-runs.jsonl"
}
```

## Local model hook

AdLint uses hybrid analysis when local model review is enabled: deterministic
rules always run, and the local Ollama-compatible model adds decision-support
metadata. The Web UI enables this by default; CLI users can pass
`--enable-model`, and API callers can set `model_enabled: true`.

```bash
ollama pull gpt-oss-safeguard:20b
ADLINT_OLLAMA_MODEL=gpt-oss-safeguard:20b \
  adlint scan examples/high_risk_tiktok_health.json --enable-model
```

The default Ollama endpoint is `http://localhost:11434/api/chat`. Set
`ADLINT_OLLAMA_URL` to point AdLint at a different Ollama-compatible chat
endpoint.

If the model endpoint is unavailable, AdLint still returns rule-based findings
and marks the model status as `unavailable`.

## Related docs

- `docs/policy_design.md`
- `docs/legal_disclaimer.md`
- `docs/local_models.md`
- `docs/eval_report.md`
- `docs/research_paper.md`
- `docs/adlint_hybrid_eval_paper.tex`

## Non-goals

AdLint does not aim to:

- Guarantee platform approval.
- Provide legal advice or replace counsel.
- Make definitive HIPAA, FTC, state privacy, or other statutory findings.
- Store PHI or user-level customer data by default.
- Submit ads to platforms or mutate live ad accounts.
- Fine-tune models before stronger eval evidence exists.

## References

- [OpenAI gpt-oss-safeguard](https://openai.com/index/introducing-gpt-oss-safeguard/)
- [OpenAI gpt-oss](https://openai.com/index/introducing-gpt-oss/)
- [HHS tracking technologies guidance](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/hipaa-online-tracking/index.html)
- [FTC health products compliance guidance](https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance)
- [FTC Health Breach Notification Rule](https://www.ftc.gov/tips-advice/business-center/guidance/complying-ftcs-health-breach-notification-rule)
- [Washington My Health My Data Act guidance](https://www.atg.wa.gov/protecting-washingtonians-personal-health-data-and-privacy)
- [California CCPA](https://oag.ca.gov/privacy/ccpa)
- [IAB Content Taxonomy](https://iabtechlab.com/standards/content-taxonomy/)
