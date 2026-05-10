from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = (ROOT / "adlint/static/index.html").read_text()
APP_JS = (ROOT / "adlint/static/app.js").read_text()
STYLES_CSS = (ROOT / "adlint/static/styles.css").read_text()


def test_local_model_controls_are_present_and_default_off() -> None:
    assert "<legend>Local model</legend>" in INDEX_HTML
    assert 'id="model_enabled"' in INDEX_HTML
    assert 'name="model_enabled"' in INDEX_HTML
    assert 'id="model_enabled" name="model_enabled" type="checkbox" />' in INDEX_HTML
    assert 'id="model_affects_score"' in INDEX_HTML
    assert 'name="model_affects_score"' in INDEX_HTML
    assert 'id="ollama_model"' in INDEX_HTML
    assert 'name="ollama_model"' in INDEX_HTML
    assert 'list="ollama-model-options"' in INDEX_HTML
    assert 'value="gpt-oss-safeguard:20b"' in INDEX_HTML
    assert 'id="ollama-model-options"' in INDEX_HTML


def test_copy_fields_are_required_so_placeholders_do_not_submit() -> None:
    assert 'placeholder="Ad headline"' in INDEX_HTML
    assert 'value="GLP-1 weight loss consults from home"' in INDEX_HTML
    assert 'id="body" name="body" rows="5" placeholder="Primary ad copy" required' in INDEX_HTML
    assert "See if compounded semaglutide is right for you." in INDEX_HTML
    assert 'placeholder="Call to action" value="Check eligibility" required' in INDEX_HTML
    assert 'form.addEventListener(\n  "invalid",' in APP_JS
    assert "Add headline, body, and CTA text before reviewing." in APP_JS


def test_page_starts_with_glp1_sample_context() -> None:
    assert 'value="GLP-1 weight loss consults from home"' in INDEX_HTML
    assert "results that can help you lose weight fast" in INDEX_HTML
    assert 'value="Check eligibility"' in INDEX_HTML
    assert '<option value="health" selected>Health</option>' in INDEX_HTML


def test_model_discovery_fetches_models_and_keeps_fallback_option() -> None:
    assert 'const DEFAULT_OLLAMA_MODEL = "gpt-oss-safeguard:20b";' in APP_JS
    assert 'fetch("/models")' in APP_JS
    assert "normalizeModelList(payload)" in APP_JS
    assert "modelName(payload?.default_model)" in APP_JS
    assert "populateModelOptions([DEFAULT_OLLAMA_MODEL])" in APP_JS
    assert "function uniqueModelOptions(models)" in APP_JS
    assert "for (const model of [...models, DEFAULT_OLLAMA_MODEL])" in APP_JS
    assert "if (value && !values.includes(value)) values.push(value)" in APP_JS


def test_model_toggle_controls_disabled_state_and_reset_defaults() -> None:
    assert 'modelEnabledInput.addEventListener("change", syncLocalModelState)' in APP_JS
    assert "ollamaModelInput.disabled = !modelEnabledInput.checked" in APP_JS
    assert "modelAffectsScoreInput.disabled = !modelEnabledInput.checked" in APP_JS
    assert "function restoreLocalModelDefaults()" in APP_JS
    assert "modelEnabledInput.checked = false" in APP_JS
    assert "modelAffectsScoreInput.checked = false" in APP_JS
    assert "ollamaModelInput.value = DEFAULT_OLLAMA_MODEL" in APP_JS
    assert "restoreLocalModelDefaults();" in APP_JS


def test_analyze_payload_includes_model_keys_when_enabled() -> None:
    assert 'const modelEnabled = formData.get("model_enabled") === "on";' in APP_JS
    assert "model_enabled: modelEnabled" in APP_JS
    assert "if (modelEnabled)" in APP_JS
    assert "payload.ollama_model" in APP_JS
    assert "payload.model_affects_score" in APP_JS
    assert 'fetch("/analyze"' in APP_JS


def test_results_and_markdown_expose_model_status() -> None:
    assert "renderModelStatus(result.model, runMeta)" in APP_JS
    assert "${renderSummary(result)}\n    ${renderModelStatus(result.model, runMeta)}" in APP_JS
    assert "<h3>Local model status</h3>" in APP_JS
    assert "disabled" in APP_JS
    assert "unavailable" in APP_JS
    assert "invalid_response" in APP_JS
    assert "ok" in APP_JS
    assert "Model status:" in APP_JS
    assert "modelStatusLabel(result.model)" in APP_JS


