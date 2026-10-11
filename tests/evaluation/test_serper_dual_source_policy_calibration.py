from __future__ import annotations

import json
from pathlib import Path

import pytest

from product_variant_resolver.serper_dual_source_evaluation import (
    DATASET as POSITIVE_DATASET,
)
from product_variant_resolver.serper_dual_source_evaluation import (
    load_frozen_grouped_split,
    load_serper_dual_source_dataset,
)
from product_variant_resolver.serper_dual_source_policy_calibration import (
    POLICY_DATASET,
    POLICY_DATASET_SHA256,
    PolicyQueryDataset,
    _calibration_metrics,
    _contains_row_level_key,
    build_grouped_split,
    check,
    load_policy_dataset,
)

ROOT = Path(__file__).resolve().parents[2]


def test_frozen_policy_dataset_has_paired_development_and_holdout_contract() -> None:
    dataset = load_policy_dataset(ROOT / POLICY_DATASET)
    assert dataset.target_count == 80
    assert dataset.record_count == 160
    assert len(dataset.target_pairs()) == 80
    assert all(
        image.target_id == shopping.target_id
        and image.source_type == "image_search"
        and shopping.source_type == "shopping"
        for image, shopping in dataset.target_pairs()
    )
    targets = [pair[0] for pair in dataset.target_pairs()]
    assert sum(row.partition == "no_match_development" for row in targets) == 40
    assert (
        sum(row.partition == "policy_holdout" and row.truth == "catalog_present" for row in targets)
        == 20
    )
    assert (
        sum(
            row.partition == "policy_holdout" and row.truth == "catalog_relative_no_match"
            for row in targets
        )
        == 20
    )


def test_policy_dataset_rejects_source_pair_disagreement() -> None:
    payload = json.loads((ROOT / POLICY_DATASET).read_text(encoding="utf-8"))
    payload["records"][1]["expected_casting"] = "Changed Casting"
    with pytest.raises(ValueError, match="expected casting differs|source truth differs"):
        PolicyQueryDataset.model_validate(payload)


def test_grouped_split_is_deterministic_and_keeps_source_pairs_together() -> None:
    positive = load_serper_dual_source_dataset(ROOT / POSITIVE_DATASET)
    positive_split = load_frozen_grouped_split(positive, ROOT / POSITIVE_DATASET)
    policy = load_policy_dataset(ROOT / POLICY_DATASET)
    negative_ids = tuple(
        image.target_id
        for image, _shopping in policy.target_pairs()
        if image.partition == "no_match_development"
    )
    split = build_grouped_split(positive_split.development_target_ids, negative_ids)
    repeated = build_grouped_split(positive_split.development_target_ids, negative_ids)
    assert split == repeated
    assert len(split.assignment) == 140
    assert sum(value == "calibration_fit" for value in split.assignment.values()) == 98
    assert sum(value == "threshold_selection" for value in split.assignment.values()) == 42
    assert all(
        split.assignment[image.target_id] == split.assignment[shopping.target_id]
        for image, shopping in policy.target_pairs()
        if image.partition == "no_match_development"
    )


def test_calibration_metrics_report_reliability_and_risk_coverage() -> None:
    metrics = _calibration_metrics([0.95, 0.80, 0.20, 0.05], [1, 1, 0, 0])
    assert metrics["sample_count"] == 4
    assert metrics["positive_count"] == 2
    assert len(metrics["reliability_bins"]) == 10
    assert len(metrics["risk_coverage"]) == 5
    assert metrics["brier_score"] < 0.03


def test_recursive_guard_rejects_row_level_output() -> None:
    assert _contains_row_level_key({"metrics": {"records": []}})
    assert _contains_row_level_key({"query": "secret"})
    assert not _contains_row_level_key({"sample_count": 84, "brier_score": 0.1})


def test_materialized_artifacts_are_aggregate_only_and_holdout_is_sealed() -> None:
    payload = check(ROOT)
    assert payload["bindings"]["policy_dataset_sha256"] == POLICY_DATASET_SHA256
    assert payload["grouped_split"]["fit_observation_count"] == 196
    assert payload["grouped_split"]["selection_observation_count"] == 84
    assert payload["guardrails"]["fresh_holdout_observations_scored"] == 0
    assert payload["guardrails"]["opened_50_target_ranking_final_reused"] is False
    assert payload["guardrails"]["runtime_eligible"] is False
    assert payload["metrics"]["selected_method"] in {
        "five_feature_logistic",
        "top_score_isotonic",
        "top_score_temperature",
    }
