from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SEED_PATH = ROOT / "evals" / "datasets" / "seed_ads.jsonl"
OUTPUT_PATH = ROOT / "evals" / "datasets" / "rule_benchmark_v1.jsonl"
TARGET_EXAMPLES = 213


def main() -> int:
    rows = build_rows()
    OUTPUT_PATH.write_text(_to_jsonl(rows), encoding="utf-8")
    print(f"Wrote {len(rows)} examples to {OUTPUT_PATH}")
    return 0


def build_rows() -> list[dict[str, Any]]:
    rows = _load_seed_rows()
    rows.extend(_approved_rows())
    rows.extend(_high_risk_health_rows())
    rows.extend(_review_health_rows())
    rows.extend(_privacy_rows())
    rows.extend(_finance_rows())
    rows.extend(_linkedin_rows())
    rows.extend(_disclosure_rows())
    rows.extend(_meta_rows())
    rows.extend(_brand_safety_rows())
    rows.extend(_landing_page_rows())
    _validate_rows(rows)
    return rows


def _load_seed_rows() -> list[dict[str, Any]]:
    return [json.loads(line) for line in SEED_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def _approved_rows() -> list[dict[str, Any]]:
    saas = [
        ("Campaign calendar for lean teams", "Coordinate briefs, tasks, and launch approvals in one workspace.", "Request demo"),
        ("Creative QA checklist", "Review assets, copy, and routing notes before the next launch.", "Download"),
        ("Weekly reporting workspace", "Bring spend, pacing, and learning notes into a single dashboard.", "See templates"),
        ("Launch notes for marketers", "Share approval notes and creative learnings with your team.", "Get the guide"),
        ("Content planning board", "Plan posts, experiments, and reviews without changing ad accounts.", "Try board"),
        ("Brief builder for agencies", "Create repeatable client briefs and status updates.", "Start planning"),
        ("Landing page QA reminders", "Track copy, links, and analytics checks before publishing.", "Get checklist"),
        ("Marketing ops calendar", "Organize launches, owners, and due dates for campaign teams.", "View sample"),
        ("Ad testing workspace", "Compare concepts and notes before sending assets for review.", "Start workspace"),
        ("Budget pacing templates", "Document spend plans and vendor notes for monthly reviews.", "Download"),
        ("Creative intake form", "Collect campaign details, references, and launch dates in one place.", "Create form"),
        ("Client approval tracker", "Follow review status and next steps across campaigns.", "See workflow"),
        ("Experiment archive", "Save hypotheses, results, and next-test ideas for your team.", "Browse examples"),
        ("Media plan summary", "Build a clear planning doc for channels, audiences, and dates.", "Use template"),
        ("Content calendar export", "Prepare launch notes and timelines for stakeholders.", "Export sample"),
    ]
    general = [
        ("Neighborhood event calendar", "Find workshops, volunteer days, and community classes.", "Browse events"),
        ("Recipe newsletter sponsor", "Reach readers planning weeknight meals and grocery lists.", "Sponsor"),
        ("Outdoor gear checklist", "Pack for weekend trips with a simple preparation list.", "Download"),
        ("Book club discussion guide", "Get prompts and schedules for your next group meeting.", "Read guide"),
        ("Design portfolio templates", "Organize case studies, drafts, and client notes.", "View templates"),
        ("Home office setup ideas", "Compare desks, lighting, and cable organization tips.", "Explore"),
        ("Local services directory", "Find appointment times, reviews, and contact details.", "Search"),
        ("Travel planning worksheet", "Map destinations, budgets, and packing notes.", "Get worksheet"),
        ("Podcast production notes", "Plan topics, guests, and recording checklists.", "Download notes"),
        ("Garden maintenance calendar", "Track planting, watering, and seasonal tasks.", "Open calendar"),
        ("Creator media kit builder", "Collect rates, audience notes, and sample work.", "Build kit"),
        ("Small business launch guide", "Prepare vendor lists, milestones, and outreach tasks.", "Read guide"),
        ("Team offsite planner", "Coordinate agendas, venues, and travel details.", "Start plan"),
        ("Retail display checklist", "Review signage, layout, and inventory notes.", "Download list"),
        ("Newsletter planning board", "Plan issues, sections, and publishing dates.", "Start board"),
    ]
    wellness = [
        ("Hydration habit reminders", "Build a simple water and break routine for busy days.", "Learn more"),
        ("Evening stretch guide", "Gentle mobility ideas for winding down after work.", "Download"),
        ("Mindful meal planning", "Organize grocery lists and weekday prep notes.", "Get planner"),
        ("Walking group schedule", "Coordinate local walks and social check-ins.", "Join list"),
        ("Desk break timer", "Set reminders for posture, breathing, and short breaks.", "Try timer"),
        ("Sleep routine checklist", "Create a calmer bedtime process with practical reminders.", "Get checklist"),
        ("Team wellness calendar", "Plan voluntary activities and resource links for employees.", "View calendar"),
        ("Fitness class organizer", "Track class times, locations, and signup notes.", "See schedule"),
        ("Stress journal template", "Reflect on routines, priorities, and small adjustments.", "Download"),
        ("Healthy lunch ideas", "Save recipes, prep steps, and grocery notes.", "Browse ideas"),
    ]
    rows = []
    rows.extend(_fixed_rows("benchmark-approved-saas", "linkedin", "saas", saas[:9], "approved", []))
    rows.extend(_fixed_rows("benchmark-approved-general", "google", "general", general[:9], "approved", []))
    rows.extend(_fixed_rows("benchmark-approved-wellness", "google", "wellness", wellness[:6], "approved", []))
    return rows


def _high_risk_health_rows() -> list[dict[str, Any]]:
    weight_rows = [
        ("Lose 12 pounds with our coaching plan", "Track meals and burn fat with daily reminders.", "Start now"),
        ("Belly fat challenge for summer", "A simple routine built around weight loss goals.", "Join today"),
        ("Body transformation plan", "Support your program with before meals and burn fat tips.", "Learn more"),
        ("Lose weight with daily prompts", "Build a routine around body transformation milestones.", "Get app"),
        ("Burn fat during busy weeks", "Short lessons for weight loss and habit tracking.", "Start"),
        ("Lose 18 pounds with guided check-ins", "Daily planning for nutrition and activity.", "Try plan"),
        ("Belly fat support program", "Track workouts, meals, and body transformation notes.", "Request details"),
        ("Weight loss accountability kit", "Plan progress notes and reminders with a coach.", "Download"),
        ("Lose 10 pounds challenge", "Set weekly goals and review progress with prompts.", "Join challenge"),
        ("Body transformation journal", "Record meals, activity, and weight loss reflections.", "Open journal"),
        ("Burn fat meal planner", "Create shopping lists for your weight loss routine.", "Use planner"),
        ("Lose 15 pounds tracker", "Organize check-ins and habit milestones.", "Start tracker"),
        ("Belly fat habit guide", "Daily reminders for workouts and meal planning.", "Get guide"),
        ("Weight loss text reminders", "Follow body transformation prompts each morning.", "Sign up"),
        ("Lose 20 pounds challenge", "Plan activity, meals, and weekly review notes.", "Join"),
        ("Burn fat workout calendar", "Schedule weight loss sessions and check-ins.", "View calendar"),
    ]
    clinic_rows = [
        ("Clinic appointment scheduler", "Book with a provider and manage patient follow-up.", "Book appointment"),
        ("Telehealth appointment reminders", "Coordinate provider notes and book appointment check-ins for patients.", "Request demo"),
        ("Medical clinic intake workflow", "Collect intake form details before a provider visit.", "Start intake"),
        ("Prescription support visit", "Meet a provider and book appointment follow-up for patients.", "Schedule"),
        ("Health insurance appointment help", "Prepare patient notes and book appointment follow-up.", "Learn more"),
        ("Medical device consultation", "Book appointment details with a clinic provider and patient records.", "Book now"),
        ("Pharmacy refill coordination", "Share patient details before a book appointment request.", "Start request"),
        ("Clinic appointment follow-up portal", "Manage book appointment reminders and medical record tasks.", "Open portal"),
        ("Telehealth provider visit", "Book appointment reminders for patient care.", "Get started"),
        ("Medical treatment planning", "Discuss options with a clinic provider.", "Schedule call"),
        ("Patient appointment checklist", "Prepare questions for your provider visit.", "Download"),
        ("Clinic appointment alerts", "Coordinate provider availability and patient reminders.", "Turn on alerts"),
    ]
    weight_rows = weight_rows[:10]
    clinic_rows = clinic_rows[:8]
    rows = []
    rows.extend(
        _fixed_rows(
            "benchmark-health-weight",
            "tiktok",
            "health",
            weight_rows,
            "high_risk",
            ["weight_loss_claim", "tiktok_weight_management_claim"],
        )
    )
    rows.extend(
        _fixed_rows(
            "benchmark-health-clinic",
            "google",
            "health",
            clinic_rows,
            "high_risk",
            ["google_health_restricted_category", "hipaa_marketing_review", "health_form_tracking_risk"],
        )
    )
    return rows


def _review_health_rows() -> list[dict[str, Any]]:
    rows = [
        ("Science-backed breathing guide", "Short practices for building a calmer routine.", "Read more"),
        ("Evidence-based mobility tips", "Simple stretches for busy teams.", "Download"),
        ("Backed by science sleep habits", "Create a consistent evening checklist.", "Get guide"),
        ("Science-backed hydration ideas", "Plan reminders and practical daily routines.", "Learn more"),
        ("Evidence-based meal planning", "Organize weekly prep and shopping notes.", "Start"),
        ("Backed by science focus breaks", "Build a repeatable break schedule.", "Try timer"),
        ("Science-backed meditation prompts", "Reflect on stress, routines, and priorities.", "Open prompts"),
        ("Evidence-based desk stretch routine", "Gentle movement ideas for workdays.", "View routine"),
        ("Backed by science wellness newsletter", "Monthly tips for calmer planning.", "Subscribe"),
        ("Science-backed habit calendar", "Track voluntary wellness activities.", "Use calendar"),
        ("Evidence-based sleep checklist", "Prepare an evening routine with reminders.", "Download"),
        ("Backed by science nutrition notes", "Organize meal ideas and prep steps.", "Get notes"),
    ]
    return _fixed_rows(
        "benchmark-wellness-evidence",
        "google",
        "wellness",
        rows,
        "needs_review",
        ["wellness_claim_review"],
    )


def _privacy_rows() -> list[dict[str, Any]]:
    rows = [
        ("Wellness newsletter signup", "Join a weekly routine planning list.", "Sign up"),
        ("Sleep tips email course", "Get gentle reminders for evening routines.", "Join course"),
        ("Hydration habit signup", "Receive daily planning prompts.", "Subscribe"),
        ("Mindfulness checklist download", "Enter email to get the guide.", "Download"),
        ("Fitness class reminders", "Get schedule alerts and preparation notes.", "Get alerts"),
        ("Wellness challenge updates", "Join the list for voluntary habit prompts.", "Join list"),
        ("Meal planning newsletter", "Save recipes and weekly prep reminders.", "Sign up"),
        ("Desk stretch reminders", "Receive short break prompts by email.", "Subscribe"),
        ("Walking group signup", "Get schedule updates and event notes.", "Join"),
        ("Stress journal download", "Enter email for the template.", "Download"),
        ("Sleep routine form", "Share your email for a checklist.", "Get checklist"),
        ("Wellness tips form", "Sign up for practical weekly ideas.", "Submit"),
    ]
    landing_page = (
        "<html><head><script src='https://connect.facebook.net/en_US/fbevents.js'></script></head>"
        "<body><h1>Email signup</h1><form><label>Email signup</label><input name='email'></form></body></html>"
    )
    return [
        _row(
            f"benchmark-privacy-tracking-{index:03d}",
            "google",
            "wellness",
            headline,
            body,
            cta,
            "needs_review",
            ["tracking_pixel_risk", "health_form_tracking_risk"],
            landing_page_html=landing_page,
        )
        for index, (headline, body, cta) in enumerate(rows, start=1)
    ]


def _finance_rows() -> list[dict[str, Any]]:
    items = [
        (("Guaranteed approval loan review", "Fix your credit with no fees listed up front.", "Apply"), ["google_misrepresentation_risk", "google_financial_claim_review", "guaranteed_outcome"]),
        (("Risk-free investment briefing", "Double your money with a secret method.", "Start"), ["google_financial_claim_review", "google_misrepresentation_risk", "guaranteed_outcome"]),
        (("Credit repair sprint", "Guaranteed approval after the program.", "Join"), ["google_misrepresentation_risk", "google_financial_claim_review", "guaranteed_outcome"]),
        (("No fees debt plan", "Fix your credit fast with limited time terms.", "Learn more"), ["google_misrepresentation_risk", "google_financial_claim_review"]),
        (("Double your money workshop", "Review a risk-free investment strategy.", "Reserve seat"), ["google_financial_claim_review", "guaranteed_outcome"]),
        (("Guaranteed approval business card", "No fees and secret method for applicants.", "Apply now"), ["google_misrepresentation_risk", "google_financial_claim_review", "guaranteed_outcome"]),
        (("Fix your credit checklist", "Limited time access to our approval process.", "Download"), ["google_misrepresentation_risk", "google_financial_claim_review"]),
        (("Risk-free investment course", "Double your money with weekly lessons.", "Enroll"), ["google_financial_claim_review", "guaranteed_outcome"]),
        (("No fees credit offer", "Guaranteed approval for qualifying applicants.", "Apply"), ["google_misrepresentation_risk", "google_financial_claim_review", "guaranteed_outcome"]),
        (("Secret method investing guide", "Risk-free investment ideas for beginners.", "Get guide"), ["google_misrepresentation_risk", "google_financial_claim_review", "guaranteed_outcome"]),
        (("Credit score repair plan", "Fix your credit with guaranteed approval language.", "Start"), ["google_misrepresentation_risk", "google_financial_claim_review", "guaranteed_outcome"]),
        (("Double your money challenge", "No fees to join the investment training.", "Join"), ["google_misrepresentation_risk", "google_financial_claim_review"]),
    ]
    return [
        _row(
            f"benchmark-finance-google-{index:03d}",
            "google",
            "finance",
            headline,
            body,
            cta,
            "high_risk",
            expected_policy_ids,
        )
        for index, ((headline, body, cta), expected_policy_ids) in enumerate(items, start=1)
    ]


def _linkedin_rows() -> list[dict[str, Any]]:
    professional = [
        ("Double your salary coaching", "Prepare for interviews with a weekly plan.", "Apply"),
        ("Get hired instantly toolkit", "Optimize your resume and outreach sequence.", "Download"),
        ("10x productivity for analysts", "Plan workflows and reporting habits.", "Request demo"),
        ("Double your salary bootcamp", "Practice interview stories and negotiation scripts.", "Enroll"),
        ("Get hired instantly after training", "Follow daily application tasks.", "Start"),
        ("10x productivity dashboard", "Organize tasks, metrics, and team updates.", "Try"),
        ("Double your salary playbook", "Review compensation planning examples.", "Read"),
        ("Get hired instantly resume guide", "Use templates for outreach and interviews.", "Download"),
        ("10x productivity planning app", "Coordinate briefs and updates.", "Request access"),
        ("Double your salary webinar", "Join a professional coaching session.", "Register"),
    ]
    sensitive = [
        ("Analytics for young professionals only", "Dashboards for recent graduates only.", ["linkedin_sensitive_targeting", "linkedin_discrimination_risk"]),
        ("Hiring event for recent graduates only", "Roles for young professionals only.", ["linkedin_sensitive_targeting", "linkedin_discrimination_risk"]),
        ("Career group by age", "Community resources for a specific age cohort.", ["linkedin_sensitive_targeting"]),
        ("Benefits guide for pregnancy support", "Review workplace resources and policies.", ["linkedin_sensitive_targeting"]),
        (
            "Professional network by religion",
            "Join a group filtered around religion.",
            ["linkedin_sensitive_targeting", "brand_safety_sensitive_social_issue"],
        ),
        ("Recruiting campaign by ethnicity", "Segment outreach by ethnicity.", ["linkedin_sensitive_targeting"]),
        ("Wellness tool for disability support", "Resources for employees with a disability.", ["linkedin_sensitive_targeting"]),
        ("Native speaker hiring filter", "Applicants must be native speaker.", ["linkedin_discrimination_risk"]),
        ("Recent graduates only role alerts", "Subscribe for entry-level job posts.", ["linkedin_sensitive_targeting", "linkedin_discrimination_risk"]),
        ("Young professionals only membership", "Career resources for early-career workers.", ["linkedin_sensitive_targeting", "linkedin_discrimination_risk"]),
    ]
    rows = _fixed_rows(
        "benchmark-linkedin-professional",
        "linkedin",
        "saas",
        professional,
        "high_risk",
        ["linkedin_professional_claim_review"],
    )
    rows.extend(
        _row(
            f"benchmark-linkedin-sensitive-{index:03d}",
            "linkedin",
            "saas",
            headline,
            body,
            "Learn more",
            "high_risk",
            expected_policy_ids,
        )
        for index, (headline, body, expected_policy_ids) in enumerate(sensitive, start=1)
    )
    return rows


def _disclosure_rows() -> list[dict[str, Any]]:
    rows = [
        ("Sponsored morning routine", "Use my affiliate code for the partner product.", "Shop"),
        ("Paid partnership desk setup", "I may earn commission through this promo code.", "Use code"),
        ("Affiliate protein review", "This partner supplement is featured in my routine.", "Shop now"),
        ("Promo code for creator course", "Sponsored by the brand and includes commission.", "Enroll"),
        ("Paid partnership sleep tips", "Use my promo code for the featured product.", "Get offer"),
        ("Affiliate gear list", "Partner links may earn commission.", "Browse"),
        ("Sponsored skincare routine", "Use the creator promo code at checkout.", "Shop"),
        ("Partner supplement review", "Paid partnership details are in the caption.", "Learn more"),
        ("Commission-based product picks", "Affiliate links support the channel.", "View picks"),
        ("Promo code wellness haul", "Sponsored favorites from a brand partner.", "Use code"),
    ]
    return _fixed_rows(
        "benchmark-disclosure-tiktok",
        "tiktok",
        "creator",
        rows,
        "needs_review",
        ["tiktok_disclosure_risk", "missing_affiliate_or_sponsor_disclosure"],
    )


def _meta_rows() -> list[dict[str, Any]]:
    approved = [
        ("Campaign launch notes for teams", "Organize briefs, approvals, and next steps.", "Learn more"),
        ("Creative testing checklist", "Compare messages and asset notes before publishing.", "Download"),
        ("Retail planning calendar", "Track seasonal promotions, tasks, and owner notes.", "View calendar"),
        ("Wellness event schedule", "Find voluntary classes and preparation reminders.", "Browse events"),
    ]
    approved_near_miss = [
        (
            "Hiring pipeline dashboard",
            "Plan recruiting tasks and approval notes without advertising a specific role.",
            "Request demo",
            "saas",
        ),
        (
            "Insurance education webinar",
            "Learn how coverage terms work; no quote or application is offered.",
            "Register",
            "finance",
        ),
        (
            "Creator desk tour",
            "A personal workflow walkthrough with gear notes and editing tips.",
            "Watch",
            "creator",
        ),
        (
            "Mortgage calculator worksheet",
            "Estimate hypothetical payments for planning; no lender matching is provided.",
            "Download",
            "finance",
        ),
    ]
    creator_review = [
        ("Paid partnership desk setup", "Use my affiliate code for the partner product.", "Shop now"),
        ("Sponsored morning routine", "The partner product is featured with a promo code.", "Use code"),
        ("Affiliate creator toolkit", "This paid partnership includes setup templates.", "Download"),
        ("Partner product workflow", "Sponsored tips include affiliate resources.", "Learn more"),
    ]
    platform_review = [
        (
            "Compare credit card options",
            "Review eligibility, terms, disclosures, and 18+ targeting before you apply for credit.",
            "Learn more",
            ["meta_financial_services_authorization_review"],
            "finance",
        ),
        (
            "Mortgage planning guide",
            "Start a mortgage application with this credit offer and financial products and services checklist before applying.",
            "Download guide",
            ["meta_financial_services_authorization_review", "meta_special_ad_category_review"],
            "finance",
        ),
        (
            "Reproductive health appointment guide",
            "Family planning resources and contraception appointment preparation for adults 18+.",
            "Learn more",
            ["meta_health_wellness_age_targeting_review", "washington_mhmda_indicator"],
            "health",
        ),
        (
            "Hiring campaign checklist",
            "Plan compliant job opening creative and employment opportunity audience settings.",
            "Download",
            ["meta_special_ad_category_review"],
            "saas",
        ),
    ]
    high_risk = [
        (
            "Are you overweight? See a before and after transformation",
            "Our clinically proven supplement helps you lose 20 pounds and melts fat.",
            "Learn more",
            [
                "meta_personal_attributes_health",
                "meta_health_appearance_results",
                "unsupported_health_claim",
                "weight_loss_claim",
                "before_after_claim",
            ],
            "health",
        ),
        (
            "Tired of your symptoms? Try our transformation plan",
            "A clinical study routine supports dramatic results.",
            "Start today",
            [
                "meta_personal_attributes_health",
                "meta_health_appearance_results",
                "unsupported_health_claim",
                "before_after_claim",
            ],
            "health",
        ),
        (
            "Struggling with debt and bad credit?",
            "Explore a planning consultation for people behind on bills.",
            "Learn more",
            ["meta_personal_attributes_finance"],
            "finance",
        ),
        (
            "Are you broke after monthly bills?",
            "Review neutral budgeting resources for credit planning.",
            "Get guide",
            ["meta_personal_attributes_finance"],
            "finance",
        ),
        (
            "Tell us your symptoms before booking",
            "Submit your medical history and upload your diagnosis to find a provider match.",
            "Start intake",
            ["meta_private_information_request"],
            "health",
        ),
    ]

    rows = _fixed_rows("benchmark-meta-approved", "meta", "saas", approved, "approved", [])
    rows.extend(
        _row(
            f"benchmark-meta-approved-near-miss-{index:03d}",
            "meta",
            industry,
            headline,
            body,
            cta,
            "approved",
            [],
        )
        for index, (headline, body, cta, industry) in enumerate(approved_near_miss, start=1)
    )
    rows.extend(
        _fixed_rows(
            "benchmark-meta-creator",
            "meta",
            "creator",
            creator_review,
            "needs_review",
            ["meta_branded_content_disclosure", "missing_affiliate_or_sponsor_disclosure"],
        )
    )
    rows.extend(
        _row(
            f"benchmark-meta-review-{index:03d}",
            "meta",
            industry,
            headline,
            body,
            cta,
            "needs_review",
            expected_policy_ids,
        )
        for index, (headline, body, cta, expected_policy_ids, industry) in enumerate(platform_review, start=1)
    )
    rows.extend(
        _row(
            f"benchmark-meta-high-risk-{index:03d}",
            "meta",
            industry,
            headline,
            body,
            cta,
            "high_risk",
            expected_policy_ids,
        )
        for index, (headline, body, cta, expected_policy_ids, industry) in enumerate(high_risk, start=1)
    )
    return rows


def _brand_safety_rows() -> list[dict[str, Any]]:
    items = [
        ("Election night sponsorship", "Advertise beside political ballot analysis.", "brand_safety_politics", "needs_review"),
        ("Political campaign finance report", "Sponsor a newsletter about election rules.", "brand_safety_politics", "needs_review"),
        ("War update coverage", "Inventory around conflict and disaster updates.", "brand_safety_tragedy_conflict", "high_risk"),
        ("Disaster response article", "Run ads next to tragedy coverage.", "brand_safety_tragedy_conflict", "high_risk"),
        ("Hoax tracking newsletter", "Block conspiracy and misinformation placements.", "brand_safety_misinformation", "high_risk"),
        ("Fake news adjacency list", "Avoid misinformation around misinformation claims.", "brand_safety_misinformation", "high_risk"),
        ("Adult content placement", "Explicit inventory for restricted campaigns.", "brand_safety_adult_content", "high_risk"),
        ("Sexual content category", "Review adult adjacency and suitability controls.", "brand_safety_adult_content", "high_risk"),
        ("Violent news sponsorship", "Advertise near assault and weapon policy analysis.", "brand_safety_violence", "high_risk"),
        ("Weapon policy newsletter", "Coverage includes violence and public safety topics.", "brand_safety_violence", "high_risk"),
        ("Immigration issue research", "Download reporting on religion and race trends.", "brand_safety_sensitive_social_issue", "needs_review"),
        ("Gender identity policy brief", "Sponsor social issue research.", "brand_safety_sensitive_social_issue", "needs_review"),
        ("Boycott tracking brief", "Monitor controversial stories and brand fit.", "brand_safety_controversial_content", "needs_review"),
        ("Scandal update sponsorship", "Review outrage and boycott coverage.", "brand_safety_controversial_content", "needs_review"),
        ("Murder trial analysis", "Inventory beside violent crime reporting.", "brand_safety_violence", "high_risk"),
        ("Disaster fundraising coverage", "Sponsor updates after a public tragedy.", "brand_safety_tragedy_conflict", "high_risk"),
    ]
    return [
        _row(
            f"benchmark-brand-safety-{index:03d}",
            "google",
            "general",
            headline,
            body,
            "Review inventory",
            decision,
            [policy_id],
        )
        for index, (headline, body, policy_id, decision) in enumerate(items, start=1)
    ]


def _landing_page_rows() -> list[dict[str, Any]]:
    rows = [
        ("Clinically proven supplement discount", "Lose weight with our guaranteed plan."),
        ("Doctor recommended supplement sale", "Lose 10 pounds with a guaranteed routine."),
        ("Clinically backed weight loss offer", "Burn fat with a guaranteed supplement discount."),
        ("Supplement plan guaranteed", "Lose weight with clinically backed coaching."),
        ("Clinically proven weight loss trial", "Supplement plan with a guaranteed discount."),
        ("Doctor recommended weight plan", "Lose 12 pounds with a guaranteed supplement offer."),
        ("Clinically backed supplement starter kit", "Burn fat with our guaranteed routine."),
        ("Weight loss supplement discount", "Clinically proven guaranteed program for busy weeks."),
        ("Guaranteed supplement challenge", "Lose weight with clinical study check-ins."),
        ("Supplement sale for weight loss", "Doctor recommended plan with guaranteed support."),
    ]
    landing_page = "<html><body><h1>General lifestyle newsletter</h1><p>Recipes and travel notes.</p></body></html>"
    return [
        _row(
            f"benchmark-landing-mismatch-{index:03d}",
            "google",
            "health",
            headline,
            body,
            "Buy now",
            "high_risk",
            [
                "unsupported_health_claim",
                "guaranteed_outcome",
                "weight_loss_claim",
                "google_health_restricted_category",
                "landing_page_offer_mismatch",
            ],
            landing_page_html=landing_page,
        )
        for index, (headline, body) in enumerate(rows, start=1)
    ]


def _fixed_rows(
    prefix: str,
    platform: str,
    industry: str,
    items: list[tuple[str, str, str]],
    expected_decision: str,
    expected_policy_ids: list[str],
) -> list[dict[str, Any]]:
    return [
        _row(
            f"{prefix}-{index:03d}",
            platform,
            industry,
            headline,
            body,
            cta,
            expected_decision,
            expected_policy_ids,
        )
        for index, (headline, body, cta) in enumerate(items, start=1)
    ]


def _row(
    row_id: str,
    platform: str,
    industry: str,
    headline: str,
    body: str,
    cta: str,
    expected_decision: str,
    expected_policy_ids: list[str],
    *,
    landing_page_html: str | None = None,
) -> dict[str, Any]:
    input_payload: dict[str, Any] = {
        "platform": platform,
        "industry": industry,
        "headline": headline,
        "body": body,
        "cta": cta,
    }
    if landing_page_html is not None:
        input_payload["landing_page_html"] = landing_page_html
    return {
        "id": row_id,
        "input": input_payload,
        "expected_decision": expected_decision,
        "expected_policy_ids": expected_policy_ids,
    }


def _validate_rows(rows: list[dict[str, Any]]) -> None:
    ids = [row["id"] for row in rows]
    if len(rows) != TARGET_EXAMPLES:
        raise ValueError(f"Expected {TARGET_EXAMPLES} benchmark rows, got {len(rows)}")
    if len(ids) != len(set(ids)):
        raise ValueError("Benchmark row ids must be unique")
    decisions = {row["expected_decision"] for row in rows}
    expected_decisions = {"approved", "needs_review", "high_risk"}
    if decisions != expected_decisions:
        raise ValueError(f"Benchmark must cover {sorted(expected_decisions)}, got {sorted(decisions)}")


def _to_jsonl(rows: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(row, separators=(",", ":")) for row in rows) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
