# Announcement draft

## Short post

I open-sourced **AdLint** — a local-first linting tool for ads, landing pages,
and growth campaigns before they hit platform review.

Think ESLint, but for risky ad claims:

- Flags unsupported health/finance claims, disclosure gaps, platform-policy review triggers, landing-page mismatch, privacy-sensitive tracking, and brand-safety concerns.
- Runs locally through a CLI, FastAPI service, or small Web UI.
- Uses transparent YAML policy rules and eval gates instead of black-box compliance theater.
- Keeps raw ad copy out of storage by default.
- Includes initial Google, TikTok, LinkedIn, and Meta Ads heuristic modules.

It is not legal advice and it does not guarantee platform approval. The goal is
simple: give growth teams earlier, explainable feedback before campaign review
becomes expensive.

Repo: https://github.com/ftchvs/AdLint

## Longer post

Growth teams usually find ad risk late — during platform review, legal review,
or after a landing page is already collecting traffic.

I wanted a lightweight preflight step that works like developer tooling:
transparent, local, scriptable, and easy to extend.

So I open-sourced **AdLint**.

AdLint scans draft ad copy and optional landing-page context, then returns:

- `approved`, `needs_review`, or `high_risk`
- exact matched evidence
- policy categories and severity
- recommended actions
- safer rewrite options
- JSON/Markdown reports

The project is intentionally local-first. The rule engine is deterministic and
policy-as-code-first. There is also an optional Ollama-compatible local model
reviewer, but the baseline does not depend on hosted models.

What is in the first OSS release:

- CLI, API, and Web UI
- policy YAML files
- initial platform modules for Google, TikTok, LinkedIn, and Meta Ads
- privacy/disclosure/landing-page/brand-safety checks
- seed evals, benchmark evals, real-case fixtures, and policy coverage gates

What it does *not* claim:

- legal advice
- definitive compliance decisions
- guaranteed platform approval
- complete Meta/Google/TikTok/LinkedIn policy parity

If you work on growth, regulated campaigns, creator ads, landing pages, or local
AI/product tooling, I’d love feedback and contributions.

Repo: https://github.com/ftchvs/AdLint

## Product Hunt / Hacker News style blurb

AdLint is a local-first ad preflight tool for growth teams. It scans draft ad
copy and landing-page context for risky claims, disclosure gaps, platform-policy
review triggers, privacy-sensitive tracking, and brand-safety concerns. It ships
with CLI/API/Web UI workflows, transparent YAML policy rules, eval gates, and an
optional local AI reviewer.
