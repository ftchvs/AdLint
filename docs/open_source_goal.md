# Open-source project goal

## Working prompt

Make AdLint a legitimately useful open-source, local-first preflight tool for
growth and marketing teams before they ship ads or landing pages.

Prioritize work that makes the project more trustworthy to a stranger landing on
GitHub:

1. **Useful out of the box**: clear install path, runnable examples, CLI/API/Web
   UI workflows, and reports a marketer can understand.
2. **Evidence-backed policies**: platform, disclosure, privacy, health, finance,
   and brand-safety rules with source notes, scoped claims, and conservative
   review language.
3. **False-positive discipline**: every broad rule needs near-miss tests or eval
   rows so benign education, tooling, or planning content is not overflagged.
4. **Transparent quality gates**: benchmark, seed eval, real-case eval, policy
   coverage, and PR preflight should make regressions obvious.
5. **Local-first trust**: no default raw ad persistence, no secret data in tests,
   no live ad-account mutations, and no legal/platform approval guarantees.

## Near-term OSS roadmap

### 1. Meta Ads credibility

- Keep the Meta module framed as initial heuristic coverage, not policy parity.
- Add source-linked docs and reviewed-date notes when new Meta rules land.
- Expand from synthetic triggers to paraphrased, public-source examples where
  safe and legally usable.
- Split broad regulated-category checks into higher-precision subcases.

### 2. Contributor-friendly policy work

- Add one example, one positive eval, and one near-miss eval for each new policy.
- Prefer policy IDs that describe the review reason, not a vague platform bucket.
- Require recommended actions that tell a marketer what to change or verify.

### 3. Product relevance

- Improve first-run experience: demo configs, screenshots/GIFs, and concise
  report examples.
- Make landing-page mismatch and disclosure checks easy to demo in the CLI and
  Web UI.
- Keep README language practical: who uses this, what it catches, what it does
  not promise.

### 4. Research/eval credibility

- Treat synthetic benchmarks as regression tests, not accuracy claims.
- Keep adding real-case/adjudicated datasets without private data.
- Track false positives and false negatives explicitly in CI-facing checks.

## Definition of solid

AdLint is “solid OSS” when a new contributor can clone it, run examples, trust
its privacy posture, understand policy scope, add a rule with tests, and see CI
catch both missed risky cases and noisy overtriggering.
