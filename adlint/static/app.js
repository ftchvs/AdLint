const form = document.querySelector("#review-form");
const emptyState = document.querySelector("#status-empty");
const loadingState = document.querySelector("#status-loading");
const loadingCopy = document.querySelector("#loading-copy");
const loadingTrace = document.querySelector("#loading-trace");
const errorState = document.querySelector("#status-error");
const resultContent = document.querySelector("#result-content");
const resultTabs = document.querySelector("#result-tabs");
const exportActions = document.querySelector("#export-actions");
const copyJsonButton = document.querySelector("#copy-json");
const exportJsonButton = document.querySelector("#export-json");
const exportMarkdownButton = document.querySelector("#export-markdown");
const modelEnabledInput = document.querySelector("#model_enabled");
const modelAffectsScoreInput = document.querySelector("#model_affects_score");
const ollamaModelInput = document.querySelector("#ollama_model");

const DEFAULT_OLLAMA_MODEL = "gpt-oss-safeguard:20b";
const FALLBACK_OLLAMA_MODELS = [
  DEFAULT_OLLAMA_MODEL,
  "gpt-oss:20b",
  "qwen3-coder:30b",
  "qwen3.5:35b-a3b",
  "gemma4:26b",
];
const RULE_ONLY_TIMEOUT_MS = 30000;
const LOCAL_MODEL_TIMEOUT_MS = 210000;
const EMBEDDING_MODEL_MARKERS = ["embed", "bge-"];
const MODEL_STATUSES = ["disabled", "unavailable", "invalid_response", "ok"];
const ANALYSIS_STEPS = [
  ["intake", "Input normalized", "Copy, campaign context, modules, and optional landing inputs are prepared for review."],
  ["landing", "Landing page parsed", "Inline HTML or a reachable URL is converted into title, claim, form, tracker, and disclaimer signals."],
  ["rules", "Rules scanned", "Policy YAML checks run first so the baseline result does not depend on model availability."],
  ["model", "Local model reviewed", "When enabled, Ollama returns structured metadata-only review notes unless score impact is explicitly enabled. Hidden model reasoning is not exposed."],
  ["merge", "Evidence merged", "Rule signals remain the trusted baseline; model findings are deduplicated into policy hits only when score impact is enabled."],
  ["score", "Risk scored", "Severity, evidence, industry, platform, privacy, and landing context produce the final decision."],
  ["rewrite", "Rewrites prepared", "Rewrite options are generated from triggered policies without changing the submitted ad."],
];

let lastResult = null;
let lastRunMeta = null;
let loadingTraceTimer = null;

initLocalModelControls();
initResultTabs();

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = buildPayload(new FormData(form));
  const startedAt = performance.now();
  setLoadingCopy(payload);
  startLoadingTrace(payload);
  setState("loading");
  setSubmitting(true);

  try {
    const response = await fetchWithTimeout("/analyze", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(payload),
    }, requestTimeoutMs(payload));

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || `Request failed with status ${response.status}`);
    }

    lastResult = await response.json();
    lastRunMeta = {
      duration_ms: Math.max(1, Math.round(performance.now() - startedAt)),
      model_enabled: Boolean(payload.model_enabled),
      ollama_model: payload.ollama_model || null,
      landing_page_supplied: Boolean(payload.landing_page_html || payload.landing_page_url),
      module_count: payload.policy_modules.length,
    };
    renderResult(lastResult, lastRunMeta);
    setState("result");
  } catch (error) {
    lastResult = null;
    lastRunMeta = null;
    renderError(error);
    setState("error");
  } finally {
    stopLoadingTrace();
    setSubmitting(false);
  }
});

async function fetchWithTimeout(url, options, timeoutMs) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (error && error.name === "AbortError") {
      const seconds = Math.round(timeoutMs / 1000);
      throw new Error(`Review timed out after ${seconds}s. Try a smaller local model or run again after the model has warmed up.`);
    }
    throw error;
  } finally {
    window.clearTimeout(timer);
  }
}

function requestTimeoutMs(payload) {
  return payload.model_enabled ? LOCAL_MODEL_TIMEOUT_MS : RULE_ONLY_TIMEOUT_MS;
}

