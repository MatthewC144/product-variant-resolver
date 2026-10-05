from __future__ import annotations

from pathlib import Path

import pytest

from product_variant_resolver.image_search_evaluation import (
    load_frozen_split,
    load_image_search_dataset,
)
from product_variant_resolver.image_search_pointwise_calibration import (
    FIT_COUNT,
    FROZEN_INNER_SPLIT_SHA256,
    SELECTION_COUNT,
    CalibrationRow,
    _inner_assignment,
    check,
    fit_development_calibration,
    select_threshold,
)

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data/evaluation/image-search-resolver-v1/dataset.json"


def test_nested_development_split_is_frozen_and_disjoint() -> None:
    dataset = load_image_search_dataset(DATASET)
    outer = load_frozen_split(dataset, DATASET)
    assignment, digest = _inner_assignment(outer.development_case_ids)
    assert digest == FROZEN_INNER_SPLIT_SHA256
    assert len(assignment) == 100
    assert sum(value == "calibration_fit" for value in assignment.values()) == FIT_COUNT
    assert sum(value == "threshold_selection" for value in assignment.values()) == SELECTION_COUNT
    assert set(assignment) == set(outer.development_case_ids)
    assert not set(assignment) & set(outer.test_case_ids)


def test_actual_calibration_artifacts_are_aggregate_and_valid() -> None:
    payload = check(ROOT, require_local_source=False)
    assert payload["status"] == "development_calibrated_not_runtime_eligible"
    assert payload["guardrails"]["test_cases_scored"] == 0
    assert payload["guardrails"]["row_level_output_persisted"] is False
    assert payload["guardrails"]["runtime_eligible"] is False


def test_threshold_selector_chooses_highest_coverage_eligible_threshold() -> None:
    result = select_threshold(
        [(0.9, 1), (0.8, 1), (0.7, 0), (0.6, 1), (0.5, 0)],
        minimum_precision=0.75,
        minimum_accepted=2,
    )
    assert result.threshold == 0.6
    assert result.accepted_count == 4
    assert result.accepted_correct == 3
    assert result.precision == 0.75
    assert result.coverage == 0.8


def test_threshold_selector_publishes_shortfall_instead_of_forcing_policy() -> None:
    with pytest.raises(ValueError, match="cannot meet"):
        select_threshold(
            [(0.9, 0), (0.8, 0), (0.7, 1)],
            minimum_precision=1.0,
            minimum_accepted=2,
        )


def test_calibration_policy_is_positive_only_and_not_runtime_eligible() -> None:
    rows: list[CalibrationRow] = []
    for index in range(FIT_COUNT):
        label = index % 2
        score = 5.0 if label else -5.0
        rows.append(
            CalibrationRow(
                case_id=f"fit-{index:03d}",
                partition="calibration_fit",
                vector=(score, 1.0, 1.0, 0.0, 0.0),
                exact_top1_correct=label,
            )
        )
    for index in range(SELECTION_COUNT):
        label = int(index < 20)
        score = 5.0 if label else -5.0
        rows.append(
            CalibrationRow(
                case_id=f"selection-{index:03d}",
                partition="threshold_selection",
                vector=(score, 1.0, 1.0, 0.0, 0.0),
                exact_top1_correct=label,
            )
        )

    artifact, policy, metrics = fit_development_calibration(rows, "a" * 64)

    assert artifact.model_version == "logistic-python-v1+neural-pointwise-v1"
    assert policy.no_match_threshold == 0.0
    assert policy.margin_threshold == 0.0
    assert policy.require_positive_top_score is False
    assert policy.runtime_eligible is False
    assert metrics["fit"]["sample_count"] == FIT_COUNT
    assert metrics["threshold_selection"]["sample_count"] == SELECTION_COUNT
    assert metrics["threshold_selection"]["precision"] == 1.0
