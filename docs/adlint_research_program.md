# AdLint research program

This document is the working contract for research-loop experiments in this
repo. The goal is to make eval-driven improvements reproducible without
tuning labels, protected source rows, or legal text just to improve metrics.

## Experiment loop

1. Start with a run tag and a short hypothesis.

   ```bash
   .venv/bin/python evals/research_loop.py start \
     --tag research-example \
     --description "Test one narrow blind-holdout miss cluster." \
     --dry-run
   ```

2. Capture the deterministic baseline before changing behavior.

   ```bash
   make research-summary
   ```

3. Edit only the allowed research surfaces for the current slice.
4. Run the same summary and any relevant validators again.
5. Keep the experiment only when the change improves the target miss cluster
   without benchmark, real-case, blind-holdout, privacy, or legal regressions.
6. Discard the experiment when it edits protected data, weakens a validator,
   worsens a baseline, or only improves metrics by changing labels.

The runner writes JSONL records under `logs/research_loop/`, which is ignored
by Git. Use those logs as local evidence, not as product artifacts.
When you have separate post-change commands, pass them with
`--candidate-command name::command` so the runner records deterministic metric
deltas against the captured baselines.

## Allowed edit surfaces

The research-loop infrastructure slice may edit:

- `Makefile`
- `docs/adlint_research_program.md`
- `docs/research_loop.md`
- `evals/research_loop.py`
- `evals/run_eval.py`
- `tests/test_eval_runner.py`
- `tests/test_research_loop.py`

`docs/eval_report.md` and `evals/README.md` are allowed only when the change is
documentation for this research loop. Product runtime paths such as `adlint/`,
`api/`, and `examples/` are outside this slice unless a later Linear issue
explicitly assigns them.

## Protected file sets

Do not change these inside a research-loop experiment:

- `evals/datasets/*.jsonl`
- `evals/generate_*dataset.py`
- `evals/validate_real_cases.py`
- `evals/preflight_eval_assets.py`
- `evals/real_cases.md`
- `docs/legal_disclaimer.md`

These files protect source-backed labels, generated benchmark contracts,
validators, and legal guardrails. If a protected row appears wrong, open a
follow-up with source evidence and reviewer notes. Do not relabel it inside a
metric-improvement experiment.

Raw public-source material must stay out of the repo unless it has already
been paraphrased into an accepted local dataset row. Do not commit screenshots,
account IDs, targeting details, live landing-page URLs, or copied ad creative
used only for research triage.

## Baseline commands

Use the fast baseline summary across the seed set, deterministic benchmark,
real cases, and blind holdout:

```bash
make research-summary
```

For source-backed dataset integrity, run:

```bash
make pr-preflight
make real-cases-validate
make real-world-blind-validate
```

The compact eval summary is JSON with a stable schema:

- `dataset`, `mode`, `total_rows`, `scored_rows`, and `skipped_rows`
- `decision_accuracy`
- `decision_mismatch_count`
- `confusion_matrix_deltas`
- `policy_false_positive_count` and `policy_false_negative_count`
- `top_review_note_row_ids`
- `model_status_counts`
- `elapsed_seconds`

The elapsed value is expected to vary; the field names and nested structure
must remain deterministic for research logs and automation.

## Keep and discard rules

Keep a candidate only when all of these are true:

- It leaves protected files unchanged.
- It has a narrow hypothesis tied to row IDs and policy IDs.
- `make research-summary` and relevant validators pass.
- Blind-holdout misses improve without reducing seed, benchmark, or real-case
  reliability.
- Review notes explain any remaining false positives or false negatives.

Discard a candidate when any of these are true:

- It changes labels, source rows, validators, or legal text to improve metrics.
- It improves one holdout row by overfitting a brittle phrase.
- It adds model, ML, or hardware-specific dependencies before a deterministic
  comparison proves value.
- It produces non-zero validation failures.
- It touches unrelated product runtime files.

Use the runner's discard plan before reverting work:

```bash
.venv/bin/python evals/research_loop.py discard --tag research-example
```

Only use `--execute` after confirming the plan lists allowed research files
and no protected or unowned changes.

## Privacy and legal guardrails

AdLint evals are decision-support regression checks. They are not legal
advice, compliance certification, or platform approval guarantees. Keep
language consistent with `docs/legal_disclaimer.md`.

For public-source research:

- Prefer paraphrased, deterministic inputs over copied creative.
- Avoid live network fetches in eval rows.
- Do not store personal data, account IDs, targeting segments, screenshots, or
  raw scraped pages in the repo.
- Preserve `real_world_blind_v1` as a holdout until a supervised report records
  the baseline and follow-up work.

## Backlog constraints

This contract covers the research-loop infrastructure items:

- AND-46: program contract and guardrails.
- AND-47: compact machine-readable summaries and `make research-summary`.
- AND-48: sandboxed runner, protected-file enforcement, and JSONL logs.
- AND-49: supervised blind-holdout pilot report without label tuning.
- AND-50: Apple Silicon dependency decision.

## Apple Silicon decision

The first research runner is dependency-free and Apple-safe. It uses the
standard library, Git, and existing eval commands. It does not add MLX,
PyTorch, MPS, or new model-serving dependencies.

MLX can be reconsidered later only after a tiny deterministic comparison shows
that a local model or adapter improves a named row/policy cluster without
regressing the deterministic baselines. The comparison should fit in a small
script or fixture first; dependency selection comes after measured value.

On Apple Silicon laptops, run deterministic summaries before live model
experiments. Local model runs can heat the machine and take minutes. Stop a
foreground run with `Ctrl-C`. If an eval was launched in the background, stop
only the process you own, for example:

```bash
pkill -f "evals/run_eval.py"
```

Do not kill shared model servers or unrelated processes during parallel work.
