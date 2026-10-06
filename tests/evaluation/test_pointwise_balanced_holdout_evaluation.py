from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from product_variant_resolver.pointwise_balanced_holdout_evaluation import (
    MINIMUM_EXACT_CORRECT_MATCHED,
    NEGATIVE_COUNT,
    OUTPUT_PATH,
    POSITIVE_COUNT,
    check,
    combine_metrics,
    evaluate,
    summarize_positive,
)
from product_variant_resolver.schemas import ResolutionStatus

ROOT = Path(__file__).resolve().parents[2]
RESULT_SHA256 = "8764f2642208b7cfddf63402fb18f487514af1b38a2d183afbc4da41b72a9566"


def test_actual_balanced_result_is_aggregate_only_and_non_runtime() -> None:
    assert hashlib.sha256((ROOT / OUTPUT_PATH).read_bytes()).hexdigest() == RESULT_SHA256
    payload = check(ROOT)
    assert payload["positive_metrics"]["sample_count"] == POSITIVE_COUNT
    assert payload["negative_metrics_reused"]["sample_count"] == NEGATIVE_COUNT
    assert payload["combined_metrics"]["sample_count"] == POSITIVE_COUNT + NEGATIVE_COUNT
    assert payload["guardrails"]["negative_holdout_rerun"] is False
    assert payload["guardrails"]["row_level_output_persisted"] is False
    assert payload["guardrails"]["runtime_activation_authorized"] is False


def test_positive_summary_preserves_casting_and_exact_identity_levels() -> None:
    matched = MINIMUM_EXACT_CORRECT_MATCHED
    statuses = [ResolutionStatus.matched] * matched + [ResolutionStatus.ambiguous] * (
        POSITIVE_COUNT - matched
    )
    exact = [True] * matched + [False] * (POSITIVE_COUNT - matched)
    metrics = summarize_positive(
        statuses,
        ["reason"] * POSITIVE_COUNT,
        [0.5] * POSITIVE_COUNT,
        exact,
        exact,
    )
    assert metrics["casting_correct_matched_count"] == matched
    assert metrics["exact_correct_matched_count"] == matched
    assert metrics["exact_matched_precision"] == 1.0
    assert metrics["false_no_match_rate"] == 0.0


def test_combined_metrics_count_wrong_release_as_false_decisive() -> None:
    positive = {
        "ambiguous_count": 40,
        "exact_correct_matched_count": 9,
        "exact_match_recall": 9 / 53,
        "false_no_match_count": 1,
        "matched_count": 12,
    }
    negative = {
        "ambiguous_count": 9,
        "matched_count": 0,
        "no_match_count": 11,
        "no_match_recall": 11 / 20,
    }
    combined = combine_metrics(positive, negative)
    assert combined["end_to_end_correct_count"] == 20
    assert combined["false_decisive_count"] == 4
    assert combined["ambiguous_count"] == 49


def test_check_rejects_row_level_output(tmp_path: Path) -> None:
    destination = tmp_path / OUTPUT_PATH
    destination.parent.mkdir(parents=True)
    payload = json.loads((ROOT / OUTPUT_PATH).read_text(encoding="utf-8"))
    payload["predictions"] = [{"query": "forbidden"}]
    destination.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="row-level"):
        check(tmp_path)


def test_evaluate_refuses_a_second_positive_run_before_model_load(tmp_path: Path) -> None:
    destination = tmp_path / OUTPUT_PATH
    destination.parent.mkdir(parents=True)
    destination.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError, match="one positive run"):
        evaluate(tmp_path)
