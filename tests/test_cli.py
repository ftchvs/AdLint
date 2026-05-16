from __future__ import annotations

import json
from pathlib import Path

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


def test_cli_batch_prints_private_json_summary(tmp_path, capsys) -> None:
    csv_path = tmp_path / "ads.csv"
    csv_path.write_text(
        "\n".join(
            [
                "id,platform,industry,headline,body,cta",
                "safe,linkedin,saas,Plan campaign launches,Coordinate launch notes.,Learn more",
                "risk,tiktok,health,Lose 20 pounds in 30 days guaranteed,Our clinically proven supplement melts fat fast.,Buy now",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert main(["batch", str(csv_path)]) == 0

    output = json.loads(capsys.readouterr().out)
    assert output["total_rows"] == 2
    assert output["decision_counts"] == {"approved": 1, "high_risk": 1}
    assert output["privacy"]["raw_creative_included"] is False
    assert output["rows"][0]["id"] == "safe"
    assert output["rows"][0]["decision"] == "approved"
    assert output["rows"][1]["id"] == "risk"
    assert output["rows"][1]["decision"] == "high_risk"
    assert "Lose 20 pounds" not in json.dumps(output)
    assert "clinically proven supplement" not in json.dumps(output)


def test_cli_batch_writes_local_archive_and_csv_summary(tmp_path, capsys) -> None:
    csv_path = tmp_path / "ads.csv"
    output_dir = tmp_path / "archive"
    csv_path.write_text(
        "\n".join(
            [
                "id,platform,industry,headline,body,cta,policy_modules",
                "client-a,linkedin,saas,Plan campaign launches,Coordinate launch notes.,Learn more,platform",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert main(["batch", str(csv_path), "--output-dir", str(output_dir), "--format", "csv"]) == 0

    stdout = capsys.readouterr().out
    assert stdout.startswith("id,decision,risk_score,requires_review,policy_ids")
    assert "client-a,approved," in stdout
    assert (output_dir / "adlint-batch-summary.json").exists()
    assert (output_dir / "adlint-batch-summary.csv").exists()
    assert (output_dir / "adlint-batch-summary.md").exists()
    assert (output_dir / "client-a.json").exists()
    assert (output_dir / "client-a.md").exists()

    summary = json.loads((output_dir / "adlint-batch-summary.json").read_text(encoding="utf-8"))
    assert summary["privacy"]["raw_creative_included"] is False
    assert summary["rows"][0]["reports"]["json"] == str(Path(output_dir) / "client-a.json")


def test_cli_batch_accepts_creative_asset_metadata_column(tmp_path, capsys) -> None:
    csv_path = tmp_path / "ads.csv"
    output_dir = tmp_path / "archive"
    csv_path.write_text(
        "\n".join(
            [
                "id,platform,industry,headline,body,cta,creative_assets",
                'asset-a,meta,saas,Plan campaign launches,Coordinate launch notes.,Learn more,"[{""kind"": ""image"", ""path"": ""banner.png""}]"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert main(["batch", str(csv_path), "--output-dir", str(output_dir)]) == 0

    capsys.readouterr()
    report = json.loads((output_dir / "asset-a.json").read_text(encoding="utf-8"))
    assert report["creative_assets"] == [{"kind": "image", "path": "banner.png"}]


def test_cli_batch_markdown_summary_omits_raw_copy(tmp_path, capsys) -> None:
    csv_path = tmp_path / "ads.csv"
    csv_path.write_text(
        "\n".join(
            [
                "id,platform,industry,headline,body,cta",
                "risk,tiktok,health,Lose 20 pounds in 30 days guaranteed,Our clinically proven supplement melts fat fast.,Buy now",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert main(["batch", str(csv_path), "--format", "markdown"]) == 0

    output = capsys.readouterr().out
    assert output.startswith("# AdLint Batch Summary")
    assert "| risk | `high_risk` |" in output
    assert "Batch summaries intentionally omit raw ad copy" in output
    assert "Lose 20 pounds" not in output
    assert "clinically proven supplement" not in output
