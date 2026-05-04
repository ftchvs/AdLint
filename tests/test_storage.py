from __future__ import annotations

import json
import sqlite3

from adlint.engine import analyze
from adlint.storage import DEFAULT_STORAGE_PATH, schema_sql


def test_sqlite_storage_disabled_by_default(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    result = analyze(
        {
            "platform": "google",
            "industry": "general",
            "headline": "Download campaign checklist",
            "body": "A free worksheet for launch planning.",
            "cta": "Download",
        }
    )

    assert result.reports == {}
    assert not (tmp_path / DEFAULT_STORAGE_PATH).exists()


def test_sqlite_storage_enabled_writes_metadata_only(tmp_path) -> None:
    db_path = tmp_path / "metadata.sqlite3"

    result = analyze(
        {
            "platform": "tiktok",
            "industry": "health",
            "headline": "Lose 20 pounds in 30 days guaranteed",
            "body": "Our clinically proven supplement melts fat fast.",
            "cta": "Buy now",
            "storage_enabled": True,
            "storage_path": str(db_path),
        }
    )

    assert result.reports["storage"] == str(db_path)
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT platform, industry, decision, policy_hit_count, policy_ids_json,
                   enabled_modules_json, logging_enabled
            FROM analysis_runs
            """
        ).fetchone()
        eval_run_count = connection.execute("SELECT COUNT(*) FROM eval_runs").fetchone()[0]

    assert row[0] == "tiktok"
    assert row[1] == "health"
    assert row[2] == "high_risk"
    assert row[3] >= 1
    assert "weight_loss_claim" in json.loads(row[4])
    assert "health_claims" in json.loads(row[5])
    assert row[6] == 0
    assert eval_run_count == 0


def test_sqlite_storage_does_not_persist_raw_ad_or_page_fields(tmp_path) -> None:
    db_path = tmp_path / "metadata.sqlite3"
    raw_values = {
        "headline": "UNIQUE_HEADLINE_DO_NOT_STORE_946a",
        "body": "UNIQUE_BODY_DO_NOT_STORE_946a clinically proven cure",
        "cta": "UNIQUE_CTA_DO_NOT_STORE_946a",
        "landing_page_url": "https://example.com/UNIQUE_URL_DO_NOT_STORE_946a",
        "landing_page_html": "<html>UNIQUE_HTML_DO_NOT_STORE_946a</html>",
    }

    analyze(
        {
            "platform": "google",
            "industry": "health",
            **raw_values,
            "storage_enabled": True,
            "storage_path": str(db_path),
        }
    )

    raw_database = db_path.read_bytes()
    for value in raw_values.values():
        assert value.encode("utf-8") not in raw_database

    with sqlite3.connect(db_path) as connection:
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(analysis_runs)").fetchall()
        }
    assert {"headline", "body", "cta", "landing_page_url", "landing_page_html"}.isdisjoint(columns)


def test_jsonl_logging_stays_independent_when_sqlite_is_not_enabled(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    log_path = tmp_path / "runs.jsonl"

    result = analyze(
        {
            "platform": "google",
            "industry": "general",
            "headline": "Download campaign checklist",
            "body": "A free worksheet for launch planning.",
            "cta": "Download",
            "logging_enabled": True,
            "log_path": str(log_path),
        }
    )

    assert result.reports["log"] == str(log_path)
    assert json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])["input"]["headline"] == (
        "Download campaign checklist"
    )
    assert not (tmp_path / DEFAULT_STORAGE_PATH).exists()


def test_sqlite_schema_is_inspectable_and_versioned() -> None:
    sql = schema_sql()

    assert "CREATE TABLE IF NOT EXISTS schema_migrations" in sql
    assert "CREATE TABLE IF NOT EXISTS analysis_runs" in sql
    assert "CREATE TABLE IF NOT EXISTS eval_runs" in sql
    assert "CREATE TABLE IF NOT EXISTS eval_results" in sql
    assert "headline" not in sql
    assert "landing_page_html" not in sql
