from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from adlint.models import AnalysisResult, Submission


DEFAULT_STORAGE_PATH = "logs/adlint-metadata.sqlite3"
SCHEMA_VERSION = 1

MIGRATIONS: tuple[tuple[int, str], ...] = (
    (
        1,
        """
        CREATE TABLE IF NOT EXISTS analysis_runs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          run_id TEXT NOT NULL UNIQUE,
          created_at TEXT NOT NULL,
          source TEXT NOT NULL,
          platform TEXT NOT NULL,
          country TEXT NOT NULL,
          industry TEXT NOT NULL,
          decision TEXT NOT NULL,
          risk_score REAL NOT NULL,
          requires_review INTEGER NOT NULL,
          policy_hit_count INTEGER NOT NULL,
          policy_ids_json TEXT NOT NULL,
          policy_categories_json TEXT NOT NULL,
          policy_severity_counts_json TEXT NOT NULL,
          enabled_modules_json TEXT NOT NULL,
          model_json TEXT NOT NULL,
          logging_enabled INTEGER NOT NULL,
          report_paths_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_analysis_runs_created_at
          ON analysis_runs(created_at);
        CREATE INDEX IF NOT EXISTS idx_analysis_runs_decision
          ON analysis_runs(decision);

        CREATE TABLE IF NOT EXISTS eval_runs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          run_id TEXT NOT NULL UNIQUE,
          created_at TEXT NOT NULL,
          evaluator TEXT NOT NULL,
          dataset_path TEXT NOT NULL,
          generator TEXT NOT NULL,
          total_examples INTEGER NOT NULL,
          aggregate_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_eval_runs_created_at
          ON eval_runs(created_at);
        CREATE INDEX IF NOT EXISTS idx_eval_runs_evaluator
          ON eval_runs(evaluator);

        CREATE TABLE IF NOT EXISTS eval_results (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          eval_run_id INTEGER NOT NULL REFERENCES eval_runs(id) ON DELETE CASCADE,
          row_id TEXT NOT NULL,
          generator TEXT NOT NULL,
          overall_score REAL NOT NULL,
          dimension_scores_json TEXT NOT NULL,
          passed INTEGER NOT NULL,
          failure_codes_json TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_eval_results_run_id
          ON eval_results(eval_run_id);
        CREATE INDEX IF NOT EXISTS idx_eval_results_row_id
          ON eval_results(row_id);
        """,
    ),
)


def schema_sql() -> str:
    migration_blocks = [f"-- migration {version}\n{sql.strip()}" for version, sql in MIGRATIONS]
    return "\n\n".join(
        [
            _schema_migrations_sql().strip(),
            *migration_blocks,
        ]
    )


def migrate_database(path: str | Path | None = None) -> str:
    db_path = _storage_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        _ensure_migrations_table(connection)
        applied = _applied_migrations(connection)
        for version, sql in MIGRATIONS:
            if version in applied:
                continue
            connection.executescript(sql)
            connection.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (version, _now()),
            )
        connection.commit()
    return str(db_path)


def record_analysis_run(
    submission: Submission,
    result: AnalysisResult,
    path: str | Path | None = None,
) -> str:
    db_path = Path(migrate_database(path))
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            """
            INSERT INTO analysis_runs(
              run_id,
              created_at,
              source,
              platform,
              country,
              industry,
              decision,
              risk_score,
              requires_review,
              policy_hit_count,
              policy_ids_json,
              policy_categories_json,
              policy_severity_counts_json,
              enabled_modules_json,
              model_json,
              logging_enabled,
              report_paths_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                _now(),
                "scan",
                submission.platform,
                submission.country,
                submission.industry,
                result.decision,
                float(result.risk_score),
                int(result.requires_review),
                len(result.policy_hits),
                _json(sorted({hit.policy_id for hit in result.policy_hits})),
                _json(sorted({hit.category for hit in result.policy_hits})),
                _json(dict(sorted(Counter(hit.severity for hit in result.policy_hits).items()))),
                _json(result.enabled_modules),
                _json(_model_metadata(result.model)),
                int(result.logging_enabled),
                _json(dict(sorted(result.reports.items()))),
            ),
        )
        connection.commit()
    return str(db_path)


def record_eval_run(
    *,
    path: str | Path,
    evaluator: str,
    dataset_path: str,
    generator: str,
    total_examples: int,
    aggregate: dict[str, Any],
    results: Iterable[dict[str, Any]],
) -> str:
    db_path = Path(migrate_database(path))
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        cursor = connection.execute(
            """
            INSERT INTO eval_runs(
              run_id,
              created_at,
              evaluator,
              dataset_path,
              generator,
              total_examples,
              aggregate_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                _now(),
                evaluator,
                dataset_path,
                generator,
                int(total_examples),
                _json(aggregate),
            ),
        )
        eval_run_id = int(cursor.lastrowid)
        for result in results:
            connection.execute(
                """
                INSERT INTO eval_results(
                  eval_run_id,
                  row_id,
                  generator,
                  overall_score,
                  dimension_scores_json,
                  passed,
                  failure_codes_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eval_run_id,
                    str(result.get("id", "")),
                    generator,
                    float(result.get("overall_score", 0.0)),
                    _json(result.get("scores", {})),
                    int(bool(result.get("passed_min_scores", False))),
                    _json(result.get("failure_codes", [])),
                ),
            )
        connection.commit()
    return str(db_path)


def _schema_migrations_sql() -> str:
    return """
    CREATE TABLE IF NOT EXISTS schema_migrations (
      version INTEGER PRIMARY KEY,
      applied_at TEXT NOT NULL
    );
    """


def _ensure_migrations_table(connection: sqlite3.Connection) -> None:
    connection.execute(_schema_migrations_sql())


def _applied_migrations(connection: sqlite3.Connection) -> set[int]:
    rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    return {int(row[0]) for row in rows}


def _storage_path(path: str | Path | None) -> Path:
    return Path(path or DEFAULT_STORAGE_PATH)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _model_metadata(model: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {"enabled", "provider", "model", "endpoint", "status", "raw_decision"}
    return {key: value for key, value in model.items() if key in allowed_keys}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect or initialize AdLint SQLite metadata storage.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("schema", help="Print the current SQLite schema migrations.")

    init_parser = subparsers.add_parser("init", help="Create or migrate a metadata database.")
    init_parser.add_argument(
        "path",
        nargs="?",
        default=DEFAULT_STORAGE_PATH,
        help=f"SQLite database path. Defaults to {DEFAULT_STORAGE_PATH}.",
    )

    args = parser.parse_args(argv)
    if args.command == "schema":
        print(schema_sql())
        return 0
    if args.command == "init":
        print(migrate_database(args.path))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
