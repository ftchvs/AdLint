from __future__ import annotations

import json
from pathlib import Path
from typing import Any


OUTPUT_PATH = Path(__file__).resolve().parent / "datasets" / "real_cases_v1.jsonl"
ACCESSED_AT = "2026-05-02"


def main() -> int:
    rows = build_rows()
    OUTPUT_PATH.write_text(
        "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} rows to {OUTPUT_PATH}")
    return 0


def build_rows() -> list[dict[str, Any]]:
    rows = approved_rows() + needs_review_rows() + high_risk_rows()
    decisions = [row["expected_decision"] for row in rows]
    assert decisions.count("approved") == 25
    assert decisions.count("needs_review") == 25
    assert decisions.count("high_risk") == 25
    assert len({row["id"] for row in rows}) == 75
    return rows


def approved_rows() -> list[dict[str, Any]]:
    cases = [
        ("slack_team_updates_control", "Slack", "Slack product page", "https://slack.com/", "linkedin", "saas", "Organize team launch updates", "Create channels for project notes, approvals, and weekly planning.", "See workspace tools"),
        ("salesforce_crm_pipeline_control", "Salesforce", "Salesforce CRM page", "https://www.salesforce.com/products/sales-cloud/", "google", "saas", "Manage customer pipeline notes", "Give sales teams one place to track tasks, contacts, and next steps.", "View CRM"),
        ("hubspot_crm_onboarding_control", "HubSpot", "HubSpot CRM product page", "https://www.hubspot.com/products/crm", "linkedin", "saas", "Start a simple contact workspace", "Organize customer records and handoffs across your growing team.", "Explore CRM"),
        ("asana_project_templates_control", "Asana", "Asana product page", "https://asana.com/", "google", "saas", "Plan product work in one board", "Use templates, tasks, and project views to keep launches coordinated.", "Browse templates"),
        ("notion_docs_workspace_control", "Notion", "Notion product page", "https://www.notion.so/product", "linkedin", "saas", "Centralize docs and planning", "Bring team notes, process pages, and project lists into one workspace.", "See examples"),
        ("figma_design_review_control", "Figma", "Figma design product page", "https://www.figma.com/", "google", "saas", "Review designs with your team", "Collect comments, align on layouts, and prepare handoff notes.", "Open design tools"),
        ("jira_issue_tracking_control", "Atlassian", "Jira product page", "https://www.atlassian.com/software/jira", "linkedin", "saas", "Track engineering work clearly", "Prioritize requests, plan releases, and follow progress across teams.", "Explore Jira"),
        ("zoom_meeting_notes_control", "Zoom", "Zoom product page", "https://www.zoom.com/", "google", "saas", "Run clearer team meetings", "Host calls, share agendas, and follow up with organized notes.", "Start a meeting"),
        ("dropbox_file_sharing_control", "Dropbox", "Dropbox product page", "https://www.dropbox.com/", "linkedin", "saas", "Share campaign files securely", "Keep creative drafts and launch assets available to approved teammates.", "View plans"),
        ("calendly_scheduling_control", "Calendly", "Calendly product page", "https://calendly.com/", "google", "saas", "Simplify customer scheduling", "Let visitors choose available times and receive organized meeting reminders.", "Try scheduling"),
        ("mailchimp_newsletter_control", "Mailchimp", "Mailchimp marketing page", "https://mailchimp.com/", "google", "general", "Send a monthly product newsletter", "Share company updates, product tips, and event invitations with subscribers.", "Create a newsletter"),
        ("shopify_store_setup_control", "Shopify", "Shopify product page", "https://www.shopify.com/", "google", "general", "Launch an online product catalog", "Build pages, manage orders, and organize store operations from one dashboard.", "Start store setup"),
        ("stripe_payments_control", "Stripe", "Stripe payments page", "https://stripe.com/payments", "linkedin", "finance", "Accept online payments", "Set up payment forms, invoices, and reporting tools for your business.", "Explore payments"),
        ("canva_brand_kit_control", "Canva", "Canva product page", "https://www.canva.com/", "google", "general", "Design brand assets faster", "Create social posts, presentations, and launch graphics from shared templates.", "Start designing"),
        ("miro_workshop_board_control", "Miro", "Miro product page", "https://miro.com/", "linkedin", "saas", "Map workshop ideas visually", "Collect sticky notes, diagrams, and team feedback in a shared board.", "Open board"),
        ("buffer_social_planning_control", "Buffer", "Buffer product page", "https://buffer.com/", "google", "general", "Plan social content calendars", "Draft posts, organize approvals, and review publishing schedules.", "Plan posts"),
        ("hootsuite_social_management_control", "Hootsuite", "Hootsuite product page", "https://www.hootsuite.com/", "linkedin", "general", "Coordinate social publishing", "Manage brand channels, team workflows, and reporting calendars.", "View platform"),
        ("grammarly_business_control", "Grammarly", "Grammarly Business page", "https://www.grammarly.com/business", "google", "saas", "Write clearer team messages", "Help teams draft concise emails, documents, and support replies.", "Improve writing"),
        ("intercom_support_inbox_control", "Intercom", "Intercom product page", "https://www.intercom.com/", "linkedin", "saas", "Organize customer conversations", "Route support questions, collect context, and keep replies consistent.", "Explore inbox"),
        ("zendesk_help_center_control", "Zendesk", "Zendesk product page", "https://www.zendesk.com/", "google", "saas", "Build a helpful support center", "Publish answers, manage tickets, and track customer service workflows.", "View support tools"),
        ("airtable_operations_tracker_control", "Airtable", "Airtable product page", "https://www.airtable.com/", "linkedin", "saas", "Track operations in flexible tables", "Coordinate vendors, project status, and content calendars with your team.", "Browse templates"),
        ("quickbooks_expense_dashboard_control", "Intuit QuickBooks", "QuickBooks product page", "https://quickbooks.intuit.com/", "google", "finance", "Organize business expenses", "Track invoices, payments, and reports with accounting tools for teams.", "View accounting tools"),
        ("docusign_agreement_workflow_control", "DocuSign", "DocuSign product page", "https://www.docusign.com/", "linkedin", "saas", "Prepare agreements for signature", "Send documents, collect signatures, and store completed agreements.", "Start agreement"),
        ("surveymonkey_feedback_control", "SurveyMonkey", "SurveyMonkey product page", "https://www.surveymonkey.com/", "google", "general", "Collect customer feedback", "Create surveys to learn about product experience and service quality.", "Build survey"),
        ("typeform_intake_form_control", "Typeform", "Typeform product page", "https://www.typeform.com/", "linkedin", "saas", "Create friendly intake forms", "Gather preferences, requests, and event details through branded forms.", "Create form"),
    ]
    return [
        _row(
            row_id=row_id,
            source_type="public_marketing_example",
            source_tier="tier_3_public_marketing_example",
            source_org=org,
            source_title=title,
            source_url=url,
            label_basis="Public product or marketing page paraphrased into a policy-safe control row.",
            label_confidence="medium",
            label_rationale="The row avoids regulated claims, sensitive targeting, disclosure claims, and landing-page mismatch signals.",
            policy_areas=["control"],
            copyright_status="paraphrased",
            outcome_source="public_marketing_example",
            expected_decision="approved",
            expected_policy_ids=[],
            platform=platform,
            industry=industry,
            headline=headline,
            body=body,
            cta=cta,
            landing_page_html=_simple_page(headline, body),
        )
        for row_id, org, title, url, platform, industry, headline, body, cta in cases
    ]


