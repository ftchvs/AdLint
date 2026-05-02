from __future__ import annotations

import json
import importlib.util
import sys
from pathlib import Path

import pytest

from adlint.models import Evidence, PolicyHit


ROOT = Path(__file__).resolve().parents[1]
RUN_EVAL_PATH = ROOT / "evals" / "run_eval.py"
RUN_EVAL_SPEC = importlib.util.spec_from_file_location("run_eval", RUN_EVAL_PATH)
assert RUN_EVAL_SPEC is not None
assert RUN_EVAL_SPEC.loader is not None
run_eval = importlib.util.module_from_spec(RUN_EVAL_SPEC)
RUN_EVAL_SPEC.loader.exec_module(run_eval)

GENERATE_BENCHMARK_PATH = ROOT / "evals" / "generate_benchmark_dataset.py"
GENERATE_BENCHMARK_SPEC = importlib.util.spec_from_file_location("generate_benchmark_dataset", GENERATE_BENCHMARK_PATH)
assert GENERATE_BENCHMARK_SPEC is not None
assert GENERATE_BENCHMARK_SPEC.loader is not None
generate_benchmark_dataset = importlib.util.module_from_spec(GENERATE_BENCHMARK_SPEC)
GENERATE_BENCHMARK_SPEC.loader.exec_module(generate_benchmark_dataset)


