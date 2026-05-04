# Policy Coverage Matrix

Validation status: OK
Total bundled policy count: 36
Total dataset row count: 329

## Dataset Row Counts

| Dataset | Rows | Coverage requirement |
| --- | ---: | --- |
| evals/datasets/real_cases_v1.jsonl | 75 | diagnostic only |
| evals/datasets/rule_benchmark_v1.jsonl | 200 | required complete |
| evals/datasets/seed_ads.jsonl | 54 | required complete |

## Coverage

| Policy ID | Category | Modules | Platform filters | Industry filters | seed_ads count | rule_benchmark_v1 count | real_cases_v1 count | Total count |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| before_after_claim | health_claims | health_claims | all | all | 2 | 4 | 4 | 10 |
| brand_safety_adult_content | brand_safety | brand_safety | all | all | 1 | 3 | 1 | 5 |
| brand_safety_controversial_content | brand_safety | brand_safety | all | all | 1 | 3 | 1 | 5 |
| brand_safety_misinformation | brand_safety | brand_safety | all | all | 3 | 5 | 2 | 10 |
| brand_safety_politics | brand_safety | brand_safety | all | all | 1 | 3 | 2 | 6 |
| brand_safety_sensitive_social_issue | brand_safety | brand_safety | all | all | 1 | 4 | 2 | 7 |
| brand_safety_tragedy_conflict | brand_safety | brand_safety | all | all | 1 | 4 | 1 | 6 |
| brand_safety_violence | brand_safety | brand_safety | all | all | 1 | 4 | 1 | 6 |
| ccpa_sensitive_health_indicator | privacy | privacy | all | health, wellness | 5 | 5 | 5 | 15 |
| fake_urgency_scarcity | misrepresentation | health_claims, platform | all | all | 1 | 1 | 6 | 8 |
| ftc_health_breach_notification_indicator | privacy | privacy | all | health, wellness | 4 | 4 | 3 | 11 |
| google_financial_claim_review | platform_policy | platform | google | finance | 2 | 14 | 2 | 18 |
| google_health_restricted_category | platform_policy | platform | google | health, wellness | 3 | 21 | 8 | 32 |
| google_misrepresentation_risk | platform_policy | platform | google | all | 5 | 15 | 3 | 23 |
| guaranteed_outcome | health_claims | health_claims | all | all | 8 | 27 | 6 | 41 |
| health_form_tracking_risk | privacy | privacy | all | health, wellness | 4 | 24 | 4 | 32 |
| hipaa_marketing_review | privacy | privacy | all | health | 4 | 12 | 4 | 20 |
| hipaa_tracking_technology_review | privacy | privacy | all | health | 1 | 1 | 4 | 6 |
| landing_page_offer_mismatch | landing_page | landing_page | all | all | 1 | 11 | 3 | 15 |
| linkedin_discrimination_risk | platform_policy | platform | linkedin | finance, saas, general | 1 | 6 | 3 | 10 |
| linkedin_professional_claim_review | platform_policy | platform | linkedin | saas, finance, creator, general | 3 | 13 | 2 | 18 |
| linkedin_sensitive_targeting | platform_policy | platform | linkedin | all | 2 | 11 | 3 | 16 |
| medical_cure_claim | health_claims | health_claims | all | all | 2 | 2 | 1 | 5 |
| meta_branded_content_disclosure | platform_policy | platform | meta | creator, wellness, health, finance | 1 | 5 | 0 | 6 |
| meta_health_appearance_results | platform_policy | platform | meta | health, wellness | 1 | 3 | 0 | 4 |
| meta_personal_attributes_finance | platform_policy | platform | meta | finance | 1 | 3 | 0 | 4 |
| meta_personal_attributes_health | platform_policy | platform | meta | health, wellness | 1 | 3 | 0 | 4 |
| missing_affiliate_or_sponsor_disclosure | disclosure | disclosure, platform | all | creator, wellness, health, finance | 5 | 19 | 6 | 30 |
| tiktok_disclosure_risk | platform_policy | platform | tiktok | creator, wellness, health | 4 | 14 | 5 | 23 |
| tiktok_misleading_content | platform_policy | platform | tiktok | all | 3 | 3 | 1 | 7 |
| tiktok_weight_management_claim | platform_policy | platform | tiktok | health, wellness | 2 | 12 | 2 | 16 |
| tracking_pixel_risk | privacy | privacy | all | health, wellness | 4 | 16 | 5 | 25 |
| unsupported_health_claim | health_claims | health_claims | all | health, wellness | 4 | 16 | 4 | 24 |
| washington_mhmda_indicator | privacy | privacy | all | health, wellness | 3 | 3 | 3 | 9 |
| weight_loss_claim | health_claims | health_claims, platform | all | health, wellness | 4 | 25 | 6 | 35 |
| wellness_claim_review | health_claims | health_claims | all | health, wellness | 2 | 14 | 6 | 22 |
