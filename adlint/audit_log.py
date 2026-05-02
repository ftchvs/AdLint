from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

from adlint.models import AnalysisResult, Submission


def write_run_log(submission: Submission, result: AnalysisResult, path: str | None = None) -> str:
    log_path = Path(path or "logs/adlint-runs.jsonl")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(UTC).isoformat(),
        "input": {
            "platform": submission.platform,
            "country": submission.country,
            "industry": submission.industry,
            "headline": submission.headline,
            "body": submission.body,
            "cta": submission.cta,
            "target_age_range": submission.target_age_range,
            "landing_page_url": submission.landing_page_url,
            "policy_modules": list(submission.policy_modules),
        },
        "result": result.to_dict(),
    }
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return str(log_path)
