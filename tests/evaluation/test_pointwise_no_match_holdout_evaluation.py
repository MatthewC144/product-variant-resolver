from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from product_variant_resolver.pointwise_no_match_holdout_evaluation import (
    MAXIMUM_MATCHED_COUNT,
    MINIMUM_NO_MATCH_COUNT,
    OUTPUT_PATH,
    check,
    evaluate,
    summarize,
)
from product_variant_resolver.schemas import ResolutionStatus

ROOT = Path(__file__).resolve().parents[2]
RESULT_SHA256 = "937eabc88164532ce686d5c1d4521d0ffef58efc2691d8836cba723fd68b05c6"


def test_actual_holdout_result_is_aggregate_only_and_non_runtime() -> None:
    assert hashlib.sha256((ROOT / OUTPUT_PATH).read_bytes()).hexdigest() == RESULT_SHA256
    payload = check(ROOT)
    metrics = payload["metrics"]
    assert metrics["sample_count"] == 20
    assert metrics["no_match_count"] + metrics["ambiguous_count"] + metrics["matched_count"] == 20
    assert payload["guardrails"]["row_level_output_persisted"] is False
    assert payload["guardrails"]["runtime_activation_authorized"] is False
    assert payload["guardrails"]["model_changed"] is False
    assert payload["guardrails"]["thresholds_changed"] is False


def test_summary_uses_preregistered_aggregate_gates() -> None:
    statuses = (
        [ResolutionStatus.no_match] * MINIMUM_NO_MATCH_COUNT
        + [ResolutionStatus.matched] * MAXIMUM_MATCHED_COUNT
        + [ResolutionStatus.ambiguous] * (20 - MINIMUM_NO_MATCH_COUNT - MAXIMUM_MATCHED_COUNT)
    )
    metrics = summarize(statuses, ["reason"] * 20, [0.5] * 20)
    assert metrics["no_match_recall"] == MINIMUM_NO_MATCH_COUNT / 20
    assert metrics["false_match_rate"] == MAXIMUM_MATCHED_COUNT / 20
    assert metrics["decisive_count"] == MINIMUM_NO_MATCH_COUNT + MAXIMUM_MATCHED_COUNT


def test_check_rejects_row_level_output(tmp_path: Path) -> None:
    destination = tmp_path / OUTPUT_PATH
    destination.parent.mkdir(parents=True)
    payload = json.loads((ROOT / OUTPUT_PATH).read_text(encoding="utf-8"))
    payload["predictions"] = [{"query": "forbidden"}]
    destination.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="row-level"):
        check(tmp_path)


def test_evaluate_refuses_a_second_run_before_loading_the_model(tmp_path: Path) -> None:
    destination = tmp_path / OUTPUT_PATH
    destination.parent.mkdir(parents=True)
    destination.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError, match="one run"):
        evaluate(tmp_path)
