# Eval Report

Status: seed eval only.

The MVP includes `evals/datasets/seed_ads.jsonl`, a 50-example curated seed set
covering health, wellness, finance, SaaS, creator disclosure, privacy, landing
page mismatch, and brand-safety scenarios.

Run:

```bash
make eval
```

Current limitations:

- The seed set is intentionally small and policy-author authored.
- It validates deterministic rule behavior, not real-world legal outcomes.
- Model-assisted classification should be benchmarked separately once a local
  model is available.
- Rewrite quality is not yet scored automatically.

Future benchmark reports should include confusion matrices, false positive and
false negative review notes, rule-only versus model-only versus hybrid
comparisons, and representative failure modes.
