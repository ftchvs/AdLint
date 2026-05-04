from __future__ import annotations

import argparse
import json
from collections import Counter

from generate_real_world_blind_dataset import build_candidate_pool


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print the 150-row public-source blind-eval candidate pool without writing files."
    )
    parser.add_argument(
        "--format",
        choices=("jsonl", "summary"),
        default="summary",
        help="jsonl prints full candidate rows; summary prints counts by status, decision, and source platform.",
    )
    args = parser.parse_args(argv)

    rows = build_candidate_pool()
    if args.format == "jsonl":
        for row in rows:
            print(json.dumps(row, sort_keys=True, separators=(",", ":")))
        return 0

    print(f"candidates: {len(rows)}")
    for label, counts in (
        ("adjudication_status", Counter(row["adjudication_status"] for row in rows)),
        ("expected_decision", Counter(row["expected_decision"] for row in rows)),
        ("source_platform", Counter(row["source_platform"] for row in rows)),
    ):
        print(label)
        for key, count in sorted(counts.items()):
            print(f"  {key}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
