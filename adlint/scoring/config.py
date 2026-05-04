from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Mapping

import yaml


DEFAULT_SEVERITY_WEIGHTS = {
    "low": 0.2,
    "medium": 0.4,
    "high": 0.7,
    "critical": 0.9,
}
DEFAULT_REGULATED_INDUSTRIES = frozenset({"health", "wellness", "finance"})


@dataclass(frozen=True)
class DecisionThresholds:
    needs_review: float = 0.35
    high_risk: float = 0.7
    max_without_high_severity: float = 0.69


@dataclass(frozen=True)
class EvidenceCountWeight:
    per_item: float = 0.02
    max: float = 0.12


@dataclass(frozen=True)
class CategoryWeights:
    regulated_category: float = 0.08
    landing_page_mismatch: float = 0.08
    privacy_tracking: float = 0.1
    brand_safety: float = 0.05


@dataclass(frozen=True)
class ScoringConfig:
    thresholds: DecisionThresholds
    severity_weights: dict[str, float]
    evidence_count: EvidenceCountWeight
    weights: CategoryWeights
    regulated_industries: frozenset[str]


DEFAULT_SCORING_CONFIG = ScoringConfig(
    thresholds=DecisionThresholds(),
    severity_weights=dict(DEFAULT_SEVERITY_WEIGHTS),
    evidence_count=EvidenceCountWeight(),
    weights=CategoryWeights(),
    regulated_industries=DEFAULT_REGULATED_INDUSTRIES,
)


def load_scoring_config(path: str | Path) -> ScoringConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Scoring config file not found: {config_path}")

    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if data is None:
        data = {}
    return scoring_config_from_dict(data, source=str(config_path))


def scoring_config_from_dict(raw: Mapping[str, Any], *, source: str = "scoring.yml") -> ScoringConfig:
    if not isinstance(raw, Mapping):
        raise ValueError(f"{source} must be a YAML object.")

    _reject_unknown_keys(raw, {"thresholds", "weights", "regulated_industries"}, source)

    thresholds = _build_thresholds(raw.get("thresholds"), source)
    weights = _mapping_or_empty(raw.get("weights"), f"{source} weights")
    _reject_unknown_keys(
        weights,
        {
            "severity",
            "evidence_count",
            "regulated_category",
            "landing_page_mismatch",
            "privacy_tracking",
            "brand_safety",
        },
        f"{source} weights",
    )

    severity_weights = _build_severity_weights(weights.get("severity"), source)
    evidence_count = _build_evidence_count(weights.get("evidence_count"), source)
    category_weights = _build_category_weights(weights, source)
    regulated_industries = _build_regulated_industries(raw.get("regulated_industries"), source)

    return ScoringConfig(
        thresholds=thresholds,
        severity_weights=severity_weights,
        evidence_count=evidence_count,
        weights=category_weights,
        regulated_industries=regulated_industries,
    )


def _build_thresholds(raw: Any, source: str) -> DecisionThresholds:
    values = _mapping_or_empty(raw, f"{source} thresholds")
    _reject_unknown_keys(
        values,
        {"needs_review", "high_risk", "max_without_high_severity"},
        f"{source} thresholds",
    )
    thresholds = replace(
        DEFAULT_SCORING_CONFIG.thresholds,
        needs_review=_number(
            values.get("needs_review", DEFAULT_SCORING_CONFIG.thresholds.needs_review),
            f"{source} thresholds.needs_review",
        ),
        high_risk=_number(
            values.get("high_risk", DEFAULT_SCORING_CONFIG.thresholds.high_risk),
            f"{source} thresholds.high_risk",
        ),
        max_without_high_severity=_number(
            values.get(
                "max_without_high_severity",
                DEFAULT_SCORING_CONFIG.thresholds.max_without_high_severity,
            ),
            f"{source} thresholds.max_without_high_severity",
        ),
    )
    if thresholds.high_risk <= thresholds.needs_review:
        raise ValueError(
            f"{source} thresholds.high_risk must be greater than "
            "thresholds.needs_review."
        )
    if thresholds.max_without_high_severity >= thresholds.high_risk:
        raise ValueError(
            f"{source} thresholds.max_without_high_severity must be less than "
            "thresholds.high_risk."
        )
    return thresholds


def _build_severity_weights(raw: Any, source: str) -> dict[str, float]:
    values = _mapping_or_empty(raw, f"{source} weights.severity")
    _reject_unknown_keys(values, set(DEFAULT_SEVERITY_WEIGHTS), f"{source} weights.severity")
    severity_weights = dict(DEFAULT_SEVERITY_WEIGHTS)
    for severity in DEFAULT_SEVERITY_WEIGHTS:
        if severity in values:
            severity_weights[severity] = _number(values[severity], f"{source} weights.severity.{severity}")

    ordered = ["low", "medium", "high", "critical"]
    for lower, higher in zip(ordered, ordered[1:]):
        if severity_weights[lower] > severity_weights[higher]:
            raise ValueError(
                f"{source} weights.severity.{lower} must be less than or equal to "
                f"weights.severity.{higher}."
            )
    return severity_weights


def _build_evidence_count(raw: Any, source: str) -> EvidenceCountWeight:
    values = _mapping_or_empty(raw, f"{source} weights.evidence_count")
    _reject_unknown_keys(values, {"per_item", "max"}, f"{source} weights.evidence_count")
    return replace(
        DEFAULT_SCORING_CONFIG.evidence_count,
        per_item=_number(
            values.get("per_item", DEFAULT_SCORING_CONFIG.evidence_count.per_item),
            f"{source} weights.evidence_count.per_item",
        ),
        max=_number(
            values.get("max", DEFAULT_SCORING_CONFIG.evidence_count.max),
            f"{source} weights.evidence_count.max",
        ),
    )


def _build_category_weights(raw: Mapping[str, Any], source: str) -> CategoryWeights:
    return replace(
        DEFAULT_SCORING_CONFIG.weights,
        regulated_category=_number(
            raw.get("regulated_category", DEFAULT_SCORING_CONFIG.weights.regulated_category),
            f"{source} weights.regulated_category",
        ),
        landing_page_mismatch=_number(
            raw.get("landing_page_mismatch", DEFAULT_SCORING_CONFIG.weights.landing_page_mismatch),
            f"{source} weights.landing_page_mismatch",
        ),
        privacy_tracking=_number(
            raw.get("privacy_tracking", DEFAULT_SCORING_CONFIG.weights.privacy_tracking),
            f"{source} weights.privacy_tracking",
        ),
        brand_safety=_number(
            raw.get("brand_safety", DEFAULT_SCORING_CONFIG.weights.brand_safety),
            f"{source} weights.brand_safety",
        ),
    )


def _build_regulated_industries(raw: Any, source: str) -> frozenset[str]:
    if raw is None:
        return DEFAULT_SCORING_CONFIG.regulated_industries
    if not isinstance(raw, list):
        raise ValueError(f"{source} regulated_industries must be a list of strings.")
    industries = []
    for index, item in enumerate(raw):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"{source} regulated_industries[{index}] must be a non-empty string."
            )
        industries.append(item.lower())
    return frozenset(industries)


def _mapping_or_empty(raw: Any, label: str) -> Mapping[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise ValueError(f"{label} must be a YAML object.")
    return raw


def _reject_unknown_keys(raw: Mapping[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        supported = ", ".join(sorted(allowed))
        raise ValueError(f"Unknown {label} key '{unknown[0]}'. Supported keys: {supported}.")


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number between 0.0 and 1.0.")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{label} must be a number between 0.0 and 1.0.")
    return number
