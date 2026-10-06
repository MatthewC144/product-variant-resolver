"""Output-blind evaluation of the frozen Pointwise v2 policy on the no-match holdout."""

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
from .image_search_pointwise_calibration import (
    load_pointwise_scoring_context as load_scoring_context,
)
from .image_search_pointwise_calibration import score_pointwise_query
from .image_search_ranking_development import POINTWISE_CONFIG, POINTWISE_MODEL
from .pointwise_three_class_calibration import (
    CALIBRATION_PATH,
    POLICY_PATH,
    SELECTION_PATH,
)
from .pointwise_three_class_calibration import check as check_three_class
from .policy import DecisionPolicy
from .schemas import ResolutionStatus

SCHEMA_VERSION = "pvr-image-search-pointwise-no-match-holdout-evaluation-v1"
HOLDOUT_PATH = Path("data/evaluation/image-search-pointwise-no-match-holdout-v1/dataset.json")
OUTPUT_PATH = Path(
    "data/evaluation/image-search-pointwise-no-match-holdout-evaluation-v1/results.json"
)
CATALOG_PATH = Path("data/external/hot-wheels-wiki/local-export-2023-2026/normalized.json")

HOLDOUT_SHA256 = "b46367efb54c9ab2a74c23d0824d1da5f939ecdf74a63c612da37c0688c50a7e"
CATALOG_SHA256 = "b4e0747450a5447c2bf66b0838c91f3f723a19ac97c90c7ac3636cf3a9a709d4"
CALIBRATION_SHA256 = "22990e52d2a64a051ac4da272999e628dc7c41f300bc7e897f431da2fbd7406d"
POLICY_SHA256 = "68969b386a05002fca8f48826f37f5a00c24128672fbfbf3befb748b881ab418"
SELECTION_SHA256 = "e67c8789889e09ca54871bbb93e0e979309286bae7970a321dcf97db4facebfe"
POINTWISE_CONFIG_SHA256 = "3a88163cc7abc84468024f5e6410e0ca489a80a710b67b4c2474c4b4f7d7fad6"
POINTWISE_MANIFEST_SHA256 = "32f889bb415ef5a56760a299da0635e8e1704d46fe0b11ded06c563de896feb8"
OWNER_AUTHORIZATION_SHA256 = "487f623544d39eac0574dab35ea03fda052f114f6c16b75b4f7db8e4dbe02eba"

