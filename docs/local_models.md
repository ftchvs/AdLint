# Local Model Runtime

AdLint's deterministic rules always run. When local model review is enabled,
AdLint adds an Ollama-compatible model pass as decision-support metadata; it
does not replace the rule-based findings or provide legal advice.

The Web UI starts in rule-only mode and lets users opt into Local model review.
The model selector is populated from local Ollama tags when available, filters
obvious embedding-only models, and falls back to known review-model options.
Client-side timeout recovery keeps a slow/stuck local model call from leaving
the form disabled forever. API callers control the same behavior with
`model_enabled`, `model_affects_score`, and `ollama_model` in `POST /analyze`.
CLI users can pass `--enable-model`, `--model-affects-score`, and
`--ollama-model`.

Example:

```bash
ollama pull gpt-oss-safeguard:20b
ADLINT_OLLAMA_MODEL=gpt-oss-safeguard:20b adlint scan examples/high_risk_tiktok_health.json --enable-model
```

Environment variables:

- `ADLINT_OLLAMA_MODEL`: classifier model name. Defaults to
  `gpt-oss-safeguard:20b`.
- `ADLINT_OLLAMA_URL`: Ollama-compatible chat endpoint. Defaults to
  `http://localhost:11434/api/chat`.
- `ADLINT_OLLAMA_TIMEOUT`: generation timeout in seconds for model calls.
  The default is 45 seconds; eval targets use 300 seconds for slow local rows.
- `ADLINT_OLLAMA_NUM_PREDICT`: optional positive token cap for local model
  generation. Leave unset for Ollama defaults; set it for evals when a model
  times out while producing verbose JSON. The development API target uses a
  bounded default so local review runs fail closed instead of hanging forever.

API fields:

- `GET /models`: returns local model configuration and available model choices
  for clients such as the Web UI.
- `POST /analyze` `model_enabled`: enables or disables the local model pass for
  the request. The Web UI sends `false` by default unless the Local model
  toggle is enabled.
- `POST /analyze` `model_affects_score`: lets valid model findings join
  `policy_hits` and affect the final score. The default is `false`, so local
  model output remains metadata-only.
- `POST /analyze` `ollama_model`: overrides `ADLINT_OLLAMA_MODEL` for that
  request when a specific model is selected.

If the model endpoint is unavailable, AdLint still returns rule-based findings
and marks the model status as `unavailable` in the JSON output. The rule-based
decision, risk score, policy hits, and rewrites are still returned.

## Model trust boundary

Local model output is treated as untrusted runtime metadata until it passes the
`adlint.model_review.v1` schema. AdLint validates that:

- `decision` is one of `approved`, `needs_review`, or `high_risk`.
- `categories` and `evidence` are arrays of strings.
- `recommended_action`, when present, is a string.

AdLint sends deterministic local classifier calls with JSON formatting,
`temperature: 0`, and `think: false` where supported. Some local models still
wrap JSON in Markdown fences or pre/post text, so AdLint extracts the enclosed
JSON object before schema validation.

Invalid JSON, unknown decisions, and malformed fields produce
`status: invalid_response`, `valid_response: false`, and `ignored: true`. Those
responses add no findings and never affect scoring.

Landing-page content is also treated as untrusted evidence. The prompt wraps ad
copy, extracted landing-page fields, and optional HTML excerpts in explicit
untrusted sections and tells the model not to follow instructions embedded in
those fields. AdLint prefers the structured landing-page snapshot — title,
headings, visible claims, forms, disclaimers, pricing text, trackers, and fetch
errors — over raw HTML.

## What the model can change

| Output | Default rule-only | `model_enabled: true` | `model_affects_score: true` |
| --- | --- | --- | --- |
| Deterministic rules | Yes | Yes | Yes |
| Final decision / risk score | Rules only | Rules only | Rules + valid model findings |
| `policy_hits` | Rule hits | Rule hits | Rule hits plus valid model hits |
| `model.status` | `disabled` | Runtime/schema status | Runtime/schema status |
| `model.findings` | Empty/absent | Valid model findings | Valid model findings |
| Invalid model response | N/A | Ignored | Ignored |

Keep score impact off unless you are explicitly evaluating model contribution
or running a workflow that accepts model-added review burden.

For production-reliability diagnostics, run the balanced 75-row public-source
real-case comparison:

```bash
make model-smoke
make real-cases-model-quality
```

For the harder blind holdout, run:

```bash
make real-world-blind-model-quality
```

The target requires model availability and writes ignored JSON/Markdown
artifacts under `evals/results/`. It sets `ADLINT_OLLAMA_TIMEOUT=300` for the
eval process because local inference can be slow on sensitive-context rows.
Treat model-only and hybrid metrics as measured local-model quality for that
run, not as legal-compliance or platform approval evidence.

To measure whether model-added notes are actually useful to a human reviewer,
run:

```bash
make model-benchmark
make model-usefulness
```

`model-usefulness` labels model-added findings against
`evals/datasets/model_review_usefulness_v1.jsonl` and reports useful-note
precision, false-review burden, generic-review burden, and invalid-response
rate. This is the current signal/noise loop for deciding whether a local model
is ready for score impact.

## Current Model Recommendation

Keep deterministic rules as the production baseline. The recommended local
model default remains `gpt-oss-safeguard:20b`. Use local model output as review
metadata only until measured runs show reliable decision accuracy, detailed
YAML policy-id recall, and acceptable false-review burden.

Run `make model-smoke` before spending time on a full live model-quality run.
The older 2026-05-04 smoke showed why score impact remains off by default:
models could add generic review notes or invalid JSON even when hybrid rule
accuracy stayed intact.

PR #16 improved runtime stability by disabling Ollama thinking output where
supported, accepting fenced JSON, and bounding local generation. With
`ADLINT_OLLAMA_TIMEOUT=180` and `ADLINT_OLLAMA_NUM_PREDICT=1024`, a live local
matrix reported `model.status: ok` for installed review models including
`gpt-oss-safeguard:20b`, `gpt-oss:20b`, `qwen3-coder:30b`,
`qwen3.5:35b-a3b`, and `gemma4:26b`. Treat that as runtime compatibility, not
proof of better policy judgment.

Model selection guidance:

- Prefer `gpt-oss-safeguard:20b` as the default local reviewer until newer
  evals show another model has better useful-note precision and lower review
  burden.
- Use `ADLINT_OLLAMA_TIMEOUT` and `ADLINT_OLLAMA_NUM_PREDICT` for slow models
  during manual evals, but do not infer quality from `status: ok` alone.
- Keep `model_affects_score` off unless you are explicitly measuring whether a
  model's findings improve outcomes without adding unacceptable false review
  burden.
