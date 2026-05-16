from __future__ import annotations

import ast
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
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

SCRIPT_ASSIGNMENT_RE = re.compile(
    r"""
    (?P<key>\b(?:textContent|innerText|innerHTML|outerText|value|placeholder|
    ariaLabel|label|title|heading|headline|subheadline|body|copy|claim|claims|
    disclaimer|disclaimers|price|pricing|cta)\b)
    \s*(?::|=)\s*
    (?P<quote>["'])(?P<value>(?:\\.|[^\\])*?)(?P=quote)
    """,
    re.IGNORECASE | re.VERBOSE | re.DOTALL,
)

SCRIPT_TEXT_KEYS = (
    "body",
    "button",
    "claim",
    "copy",
    "cta",
    "description",
    "disclaimer",
    "headline",
    "hero",
    "offer",
    "price",
    "pricing",
    "subheadline",
    "subtitle",
    "text",
    "title",
)

FORM_TEXT_KEYS = (
    "field",
    "form",
    "input",
    "label",
    "lead",
    "placeholder",
    "signup",
)

FORM_VALUE_KEYWORDS = (
    "address",
    "birth",
    "dob",
    "email",
    "first name",
    "full name",
    "last name",
    "name",
    "phone",
    "signup",
    "sign up",
    "zip",
)


def extract_landing_page(url: str | None = None, html: str | None = None) -> LandingPageSnapshot:
    if html:
        return _parse_html_with_errors(html, url)
    if not url:
        return LandingPageSnapshot()

    try:
        loaded = _load_url_or_file(url)
    except Exception as exc:  # pragma: no cover - exact platform errors vary
        return LandingPageSnapshot(url=url, fetch_error=f"Fetch error: {exc}")
    return _parse_html_with_errors(loaded, url)


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


def _parse_html_with_errors(html: str, url: str | None) -> LandingPageSnapshot:
    try:
        return _parse_html(html, url)
    except Exception as exc:  # pragma: no cover - defensive parser boundary
        return LandingPageSnapshot(url=url, fetch_error=f"Parser error: {exc}")


def _parse_html(html: str, url: str | None) -> LandingPageSnapshot:
    parser = _LandingPageParser()
    parser.feed(html)
    parser.close()

    script_text = _extract_script_text(parser.inline_scripts)
    texts = _unique([*parser.text_chunks, *script_text.text_chunks])
    visible_claims = tuple(item for item in texts if _looks_like_claim(item))[:12]
    pricing_text = tuple(item for item in texts if _looks_like_pricing(item))[:8]
    disclaimers = tuple(item for item in texts if _looks_like_disclaimer(item))[:8]
    tracking_scripts = _detect_trackers(parser.scripts)

    return LandingPageSnapshot(
        url=url,
        title=parser.title,
        headings=tuple(_unique(parser.headings))[:10],
        visible_claims=visible_claims,
        forms=tuple(_unique([*parser.forms, *script_text.forms]))[:8],
        pricing_text=pricing_text,
        disclaimers=disclaimers,
        tracking_scripts=tracking_scripts,
    )


@dataclass(frozen=True)
class _ScriptText:
    text_chunks: tuple[str, ...]
    forms: tuple[str, ...]


class _LandingPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title: str | None = None
        self.headings: list[str] = []
        self.forms: list[str] = []
        self.scripts: list[str] = []
        self.inline_scripts: list[str] = []
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
                self.inline_scripts.append(inline)
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


def _extract_script_text(scripts: list[str]) -> _ScriptText:
    text_chunks: list[str] = []
    forms: list[str] = []
    for script in scripts:
        for raw_text, path in _script_json_strings(script):
            clean = _clean_script_text(raw_text)
            if not clean:
                continue
            if _looks_like_script_form_text(clean, path):
                forms.append(clean)
            if _looks_like_script_page_text(clean, path):
                text_chunks.append(clean)

        for match in SCRIPT_ASSIGNMENT_RE.finditer(script):
            path = (match.group("key"),)
            clean = _clean_script_text(_decode_script_string(match.group("quote"), match.group("value")))
            if not clean:
                continue
            if _looks_like_script_form_text(clean, path):
                forms.append(clean)
            if _looks_like_script_page_text(clean, path):
                text_chunks.append(clean)

    return _ScriptText(text_chunks=tuple(text_chunks), forms=tuple(forms))


