# Local Model Runtime

AdLint's deterministic rules always run. When local model review is enabled,
AdLint adds an Ollama-compatible model pass as decision-support metadata; it
does not replace the rule-based findings or provide legal advice.

The Web UI enables the Local model toggle by default and lets users select a
model. Users can turn the toggle off for a rule-only run. API callers control
the same behavior with `model_enabled` and `ollama_model` in `POST /analyze`.
CLI users can pass `--enable-model` and `--ollama-model`.

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
  the request. The Web UI sends `true` by default unless the Local model toggle
  is off.
- `POST /analyze` `ollama_model`: overrides `ADLINT_OLLAMA_MODEL` for that
  request when a specific model is selected.

If the model endpoint is unavailable, AdLint still returns rule-based findings
and marks the model status as `unavailable` in the JSON output. The rule-based
decision, risk score, policy hits, and rewrites are still returned.

For production-reliability diagnostics, run the balanced 75-row public-source
real-case comparison:

```bash
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
