# Meta Ads policy scope

AdLint's Meta module is an initial, conservative preflight surface for campaign
review. It is not a complete implementation of Meta's Advertising Standards and
it does not guarantee Meta approval.

## What the current module covers

The bundled `platform_meta_ads.yml` rules focus on high-signal patterns that are
useful before a growth team sends creative to review:

- **Selected personal attributes**: health/body and vulnerable-finance wording that
  can imply knowledge of the viewer's condition or status. The current module
  does not yet cover every Meta personal-attribute class such as religion, race,
  disability, gender identity, sexual orientation, or trade-union membership.
- **Health and appearance results**: transformation, weight-loss, and negative
  self-perception framing.
- **Health/wellness age-targeting review**: weight-loss, cosmetic, sexual-health,
  and reproductive-health terms that should trigger human review before launch.
- **Financial services authorization review**: credit, loan, insurance,
  investment, refinance, and cash-advance offers that may require 18+ targeting,
  disclosures, licensing, or authorization checks.
- **Special Ad Category review**: housing, employment, and financial-products
  contexts that may require Meta campaign-level category settings and targeting
  limits.
- **Private information requests**: ad copy asking for health, financial, or
  similarly private information.
- **Branded content disclosure**: sponsorship, affiliate, promo-code, and paid
  partnership language.

## Source references

Use these official Meta references when extending the module:

- Meta Advertising Standards overview:
  <https://transparency.meta.com/policies/ad-standards/>
- Financial and Insurance Products and Services:
  <https://transparency.meta.com/policies/ad-standards/restricted-goods-services/financial-services/>
- Discriminatory Practices and Special Ad Category context:
  <https://transparency.meta.com/policies/ad-standards/unacceptable-content/discriminatory-practices>
- Marketing API Special Ad Categories:
  <https://developers.facebook.com/docs/marketing-api/audiences/special-ad-category/>
- Branded Content Policies:
  <https://www.facebook.com/business/help/221149188908254>

## Deliberate limitations

- Rules are deterministic phrase and pattern checks, not a legal or platform
  approval model.
- Synthetic benchmark rows are regression coverage, not production accuracy
  claims.
- The module intentionally routes ambiguous regulated-category copy to
  `needs_review` rather than trying to decide eligibility automatically.
- Campaign-level fields such as actual Meta objective, placement, age targeting,
  country targeting, and `special_ad_categories` are not modeled yet.
- Landing-page mismatch is currently handled by AdLint's generic landing-page
  module rather than a Meta-specific policy id.

## Good next contributions

- Add public-source, paraphrased Meta Ad Library and Meta policy examples.
- Add explicit campaign metadata fields for age range, country, and special ad
  category selection, then make review rules conditional on those fields.
- Add Meta-specific landing-page and destination-quality policy ids beyond the generic landing-page mismatch rule.
- Split regulated finance review into offer, education, and brand-awareness
  subcases with stronger false-positive fixtures.