def needs_review_rows() -> list[dict[str, Any]]:
    cases = [
        ("ftc_wellness_science_backed_sleep_review", "FTC", "Health Products Compliance Guidance", "https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance", "google", "wellness", "Science-backed bedtime routine", "A gentle evening program with science-backed tips for better sleep habits.", "Join routine", ["wellness_claim_review"], ["health_claims"], "FTC guidance supports review of evidence-framed health and wellness claims."),
        ("ftc_wellness_evidence_based_hydration_review", "FTC", "Health Products Compliance Guidance", "https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance", "google", "wellness", "Evidence-based hydration reminders", "Daily wellness reminders use evidence-based planning to support hydration habits.", "Get reminders", ["wellness_claim_review"], ["health_claims"], "Evidence framing requires substantiation review without making a high-risk disease claim."),
        ("ftc_wellness_backed_by_science_mindfulness_review", "FTC", "Health Products Compliance Guidance", "https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance", "tiktok", "wellness", "Backed by science mindfulness prompts", "Short prompts help people build a calmer routine, backed by science and habit research.", "Try prompts", ["wellness_claim_review"], ["health_claims"], "The claim is wellness-oriented and evidence-framed, so reviewer substantiation is appropriate."),
        ("ftc_wellness_science_backed_nutrition_review", "FTC", "Health Products Compliance Guidance", "https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance", "google", "wellness", "Science-backed meal planning ideas", "Weekly guides share science-backed ways to organize grocery lists and meals.", "Read guide", ["wellness_claim_review"], ["health_claims"], "Science-backed wellness language should be reviewed for supporting evidence."),
        ("ftc_wellness_evidence_based_recovery_review", "FTC", "Health Products Compliance Guidance", "https://www.ftc.gov/business-guidance/resources/health-products-compliance-guidance", "linkedin", "wellness", "Evidence-based recovery checklist", "Help teams share evidence-based stretching and recovery reminders after busy workdays.", "Download checklist", ["wellness_claim_review"], ["health_claims"], "The row uses evidence framing in a wellness context without absolute outcome language."),
        ("asa_before_after_skin_routine_review", "ASA/CAP", "CAP guidance on before and after photos", "https://www.asa.org.uk/advice-online/use-of-before-and-after-photos.html", "google", "wellness", "Before and after routine gallery", "See the difference in a skincare routine gallery with customer before and after examples.", "View gallery", ["before_after_claim"], ["health_claims"], "Before-and-after framing is review-worthy even where the copy avoids absolute outcomes."),
        ("asa_transformation_photo_fitness_review", "ASA/CAP", "CAP guidance on before and after photos", "https://www.asa.org.uk/advice-online/use-of-before-and-after-photos.html", "tiktok", "wellness", "Transformation photo class recap", "Watch transformation photo stories from members who joined a weekly movement class.", "Watch recap", ["before_after_claim"], ["health_claims"], "Transformation-photo language can imply atypical results and should be reviewed."),
        ("asa_dramatic_results_hair_review", "ASA/CAP", "CAP guidance on before and after photos", "https://www.asa.org.uk/advice-online/use-of-before-and-after-photos.html", "google", "wellness", "Dramatic results styling diary", "A styling diary shows dramatic results after people changed their daily hair routine.", "Read diary", ["before_after_claim"], ["health_claims"], "The row isolates before-after result framing for reviewer context."),
        ("ftc_last_chance_membership_review", "FTC", "Advertising and Marketing on the Internet", "https://www.ftc.gov/business-guidance/resources/advertising-marketing-internet-rules-road", "google", "general", "Last chance for member pricing", "Last chance to join the community plan before the public price changes next week.", "Join plan", ["fake_urgency_scarcity"], ["misrepresentation"], "Scarcity pressure is present and should be checked for truthfulness."),
        ("ftc_act_now_event_review", "FTC", "Advertising and Marketing on the Internet", "https://www.ftc.gov/business-guidance/resources/advertising-marketing-internet-rules-road", "linkedin", "general", "Act now for workshop access", "Act now to reserve workshop access while the team finalizes the attendee list.", "Reserve seat", ["fake_urgency_scarcity"], ["misrepresentation"], "Urgency language should be reviewed for accurate availability."),
        ("ftc_limited_spots_webinar_review", "FTC", "Advertising and Marketing on the Internet", "https://www.ftc.gov/business-guidance/resources/advertising-marketing-internet-rules-road", "google", "saas", "Limited spots for onboarding webinar", "Limited spots are available for a live onboarding webinar with the product team.", "Save seat", ["fake_urgency_scarcity"], ["misrepresentation"], "Limited-space copy needs reviewer confirmation that the constraint is real."),
        ("ftc_only_left_inventory_review", "FTC", "Advertising and Marketing on the Internet", "https://www.ftc.gov/business-guidance/resources/advertising-marketing-internet-rules-road", "google", "general", "Only 12 left in the workshop bundle", "Only 12 left for this workshop bundle while the current batch is prepared.", "Get bundle", ["fake_urgency_scarcity"], ["misrepresentation"], "Inventory scarcity should be verified before launch."),
        ("ftc_sponsored_creator_tool_review", "FTC", "Endorsement Guides", "https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking", "tiktok", "creator", "Sponsored creator planning tool", "A sponsored creator shows how the planning board fits into a weekly content workflow.", "See tool", ["missing_affiliate_or_sponsor_disclosure", "tiktok_disclosure_risk"], ["disclosure", "platform_policy"], "Sponsored creator language needs prominent material-connection disclosure."),
        ("ftc_affiliate_camera_kit_review", "FTC", "Endorsement Guides", "https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking", "tiktok", "creator", "Affiliate camera kit walkthrough", "A creator shares an affiliate link for a camera kit used in behind-the-scenes videos.", "Shop kit", ["missing_affiliate_or_sponsor_disclosure", "tiktok_disclosure_risk"], ["disclosure", "platform_policy"], "Affiliate language should be reviewed for clear disclosure."),
        ("ftc_paid_partnership_template_review", "FTC", "Endorsement Guides", "https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking", "tiktok", "creator", "Paid partnership editing template", "A paid partnership clip shows how the editing template organizes product clips.", "Use template", ["missing_affiliate_or_sponsor_disclosure", "tiktok_disclosure_risk"], ["disclosure", "platform_policy"], "Paid partnership context requires disclosure review."),
        ("ftc_promo_code_budget_app_review", "FTC", "Endorsement Guides", "https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking", "tiktok", "finance", "Promo code for budget planner", "A creator shares a promo code for a budgeting workspace and explains setup steps.", "Use code", ["missing_affiliate_or_sponsor_disclosure"], ["disclosure"], "Promo-code copy indicates a possible material connection."),
        ("ftc_commission_course_review", "FTC", "Endorsement Guides", "https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking", "linkedin", "creator", "Commission link for creator course", "The creator notes a commission link while describing the course checklist.", "View checklist", ["missing_affiliate_or_sponsor_disclosure"], ["disclosure"], "Commission language should be checked for disclosure clarity."),
        ("tiktok_partner_creator_review", "TikTok", "Branded Content Policy", "https://support.tiktok.com/en/business-and-creator/creator-and-business-accounts/branded-content-policy", "tiktok", "creator", "Partner story for travel planner", "A partner creator walks through a travel planner and shares a packing workflow.", "Watch story", ["tiktok_disclosure_risk"], ["platform_policy"], "Partner creator language maps to TikTok disclosure review."),
        ("iab_political_news_adjacency_review", "IAB Tech Lab", "Content Taxonomy", "https://iabtechlab.com/standards/content-taxonomy/", "google", "general", "Advertise near election analysis", "Sponsor neutral news coverage during ballot season for local readers.", "Request inventory", ["brand_safety_politics"], ["brand_safety"], "Political adjacency should be reviewed for suitability settings."),
        ("iab_social_issue_context_review", "IAB Tech Lab", "Content Taxonomy", "https://iabtechlab.com/standards/content-taxonomy/", "google", "general", "Community forum on a social issue", "Promote a civic forum discussing a local social issue with neutral moderation.", "Learn more", ["brand_safety_sensitive_social_issue"], ["brand_safety"], "Sensitive social issue context can need brand-suitability review."),
        ("iab_controversial_topic_review", "IAB Tech Lab", "Content Taxonomy", "https://iabtechlab.com/standards/content-taxonomy/", "google", "general", "Sponsor controversial media analysis", "Place ads near a controversial story analysis package with careful exclusions.", "Review package", ["brand_safety_controversial_content"], ["brand_safety"], "Controversial adjacency should route to brand-safety review."),
        ("iab_campaign_finance_review", "IAB Tech Lab", "Content Taxonomy", "https://iabtechlab.com/standards/content-taxonomy/", "linkedin", "general", "Report on campaign finance data", "Promote a research briefing about campaign finance reporting for policy teams.", "Read report", ["brand_safety_politics"], ["brand_safety"], "Campaign-finance context is political content under the current brand-safety rules."),
        ("google_credit_discount_trial_mismatch_review", "Google Ads", "Misrepresentation policy", "https://support.google.com/adspolicy/answer/6020955", "google", "finance", "Credit discount starter trial", "Compare credit discount tools and trial onboarding steps for a small team.", "Start comparison", ["landing_page_offer_mismatch"], ["landing_page"], "The ad emphasizes credit, discount, and trial terms absent from the deterministic landing page."),
        ("google_privacy_discount_trial_mismatch_review", "Google Ads", "Misrepresentation policy", "https://support.google.com/adspolicy/answer/6020955", "google", "general", "Privacy discount trial checklist", "Review a privacy discount trial checklist for vendor onboarding.", "Open checklist", ["landing_page_offer_mismatch"], ["landing_page"], "The landing page omits multiple material terms emphasized by the ad."),
        ("google_salary_discount_credit_mismatch_review", "Google Ads", "Misrepresentation policy", "https://support.google.com/adspolicy/answer/6020955", "google", "finance", "Salary credit discount guide", "Download a salary credit discount guide for benefits planning teams.", "Download guide", ["landing_page_offer_mismatch"], ["landing_page"], "The deterministic landing page does not support the main salary, credit, and discount terms."),
    ]
    return [
        _row(
            row_id=row_id,
            source_type="policy_example",
            source_tier="tier_2_public_platform_case" if org in {"Google Ads", "TikTok"} else "tier_4_synthetic_from_real_pattern",
            source_org=org,
            source_title=title,
            source_url=url,
            label_basis="Public policy or guidance source paraphrased into a deterministic review row.",
            label_confidence="medium",
            label_rationale=rationale,
            policy_areas=policy_areas,
            copyright_status="paraphrased",
            outcome_source="policy_example",
            expected_decision="needs_review",
            expected_policy_ids=policy_ids,
            platform=platform,
            industry=industry,
            headline=headline,
            body=body,
            cta=cta,
            landing_page_html=_mismatch_page() if policy_ids == ["landing_page_offer_mismatch"] else _simple_page(headline, body),
        )
        for row_id, org, title, url, platform, industry, headline, body, cta, policy_ids, policy_areas, rationale in cases
    ]


