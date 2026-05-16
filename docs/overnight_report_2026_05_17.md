# Overnight report: competitive evolution

Date: 2026-05-17
Branch: `codex/overnight-competitive-evolution`

## Research links

- [InspectAd](https://inspectad.com/)
- [Veriad](https://www.veriad.com/)
- [PerformLine](https://performline.com/)
- [FastGrow](https://www.fastgrow.ai/)
- [Adlyzerra](https://adlyzerra.com/)
- [AdMeIn](https://admein.io/)
- [Meta Advertising Standards](https://transparency.meta.com/policies/ad-standards/)
- [Google Ads misrepresentation policy](https://support.google.com/adspolicy/answer/6020955?hl=en)
- [Google Ads destination requirements](https://support.google.com/adspolicy/answer/6368661?hl=en)
- [Google Ads healthcare policy](https://support.google.com/adspolicy/answer/176031?hl=en)
- [Google Ads financial products policy](https://support.google.com/adspolicy/answer/2464998?hl=en)
- [TikTok ad review guidance](https://ads.us.tiktok.com/help/article/advertising-on-tiktok-first-things-to-note?lang=en)
- [TikTok misleading and false content policy](https://ads.tiktok.com/help/article/tiktok-ads-policy-misleading-and-false-content?lang=en)
- [LinkedIn Ads policies](https://www.linkedin.com/legal/ads-policy)
- [IAB Content Taxonomy](https://www.iab.com/guidelines/taxonomy)

See `docs/competitive_research_2026_05_16.md` for the concise comparison.

## Shipped changes

- Added competitor/source research that positions AdLint as a local-first
  preflight tool, not a hosted approval oracle.
- Added private CSV batch review with local archive output and summaries that
  omit raw ad copy, landing HTML, and creative asset metadata by default.
- Added policy source notes to policy hits and Markdown reports, then completed
  source metadata coverage across built-in policies.
- Added marketer-facing launch readiness summaries and prioritized fixes.
- Tightened landing-page consistency checks for material offer terms including
  free trials, discounts, promo codes, limited-time offers, and percent-off copy.
- Added metadata-only creative asset placeholders. Supplied OCR/text overlay,
  transcript, alt text, and labels run through existing text rules, while raw
  media paths serialize only as basenames and storage remains metadata-only.
- Added focused docs, examples, and evals for batch review, landing-page offer
  consistency, and creative asset metadata.

## Commits

- `428f723 docs: add competitive research note`
- `8593988 docs: add competitive research notes`
- `d4e91d7 feat: add private CSV batch review`
- `29fbb99 feat: include policy source notes in reports`
- `a73aa9f feat: add batch archive summaries`
- `6113c67 feat: complete policy source coverage`
- `0c1f185 docs: document batch CSV workflow`
- `abd5e38 feat: add launch readiness report summary`
- `c2aa66f fix: tighten landing page offer consistency checks`
- `393053b feat: add creative asset metadata placeholders`
- `8745fdc feat: add metadata-only creative asset review`

## Verification

- `make test`: passed, `212 passed`
- `make eval`: passed, seed eval `58` rows, decision accuracy `1.0`
- `make benchmark`: passed, benchmark eval `213` rows, decision accuracy `1.0`
- `make policy-coverage-validate`: passed, `40` policies and `346` rows
- `make pr-preflight`: passed
- `make landing-page-consistency`: passed, `4` rows, decision accuracy `1.0`
- `make creative-assets-eval`: passed, `2` rows, decision accuracy `1.0`

No verification blockers.

## Next recommended issues

1. Add a small "review packet" export that bundles batch summary, per-row
   Markdown reports, policy source links, and a manifest for local handoff.
2. Add optional local-only asset validators for dimensions, duration, file size,
   and declared MIME type before any OCR/frame-analysis work.
3. Add a false-positive review dataset with near-miss offer language, benign
   health-adjacent copy, and platform-specific review labels to keep sensitivity
   changes disciplined.