def _script_json_strings(script: str) -> list[tuple[str, tuple[str, ...]]]:
    strings: list[tuple[str, tuple[str, ...]]] = []
    seen_candidates: set[str] = set()
    for candidate in _json_candidates(script):
        if candidate in seen_candidates:
            continue
        seen_candidates.add(candidate)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        strings.extend(_walk_json_strings(parsed))
    return strings


def _json_candidates(script: str) -> list[str]:
    stripped = script.strip().rstrip(";")
    candidates: list[str] = []
    if stripped.startswith(("{", "[")):
        candidates.append(stripped)

    for match in re.finditer(r"=\s*([{[])", script):
        candidate = _balanced_json_slice(script, match.start(1))
        if candidate:
            candidates.append(candidate)
    return candidates


def _balanced_json_slice(text: str, start: int) -> str | None:
    closing_for = {"{": "}", "[": "]"}
    stack: list[str] = []
    quote: str | None = None
    escaped = False

    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue

        if char in {'"', "'"}:
            quote = char
            continue
        if char in closing_for:
            stack.append(closing_for[char])
            continue
        if stack and char == stack[-1]:
            stack.pop()
            if not stack:
                return text[start : index + 1]
    return None


def _walk_json_strings(value: object, path: tuple[str, ...] = ()) -> list[tuple[str, tuple[str, ...]]]:
    if isinstance(value, str):
        return [(value, path)]
    if isinstance(value, dict):
        result: list[tuple[str, tuple[str, ...]]] = []
        for key, child in value.items():
            result.extend(_walk_json_strings(child, (*path, str(key))))
        return result
    if isinstance(value, list):
        result = []
        for child in value:
            result.extend(_walk_json_strings(child, path))
        return result
    return []


def _decode_script_string(quote: str, value: str) -> str:
    try:
        decoded = ast.literal_eval(f"{quote}{value}{quote}")
    except (SyntaxError, ValueError):
        return value
    return str(decoded)


def _looks_like_script_page_text(text: str, path: tuple[str, ...]) -> bool:
    if not _looks_like_human_text(text):
        return False
    if _looks_like_claim(text) or _looks_like_pricing(text) or _looks_like_disclaimer(text):
        return True
    path_text = ".".join(path).lower()
    return any(key in path_text for key in SCRIPT_TEXT_KEYS)


def _looks_like_script_form_text(text: str, path: tuple[str, ...]) -> bool:
    if not _looks_like_human_text(text, allow_short=True):
        return False
    lower = text.lower()
    path_text = ".".join(path).lower()
    return any(key in path_text for key in FORM_TEXT_KEYS) and any(
        keyword in lower for keyword in FORM_VALUE_KEYWORDS
    )


def _looks_like_human_text(text: str, *, allow_short: bool = False) -> bool:
    if len(text) > 280:
        return False
    lower = text.lower()
    if lower.startswith(("http://", "https://", "mailto:", "tel:")):
        return False
    if re.fullmatch(r"[#./:_\-a-z0-9]+", lower):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z'-]*", text)
    return len(words) >= (1 if allow_short else 2)


def _looks_like_claim(text: str) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in CLAIM_KEYWORDS)


def _looks_like_pricing(text: str) -> bool:
    lower = text.lower()
    return (
        "$" in text
        or bool(re.search(r"\b\d{1,3}\s*%\s*off\b", lower))
        or any(word in lower for word in ("price", "pricing", "free trial", "discount", "limited time", "promo code"))
    )


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


def _clean_script_text(text: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", text)
    return _clean_text(without_tags)


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
