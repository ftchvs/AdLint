from __future__ import annotations

import argparse
import json
from typing import Sequence

from adlint.batch import BatchOptions, run_batch, summary_to_markdown, to_summary_csv
from adlint.config import load_config
from adlint.engine import analyze
from adlint.reports import to_markdown


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adlint")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Analyze an ad config.")
    scan_parser.add_argument("config", help="Path to JSON or YAML ad config.")
    scan_parser.add_argument(
        "--policy-path",
        action="append",
        default=None,
        help="Policy YAML file or directory. Can be passed multiple times.",
    )
    scan_parser.add_argument("--output-dir", help="Write JSON and Markdown reports to this directory.")
    scan_parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Format printed to stdout.",
    )
    scan_parser.add_argument(
        "--enable-model",
        action="store_true",
        help="Call a local Ollama-compatible classifier for metadata-only review notes.",
    )
    scan_parser.add_argument(
        "--model-affects-score",
        action="store_true",
        help="Allow valid local-model findings to join policy hits and affect scoring. Off by default.",
    )
    scan_parser.add_argument(
        "--ollama-model",
        help="Ollama model name, defaulting to ADLINT_OLLAMA_MODEL or gpt-oss-safeguard:20b.",
    )
    scan_parser.add_argument(
        "--scoring-config",
        help="Path to optional scoring.yml threshold and weight overrides.",
    )
    scan_parser.add_argument(
        "--enable-storage",
        action="store_true",
        help="Opt into SQLite metadata storage for this scan.",
    )
    scan_parser.add_argument(
        "--storage-path",
        help="SQLite metadata database path. Passing this also opts into storage.",
    )

    batch_parser = subparsers.add_parser("batch", help="Analyze a CSV of ad configs.")
    batch_parser.add_argument("csv", help="Path to CSV with ad config columns.")
    batch_parser.add_argument(
        "--policy-path",
        action="append",
        default=None,
        help="Policy YAML file or directory. Can be passed multiple times.",
    )
    batch_parser.add_argument(
        "--output-dir",
        help="Write a local batch archive with summaries and per-row reports.",
    )
    batch_parser.add_argument(
        "--format",
        choices=("json", "csv", "markdown"),
        default="json",
        help="Summary format printed to stdout.",
    )
    batch_parser.add_argument(
        "--enable-model",
        action="store_true",
        help="Call a local Ollama-compatible classifier for metadata-only review notes.",
    )
    batch_parser.add_argument(
        "--model-affects-score",
        action="store_true",
        help="Allow valid local-model findings to join policy hits and affect scoring. Off by default.",
    )
    batch_parser.add_argument(
        "--ollama-model",
        help="Ollama model name, defaulting to ADLINT_OLLAMA_MODEL or gpt-oss-safeguard:20b.",
    )
    batch_parser.add_argument(
        "--scoring-config",
        help="Path to optional scoring.yml threshold and weight overrides.",
    )

    args = parser.parse_args(argv)

    if args.command == "scan":
        config = load_config(args.config)
        if args.enable_storage or args.storage_path:
            config["storage_enabled"] = True
        if args.model_affects_score:
            config["model_affects_score"] = True
        if args.storage_path:
            config["storage_path"] = args.storage_path
        result = analyze(
            config,
            policy_paths=args.policy_path,
            output_dir=args.output_dir,
            enable_model=args.enable_model or None,
            ollama_model=args.ollama_model,
            scoring_config_path=args.scoring_config,
        )
        if args.format == "markdown":
            print(to_markdown(result))
        else:
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0

    if args.command == "batch":
        result = run_batch(
            args.csv,
            BatchOptions(
                policy_paths=args.policy_path,
                output_dir=args.output_dir,
                enable_model=True if args.enable_model else None,
                model_affects_score=args.model_affects_score,
                ollama_model=args.ollama_model,
                scoring_config_path=args.scoring_config,
            ),
        )
        if args.format == "csv":
            print(to_summary_csv(result), end="")
        elif args.format == "markdown":
            print(summary_to_markdown(result))
        else:
            print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
