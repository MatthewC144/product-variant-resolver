from __future__ import annotations

from pathlib import Path

import pytest

from product_variant_resolver.pointwise_three_class_calibration import (
    MATCH_MINIMUM_PRECISION,
    MAXIMUM_FALSE_NO_MATCH_RATE,
    NO_MATCH_MINIMUM_PRECISION,
    check,
    select_no_match_threshold,
)

ROOT = Path(__file__).resolve().parents[2]


def test_actual_three_class_artifacts_pass_both_frozen_gates() -> None:
    payload = check(ROOT, require_local_inputs=True)
    assert payload["status"] == "development_three_class_calibrated_not_runtime_authorized"
    assert payload["shortfalls"] == []
    selection = payload["metrics"]["threshold_selection"]
    assert selection["match"]["precision"] >= MATCH_MINIMUM_PRECISION
    assert selection["no_match"]["precision"] >= NO_MATCH_MINIMUM_PRECISION
    assert selection["no_match"]["catalog_present_false_rate"] <= MAXIMUM_FALSE_NO_MATCH_RATE
    assert payload["guardrails"]["final_test_cases_read"] == 0
    assert payload["guardrails"]["runtime_eligible"] is False


def test_no_match_selector_maximizes_recall_under_safety_gates() -> None:
    rows = [
        (0.05, True),
        (0.10, True),
        (0.15, True),
        (0.20, True),
        (0.25, True),
        (0.30, False),
        (0.40, False),
        (0.80, False),
    ]
    selected = select_no_match_threshold(
        rows,
        match_threshold=0.70,
        minimum_accepted=5,
        minimum_precision=0.90,
        maximum_false_no_match_rate=0.10,
    )
    assert selected.predicted_count == 5
    assert selected.correct_count == 5
    assert selected.precision == 1.0
    assert selected.recall == 1.0
    assert selected.catalog_present_false_count == 0


def test_no_match_selector_reports_shortfall_instead_of_relaxing_gate() -> None:
    rows = [
        (0.05, False),
        (0.10, False),
        (0.15, False),
        (0.80, True),
        (0.85, True),
        (0.90, True),
        (0.95, True),
        (0.99, True),
    ]
    with pytest.raises(ValueError, match="cannot meet"):
        select_no_match_threshold(rows, match_threshold=0.99)
