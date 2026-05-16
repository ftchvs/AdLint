# Competitive research: ad preflight and creative QA

Date: 2026-05-16

This note compares AdLint against current ad compliance, creative QA, and
open-source-adjacent tools. The goal is not to copy hosted compliance suites;
it is to identify small, local-first improvements that make AdLint more useful
before a marketer sends creative to a platform, legal reviewer, or paid-media
buyer.

## Comparable products

| Product | Positioning signal | Relevant gaps for AdLint |
| --- | --- | --- |
| [InspectAd](https://inspectad.com/) | Checks ad copy, images, videos, landing pages, and CSV imports against platform policies, with citations and rewrites. | Batch/CSV review, policy citations in reports, image/video architecture, marketer-facing "fix and re-check" flow. |
| [Veriad](https://www.veriad.com/) | AI marketing compliance with brand, internal, and industry criteria, secure uploads, detailed reports, DAM sync, and explicit false-positive positioning. | False-positive discipline, configurable criteria, report attachment/export, source notes for reviewers. |
| [PerformLine](https://performline.com/) | Enterprise marketing compliance across pre-publication review, monitoring, remediation, and audit-ready documentation. | Campaign archive/export, action history, defensible local reports, clearer reviewer workflow. |
| [FastGrow](https://www.fastgrow.ai/) | AI creative and compliance workspace for generation, risk review, repair, version management, reporting, and multi-platform asset management. | Batch client reports, launch-readiness summary, landing-page consistency, version/export framing. |
| [Adlyzerra](https://adlyzerra.com/) | Visual creative analysis for Facebook, TikTok, and Google with frame scanning, object labels, landing-page alignment, and CSV export. | Image/video placeholder architecture, visual metadata hooks, exportable summaries without storing raw creative by default. |
| [AdMeIn](https://admein.io/) | AdOps QA suite for VAST, HTML5, display tags, creative ZIPs, and video asset validation. | Open-source-adjacent QA checks for asset metadata, file specs, and future validators separate from policy claims. |

## Platform guidance signals

- [Meta Advertising Standards](https://transparency.meta.com/policies/ad-standards/)
  say ad review may include text, image, video, targeting information, and
  associated landing pages. Meta also emphasizes that review systems may miss
  issues and that ads remain subject to re-review.
- [Google Ads misrepresentation policy](https://support.google.com/adspolicy/answer/6020955?hl=en)
  emphasizes clear, honest information and calls out misleading business,
  pricing, affiliation, and claim patterns.
- [Google Ads destination requirements](https://support.google.com/adspolicy/answer/6368661?hl=en)
  cover functional destinations, crawlability, destination mismatch,
  frustrating navigation, direct-download links, and low-value bridge pages.
- [TikTok ad review guidance](https://ads.us.tiktok.com/help/article/advertising-on-tiktok-first-things-to-note?lang=en)
  says review considers captions/text, images, audio, target market, age
  group, landing-page consistency, and landing-page functionality.
- [TikTok misleading and false content policy](https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content?lang=en)
  explicitly covers exaggerated results, inconsistent ad/landing-page
  information, clickbait UI, before-and-after comparisons, AIGC labeling, and
  identity misuse.

## AdLint comparison

AdLint already has a strong local-first core: deterministic YAML policies, CLI,
FastAPI, a local Web UI, rewrite suggestions, landing-page extraction,
metadata-only storage, eval datasets, policy coverage checks, and local model
review that is off by default. That makes it credible as an open-source
preflight tool, especially where hosted tools are too opaque or risky for raw
creative.

The strongest gaps are practical workflow gaps rather than broad AI claims:

- Batch review: source products treat CSV/import workflows as table stakes for
  agencies and paid-media teams.
- Report clarity: reports need a marketer-facing launch-readiness summary,
  prioritized fixes, and source notes, not only policy IDs.
- Policy source notes: every platform-policy hit should show where the rule
  came from or which public guidance inspired it.
- Landing-page consistency: current mismatch detection exists, but platform
  guidance supports more explicit promotion, price, discount, and disclaimer
  consistency checks.
- Creative assets: image/video support should start as a private-by-default
  architecture for metadata and future validators, not as unverified visual AI
  claims.
- Archive/export: local campaign exports should preserve decisions, policy IDs,
  source notes, and report paths without uploading or mutating ad accounts.
- False-positive discipline: review-only signals should stay review labels, and
  docs should avoid claiming approval, legal compliance, or production-grade
  model accuracy.

## Implementation priority

1. Add batch CSV review with local summary export and no hosted data flow.
2. Add policy source notes to policies, hits, and Markdown reports.
3. Add a marketer-facing report summary with prioritized fixes and launch
   readiness.
4. Tighten landing-page consistency checks for promotions, pricing, discounts,
   and missing disclaimers.
5. Add a minimal creative asset metadata schema for future image/video checks
   while keeping raw asset storage out of scope by default.