def test_result_tabs_and_processing_trace_are_present() -> None:
    assert 'id="result-tabs"' in INDEX_HTML
    assert 'data-result-view="findings"' in INDEX_HTML
    assert 'data-result-view="processing"' in INDEX_HTML
    assert 'data-result-view="raw"' in INDEX_HTML
    assert 'id="loading-trace"' in INDEX_HTML
    assert "const ANALYSIS_STEPS = [" in APP_JS
    assert "Processing trace" in APP_JS
    assert "Data flow" in APP_JS
    assert "Hidden model reasoning is not exposed" in APP_JS
    assert "metadata-only review notes" in APP_JS
    assert "function setResultView(viewName)" in APP_JS


def test_results_use_consumer_friendly_summary_and_findings() -> None:
    assert 'class="outcome-card ${escapeHtml(decisionClass)}"' in APP_JS
    assert "Review before launch." in APP_JS
    assert "Revise before launch." in APP_JS
    assert "Risk score" in APP_JS
    assert "What to do next" in APP_JS
    assert "Findings" in APP_JS
    assert "Recommended fix" in APP_JS
    assert "View matched copy" in APP_JS
    assert "Reviewer needed" in APP_JS
    assert "High priority" in APP_JS
    assert "Checks included" in APP_JS
    assert "Safer copy options" in APP_JS
    assert ".outcome-card {" in STYLES_CSS
    assert ".risk-bar" in STYLES_CSS
    assert ".action-list" in STYLES_CSS
    assert ".finding-card" in STYLES_CSS
    assert ".finding-card-shell" in STYLES_CSS
    assert ".finding-index" in STYLES_CSS
    assert ".finding-status-stack" in STYLES_CSS
    assert ".evidence-disclosure" in STYLES_CSS


def test_clipboard_copy_has_denied_permission_fallback() -> None:
    assert "await navigator.clipboard.writeText(text)" in APP_JS
    assert "Fall back for browsers that expose Clipboard API but deny write access." in APP_JS
    assert 'document.createElement("textarea")' in APP_JS


def test_loading_copy_mentions_rules_and_local_model() -> None:
    assert "Running policy rules through the local API." in APP_JS
    assert "The local model is also reviewing metadata for this run." in APP_JS


def test_geist_style_layout_uses_focused_app_shell_not_marketing_hero() -> None:
    assert '<div class="app-shell">' in INDEX_HTML
    assert '<header class="topbar">' in INDEX_HTML
    assert '<main class="workspace">' in INDEX_HTML
    assert 'class="panel input-panel"' in INDEX_HTML
    assert 'class="panel result-panel"' in INDEX_HTML
    assert "Ad preflight" in INDEX_HTML
    assert "Result" in INDEX_HTML
    assert "workspace {" in STYLES_CSS
    assert "grid-template-columns: minmax(360px, 0.74fr) minmax(520px, 1fr);" in STYLES_CSS
    assert "@media (max-width: 980px)" in STYLES_CSS
    assert "grid-template-columns: 1fr;" in STYLES_CSS


def test_geist_style_system_font_and_restrained_surfaces_are_preserved() -> None:
    assert '"Geist"' in STYLES_CSS
    assert '"Geist Sans"' in STYLES_CSS
    assert "font-family:" in STYLES_CSS
    assert "ui-sans-serif" in STYLES_CSS
    assert "system-ui" in STYLES_CSS
    assert "-apple-system" in STYLES_CSS
    assert ".panel {" in STYLES_CSS
    assert "border: 1px solid var(--border);" in STYLES_CSS
    assert "border-radius: 8px;" in STYLES_CSS
    assert "box-shadow: var(--shadow);" in STYLES_CSS
    assert "h1 {" in STYLES_CSS
    assert "line-height: 0.98;" in STYLES_CSS
    assert ".primary-button," in STYLES_CSS
    assert "border-radius: 5px;" in STYLES_CSS


def test_platform_select_includes_meta_ads() -> None:
    assert '<option value="meta">Meta</option>' in INDEX_HTML
