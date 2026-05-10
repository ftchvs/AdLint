# AdLint v0.1.0 release notes

AdLint is an open-source, local-first preflight tool for ads, landing pages, and
growth campaigns before they hit platform review.

Think **ESLint for risky ad claims**: transparent policy-as-code checks,
evidence-backed findings, safer rewrite suggestions, and eval gates that run
locally.

## What ships in v0.1.0

- **CLI preflight**: scan JSON/YAML campaign configs and export JSON or Markdown reports.
- **Local API + Web UI**: paste ad copy, choose platform/industry/modules, and review findings locally.
- **Policy-as-code**: inspectable YAML rules for health claims, platform policies, privacy, disclosure, landing-page mismatch, and brand safety.
- **Platform modules**: initial Google, TikTok, LinkedIn, and Meta Ads heuristic coverage.
- **Evidence-based output**: every finding includes matched copy, severity, category, and a recommended action.
- **Safer rewrites**: deterministic rewrite suggestions for common high-risk or review-required findings.
- **Local-first posture**: no default raw ad persistence; optional run logging/storage are opt-in.
- **Eval gates**: seed evals, benchmark evals, real-case fixtures, policy coverage validation, and PR preflight checks.
- **Optional local AI reviewer**: Ollama-compatible model review can add decision-support metadata, but deterministic rules remain the trusted baseline.

## Demo

![AdLint Web UI review](assets/adlint-ui-review.png)

Example report output is available at:

- `docs/assets/demo/adlint-report.md`
- `docs/assets/demo/adlint-report.json`

## Honest scope

AdLint is decision-support software. It does **not** provide legal advice,
guarantee platform approval, or make definitive statutory determinations.

The Meta Ads module is intentionally framed as **initial heuristic coverage**,
not full Meta policy parity. See `docs/meta_ads_scope.md` for source references,
coverage notes, and non-goals.

## Good first contributions

- Add public-source/paraphrased eval cases.
- Add policy rules with positive and near-miss examples.
- Improve the optional local AI reviewer and measure whether it adds signal or noise.
- Add demo assets, docs, and first-run workflow polish.

## Launch positioning

Suggested announcement line:

> I open-sourced AdLint: a local-first linting tool for ads, landing pages, and
growth campaigns before they hit platform review.

Hooks:

- Runs locally; no ad copy leaves your machine by default.
- Policy-as-code + evals, not black-box compliance theater.
- CLI/API/Web UI for growth teams that want preflight feedback before launch.
