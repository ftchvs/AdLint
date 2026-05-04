from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from urllib.parse import quote


OUTPUT_PATH = Path(__file__).resolve().parent / "datasets" / "real_world_blind_v1.jsonl"
ACCESSED_AT = "2026-05-03"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the web-sourced blind real-world eval.")
    parser.add_argument(
        "--candidates",
        action="store_true",
        help="print the full 150-row candidate pool to stdout without writing files",
    )
    args = parser.parse_args(argv)

    if args.candidates:
        for row in build_candidate_pool():
            print(json.dumps(row, sort_keys=True, separators=(",", ":")))
        return 0

    rows = build_rows()
    OUTPUT_PATH.write_text(
        "\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(rows)} rows to {OUTPUT_PATH}")
    return 0


def build_rows() -> list[dict[str, Any]]:
    rows = [row for row in build_candidate_pool() if row["adjudication_status"] == "accepted"]
    decisions = [row["expected_decision"] for row in rows]
    assert len(rows) == 90
    assert decisions.count("approved") == 30
    assert decisions.count("needs_review") == 30
    assert decisions.count("high_risk") == 30
    assert len({row["id"] for row in rows}) == len(rows)
    assert len({row["source_url"] for row in rows}) == len(rows)
    assert len({_normalize(row["input"]["headline"]) for row in rows}) == len(rows)
    assert all(row["rule_tuning_holdout"] is True for row in rows)
    return rows


def build_candidate_pool() -> list[dict[str, Any]]:
    accepted = approved_rows() + needs_review_rows() + high_risk_rows()
    rejected = _rejected_candidates(accepted)
    assert len(accepted) == 90
    assert len(rejected) == 60
    return accepted + rejected