form.addEventListener(
  "invalid",
  () => {
    lastResult = null;
    resultContent.innerHTML = "";
    resultContent.classList.remove("has-result");
    renderError(new Error("Add headline, body, and CTA text before reviewing."));
    setState("error");
  },
  true,
);

form.addEventListener("reset", () => {
  window.setTimeout(() => {
    restoreLocalModelDefaults();
    lastResult = null;
    lastRunMeta = null;
    resultContent.innerHTML = "";
    resultContent.classList.remove("has-result");
    exportActions.hidden = true;
    resultTabs.hidden = true;
    setState("empty");
  }, 0);
});

copyJsonButton.addEventListener("click", () => {
  if (!lastResult) return;
  copyText(JSON.stringify(lastResult, null, 2));
});

exportJsonButton.addEventListener("click", () => {
  if (!lastResult) return;
  downloadFile("adlint-report.json", "application/json", `${JSON.stringify(lastResult, null, 2)}\n`);
});

exportMarkdownButton.addEventListener("click", () => {
  if (!lastResult) return;
  downloadFile("adlint-report.md", "text/markdown", toMarkdown(lastResult));
});

function initLocalModelControls() {
  restoreLocalModelDefaults();
  modelEnabledInput.addEventListener("change", syncLocalModelState);
  discoverModels();
}

function initResultTabs() {
  resultTabs.querySelectorAll("[data-result-view]").forEach((button) => {
    button.addEventListener("click", () => {
      setResultView(button.getAttribute("data-result-view") || "findings");
    });
  });
}

async function discoverModels() {
  try {
    const response = await fetch("/models");
    if (!response.ok) throw new Error(`Model discovery failed with status ${response.status}`);
    const payload = await response.json();
    const models = normalizeModelList(payload);
    const defaultModel = modelName(payload?.default_model) || DEFAULT_OLLAMA_MODEL;
    populateModelOptions([defaultModel, ...models, ...FALLBACK_OLLAMA_MODELS]);
    if (!ollamaModelInput.value.trim() || ollamaModelInput.value === DEFAULT_OLLAMA_MODEL) {
      ollamaModelInput.value = defaultModel;
    }
  } catch {
    populateModelOptions(FALLBACK_OLLAMA_MODELS);
    if (!ollamaModelInput.value.trim()) ollamaModelInput.value = DEFAULT_OLLAMA_MODEL;
  }
}

function normalizeModelList(payload) {
  const source = Array.isArray(payload) ? payload : payload && Array.isArray(payload.models) ? payload.models : [];
  return [...new Set(source.map(modelName).filter(isReviewModelOption))];
}

function modelName(item) {
  if (typeof item === "string") return item.trim();
  if (item && typeof item === "object") {
    return String(item.name || item.model || "").trim();
  }
  return "";
}

function isReviewModelOption(value) {
  if (!value) return false;
  const normalized = value.toLowerCase();
  return !EMBEDDING_MODEL_MARKERS.some((marker) => normalized.includes(marker));
}

function populateModelOptions(models) {
  const values = uniqueModelOptions(models);
  const currentValue = ollamaModelInput.value.trim();
  ollamaModelInput.innerHTML = values
    .map((model) => {
      const safe = escapeHtml(model);
      return `<option value="${safe}">${safe}</option>`;
    })
    .join("");
  if (currentValue && values.includes(currentValue)) {
    ollamaModelInput.value = currentValue;
  } else {
    ollamaModelInput.value = values.includes(DEFAULT_OLLAMA_MODEL) ? DEFAULT_OLLAMA_MODEL : values[0] || "";
  }
}

function uniqueModelOptions(models) {
  const values = [];
  for (const model of [...models, ...FALLBACK_OLLAMA_MODELS]) {
    const value = modelName(model);
    if (value && !values.includes(value)) values.push(value);
  }
  return values;
}

function restoreLocalModelDefaults() {
  modelEnabledInput.checked = false;
  modelAffectsScoreInput.checked = false;
  ollamaModelInput.value = DEFAULT_OLLAMA_MODEL;
  syncLocalModelState();
}

