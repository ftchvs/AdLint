# Policy Coverage Matrix

Validation status: OK
Total bundled policy count: 32
Total dataset row count: 263

## Dataset Row Counts

| Dataset | Rows | Coverage requirement |
| --- | ---: | --- |
| evals/datasets/real_cases_v1.jsonl | 13 | diagnostic only |
| evals/datasets/rule_benchmark_v1.jsonl | 200 | required complete |
| evals/datasets/seed_ads.jsonl | 50 | required complete |

## Coverage

| Policy ID | Category | Modules | Platform filters | Industry filters | seed_ads count | rule_benchmark_v1 count | real_cases_v1 count | Total count |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| before_after_claim | health_claims | health_claims | all | all | 1 | 1 | 1 | 3 |
| brand_safety_adult_content | brand_safety | brand_safety | all | all | 1 | 3 | 0 | 4 |
| brand_safety_controversial_content | brand_safety | brand_safety | all | all | 1 | 3 | 0 | 4 |
| brand_safety_misinformation | brand_safety | brand_safety | all | all | 3 | 5 | 2 | 10 |
| brand_safety_politics | brand_safety | brand_safety | all | all | 1 | 3 | 0 | 4 |
| brand_safety_sensitive_social_issue | brand_safety | brand_safety | all | all | 1 | 4 | 1 | 6 |
| brand_safety_tragedy_conflict | brand_safety | brand_safety | all | all | 1 | 4 | 0 | 5 |
| brand_safety_violence | brand_safety | brand_safety | all | all | 1 | 4 | 0 | 5 |
| ccpa_sensitive_health_indicator | privacy | privacy | all | health, wellness | 5 | 5 | 4 | 14 |
| fake_urgency_scarcity | misrepresentation | health_claims, platform | all | all | 1 | 1 | 2 | 4 |
| ftc_health_breach_notification_indicator | privacy | privacy | all | health, wellness | 4 | 4 | 2 | 10 |
| google_financial_claim_review | platform_policy | platform | google | finance | 2 | 14 | 0 | 16 |
| google_health_restricted_category | platform_policy | platform | google | health, wellness | 3 | 21 | 7 | 31 |
| google_misrepresentation_risk | platform_policy | platform | google | all | 5 | 15 | 2 | 22 |
| guaranteed_outcome | health_claims | health_claims | all | all | 8 | 27 | 4 | 39 |
| health_form_tracking_risk | privacy | privacy | all | health, wellness | 4 | 24 | 3 | 31 |
| hipaa_marketing_review | privacy | privacy | all | health | 4 | 12 | 3 | 19 |
| hipaa_tracking_technology_review | privacy | privacy | all | health | 1 | 1 | 3 | 5 |
| landing_page_offer_mismatch | landing_page | landing_page | all | all | 1 | 11 | 0 | 12 |
| linkedin_discrimination_risk | platform_policy | platform | linkedin | finance, saas, general | 1 | 6 | 1 | 8 |
| linkedin_professional_claim_review | platform_policy | platform | linkedin | saas, finance, creator, general | 3 | 13 | 1 | 17 |
| linkedin_sensitive_targeting | platform_policy | platform | linkedin | all | 2 | 11 | 1 | 14 |
| medical_cure_claim | health_claims | health_claims | all | all | 2 | 2 | 1 | 5 |
| missing_affiliate_or_sponsor_disclosure | disclosure | disclosure, platform | all | creator, wellness, health, finance | 4 | 14 | 0 | 18 |
| tiktok_disclosure_risk | platform_policy | platform | tiktok | creator, wellness, health | 4 | 14 | 0 | 18 |
| tiktok_misleading_content | platform_policy | platform | tiktok | all | 3 | 3 | 1 | 7 |
| tiktok_weight_management_claim | platform_policy | platform | tiktok | health, wellness | 2 | 12 | 1 | 15 |
| tracking_pixel_risk | privacy | privacy | all | health, wellness | 4 | 16 | 4 | 24 |
| unsupported_health_claim | health_claims | health_claims | all | health, wellness | 3 | 13 | 4 | 20 |
| washington_mhmda_indicator | privacy | privacy | all | health, wellness | 3 | 3 | 2 | 8 |
| weight_loss_claim | health_claims | health_claims, platform | all | health, wellness | 3 | 23 | 5 | 31 |
| wellness_claim_review | health_claims | health_claims | all | health, wellness | 2 | 14 | 1 | 17 |
