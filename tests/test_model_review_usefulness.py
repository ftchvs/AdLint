from __future__ import annotations

from evals import model_review_usefulness


def test_measure_usefulness_reports_useful_and_false_review_burden() -> None:
    metrics = {
        "dataset": "evals/datasets/seed_ads.jsonl",
        "modes": {"hybrid": {"model_status_counts": {"ok": 3, "invalid_response": 1}}},
        "hybrid_value": {
            "comparable_rows": 4,
            "rows_with_model_added_generic_review": 3,
            "review_notes": {
                "model_added_findings": [
                    {
                        "row_id": "health-001",
                        "added_policy_ids": ["model_policy_review"],
                        "added_generic_policy_ids": ["model_policy_review"],
                        "added_false_positive_policy_ids": [],
                    },
                    {
                        "row_id": "saas-001",
                        "added_policy_ids": ["model_policy_review"],
                        "added_generic_policy_ids": ["model_policy_review"],
                        "added_false_positive_policy_ids": ["model_policy_review"],
                    },
                    {
                        "row_id": "unlabeled-row",
                        "added_policy_ids": ["model_policy_review"],
                        "added_generic_policy_ids": ["model_policy_review"],
                        "added_false_positive_policy_ids": [],
                    },
                ]
            },
        },
    }
    labels = {
        "health-001": {
            "expected_review_dimension": "claim_substantiation",
            "acceptable_generic_review": True,
            "useful_policy_ids": ["model_policy_review"],
        },
        "saas-001": {
            "expected_review_dimension": "none",
            "acceptable_generic_review": False,
            "useful_policy_ids": [],
        },
    }

    report = model_review_usefulness.measure_usefulness(metrics, labels)

    assert report["model_added_note_rows"] == 3
    assert report["labeled_model_added_note_rows"] == 2
    assert report["useful_model_added_note_rows"] == 1
    assert report["false_review_burden_rows"] == 1
    assert report["useful_note_precision"] == 0.5
    assert report["false_review_burden_rate"] == 0.5
    assert report["generic_review_burden_rate"] == 0.75
    assert report["model_invalid_response_rate"] == 0.25
    assert report["unlabeled_model_added_note_rows"] == 1


def test_model_review_usefulness_labels_are_valid_and_unique() -> None:
    labels = model_review_usefulness._load_labels(
        model_review_usefulness.Path("evals/datasets/model_review_usefulness_v1.jsonl")
    )

    assert labels
    assert "health-001" in labels
    assert all("expected_review_dimension" in row for row in labels.values())
    assert all("acceptable_generic_review" in row for row in labels.values())
    assert all(isinstance(row.get("useful_policy_ids", []), list) for row in labels.values())
