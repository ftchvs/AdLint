const form = document.querySelector("#review-form");
const emptyState = document.querySelector("#status-empty");
const loadingState = document.querySelector("#status-loading");
const errorState = document.querySelector("#status-error");
const resultContent = document.querySelector("#result-content");
const exportActions = document.querySelector("#export-actions");
const copyJsonButton = document.querySelector("#copy-json");
const exportJsonButton = document.querySelector("#export-json");
const exportMarkdownButton = document.querySelector("#export-markdown");

let lastResult = null;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  setState("loading");
  setSubmitting(true);

  try {
    const response = await fetch("/analyze", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(buildPayload(new FormData(form))),
    });

    if (!response.ok) {
      const detail = await response.text();
      throw new Error(detail || `Request failed with status ${response.status}`);
    }

    lastResult = await response.json();
    renderResult(lastResult);
    setState("result");
  } catch (error) {
    lastResult = null;
    renderError(error);
    setState("error");
  } finally {
    setSubmitting(false);
  }
});

form.addEventListener("reset", () => {
  window.setTimeout(() => {
    lastResult = null;
    resultContent.innerHTML = "";
    resultContent.classList.remove("has-result");
    exportActions.hidden = true;
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

function buildPayload(formData) {
  const payload = {
    platform: stringValue(formData, "platform", "google"),
    industry: stringValue(formData, "industry", "general"),
    headline: stringValue(formData, "headline", ""),
    body: stringValue(formData, "body", ""),
    cta: stringValue(formData, "cta", ""),
    policy_modules: formData.getAll("policy_modules").map(String),
  };

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
  button.textContent = isSubmitting ? "Analyzing" : "Analyze";
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
}

function renderError(error) {
  const message = error instanceof Error ? error.message : "Unable to analyze this ad.";
  errorState.innerHTML = `
    <p class="state-title">Analysis failed</p>
    <p>${escapeHtml(message)}</p>
  `;
  resultContent.innerHTML = "";
}

function renderResult(result) {
  resultContent.innerHTML = `
    ${renderSummary(result)}
    ${renderListSection("Recommended actions", result.recommended_actions)}
    ${renderPolicyHits(result.policy_hits)}
    ${renderRewrites(result.safer_rewrites)}
    ${renderLandingPage(result.landing_page)}
    <section class="result-section">
      <h3>Raw JSON</h3>
      <pre class="raw-json">${escapeHtml(JSON.stringify(result, null, 2))}</pre>
    </section>
  `;

  resultContent.querySelectorAll("[data-copy-rewrite]").forEach((button) => {
    button.addEventListener("click", () => {
      const index = Number(button.getAttribute("data-copy-rewrite"));
      const rewrite = result.safer_rewrites[index];
      copyText(formatRewrite(rewrite));
    });
  });
}

function renderSummary(result) {
  const decisionClass = String(result.decision || "").replace("_", "-");
  return `
    <section class="summary-strip" aria-label="Review summary">
      <div class="metric">
        <span class="metric-label">Decision</span>
        <span class="metric-value decision ${escapeHtml(decisionClass)}">${escapeHtml(result.decision || "unknown")}</span>
      </div>
      <div class="metric">
        <span class="metric-label">Risk score</span>
        <span class="metric-value">${formatRiskScore(result.risk_score)}</span>
      </div>
      <div class="metric">
        <span class="metric-label">Requires review</span>
        <span class="metric-value">${result.requires_review ? "Yes" : "No"}</span>
      </div>
    </section>
    <section class="result-section">
      <h3>Enabled modules</h3>
      <div class="hit-meta">${(result.enabled_modules || []).map((module) => `<span class="tag">${escapeHtml(module)}</span>`).join("")}</div>
    </section>
  `;
}

function renderListSection(title, values) {
  if (!values || values.length === 0) {
    return `
      <section class="result-section">
        <h3>${escapeHtml(title)}</h3>
        <p class="muted">No items.</p>
      </section>
    `;
  }

  return `
    <section class="result-section">
      <h3>${escapeHtml(title)}</h3>
      <ul>${values.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul>
    </section>
  `;
}

function renderPolicyHits(hits) {
  if (!hits || hits.length === 0) {
    return `
      <section class="result-section">
        <h3>Policy hits</h3>
        <p class="muted">No policy hits detected.</p>
      </section>
    `;
  }

  return `
    <section class="result-section">
      <h3>Policy hits</h3>
      ${hits.map(renderPolicyHit).join("")}
    </section>
  `;
}

function renderPolicyHit(hit) {
  const evidence = hit.evidence || [];
  return `
    <article class="hit-row">
      <div class="hit-meta">
        <span class="tag">${escapeHtml(hit.policy_id || "policy")}</span>
        <span class="tag ${escapeHtml(hit.severity || "")}">${escapeHtml(hit.severity || "unknown")}</span>
        <span class="tag">${escapeHtml(hit.category || "uncategorized")}</span>
        ${hit.requires_review ? '<span class="tag medium">requires_review</span>' : ""}
      </div>
      ${hit.description ? `<p class="muted">${escapeHtml(hit.description)}</p>` : ""}
      <p><strong>Action:</strong> ${escapeHtml(hit.recommended_action || "Review the finding.")}</p>
      <div class="evidence-list">
        ${evidence.map((item) => `
          <div class="evidence-item">
            <span class="evidence-source">${escapeHtml(item.source || "source")}</span>
            <span>${escapeHtml(item.text || "")}</span>
          </div>
        `).join("")}
      </div>
    </article>
  `;
}

function renderRewrites(rewrites) {
  if (!rewrites || rewrites.length === 0) {
    return `
      <section class="result-section">
        <h3>Safer rewrites</h3>
        <p class="muted">No rewrite suggested.</p>
      </section>
    `;
  }

  return `
    <section class="result-section">
      <h3>Safer rewrites</h3>
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
        <h3>Landing page findings</h3>
        <p class="muted">No landing page supplied.</p>
      </section>
    `;
  }

  return `
    <section class="result-section">
      <h3>Landing page findings</h3>
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

function formatRiskScore(score) {
  if (typeof score !== "number") return "0.00";
  return score.toFixed(2);
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

  lines.push("", "## Recommended Actions", "");
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

  lines.push("", "## Decision-Support Disclaimer", "", "AdLint is a preflight decision-support tool. It does not provide legal advice, guarantee platform approval, or make definitive statutory violation determinations.", "");
  return lines.join("\n");
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
    await navigator.clipboard.writeText(text);
    return;
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
