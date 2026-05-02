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