def approved_rows() -> list[dict[str, Any]]:
    cases = [
        ("blind_slack_launch_workspace", "Slack", "Slack product page", "https://slack.com/", "linkedin", "saas", "Organize product launch channels", "Create project channels, assign owners, and share launch updates in one workspace.", "See workspace tools"),
        ("blind_salesforce_pipeline_notes", "Salesforce", "Salesforce Sales Cloud page", "https://www.salesforce.com/products/sales-cloud/", "google", "saas", "Keep sales pipeline notes current", "Track accounts, tasks, and handoffs for customer teams without regulated outcome claims.", "View CRM"),
        ("blind_hubspot_contact_workspace", "HubSpot", "HubSpot CRM page", "https://www.hubspot.com/products/crm", "linkedin", "saas", "Start a simple contact workspace", "Bring customer records, notes, and follow-up tasks into one shared dashboard.", "Explore CRM"),
        ("blind_asana_project_templates", "Asana", "Asana product page", "https://asana.com/", "google", "saas", "Plan launch work with templates", "Use boards, timelines, and task owners to keep product work coordinated.", "Browse templates"),
        ("blind_notion_team_docs", "Notion", "Notion product page", "https://www.notion.so/product", "linkedin", "saas", "Centralize team docs and notes", "Create process pages, project plans, and meeting notes for a growing team.", "See examples"),
        ("blind_figma_design_handoff", "Figma", "Figma product page", "https://www.figma.com/", "google", "saas", "Review design handoffs faster", "Collect comments, organize assets, and prepare designs for implementation.", "Open design tools"),
        ("blind_jira_issue_planning", "Atlassian", "Jira product page", "https://www.atlassian.com/software/jira", "linkedin", "saas", "Track engineering issues clearly", "Prioritize bugs, plan sprints, and follow release status across teams.", "Explore Jira"),
        ("blind_zoom_meeting_workspace", "Zoom", "Zoom product page", "https://www.zoom.com/", "google", "saas", "Run clearer customer meetings", "Host calls, share agendas, and keep meeting follow-ups organized.", "Start a meeting"),
        ("blind_dropbox_asset_library", "Dropbox", "Dropbox product page", "https://www.dropbox.com/", "linkedin", "saas", "Share approved campaign assets", "Keep creative drafts, launch files, and stakeholder folders in one place.", "View plans"),
        ("blind_calendly_demo_scheduling", "Calendly", "Calendly product page", "https://calendly.com/", "google", "saas", "Simplify demo scheduling", "Let visitors choose available times and receive organized calendar reminders.", "Try scheduling"),
        ("blind_mailchimp_product_newsletter", "Mailchimp", "Mailchimp marketing page", "https://mailchimp.com/", "google", "general", "Send a monthly product newsletter", "Share product tips, company updates, and event invitations with subscribers.", "Create newsletter"),
        ("blind_shopify_store_catalog", "Shopify", "Shopify product page", "https://www.shopify.com/", "google", "general", "Build an online product catalog", "Create store pages, manage orders, and organize product information.", "Start store setup"),
        ("blind_stripe_payment_forms", "Stripe", "Stripe payments page", "https://stripe.com/payments", "linkedin", "finance", "Set up online payment forms", "Accept payments, send invoices, and review transaction reporting in one dashboard.", "Explore payments"),
        ("blind_canva_brand_templates", "Canva", "Canva product page", "https://www.canva.com/", "google", "general", "Design brand templates faster", "Create presentations, launch graphics, and social posts from shared templates.", "Start designing"),
        ("blind_miro_workshop_board", "Miro", "Miro product page", "https://miro.com/", "linkedin", "saas", "Map workshop ideas visually", "Collect notes, diagrams, and feedback in a shared planning board.", "Open board"),
        ("blind_buffer_social_calendar", "Buffer", "Buffer product page", "https://buffer.com/", "google", "general", "Plan social content calendars", "Draft posts, organize approvals, and review upcoming publishing schedules.", "Plan posts"),
        ("blind_hootsuite_channel_workflow", "Hootsuite", "Hootsuite product page", "https://www.hootsuite.com/", "linkedin", "general", "Coordinate social channel workflows", "Manage brand channels, team approvals, and reporting calendars.", "View platform"),
        ("blind_grammarly_team_writing", "Grammarly", "Grammarly Business page", "https://www.grammarly.com/business", "google", "saas", "Write clearer team messages", "Help teams draft concise emails, documents, and support replies.", "Improve writing"),
        ("blind_intercom_support_routes", "Intercom", "Intercom product page", "https://www.intercom.com/", "linkedin", "saas", "Route customer conversations", "Collect context, assign replies, and keep support conversations organized.", "Explore inbox"),
        ("blind_zendesk_help_center", "Zendesk", "Zendesk product page", "https://www.zendesk.com/", "google", "saas", "Publish a helpful support center", "Create help articles, manage tickets, and track support workflows.", "View support tools"),
        ("blind_airtable_vendor_tracker", "Airtable", "Airtable product page", "https://www.airtable.com/", "linkedin", "saas", "Track vendors in flexible tables", "Coordinate status, owners, and content calendars with a shared workspace.", "Browse templates"),
        ("blind_quickbooks_invoice_dashboard", "Intuit QuickBooks", "QuickBooks product page", "https://quickbooks.intuit.com/", "google", "finance", "Organize invoices and expenses", "Track invoices, payments, and business reports with accounting tools.", "View accounting tools"),
        ("blind_docusign_signature_flow", "DocuSign", "DocuSign product page", "https://www.docusign.com/", "linkedin", "saas", "Prepare agreements for signature", "Send documents, collect signatures, and store completed agreements.", "Start agreement"),
        ("blind_surveymonkey_feedback_form", "SurveyMonkey", "SurveyMonkey product page", "https://www.surveymonkey.com/", "google", "general", "Collect customer feedback surveys", "Create surveys to learn about product experience and service quality.", "Build survey"),
        ("blind_typeform_event_intake", "Typeform", "Typeform product page", "https://www.typeform.com/", "linkedin", "saas", "Create friendly event intake forms", "Gather preferences, requests, and event details through branded forms.", "Create form"),
        ("blind_trello_kanban_board", "Trello", "Trello product page", "https://trello.com/", "google", "saas", "Organize tasks on a visual board", "Move cards through planning, review, and done columns with your team.", "Open board"),
        ("blind_github_project_planning", "GitHub", "GitHub product page", "https://github.com/features/issues", "linkedin", "saas", "Plan software work with issues", "Track bugs, tasks, and project boards alongside repository work.", "Explore issues"),
        ("blind_microsoft_teams_collaboration", "Microsoft Teams", "Microsoft Teams product page", "https://www.microsoft.com/en-us/microsoft-teams/group-chat-software", "google", "saas", "Bring team chat and meetings together", "Coordinate chats, files, calls, and meetings in a shared team workspace.", "View Teams"),
        ("blind_google_workspace_docs", "Google Workspace", "Google Workspace product page", "https://workspace.google.com/", "google", "saas", "Create shared docs and calendars", "Use email, docs, storage, and calendars to keep teams coordinated.", "See Workspace"),
        ("blind_monday_work_management", "monday.com", "monday.com product page", "https://monday.com/", "linkedin", "saas", "Manage team work in one place", "Plan projects, assign tasks, and review progress across departments.", "View work platform"),
    ]
    return [
        _row(
            row_id=row_id,
            source_platform="public_brand_page",
            source_capture_type="public_marketing_page",
            ad_observed_status="unknown",
            source_type="public_marketing_example",
            source_tier="tier_3_public_marketing_example",
            source_org=org,
            source_title=title,
            source_url=url,
            label_basis="Public product or marketing page paraphrased into a policy-safe blind holdout row.",
            label_confidence="medium",
            label_rationale="The row avoids regulated claims, sensitive targeting, creator disclosure issues, and landing-page mismatch signals.",
            policy_areas=["control"],
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
        ("blind_sleep_science_prompt_review", "google_ads_transparency", "google", "wellness", "Science-backed sleep reset prompts", "Promote a nightly routine with science-backed prompts for calmer sleep habits.", "Try prompts", ["wellness_claim_review"], ["health_claims"], "Science-backed wellness language needs substantiation review.", "wellness sleep science", "Google Ads Transparency Center wellness search"),
        ("blind_hydration_evidence_reminder_review", "meta_ad_library", "google", "wellness", "Evidence-based hydration reminder plan", "Share daily hydration reminders described as evidence-based habit support.", "Get reminders", ["wellness_claim_review"], ["health_claims"], "Evidence-framed wellness copy should be reviewed before launch.", "hydration evidence based", "Meta Ad Library wellness search"),
        ("blind_skin_before_after_gallery_review", "asa", "google", "wellness", "Before and after skin routine gallery", "Show customer before and after examples from a daily skincare routine.", "View gallery", ["before_after_claim"], ["health_claims"], "Before-and-after result framing can imply atypical outcomes.", "before-after-photos", "ASA before and after photos advice"),
        ("blind_fitness_transformation_recap_review", "tiktok_ccl", "tiktok", "wellness", "Transformation photo class recap", "Invite viewers to watch transformation photo stories from a weekly movement class.", "Watch recap", ["before_after_claim"], ["health_claims"], "Transformation-photo language should be checked for typical-results context.", "fitness transformation photo", "TikTok CCL fitness transformation search"),
        ("blind_membership_last_chance_review", "google_ads_transparency", "google", "general", "Last chance for member pricing", "Last chance to join the community plan before the public price changes next week.", "Join plan", ["fake_urgency_scarcity"], ["misrepresentation"], "Scarcity language needs verification that the deadline is real.", "last chance member pricing", "Google Ads Transparency Center urgency search"),
        ("blind_webinar_limited_spots_review", "linkedin_ad_library", "linkedin", "saas", "Limited spots for onboarding webinar", "Limited spots are available for a live onboarding webinar with the product team.", "Save seat", ["fake_urgency_scarcity"], ["misrepresentation"], "Limited-space claims need reviewer confirmation before launch.", "limited spots webinar", "LinkedIn Ad Library scarcity search"),
        ("blind_sponsored_creator_planner_review", "tiktok_ccl", "tiktok", "creator", "Sponsored creator planning walkthrough", "A sponsored creator shows how a planning board fits into weekly content work.", "See tool", ["missing_affiliate_or_sponsor_disclosure", "tiktok_disclosure_risk"], ["disclosure", "platform_policy"], "Sponsored creator context requires clear material-connection disclosure.", "sponsored creator planner", "TikTok CCL sponsored creator search"),
        ("blind_affiliate_camera_walkthrough_review", "tiktok_ccl", "tiktok", "creator", "Affiliate camera kit walkthrough", "A creator shares an affiliate link for a camera kit used in behind-the-scenes videos.", "Shop kit", ["missing_affiliate_or_sponsor_disclosure", "tiktok_disclosure_risk"], ["disclosure", "platform_policy"], "Affiliate-language copy should be reviewed for disclosure clarity.", "affiliate camera kit", "TikTok CCL affiliate search"),
        ("blind_paid_template_demo_review", "tiktok_ccl", "tiktok", "creator", "Paid partnership editing template demo", "A paid partnership clip shows how an editing template organizes product clips.", "Use template", ["missing_affiliate_or_sponsor_disclosure", "tiktok_disclosure_risk"], ["disclosure", "platform_policy"], "Paid partnership context requires prominent disclosure review.", "paid partnership template", "TikTok CCL paid partnership search"),
        ("blind_budget_app_promo_code_review", "meta_ad_library", "tiktok", "finance", "Promo code for budget planner setup", "A creator shares a promo code for a budgeting workspace and explains setup steps.", "Use code", ["missing_affiliate_or_sponsor_disclosure"], ["disclosure"], "Promo-code copy indicates a possible material connection.", "promo code budget planner", "Meta Ad Library promo code search"),
        ("blind_commission_course_checklist_review", "linkedin_ad_library", "linkedin", "creator", "Commission link for creator course", "The creator notes a commission link while describing the course checklist.", "View checklist", ["missing_affiliate_or_sponsor_disclosure"], ["disclosure"], "Commission language should be checked for clear disclosure.", "commission creator course", "LinkedIn Ad Library commission search"),
        ("blind_partner_travel_story_review", "tiktok_ccl", "tiktok", "creator", "Partner story for travel planner", "A partner creator walks through a travel planner and shares a packing workflow.", "Watch story", ["tiktok_disclosure_risk"], ["platform_policy"], "Partner creator language maps to TikTok disclosure review.", "partner creator travel planner", "TikTok CCL partner creator search"),
        ("blind_election_analysis_adjacency_review", "meta_ad_library", "google", "general", "Advertise near election analysis", "Sponsor neutral news coverage during ballot season for local readers.", "Request inventory", ["brand_safety_politics"], ["brand_safety"], "Political adjacency should be reviewed for suitability settings.", "election analysis sponsor", "Meta Ad Library election analysis search"),
        ("blind_social_issue_forum_review", "meta_ad_library", "google", "general", "Community forum on a social issue", "Promote a civic forum discussing a local social issue with neutral moderation.", "Learn more", ["brand_safety_sensitive_social_issue"], ["brand_safety"], "Sensitive social issue context can need brand-suitability review.", "social issue forum", "Meta Ad Library social issue search"),
        ("blind_controversial_media_package_review", "google_ads_transparency", "google", "general", "Sponsor controversial media analysis", "Place ads near a controversial story analysis package with careful exclusions.", "Review package", ["brand_safety_controversial_content"], ["brand_safety"], "Controversial adjacency should route to brand-safety review.", "controversial media analysis", "Google Ads Transparency Center controversial search"),
        ("blind_campaign_finance_report_review", "linkedin_ad_library", "linkedin", "general", "Report on campaign finance data", "Promote a research briefing about campaign finance reporting for policy teams.", "Read report", ["brand_safety_politics"], ["brand_safety"], "Campaign-finance context is political content under brand-safety rules.", "campaign finance report", "LinkedIn Ad Library campaign finance search"),
        ("blind_credit_trial_mismatch_review", "google_ads_transparency", "google", "finance", "Credit discount starter trial", "Compare credit discount tools and trial onboarding steps for a small team.", "Start comparison", ["landing_page_offer_mismatch"], ["landing_page"], "The ad emphasizes credit, discount, and trial terms absent from the landing page.", "credit discount trial", "Google Ads Transparency Center credit trial search"),
        ("blind_privacy_trial_mismatch_review", "google_ads_transparency", "google", "general", "Privacy discount trial checklist", "Review a privacy discount trial checklist for vendor onboarding.", "Open checklist", ["landing_page_offer_mismatch"], ["landing_page"], "The landing page omits multiple material terms emphasized by the ad.", "privacy discount trial", "Google Ads Transparency Center privacy trial search"),
        ("blind_salary_credit_guide_mismatch_review", "linkedin_ad_library", "linkedin", "finance", "Salary credit discount guide", "Download a salary credit discount guide for benefits planning teams.", "Download guide", ["landing_page_offer_mismatch"], ["landing_page"], "The deterministic landing page does not support the main salary, credit, and discount terms.", "salary credit discount guide", "LinkedIn Ad Library salary credit search"),
        ("blind_projection_return_review", "google_ads_transparency", "google", "finance", "Projected return planning workbook", "Compare projected return scenarios for a new savings plan without committing today.", "Open workbook", ["google_financial_claim_review"], ["platform_policy"], "Finance outcome framing should receive review even without an explicit guarantee.", "projected return workbook", "Google Ads Transparency Center finance search"),
        ("blind_productivity_claim_review", "linkedin_ad_library", "linkedin", "saas", "Productivity system for busy teams", "Use the workflow to improve team output and support faster weekly planning.", "View workflow", ["linkedin_professional_claim_review"], ["platform_policy"], "Professional performance claims should be checked for substantiation and context.", "productivity workflow teams", "LinkedIn Ad Library productivity search"),
        ("blind_promotion_workshop_review", "linkedin_ad_library", "linkedin", "general", "Promotion workshop for team leads", "Learn a workshop method for preparing promotion packets and manager conversations.", "Save seat", ["linkedin_professional_claim_review"], ["platform_policy"], "Career outcome framing is review-worthy even without an absolute promise.", "promotion workshop team leads", "LinkedIn Ad Library promotion search"),
        ("blind_health_quiz_signup_review", "meta_ad_library", "google", "wellness", "Health quiz with email reminders", "Take a health quiz and sign up for weekly reminder emails about routine goals.", "Take quiz", ["health_form_tracking_risk"], ["privacy"], "Health-form and email-signup context should be privacy-reviewed.", "health quiz email signup", "Meta Ad Library health quiz search"),
        ("blind_telehealth_info_review", "google_ads_transparency", "google", "health", "Telehealth information appointment guide", "Read a guide about telehealth appointment preparation and provider questions.", "Read guide", ["google_health_restricted_category"], ["platform_policy"], "Healthcare and appointment context should be checked for platform eligibility.", "telehealth appointment guide", "Google Ads Transparency Center telehealth search"),
        ("blind_creator_brand_tag_review", "tiktok_ccl", "tiktok", "creator", "Brand-tagged morning routine story", "A creator tags the brand while showing a morning routine and product setup.", "Watch story", ["tiktok_disclosure_risk"], ["platform_policy"], "Commercial-content context should be reviewed for proper disclosure.", "brand tagged routine", "TikTok CCL brand tagged search"),
        ("blind_neutral_policy_briefing_review", "linkedin_ad_library", "linkedin", "general", "Briefing on ballot policy updates", "Invite policy teams to read a neutral briefing about ballot-process updates.", "Read briefing", ["brand_safety_politics"], ["brand_safety"], "Ballot-process context should route to political suitability review.", "ballot policy briefing", "LinkedIn Ad Library ballot search"),
        ("blind_religion_context_event_review", "meta_ad_library", "google", "general", "Community event for faith leaders", "Promote a public community event for faith leaders and local organizers.", "Register", ["brand_safety_sensitive_social_issue"], ["brand_safety"], "Religion-adjacent context can require sensitive-topic review.", "faith leaders community event", "Meta Ad Library religion event search"),
        ("blind_scandal_analysis_newsletter_review", "google_ads_transparency", "google", "general", "Newsletter on industry scandal analysis", "Sponsor an editorial newsletter analyzing a recent industry scandal.", "Read newsletter", ["brand_safety_controversial_content"], ["brand_safety"], "Scandal adjacency should be checked for brand suitability.", "industry scandal newsletter", "Google Ads Transparency Center scandal search"),
        ("blind_after_photo_hair_diary_review", "asa", "google", "wellness", "Dramatic results hair routine diary", "A diary shows dramatic results after people changed their daily hair routine.", "Read diary", ["before_after_claim"], ["health_claims"], "Dramatic-results framing can imply atypical outcomes.", "dramatic-results-hair", "ASA dramatic results advice"),
        ("blind_scarce_inventory_bundle_review", "google_ads_transparency", "google", "general", "Only 12 workshop bundles left", "Only 12 left for this workshop bundle while the current batch is prepared.", "Get bundle", ["fake_urgency_scarcity"], ["misrepresentation"], "Inventory scarcity should be verified before launch.", "only 12 workshop bundle", "Google Ads Transparency Center scarcity search"),
    ]
    return [
        _row(
            row_id=row_id,
            source_platform=source_platform,
            source_capture_type="ruling" if source_platform == "asa" else "ad_library_entry",
            ad_observed_status="archived" if source_platform in {"asa", "ftc"} else "unknown",
            source_type="blind_public_candidate",
            source_tier="tier_2_public_platform_case",
            source_org=_source_org(source_platform),
            source_title=source_title,
            source_url=_source_url(source_platform, query),
            label_basis="Public web source or ad-library search paraphrased into a blind holdout row.",
            label_confidence="medium",
            label_rationale=rationale,
            policy_areas=policy_areas,
            outcome_source="internal_adjudication",
            expected_decision="needs_review",
            expected_policy_ids=policy_ids,
            platform=platform,
            industry=industry,
            headline=headline,
            body=body,
            cta=cta,
            landing_page_html=_mismatch_page() if policy_ids == ["landing_page_offer_mismatch"] else _simple_page(headline, body),
        )
        for (
            row_id,
            source_platform,
            platform,
            industry,
            headline,
            body,
            cta,
            policy_ids,
            policy_areas,
            rationale,
            query,
            source_title,
        ) in cases
    ]


def high_risk_rows() -> list[dict[str, Any]]:
    cases = [
        ("blind_ftc_nextmed_glp1_high_risk", "ftc", "regulator_case", "FTC", "FTC NextMed weight-loss case", "https://www.ftc.gov/node/88624", "2025-07-14", "google", "health", "Lose 50 pounds with GLP-1 telehealth", "Weight loss program members lose 50 pounds with prescription support. Start a free trial before the offer expires today and book a clinic appointment online.", "Start free trial", ["weight_loss_claim", "google_health_restricted_category", "google_misrepresentation_risk", "fake_urgency_scarcity"], ["health_claims", "platform_policy", "misrepresentation"], "Telehealth weight-loss copy combines quantified outcome, prescription, free-trial, and urgency terms."),
        ("blind_ftc_sensa_fad_weight_loss_high_risk", "ftc", "regulator_case", "FTC", "FTC Sensa weight-loss settlement", "https://www.ftc.gov/news-events/news/press-releases/2014/01/sensa-three-other-marketers-fad-weight-loss-products-settle-ftc-charges-crackdown-deceptive", "2014-01-07", "google", "wellness", "Lose 30 pounds without changing meals", "Clinically proven and evidence-based weight loss supplement. Guaranteed results with a risk-free free trial.", "Try free trial", ["weight_loss_claim", "unsupported_health_claim", "wellness_claim_review", "guaranteed_outcome", "google_health_restricted_category", "google_misrepresentation_risk"], ["health_claims", "platform_policy", "misrepresentation"], "Weight-loss supplement ad uses quantified loss, substantiation language, and guarantee terms."),
        ("blind_ftc_enforma_exercise_bottle_high_risk", "ftc", "regulator_case", "FTC", "FTC Enforma weight-loss settlement", "https://www.ftc.gov/news-events/news/press-releases/2000/04/marketers-enforma-system-settle-ftc-charges-deceptive-advertising-their-weight-loss-products", "2000-04-25", "google", "wellness", "Burn fat while doing nothing", "Exercise in a bottle helps your body burn fat while you sleep, works for everyone, and needs no diet changes.", "Order system", ["weight_loss_claim", "guaranteed_outcome", "unsupported_health_claim"], ["health_claims"], "Effortless fat-burning and universal outcome promises are high-risk health claims."),
        ("blind_ftc_nutrimost_40_day_loss_high_risk", "ftc", "regulator_case", "FTC", "FTC NutriMost weight-loss settlement", "https://www.ftc.gov/news-events/news/press-releases/2017/04/marketers-nutrimost-ultimate-fat-loss-system-settle-ftc-charges", "2017-04-20", "google", "wellness", "Lose 40 pounds in 40 days", "Breakthrough technology and personalized supplements help users lose 40 pounds in 40 days.", "Start program", ["weight_loss_claim", "unsupported_health_claim", "google_health_restricted_category"], ["health_claims", "platform_policy"], "Fast quantified weight-loss and breakthrough supplement framing need high-risk routing."),
        ("blind_ftc_acai_fake_news_high_risk", "ftc", "regulator_case", "FTC", "FTC fake news acai berry case", "https://www.ftc.gov/news-events/news/press-releases/2013/02/ftc-permanently-stops-fake-news-website-operator-allegedly-deceived-consumers-about-acai-berry", "2013-02-07", "tiktok", "wellness", "Fake news weight loss berry secret", "Everyone is switching to this miracle berry capsule. It melts fat fast and uses a secret method.", "Watch story", ["weight_loss_claim", "tiktok_weight_management_claim", "tiktok_misleading_content", "brand_safety_misinformation"], ["health_claims", "platform_policy", "brand_safety"], "Fake-news, miracle, secret-method, and fat-loss framing are high-risk."),
        ("blind_ftc_pure_green_coffee_high_risk", "ftc", "regulator_case", "FTC", "FTC Pure Green Coffee judgment", "https://www.ftc.gov/news-events/news/press-releases/2016/11/ftc-wins-summary-judgment-against-pitchman-deceptive-green-coffee-weight-loss-ads-30-million", "2016-11-14", "tiktok", "wellness", "Miracle green coffee melts fat", "A secret green coffee capsule melts fat and helps users lose weight with instant results.", "Watch story", ["weight_loss_claim", "tiktok_weight_management_claim", "tiktok_misleading_content", "brand_safety_misinformation"], ["health_claims", "platform_policy", "brand_safety"], "Miracle weight-loss and instant-result claims map to high-risk platform and health policies."),
        ("blind_ftc_tarr_fake_trial_high_risk", "ftc", "regulator_case", "FTC", "FTC Tarr deceptive health products case", "https://www.ftc.gov/news-events/press-releases/2017/11/internet-marketers-dietary-supplement-skincare-products-banned", "2017-11-15", "google", "wellness", "Risk-free wrinkle and weight trial", "Risk-free free trial for a supplement that melts fat and delivers instant results before the limited time offer ends.", "Start trial", ["weight_loss_claim", "guaranteed_outcome", "google_misrepresentation_risk", "fake_urgency_scarcity"], ["health_claims", "platform_policy", "misrepresentation"], "Free-trial, instant-result, and fat-loss claims create high-risk misrepresentation and health risk."),
        ("blind_ftc_peel_patch_high_risk", "ftc", "regulator_case", "FTC", "FTC Peel Away the Pounds patch case", "https://www.ftc.gov/node/41409", "2004-01-09", "google", "wellness", "Patch helps lose pounds each week", "Wear this patch to lose 3 to 5 pounds per week without changing meals or exercise.", "Try patch", ["weight_loss_claim", "google_health_restricted_category"], ["health_claims", "platform_policy"], "Patch-based quantified weight-loss claims are high-risk."),
        ("blind_ftc_goodrx_health_data_high_risk", "ftc", "regulator_case", "FTC", "FTC GoodRx health data advertising order", "https://www.ftc.gov/news-events/news/press-releases/2023/02/ftc-enforcement-action-bar-goodrx-sharing-consumers-sensitive-health-info-advertising", "2023-02-01", "google", "health", "Prescription discount reminders for patients", "Use health app prescription searches and health data to retarget patient audiences with pharmacy discount ads.", "Get coupon", ["ftc_health_breach_notification_indicator", "washington_mhmda_indicator", "ccpa_sensitive_health_indicator", "hipaa_marketing_review", "hipaa_tracking_technology_review", "tracking_pixel_risk", "google_health_restricted_category"], ["privacy", "platform_policy"], "Health app, patient, prescription, and tracker context requires high-risk privacy review.", _health_tracking_page("Prescription discount reminders")),
        ("blind_ftc_betterhelp_health_ads_high_risk", "ftc", "regulator_case", "FTC", "FTC BetterHelp health data advertising order", "https://www.ftc.gov/news-events/news/press-releases/2023/03/ftc-proposes-order-banning-betterhelp-sharing-consumers-health-data-advertising", "2023-03-02", "google", "health", "Therapy provider retargeting campaign", "Retarget patient audiences after therapy appointment searches and health condition form submissions.", "Book appointment", ["hipaa_marketing_review", "hipaa_tracking_technology_review", "tracking_pixel_risk", "health_form_tracking_risk", "ccpa_sensitive_health_indicator"], ["privacy", "platform_policy"], "Therapy, patient, appointment, health-condition, and tracker context creates high-risk privacy review.", _health_tracking_page("Therapy appointment search")),
        ("blind_ftc_premom_fertility_sdk_high_risk", "ftc", "regulator_case", "FTC", "FTC Premom fertility app health data case", "https://www.ftc.gov/news-events/news/press-releases/2023/05/ftc-says-premom-shared-users-sensitive-health-data-google-china-based-marketing-analytics-firms", "2023-05-17", "google", "wellness", "Fertility app sync reminders", "Sync your data in a health app using reproductive health insights and precise geolocation reminders.", "Sync data", ["ftc_health_breach_notification_indicator", "washington_mhmda_indicator", "ccpa_sensitive_health_indicator"], ["privacy"], "Reproductive health, health app, data sync, and geolocation context is high-risk."),
        ("blind_ftc_cerebral_tracking_high_risk", "ftc", "regulator_case", "FTC", "FTC Cerebral health information case", "https://www.ftc.gov/news-events/news/press-releases/2024/04/ftc-says-online-mental-health-company-cerebral-shared-consumers-sensitive-personal-health-information", "2024-04-15", "google", "health", "ADHD appointment intake campaign", "Optimize ads from completed intake forms for patients seeking ADHD medical treatment and clinic appointment scheduling.", "Book appointment", ["hipaa_marketing_review", "hipaa_tracking_technology_review", "tracking_pixel_risk", "health_form_tracking_risk", "ccpa_sensitive_health_indicator"], ["privacy", "platform_policy"], "Patient intake, medical treatment, clinic appointment, and tracker context requires high-risk review.", _health_tracking_page("ADHD medical treatment")),
        ("blind_asa_angel_clinic_injection_high_risk", "asa", "ruling", "ASA/CAP", "The Angel Clinic ASA ruling", "https://www.asa.org.uk/rulings/the-angel-clinic-a22-1176082-the-angel-clinic.html", "2023-01-11", "google", "health", "Weekly weight loss injection appointments", "Medical clinic appointment for prescription weight loss treatment. Only 10 spots left; see the difference in before and after transformation photos.", "Message clinic", ["google_health_restricted_category", "weight_loss_claim", "before_after_claim", "fake_urgency_scarcity"], ["health_claims", "platform_policy", "misrepresentation"], "Prescription weight-loss treatment, scarcity, and before-after framing require high-risk routing."),
        ("blind_asa_hexpress_weight_pen_high_risk", "asa", "ruling", "ASA/CAP", "Hexpress Healthcare ASA ruling", "https://www.asa.org.uk/rulings/hexpress-healthcare-ltd-a24-1264776-hexpress-healthcare-ltd.html", "2025-07-09", "google", "health", "Clinically backed weight loss pen treatment", "Access once-weekly prescription weight loss treatment after a quick online clinic appointment.", "Start consultation", ["unsupported_health_claim", "weight_loss_claim", "google_health_restricted_category"], ["health_claims", "platform_policy"], "Prescription weight-loss treatment and clinical claim framing are high-risk."),
        ("blind_google_credit_repair_high_risk", "google_ads_transparency", "ad_library_entry", "Google Ads Transparency Center", "Google credit repair ad-library search", _source_url("google_ads_transparency", "guaranteed approval credit repair"), None, "google", "finance", "Guaranteed approval credit repair", "Fix your credit fast with guaranteed approval and no fees before enrollment.", "Apply now", ["guaranteed_outcome", "google_misrepresentation_risk", "google_financial_claim_review"], ["finance", "platform_policy", "misrepresentation"], "Credit repair copy promises guaranteed approval and no-fee terms."),
        ("blind_google_risk_free_investment_high_risk", "google_ads_transparency", "ad_library_entry", "Google Ads Transparency Center", "Google investment ad-library search", _source_url("google_ads_transparency", "risk free investment double money"), None, "google", "finance", "Risk-free investment doubles your money", "Start a risk-free investment plan that can double your money after signup.", "Start plan", ["guaranteed_outcome", "google_financial_claim_review"], ["finance", "platform_policy"], "Finance copy promises risk-free investment and doubled money."),
        ("blind_linkedin_double_salary_high_risk", "linkedin_ad_library", "ad_library_entry", "LinkedIn Ad Library", "LinkedIn salary outcome search", _source_url("linkedin_ad_library", "double your salary"), None, "linkedin", "general", "Double your salary with this system", "Use our career workflow and double your salary after a few weeks of outreach.", "Start system", ["linkedin_professional_claim_review"], ["platform_policy", "misrepresentation"], "Professional ad makes an unqualified salary outcome promise."),
        ("blind_linkedin_recent_grads_high_risk", "linkedin_ad_library", "ad_library_entry", "LinkedIn Ad Library", "LinkedIn recent graduates hiring search", _source_url("linkedin_ad_library", "recent graduates only hiring"), None, "linkedin", "general", "Analyst roles for recent graduates only", "Promote analyst hiring to recent graduates only and exclude other applicants.", "Apply now", ["linkedin_sensitive_targeting", "linkedin_discrimination_risk"], ["platform_policy"], "Recent-graduates-only employment copy creates discrimination and sensitive-targeting risk."),
        ("blind_linkedin_native_speaker_high_risk", "linkedin_ad_library", "ad_library_entry", "LinkedIn Ad Library", "LinkedIn native speaker hiring search", _source_url("linkedin_ad_library", "must be native speaker job ad"), None, "linkedin", "general", "Support roles must be native speaker", "Hiring for support roles with a must be native speaker requirement in the ad.", "Apply now", ["linkedin_discrimination_risk"], ["platform_policy"], "Native-speaker requirement creates employment discrimination review risk."),
        ("blind_linkedin_medical_condition_targeting_high_risk", "linkedin_ad_library", "ad_library_entry", "LinkedIn Ad Library", "LinkedIn medical condition targeting search", _source_url("linkedin_ad_library", "medical condition resource targeting"), None, "linkedin", "general", "Support group resource for medical condition", "Target members by medical condition and invite them to a resource webinar.", "Register", ["linkedin_sensitive_targeting"], ["platform_policy", "privacy"], "Medical-condition targeting is high-risk sensitive targeting."),
        ("blind_meta_housing_exclusion_high_risk", "meta_ad_library", "ad_library_entry", "Meta Ad Library", "Meta housing exclusion search", _source_url("meta_ad_library", "housing young professionals only religion ethnicity"), None, "linkedin", "general", "Luxury apartments for young professionals only", "Promote apartment listings to young professionals only while excluding users by religion and ethnicity.", "Apply today", ["linkedin_sensitive_targeting", "linkedin_discrimination_risk", "brand_safety_sensitive_social_issue"], ["platform_policy", "brand_safety"], "Housing campaign copy references exclusion by sensitive attributes."),
        ("blind_iab_violent_adjacency_high_risk", "meta_ad_library", "ad_library_entry", "Meta Ad Library", "Violence adjacency ad-library search", _source_url("meta_ad_library", "violent assault weapon coverage ads"), None, "google", "general", "Run ads beside violent breaking news", "Place the campaign near coverage of a violent assault and weapon investigation.", "Request inventory", ["brand_safety_violence"], ["brand_safety"], "Violent assault and weapon adjacency is high-severity brand-safety risk."),
        ("blind_iab_adult_adjacency_high_risk", "google_ads_transparency", "ad_library_entry", "Google Ads Transparency Center", "Adult adjacency ad-library search", _source_url("google_ads_transparency", "adult explicit entertainment inventory"), None, "google", "general", "Advertise beside adult entertainment reviews", "Buy inventory next to adult entertainment pages with explicit discussion threads.", "Request inventory", ["brand_safety_adult_content"], ["brand_safety"], "Adult and explicit content adjacency is high-severity brand-safety risk."),
        ("blind_iab_tragedy_conflict_high_risk", "meta_ad_library", "ad_library_entry", "Meta Ad Library", "Tragedy conflict ad-library search", _source_url("meta_ad_library", "war disaster death coverage ads"), None, "google", "general", "Promote offer near war disaster coverage", "Place product ads beside war, disaster, and death coverage during breaking news.", "Request inventory", ["brand_safety_tragedy_conflict"], ["brand_safety"], "War, disaster, and death coverage adjacency is high-risk."),
        ("blind_iab_misinformation_cure_high_risk", "tiktok_ccl", "ad_library_entry", "TikTok Commercial Content Library", "Miracle cure CCL search", _source_url("tiktok_ccl", "miracle cure conspiracy supplement"), None, "tiktok", "wellness", "Miracle cure conspiracy supplement", "A miracle cure supplement prevents disease and exposes the health conspiracy everyone is sharing.", "Watch now", ["medical_cure_claim", "unsupported_health_claim", "brand_safety_misinformation", "tiktok_misleading_content"], ["health_claims", "brand_safety", "platform_policy"], "Medical cure and conspiracy/misinformation framing create critical review risk."),
        ("blind_tiktok_detox_tea_creator_high_risk", "tiktok_ccl", "ad_library_entry", "TikTok Commercial Content Library", "Detox tea creator CCL search", _source_url("tiktok_ccl", "detox tea lose 20 pounds promo code"), None, "tiktok", "wellness", "Sponsored detox tea weight loss story", "Paid partnership creator says use my promo code to lose 20 pounds with this tea.", "Use promo code", ["weight_loss_claim", "tiktok_weight_management_claim", "missing_affiliate_or_sponsor_disclosure", "tiktok_disclosure_risk"], ["health_claims", "platform_policy", "disclosure"], "Creator copy combines sponsored promo-code disclosure risk with quantified weight-loss claims."),
        ("blind_tiktok_skinny_secret_high_risk", "tiktok_ccl", "ad_library_entry", "TikTok Commercial Content Library", "Skinny secret CCL search", _source_url("tiktok_ccl", "skinny secret instant body transformation"), None, "tiktok", "wellness", "Skinny secret body transformation", "This secret routine gives instant body transformation results and everyone is switching.", "Watch routine", ["tiktok_weight_management_claim", "tiktok_misleading_content", "weight_loss_claim"], ["health_claims", "platform_policy"], "Body-image, instant, secret, and everyone-is-switching framing are high-risk."),
        ("blind_google_no_side_effects_supplement_high_risk", "google_ads_transparency", "ad_library_entry", "Google Ads Transparency Center", "No side effects supplement search", _source_url("google_ads_transparency", "doctor recommended supplement no side effects"), None, "google", "health", "Doctor recommended supplement with no side effects", "Doctor recommended supplement works for everyone with no side effects and instant results.", "Shop supplement", ["unsupported_health_claim", "guaranteed_outcome", "google_health_restricted_category"], ["health_claims", "platform_policy"], "Doctor-recommended supplement and no-side-effects claims are high-risk."),
        ("blind_google_patient_retargeting_high_risk", "google_ads_transparency", "ad_library_entry", "Google Ads Transparency Center", "Patient retargeting search", _source_url("google_ads_transparency", "patient retargeting appointment google analytics"), None, "google", "health", "Patient appointment retargeting campaign", "Retarget patient appointment visitors after they book appointment slots with a clinic provider.", "Book appointment", ["hipaa_marketing_review", "hipaa_tracking_technology_review", "tracking_pixel_risk", "health_form_tracking_risk", "google_health_restricted_category"], ["privacy", "platform_policy"], "Patient appointment retargeting combines healthcare, patient, appointment, and tracker signals.", _health_tracking_page("Patient appointment retargeting")),
        ("blind_google_biometric_health_app_high_risk", "google_ads_transparency", "ad_library_entry", "Google Ads Transparency Center", "Biometric health app search", _source_url("google_ads_transparency", "biometric health app precise geolocation"), None, "google", "wellness", "Biometric health app location reminders", "Sync your data with a health app using biometric insights and precise geolocation.", "Sync data", ["ftc_health_breach_notification_indicator", "washington_mhmda_indicator", "ccpa_sensitive_health_indicator"], ["privacy"], "Health app, biometric, and precise geolocation language creates sensitive data review risk."),
    ]
    return [
        _row(
            row_id=row_id,
            source_platform=source_platform,
            source_capture_type=source_capture_type,
            ad_observed_status="archived" if source_capture_type in {"regulator_case", "ruling"} else "unknown",
            source_type=source_capture_type,
            source_tier="tier_4_synthetic_from_real_pattern" if source_capture_type in {"regulator_case", "ruling"} else "tier_2_public_platform_case",
            source_org=source_org,
            source_title=source_title,
            source_url=source_url,
            case_date=case_date,
            label_basis="Public web source paraphrased into a blind holdout high-risk row.",
            label_confidence="high" if source_capture_type in {"regulator_case", "ruling"} else "medium",
            label_rationale=rationale,
            policy_areas=policy_areas,
            outcome_source="public_enforcement" if source_capture_type == "regulator_case" else ("public_ruling" if source_capture_type == "ruling" else "internal_adjudication"),
            expected_decision="high_risk",
            expected_policy_ids=policy_ids,
            platform=platform,
            industry=industry,
            headline=headline,
            body=body,
            cta=cta,
            landing_page_html=landing_page_html if landing_page_html is not None else _simple_page(headline, body),
        )
        for (
            row_id,
            source_platform,
            source_capture_type,
            source_org,
            source_title,
            source_url,
            case_date,
            platform,
            industry,
            headline,
            body,
            cta,
            policy_ids,
            policy_areas,
            rationale,
            *landing_page,
        ) in cases
        for landing_page_html in [landing_page[0] if landing_page else None]
    ]


def _row(
    *,
    row_id: str,
    source_platform: str,
    source_capture_type: str,
    ad_observed_status: str,
    source_type: str,
    source_tier: str,
    source_org: str,
    source_title: str,
    source_url: str,
    label_basis: str,
    label_confidence: str,
    label_rationale: str,
    policy_areas: list[str],
    outcome_source: str,
    expected_decision: str,
    expected_policy_ids: list[str],
    platform: str,
    industry: str,
    headline: str,
    body: str,
    cta: str,
    landing_page_html: str,
    adjudication_status: str = "accepted",
    adjudicator_notes: str | None = None,
    rule_tuning_holdout: bool = True,
    case_date: str | None = None,
    jurisdiction: str = "US",
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": row_id,
        "source_type": source_type,
        "source_platform": source_platform,
        "source_capture_type": source_capture_type,
        "source_org": source_org,
        "source_title": source_title,
        "source_url": source_url,
        "source_tier": source_tier,
        "ad_observed_status": ad_observed_status,
        "adjudication_status": adjudication_status,
        "adjudicator_notes": adjudicator_notes
        or f"Accepted as a blind holdout {expected_decision} row; do not tune deterministic rules from this row before baseline reporting.",
        "rule_tuning_holdout": rule_tuning_holdout,
        "jurisdiction": jurisdiction,
        "accessed_at": ACCESSED_AT,
        "label_basis": label_basis,
        "label_confidence": label_confidence,
        "label_rationale": label_rationale,
        "provenance": f"{source_url} accessed {ACCESSED_AT}; paraphrased into deterministic local blind eval input.",
        "policy_areas": policy_areas,
        "copyright_status": "paraphrased",
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


def _rejected_candidates(accepted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rejected: list[dict[str, Any]] = []
    for index, row in enumerate(accepted[:60], start=1):
        clone = json.loads(json.dumps(row))
        clone["id"] = f"rejected_{row['id']}"
        clone["source_url"] = f"{row['source_url']}#rejected-candidate-{index}"
        clone["adjudication_status"] = "rejected"
        clone["adjudicator_notes"] = "Rejected from v1 final set to preserve exact label balance and avoid over-representing the same source family."
        clone["rule_tuning_holdout"] = False
        rejected.append(clone)
    return rejected


def _source_url(source_platform: str, query: str) -> str:
    encoded = quote(query)
    if source_platform == "meta_ad_library":
        return f"https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=US&q={encoded}"
    if source_platform == "google_ads_transparency":
        return f"https://adstransparency.google.com/?region=US&query={encoded}"
    if source_platform == "tiktok_ccl":
        return f"https://library.tiktok.com/ads?region=GB&query={encoded}"
    if source_platform == "linkedin_ad_library":
        return f"https://www.linkedin.com/ad-library/search?keyword={encoded}"
    if source_platform == "asa":
        return f"https://www.asa.org.uk/advice-online/{query}.html"
    if source_platform == "ftc":
        return f"https://www.ftc.gov/search?search={encoded}"
    raise ValueError(f"unknown source platform: {source_platform}")


def _source_org(source_platform: str) -> str:
    return {
        "ftc": "FTC",
        "asa": "ASA/CAP",
        "meta_ad_library": "Meta Ad Library",
        "google_ads_transparency": "Google Ads Transparency Center",
        "tiktok_ccl": "TikTok Commercial Content Library",
        "linkedin_ad_library": "LinkedIn Ad Library",
        "public_brand_page": "Public brand page",
    }[source_platform]


def _simple_page(headline: str, body: str) -> str:
    return f"<html><title>{headline}</title><h1>{headline}</h1><p>{body}</p></html>"


def _mismatch_page() -> str:
    return "<html><title>Resource center</title><h1>Planning resource</h1><p>Read general onboarding notes and team setup guidance.</p></html>"


def _health_tracking_page(title: str) -> str:
    return (
        f"<html><title>{title}</title><h1>{title}</h1>"
        "<p>Patients can book appointment slots and share health condition details with a clinic provider.</p>"
        "<form><label>Intake form</label><input name='health condition'></form>"
        "<script src='https://www.google-analytics.com/analytics.js'></script>"
        "<script>conversion event client id</script></html>"
    )


def _normalize(value: str) -> str:
    return " ".join("".join(ch.lower() if ch.isalnum() else " " for ch in value).split())


if __name__ == "__main__":
    raise SystemExit(main())
