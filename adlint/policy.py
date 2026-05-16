from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Iterable

import yaml

from adlint.models import ALL_PLATFORMS, Policy, Submission


DEFAULT_MODULES = (
    "health_claims",
    "platform",
    "privacy",
    "brand_safety",
    "disclosure",
    "landing_page",
)


def load_policies(paths: Iterable[str | Path] | None = None) -> list[Policy]:
    policy_files: list[Path] = []
    if paths:
        for raw_path in paths:
            path = Path(raw_path)
            if path.is_dir():
                policy_files.extend(sorted(path.glob("*.yml")))
                policy_files.extend(sorted(path.glob("*.yaml")))
            else:
                policy_files.append(path)
    else:
        policy_dir = resources.files("adlint").joinpath("policies")
        policy_files = [
            Path(item)
            for item in policy_dir.iterdir()
            if item.name.endswith((".yml", ".yaml"))
        ]

    policies: list[Policy] = []
    for policy_file in sorted(policy_files):
        policies.extend(_load_policy_file(policy_file))
    return policies


def filter_policies(policies: Iterable[Policy], submission: Submission) -> list[Policy]:
    enabled_modules = set(submission.policy_modules or DEFAULT_MODULES)
    selected: list[Policy] = []
    for policy in policies:
        if policy.modules and not enabled_modules.intersection(policy.modules):
            continue
        if policy.platforms and submission.platform != ALL_PLATFORMS and submission.platform not in policy.platforms:
            continue
        if policy.industries and submission.industry not in policy.industries:
            continue
        selected.append(policy)
    return selected


def enabled_modules(submission: Submission) -> list[str]:
    return sorted(set(submission.policy_modules or DEFAULT_MODULES))


def _load_policy_file(path: Path) -> list[Policy]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("policies"), list):
        raise ValueError(f"Policy file must contain a policies list: {path}")

    policies: list[Policy] = []
    for item in raw["policies"]:
        if not isinstance(item, dict):
            raise ValueError(f"Policy item must be a mapping in {path}")
        policies.append(
            Policy(
                id=str(item["id"]),
                severity=str(item["severity"]),
                category=str(item["category"]),
                description=str(item.get("description", "")),
                signals=tuple(str(signal) for signal in item.get("signals", ())),
                recommended_action=str(item.get("recommended_action", "")),
                modules=tuple(str(value) for value in item.get("modules", ())),
                platforms=tuple(str(value) for value in item.get("platforms", ())),
                industries=tuple(str(value) for value in item.get("industries", ())),
                rewrite_strategy=item.get("rewrite_strategy"),
                requires_review=bool(item.get("requires_review", False)),
                model_prompt=item.get("model_prompt"),
                source_url=item.get("source_url"),
                source_note=item.get("source_note"),
                iab_taxonomy=dict(item.get("iab_taxonomy") or {}),
            )
        )
    return policies
