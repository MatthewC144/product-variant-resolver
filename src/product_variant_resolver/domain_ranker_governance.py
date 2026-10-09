"""Hash-bound DRSP-T1 authorization and governance gate.

This module validates data lineage and permissions only. It deliberately does not
load a resolver, score a query, mine negatives, train a model, or select thresholds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
from pathlib import Path
from typing import Any

from .identity import normalize_text
from .pointwise_no_match_governance import (
    CANDIDATE_SET_SHA256,
)
from .pointwise_no_match_governance import (
    SPLIT_ASSIGNMENT_SHA256 as NO_MATCH_SPLIT_SHA256,
)
from .pointwise_no_match_governance import check as check_no_match_governance
from .pointwise_no_match_readiness import (
    FIT_COUNT,
    SELECTION_COUNT,
)
from .pointwise_no_match_readiness import (
    build_readiness as build_no_match_readiness,
)

SCHEMA_VERSION = "pvr-domain-ranker-governance-v1"
AUTHORIZATION_SCHEMA_VERSION = "pvr-drsp-t1-owner-authorization-v1"
VERSION = "domain-ranker-selective-prediction-development-v1"

DIRECTORY = Path("data/evaluation/domain-ranker-selective-prediction-development-v1")
AUTHORIZATION_PATH = DIRECTORY / "owner-authorization.json"
GOVERNANCE_PATH = DIRECTORY / "governance.json"

POSITIVE_DATASET_PATH = Path("data/evaluation/image-search-resolver-v1/dataset.json")
HUMAN_DATASET_PATH = Path("data/human_labeled_names.json")
CATALOG_PATH = Path("data/external/hot-wheels-wiki/local-export-2023-2026/normalized.json")
NEGATIVE_HOLDOUT_PATH = Path(
    "data/evaluation/image-search-pointwise-no-match-holdout-v1/dataset.json"
)
NO_MATCH_GOVERNANCE_PATH = Path(
    "data/evaluation/image-search-pointwise-no-match-readiness-v1/governance-overlay.json"
)
NO_MATCH_READINESS_PATH = Path(
    "data/evaluation/image-search-pointwise-no-match-readiness-v1/readiness.json"
)
NO_MATCH_AUTHORIZATION_PATH = Path(
    "data/evaluation/image-search-pointwise-no-match-readiness-v1/pnmr-g1-owner-authorization.json"
)

POSITIVE_DATASET_SHA256 = "b0feeff8f1158ab67cfac2ae493eefc04a6aba1b90d4fce448724341315e095c"
POSITIVE_SPLIT_SHA256 = "10ed70cc347f1b548c156e033645d6b0e90f48ee66c95af631832e8d55aebdac"
HUMAN_DATASET_SHA256 = "68b5dfdb8d0fa4972328d172cc5a56d78ac8bf00bc740083b2bfc07eb2a91188"
CATALOG_SHA256 = "b4e0747450a5447c2bf66b0838c91f3f723a19ac97c90c7ac3636cf3a9a709d4"
NEGATIVE_HOLDOUT_SHA256 = "b46367efb54c9ab2a74c23d0824d1da5f939ecdf74a63c612da37c0688c50a7e"
NO_MATCH_READINESS_FILE_SHA256 = "d723aedbba7f0d7438a78595b2ea5654e19e12aa664eecaaf435240f550d9c73"
NO_MATCH_AUTHORIZATION_FILE_SHA256 = (
    "6f438a2dd37f48b3c9f38329bfeea991061fc36cc8eda78c3489f22873133d2c"
)
NO_MATCH_GOVERNANCE_FILE_SHA256 = "1008ae962c17d1c3a4a9eb54a3488211c2514f9749e70b2915a7a7a291660ab4"

POSITIVE_TOTAL_COUNT = 153
POSITIVE_DEVELOPMENT_COUNT = 100
POSITIVE_TEST_COUNT = 53
CATALOG_COUNT = 1_763
NEGATIVE_HOLDOUT_COUNT = 20

POSITIVE_SPLIT_SALT = "pvr:image-search-release-ranking:development-test:v1"
# The verbatim owner response stays in the private conversation record.  Public
# artifacts retain only this digest plus the normalized, bounded interpretation.
OWNER_STATEMENT_SHA256 = "573456b91b18191e2fbf87048ff1fe4dea4cdddef0be0ae1294e44e20446ab86"

_ROW_LEVEL_KEYS = {
    "assignment",
    "assignments",
    "candidate",
    "candidates",
    "case_id",
    "case_ids",
    "expected_casting",
    "expected_full_identity",
    "label",
    "labels",
    "prediction",
    "predictions",
    "query",
    "queries",
    "record",
    "records",
    "row",
    "rows",
}


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


def _content_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _file_sha256(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{path}: required regular file is absent or unsafe")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_file(path: Path, expected_sha256: str, label: str) -> None:
    if _file_sha256(path) != expected_sha256:
        raise ValueError(f"{label} differs from the frozen SHA-256 binding")


def _string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _positive_split_audit(root: Path) -> dict[str, Any]:
    path = root / POSITIVE_DATASET_PATH
    _require_file(path, POSITIVE_DATASET_SHA256, "positive dataset")
    payload = _load_object(path)
    if payload.get("dataset_version") != "image-search-resolver-v1":
        raise ValueError("positive dataset version differs from the frozen contract")
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != POSITIVE_TOTAL_COUNT:
        raise ValueError("positive dataset must contain exactly 153 records")

    seen_ids: set[str] = set()
    seen_queries: set[str] = set()
    keyed: list[tuple[str, str]] = []
    for index, raw in enumerate(records, start=1):
        if not isinstance(raw, dict):
            raise TypeError("positive dataset record must be an object")
        case_id = _string(raw.get("id"), "positive case ID")
        if case_id != f"isr-{index:04d}" or case_id in seen_ids:
            raise ValueError("positive case IDs differ from the frozen ordered contract")
        query = normalize_text(_string(raw.get("query"), "positive query"))
        casting = normalize_text(_string(raw.get("expected_casting"), "positive casting"))
        identity = raw.get("expected_full_identity")
        if not isinstance(identity, dict):
            raise TypeError("positive expected identity must be an object")
        if normalize_text(_string(identity.get("casting"), "identity casting")) != casting:
            raise ValueError("positive casting and expected identity disagree")
        if not query or query in seen_queries:
            raise ValueError("positive normalized queries must be non-empty and unique")
        seen_ids.add(case_id)
        seen_queries.add(query)
        split_key = hashlib.sha256(
            f"{POSITIVE_SPLIT_SALT}\0{case_id}\0{casting}".encode()
        ).hexdigest()
        keyed.append((split_key, case_id))

    development_ids = {case_id for _, case_id in sorted(keyed)[:POSITIVE_DEVELOPMENT_COUNT]}
    assignments = [
        {
            "case_id": _string(raw.get("id"), "positive case ID"),
            "split": (
                "development"
                if _string(raw.get("id"), "positive case ID") in development_ids
                else "test"
            ),
        }
        for raw in records
        if isinstance(raw, dict)
    ]
    assignment_sha256 = hashlib.sha256(
        json.dumps(assignments, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    development_count = sum(item["split"] == "development" for item in assignments)
    test_count = sum(item["split"] == "test" for item in assignments)
    if (
        assignment_sha256 != POSITIVE_SPLIT_SHA256
        or development_count != POSITIVE_DEVELOPMENT_COUNT
        or test_count != POSITIVE_TEST_COUNT
    ):
        raise ValueError("positive development/test split differs from the frozen contract")
    return {
        "dataset_sha256": POSITIVE_DATASET_SHA256,
        "split_assignment_sha256": POSITIVE_SPLIT_SHA256,
        "total_count": POSITIVE_TOTAL_COUNT,
        "development_count": development_count,
        "permanently_excluded_test_count": test_count,
    }


def _no_match_development_audit(root: Path, *, require_local_catalog: bool) -> dict[str, Any]:
    _require_file(root / HUMAN_DATASET_PATH, HUMAN_DATASET_SHA256, "human dataset")
    catalog_present = (root / CATALOG_PATH).exists()
    if require_local_catalog or catalog_present:
        readiness = build_no_match_readiness(root)
        overlay = check_no_match_governance(root)
    else:
        _require_file(
            root / NO_MATCH_READINESS_PATH,
            NO_MATCH_READINESS_FILE_SHA256,
            "no-match readiness artifact",
        )
        _require_file(
            root / NO_MATCH_AUTHORIZATION_PATH,
            NO_MATCH_AUTHORIZATION_FILE_SHA256,
            "no-match authorization artifact",
        )
        _require_file(
            root / NO_MATCH_GOVERNANCE_PATH,
            NO_MATCH_GOVERNANCE_FILE_SHA256,
            "no-match governance artifact",
        )
        readiness = _load_object(root / NO_MATCH_READINESS_PATH)
        overlay = _load_object(root / NO_MATCH_GOVERNANCE_PATH)
    audit = readiness.get("audit")
    split = readiness.get("prospective_split")
    if not isinstance(audit, dict) or not isinstance(split, dict):
        raise TypeError("no-match readiness audit sections must be objects")
    if (
        audit.get("candidate_set_sha256") != CANDIDATE_SET_SHA256
        or audit.get("exact_family_absent_count") != FIT_COUNT + SELECTION_COUNT
        or split.get("assignment_sha256") != NO_MATCH_SPLIT_SHA256
        or split.get("fit_count") != FIT_COUNT
        or split.get("selection_count") != SELECTION_COUNT
    ):
        raise ValueError("no-match development set or split differs from the frozen contract")
    permissions = overlay.get("permissions")
    if not isinstance(permissions, dict) or (
        permissions.get("pointwise_development_calibration_fit") is not True
        or permissions.get("pointwise_development_threshold_selection") is not True
        or permissions.get("runtime_activation") is not False
    ):
        raise ValueError("no-match governance permissions differ from the approved narrow scope")
    return {
        "human_dataset_sha256": HUMAN_DATASET_SHA256,
        "candidate_set_sha256": CANDIDATE_SET_SHA256,
        "split_assignment_sha256": NO_MATCH_SPLIT_SHA256,
        "calibration_fit_count": FIT_COUNT,
        "threshold_selection_count": SELECTION_COUNT,
        "governance_overlay_sha256": _file_sha256(root / NO_MATCH_GOVERNANCE_PATH),
    }


def _catalog_audit(root: Path, *, require_local_catalog: bool) -> dict[str, Any]:
    path = root / CATALOG_PATH
    rights_state = "access_permission_and_republication_rights_not_provided"
    if not path.exists() and not require_local_catalog:
        return {
            "catalog_sha256": CATALOG_SHA256,
            "record_count": CATALOG_COUNT,
            "local_file_revalidated": False,
            "recorded_source_rights_state": rights_state,
        }
    _require_file(path, CATALOG_SHA256, "frozen catalog")
    payload = _load_object(path)
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != CATALOG_COUNT:
        raise ValueError("frozen catalog must contain exactly 1,763 records")
    if payload.get("source_rights_state") != rights_state:
        raise ValueError("catalog source-rights state differs from the frozen source record")
    return {
        "catalog_sha256": CATALOG_SHA256,
        "record_count": CATALOG_COUNT,
        "local_file_revalidated": True,
        "recorded_source_rights_state": rights_state,
    }


def _negative_holdout_audit(root: Path) -> dict[str, Any]:
    path = root / NEGATIVE_HOLDOUT_PATH
    _require_file(path, NEGATIVE_HOLDOUT_SHA256, "opened negative holdout")
    payload = _load_object(path)
    records = payload.get("records")
    approval = payload.get("approval")
    if (
        payload.get("dataset_version") != "image-search-pointwise-no-match-holdout-v1"
        or payload.get("status") != "owner_reviewed_frozen_not_scored"
        or not isinstance(records, list)
        or len(records) != NEGATIVE_HOLDOUT_COUNT
        or not isinstance(approval, dict)
    ):
        raise ValueError("opened negative holdout differs from the frozen contract")
    if any(
        approval.get(key) is not False
        for key in (
            "model_retuning_authorized",
            "resolver_scoring_authorized",
            "runtime_activation_authorized",
            "threshold_retuning_authorized",
        )
    ):
        raise ValueError("opened negative holdout permission boundary changed")
    return {
        "dataset_sha256": NEGATIVE_HOLDOUT_SHA256,
        "permanently_excluded_count": NEGATIVE_HOLDOUT_COUNT,
    }


def audit_inputs(root: Path, *, require_local_catalog: bool = True) -> dict[str, Any]:
    """Validate all DRSP-T1 inputs and return aggregate-only evidence."""
    catalog = _catalog_audit(root, require_local_catalog=require_local_catalog)
    return {
        "positive": _positive_split_audit(root),
        "no_match_development": _no_match_development_audit(
            root, require_local_catalog=require_local_catalog
        ),
        "catalog": catalog,
        "negative_holdout": _negative_holdout_audit(root),
    }


def build_authorization(root: Path, *, require_local_catalog: bool = True) -> dict[str, Any]:
    inputs = audit_inputs(root, require_local_catalog=require_local_catalog)
    inputs["catalog"].pop("local_file_revalidated")
    # Materialization always uses require_local_catalog=True.  This stable statement lets a
    # public checkout validate the artifact without mounting the Git-ignored source snapshot.
    inputs["catalog"]["local_file_revalidated_at_materialization"] = True
    body: dict[str, Any] = {
        "schema_version": AUTHORIZATION_SCHEMA_VERSION,
        "gate": "DRSP-T1",
        "authorization_date": "2026-10-09",
        "authorized_by": "project_owner",
        "owner_statement_sha256": OWNER_STATEMENT_SHA256,
        "decision": "approve_path_b_for_owner_attested_local_only_ml_development",
        "rights_interpretation": {
            "basis": "project_owner_attestation_of_google_acquisition",
            "independently_verified_license_or_redistribution_rights": False,
            "catalog_recorded_rights_state": (
                "access_permission_and_republication_rights_not_provided"
            ),
            "rights_cleared_claim_allowed": False,
        },
        "authorized_scopes": {
            "positive_development": {
                "count": POSITIVE_DEVELOPMENT_COUNT,
                "fields": ["query", "expected_casting", "expected_full_identity"],
                "uses": [
                    "family_safe_development_partitioning",
                    "one_shot_hard_negative_mining",
                    "local_domain_cross_encoder_fine_tuning",
                    "local_ranker_selection",
                ],
            },
            "catalog_identity_projection": {
                "count": CATALOG_COUNT,
                "fields": [
                    "brand",
                    "casting_name",
                    "collector_number",
                    "color",
                    "release_year",
                    "series",
                    "series_position",
                    "source_record_id",
                    "toy_number",
                    "variant_note",
                ],
                "uses": ["frozen_candidate_pool_construction", "hard_negative_identity_evidence"],
            },
            "no_match_development": {
                "count": FIT_COUNT + SELECTION_COUNT,
                "fields": [
                    "initial_name",
                    "human_label_brand",
                    "human_label_casting",
                    "human_label_confidence",
                ],
                "uses": ["calibration_fit", "threshold_selection"],
                "ranker_fine_tuning_allowed": False,
                "hard_negative_mining_allowed": False,
            },
        },
        "publication_and_retention": {
            "raw_training_projection": "local_only_git_ignored",
            "mined_pairs": "local_only_git_ignored",
            "fine_tuned_checkpoints": "local_only_git_ignored",
            "public_outputs": "hashes_counts_limitations_and_aggregate_evidence_only",
            "checkpoint_or_weights_publication_allowed": False,
            "retention": "local_development_only_until_owner_deletion_or_milestone_cleanup",
        },
        "prohibited_actions": [
            "read_or_use_53_positive_test_rows_in_any_adaptive_phase",
            "read_or_use_20_negative_holdout_rows_in_any_adaptive_phase",
            "fine_tune_ranker_on_52_no_match_development_rows",
            "publish_row_level_training_or_mined_pair_data",
            "publish_checkpoint_or_model_weights",
            "claim_fresh_final_performance",
            "activate_runtime_policy",
            "claim_manufacturer_or_global_truth",
            "perform_live_recollection",
        ],
        "bindings": inputs,
        "authorization_boundary": {
            "materialize_drsp_t1_governance": True,
            "drsp_t2_or_later_authorized_by_this_artifact": False,
            "resolver_evaluation_authorized": False,
            "model_training_started": False,
        },
    }
    return {**body, "authorization_sha256": _content_sha256(body)}


def _validate_authorization(
    payload: dict[str, Any], root: Path, *, require_local_catalog: bool = True
) -> None:
    expected = build_authorization(root, require_local_catalog=require_local_catalog)
    if payload != expected:
        raise ValueError("DRSP-T1 owner authorization is stale, generic, or out of scope")
    body = {key: value for key, value in payload.items() if key != "authorization_sha256"}
    if payload.get("authorization_sha256") != _content_sha256(body):
        raise ValueError("DRSP-T1 owner authorization checksum is stale")


def build_governance(
    root: Path,
    authorization: dict[str, Any],
    *,
    require_local_catalog: bool = True,
) -> dict[str, Any]:
    _validate_authorization(authorization, root, require_local_catalog=require_local_catalog)
    bindings = authorization["bindings"]
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "version": VERSION,
        "status": "active_for_owner_attested_local_only_development",
        "materialization_date": "2026-10-09",
        "materialized_by": "product_variant_resolver.domain_ranker_governance",
        "owner_authorization_sha256": authorization["authorization_sha256"],
        "rights_state": "owner_attested_not_independently_verified",
        "authority_scope": ("frozen_third_party_catalog_relative_not_manufacturer_or_global_truth"),
        "bindings": {
            "positive_dataset_sha256": bindings["positive"]["dataset_sha256"],
            "positive_split_assignment_sha256": bindings["positive"]["split_assignment_sha256"],
            "human_dataset_sha256": bindings["no_match_development"]["human_dataset_sha256"],
            "no_match_candidate_set_sha256": bindings["no_match_development"][
                "candidate_set_sha256"
            ],
            "no_match_split_assignment_sha256": bindings["no_match_development"][
                "split_assignment_sha256"
            ],
            "catalog_sha256": bindings["catalog"]["catalog_sha256"],
            "negative_holdout_sha256": bindings["negative_holdout"]["dataset_sha256"],
        },
        "admitted_aggregate_counts": {
            "positive_development": POSITIVE_DEVELOPMENT_COUNT,
            "no_match_calibration_fit": FIT_COUNT,
            "no_match_threshold_selection": SELECTION_COUNT,
        },
        "permanent_denylist": {
            "positive_test": {
                "parent_dataset_sha256": POSITIVE_DATASET_SHA256,
                "split_assignment_sha256": POSITIVE_SPLIT_SHA256,
                "count": POSITIVE_TEST_COUNT,
                "scope": "records_queries_and_exact_identities",
            },
            "negative_holdout": {
                "dataset_sha256": NEGATIVE_HOLDOUT_SHA256,
                "count": NEGATIVE_HOLDOUT_COUNT,
                "scope": "records_queries_and_expected_identities",
            },
            "applies_to": [
                "partition_assignment",
                "candidate_pool_adaptation",
                "hard_negative_mining",
                "fine_tuning",
                "model_selection",
                "calibration_fit",
                "threshold_selection",
                "future_final_manifest",
            ],
        },
        "permissions": {
            "positive_local_hard_negative_mining": True,
            "positive_local_domain_fine_tuning": True,
            "positive_local_ranker_selection": True,
            "no_match_calibration_fit": True,
            "no_match_threshold_selection": True,
            "no_match_ranker_fine_tuning": False,
            "public_row_level_data": False,
            "public_checkpoint_or_weights": False,
            "fresh_final_claim": False,
            "runtime_activation": False,
            "manufacturer_or_global_truth_claim": False,
            "live_recollection": False,
        },
        "artifact_boundary": {
            "local_git_ignored": [
                "training_projections",
                "split_membership",
                "candidate_text",
                "mined_pairs",
                "row_labels",
                "row_predictions",
                "checkpoints",
            ],
            "git_trackable": ["hashes", "counts", "limitations", "aggregate_evidence"],
        },
        "guardrails": {
            "resolver_loaded": False,
            "neural_model_loaded": False,
            "queries_scored": 0,
            "hard_negatives_mined": 0,
            "training_runs_started": 0,
            "positive_test_rows_read_for_adaptation": 0,
            "negative_holdout_rows_read_for_adaptation": 0,
            "runtime_default_changed": False,
        },
        "next_allowed_action": "separate_owner_authorization_for_drsp_t2",
    }
    governance = {**body, "governance_sha256": _content_sha256(body)}
    if _contains_row_level_key(governance):
        raise ValueError("DRSP-T1 governance contains forbidden row-level output")
    return governance


def _contains_row_level_key(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            (isinstance(key, str) and key in _ROW_LEVEL_KEYS) or _contains_row_level_key(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_row_level_key(item) for item in value)
    return False


def _validate_governance(
    payload: dict[str, Any],
    root: Path,
    authorization: dict[str, Any],
    *,
    require_local_catalog: bool = True,
) -> None:
    expected = build_governance(root, authorization, require_local_catalog=require_local_catalog)
    if payload != expected:
        raise ValueError("DRSP-T1 governance is stale, tampered, or out of scope")
    body = {key: value for key, value in payload.items() if key != "governance_sha256"}
    if payload.get("governance_sha256") != _content_sha256(body):
        raise ValueError("DRSP-T1 governance checksum is stale")
    if _contains_row_level_key(payload):
        raise ValueError("DRSP-T1 governance contains forbidden row-level output")


def materialize(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    authorization_path = root / AUTHORIZATION_PATH
    governance_path = root / GOVERNANCE_PATH
    if authorization_path.exists() or governance_path.exists():
        raise FileExistsError("DRSP-T1 authorization or governance already exists")
    authorization = build_authorization(root)
    governance = build_governance(root, authorization)
    authorization_path.parent.mkdir(parents=True, exist_ok=True)
    authorization_path.write_bytes(_canonical_bytes(authorization))
    governance_path.write_bytes(_canonical_bytes(governance))
    authorization_path.chmod(0o644)
    governance_path.chmod(0o644)
    return authorization, governance


def check(root: Path, *, require_local_catalog: bool = False) -> dict[str, Any]:
    authorization_path = root / AUTHORIZATION_PATH
    governance_path = root / GOVERNANCE_PATH
    if stat.S_IMODE(authorization_path.stat().st_mode) != 0o644:
        raise ValueError("DRSP-T1 owner authorization must use mode 0644")
    if stat.S_IMODE(governance_path.stat().st_mode) != 0o644:
        raise ValueError("DRSP-T1 governance must use mode 0644")
    authorization = _load_object(authorization_path)
    governance = _load_object(governance_path)
    _validate_authorization(authorization, root, require_local_catalog=require_local_catalog)
    _validate_governance(
        governance,
        root,
        authorization,
        require_local_catalog=require_local_catalog,
    )
    return governance


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize or validate the DRSP-T1 gate")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--require-local-catalog", action="store_true")
    parser.add_argument("--acknowledge-owner-authorization", action="store_true")
    arguments = parser.parse_args()
    root = Path.cwd()
    if arguments.run:
        if not arguments.acknowledge_owner_authorization:
            parser.error("--run requires --acknowledge-owner-authorization")
        _authorization, governance = materialize(root)
        print(json.dumps(governance, indent=2, sort_keys=True))
        return
    if arguments.check:
        check(root, require_local_catalog=arguments.require_local_catalog)
        print("valid")
        return
    parser.error("choose --run or --check")


if __name__ == "__main__":
    main()
