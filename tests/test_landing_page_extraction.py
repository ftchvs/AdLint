from __future__ import annotations

from adlint.engine import analyze
from adlint.scrapers import landing_page
from adlint.scrapers.landing_page import extract_landing_page


def test_inline_json_script_contributes_landing_claims_forms_pricing_and_disclaimers() -> None:
    html = """
    <html>
      <head>
        <script id="__NEXT_DATA__" type="application/json">
          {
            "props": {
              "pageProps": {
                "hero": {
                  "claim": "Clinically proven sleep results in seven days",
                  "price": "Membership pricing starts at $19 per month"
                },
                "signupForm": {
                  "fields": [
                    {"label": "Email address"},
                    {"placeholder": "Phone number"}
                  ]
                },
                "disclaimer": "Results vary. Not medical advice."
              }
            }
          }
        </script>
      </head>
      <body><h1>Sleep plan</h1></body>
    </html>
    """

    snapshot = extract_landing_page(html=html)

    assert "Clinically proven sleep results in seven days" in snapshot.visible_claims
    assert "Membership pricing starts at $19 per month" in snapshot.pricing_text
    assert "Results vary. Not medical advice." in snapshot.disclaimers
    assert "Email address" in snapshot.forms
    assert "Phone number" in snapshot.forms


def test_script_assigned_text_and_inline_analytics_are_extracted_locally() -> None:
    html = """
    <html>
      <body>
        <div id="claim"></div>
        <script>
          window.dataLayer = window.dataLayer || [];
          gtag("config", "G-123");
          document.querySelector("#claim").textContent = "Guaranteed income results for members";
          document.querySelector("#price").innerText = "Free trial, then $49 monthly";
          document.querySelector("#terms").innerHTML = "<p>Terms apply. Privacy policy applies.</p>";
          const form = {label: "Full name", placeholder: "Email address"};
        </script>
      </body>
    </html>
    """

    snapshot = extract_landing_page(html=html)

    assert "Guaranteed income results for members" in snapshot.visible_claims
    assert "Free trial, then $49 monthly" in snapshot.pricing_text
    assert "Terms apply. Privacy policy applies." in snapshot.disclaimers
    assert "Full name" in snapshot.forms
    assert "Email address" in snapshot.forms
    assert "Google Analytics" in snapshot.tracking_scripts


def test_percent_off_and_promo_code_text_is_pricing_context() -> None:
    snapshot = extract_landing_page(
        html="<html><body><p>Limited time 50% off with promo code LAUNCH50.</p></body></html>"
    )

    assert "Limited time 50% off with promo code LAUNCH50." in snapshot.pricing_text


def test_fetch_and_parser_errors_are_reported_as_landing_context_not_policy_hits(monkeypatch) -> None:
    fetch_result = analyze(
        {
            "platform": "google",
            "industry": "general",
            "headline": "Download planning guide",
            "body": "A worksheet for campaign launch planning.",
            "cta": "Download",
            "landing_page_url": "ftp://example.com/offer",
        }
    )

    assert fetch_result.decision == "approved"
    assert fetch_result.policy_hits == []
    assert fetch_result.landing_page.fetch_error
    assert fetch_result.landing_page.fetch_error.startswith("Fetch error:")

    def fail_feed(self, html):  # pragma: no cover - exercised by parser error path
        raise ValueError("broken markup parser")

    monkeypatch.setattr(landing_page._LandingPageParser, "feed", fail_feed)

    snapshot = extract_landing_page(html="<html><body>Broken</body></html>")

    assert snapshot.fetch_error == "Parser error: broken markup parser"
