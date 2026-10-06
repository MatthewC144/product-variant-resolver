"""One-run positive policy evaluation plus the frozen no-match aggregate result."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from statistics import fmean
from typing import Any

from .calibration import CalibrationArtifact, LogisticCalibrator
from .identity import normalize_text
from .image_search_evaluation import (
    DATASET,
    FROZEN_DATASET_SHA256,
    FROZEN_SPLIT_SHA256,
    SOURCE,
    bind_dataset_to_source,
    load_frozen_split,
    load_image_search_dataset,
    load_source_records,
)
from .image_search_pointwise_calibration import (
    load_pointwise_scoring_context as load_scoring_context,
)
from .image_search_pointwise_calibration import score_pointwise_query
from .image_search_ranking_development import (
    FINAL_COMPARISON,
    POINTWISE_CONFIG,
    POINTWISE_MODEL,
)
from .pointwise_no_match_holdout_evaluation import (
    OUTPUT_PATH as NEGATIVE_RESULT_PATH,
)
from .pointwise_no_match_holdout_evaluation import check as check_negative_result
from .pointwise_three_class_calibration import (
    CALIBRATION_PATH,
    POLICY_PATH,
    SELECTION_PATH,
)
from .pointwise_three_class_calibration import check as check_three_class
from .policy import DecisionPolicy
from .schemas import ResolutionStatus

SCHEMA_VERSION = "pvr-image-search-pointwise-balanced-holdout-evaluation-v1"
OUTPUT_PATH = Path("data/evaluation/image-search-pointwise-balanced-holdout-v1/results.json")

POSITIVE_DATASET_SHA256 = FROZEN_DATASET_SHA256
POSITIVE_SPLIT_SHA256 = FROZEN_SPLIT_SHA256
POSITIVE_FINAL_COMPARISON_SHA256 = (
    "fdf5c81f073d134a1f15b8427102ff7f6e48b651f350febb6e800b39a389c5a7"
)
CATALOG_SHA256 = "b4e0747450a5447c2bf66b0838c91f3f723a19ac97c90c7ac3636cf3a9a709d4"
CALIBRATION_SHA256 = "22990e52d2a64a051ac4da272999e628dc7c41f300bc7e897f431da2fbd7406d"
POLICY_SHA256 = "68969b386a05002fca8f48826f37f5a00c24128672fbfbf3befb748b881ab418"
SELECTION_SHA256 = "e67c8789889e09ca54871bbb93e0e979309286bae7970a321dcf97db4facebfe"
POINTWISE_CONFIG_SHA256 = "3a88163cc7abc84468024f5e6410e0ca489a80a710b67b4c2474c4b4f7d7fad6"
POINTWISE_MANIFEST_SHA256 = "32f889bb415ef5a56760a299da0635e8e1704d46fe0b11ded06c563de896feb8"
NEGATIVE_RESULT_SHA256 = "937eabc88164532ce686d5c1d4521d0ffef58efc2691d8836cba723fd68b05c6"
OWNER_AUTHORIZATION_SHA256 = "3c67524ab06ab2c63608182535390cb55e61a1566aa6d5dee023821fea2d066b"

POSITIVE_COUNT = 53
NEGATIVE_COUNT = 20
MINIMUM_EXACT_CORRECT_MATCHED = 5
MINIMUM_EXACT_MATCHED_PRECISION = 0.90
MAXIMUM_FALSE_NO_MATCH_RATE = 0.10
AUTHORITY_NOTE = (
    "Expected identities and no-match truth are relative only to the frozen third-party catalog "
    "snapshot; they are not manufacturer-certified or global product truth."
)

_ROW_LEVEL_KEYS = {
    "candidate",
    "candidates",
    "case_id",
    "case_ids",
    "expected_casting",
    "expected_full_identity",
    "id",
    "prediction",
    "predictions",
    "query",
    "queries",
    "row",
    "rows",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return payload


def _contains_row_level_key(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            (isinstance(key, str) and key in _ROW_LEVEL_KEYS) or _contains_row_level_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_row_level_key(item) for item in value)
    return False


def _require_keys(value: dict[str, Any], expected: set[str], name: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{name} keys differ from the frozen contract")


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    return value


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _bindings(root: Path) -> dict[str, str]:
    bindings = {
        "calibration_path": str(CALIBRATION_PATH),
        "calibration_sha256": _sha256(root / CALIBRATION_PATH),
        "catalog_path": str(SOURCE),
        "catalog_sha256": _sha256(root / SOURCE),
        "negative_result_path": str(NEGATIVE_RESULT_PATH),
        "negative_result_sha256": _sha256(root / NEGATIVE_RESULT_PATH),
        "owner_authorization_sha256": OWNER_AUTHORIZATION_SHA256,
        "pointwise_config_sha256": _sha256(root / POINTWISE_CONFIG),
        "pointwise_model_manifest_sha256": _sha256(root / POINTWISE_MODEL / "manifest.json"),
        "policy_path": str(POLICY_PATH),
        "policy_sha256": _sha256(root / POLICY_PATH),
        "positive_dataset_path": str(DATASET),
        "positive_dataset_sha256": _sha256(root / DATASET),
        "positive_final_comparison_path": str(FINAL_COMPARISON),
        "positive_final_comparison_sha256": _sha256(root / FINAL_COMPARISON),
        "positive_split_sha256": POSITIVE_SPLIT_SHA256,
        "selection_path": str(SELECTION_PATH),
        "selection_sha256": _sha256(root / SELECTION_PATH),
    }
    expected = {
        "calibration_sha256": CALIBRATION_SHA256,
        "catalog_sha256": CATALOG_SHA256,
        "negative_result_sha256": NEGATIVE_RESULT_SHA256,
        "pointwise_config_sha256": POINTWISE_CONFIG_SHA256,
        "pointwise_model_manifest_sha256": POINTWISE_MANIFEST_SHA256,
        "policy_sha256": POLICY_SHA256,
        "positive_dataset_sha256": POSITIVE_DATASET_SHA256,
        "positive_final_comparison_sha256": POSITIVE_FINAL_COMPARISON_SHA256,
        "positive_split_sha256": POSITIVE_SPLIT_SHA256,
        "selection_sha256": SELECTION_SHA256,
    }
    if any(bindings[key] != value for key, value in expected.items()):
        raise ValueError("evaluation input differs from the frozen PBHE-G1 binding")
    return bindings


def summarize_positive(
    statuses: list[ResolutionStatus],
    reasons: list[str],
    confidences: list[float],
    casting_correct: list[bool],
    exact_correct: list[bool],
) -> dict[str, Any]:
    if not (
        len(statuses)
        == len(reasons)
        == len(confidences)
        == len(casting_correct)
        == len(exact_correct)
        == POSITIVE_COUNT
        and all(math.isfinite(value) and 0 <= value <= 1 for value in confidences)
    ):
        raise ValueError("positive outcomes must contain 53 aligned finite rows")
    if any(
        exact and not casting for exact, casting in zip(exact_correct, casting_correct, strict=True)
    ):
        raise ValueError("an exact release match must also be a casting match")
    status_counts = Counter(status.value for status in statuses)
    reason_counts = Counter(reasons)
    matched_count = status_counts[ResolutionStatus.matched.value]
    ambiguous_count = status_counts[ResolutionStatus.ambiguous.value]
    no_match_count = status_counts[ResolutionStatus.no_match.value]
    casting_correct_count = sum(casting_correct)
    exact_correct_count = sum(exact_correct)
    return {
        "ambiguous_count": ambiguous_count,
        "ambiguous_rate": ambiguous_count / POSITIVE_COUNT,
        "casting_correct_matched_count": casting_correct_count,
        "casting_match_recall": casting_correct_count / POSITIVE_COUNT,
        "casting_matched_precision": (
            casting_correct_count / matched_count if matched_count else 0.0
        ),
        "confidence_summary": {
            "maximum": max(confidences),
            "mean": fmean(confidences),
            "minimum": min(confidences),
        },
        "decision_reason_counts": dict(sorted(reason_counts.items())),
        "exact_correct_matched_count": exact_correct_count,
        "exact_match_recall": exact_correct_count / POSITIVE_COUNT,
        "exact_matched_precision": exact_correct_count / matched_count if matched_count else 0.0,
        "false_no_match_count": no_match_count,
        "false_no_match_rate": no_match_count / POSITIVE_COUNT,
        "matched_count": matched_count,
        "sample_count": POSITIVE_COUNT,
    }


def combine_metrics(positive: dict[str, Any], negative: dict[str, Any]) -> dict[str, Any]:
    exact_positive = _integer(positive.get("exact_correct_matched_count"), "positive exact correct")
    positive_matched = _integer(positive.get("matched_count"), "positive matched")
    positive_no_match = _integer(positive.get("false_no_match_count"), "positive no-match")
    positive_ambiguous = _integer(positive.get("ambiguous_count"), "positive ambiguous")
    negative_no_match = _integer(negative.get("no_match_count"), "negative no-match")
    negative_matched = _integer(negative.get("matched_count"), "negative matched")
    negative_ambiguous = _integer(negative.get("ambiguous_count"), "negative ambiguous")
    total = POSITIVE_COUNT + NEGATIVE_COUNT
    decisive = positive_matched + positive_no_match + negative_no_match + negative_matched
    correct = exact_positive + negative_no_match
    false_decisive = positive_matched - exact_positive + positive_no_match + negative_matched
    ambiguous = positive_ambiguous + negative_ambiguous
    return {
        "ambiguous_count": ambiguous,
        "ambiguous_rate": ambiguous / total,
        "balanced_identity_recall": (
            _number(positive.get("exact_match_recall"), "positive exact recall")
            + _number(negative.get("no_match_recall"), "negative no-match recall")
        )
        / 2,
        "decisive_count": decisive,
        "decisive_exact_precision": correct / decisive if decisive else 0.0,
        "end_to_end_correct_count": correct,
        "end_to_end_exact_accuracy": correct / total,
        "false_decisive_count": false_decisive,
        "false_decisive_rate": false_decisive / total,
        "negative_count": NEGATIVE_COUNT,
        "positive_count": POSITIVE_COUNT,
        "sample_count": total,
    }


def _gates(positive: dict[str, Any], negative_gate_passed: bool) -> dict[str, bool]:
    exact_count_met = (
        _integer(positive.get("exact_correct_matched_count"), "exact matched count")
        >= MINIMUM_EXACT_CORRECT_MATCHED
    )
    precision_met = (
        _number(positive.get("exact_matched_precision"), "exact matched precision")
        >= MINIMUM_EXACT_MATCHED_PRECISION
    )
    false_no_match_met = (
        _number(positive.get("false_no_match_rate"), "false no-match rate")
        <= MAXIMUM_FALSE_NO_MATCH_RATE
    )
    return {
        "aggregate_balanced_gate_passed": (
            exact_count_met and precision_met and false_no_match_met and negative_gate_passed
        ),
        "maximum_positive_false_no_match_rate_met": false_no_match_met,
        "minimum_exact_correct_matched_met": exact_count_met,
        "minimum_exact_matched_precision_met": precision_met,
        "negative_aggregate_gate_reused_and_passed": negative_gate_passed,
    }


def evaluate(root: Path) -> dict[str, Any]:
    if (root / OUTPUT_PATH).exists():
        raise FileExistsError(
            "PBHE-G1 permits one positive run; validate existing results with --check"
        )
    bindings_before = _bindings(root)
    check_three_class(root, require_local_inputs=True)
    negative_payload = check_negative_result(root)
    negative_metrics = negative_payload.get("metrics")
    negative_gates = negative_payload.get("gates")
    if not isinstance(negative_metrics, dict) or not isinstance(negative_gates, dict):
        raise TypeError("frozen negative result is incomplete")
    negative_gate_passed = negative_gates.get("aggregate_gate_passed") is True

    dataset = load_image_search_dataset(root / DATASET)
    split = load_frozen_split(dataset, root / DATASET)
    if (
        split.assignment_sha256 != POSITIVE_SPLIT_SHA256
        or len(split.test_case_ids) != POSITIVE_COUNT
    ):
        raise ValueError("positive test split differs from PBHE-G1")
    test_ids = set(split.test_case_ids)
    cases = [case for case in dataset.records if case.id in test_ids]
    source_records = load_source_records(root / SOURCE)
    source_bindings = bind_dataset_to_source(dataset, source_records)
    target_by_case = {binding.case_id: binding.evaluation_uuid for binding in source_bindings}

    calibration = CalibrationArtifact.load(root / CALIBRATION_PATH)
    calibrator = LogisticCalibrator(calibration)
    policy = DecisionPolicy.load(root / POLICY_PATH)
    if policy.version != "image-search-development-neural-pointwise-v2" or policy.runtime_eligible:
        raise ValueError("Pointwise v2 policy is not frozen development-only")
    context = load_scoring_context(root)

    statuses: list[ResolutionStatus] = []
    reasons: list[str] = []
    confidences: list[float] = []
    casting_correct: list[bool] = []
    exact_correct: list[bool] = []
    for case in cases:
        candidates = score_pointwise_query(context, case.query)
        confidence = calibrator.probability(candidates)
        status, reason = policy.decide(candidates, confidence)
        accepted = status is ResolutionStatus.matched and bool(candidates)
        statuses.append(status)
        reasons.append(reason)
        confidences.append(confidence)
        casting_correct.append(
            accepted
            and normalize_text(candidates[0].product.product.casting)
            == normalize_text(case.expected_casting)
        )
        exact_correct.append(
            accepted and candidates[0].product.canonical_uuid == target_by_case[case.id]
        )

    if _bindings(root) != bindings_before:
        raise ValueError("a frozen PBHE-G1 input changed during scoring")
    positive_metrics = summarize_positive(
        statuses, reasons, confidences, casting_correct, exact_correct
    )
    combined_metrics = combine_metrics(positive_metrics, negative_metrics)
    gates = _gates(positive_metrics, negative_gate_passed)
    return {
        "authority_note": AUTHORITY_NOTE,
        "bindings": bindings_before,
        "combined_metrics": combined_metrics,
        "gates": gates,
        "guardrails": {
            "answers_changed": False,
            "dataset_membership_changed": False,
            "features_changed": False,
            "model_changed": False,
            "negative_holdout_rerun": False,
            "row_level_output_persisted": False,
            "runtime_activation_authorized": False,
            "runtime_default_changed": False,
            "thresholds_changed": False,
        },
        "negative_metrics_reused": {
            "ambiguous_count": _integer(
                negative_metrics.get("ambiguous_count"), "negative ambiguous"
            ),
            "false_match_rate": _number(
                negative_metrics.get("false_match_rate"), "negative false match"
            ),
            "matched_count": _integer(negative_metrics.get("matched_count"), "negative matched"),
            "no_match_count": _integer(negative_metrics.get("no_match_count"), "negative no-match"),
            "no_match_recall": _number(negative_metrics.get("no_match_recall"), "negative recall"),
            "sample_count": _integer(negative_metrics.get("sample_count"), "negative sample count"),
        },
        "next_allowed_action": (
            "review_balanced_aggregate_before_any_runtime_proposal"
            if gates["aggregate_balanced_gate_passed"]
            else "record_policy_gate_shortfall_without_retuning_on_either_holdout"
        ),
        "positive_metrics": positive_metrics,
        "protocol": {
            "authorized_positive_run_count": 1,
            "candidate_limit": 25,
            "completed_positive_run_count": 1,
            "maximum_positive_false_no_match_rate": MAXIMUM_FALSE_NO_MATCH_RATE,
            "minimum_exact_correct_matched": MINIMUM_EXACT_CORRECT_MATCHED,
            "minimum_exact_matched_precision": MINIMUM_EXACT_MATCHED_PRECISION,
            "negative_result_reused_without_rescoring": True,
            "output_blind": True,
            "positive_prior_policy_evaluation": False,
            "positive_prior_ranking_evaluation": True,
            "positive_sample_count": POSITIVE_COUNT,
        },
        "schema_version": SCHEMA_VERSION,
        "status": "balanced_holdout_evaluated_not_runtime_authorized",
    }


def check(root: Path) -> dict[str, Any]:
    payload = _load_object(root / OUTPUT_PATH)
    if _contains_row_level_key(payload):
        raise ValueError("balanced evaluation result contains row-level data")
    _require_keys(
        payload,
        {
            "authority_note",
            "bindings",
            "combined_metrics",
            "gates",
            "guardrails",
            "negative_metrics_reused",
            "next_allowed_action",
            "positive_metrics",
            "protocol",
            "schema_version",
            "status",
        },
        "balanced evaluation result",
    )
    if (
        payload.get("schema_version") != SCHEMA_VERSION
        or payload.get("status") != "balanced_holdout_evaluated_not_runtime_authorized"
        or payload.get("authority_note") != AUTHORITY_NOTE
    ):
        raise ValueError("balanced evaluation identity changed")
    bindings = payload.get("bindings")
    positive = payload.get("positive_metrics")
    negative = payload.get("negative_metrics_reused")
    combined = payload.get("combined_metrics")
    gates = payload.get("gates")
    protocol = payload.get("protocol")
    guardrails = payload.get("guardrails")
    if not all(
        isinstance(item, dict)
        for item in (bindings, positive, negative, combined, gates, protocol, guardrails)
    ):
        raise TypeError("balanced evaluation sections must be objects")
    assert isinstance(bindings, dict)
    assert isinstance(positive, dict)
    assert isinstance(negative, dict)
    assert isinstance(combined, dict)
    assert isinstance(gates, dict)
    assert isinstance(protocol, dict)
    assert isinstance(guardrails, dict)
    if bindings != _bindings(root):
        raise ValueError("balanced evaluation bindings changed")
    checked_negative = check_negative_result(root)
    if negative != {
        key: checked_negative["metrics"][key]
        for key in (
            "ambiguous_count",
            "false_match_rate",
            "matched_count",
            "no_match_count",
            "no_match_recall",
            "sample_count",
        )
    }:
        raise ValueError("reused negative aggregate differs from the frozen result")
    status_counts = (
        _integer(positive.get("matched_count"), "positive matched"),
        _integer(positive.get("ambiguous_count"), "positive ambiguous"),
        _integer(positive.get("false_no_match_count"), "positive no-match"),
    )
    if (
        sum(status_counts) != POSITIVE_COUNT
        or _integer(positive.get("sample_count"), "positive sample count") != POSITIVE_COUNT
    ):
        raise ValueError("positive status counts are inconsistent")
    exact_count = _integer(positive.get("exact_correct_matched_count"), "exact correct matched")
    casting_count = _integer(
        positive.get("casting_correct_matched_count"), "casting correct matched"
    )
    matched_count = status_counts[0]
    if not 0 <= exact_count <= casting_count <= matched_count:
        raise ValueError("positive identity counts are inconsistent")
    expected_rates = {
        "ambiguous_rate": status_counts[1] / POSITIVE_COUNT,
        "casting_match_recall": casting_count / POSITIVE_COUNT,
        "casting_matched_precision": casting_count / matched_count if matched_count else 0.0,
        "exact_match_recall": exact_count / POSITIVE_COUNT,
        "exact_matched_precision": exact_count / matched_count if matched_count else 0.0,
        "false_no_match_rate": status_counts[2] / POSITIVE_COUNT,
    }
    if any(
        not math.isclose(_number(positive.get(key), key), value, abs_tol=1e-15)
        for key, value in expected_rates.items()
    ):
        raise ValueError("positive rates are inconsistent")
    reasons = positive.get("decision_reason_counts")
    confidence = positive.get("confidence_summary")
    if (
        not isinstance(reasons, dict)
        or any(_integer(value, "reason count") < 0 for value in reasons.values())
        or sum(reasons.values()) != POSITIVE_COUNT
        or not isinstance(confidence, dict)
        or set(confidence) != {"minimum", "maximum", "mean"}
    ):
        raise ValueError("positive aggregate summaries are invalid")
    minimum = _number(confidence.get("minimum"), "minimum confidence")
    maximum = _number(confidence.get("maximum"), "maximum confidence")
    mean = _number(confidence.get("mean"), "mean confidence")
    if not 0 <= minimum <= mean <= maximum <= 1:
        raise ValueError("positive confidence summary is invalid")
    expected_combined = combine_metrics(positive, negative)
    if combined != expected_combined:
        raise ValueError("balanced aggregate metrics are inconsistent")
    negative_gate_passed = checked_negative["gates"]["aggregate_gate_passed"] is True
    expected_gates = _gates(positive, negative_gate_passed)
    if gates != expected_gates:
        raise ValueError("balanced gates are inconsistent")
    if protocol != {
        "authorized_positive_run_count": 1,
        "candidate_limit": 25,
        "completed_positive_run_count": 1,
        "maximum_positive_false_no_match_rate": MAXIMUM_FALSE_NO_MATCH_RATE,
        "minimum_exact_correct_matched": MINIMUM_EXACT_CORRECT_MATCHED,
        "minimum_exact_matched_precision": MINIMUM_EXACT_MATCHED_PRECISION,
        "negative_result_reused_without_rescoring": True,
        "output_blind": True,
        "positive_prior_policy_evaluation": False,
        "positive_prior_ranking_evaluation": True,
        "positive_sample_count": POSITIVE_COUNT,
    }:
        raise ValueError("balanced evaluation protocol changed")
    if guardrails != {
        "answers_changed": False,
        "dataset_membership_changed": False,
        "features_changed": False,
        "model_changed": False,
        "negative_holdout_rerun": False,
        "row_level_output_persisted": False,
        "runtime_activation_authorized": False,
        "runtime_default_changed": False,
        "thresholds_changed": False,
    }:
        raise ValueError("balanced evaluation guardrails changed")
    expected_next = (
        "review_balanced_aggregate_before_any_runtime_proposal"
        if expected_gates["aggregate_balanced_gate_passed"]
        else "record_policy_gate_shortfall_without_retuning_on_either_holdout"
    )
    if payload.get("next_allowed_action") != expected_next:
        raise ValueError("balanced evaluation next action changed")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run or validate the one-time Pointwise balanced holdout evaluation"
    )
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--acknowledge-positive-policy-layer-only", action="store_true")
    parser.add_argument("--acknowledge-negative-not-rerun", action="store_true")
    parser.add_argument("--acknowledge-no-retuning", action="store_true")
    parser.add_argument("--acknowledge-no-runtime-activation", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.run:
        if not (
            args.acknowledge_positive_policy_layer_only
            and args.acknowledge_negative_not_rerun
            and args.acknowledge_no_retuning
            and args.acknowledge_no_runtime_activation
        ):
            parser.error("--run requires all four PBHE-G1 acknowledgements")
        print(json.dumps(evaluate(root), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return
    if args.check:
        check(root)
        print("valid")
        return
    parser.error("choose --run or --check")


if __name__ == "__main__":
    main()
