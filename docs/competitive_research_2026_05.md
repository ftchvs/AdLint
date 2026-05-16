# Competitive research notes, May 2026

Reviewed on 2026-05-16. This note is a concise source list and product-gap
comparison for AdLint as a local-first, open-source preflight tool. It is not a
market-size study.

## Comparable products and signals

| Product/source | Relevant public claims | AdLint implication |
| --- | --- | --- |
| InspectAd AI | Checks ad copy, images, videos, landing pages, and CSV imports across Meta, TikTok, Google, and LinkedIn. Reports include policy citations and compliant rewrites. Source: <https://inspectad.com/> | AdLint already covers copy, landing-page extraction, rewrites, and multi-platform rules. Batch CSV review and source-linked findings are the obvious open-source gaps. |
| Veriad | AI compliance reports, custom brand/internal/industry criteria, DAM sync, and low false-positive positioning. Source: <https://www.veriad.com/> | Keep false-positive discipline explicit: route ambiguous cases to `needs_review`, document rule scope, and test every policy expansion. |
| PerformLine | Enterprise pre-publication review, continuous monitoring, workflow/remediation, and audit-ready archives across web, social, email, calls, messages, docs, and partner channels. Source: <https://performline.com/> | AdLint should not copy enterprise monitoring, but can offer local campaign archives and exportable reports for pre-publication review. |
| Adlyzerra | Visual creative analysis for Facebook, TikTok, and Google using Vision/Video AI, safety scores, object labels, video frame scans, landing-page keyword alignment, and CSV export. Source: <https://adlyzerra.com/> | Add image/video placeholders without unverified ML claims: accept asset metadata now, keep raw files private, and design future OCR/frame findings behind explicit opt-in. |
| FastGrow | Creative/compliance workspace for asset generation, risk review, repair, version management, batch review, white-label reports, and multi-platform policy coverage. Source: <https://www.fastgrow.ai/> | Batch review, marketer-facing summaries, version/export history, and platform-specific source notes matter more than broad model claims. |
| Google Ads policy center | Google emphasizes clear, professional ads and destinations, legal responsibility, restricted categories, destination quality, and personalized-ad targeting restrictions for sensitive interests. Sources: <https://support.google.com/adspolicy/answer/6008942?hl=en>, <https://support.google.com/adspolicy/answer/143465?hl=en> | Policy hits should include source notes where possible, especially destination quality, misrepresentation, and sensitive targeting. |
| TikTok misleading and false content policy | TikTok calls out misleading claims, deceptive click elements, before/after comparisons, and AIGC labeling for significantly modified media. Source: <https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content?lang=en> | AdLint should keep TikTok before/after and misleading-claim checks conservative, and introduce media support as architecture before claiming automated visual review. |
| Meta Advertising Standards | Official policy hub: <https://transparency.meta.com/policies/ad-standards/>. Current AdLint scope is documented in `docs/meta_ads_scope.md`. | Keep Meta rules scoped and source-linked. Add exact platform source notes in reports without suggesting approval guarantees. |

## Current AdLint positioning

AdLint is strongest where commercial products are weakest for open-source
users: it is local-first, auditable, deterministic, and private by default. The
project should avoid hosted data collection, ad-account mutation, legal approval
guarantees, and unsupported "AI approval" claims.

## Highest-leverage gaps

1. Batch CSV preflight for media buyers and agencies.
2. Marketer-facing summary exports that can be attached to a launch review.
3. Policy source notes directly in JSON and Markdown reports.
4. Campaign archive/export that stores summary metadata without raw creative by
   default.
5. Image/video placeholder architecture with explicit non-goals until OCR,
   audio, and frame-level checks are implemented and evaluated.
6. More landing-page consistency checks, especially destination mismatch and
   material-term visibility.
7. Continued false-positive discipline through narrow rules, review labels, and
   eval rows for every behavior change.

