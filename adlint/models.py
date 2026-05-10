from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


Decision = str
Severity = str


@dataclass(frozen=True)
class Evidence:
    text: str
    source: str

    def to_dict(self) -> dict[str, str]:
        return {"text": self.text, "source": self.source}


@dataclass(frozen=True)
class Policy:
    id: str
    severity: Severity
    category: str
    description: str
    signals: tuple[str, ...]
    recommended_action: str
    modules: tuple[str, ...] = ()
    platforms: tuple[str, ...] = ()
    industries: tuple[str, ...] = ()
    rewrite_strategy: str | None = None
    requires_review: bool = False
    model_prompt: str | None = None
    iab_taxonomy: dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyHit:
    policy_id: str
    severity: Severity
    category: str
    evidence: list[Evidence]
    recommended_action: str
    requires_review: bool = False
    description: str = ""
    source: str = "rules"
    iab_taxonomy: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "policy_id": self.policy_id,
            "severity": self.severity,
            "category": self.category,
            "evidence": [item.to_dict() for item in self.evidence],
            "recommended_action": self.recommended_action,
        }
        if self.requires_review:
            payload["requires_review"] = True
        if self.description:
            payload["description"] = self.description
        if self.source != "rules":
            payload["source"] = self.source
        if self.iab_taxonomy:
            payload["iab_taxonomy"] = self.iab_taxonomy
        return payload


@dataclass(frozen=True)
class LandingPageSnapshot:
    url: str | None = None
    title: str | None = None
    headings: tuple[str, ...] = ()
    visible_claims: tuple[str, ...] = ()
    forms: tuple[str, ...] = ()
    pricing_text: tuple[str, ...] = ()
    disclaimers: tuple[str, ...] = ()
    tracking_scripts: tuple[str, ...] = ()
    fetch_error: str | None = None

    def text_fields(self) -> dict[str, str]:
        fields: dict[str, str] = {}
        if self.title:
            fields["landing_page_title"] = self.title
        for index, value in enumerate(self.headings, start=1):
            fields[f"landing_page_heading_{index}"] = value
        for index, value in enumerate(self.visible_claims, start=1):
            fields[f"landing_page_claim_{index}"] = value
        for index, value in enumerate(self.forms, start=1):
            fields[f"landing_page_form_{index}"] = value
        for index, value in enumerate(self.pricing_text, start=1):
            fields[f"landing_page_pricing_{index}"] = value
        for index, value in enumerate(self.disclaimers, start=1):
            fields[f"landing_page_disclaimer_{index}"] = value
        for index, value in enumerate(self.tracking_scripts, start=1):
            fields[f"landing_page_tracker_{index}"] = value
        return fields

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "headings": list(self.headings),
            "visible_claims": list(self.visible_claims),
            "forms": list(self.forms),
            "pricing_text": list(self.pricing_text),
            "disclaimers": list(self.disclaimers),
            "tracking_scripts": list(self.tracking_scripts),
            "fetch_error": self.fetch_error,
        }


@dataclass(frozen=True)
class Submission:
    platform: str
    country: str
    industry: str
    headline: str = ""
    body: str = ""
    cta: str = ""
    target_age_range: str | None = None
    landing_page_url: str | None = None
    landing_page_html: str | None = None
    policy_modules: tuple[str, ...] = ()
    model_enabled: bool = False
    model_affects_score: bool = False
    logging_enabled: bool = False
    log_path: str | None = None
    storage_enabled: bool = False
    storage_path: str | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Submission":
        modules = raw.get("policy_modules") or raw.get("modules") or ()
        return cls(
            platform=str(raw.get("platform", "google")).lower(),
            country=str(raw.get("country", "US")),
            industry=str(raw.get("industry", "general")).lower(),
            headline=str(raw.get("headline", "")),
            body=str(raw.get("body", "")),
            cta=str(raw.get("cta", "")),
            target_age_range=raw.get("target_age_range"),
            landing_page_url=raw.get("landing_page_url"),
            landing_page_html=raw.get("landing_page_html"),
            policy_modules=tuple(str(item) for item in modules),
            model_enabled=bool(raw.get("model_enabled", False)),
            model_affects_score=bool(raw.get("model_affects_score", False)),
            logging_enabled=bool(raw.get("logging_enabled", False)),
            log_path=raw.get("log_path"),
            storage_enabled=bool(raw.get("storage_enabled", False)),
            storage_path=raw.get("storage_path"),
        )

    def ad_fields(self) -> dict[str, str]:
        return {
            "headline": self.headline,
            "body": self.body,
            "cta": self.cta,
            "platform": self.platform,
            "industry": self.industry,
            "country": self.country,
            "target_age_range": self.target_age_range or "",
        }


@dataclass
class AnalysisResult:
    decision: Decision
    risk_score: float
    policy_hits: list[PolicyHit]
    requires_review: bool
    recommended_actions: list[str]
    safer_rewrites: list[dict[str, str]]
    landing_page: LandingPageSnapshot
    enabled_modules: list[str]
    model: dict[str, Any]
    logging_enabled: bool
    reports: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "decision": self.decision,
            "risk_score": self.risk_score,
            "policy_hits": [hit.to_dict() for hit in self.policy_hits],
            "requires_review": self.requires_review,
            "recommended_actions": self.recommended_actions,
            "safer_rewrites": self.safer_rewrites,
            "landing_page": self.landing_page.to_dict(),
            "enabled_modules": self.enabled_modules,
            "model": self.model,
            "logging_enabled": self.logging_enabled,
        }
        if self.reports:
            payload["reports"] = self.reports
        return payload
