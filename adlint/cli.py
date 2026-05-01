from __future__ import annotations

import argparse
import json
from typing import Sequence

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
        help="Call a local Ollama-compatible classifier in addition to deterministic rules.",
    )
    scan_parser.add_argument(
        "--ollama-model",
        help="Ollama model name, defaulting to ADLINT_OLLAMA_MODEL or gpt-oss-safeguard-20b.",
    )

    args = parser.parse_args(argv)

    if args.command == "scan":
        config = load_config(args.config)
        result = analyze(
            config,
            policy_paths=args.policy_path,
            output_dir=args.output_dir,
            enable_model=args.enable_model or None,
            ollama_model=args.ollama_model,
        )
        if args.format == "markdown":
            print(to_markdown(result))
        else:
            print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2