def test_eval_runner_skips_blank_lines_and_preserves_row_ids(tmp_path) -> None:
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text(
        "\n".join(
            [
                "",
                json.dumps(
                    {
                        "id": "approved-saas",
                        "input": {
                            "platform": "linkedin",
                            "industry": "saas",
                            "headline": "Plan campaign launches",
                            "body": "Coordinate launch notes.",
                            "cta": "Learn more",
                        },
                        "expected_decision": "approved",
                    }
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    rows = run_eval._load_rows(dataset)
    metrics = run_eval._metrics([run_eval._score_row(row) for row in rows])

    assert metrics["total_examples"] == 1
    assert metrics["decision_accuracy"] == 1.0
    assert metrics["confusion_matrix"]["approved"]["approved"] == 1
    assert metrics["results"][0]["id"] == "approved-saas"


def test_eval_runner_reports_dataset_schema_errors_with_line_number(tmp_path) -> None:
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text(
        json.dumps({"id": "missing-label", "input": {"headline": "Missing expected decision"}}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match=r"Missing input or expected_decision at .*dataset\.jsonl:1"):
        run_eval._load_rows(dataset)


def test_eval_runner_writes_metrics_output_and_returns_success(tmp_path, monkeypatch, capsys) -> None:
    dataset = tmp_path / "dataset.jsonl"
    output_path = tmp_path / "metrics" / "eval.json"
    markdown_path = tmp_path / "metrics" / "eval.md"
    dataset.write_text(
        json.dumps(
            {
                "id": "brand-review",
                "input": {
                    "platform": "google",
                    "industry": "general",
                    "headline": "Advertise near election analysis",
                    "body": "Sponsor political coverage during ballot season.",
                    "cta": "Request inventory",
                },
                "expected_decision": "needs_review",
                "expected_policy_ids": ["brand_safety_politics"],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_eval.py",
            str(dataset),
            "--output",
            str(output_path),
            "--markdown-output",
            str(markdown_path),
            "--min-decision-accuracy",
            "0.99",
        ],
    )

    assert run_eval.main() == 0

    stdout_metrics = json.loads(capsys.readouterr().out)
    file_metrics = json.loads(output_path.read_text(encoding="utf-8"))
    assert stdout_metrics == file_metrics
    assert "## Confusion Matrix" in markdown_path.read_text(encoding="utf-8")
    assert stdout_metrics["decision_accuracy"] == 1.0
    assert stdout_metrics["policy_metrics"]["brand_safety_politics"]["recall"] == 1.0


def test_eval_runner_limit_scores_only_first_rows(tmp_path, monkeypatch, capsys) -> None:
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "first",
                        "input": {
                            "platform": "linkedin",
                            "industry": "saas",
                            "headline": "Plan campaign launches",
                            "body": "Coordinate launch notes.",
                            "cta": "Learn more",
                        },
                        "expected_decision": "approved",
                    }
                ),
                json.dumps(
                    {
                        "id": "second",
                        "input": {
                            "platform": "google",
                            "industry": "finance",
                            "headline": "Guaranteed approval credit card",
                            "body": "Fix your credit fast with no fees.",
                            "cta": "Apply now",
                        },
                        "expected_decision": "high_risk",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["run_eval.py", str(dataset), "--limit", "1"])

    assert run_eval.main() == 0

    metrics = json.loads(capsys.readouterr().out)
    assert metrics["input_examples"] == 1
    assert metrics["results"][0]["id"] == "first"


def test_eval_runner_returns_failure_when_accuracy_threshold_is_not_met(tmp_path, monkeypatch, capsys) -> None:
    dataset = tmp_path / "dataset.jsonl"
    dataset.write_text(
        json.dumps(
            {
                "id": "threshold-miss",
                "input": {
                    "platform": "linkedin",
                    "industry": "saas",
                    "headline": "Plan campaign launches",
                    "body": "Coordinate launch notes.",
                    "cta": "Learn more",
                },
                "expected_decision": "high_risk",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["run_eval.py", str(dataset), "--min-decision-accuracy", "1.0"])

    assert run_eval.main() == 1
    metrics = json.loads(capsys.readouterr().out)
    assert metrics["decision_accuracy"] == 0.0
    assert metrics["review_notes"]["decision_mismatches"][0]["decision_error_type"] == "undercall"


def test_model_only_eval_skips_when_requested_model_is_unavailable(monkeypatch) -> None:
    def fake_classify(submission, *, model=None, endpoint=None):
        return [], {
            "enabled": True,
            "provider": "ollama",
            "model": model,
            "endpoint": endpoint,
            "status": "unavailable",
            "reason": "model_not_installed",
            "ran": False,
        }

    monkeypatch.setattr(run_eval, "classify_with_ollama", fake_classify)

    metrics = run_eval._run_eval(
        [
            {
                "id": "approved-saas",
                "input": {
                    "platform": "linkedin",
                    "industry": "saas",
                    "headline": "Plan campaign launches",
                    "body": "Coordinate launch notes.",
                    "cta": "Learn more",
                },
                "expected_decision": "approved",
            }
        ],
        mode="model-only",
        ollama_model="missing-model",
    )

    assert metrics["mode"] == "model-only"
    assert metrics["input_examples"] == 1
    assert metrics["total_examples"] == 0
    assert metrics["skipped_examples"] == 1
    assert metrics["model_status_counts"] == {"unavailable": 1}
    assert metrics["model_required_failures"] == 1


def test_model_only_eval_scores_valid_local_model_response(monkeypatch) -> None:
    def fake_classify(submission, *, model=None, endpoint=None):
        return [
            PolicyHit(
                policy_id="model_policy_review",
                severity="medium",
                category="model_review",
                evidence=[Evidence(text="review requested", source="model")],
                recommended_action="Review model concern.",
                requires_review=True,
                source="ollama",
            )
        ], {
            "enabled": True,
            "provider": "ollama",
            "model": model,
            "endpoint": endpoint,
            "status": "ok",
            "ran": True,
            "raw_decision": "needs_review",
        }

    monkeypatch.setattr(run_eval, "classify_with_ollama", fake_classify)

    metrics = run_eval._run_eval(
        [
            {
                "id": "model-review",
                "input": {
                    "platform": "google",
                    "industry": "general",
                    "headline": "Check this ad",
                    "body": "The local model asks for review.",
                    "cta": "Learn more",
                },
                "expected_decision": "needs_review",
                "expected_policy_ids": ["model_policy_review"],
                "expected_categories": ["model_review"],
            }
        ],
        mode="model-only",
        ollama_model="installed-model",
    )

    assert metrics["total_examples"] == 1
    assert metrics["decision_accuracy"] == 1.0
    assert metrics["model_status_counts"] == {"ok": 1}
    assert metrics["policy_metrics"]["model_policy_review"]["recall"] == 1.0


def test_eval_runner_reports_confusion_matrix_notes_and_category_metrics() -> None:
    results = [
        {
            "id": "ok",
            "expected_decision": "approved",
            "actual_decision": "approved",
            "decision_match": True,
            "decision_error_type": None,
            "expected_policy_ids": [],
            "actual_policy_ids": [],
            "expected_categories": [],
            "actual_categories": [],
            "actual_policy_categories": {},
            "policy_evidence": {},
            "policy_true_positives": [],
            "policy_false_negatives": [],
            "policy_false_positives": [],
            "category_true_positives": [],
            "category_false_negatives": [],
            "category_false_positives": [],
        },
        {
            "id": "miss",
            "expected_decision": "needs_review",
            "actual_decision": "high_risk",
            "decision_match": False,
            "decision_error_type": "overcall",
            "expected_policy_ids": ["wellness_claim_review"],
            "actual_policy_ids": ["wellness_claim_review", "guaranteed_outcome"],
            "expected_categories": ["health_claims"],
            "actual_categories": ["health_claims"],
            "actual_policy_categories": {
                "wellness_claim_review": "health_claims",
                "guaranteed_outcome": "health_claims",
            },
            "policy_evidence": {
                "guaranteed_outcome": [{"source": "headline", "text": "guaranteed"}],
            },
            "policy_true_positives": ["wellness_claim_review"],
            "policy_false_negatives": [],
            "policy_false_positives": ["guaranteed_outcome"],
            "category_true_positives": ["health_claims"],
            "category_false_negatives": [],
            "category_false_positives": [],
        },
    ]

    metrics = run_eval._metrics(results)

    assert metrics["decision_accuracy"] == 0.5
    assert metrics["confusion_matrix"]["needs_review"]["high_risk"] == 1
    assert metrics["decision_metrics"]["high_risk"]["false_positive_count"] == 1
    assert metrics["policy_metrics"]["guaranteed_outcome"]["precision"] == 0.0
    assert metrics["category_metrics"]["health_claims"]["recall"] == 1.0
    assert metrics["review_notes"]["decision_mismatches"][0]["row_id"] == "miss"
    assert metrics["review_notes"]["false_positives"][0]["evidence"] == [{"source": "headline", "text": "guaranteed"}]


def test_eval_runner_counts_categories_once_per_row() -> None:
    results = [
        {
            "id": "two-health-policies",
            "expected_decision": "high_risk",
            "actual_decision": "high_risk",
            "decision_match": True,
            "decision_error_type": None,
            "expected_policy_ids": ["unsupported_health_claim", "guaranteed_outcome"],
            "actual_policy_ids": ["unsupported_health_claim", "guaranteed_outcome"],
            "expected_categories": ["health_claims"],
            "actual_categories": ["health_claims"],
            "actual_policy_categories": {
                "unsupported_health_claim": "health_claims",
                "guaranteed_outcome": "health_claims",
            },
            "policy_evidence": {},
            "policy_true_positives": ["unsupported_health_claim", "guaranteed_outcome"],
            "policy_false_negatives": [],
            "policy_false_positives": [],
            "category_true_positives": ["health_claims"],
            "category_false_negatives": [],
            "category_false_positives": [],
        }
    ]

    metrics = run_eval._metrics(results)

    assert metrics["policy_metrics"]["guaranteed_outcome"]["true_positive_count"] == 1
    assert metrics["policy_metrics"]["unsupported_health_claim"]["true_positive_count"] == 1
    assert metrics["category_metrics"]["health_claims"]["true_positive_count"] == 1


def test_hybrid_value_metrics_quantify_model_adds_and_harm() -> None:
    modes = {
        "rule-only": {
            "decision_accuracy": 0.5,
            "results": [
                {
                    "id": "rescued",
                    "expected_decision": "needs_review",
                    "actual_decision": "approved",
                    "decision_match": False,
                    "decision_error_type": "undercall",
                    "expected_policy_ids": ["model_policy_review"],
                    "actual_policy_ids": [],
                    "model": {"status": "disabled"},
                },
                {
                    "id": "extra-review",
                    "expected_decision": "approved",
                    "actual_decision": "approved",
                    "decision_match": True,
                    "decision_error_type": None,
                    "expected_policy_ids": [],
                    "actual_policy_ids": [],
                    "model": {"status": "disabled"},
                },
            ],
        },
        "model-only": {
            "decision_accuracy": 0.5,
            "results": [
                {
                    "id": "rescued",
                    "expected_decision": "needs_review",
                    "actual_decision": "needs_review",
                    "decision_match": True,
                    "decision_error_type": None,
                    "actual_policy_ids": ["model_policy_review"],
                    "model": {"status": "ok"},
                },
                {
                    "id": "extra-review",
                    "expected_decision": "approved",
                    "actual_decision": "needs_review",
                    "decision_match": False,
                    "decision_error_type": "overcall",
                    "actual_policy_ids": ["model_policy_review"],
                    "model": {"status": "ok"},
                },
            ],
        },
        "hybrid": {
            "decision_accuracy": 1.0,
            "results": [
                {
                    "id": "rescued",
                    "expected_decision": "needs_review",
                    "actual_decision": "needs_review",
                    "decision_match": True,
                    "decision_error_type": None,
                    "expected_policy_ids": ["model_policy_review"],
                    "actual_policy_ids": ["model_policy_review"],
                    "model": {"status": "ok"},
                },
                {
                    "id": "extra-review",
                    "expected_decision": "approved",
                    "actual_decision": "approved",
                    "decision_match": True,
                    "decision_error_type": None,
                    "expected_policy_ids": [],
                    "actual_policy_ids": ["model_policy_review"],
                    "model": {"status": "ok"},
                },
            ],
        },
    }

    value = run_eval._hybrid_value_metrics(modes)

    assert value["hybrid_vs_rule_decision_accuracy_delta"] == 0.5
    assert value["model_ok_rows"] == 2
    assert value["decision_improvement_count"] == 1
    assert value["decision_regression_count"] == 0
    assert value["model_added_policy_hit_count"] == 2
    assert value["model_added_expected_policy_hit_count"] == 1
    assert value["model_added_false_positive_policy_hit_count"] == 1
    assert value["model_rescued_policy_false_negative_count"] == 1
    assert value["model_only_overcall_count"] == 1
    extra_review_note = next(
        note for note in value["review_notes"]["model_added_findings"] if note["row_id"] == "extra-review"
    )
    assert extra_review_note["added_false_positive_policy_ids"] == [
        "model_policy_review"
    ]


def test_benchmark_dataset_is_reproducible_labeled_and_large_enough() -> None:
    generated_rows = generate_benchmark_dataset.build_rows()
    dataset_path = ROOT / "evals" / "datasets" / "rule_benchmark_v1.jsonl"
    dataset_rows = run_eval._load_rows(dataset_path)

    assert len(dataset_rows) == 200
    assert len(dataset_rows) == len({row["id"] for row in dataset_rows})
    assert {row["expected_decision"] for row in dataset_rows} == {"approved", "needs_review", "high_risk"}
    assert dataset_rows == generated_rows


def test_benchmark_dataset_reports_policy_and_category_precision_recall() -> None:
    dataset_path = ROOT / "evals" / "datasets" / "rule_benchmark_v1.jsonl"
    rows = run_eval._load_rows(dataset_path)
    policy_categories = run_eval._policy_categories()
    metrics = run_eval._metrics(
        [run_eval._score_row(row, policy_categories=policy_categories) for row in rows],
        max_review_notes=100,
    )

    assert metrics["total_examples"] == 200
    assert metrics["decision_accuracy"] == 1.0
    assert {"approved", "needs_review", "high_risk"} <= metrics["confusion_matrix"].keys()
    assert "health_claims" in metrics["category_metrics"]
    assert "guaranteed_outcome" in metrics["policy_metrics"]
    assert metrics["review_notes"]["decision_mismatches"] == []
    assert metrics["review_notes"]["false_positives"] == []
    assert metrics["review_notes"]["false_negatives"] == []


def test_real_case_dataset_has_adjudicated_policy_labels() -> None:
    dataset_path = ROOT / "evals" / "datasets" / "real_cases_v1.jsonl"
    rows = run_eval._load_rows(dataset_path)
    policy_categories = run_eval._policy_categories()
    metrics = run_eval._metrics(
        [run_eval._score_row(row, policy_categories=policy_categories) for row in rows],
        max_review_notes=100,
    )

    assert metrics["total_examples"] == 13
    assert metrics["decision_accuracy"] == 1.0
    assert metrics["review_notes"]["decision_mismatches"] == []
    assert metrics["review_notes"]["false_positives"] == []
    assert metrics["review_notes"]["false_negatives"] == []


def test_eval_docs_reference_current_reproducible_commands_and_dataset() -> None:
    eval_report = (ROOT / "docs" / "eval_report.md").read_text(encoding="utf-8")
    eval_readme = (ROOT / "evals" / "README.md").read_text(encoding="utf-8")

    assert "make benchmark-data" in eval_report
    assert "make benchmark" in eval_report
    assert "make model-benchmark" in eval_report
    assert "make model-smoke" in eval_report
    assert "make model-smoke" in eval_readme
    assert "make eval" in eval_report
    assert "evals/datasets/rule_benchmark_v1.jsonl" in eval_report
    assert "not evidence of legal compliance" in eval_report
    assert "make benchmark-data" in eval_readme
    assert "make model-benchmark" in eval_readme
    assert "do not predict" in eval_readme
    assert "platform approval" in eval_readme