function syncLocalModelState() {
  ollamaModelInput.disabled = !modelEnabledInput.checked;
  modelAffectsScoreInput.disabled = !modelEnabledInput.checked;
  ollamaModelInput.setAttribute("aria-disabled", String(!modelEnabledInput.checked));
  modelAffectsScoreInput.setAttribute("aria-disabled", String(!modelEnabledInput.checked));
  if (!modelEnabledInput.checked) {
    modelAffectsScoreInput.checked = false;
  }
}

function buildPayload(formData) {
  const modelEnabled = formData.get("model_enabled") === "on";
  const payload = {
    platform: stringValue(formData, "platform", "google"),
    industry: stringValue(formData, "industry", "general"),
    headline: stringValue(formData, "headline", ""),
    body: stringValue(formData, "body", ""),
    cta: stringValue(formData, "cta", ""),
    policy_modules: formData.getAll("policy_modules").map(String),
    model_enabled: modelEnabled,
  };

  if (modelEnabled) {
    payload.ollama_model = stringValue(formData, "ollama_model", DEFAULT_OLLAMA_MODEL) || DEFAULT_OLLAMA_MODEL;
    payload.model_affects_score = formData.get("model_affects_score") === "on";
  }

  const landingHtml = stringValue(formData, "landing_page_html", "");
  const landingUrl = stringValue(formData, "landing_page_url", "");
  if (landingHtml) {
    payload.landing_page_html = landingHtml;
  } else if (landingUrl) {
    payload.landing_page_url = landingUrl;
  }

  return payload;
}

function stringValue(formData, key, fallback) {
  const value = formData.get(key);
  return typeof value === "string" ? value.trim() : fallback;
}

function setSubmitting(isSubmitting) {
  const button = form.querySelector("button[type='submit']");
  button.disabled = isSubmitting;
  button.textContent = isSubmitting ? "Reviewing" : "Run review";
}

function setLoadingCopy(payload) {
  loadingCopy.textContent = payload.model_enabled
    ? "Running policy rules through the local API. The local model is also reviewing metadata for this run."
    : "Running policy rules through the local API.";
}

function startLoadingTrace(payload) {
  stopLoadingTrace();
  let activeIndex = 0;
  const steps = analysisSteps(payload);
  renderTrace(loadingTrace, steps, activeIndex, "loading");
  loadingTraceTimer = window.setInterval(() => {
    activeIndex = Math.min(activeIndex + 1, steps.length - 1);
    renderTrace(loadingTrace, steps, activeIndex, "loading");
  }, 520);
}

function stopLoadingTrace() {
  if (loadingTraceTimer) {
    window.clearInterval(loadingTraceTimer);
    loadingTraceTimer = null;
  }
}

function setState(name) {
  for (const element of [emptyState, loadingState, errorState]) {
    element.classList.remove("is-visible");
  }
  resultContent.classList.toggle("has-result", name === "result");

  if (name === "empty") emptyState.classList.add("is-visible");
  if (name === "loading") loadingState.classList.add("is-visible");
  if (name === "error") errorState.classList.add("is-visible");
  exportActions.hidden = name !== "result";
  resultTabs.hidden = name !== "result";
}

function renderError(error) {
  const message = error instanceof Error ? error.message : "Unable to review this ad.";
  errorState.innerHTML = `
    <p class="state-title">Review failed</p>
    <p>${escapeHtml(message)}</p>
  `;
  resultContent.innerHTML = "";
}

function renderResult(result, runMeta = {}) {
  resultContent.innerHTML = `
    ${renderSummary(result)}
    ${renderModelStatus(result.model, runMeta)}
    <div class="result-view is-active" data-view-panel="findings">
      ${renderFindingsView(result)}
    </div>
    <div class="result-view" data-view-panel="processing">
      ${renderProcessingView(result, runMeta)}
    </div>
    <div class="result-view" data-view-panel="raw">
      <section class="result-section">
        <h3>Raw JSON</h3>
        <pre class="raw-json">${escapeHtml(JSON.stringify(result, null, 2))}</pre>
      </section>
    </div>
  `;
  setResultView("findings");

  resultContent.querySelectorAll("[data-copy-rewrite]").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.getAttribute("data-copy-rewrite"));
      const rewrite = result.safer_rewrites[index];
      copyText(formatRewrite(rewrite));
    });
  });
}