def high_risk_rows() -> list[dict[str, Any]]:
    cases = [
        ("ftc_truheight_growth_supplement_2026", "regulator_case", "FTC", "FTC Takes Action Against TruHeight for Deceptive, Unsubstantiated Advertising for Supposed Height-Enhancing Supplements for Kids and Teens", "https://www.ftc.gov/news-events/news/press-releases/2026/04/ftc-takes-action-against-truheight-deceptive-unsubstantiated-advertising-supposed-height-enhancing", "2026-04-24", "US", "Public FTC enforcement summary; row paraphrases the claim pattern for deterministic policy testing.", "high", "Child growth supplement promotion uses clinical, doctor, supplement, and absolute outcome language.", ["health_claims", "platform_policy"], "public_enforcement", "google", "health", "Clinically proven growth supplement for kids", "Doctor recommended daily supplement helps teens grow taller. Works for everyone with no side effects when taken every day.", "Shop supplements", "<html><title>Growth supplement</title><h1>Clinically proven growth supplement</h1><p>Doctor recommended supplement information for families. Results vary and medical review may be needed.</p></html>", ["unsupported_health_claim", "guaranteed_outcome", "google_health_restricted_category"]),
        ("ftc_nextmed_weight_loss_terms_2025", "regulator_case", "FTC", "FTC Takes Action Against Telemedicine Firm NextMed Over Charges It Used Misleading Prices, Fake Reviews, and Deceptive Weight Loss Claims to Sell GLP-1 Weight-Loss Programs", "https://www.ftc.gov/node/88624", "2025-07-14", "US", "Public FTC enforcement summary; row paraphrases weight-loss and offer-term risk patterns.", "high", "Telehealth weight-loss program combines quantified weight-loss, prescription, clinic, free-trial, and urgency signals.", ["health_claims", "platform_policy", "misrepresentation"], "public_enforcement", "google", "health", "Lose 50 pounds with GLP-1 telehealth", "Weight loss program members lose 50 pounds with prescription support. Start a free trial before the offer expires today and book a clinic appointment online.", "Start free trial", "<html><title>Telehealth weight loss</title><h1>Prescription telehealth weight loss</h1><p>Lose weight with clinical support. Free trial and membership terms apply. Book a clinic appointment.</p></html>", ["weight_loss_claim", "google_health_restricted_category", "google_misrepresentation_risk", "fake_urgency_scarcity"]),
        ("ftc_goodrx_health_ads_2023", "regulator_case", "FTC", "FTC Enforcement Action to Bar GoodRx from Sharing Consumers' Sensitive Health Info for Advertising", "https://www.ftc.gov/news-events/news/press-releases/2023/02/ftc-enforcement-action-bar-goodrx-sharing-consumers-sensitive-health-info-advertising", "2023-02-01", "US", "Public FTC enforcement summary; row paraphrases health-data advertising and tracker patterns.", "high", "Health app and prescription context combines health data, patient language, health-condition form data, ad trackers, and Google health-category review.", ["privacy", "health_claims"], "public_enforcement", "google", "health", "Prescription discount reminders for patients", "Use health app prescription searches and health data to retarget patient audiences with pharmacy discount ads.", "Get coupon", "<html><title>Prescription savings</title><h1>Health app prescription discounts</h1><p>Patients can compare prescription prices and health data preferences.</p><form><label>Health condition</label><input name='health condition'></form><script src='https://connect.facebook.net/en_US/fbevents.js'></script><script src='https://www.google-analytics.com/analytics.js'></script></html>", ["ftc_health_breach_notification_indicator", "washington_mhmda_indicator", "ccpa_sensitive_health_indicator", "hipaa_marketing_review", "hipaa_tracking_technology_review", "tracking_pixel_risk", "google_health_restricted_category"]),
        ("ftc_betterhelp_mental_health_ads_2023", "regulator_case", "FTC", "FTC to Ban BetterHelp from Revealing Consumers' Data, Including Sensitive Mental Health Information, to Facebook and Others", "https://www.ftc.gov/news-events/news/press-releases/2023/03/ftc-ban-betterhelp-revealing-consumers-data-including-sensitive-mental-health-information-facebook", "2023-03-02", "US", "Public FTC enforcement summary; row paraphrases mental-health questionnaire retargeting risk.", "high", "Mental-health questionnaire and symptoms fields are paired with Meta and TikTok tracking.", ["privacy", "platform_policy"], "public_enforcement", "tiktok", "health", "Online therapy matched to your symptoms", "Retarget people who completed a mental health quiz about anxiety or depression symptoms with therapy subscription ads.", "Take the health quiz", "<html><title>Mental health quiz</title><h1>Therapy support</h1><p>Share symptoms and health data to match with a provider.</p><form><label>Symptoms</label><input name='symptoms'></form><script src='https://connect.facebook.net/en_US/fbevents.js'></script><script src='https://analytics.tiktok.com/i18n/pixel/events.js'></script></html>", ["health_form_tracking_risk", "tracking_pixel_risk", "ccpa_sensitive_health_indicator", "hipaa_marketing_review", "hipaa_tracking_technology_review"]),
        ("ftc_premom_fertility_sdk_ads_2023", "regulator_case", "FTC", "Ovulation Tracking App Premom Will be Barred from Sharing Health Data for Advertising", "https://www.ftc.gov/news-events/news/press-releases/2023/05/ovulation-tracking-app-premom-will-be-barred-sharing-health-data-advertising-under-proposed-ftc", "2023-05-17", "US", "Public FTC enforcement summary; row paraphrases reproductive-health app data sharing and analytics risk.", "high", "Fertility app campaign references reproductive health, sync data, precise geolocation, health data, and analytics scripts.", ["privacy"], "public_enforcement", "google", "health", "Fertility health app reminders", "Sync your data from an ovulation health app and use reproductive health insights plus precise geolocation to personalize fertility product ads.", "Sync your data", "<html><title>Fertility health app</title><h1>Reproductive health reminders</h1><p>Health data, reproductive health, and precise geolocation help personalize reminders.</p><form><label>Health quiz</label><input name='cycle'></form><script src='https://www.googletagmanager.com/gtm.js'></script></html>", ["ftc_health_breach_notification_indicator", "washington_mhmda_indicator", "ccpa_sensitive_health_indicator", "health_form_tracking_risk", "tracking_pixel_risk"]),
        ("ftc_cerebral_tracking_ads_2024", "regulator_case", "FTC", "Proposed FTC Order Will Prohibit Telehealth Firm Cerebral from Using or Disclosing Sensitive Data for Most Advertising Purposes", "https://www.ftc.gov/news-events/news/press-releases/2024/04/proposed-ftc-order-will-prohibit-telehealth-firm-cerebral-using-or-disclosing-sensitive-data", "2024-04-15", "US", "Public FTC enforcement summary; row paraphrases telehealth intake and pixel-sharing risk.", "high", "Telehealth clinic, appointment, patient, symptoms, conversion events, and third-party pixels create privacy review risk.", ["privacy", "platform_policy"], "public_enforcement", "tiktok", "health", "ADHD telehealth treatment appointment", "Optimize TikTok ads from completed intake forms for patients seeking ADHD medical treatment and clinic appointment scheduling.", "Book appointment", "<html><title>Telehealth appointment</title><h1>Clinic appointment</h1><p>Patient health data and symptoms are used to support telehealth treatment.</p><form><label>Intake form</label><input name='symptoms'></form><script src='https://analytics.tiktok.com/i18n/pixel/events.js'></script><script src='https://snap.licdn.com/li.lms-analytics/insight.min.js'></script><script>conversion event client id</script></html>", ["hipaa_marketing_review", "hipaa_tracking_technology_review", "tracking_pixel_risk", "health_form_tracking_risk", "ccpa_sensitive_health_indicator"]),
        ("ftc_golden_sunrise_covid_cure_2020", "regulator_case", "FTC", "FTC Sues California Marketer of $23,000 COVID-19 Treatment Plan", "https://www.ftc.gov/news-events/news/press-releases/2020/07/ftc-sues-california-marketer-23000-covid-19-treatment-plan", "2020-07-31", "US", "Public FTC enforcement summary; row paraphrases disease-treatment and miracle-cure claim patterns.", "high", "Medical breakthrough and supplement promotion uses cure, treat, prevent, no-side-effects, and misinformation terms.", ["health_claims", "platform_policy", "brand_safety"], "public_enforcement", "google", "health", "Medical breakthrough supplement protocol", "This supplement protocol treats viral symptoms, prevents disease, and acts as a miracle cure with no side effects.", "Start protocol", "<html><title>Supplement protocol</title><h1>Medical breakthrough supplement</h1><p>Clinical supplement information. Consult your provider. Results vary.</p></html>", ["medical_cure_claim", "unsupported_health_claim", "guaranteed_outcome", "google_health_restricted_category", "brand_safety_misinformation"]),
        ("ftc_sensa_weight_loss_2014", "regulator_case", "FTC", "Sensa and Three Other Marketers of Fad Weight-Loss Products Settle FTC Charges", "https://www.ftc.gov/news-events/news/press-releases/2014/01/sensa-three-other-marketers-fad-weight-loss-products-settle-ftc-charges-crackdown-deceptive", "2014-01-07", "US", "Public FTC enforcement summary; row paraphrases easy weight-loss and substantiation claim patterns.", "high", "Weight-loss product uses quantified loss, clinical/evidence framing, guarantee/risk-free language, and free-trial terms.", ["health_claims", "platform_policy", "misrepresentation"], "public_enforcement", "google", "wellness", "Lose 30 pounds without changing meals", "Clinically proven and evidence-based weight loss supplement. Guaranteed results with a risk-free free trial.", "Try free trial", "<html><title>Weight loss supplement</title><h1>Clinically proven weight loss</h1><p>Lose 30 pounds claims require substantiation. Free trial terms apply and results vary.</p></html>", ["weight_loss_claim", "unsupported_health_claim", "wellness_claim_review", "guaranteed_outcome", "google_health_restricted_category", "google_misrepresentation_risk"]),
        ("ftc_pure_green_coffee_fake_news_2016", "regulator_case", "FTC", "FTC Wins Summary Judgment Against Pitchman Behind Deceptive Green Coffee Weight-Loss Ads", "https://www.ftc.gov/news-events/news/press-releases/2016/11/ftc-wins-summary-judgment-against-pitchman-deceptive-green-coffee-weight-loss-ads-30-million", "2016-11-14", "US", "Public FTC enforcement summary; row paraphrases fake-news and weight-loss ad risk patterns.", "high", "Fake-news framing, secret/miracle language, weight-loss claims, and TikTok misleading-content signals are present.", ["health_claims", "platform_policy", "brand_safety"], "public_enforcement", "tiktok", "wellness", "Fake news weight loss secret", "Everyone is switching to this miracle green coffee capsule. It melts fat fast and helps users lose weight with a secret method.", "Watch story", "<html><title>Green coffee weight loss</title><h1>Weight loss story</h1><p>Fake news style claims about a secret miracle capsule and weight loss results.</p></html>", ["weight_loss_claim", "tiktok_weight_management_claim", "tiktok_misleading_content", "brand_safety_misinformation"]),
        ("asa_angel_clinic_ozempic_scarcity_2023", "advertising_ruling", "ASA/CAP", "The Angel Clinic ASA Ruling", "https://www.asa.org.uk/rulings/the-angel-clinic-a22-1176082-the-angel-clinic.html", "2023-01-11", "UK", "Public ASA ruling; row paraphrases prescription weight-loss, scarcity, and before/after risk patterns.", "high", "Prescription weight-loss injection copy includes weight-loss, medical clinic, before/after, and scarcity wording.", ["health_claims", "platform_policy", "misrepresentation"], "public_ruling", "google", "health", "Weekly weight loss injection appointments", "Medical clinic appointment for prescription weight loss treatment. Only 10 spots left; see the difference in before and after transformation photos.", "Message clinic", "<html><title>Weight loss clinic</title><h1>Medical clinic weight loss appointment</h1><p>Prescription weight loss treatment information. Only 10 spots left and before and after examples require review.</p></html>", ["google_health_restricted_category", "weight_loss_claim", "before_after_claim", "fake_urgency_scarcity"]),
        ("asa_hexpress_weight_loss_pen_2025", "advertising_ruling", "ASA/CAP", "Hexpress Healthcare Ltd ASA Ruling", "https://www.asa.org.uk/rulings/hexpress-healthcare-ltd-a24-1264776-hexpress-healthcare-ltd.html", "2025-07-09", "UK", "Public ASA ruling; row paraphrases paid ad promotion of prescription-only weight-loss treatment.", "high", "Online medical treatment ad combines clinical weight-loss, prescription, and consultation language.", ["health_claims", "platform_policy"], "public_ruling", "google", "health", "Clinically backed weight loss pen treatment", "Access once-weekly prescription weight loss treatment after a quick online clinic appointment.", "Start consultation", "<html><title>Weight loss treatment</title><h1>Prescription weight loss treatment</h1><p>Clinically backed medical treatment after an online clinic appointment. Results vary.</p></html>", ["unsupported_health_claim", "weight_loss_claim", "google_health_restricted_category"]),
        ("ftc_lyft_earnings_guarantee_2024", "regulator_case", "FTC", "FTC Takes Action to Stop Lyft from Deceiving Drivers with Misleading Earnings Claims", "https://www.ftc.gov/news-events/news/press-releases/2024/10/ftc-takes-action-stop-lyft-deceiving-drivers-misleading-earnings-claims", "2024-10-25", "US", "Public FTC enforcement summary; row paraphrases earnings-guarantee disclosure risk.", "medium", "Professional/income ad uses guarantee and unclear outcome language; current policies approximate employment-platform risk.", ["platform_policy", "misrepresentation", "finance"], "public_enforcement", "linkedin", "general", "Guaranteed earnings this weekend", "Drive 45 rides and get a guaranteed promotion bonus with guaranteed $975 earnings. Terms and guarantee math are not shown.", "Apply now", "<html><title>Driver earnings</title><h1>Guaranteed earnings offer</h1><p>Guaranteed promotion bonus details and terms should be reviewed.</p></html>", ["guaranteed_outcome", "linkedin_professional_claim_review"]),
        ("hud_doj_meta_housing_ads_2022", "regulator_case", "HUD/DOJ", "Justice Department Secures Groundbreaking Settlement Agreement with Meta Platforms", "https://www.justice.gov/archives/opa/pr/justice-department-secures-groundbreaking-settlement-agreement-meta-platforms-formerly-known", "2022-06-21", "US", "Public DOJ settlement announcement and HUD charging context; row paraphrases discriminatory housing-ad targeting risk.", "medium", "Housing campaign targeting excludes protected or sensitive groups; current rules approximate housing discrimination risk.", ["platform_policy", "brand_safety"], "public_enforcement", "linkedin", "general", "Luxury apartments for young professionals only", "Promote apartment listings to young professionals only while excluding users by religion and ethnicity. Housing social issue targeting needs review.", "Apply today", "<html><title>Apartment listings</title><h1>Young professionals only</h1><p>Apartment campaign mentions religion, ethnicity, and social issue targeting exclusions.</p></html>", ["linkedin_sensitive_targeting", "linkedin_discrimination_risk", "brand_safety_sensitive_social_issue"]),
        ("cfpb_credit_repair_guaranteed_approval_2024", "regulator_case", "CFPB", "Credit repair and debt relief consumer advisory", "https://www.consumerfinance.gov/consumer-tools/credit-reports-and-scores/", "2024-02-01", "US", "Public consumer finance guidance; row paraphrases credit-repair guarantee risk.", "medium", "Credit repair ad uses guaranteed approval, no-fee, and fix-credit language.", ["finance", "platform_policy", "misrepresentation"], "policy_example", "google", "finance", "Guaranteed approval credit repair", "Fix your credit fast with guaranteed approval and no fees before enrollment.", "Apply now", "<html><title>Credit repair</title><h1>Guaranteed approval credit repair</h1><p>Fix your credit fast. No fees before enrollment.</p></html>", ["guaranteed_outcome", "google_misrepresentation_risk", "google_financial_claim_review"]),
        ("ftc_business_opportunity_salary_2023", "regulator_case", "FTC", "Business opportunity rule and earnings claims", "https://www.ftc.gov/business-guidance/resources/business-guidance-concerning-multi-level-marketing", "2023-01-01", "US", "Public FTC business guidance; row paraphrases professional earnings outcome risk.", "medium", "Professional ad makes an unqualified salary outcome promise.", ["platform_policy", "misrepresentation"], "policy_example", "linkedin", "general", "Double your salary with this system", "Use our career workflow and double your salary after a few weeks of outreach.", "Start system", "<html><title>Career workflow</title><h1>Double your salary</h1><p>Career workflow for outreach and professional planning.</p></html>", ["linkedin_professional_claim_review"]),
        ("eeoc_native_speaker_job_ad_2024", "regulator_case", "EEOC", "Prohibited employment policies and practices", "https://www.eeoc.gov/prohibited-employment-policiespractices", "2024-01-01", "US", "Public EEOC guidance; row paraphrases exclusionary employment-ad wording.", "medium", "Job ad uses native-speaker exclusionary language that maps to current LinkedIn discrimination policy.", ["platform_policy"], "policy_example", "linkedin", "general", "Customer support roles, must be native speaker", "Hiring for support roles with a must be native speaker requirement in the ad.", "Apply now", "<html><title>Support roles</title><h1>Must be native speaker</h1><p>Customer support hiring page.</p></html>", ["linkedin_discrimination_risk"]),
        ("eeoc_recent_graduates_only_job_ad_2024", "regulator_case", "EEOC", "Prohibited employment policies and practices", "https://www.eeoc.gov/prohibited-employment-policiespractices", "2024-01-01", "US", "Public EEOC guidance; row paraphrases age-adjacent employment-ad wording.", "medium", "Job ad targets recent graduates only, creating sensitive targeting and discrimination review risk.", ["platform_policy"], "policy_example", "linkedin", "general", "Analyst roles for recent graduates only", "Promote analyst hiring to recent graduates only and exclude other applicants.", "Apply now", "<html><title>Analyst roles</title><h1>Recent graduates only</h1><p>Analyst hiring campaign.</p></html>", ["linkedin_sensitive_targeting", "linkedin_discrimination_risk"]),
        ("linkedin_health_condition_targeting_2024", "platform_example", "LinkedIn", "LinkedIn Ads policies", "https://www.linkedin.com/legal/ads-policy", "2024-01-01", "US", "Public platform policy; row paraphrases sensitive health-condition targeting risk.", "medium", "LinkedIn campaign targets a medical condition, which should be treated as high-risk sensitive targeting.", ["platform_policy", "privacy"], "policy_example", "linkedin", "general", "Support group resource for medical condition", "Target members by medical condition and invite them to a resource webinar.", "Register", "<html><title>Resource webinar</title><h1>Medical condition resource</h1><p>Webinar for people with a medical condition.</p></html>", ["linkedin_sensitive_targeting"]),
        ("ftc_detox_tea_weight_loss_creator_2020", "regulator_case", "FTC", "FTC endorsement guidance", "https://www.ftc.gov/business-guidance/resources/ftcs-endorsement-guides-what-people-are-asking", "2020-01-01", "US", "Public FTC endorsement guidance; row paraphrases undisclosed sponsored weight-loss creator risk.", "medium", "Creator copy includes sponsored promo-code and weight-loss claims on TikTok.", ["health_claims", "platform_policy", "disclosure"], "policy_example", "tiktok", "wellness", "Sponsored detox tea weight loss story", "Paid partnership creator says use my promo code to lose 20 pounds with this tea.", "Use promo code", "<html><title>Tea story</title><h1>Weight loss tea</h1><p>Sponsored creator story with promo code.</p></html>", ["weight_loss_claim", "tiktok_weight_management_claim", "missing_affiliate_or_sponsor_disclosure", "tiktok_disclosure_risk"]),
        ("hhs_tracking_appointment_pixel_2024", "regulator_case", "HHS OCR", "Use of online tracking technologies by HIPAA covered entities and business associates", "https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/hipaa-online-tracking/index.html", "2024-03-18", "US", "Public HHS guidance; row paraphrases health appointment page tracking risk.", "medium", "Health appointment and patient context is paired with Google Analytics, conversion-event tracking, and Google health-category review signals.", ["privacy", "platform_policy"], "policy_example", "google", "health", "Patient appointment reminder campaign", "Retarget patient appointment visitors after they book appointment slots with a clinic provider.", "Book appointment", "<html><title>Clinic appointment</title><h1>Patient appointment</h1><p>Book appointment with a provider and discuss your symptoms.</p><form><label>Appointment notes</label><input name='appointment notes'></form><script src='https://www.google-analytics.com/analytics.js'></script><script>conversion event client id</script></html>", ["hipaa_marketing_review", "hipaa_tracking_technology_review", "tracking_pixel_risk", "health_form_tracking_risk", "google_health_restricted_category"]),
        ("washington_reproductive_health_geolocation_2024", "regulator_case", "Washington Attorney General", "My Health My Data Act", "https://www.atg.wa.gov/protecting-washingtonians-personal-health-data-and-privacy", "2024-01-01", "US", "Public Washington AG guidance; row paraphrases reproductive-health and geolocation data risk.", "medium", "Health app promotion references reproductive health, health data, and precise geolocation.", ["privacy"], "policy_example", "google", "wellness", "Reproductive health app location reminders", "Sync your data in a health app using reproductive health insights and precise geolocation.", "Sync data", "<html><title>Reproductive health app</title><h1>Health app reminders</h1><p>Consumer health data and precise geolocation personalize reminders.</p></html>", ["ftc_health_breach_notification_indicator", "washington_mhmda_indicator", "ccpa_sensitive_health_indicator"]),
        ("iab_violent_news_adjacency_high_risk", "platform_example", "IAB Tech Lab", "Content Taxonomy", "https://iabtechlab.com/standards/content-taxonomy/", "2024-01-01", "US", "Public IAB taxonomy; row paraphrases unsafe violent-content adjacency.", "medium", "Ad adjacency references violent assault and weapon coverage, triggering high-severity brand-safety review.", ["brand_safety"], "policy_example", "google", "general", "Run ads beside violent breaking news", "Place the campaign near coverage of a violent assault and weapon investigation.", "Request inventory", "<html><title>News inventory</title><h1>Violent assault coverage package</h1><p>Inventory includes weapon investigation stories.</p></html>", ["brand_safety_violence"]),
        ("iab_adult_content_adjacency_high_risk", "platform_example", "IAB Tech Lab", "Content Taxonomy", "https://iabtechlab.com/standards/content-taxonomy/", "2024-01-01", "US", "Public IAB taxonomy; row paraphrases adult-content adjacency.", "medium", "Ad adjacency references adult and explicit content inventory.", ["brand_safety"], "policy_example", "google", "general", "Advertise beside adult entertainment reviews", "Buy inventory next to adult entertainment pages with explicit discussion threads.", "Request inventory", "<html><title>Adult entertainment inventory</title><h1>Explicit review pages</h1><p>Adult entertainment placements.</p></html>", ["brand_safety_adult_content"]),
        ("iab_tragedy_conflict_adjacency_high_risk", "platform_example", "IAB Tech Lab", "Content Taxonomy", "https://iabtechlab.com/standards/content-taxonomy/", "2024-01-01", "US", "Public IAB taxonomy; row paraphrases tragedy and conflict adjacency.", "medium", "Ad adjacency references war, disaster, and death coverage.", ["brand_safety"], "policy_example", "google", "general", "Promote offer near war disaster coverage", "Place product ads beside war, disaster, and death coverage during breaking news.", "Request inventory", "<html><title>Breaking news inventory</title><h1>War and disaster coverage</h1><p>Death toll updates and conflict analysis.</p></html>", ["brand_safety_tragedy_conflict"]),
        ("google_financial_risk_free_investment_2024", "platform_example", "Google Ads", "Financial products and services policy", "https://support.google.com/adspolicy/answer/2464998", "2024-01-01", "US", "Public Google Ads policy; row paraphrases high-risk finance outcome claim.", "medium", "Finance copy promises risk-free investment and doubled money.", ["finance", "platform_policy"], "policy_example", "google", "finance", "Risk-free investment doubles your money", "Start a risk-free investment plan that can double your money after signup.", "Start plan", "<html><title>Investment plan</title><h1>Risk-free investment plan</h1><p>Double your money after signup.</p></html>", ["guaranteed_outcome", "google_financial_claim_review"]),
    ]
    return [
        _row(
            row_id=row_id,
            source_type=source_type,
            source_tier="tier_4_synthetic_from_real_pattern",
            source_org=org,
            source_title=title,
            source_url=url,
            case_date=case_date,
            jurisdiction=jurisdiction,
            label_basis=label_basis,
            label_confidence=confidence,
            label_rationale=rationale,
            policy_areas=policy_areas,
            copyright_status="paraphrased",
            outcome_source=outcome_source,
            expected_decision="high_risk",
            expected_policy_ids=policy_ids,
            platform=platform,
            industry=industry,
            headline=headline,
            body=body,
            cta=cta,
            landing_page_html=landing_page_html,
        )
        for (
            row_id,
            source_type,
            org,
            title,
            url,
            case_date,
            jurisdiction,
            label_basis,
            confidence,
            rationale,
            policy_areas,
            outcome_source,
            platform,
            industry,
            headline,
            body,
            cta,
            landing_page_html,
            policy_ids,
        ) in cases
    ]


