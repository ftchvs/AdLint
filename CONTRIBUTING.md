# Contributing to AdLint

Thanks for helping improve AdLint. The project is local-first decision-support software for preflight ad, landing-page, brand-safety, privacy, and disclosure checks. The current OSS project goal is documented in `docs/open_source_goal.md`.

## Good first contributions

Good first issues usually fall into one of these buckets:

- Add or improve a policy YAML rule with clear evidence and recommended action.
- Add an example ad config under `examples/`.
- Add or improve eval rows in `evals/datasets/`.
- Improve README, docs, or legal-boundary language.
- Add tests for a policy edge case.

## Development setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
make test
```

Useful checks:

```bash
make eval
make benchmark
make real-cases-ci
make real-world-blind-ci
make policy-coverage-validate
make rewrite-quality
```

Before opening eval or policy PRs, run:

```bash
make pr-preflight
```

## Policy contribution guidelines

Policies should be explainable and conservative:

- Include a stable `id`.
- Set severity intentionally: `low`, `medium`, `high`, or `critical`.
- Prefer specific signals over broad words that create false positives.
- Include `recommended_action` so users know how to lower risk.
- Use `requires_review: true` for sensitive legal/privacy/platform concerns instead of pretending AdLint can make definitive legal decisions.
- Add tests or eval rows for the expected behavior.

Example:

```yaml
policies:
  - id: unsupported_health_claim
    severity: high
    category: health_claims
    modules: [health_claims]
    industries: [health, wellness]
    signals:
      - clinically proven
      - medical breakthrough
    recommended_action: Remove or qualify the claim and provide substantiation.
    requires_review: true
```

## Privacy and safety boundaries

AdLint should remain privacy-conscious:

- Do not add raw submission persistence by default.
- Do not include real private customer data in tests, examples, evals, screenshots, or docs.
- Do not claim legal compliance, guaranteed platform approval, or definitive statutory determinations.
- Keep local model features as decision support unless benchmarked evidence proves otherwise.

## Accessibility expectations

- Keep CLI output understandable without color alone.
- Preserve JSON output for users who need structured or automated review.
- Label Web UI form controls and keep keyboard focus visible.
- Do not communicate severity, status, or risk only through color.
- Add useful alt text for screenshots and diagrams.

## Pull request checklist

- [ ] I ran relevant tests or documented why not.
- [ ] I added/updated tests or eval rows for behavior changes.
- [ ] I preserved decision-support and legal-boundary language.
- [ ] I avoided adding private data, secrets, or raw real ad submissions.
- [ ] I checked relevant accessibility expectations from [ACCESSIBILITY.md](ACCESSIBILITY.md).
- [ ] I updated docs if the user-facing behavior changed.