function renderFindingsView(result) {
  return `
    ${renderNextSteps(result.recommended_actions)}
    ${renderPolicyHits(result.policy_hits)}
    ${renderRewrites(result.safer_rewrites)}
    ${renderLandingPage(result.landing_page)}
  `;
}

function renderProcessingView(result, runMeta = {}) {
  return `
    <section class="result-section">
      <h3>Processing trace</h3>
      <p class="muted">This trace shows observable backend steps and parsed outputs, not hidden model reasoning or chain-of-thought.</p>
      ${renderTraceMarkup(analysisStepsFromResult(result, runMeta), -1, "complete")}
    </section>
    <section class="result-section">
      <h3>Data flow</h3>
      <div class="flow-grid">
        <div class="flow-card">
          <span>Input</span>
          <strong>${escapeHtml((result.enabled_modules || []).length)} modules</strong>
          <p>Normalized copy and campaign metadata sent to <code>/analyze</code>.</p>
        </div>
        <div class="flow-card">
          <span>Rules</span>
          <strong>${escapeHtml(String(ruleHitCount(result)))} hits</strong>
          <p>Policy YAML checks produced deterministic evidence before model review.</p>
        </div>
        <div class="flow-card">
          <span>Model</span>
          <strong>${escapeHtml(modelStatusLabel(result.model))}</strong>
          <p>Local model output is parsed as structured metadata, not hidden reasoning.</p>
        </div>
        <div class="flow-card">
          <span>Score</span>
          <strong>${formatRiskScore(result.risk_score)}</strong>
          <p>Risk score and decision generated after evidence merge.</p>
        </div>
      </div>
    </section>
  `;
}

function renderModelStatus(model = {}, runMeta = {}) {
  const status = MODEL_STATUSES.includes(model.status) ? model.status : "disabled";
  const provider = model.provider || "local";
  const selectedModel = model.model || model.name || "none";
  const reason = model.error || model.detail || model.message || "";
  return `
    <section class="result-section model-status-section">
      <h3>Local model status</h3>
      <div class="model-card">
        <div>
          <span class="metric-label">Status</span>
          <strong class="model-card-value">${escapeHtml(status)}</strong>
        </div>
        <div>
          <span class="metric-label">Provider</span>
          <strong class="model-card-value">${escapeHtml(provider)}</strong>
        </div>
        <div>
          <span class="metric-label">Model</span>
          <strong class="model-card-value">${escapeHtml(selectedModel)}</strong>
        </div>
        <div>
          <span class="metric-label">Elapsed</span>
          <strong class="model-card-value">${runMeta.duration_ms ? `${escapeHtml(runMeta.duration_ms)}ms` : "n/a"}</strong>
        </div>
      </div>
      <div class="hit-meta model-card-tags">
        <span class="tag model-status ${escapeHtml(status)}">${escapeHtml(status)}</span>
        <span class="tag">${model.enabled ? "model metadata" : "rule-only"}</span>
        ${model.enabled ? `<span class="tag">${model.affects_score ? "score-impact on" : "score-impact off"}</span>` : ""}
        ${model.hit_count !== undefined ? `<span class="tag">${escapeHtml(model.hit_count)} model findings</span>` : ""}
        ${model.endpoint ? `<span class="tag">${escapeHtml(model.endpoint)}</span>` : ""}
      </div>
      ${reason ? `<p class="muted">${escapeHtml(reason)}</p>` : ""}
    </section>
  `;
}

function analysisSteps(payload) {
  return ANALYSIS_STEPS.filter(([id]) => payload.model_enabled || id !== "model").map(([id, label, detail]) => {
    if (id !== "model") return { id, label, detail };
    const model = payload.ollama_model || DEFAULT_OLLAMA_MODEL;
    return {
      id,
      label,
      detail: `Local Ollama model '${model}' receives the classifier prompt and returns strict JSON metadata when available.`,
    };
  });
}