def _row(
    *,
    row_id: str,
    source_type: str,
    source_tier: str,
    source_org: str,
    source_title: str,
    source_url: str,
    label_basis: str,
    label_confidence: str,
    label_rationale: str,
    policy_areas: list[str],
    copyright_status: str,
    outcome_source: str,
    expected_decision: str,
    expected_policy_ids: list[str],
    platform: str,
    industry: str,
    headline: str,
    body: str,
    cta: str,
    landing_page_html: str,
    case_date: str | None = None,
    jurisdiction: str = "US",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": row_id,
        "source_type": source_type,
        "source_tier": source_tier,
        "source_org": source_org,
        "source_title": source_title,
        "source_url": source_url,
        "jurisdiction": jurisdiction,
        "accessed_at": ACCESSED_AT,
        "label_basis": label_basis,
        "label_confidence": label_confidence,
        "label_rationale": label_rationale,
        "provenance": f"{source_url} accessed {ACCESSED_AT}; paraphrased into deterministic local eval input.",
        "policy_areas": policy_areas,
        "copyright_status": copyright_status,
        "outcome_source": outcome_source,
        "input": {
            "platform": platform,
            "country": jurisdiction,
            "industry": industry,
            "headline": headline,
            "body": body,
            "cta": cta,
            "landing_page_html": landing_page_html,
        },
        "expected_decision": expected_decision,
        "expected_policy_ids": expected_policy_ids,
    }
    if case_date is not None:
        row["case_date"] = case_date
    return row


def _simple_page(headline: str, body: str) -> str:
    return f"<html><title>{headline}</title><h1>{headline}</h1><p>{body}</p></html>"


def _mismatch_page() -> str:
    return "<html><title>Resource center</title><h1>Planning resource</h1><p>Read general onboarding notes and team setup guidance.</p></html>"


if __name__ == "__main__":
    raise SystemExit(main())
