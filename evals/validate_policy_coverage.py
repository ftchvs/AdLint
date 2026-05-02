from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVALS_DIR = Path(__file__).resolve().parent
for import_path in (ROOT, EVALS_DIR):
    import_path_text = str(import_path)
    if import_path_text not in sys.path:
        sys.path.insert(0, import_path_text)

from policy_coverage import (
    PolicyCoverageError,
    build_policy_coverage_report,
    render_policy_coverage_markdown,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate expected policy coverage across bundled eval datasets."
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "--markdown-output",
        type=Path,
        help="write the deterministic Markdown coverage matrix to PATH",
    )
    output_group.add_argument(
        "--check",
        type=Path,
        help="compare generated Markdown exactly against PATH",
    )
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)

    try:
        report = build_policy_coverage_report()
    except PolicyCoverageError as exc:
        print(f"ERROR {exc}", file=sys.stderr)
        return 1

    markdown = render_policy_coverage_markdown(report)
    exit_code = 0

    if args.markdown_output is not None:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown, encoding="utf-8")
        print(f"OK wrote markdown: {args.markdown_output}")

    if args.check is not None:
        try:
            existing = args.check.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"ERROR markdown check failed: {args.check}: {exc.strerror}", file=sys.stderr)
            exit_code = 1
        else:
            if existing != markdown:
                print(
                    f"ERROR markdown stale: policy coverage matrix is stale: {args.check}",
                    file=sys.stderr,
                )
                exit_code = 1
            else:
                print(f"OK markdown up to date: {args.check}")

    if report.errors:
        for error in report.errors:
            print(f"ERROR {error}", file=sys.stderr)
        return 1

    if exit_code == 0:
        print(
            "OK policy coverage valid: "
            f"{len(report.policies)} policies, {report.total_row_count} rows"
        )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