SAMPLE_COUNT = 20
MINIMUM_NO_MATCH_COUNT = 5
MAXIMUM_MATCHED_COUNT = 2
AUTHORITY_NOTE = (
    "Expected no-match truth is relative only to the frozen third-party catalog snapshot; "
    "it is not manufacturer-certified or global product truth."
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


def _contains_row_level_key(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            (isinstance(key, str) and key in _ROW_LEVEL_KEYS) or _contains_row_level_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_row_level_key(item) for item in value)
    return False


def _bindings(root: Path) -> dict[str, str]:
    bindings = {
        "calibration_path": str(CALIBRATION_PATH),
        "calibration_sha256": _sha256(root / CALIBRATION_PATH),
        "catalog_path": str(CATALOG_PATH),
        "catalog_sha256": _sha256(root / CATALOG_PATH),
        "holdout_path": str(HOLDOUT_PATH),
        "holdout_sha256": _sha256(root / HOLDOUT_PATH),
        "owner_authorization_sha256": OWNER_AUTHORIZATION_SHA256,
        "pointwise_config_sha256": _sha256(root / POINTWISE_CONFIG),
        "pointwise_model_manifest_sha256": _sha256(root / POINTWISE_MODEL / "manifest.json"),
        "policy_path": str(POLICY_PATH),
        "policy_sha256": _sha256(root / POLICY_PATH),
        "selection_path": str(SELECTION_PATH),
        "selection_sha256": _sha256(root / SELECTION_PATH),
    }
    expected = {
        "calibration_sha256": CALIBRATION_SHA256,
        "catalog_sha256": CATALOG_SHA256,
        "holdout_sha256": HOLDOUT_SHA256,
        "pointwise_config_sha256": POINTWISE_CONFIG_SHA256,
        "pointwise_model_manifest_sha256": POINTWISE_MANIFEST_SHA256,
        "policy_sha256": POLICY_SHA256,
        "selection_sha256": SELECTION_SHA256,
    }
    if any(bindings[key] != value for key, value in expected.items()):
        raise ValueError("evaluation input differs from the frozen PNMH-G2 binding")
    return bindings


def summarize(
    statuses: list[ResolutionStatus],
    reasons: list[str],
    confidences: list[float],
) -> dict[str, Any]:
    if not (
        len(statuses) == len(reasons) == len(confidences) == SAMPLE_COUNT
        and all(math.isfinite(value) and 0 <= value <= 1 for value in confidences)
    ):
        raise ValueError("holdout outcomes must contain 20 aligned finite rows")
    status_counts = Counter(status.value for status in statuses)
    reason_counts = Counter(reasons)
    no_match_count = status_counts[ResolutionStatus.no_match.value]
    ambiguous_count = status_counts[ResolutionStatus.ambiguous.value]
    matched_count = status_counts[ResolutionStatus.matched.value]
    decisive_count = no_match_count + matched_count
    return {
        "ambiguous_count": ambiguous_count,
        "ambiguous_rate": ambiguous_count / SAMPLE_COUNT,
        "confidence_summary": {
            "maximum": max(confidences),
            "mean": fmean(confidences),
            "minimum": min(confidences),
        },
        "decision_reason_counts": dict(sorted(reason_counts.items())),
        "decisive_count": decisive_count,
        "false_match_rate": matched_count / SAMPLE_COUNT,
        "matched_count": matched_count,
        "no_match_count": no_match_count,
        "no_match_recall": no_match_count / SAMPLE_COUNT,
        "sample_count": SAMPLE_COUNT,
    }


def evaluate(root: Path) -> dict[str, Any]:
    if (root / OUTPUT_PATH).exists():
        raise FileExistsError("PNMH-G2 permits one run; validate the existing result with --check")
    bindings_before = _bindings(root)
    check_three_class(root, require_local_inputs=True)
    holdout = _load_object(root / HOLDOUT_PATH)
    records = holdout.get("records")
    if (
        holdout.get("status") != "owner_reviewed_frozen_not_scored"
        or not isinstance(records, list)
        or len(records) != SAMPLE_COUNT
    ):
        raise ValueError("holdout differs from the owner-reviewed frozen dataset")

    calibration = CalibrationArtifact.load(root / CALIBRATION_PATH)
    calibrator = LogisticCalibrator(calibration)
    policy = DecisionPolicy.load(root / POLICY_PATH)
    if policy.version != "image-search-development-neural-pointwise-v2" or policy.runtime_eligible:
        raise ValueError("Pointwise v2 policy is not frozen development-only")
    context = load_scoring_context(root)

    statuses: list[ResolutionStatus] = []
    reasons: list[str] = []
    confidences: list[float] = []
    for record in records:
        if not isinstance(record, dict):
            raise TypeError("holdout record must be an object")
        query = record.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("holdout query must be non-empty")
        candidates = score_pointwise_query(context, query)
        confidence = calibrator.probability(candidates)
        status, reason = policy.decide(candidates, confidence)
        statuses.append(status)
        reasons.append(reason)
        confidences.append(confidence)

    if _bindings(root) != bindings_before:
        raise ValueError("a frozen evaluation input changed during scoring")
    metrics = summarize(statuses, reasons, confidences)
    minimum_met = metrics["no_match_count"] >= MINIMUM_NO_MATCH_COUNT
    maximum_met = metrics["matched_count"] <= MAXIMUM_MATCHED_COUNT
    aggregate_passed = minimum_met and maximum_met
    return {
        "authority_note": AUTHORITY_NOTE,
        "bindings": bindings_before,
        "gates": {
            "aggregate_gate_passed": aggregate_passed,
            "maximum_matched_count_met": maximum_met,
            "minimum_no_match_count_met": minimum_met,
        },
        "guardrails": {
            "answers_changed": False,
            "dataset_membership_changed": False,
            "features_changed": False,
            "model_changed": False,
            "row_level_output_persisted": False,
            "runtime_activation_authorized": False,
            "runtime_default_changed": False,
            "thresholds_changed": False,
        },
        "metrics": metrics,
        "next_allowed_action": (
            "review_aggregate_holdout_result_before_any_runtime_decision"
            if aggregate_passed
            else "diagnose_aggregate_shortfall_without_retuning_on_the_holdout"
        ),
        "protocol": {
            "authorized_run_count": 1,
            "candidate_limit": 25,
            "completed_run_count": 1,
            "maximum_matched_count": MAXIMUM_MATCHED_COUNT,
            "minimum_no_match_count": MINIMUM_NO_MATCH_COUNT,
            "output_blind": True,
            "sample_count": SAMPLE_COUNT,
            "truth": "catalog_relative_no_match",
        },
        "schema_version": SCHEMA_VERSION,
        "status": "holdout_evaluated_not_runtime_authorized",
    }


def check(root: Path) -> dict[str, Any]:
    payload = _load_object(root / OUTPUT_PATH)
    if _contains_row_level_key(payload):
        raise ValueError("holdout evaluation result contains row-level data")
    _require_keys(
        payload,
        {
            "authority_note",
            "bindings",
            "gates",
            "guardrails",
            "metrics",
            "next_allowed_action",
            "protocol",
            "schema_version",
            "status",
        },
        "holdout evaluation result",
    )
    if (
        payload.get("schema_version") != SCHEMA_VERSION
        or payload.get("status") != "holdout_evaluated_not_runtime_authorized"
        or payload.get("authority_note") != AUTHORITY_NOTE
    ):
        raise ValueError("holdout evaluation identity changed")
    bindings = payload.get("bindings")
    protocol = payload.get("protocol")
    metrics = payload.get("metrics")
    gates = payload.get("gates")
    guardrails = payload.get("guardrails")
    if not all(isinstance(item, dict) for item in (bindings, protocol, metrics, gates, guardrails)):
        raise TypeError("holdout evaluation sections must be objects")
    assert isinstance(bindings, dict)
    assert isinstance(protocol, dict)
    assert isinstance(metrics, dict)
    assert isinstance(gates, dict)
    assert isinstance(guardrails, dict)
    if bindings != _bindings(root):
        raise ValueError("holdout evaluation bindings changed")
    if protocol != {
        "authorized_run_count": 1,
        "candidate_limit": 25,
        "completed_run_count": 1,
        "maximum_matched_count": MAXIMUM_MATCHED_COUNT,
        "minimum_no_match_count": MINIMUM_NO_MATCH_COUNT,
        "output_blind": True,
        "sample_count": SAMPLE_COUNT,
        "truth": "catalog_relative_no_match",
    }:
        raise ValueError("holdout evaluation protocol changed")
    _require_keys(
        metrics,
        {
            "ambiguous_count",
            "ambiguous_rate",
            "confidence_summary",
            "decision_reason_counts",
            "decisive_count",
            "false_match_rate",
            "matched_count",
            "no_match_count",
            "no_match_recall",
            "sample_count",
        },
        "holdout aggregate metrics",
    )
    sample_count = _integer(metrics.get("sample_count"), "sample_count")
    no_match_count = _integer(metrics.get("no_match_count"), "no_match_count")
    ambiguous_count = _integer(metrics.get("ambiguous_count"), "ambiguous_count")
    matched_count = _integer(metrics.get("matched_count"), "matched_count")
    decisive_count = _integer(metrics.get("decisive_count"), "decisive_count")
    if (
        sample_count != SAMPLE_COUNT
        or no_match_count + ambiguous_count + matched_count != SAMPLE_COUNT
        or decisive_count != no_match_count + matched_count
        or not math.isclose(
            _number(metrics.get("no_match_recall"), "no_match_recall"),
            no_match_count / SAMPLE_COUNT,
            abs_tol=1e-15,
        )
        or not math.isclose(
            _number(metrics.get("ambiguous_rate"), "ambiguous_rate"),
            ambiguous_count / SAMPLE_COUNT,
            abs_tol=1e-15,
        )
        or not math.isclose(
            _number(metrics.get("false_match_rate"), "false_match_rate"),
            matched_count / SAMPLE_COUNT,
            abs_tol=1e-15,
        )
    ):
        raise ValueError("holdout aggregate metrics are inconsistent")
    reason_counts = metrics.get("decision_reason_counts")
    confidence = metrics.get("confidence_summary")
    if (
        not isinstance(reason_counts, dict)
        or any(not isinstance(key, str) for key in reason_counts)
        or any(_integer(value, "reason count") < 0 for value in reason_counts.values())
        or sum(reason_counts.values()) != SAMPLE_COUNT
        or not isinstance(confidence, dict)
        or set(confidence) != {"minimum", "maximum", "mean"}
    ):
        raise ValueError("holdout aggregate summaries are invalid")
    minimum = _number(confidence.get("minimum"), "minimum confidence")
    maximum = _number(confidence.get("maximum"), "maximum confidence")
    mean = _number(confidence.get("mean"), "mean confidence")
    if not 0 <= minimum <= mean <= maximum <= 1:
        raise ValueError("holdout confidence summary is invalid")
    expected_gates = {
        "aggregate_gate_passed": no_match_count >= MINIMUM_NO_MATCH_COUNT
        and matched_count <= MAXIMUM_MATCHED_COUNT,
        "maximum_matched_count_met": matched_count <= MAXIMUM_MATCHED_COUNT,
        "minimum_no_match_count_met": no_match_count >= MINIMUM_NO_MATCH_COUNT,
    }
    if gates != expected_gates:
        raise ValueError("holdout aggregate gate result is inconsistent")
    expected_guardrails = {
        "answers_changed": False,
        "dataset_membership_changed": False,
        "features_changed": False,
        "model_changed": False,
        "row_level_output_persisted": False,
        "runtime_activation_authorized": False,
        "runtime_default_changed": False,
        "thresholds_changed": False,
    }
    if guardrails != expected_guardrails:
        raise ValueError("holdout evaluation guardrails changed")
    expected_next = (
        "review_aggregate_holdout_result_before_any_runtime_decision"
        if expected_gates["aggregate_gate_passed"]
        else "diagnose_aggregate_shortfall_without_retuning_on_the_holdout"
    )
    if payload.get("next_allowed_action") != expected_next:
        raise ValueError("holdout evaluation next action changed")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run or validate the one-time frozen Pointwise no-match holdout evaluation"
    )
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--acknowledge-output-blind", action="store_true")
    parser.add_argument("--acknowledge-no-retuning", action="store_true")
    parser.add_argument("--acknowledge-no-runtime-activation", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.run:
        if not (
            args.acknowledge_output_blind
            and args.acknowledge_no_retuning
            and args.acknowledge_no_runtime_activation
        ):
            parser.error("--run requires all three PNMH-G2 acknowledgements")
        print(json.dumps(evaluate(root), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return
    if args.check:
        check(root)
        print("valid")
        return
    parser.error("choose --run or --check")


if __name__ == "__main__":
    main()
