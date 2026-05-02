# Local Model Runtime

The deterministic rules run without a model. To add a local model review pass,
run an Ollama-compatible server and pass `--enable-model`.

Example:

```bash
ollama pull gpt-oss-safeguard-20b
ADLINT_OLLAMA_MODEL=gpt-oss-safeguard-20b adlint scan examples/high_risk_tiktok_health.json --enable-model
```

Environment variables:

- `ADLINT_OLLAMA_MODEL`: classifier model name. Defaults to
  `gpt-oss-safeguard-20b`.
- `ADLINT_OLLAMA_URL`: generate endpoint. Defaults to
  `http://localhost:11434/api/generate`.

If the model endpoint is unavailable, AdLint still returns rule-based findings
and marks the model status as `unavailable` in the JSON output.

## Availability Gate

AdLint does not call `/api/generate` until it verifies that a local
Ollama-compatible server has the requested model installed.

The classifier:

- Allows loopback endpoints such as `localhost`, `127.0.0.1`, or `::1`.
- Checks `/api/tags` before generation.
- Returns `status: unavailable` and `ran: false` when the endpoint is not
  local, the server cannot be reached, or the requested model is missing.
- Uses deterministic generation options for eval runs.
- Treats malformed model JSON as `status: invalid_response` and adds no model
  policy hit.

Hybrid scans are additive. Rules always run first, and model findings can only
add a `model_policy_review` hit. The model cannot suppress or downgrade a
rule-based finding.

## Benchmark Comparison

Model comparison is optional and conservative:

```bash
make model-benchmark
```

This runs rule-only, model-only, and hybrid modes against
`evals/datasets/rule_benchmark_v1.jsonl`. If the requested local model is not
installed, model-only examples are skipped and hybrid results remain rule-based
with model status metadata.

To require a model during manual validation:

```bash
.venv/bin/python evals/run_eval.py evals/datasets/rule_benchmark_v1.jsonl \
  --mode all \
  --require-model \
  --ollama-model gpt-oss-safeguard-20b
```

Current limitation: model-only comparison does not include extracted
landing-page context, so it is not a fair replacement for the rule engine on
privacy, tracker, or landing-page mismatch rows.

## Fine-Tuning Gate

Do not fine-tune or publish adapter/model-card claims from the current
benchmark. Rule-only behavior already passes the synthetic benchmark at the
decision level, and the dataset is policy-author authored. Reconsider adapters
only after a larger adjudicated benchmark shows repeated model-addressable
misses that rules cannot cover cheaply.
