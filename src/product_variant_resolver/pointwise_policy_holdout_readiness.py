"""Audit whether an untouched no-match holdout exists for the frozen Pointwise v2 policy."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from .pointwise_three_class_calibration import (
    CALIBRATION_PATH,
    POLICY_PATH,
    SELECTION_PATH,
)
from .pointwise_three_class_calibration import (
    check as check_three_class,
)

VERSION = "image-search-pointwise-policy-holdout-readiness-v1"
SCHEMA_VERSION = "pvr-image-search-pointwise-policy-holdout-readiness-v1"
OUTPUT = Path("data/evaluation/image-search-pointwise-policy-holdout-readiness-v1/readiness.json")
HUMAN_DATASET = Path("data/human_labeled_names.json")
HUMAN_DATASET_SHA256 = "68b5dfdb8d0fa4972328d172cc5a56d78ac8bf00bc740083b2bfc07eb2a91188"
RHB_PROGRESS = Path(
    "data/evaluation/representative-hard-benchmark-v1/rhb-t6-label-review-progress-v1.json"
)
RHB_PROGRESS_SHA256 = "f972698fd0c425cc0bf19f690440f5c043d8e7abba49dc30c14249c8cd703676"
MINIMUM_UNTOUCHED_NO_MATCH_COUNT = 20

SOURCE_FILES = {
    "human_labeling_queue": Path("real-noisy-scan-labeling-queue/labeling-queue.csv"),
    "resolver_comparison_rows": Path("real-noisy-scan-comparison/review-buckets.csv"),
    "candidate_evidence_rows": Path(
        "real-noisy-scan-evidence-labeling-queue/evidence-labeling-queue.csv"
    ),
}

EXPECTED_SOURCE_INVENTORY: list[dict[str, Any]] = [
    {
        "source_id": "human_labeling_queue",
        "sha256": "52e135287c5c4b3beefb3fb32c6aa4be84bc29713dca13afb63365b250217ec0",
        "row_count": 105,
        "unique_case_count": 105,
        "tracked_overlap_count": 101,
        "untracked_case_count": 4,
        "untracked_human_answer_count": 0,
        "eligible_untouched_labeled_no_match_count": 0,
        "classification": "same_source_with_four_unlabeled_exclusions",
    },
    {
        "source_id": "resolver_comparison_rows",
        "sha256": "34619fe4cebaeeb390798b00d033d48881bc008d9ddba6c39b7b79a107200a91",
        "row_count": 230,
        "unique_case_count": 91,
        "tracked_overlap_count": 91,
        "untracked_case_count": 0,
        "untracked_human_answer_count": 0,
        "eligible_untouched_labeled_no_match_count": 0,
        "classification": "derived_rows_from_tracked_human_source",
    },
    {
        "source_id": "candidate_evidence_rows",
        "sha256": "8ad0c0f7d6845e6207914ea8918c7487b2e88a3a91edc6f25ae1976a7213fe73",
        "row_count": 1640,
        "unique_case_count": 79,
        "tracked_overlap_count": 79,
        "untracked_case_count": 0,
        "untracked_human_answer_count": 0,
        "eligible_untouched_labeled_no_match_count": 0,
        "classification": "candidate_evidence_for_tracked_human_source",
    },
]


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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _load_tracked_case_ids(root: Path) -> set[str]:
    path = root / HUMAN_DATASET
    if _sha256(path) != HUMAN_DATASET_SHA256:
        raise ValueError("tracked human dataset differs from the frozen source")
    payload = _load_object(path)
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 101:
        raise ValueError("tracked human dataset must contain 101 records")
    result: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("case_id"), str):
            raise TypeError("tracked human record must contain a string case_id")
        case_id = record["case_id"].strip()
        if not case_id or case_id in result:
            raise ValueError("tracked human case IDs must be non-empty and unique")
        result.add(case_id)
    return result


def _read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
            fields = list(reader.fieldnames or [])
    except (OSError, UnicodeError, csv.Error) as error:
        raise ValueError(f"{path}: could not read CSV") from error
    if "case_id" not in fields:
        raise ValueError(f"{path}: case_id column is required")
    return rows, fields


def audit_sources(root: Path, source_root: Path) -> list[dict[str, Any]]:
    """Return aggregate-only overlap evidence; never return case IDs or row values."""
    tracked_ids = _load_tracked_case_ids(root)
    inventory: list[dict[str, Any]] = []
    for source_id, relative_path in SOURCE_FILES.items():
        path = source_root / relative_path
        rows, fields = _read_csv(path)
        ids = {row["case_id"].strip() for row in rows if row.get("case_id", "").strip()}
        untracked = [row for row in rows if row.get("case_id", "").strip() not in tracked_ids]
        answer_fields = {
            "human_expected_candidate",
            "human_expected_brand",
            "human_expected_casting",
            "human_expected_series",
            "human_expected_variant",
            "human_expected_pricing_keyword",
        }
        available_answer_fields = answer_fields.intersection(fields)
        untracked_answer_count = sum(
            any((row.get(field) or "").strip() for field in available_answer_fields)
            for row in untracked
        )
        if source_id == "human_labeling_queue":
            classification = "same_source_with_four_unlabeled_exclusions"
        elif source_id == "resolver_comparison_rows":
            classification = "derived_rows_from_tracked_human_source"
        else:
            classification = "candidate_evidence_for_tracked_human_source"
        inventory.append(
            {
                "source_id": source_id,
                "sha256": _sha256(path),
                "row_count": len(rows),
                "unique_case_count": len(ids),
                "tracked_overlap_count": len(ids.intersection(tracked_ids)),
                "untracked_case_count": len(ids.difference(tracked_ids)),
                "untracked_human_answer_count": untracked_answer_count,
                "eligible_untouched_labeled_no_match_count": 0,
                "classification": classification,
            }
        )
    if inventory != EXPECTED_SOURCE_INVENTORY:
        raise ValueError("external source inventory differs from the reviewed aggregate evidence")
    return inventory


def build_readiness(root: Path, source_inventory: list[dict[str, Any]]) -> dict[str, Any]:
    if source_inventory != EXPECTED_SOURCE_INVENTORY:
        raise ValueError("holdout readiness requires the frozen aggregate source inventory")
    v2 = check_three_class(root)
    if v2.get("status") != "development_three_class_calibrated_not_runtime_authorized":
        raise ValueError("Pointwise v2 is not the expected frozen development policy")
    rhb = _load_object(root / RHB_PROGRESS)
    if _sha256(root / RHB_PROGRESS) != RHB_PROGRESS_SHA256:
        raise ValueError("RHB review progress differs from the audited aggregate")
    if (
        rhb.get("approved_status_counts", {}).get("no_match") != 1
        or rhb.get("labels_materialized") is not False
        or rhb.get("split_authorized") is not False
        or rhb.get("scoring_authorized") is not False
        or rhb.get("resolver_evaluation_authorized") is not False
    ):
        raise ValueError("RHB review permission boundary changed")
    return {
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
        "status": "holdout_not_ready",
        "frozen_policy": {
            "calibration_sha256": _sha256(root / CALIBRATION_PATH),
            "policy_sha256": _sha256(root / POLICY_PATH),
            "selection_sha256": _sha256(root / SELECTION_PATH),
            "runtime_eligible": False,
            "retuning_allowed": False,
        },
        "source_inventory": source_inventory,
        "independence_audit": {
            "tracked_human_case_count": 101,
            "previously_consumed_no_match_development_count": 52,
            "eligible_untouched_labeled_no_match_count": 0,
            "minimum_required_count": MINIMUM_UNTOUCHED_NO_MATCH_COUNT,
            "shortfall_count": MINIMUM_UNTOUCHED_NO_MATCH_COUNT,
            "rhb_owner_approved_no_match_count": 1,
            "rhb_holdout_eligible_count": 0,
            "rhb_ineligibility_reason": "split_scoring_and_resolver_evaluation_not_authorized",
        },
        "blockers": [
            "all_labeled_real_no_match_candidates_were_used_for_development_fit_or_selection",
            "other_local_csv_rows_are_duplicates_or_derivatives_of_the_same_human_source",
            "four_untracked_source_rows_have_no_human_identity_answer",
            "rhb_approved_no_match_is_not_authorized_for_split_scoring_or_resolver_evaluation",
        ],
        "required_holdout_contract": {
            "minimum_new_catalog_relative_no_match_count": MINIMUM_UNTOUCHED_NO_MATCH_COUNT,
            "organic_real_query_required": True,
            "independent_human_answer_required": True,
            "catalog_snapshot_binding_required": True,
            "freeze_before_resolver_access_required": True,
            "development_rows_may_not_be_reused": True,
            "synthetic_or_counterfactual_negatives_allowed": False,
            "threshold_or_model_retuning_allowed": False,
        },
        "guardrails": {
            "row_level_source_data_persisted": False,
            "external_source_files_copied": False,
            "resolver_loaded": False,
            "neural_model_loaded": False,
            "final_test_cases_read": 0,
            "final_test_cases_scored": 0,
            "policy_evaluation_performed": False,
            "runtime_default_changed": False,
            "runtime_activation_authorized": False,
        },
        "conclusion": (
            "No independently untouched, human-answered real no-match holdout exists in the "
            "audited local sources. Pointwise v2 remains development-only."
        ),
        "next_allowed_action": (
            "authorize_collection_and_independent_adjudication_of_at_least_20_new_real_"
            "catalog_relative_no_match_queries"
        ),
    }


def _contains_row_level_key(value: object) -> bool:
    forbidden = {
        "case",
        "case_id",
        "case_ids",
        "cases",
        "query",
        "queries",
        "record",
        "records",
        "label",
        "labels",
        "prediction",
        "predictions",
    }
    if isinstance(value, dict):
        return any(key in forbidden or _contains_row_level_key(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_row_level_key(item) for item in value)
    return False


def check(root: Path) -> dict[str, Any]:
    payload = _load_object(root / OUTPUT)
    if _contains_row_level_key(payload):
        raise ValueError("holdout readiness contains row-level data")
    expected = build_readiness(root, EXPECTED_SOURCE_INVENTORY)
    if _canonical_bytes(payload) != _canonical_bytes(expected):
        raise ValueError("holdout readiness differs from the frozen aggregate audit")
    return payload


def materialize(root: Path, source_root: Path) -> dict[str, Any]:
    path = root / OUTPUT
    if path.exists():
        raise FileExistsError("holdout readiness artifact already exists")
    inventory = audit_sources(root, source_root)
    payload = build_readiness(root, inventory)
    path.parent.mkdir(parents=True, exist_ok=False)
    path.write_bytes(_canonical_bytes(payload))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Pointwise policy holdout readiness")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--acknowledge-readiness-only", action="store_true")
    args = parser.parse_args()
    root = Path.cwd()
    if args.run:
        if args.source_root is None or not args.acknowledge_readiness_only:
            parser.error("--run requires --source-root and --acknowledge-readiness-only")
        print(json.dumps(materialize(root, args.source_root), indent=2, sort_keys=True))
        return
    if args.check:
        check(root)
        print("valid")
        return
    parser.error("choose --run or --check")


if __name__ == "__main__":
    main()