function analysisStepsFromResult(result, runMeta = {}) {
  const payload = {
    model_enabled: runMeta.model_enabled || Boolean(result.model?.enabled),
    ollama_model: runMeta.ollama_model || result.model?.model,
  };
  return analysisSteps(payload).map((step) => {
    if (step.id === "model") {
      return {
        ...step,
        label: `Local model ${result.model?.status || "disabled"}`,
        detail: modelTraceDetail(result.model || {}),
      };
    }
    if (step.id === "rules") {
      return {
        ...step,
        detail: `${ruleHitCount(result)} deterministic policy hits found before scoring.`,
      };
    }
    if (step.id === "score") {
      return {
        ...step,
        detail: `Decision '${result.decision}' with risk score ${formatRiskScore(result.risk_score)}.`,
      };
    }
    return step;
  });
}

function modelTraceDetail(model = {}) {
  if (model.status === "ok") {
    return model.affects_score
      ? "Ollama returned valid JSON metadata. Score impact was enabled, so model findings can join policy hits."
      : "Ollama returned valid JSON metadata. Score impact is off, so model findings remain metadata-only review notes.";
  }
  if (model.status === "invalid_response") {
    return "The local model responded, but AdLint rejected the response as invalid structured JSON and ignored it for scoring.";
  }
  if (model.status === "unavailable") {
    return "The local model was requested but unavailable, so rule-based findings still completed.";
  }
  return "Local model review was disabled for this run.";
}

function renderTrace(target, steps, activeIndex, mode) {
  target.innerHTML = renderTraceMarkup(steps, activeIndex, mode);
}

function renderTraceMarkup(steps, activeIndex, mode) {
  const rows = steps.map((step, index) => {
    const state = traceState(index, activeIndex, mode);
    return `
      <li class="trace-step ${state}">
        <span class="trace-dot" aria-hidden="true"></span>
        <div>
          <strong>${escapeHtml(step.label)}</strong>
          <p>${escapeHtml(step.detail)}</p>
        </div>
      </li>
    `;
  });
  return `<ol class="trace-list">${rows.join("")}</ol>`;
}

function traceState(index, activeIndex, mode) {
  if (mode === "complete") return "is-complete";
  if (index < activeIndex) return "is-complete";
  if (index === activeIndex) return "is-running";
  return "is-pending";
}

function setResultView(viewName) {
  resultTabs.querySelectorAll("[data-result-view]").forEach((button) => {
    button.classList.toggle("is-active", button.getAttribute("data-result-view") === viewName);
  });
  resultContent.querySelectorAll("[data-view-panel]").forEach((panel) => {
    panel.classList.toggle("is-active", panel.getAttribute("data-view-panel") === viewName);
  });
}

function renderSummary(result) {
  const decisionClass = tokenClass(result.decision || "unknown");
  const riskScore = formatRiskScore(result.risk_score);
  const riskWidth = riskPercent(result.risk_score);
  const hitCount = (result.policy_hits || []).length;
  const actionCount = (result.recommended_actions || []).length;
  return `
    <section class="outcome-card ${escapeHtml(decisionClass)}" aria-label="Review summary">
      <div class="outcome-copy">
        <span class="status-pill ${escapeHtml(decisionClass)}">${escapeHtml(decisionPillLabel(result.decision))}</span>
        <h3>${escapeHtml(decisionHeadline(result.decision))}</h3>
        <p>${escapeHtml(decisionDescription(result))}</p>
      </div>
      <div class="risk-meter" aria-label="Risk score ${escapeHtml(riskScore)}">
        <div class="risk-meter-header">
          <span>Risk score</span>
          <strong>${riskScore}</strong>
        </div>
        <div class="risk-bar" aria-hidden="true">
          <span style="width: ${riskWidth}%"></span>
        </div>
      </div>
      <div class="outcome-stats">
        <div>
          <span>Review</span>
          <strong>${result.requires_review ? "Required" : "Not required"}</strong>
        </div>
        <div>
          <span>Findings</span>
          <strong>${escapeHtml(String(hitCount))}</strong>
        </div>
        <div>
          <span>Next steps</span>
          <strong>${escapeHtml(String(actionCount))}</strong>
        </div>
      </div>
    </section>
    <section class="result-section checks-section">
      <div class="section-heading">
        <h3>Checks included</h3>
        <p class="muted">Rules and model output were merged into one review.</p>
      </div>
      <div class="hit-meta">${(result.enabled_modules || []).map((module) => `<span class="tag">${escapeHtml(formatTokenLabel(module))}</span>`).join("")}</div>
    </section>
  `;
}

