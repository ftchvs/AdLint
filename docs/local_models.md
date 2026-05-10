# Local Model Runtime

AdLint's deterministic rules always run. When local model review is enabled,
AdLint adds an Ollama-compatible model pass as decision-support metadata; it
does not replace the rule-based findings or provide legal advice.

The Web UI starts in rule-only mode and lets users opt into Local model review.
API callers control the same behavior with `model_enabled`,
`model_affects_score`, and `ollama_model` in `POST /analyze`. CLI users can
pass `--enable-model`, `--model-affects-score`, and `--ollama-model`.

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
  times out while producing verbose JSON.

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

## Current Model Recommendation

Keep deterministic rules as the production baseline. The recommended local
model default remains `gpt-oss-safeguard:20b` with the normal Ollama generation
settings. Use local model output as review metadata only until measured runs
show reliable decision accuracy and detailed YAML policy-id recall.

Run `make model-smoke` before spending time on a full live model-quality run.
The 2026-05-04 smoke used the first three seed rows and produced:

| Configuration | Runtime | Model-only rows | Model-only accuracy | Hybrid accuracy | Model status | Generic review additions | Detailed policy-id additions | Rescued rule false negatives |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| `gpt-oss-safeguard:20b` default | 81.508s | 3 | 0.333 | 1.000 | `ok: 3` | 2 | 0 | 0 |
| `gpt-oss-safeguard:20b`, `ADLINT_OLLAMA_NUM_PREDICT=128` | 28.081s | 0 | 0.000 | 1.000 | `invalid_response: 3` | 3 | 0 | 0 |

The capped-token setting is faster, but it produced invalid structured
responses on every model-required smoke row. Do not use it as a default quality
setting.

An additional installed model, `qwen3.5:35b-a3b`, was tested on the blind
holdout as a manual diagnostic. The run took 2749.144 seconds, returned
`invalid_response: 90` for model-only and hybrid model calls, scored 0 model-only
rows, and reduced hybrid decision accuracy to 0.656 on the pre-triage blind
baseline. A later smoke attempt was stopped after more than four minutes with no
completed output. Treat this model as rejected for current AdLint eval use until
its structured JSON behavior is fixed.
