# Policy Design

AdLint policies live in version-controlled YAML under `adlint/policies/`.
Each file contains a `policies` list. A policy maps simple deterministic
signals to a policy ID, severity, category, recommended action, optional
module/platform/industry filters, and optional IAB-style suitability metadata.
Built-in policies should also include source metadata when there is a stable
public reference. Source links are report context, not proof that a finding is
a definitive violation.

Minimal policy shape:

```yaml
policies:
  - id: unsupported_health_claim
    severity: high
    category: health_claims
    modules: [health_claims]
    industries: [health, wellness]
    signals:
      - clinically proven
      - guaranteed
    source_url: https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance
    source_note: FTC Health Products Compliance Guidance
    recommended_action: Remove or qualify the claim and provide substantiation.
    rewrite_strategy: qualify_claim
```

The rule engine matches signals against ad fields and extracted landing-page
fields. A `*` in a signal is treated as a bounded wildcard, which supports
patterns such as `lose * pounds` without requiring policy authors to write raw
regular expressions.

## Modules

The bundled MVP modules are:

- `health_claims`
- `platform`
- `privacy`
- `brand_safety`
- `disclosure`
- `landing_page`

Users can restrict evaluation with `policy_modules` in the scan config or load
custom YAML with `adlint scan config.json --policy-path path/to/policies`.

## Platform policy modules

Platform modules use `platforms` filters so a Google, Meta, TikTok, or
LinkedIn-specific policy does not fire on another ad network. Keep platform
policy IDs narrow enough to explain the exact review concern.

The bundled platform files are:

- `platform_google_ads.yml`: Google health, financial-claim, and
  misrepresentation checks.
- `platform_meta_ads.yml`: Meta personal-attribute health and finance checks,
  health or appearance result framing, and branded-content disclosure checks.
- `platform_tiktok_ads.yml`: TikTok weight-management, misleading-content, and
  disclosure checks.
- `platform_linkedin_ads.yml`: LinkedIn sensitive targeting, discrimination,
  and professional-claim checks.

## Review Labels

HIPAA, FTC Health Breach Notification Rule, Washington My Health My Data Act,
CCPA, and tracking-pixel findings are labeled `requires_review`. AdLint does
not make definitive legal determinations.

## Source notes

`source_url` and `source_note` are optional YAML fields. When present, they are
copied into JSON output under `policy_source` and rendered in Markdown reports
as the finding's policy source. Prefer official policy, regulator, or standards
references. Do not use source notes to imply that AdLint guarantees platform
approval or legal compliance.