function renderNextSteps(values) {
  if (!values || values.length === 0) {
    return `
      <section class="result-section">
        <div class="section-heading">
          <h3>What to do next</h3>
          <p class="muted">No immediate edits were recommended.</p>
        </div>
      </section>
    `;
  }

  return `
    <section class="result-section action-section">
      <div class="section-heading">
        <h3>What to do next</h3>
        <p class="muted">Start with these changes before launch or platform review.</p>
      </div>
      <ol class="action-list">${values.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ol>
    </section>
  `;
}

function renderPolicyHits(hits) {
  if (!hits || hits.length === 0) {
    return `
      <section class="result-section">
        <div class="section-heading">
          <h3>Findings</h3>
          <p class="muted">No policy issues were detected in this pass.</p>
        </div>
      </section>
    `;
  }

  return `
    <section class="result-section findings-section">
      <div class="section-heading">
        <h3>Findings</h3>
        <p class="muted">${escapeHtml(String(hits.length))} item${hits.length === 1 ? "" : "s"} to check before this ad runs.</p>
      </div>
      <div class="findings-list">
        ${hits.map((hit, index) => renderPolicyHit(hit, index)).join("")}
      </div>
    </section>
  `;
}

function renderPolicyHit(hit, index = 0) {
  const evidence = hit.evidence || [];
  const severityClass = tokenClass(hit.severity || "unknown");
  const title = policyHitTitle(hit);
  const evidenceLabel = `${evidence.length} matched ${evidence.length === 1 ? "phrase" : "phrases"}`;
  return `
    <article class="finding-card ${escapeHtml(severityClass)}">
      <div class="finding-card-shell">
        <div class="finding-index" aria-hidden="true">${escapeHtml(String(index + 1).padStart(2, "0"))}</div>
        <div class="finding-main">
          <div class="finding-card-header">
            <div class="finding-title-block">
              <span class="finding-kicker">${escapeHtml(formatTokenLabel(hit.category || "policy review"))}</span>
              <h4>${escapeHtml(title)}</h4>
            </div>
            <div class="finding-status-stack">
              <span class="severity-badge ${escapeHtml(severityClass)}">${escapeHtml(severityLabel(hit.severity))}</span>
              ${hit.requires_review ? '<span class="review-badge">Reviewer needed</span>' : ""}
            </div>
          </div>
          ${hit.description ? `
            <div class="finding-why">
              <span>Why it matters</span>
              <p>${escapeHtml(hit.description)}</p>
            </div>
          ` : ""}
          <div class="finding-guidance">
            <span>Recommended fix</span>
            <p>${escapeHtml(hit.recommended_action || "Review the finding.")}</p>
          </div>
          <div class="finding-footer">
            <span>${escapeHtml(formatTokenLabel(hit.policy_id || "policy"))}</span>
            <span>${escapeHtml(evidenceLabel)}</span>
          </div>
          ${renderEvidence(evidence)}
        </div>
      </div>
    </article>
  `;
}

function renderEvidence(evidence) {
  if (!evidence || evidence.length === 0) return "";
  return `
    <details class="evidence-disclosure">
      <summary>
        <span>View matched copy</span>
        <strong>${escapeHtml(String(evidence.length))}</strong>
      </summary>
      <div class="evidence-list">
        ${evidence.map((item) => `
          <div class="evidence-item">
            <span class="evidence-source">${escapeHtml(formatTokenLabel(item.source || "source"))}</span>
            <span>${escapeHtml(item.text || "")}</span>
          </div>
        `).join("")}
      </div>
    </details>
  `;
}

