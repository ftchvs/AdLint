from __future__ import annotations

import json

from adlint.cli import main


def test_cli_scan_prints_json_without_opt_in_side_effects(tmp_path, capsys) -> None:
    config_path = tmp_path / "ad.json"
    config_path.write_text(
        json.dumps(
            {
                "platform": "linkedin",
                "industry": "saas",
                "headline": "Plan campaign launches",
                "body": "Coordinate launch notes.",
                "cta": "Learn more",
            }
        ),
        encoding="utf-8",
    )

    assert main(["scan", str(config_path)]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["decision"] == "approved"
    assert output["logging_enabled"] is False
    assert output["model"] == {"enabled": False, "provider": None, "status": "disabled"}
    assert "reports" not in output


def test_cli_scan_writes_requested_reports_and_stdout_remains_parseable(tmp_path, capsys) -> None:
    config_path = tmp_path / "ad.json"
    output_dir = tmp_path / "reports" / "nested"
    config_path.write_text(
        json.dumps(
            {
                "platform": "tiktok",
                "industry": "health",
                "headline": "Lose 20 pounds in 30 days guaranteed",
                "body": "Our clinically proven supplement melts fat fast.",
                "cta": "Buy now",
            }
        ),
        encoding="utf-8",
    )

    assert main(["scan", str(config_path), "--output-dir", str(output_dir)]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["decision"] == "high_risk"
    assert output["reports"] == {
        "json": str(output_dir / "adlint-report.json"),
        "markdown": str(output_dir / "adlint-report.md"),
    }
    assert (output_dir / "adlint-report.json").exists()
    assert (output_dir / "adlint-report.md").exists()


def test_cli_scan_markdown_format_includes_disclaimer(tmp_path, capsys) -> None:
    config_path = tmp_path / "ad.json"
    config_path.write_text(
        json.dumps(
            {
                "platform": "google",
                "industry": "general",
                "headline": "Advertise beside election analysis",
                "body": "Sponsor our political coverage during ballot season.",
                "cta": "Request inventory",
            }
        ),
        encoding="utf-8",
    )

    assert main(["scan", str(config_path), "--format", "markdown"]) == 0

    output = capsys.readouterr().out
    assert output.startswith("# AdLint Report")
    assert "Decision-Support Disclaimer" in output
    assert "brand_safety_politics" in output
