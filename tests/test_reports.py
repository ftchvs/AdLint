from __future__ import annotations

import json

from adlint.engine import analyze
from adlint.reports import to_markdown, write_reports


def test_approved_markdown_report_has_empty_state_and_disclaimer() -> None:
    result = analyze(
        {
            "platform": "linkedin",
            "industry": "saas",
            "headline": "Plan campaign launches",
            "body": "Coordinate launch notes.",
            "cta": "Learn more",
        }
    )

    markdown = to_markdown(result)

    assert "No policy hits detected." in markdown
    assert "## Launch Readiness" in markdown
    assert "- Status: Ready for configured preflight review." in markdown
    assert "- Summary: No policy hits were detected by the configured deterministic rules." in markdown
    assert "  - No priority fixes from the configured rules." in markdown
    assert "- No additional actions." in markdown
    assert "No rewrite suggested." in markdown
    assert "Decision-Support Disclaimer" in markdown


def test_report_writer_serializes_review_labels_and_landing_page_context(tmp_path) -> None:
    result = analyze(
        {
            "platform": "google",
            "industry": "wellness",
            "headline": "A calmer routine for better sleep",
            "body": "Join our wellness newsletter for science-backed sleep tips.",
            "cta": "Sign up",
            "landing_page_html": "<html><head><title>Sleep newsletter</title><script src='https://connect.facebook.net/en_US/fbevents.js'></script></head><body><h1>Simple sleep tips</h1><p>Clinically proven sleep results with a free trial.</p><p>Results vary. Review our privacy policy.</p><form><label>Email signup</label><input name='email'></form></body></html>",
        }
    )

    paths = write_reports(result, tmp_path / "reports" / "nested")

    json_payload = json.loads((tmp_path / "reports" / "nested" / "adlint-report.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "reports" / "nested" / "adlint-report.md").read_text(encoding="utf-8")
    tracking_hit = next(hit for hit in json_payload["policy_hits"] if hit["policy_id"] == "tracking_pixel_risk")

    assert paths == {
        "json": str(tmp_path / "reports" / "nested" / "adlint-report.json"),
        "markdown": str(tmp_path / "reports" / "nested" / "adlint-report.md"),
    }
    assert tracking_hit["requires_review"] is True
    assert tracking_hit["policy_source"] == {
        "note": "HHS HIPAA online tracking guidance",
        "url": "https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/hipaa-online-tracking/index.html",
    }
    assert "- Status: Do not launch before fixes." in markdown
    assert "- Priority fixes:" in markdown
    assert "  - Remove or qualify the claim and provide substantiation." in markdown
    assert "- Review label: `requires_review`" in markdown
    assert "- Policy source: [HHS HIPAA online tracking guidance](https://www.hhs.gov/hipaa/for-professionals/privacy/guidance/hipaa-online-tracking/index.html)" in markdown
    assert "## Landing Page" in markdown
    assert "- Headings:" in markdown
    assert "  - Simple sleep tips" in markdown
    assert "- Visible claims:" in markdown
    assert "  - Clinically proven sleep results with a free trial." in markdown
    assert "- Forms:" in markdown
    assert "  - Email signup, email" in markdown
    assert "- Pricing:" in markdown
    assert "  - Clinically proven sleep results with a free trial." in markdown
    assert "- Disclaimers:" in markdown
    assert "  - Results vary. Review our privacy policy." in markdown
    assert "- Trackers: Meta Pixel" in markdown


def test_report_includes_creative_asset_metadata_without_policy_claims() -> None:
    result = analyze(
        {
            "platform": "meta",
            "industry": "saas",
            "headline": "Plan campaign launches",
            "body": "Coordinate launch notes.",
            "cta": "Learn more",
            "creative_assets": [
                {
                    "kind": "image",
                    "path": "creative/banner.png",
                    "mime_type": "image/png",
                    "notes": "Static banner for future OCR review.",
                }
            ],
        }
    )

    payload = result.to_dict()
    markdown = to_markdown(result)

    assert payload["creative_assets"] == [
        {
            "kind": "image",
            "path": "creative/banner.png",
            "mime_type": "image/png",
            "notes": "Static banner for future OCR review.",
        }
    ]
    assert "## Creative Assets" in markdown
    assert "metadata-only placeholder" in markdown
    assert "Raw media files are not read or stored by default." in markdown
    assert "visual compliance" not in markdown.lower()
