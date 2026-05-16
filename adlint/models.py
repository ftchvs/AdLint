from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


Decision = str
Severity = str

ALL_PLATFORMS = "all"


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
    source_url: str | None = None
    source_note: str | None = None
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
    policy_source: dict[str, str] = field(default_factory=dict)
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
        if self.policy_source:
            payload["policy_source"] = self.policy_source
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
class CreativeAsset:
    asset_id: str
    asset_type: str = "unknown"
    filename: str | None = None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None
    file_size_bytes: int | None = None
    text_overlay: str = ""
    transcript_excerpt: str = ""
    alt_text: str = ""
    labels: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, index: int = 1) -> "CreativeAsset":
        filename = _basename(raw.get("filename") or raw.get("file_name") or raw.get("path") or raw.get("url"))
        asset_id = str(raw.get("asset_id") or raw.get("id") or filename or f"asset-{index}")
        return cls(
            asset_id=_safe_asset_id(asset_id, fallback=f"asset-{index}"),
            asset_type=_asset_type(raw.get("asset_type") or raw.get("kind") or raw.get("type") or raw.get("media_type")),
            filename=filename,
            mime_type=_optional_str(raw.get("mime_type") or raw.get("content_type")),
            width=_optional_int(raw.get("width")),
            height=_optional_int(raw.get("height")),
            duration_seconds=_optional_float(raw.get("duration_seconds") or raw.get("duration")),
            file_size_bytes=_optional_int(raw.get("file_size_bytes") or raw.get("size_bytes")),
            text_overlay=_optional_str(raw.get("text_overlay") or raw.get("ocr_text")) or "",
            transcript_excerpt=_optional_str(raw.get("transcript_excerpt") or raw.get("audio_transcript")) or "",
            alt_text=_optional_str(raw.get("alt_text") or raw.get("description")) or "",
            labels=tuple(str(item).strip() for item in _raw_list(raw.get("labels")) if str(item).strip()),
        )

    def text_fields(self, *, index: int) -> dict[str, str]:
        prefix = f"creative_asset_{_safe_asset_id(self.asset_id, fallback=f'asset-{index}')}"
        fields: dict[str, str] = {}
        if self.text_overlay:
            fields[f"{prefix}_text_overlay"] = self.text_overlay
        if self.transcript_excerpt:
            fields[f"{prefix}_transcript_excerpt"] = self.transcript_excerpt
        if self.alt_text:
            fields[f"{prefix}_alt_text"] = self.alt_text
        if self.labels:
            fields[f"{prefix}_labels"] = ", ".join(self.labels)
        return fields

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "asset_id": self.asset_id,
            "asset_type": self.asset_type,
            "text_metadata": {
                "text_overlay": bool(self.text_overlay),
                "transcript_excerpt": bool(self.transcript_excerpt),
                "alt_text": bool(self.alt_text),
                "labels": len(self.labels),
            },
        }
        for key, value in (
            ("filename", self.filename),
            ("mime_type", self.mime_type),
            ("width", self.width),
            ("height", self.height),
            ("duration_seconds", self.duration_seconds),
            ("file_size_bytes", self.file_size_bytes),
        ):
            if value not in (None, ""):
                payload[key] = value
        return payload


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
    creative_assets: tuple[CreativeAsset, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Submission":
        modules = raw.get("policy_modules") or raw.get("modules") or ()
        creative_assets = _creative_assets_from_raw(raw.get("creative_assets") or raw.get("assets") or ())
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
            creative_assets=creative_assets,
        )

    def ad_fields(self) -> dict[str, str]:
        fields = {
            "headline": self.headline,
            "body": self.body,
            "cta": self.cta,
            "platform": self.platform,
            "industry": self.industry,
            "country": self.country,
            "target_age_range": self.target_age_range or "",
        }
        for index, asset in enumerate(self.creative_assets, start=1):
            fields.update(asset.text_fields(index=index))
        return fields


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
    creative_assets: tuple[CreativeAsset, ...] = ()
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
        if self.creative_assets:
            payload["creative_assets"] = [asset.to_dict() for asset in self.creative_assets]
        if self.reports:
            payload["reports"] = self.reports
        return payload


def _creative_assets_from_raw(raw: Any) -> tuple[CreativeAsset, ...]:
    if raw in (None, "", ()):
        return ()
    raw_items = raw
    if isinstance(raw, str):
        try:
            raw_items = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError("creative_assets must be valid JSON when passed as a string.") from exc
    if isinstance(raw_items, dict):
        raw_items = [raw_items]
    elif not isinstance(raw_items, list):
        raise ValueError("creative_assets must be an object or list of objects.")

    assets: list[CreativeAsset] = []
    for index, item in enumerate(raw_items, start=1):
        if not isinstance(item, dict):
            raise ValueError("Each creative asset must be an object.")
        assets.append(CreativeAsset.from_dict(item, index=index))
    return tuple(assets)


def _safe_asset_id(value: str, *, fallback: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower()).strip("_")
    return cleaned or fallback


def _asset_type(value: Any) -> str:
    normalized = str(value or "unknown").strip().lower()
    if normalized in {"image", "video", "audio", "display", "html5"}:
        return normalized
    return "unknown"


def _basename(value: Any) -> str | None:
    text = _optional_str(value)
    if not text:
        return None
    without_query = text.split("?", 1)[0].rstrip("/")
    filename = Path(without_query).name
    return filename or None


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _raw_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        if value.strip().startswith("["):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return []
            return parsed if isinstance(parsed, list) else []
        return [item.strip() for item in re.split(r"[|;,]", value) if item.strip()]
    return [value]
