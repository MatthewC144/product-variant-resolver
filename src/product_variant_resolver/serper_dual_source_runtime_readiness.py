"""Fail-closed runtime-readiness audit for the frozen dual-source ranking evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .pointwise_balanced_holdout_evaluation import check as check_balanced_holdout
from .pointwise_three_class_calibration import (
    CALIBRATION_PATH as LEGACY_CALIBRATION_PATH,
)
from .pointwise_three_class_calibration import POLICY_PATH as LEGACY_POLICY_PATH
from .pointwise_three_class_calibration import check as check_legacy_policy
from .serper_dual_source_evaluation import (
    DATASET,
    FROZEN_DATASET_SHA256,
    FROZEN_DEVELOPMENT_TARGET_COUNT,
    FROZEN_RAW_POINTWISE_DEVELOPMENT_SHA256,
    FROZEN_RAW_POINTWISE_FINAL_TEST_SHA256,
    FROZEN_RECORD_COUNT,
    FROZEN_SPLIT_SHA256,
    FROZEN_TARGET_COUNT,
    FROZEN_TEST_TARGET_COUNT,
    RAW_POINTWISE_DEVELOPMENT,
    RAW_POINTWISE_FINAL_TEST,
    load_frozen_grouped_split,
    load_frozen_raw_pointwise_development,
    load_frozen_raw_pointwise_final_test,
    load_serper_dual_source_dataset,
)

VERSION = "serper-dual-source-runtime-readiness-v1"
SCHEMA_VERSION = "pvr-serper-dual-source-runtime-readiness-v1"
OUTPUT = Path("data/evaluation/serper-dual-source-runtime-readiness-v1/readiness.json")
BALANCED_HOLDOUT = Path("data/evaluation/image-search-pointwise-balanced-holdout-v1/results.json")
LEGACY_CALIBRATION_SHA256 = (
    "22990e52d2a64a051ac4da272999e628dc7c41f300bc7e897f431da2fbd7406d"
)
LEGACY_POLICY_SHA256 = "68969b386a05002fca8f48826f37f5a00c24128672fbfbf3befb748b881ab418"
BALANCED_HOLDOUT_SHA256 = (
    "8764f2642208b7cfddf63402fb18f487514af1b38a2d183afbc4da41b72a9566"
)

NEW_NO_MATCH_DEVELOPMENT_TARGETS = 40
FRESH_POSITIVE_HOLDOUT_TARGETS = 20
FRESH_NO_MATCH_HOLDOUT_TARGETS = 20
SOURCE_OBSERVATIONS_PER_TARGET = 2


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: could not read strict JSON") from error
    if not isinstance(payload, dict):
        raise TypeError(f"{path}: JSON root must be an object")
    return payload


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _contains_row_level_key(value: object) -> bool:
    forbidden = {
        "candidate",
        "candidates",
        "case_id",
        "case_ids",
        "expected_casting",
        "expected_full_identity",
        "identity",
        "identities",
        "label",
        "labels",
        "prediction",
        "predictions",
        "query",
        "queries",
        "query_raw",
        "query_cleaned",
        "record",
        "records",
        "target_id",
        "target_ids",
    }
    if isinstance(value, dict):
        return any(key in forbidden or _contains_row_level_key(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_row_level_key(item) for item in value)
    return False


def _validate_frozen_inputs(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    dataset_path = root / DATASET
    development_path = root / RAW_POINTWISE_DEVELOPMENT
    final_path = root / RAW_POINTWISE_FINAL_TEST
    if _sha256(dataset_path) != FROZEN_DATASET_SHA256:
        raise ValueError("dual-source dataset differs from the frozen contract")
    if _sha256(development_path) != FROZEN_RAW_POINTWISE_DEVELOPMENT_SHA256:
        raise ValueError("dual-source development result differs from the frozen contract")
    if _sha256(final_path) != FROZEN_RAW_POINTWISE_FINAL_TEST_SHA256:
        raise ValueError("dual-source final result differs from the frozen contract")

    dataset = load_serper_dual_source_dataset(dataset_path)
    split = load_frozen_grouped_split(dataset, dataset_path)
    development = load_frozen_raw_pointwise_development(development_path)
    final = load_frozen_raw_pointwise_final_test(final_path)
    if (
        dataset.target_count != FROZEN_TARGET_COUNT
        or dataset.record_count != FROZEN_RECORD_COUNT
        or len(split.development_target_ids) != FROZEN_DEVELOPMENT_TARGET_COUNT
        or len(split.test_target_ids) != FROZEN_TEST_TARGET_COUNT
        or split.assignment_sha256 != FROZEN_SPLIT_SHA256
    ):
        raise ValueError("dual-source dataset or split counts changed")
    return development, final


def _validate_legacy_policy(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if _sha256(root / LEGACY_CALIBRATION_PATH) != LEGACY_CALIBRATION_SHA256:
        raise ValueError("legacy calibration differs from the frozen artifact")
    if _sha256(root / LEGACY_POLICY_PATH) != LEGACY_POLICY_SHA256:
        raise ValueError("legacy policy differs from the frozen artifact")
    if _sha256(root / BALANCED_HOLDOUT) != BALANCED_HOLDOUT_SHA256:
        raise ValueError("legacy balanced holdout differs from the frozen result")
    policy_selection = check_legacy_policy(root)
    balanced = check_balanced_holdout(root)
    policy = _load_object(root / LEGACY_POLICY_PATH)
    if policy.get("runtime_eligible") is not False:
        raise ValueError("legacy policy unexpectedly became runtime eligible")
    return policy_selection, balanced


def build_readiness(root: Path) -> dict[str, Any]:
    development, final = _validate_frozen_inputs(root)
    legacy_selection, balanced = _validate_legacy_policy(root)
    if development.get("decision", {}).get("selected_development_ranker") != "neural_pointwise":
        raise ValueError("dual-source development winner changed")
    if final.get("guardrails", {}).get("rerun_allowed") is not False:
        raise ValueError("dual-source final unexpectedly permits rerun")
    if legacy_selection.get("status") != "development_three_class_calibrated_not_runtime_authorized":
        raise ValueError("legacy policy status changed")
    if balanced.get("status") != "balanced_holdout_evaluated_not_runtime_authorized":
        raise ValueError("legacy balanced evaluation status changed")

    new_identity_count = (
        NEW_NO_MATCH_DEVELOPMENT_TARGETS
        + FRESH_POSITIVE_HOLDOUT_TARGETS
        + FRESH_NO_MATCH_HOLDOUT_TARGETS
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
        "status": "blocked_missing_source_matched_policy_data",
        "bindings": {
            "dual_source_dataset_sha256": FROZEN_DATASET_SHA256,
            "dual_source_split_sha256": FROZEN_SPLIT_SHA256,
            "dual_source_development_sha256": FROZEN_RAW_POINTWISE_DEVELOPMENT_SHA256,
            "dual_source_final_sha256": FROZEN_RAW_POINTWISE_FINAL_TEST_SHA256,
            "legacy_calibration_sha256": LEGACY_CALIBRATION_SHA256,
            "legacy_policy_sha256": LEGACY_POLICY_SHA256,
            "legacy_balanced_holdout_sha256": BALANCED_HOLDOUT_SHA256,
        },
        "available_evidence": {
            "dual_source_positive_development_target_count": FROZEN_DEVELOPMENT_TARGET_COUNT,
            "dual_source_positive_development_observation_count": (
                FROZEN_DEVELOPMENT_TARGET_COUNT * SOURCE_OBSERVATIONS_PER_TARGET
            ),
            "development_query_representation": "raw",
            "selected_ranker": "neural_pointwise",
            "ranking_final_target_count": FROZEN_TEST_TARGET_COUNT,
            "ranking_final_observation_count": (
                FROZEN_TEST_TARGET_COUNT * SOURCE_OBSERVATIONS_PER_TARGET
            ),
            "ranking_final_eligible_for_new_policy_work": False,
        },
        "legacy_policy_evidence": {
            "distribution": "older_image_search_positive_plus_human_no_match",
            "runtime_eligible": False,
            "dual_source_transfer_validated": False,
            "balanced_sample_count": balanced["combined_metrics"]["sample_count"],
            "balanced_abstention_rate": balanced["combined_metrics"]["ambiguous_rate"],
        },
        "missing_evidence": {
            "dual_source_no_match_development_target_count": 0,
            "fresh_dual_source_positive_holdout_target_count": 0,
            "fresh_dual_source_no_match_holdout_target_count": 0,
            "source_matched_policy_calibration": False,
            "fresh_policy_evaluation": False,
            "neural_runtime_load_and_latency_validation": False,
        },
        "blockers": [
            "no_dual_source_catalog_relative_no_match_development_set",
            "no_fresh_dual_source_positive_and_no_match_policy_holdout",
            "legacy_policy_distribution_does_not_match_image_and_shopping_pair",
            "legacy_policy_is_runtime_ineligible",
            "no_neural_runtime_operational_validation_for_a_qualified_policy",
        ],
        "next_dataset_contract": {
            "reuse_existing_positive_development_target_count": FROZEN_DEVELOPMENT_TARGET_COUNT,
            "new_no_match_development_target_count": NEW_NO_MATCH_DEVELOPMENT_TARGETS,
            "fresh_positive_holdout_target_count": FRESH_POSITIVE_HOLDOUT_TARGETS,
            "fresh_no_match_holdout_target_count": FRESH_NO_MATCH_HOLDOUT_TARGETS,
            "new_identity_count": new_identity_count,
            "new_source_observation_count": new_identity_count * SOURCE_OBSERVATIONS_PER_TARGET,
            "source_types": ["image_search", "shopping"],
            "query_representation": "raw",
            "group_by_identity_before_split": True,
            "catalog_relative_truth_required": True,
            "freeze_holdout_before_resolver_or_policy_access": True,
            "existing_50_target_ranking_final_may_be_reused": False,
            "temporary_collection_code_and_images_must_remain_untracked": True,
            "only_final_minimal_dataset_may_be_committed": True,
        },
        "guardrails": {
            "dataset_collection_executed": False,
            "network_or_api_call_executed": False,
            "secret_read_or_persisted": False,
            "resolver_loaded": False,
            "neural_model_loaded": False,
            "development_observations_scored": 0,
            "final_observations_scored": 0,
            "calibration_fit": False,
            "thresholds_selected_or_changed": False,
            "policy_evaluated": False,
            "runtime_default_changed": False,
            "runtime_activation_authorized": False,
        },
        "conclusion": (
            "Dual-source Pointwise ranking is supported, but source-matched decision-policy "
            "evidence is incomplete. Runtime activation and recalibration remain blocked."
        ),
        "next_allowed_action": "collect_and_freeze_the_minimal_dual_source_policy_dataset",
    }


def check(root: Path) -> dict[str, Any]:
    payload = _load_object(root / OUTPUT)
    if _contains_row_level_key(payload):
        raise ValueError("runtime readiness contains row-level data")
    expected = build_readiness(root)
    if _canonical_bytes(payload) != _canonical_bytes(expected):
        raise ValueError("runtime readiness differs from the reproducible aggregate audit")
    return payload


def materialize(root: Path) -> dict[str, Any]:
    path = root / OUTPUT
    if path.exists():
        raise FileExistsError("runtime readiness artifact already exists")
    payload = build_readiness(root)
    if _contains_row_level_key(payload):
        raise ValueError("runtime readiness contains row-level data")
    path.parent.mkdir(parents=True, exist_ok=False)
    path.write_bytes(_canonical_bytes(payload))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit dual-source Pointwise runtime readiness")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--acknowledge-readiness-only", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.run:
        if not args.acknowledge_readiness_only:
            parser.error("--run requires --acknowledge-readiness-only")
        print(json.dumps(materialize(root), ensure_ascii=False, indent=2, sort_keys=True))
        return
    if args.check:
        check(root)
        print("valid")
        return
    parser.error("choose --run or --check")


if __name__ == "__main__":
    main()
