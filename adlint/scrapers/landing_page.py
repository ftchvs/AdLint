from __future__ import annotations

import re
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from html.parser import HTMLParser
from pathlib import Path

from adlint.models import LandingPageSnapshot


TRACKER_PATTERNS = {
    "Meta Pixel": ("connect.facebook.net", "fbq(", "facebook pixel", "meta pixel"),
    "Google Analytics": ("google-analytics.com", "gtag(", "ga(", "analytics.js"),
    "Google Tag Manager": ("googletagmanager.com", "gtm.js", "google tag manager"),
    "TikTok Pixel": ("analytics.tiktok.com", "ttq.", "tiktok pixel"),
    "LinkedIn Insight Tag": ("snap.licdn.com", "_linkedin_partner_id", "linkedin insight"),
}

CLAIM_KEYWORDS = (
    "guarantee",
    "guaranteed",
    "clinically",
    "proven",
    "results",
    "risk-free",
    "cure",
    "treat",
    "weight",
    "privacy",
    "health",
    "credit",
    "income",
    "salary",
)


def extract_landing_page(url: str | None = None, html: str | None = None) -> LandingPageSnapshot:
    if html:
        return _parse_html(html, url)
    if not url:
        return LandingPageSnapshot()

    try:
        loaded = _load_url_or_file(url)
    except Exception as exc:  # pragma: no cover - exact platform errors vary
        return LandingPageSnapshot(url=url, fetch_error=str(exc))
    return _parse_html(loaded, url)


def _load_url_or_file(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme in {"", "file"}:
        path = Path(urllib.request.url2pathname(parsed.path if parsed.scheme else url))
        return path.read_text(encoding="utf-8")

    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"Unsupported landing page URL scheme: {parsed.scheme}")

    if not _robots_allows(url):
        raise PermissionError("robots.txt disallows fetching this URL")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "AdLint/0.1 (+https://github.com/ftchvs/AdLint)"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            raise ValueError(f"Expected text/html landing page, got {content_type or 'unknown'}")
        return response.read(1_000_000).decode("utf-8", errors="replace")


def _robots_allows(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    robots_url = urllib.parse.urlunparse((parsed.scheme, parsed.netloc, "/robots.txt", "", "", ""))
    parser = urllib.robotparser.RobotFileParser(robots_url)
    try:
        parser.read()
    except (urllib.error.URLError, TimeoutError):
        return True
    return parser.can_fetch("AdLint/0.1", url)


def _parse_html(html: str, url: str | None) -> LandingPageSnapshot:
    parser = _LandingPageParser()
    parser.feed(html)
    parser.close()

    texts = _unique(parser.text_chunks)
    visible_claims = tuple(item for item in texts if _looks_like_claim(item))[:12]
    pricing_text = tuple(item for item in texts if _looks_like_pricing(item))[:8]
    disclaimers = tuple(item for item in texts if _looks_like_disclaimer(item))[:8]
    tracking_scripts = _detect_trackers(parser.scripts)

    return LandingPageSnapshot(
        url=url,
        title=parser.title,
        headings=tuple(_unique(parser.headings))[:10],
        visible_claims=visible_claims,
        forms=tuple(_unique(parser.forms))[:8],
        pricing_text=pricing_text,
        disclaimers=disclaimers,
        tracking_scripts=tracking_scripts,
    )


class _LandingPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.headings: list[str] = []
        self.forms: list[str] = []
        self.scripts: list[str] = []
        self.text_chunks: list[str] = []
        self._tag_stack: list[str] = []
        self._buffer: list[str] = []
        self._script_buffer: list[str] = []
        self._form_labels: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._tag_stack.append(tag)
        attr_map = {name: value or "" for name, value in attrs}
        if tag == "script":
            src = attr_map.get("src")
            if src:
                self.scripts.append(src)
        if tag in {"title", "h1", "h2", "h3", "p", "li", "span", "label", "button"}:
            self._buffer = []
        if tag == "input":
            label = attr_map.get("name") or attr_map.get("placeholder") or attr_map.get("type")
            if label:
                self._form_labels.append(label)

    def handle_endtag(self, tag: str) -> None:
        text = _clean_text(" ".join(self._buffer))
        if tag == "title" and text:
            self.title = text
        elif tag in {"h1", "h2", "h3"} and text:
            self.headings.append(text)
        elif tag in {"p", "li", "span", "label", "button"} and text:
            self.text_chunks.append(text)
            if tag == "label":
                self._form_labels.append(text)

        if tag == "script":
            inline = _clean_text(" ".join(self._script_buffer))
            if inline:
                self.scripts.append(inline)
            self._script_buffer = []
        if tag == "form":
            label = ", ".join(_unique(self._form_labels)) or "form detected"
            self.forms.append(label)
            self._form_labels = []

        if self._tag_stack:
            self._tag_stack.pop()
        self._buffer = []

    def handle_data(self, data: str) -> None:
        if not self._tag_stack:
            return
        current = self._tag_stack[-1]
        if current == "script":
            self._script_buffer.append(data)
        elif current in {"title", "h1", "h2", "h3", "p", "li", "span", "label", "button"}:
            self._buffer.append(data)


def _detect_trackers(scripts: list[str]) -> tuple[str, ...]:
    found: list[str] = []
    joined_scripts = "\n".join(scripts).lower()
    for name, patterns in TRACKER_PATTERNS.items():
        if any(pattern.lower() in joined_scripts for pattern in patterns):
            found.append(name)
    return tuple(found)


def _looks_like_claim(text: str) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in CLAIM_KEYWORDS)


def _looks_like_pricing(text: str) -> bool:
    lower = text.lower()
    return "$" in text or any(word in lower for word in ("price", "pricing", "free trial", "discount"))


def _looks_like_disclaimer(text: str) -> bool:
    lower = text.lower()
    return any(
        phrase in lower
        for phrase in (
            "results vary",
            "not medical advice",
            "terms apply",
            "privacy policy",
            "disclaimer",
            "consult your",
        )
    )


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        clean = _clean_text(item)
        if not clean or clean in seen:
            continue
        result.append(clean)
        seen.add(clean)
    return result