function renderRewrites(rewrites) {
  if (!rewrites || rewrites.length === 0) {
    return `
    <section class="result-section">
      <h3>Safer copy options</h3>
      <p class="muted">No rewrite suggested.</p>
    </section>
  `;
  }

  return `
    <section class="result-section">
      <h3>Safer copy options</h3>
      ${rewrites.map((rewrite, index) => `
        <article class="rewrite-item">
          <div>
            <p><strong>Headline:</strong> ${escapeHtml(rewrite.headline || "")}</p>
            <p><strong>Body:</strong> ${escapeHtml(rewrite.body || "")}</p>
            <p><strong>CTA:</strong> ${escapeHtml(rewrite.cta || "")}</p>
          </div>
          <button class="secondary-button" type="button" data-copy-rewrite="${index}">Copy rewrite</button>
        </article>
      `).join("")}
    </section>
  `;
}

function renderLandingPage(page = {}) {
  const groups = [
    ["Title", page.title ? [page.title] : []],
    ["Headings", page.headings],
    ["Visible claims", page.visible_claims],
    ["Forms", page.forms],
    ["Pricing", page.pricing_text],
    ["Disclaimers", page.disclaimers],
    ["Tracking scripts", page.tracking_scripts],
    ["Fetch error", page.fetch_error ? [page.fetch_error] : []],
  ].filter(([, values]) => values && values.length > 0);

  if (groups.length === 0 && !page.url) {
    return `
      <section class="result-section">
        <h3>Landing page</h3>
        <p class="muted">No landing page supplied.</p>
      </section>
    `;
  }

  return `
    <section class="result-section">
      <h3>Landing page</h3>
      ${page.url ? `<p class="muted">${escapeHtml(page.url)}</p>` : ""}
      <div class="landing-grid">
        ${groups.map(([label, values]) => `
          <div class="landing-group">
            <p>${escapeHtml(label)}</p>
            <ul>${values.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul>
          </div>
        `).join("")}
      </div>
    </section>
  `;
}

function decisionPillLabel(decision) {
  const normalized = String(decision || "").toLowerCase();
  if (normalized === "approved") return "Looks clear";
  if (normalized === "needs_review") return "Needs review";
  if (normalized === "high_risk") return "High risk";
  return formatTokenLabel(decision || "unknown");
}

function decisionHeadline(decision) {
  const normalized = String(decision || "").toLowerCase();
  if (normalized === "approved") return "This ad looks ready for a policy pass.";
  if (normalized === "needs_review") return "Review before launch.";
  if (normalized === "high_risk") return "Revise before launch.";
  return "Review this result before launch.";
}

function decisionDescription(result) {
  const hitCount = (result.policy_hits || []).length;
  const actionCount = (result.recommended_actions || []).length;
  if (result.decision === "approved") {
    return "No major policy issues were detected. Keep a human review in the loop for regulated claims.";
  }
  if (result.decision === "high_risk") {
    return `${hitCount} finding${hitCount === 1 ? "" : "s"} and ${actionCount} next step${actionCount === 1 ? "" : "s"} point to copy that should be changed before this runs.`;
  }
  return `${hitCount} finding${hitCount === 1 ? "" : "s"} need a closer look before this campaign goes live.`;
}

function formatRiskScore(score) {
  if (typeof score !== "number") return "0.00";
  return score.toFixed(2);
}

function riskPercent(score) {
  if (typeof score !== "number") return 0;
  return Math.round(Math.max(0, Math.min(score, 1)) * 100);
}

function policyHitTitle(hit) {
  return formatTokenLabel(hit.policy_id || hit.category || "policy finding");
}

function severityLabel(severity) {
  const normalized = String(severity || "").toLowerCase();
  if (normalized === "critical") return "Critical";
  if (normalized === "high") return "High priority";
  if (normalized === "medium") return "Medium priority";
  if (normalized === "low") return "Low priority";
  return formatTokenLabel(severity || "Unknown");
}

function formatTokenLabel(value) {
  return String(value || "")
    .trim()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function tokenClass(value) {
  return String(value || "unknown")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "unknown";
}

function ruleHitCount(result) {
  return (result.policy_hits || []).filter((hit) => hit.source !== "ollama").length;
}

function formatRewrite(rewrite) {
  return [
    `Headline: ${rewrite.headline || ""}`,
    `Body: ${rewrite.body || ""}`,
    `CTA: ${rewrite.cta || ""}`,
  ].join("\n");
}

function toMarkdown(result) {
  const lines = [
    "# AdLint Report",
    "",
    `- Decision: \`${result.decision}\``,
    `- Risk score: \`${formatRiskScore(result.risk_score)}\``,
    `- Requires review: \`${String(Boolean(result.requires_review)).toLowerCase()}\``,
    `- Model status: \`${modelStatusLabel(result.model)}\``,
    "",
    "## Policy Hits",
    "",
  ];

  if (!result.policy_hits || result.policy_hits.length === 0) {
    lines.push("No policy hits detected.");
  } else {
    for (const hit of result.policy_hits) {
      lines.push(`### ${hit.policy_id}`, "", `- Severity: \`${hit.severity}\``, `- Category: \`${hit.category}\``, `- Recommended action: ${hit.recommended_action}`);
      if (hit.requires_review) lines.push("- Review label: `requires_review`");
      lines.push("- Evidence:");
      for (const evidence of hit.evidence || []) {
        lines.push(`  - \`${evidence.source}\`: ${evidence.text}`);
      }
      lines.push("");
    }
  }

  lines.push("", "## Actions", "");
  if (result.recommended_actions && result.recommended_actions.length > 0) {
    for (const action of result.recommended_actions) lines.push(`- ${action}`);
  } else {
    lines.push("- No additional actions.");
  }

  lines.push("", "## Safer Rewrites", "");
  if (result.safer_rewrites && result.safer_rewrites.length > 0) {
    result.safer_rewrites.forEach((rewrite, index) => {
      lines.push(`### Option ${index + 1}`, "", `- Headline: ${rewrite.headline}`, `- Body: ${rewrite.body}`, `- CTA: ${rewrite.cta}`, "");
    });
  } else {
    lines.push("No rewrite suggested.");
  }

  const page = result.landing_page || {};
  if (page.url || page.title || page.fetch_error || hasLandingLists(page)) {
    lines.push("", "## Landing Page", "");
    if (page.url) lines.push(`- URL: ${page.url}`);
    if (page.title) lines.push(`- Title: ${page.title}`);
    appendMarkdownList(lines, "Headings", page.headings);
    appendMarkdownList(lines, "Visible claims", page.visible_claims);
    appendMarkdownList(lines, "Forms", page.forms);
    appendMarkdownList(lines, "Pricing", page.pricing_text);
    appendMarkdownList(lines, "Disclaimers", page.disclaimers);
    if (page.tracking_scripts && page.tracking_scripts.length > 0) {
      lines.push(`- Trackers: ${page.tracking_scripts.join(", ")}`);
    }
    if (page.fetch_error) lines.push(`- Fetch error: ${page.fetch_error}`);
  }

  lines.push("", "## Decision-Support Disclaimer", "", "AdLint is a preflight decision-support tool. It does not provide legal advice, guarantee platform approval, or make definitive statutory determinations.", "");
  return lines.join("\n");
}

function modelStatusLabel(model = {}) {
  const status = MODEL_STATUSES.includes(model.status) ? model.status : "disabled";
  const selectedModel = model.model || model.name;
  return selectedModel ? `${status} (${selectedModel})` : status;
}

function hasLandingLists(page) {
  return ["headings", "visible_claims", "forms", "pricing_text", "disclaimers", "tracking_scripts"].some(
    (key) => Array.isArray(page[key]) && page[key].length > 0,
  );
}

function appendMarkdownList(lines, label, values) {
  if (!values || values.length === 0) return;
  lines.push(`- ${label}:`);
  for (const value of values) lines.push(`  - ${value}`);
}

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return;
    } catch {
      // Fall back for browsers that expose Clipboard API but deny write access.
    }
  }

  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.left = "-9999px";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  textarea.remove();
}

function downloadFile(filename, type, contents) {
  const blob = new Blob([contents], { type });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
