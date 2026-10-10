"""DRV2-T1 source/authoring governance; no row authoring or model access."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .identity import normalize_text

VERSION = "domain-ranker-v2-remediation"
SCHEMA_AUTHORIZATION = "pvr-drv2-t1-owner-authorization-v1"
SCHEMA_PROTOCOL = "pvr-drv2-query-authoring-protocol-v1"
SCHEMA_GOVERNANCE = "pvr-drv2-governance-v1"

DIRECTORY = Path("data/evaluation/domain-ranker-v2-remediation")
AUTHORIZATION_PATH = DIRECTORY / "owner-authorization.json"
PROTOCOL_PATH = DIRECTORY / "authoring-protocol.json"
GOVERNANCE_PATH = DIRECTORY / "governance.json"

CATALOG_PATH = Path("data/external/hot-wheels-wiki/local-export-2023-2026/normalized.json")
POSITIVE_PATH = Path("data/evaluation/image-search-resolver-v1/dataset.json")
NEGATIVE_HOLDOUT_PATH = Path(
    "data/evaluation/image-search-pointwise-no-match-holdout-v1/dataset.json"
)
T5_RESULT_PATH = Path("config/domain-ranker-selection-v1.json")

CATALOG_SHA256 = "b4e0747450a5447c2bf66b0838c91f3f723a19ac97c90c7ac3636cf3a9a709d4"
POSITIVE_SHA256 = "b0feeff8f1158ab67cfac2ae493eefc04a6aba1b90d4fce448724341315e095c"
NEGATIVE_HOLDOUT_SHA256 = "b46367efb54c9ab2a74c23d0824d1da5f939ecdf74a63c612da37c0688c50a7e"
T5_RESULT_SHA256 = "219789db3f1e6f7e3e114656d165ca3ebe733225139e294787dc64beaa3e25c3"
T5_RESULT_CONTENT_SHA256 = "d9665b151c4c3263afd8e24345024985904f1a407d93ce6c9173ed37d8444e2b"
OWNER_STATEMENT_SHA256 = "acfc4e74a650e7dfce69a54bc74065931f029c9d80e78e3e024f1474c5f2950a"

CATALOG_COUNT = 1_763
POSITIVE_COUNT = 153
POSITIVE_TEST_COUNT = 53
NEGATIVE_HOLDOUT_COUNT = 20
MINIMUM_QUERY_COUNT = 180
MINIMUM_TRAIN_COUNT = 120
MINIMUM_VALIDATION_COUNT = 30
MINIMUM_SELECTION_COUNT = 30
MINIMUM_EXACT_DENSITY_QUERIES = 60
MINIMUM_SAME_FAMILY_NEGATIVES = 2
MINIMUM_FAMILY_RELEASES = 3
EXPECTED_REMAINING_ROWS = 1_610
EXPECTED_ELIGIBLE_ROWS = 1_041
EXPECTED_ELIGIBLE_FAMILIES = 269

_ROW_LEVEL_KEYS = {
    "case_id",
    "cases",
    "expected",
    "expected_full_identity",
    "label",
    "labels",
    "query",
    "queries",
    "record",
    "records",
    "row",
    "rows",
    "source_record_id",
}


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


def _require_file(path: Path, expected: str, label: str) -> None:
    if _file_sha256(path) != expected:
        raise ValueError(f"{label} differs from the frozen SHA-256 binding")


def _load_object(path: Path) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise ValueError(f"duplicate JSON key: {key}")
            output[key] = value
        return output

    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: could not read strict JSON") from error
    if not isinstance(payload, dict):
        raise TypeError(f"{path}: JSON root must be an object")
    return payload


def _validate_digest(payload: Mapping[str, Any], field: str, label: str) -> None:
    body = {key: value for key, value in payload.items() if key != field}
    if payload.get(field) != _content_sha256(body):
        raise ValueError(f"{label} checksum is stale")


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _current_git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    )
    commit = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("could not resolve governance code commit")
    return commit


def _identity_key(identity: Mapping[str, Any], *, catalog: bool) -> tuple[str, ...]:
    casting_key = "casting_name" if catalog else "casting"
    values = (
        identity.get(casting_key),
        identity.get("release_year"),
        identity.get("series"),
        identity.get("collector_number"),
        identity.get("series_position"),
        identity.get("toy_number"),
    )
    normalized: list[str] = []
    for index, value in enumerate(values):
        if index == 1:
            normalized.append(str(value or ""))
        elif index == 3:
            text = str(value or "").strip().lstrip("0")
            normalized.append(text or "0")
        else:
            normalized.append(normalize_text(str(value or "")))
    return tuple(normalized)


def audit_source_capacity(root: Path) -> dict[str, Any]:
    _require_file(root / CATALOG_PATH, CATALOG_SHA256, "frozen catalog")
    _require_file(root / POSITIVE_PATH, POSITIVE_SHA256, "positive denylist dataset")
    _require_file(root / NEGATIVE_HOLDOUT_PATH, NEGATIVE_HOLDOUT_SHA256, "negative holdout dataset")
    _require_file(root / T5_RESULT_PATH, T5_RESULT_SHA256, "T5 negative result")

    t5 = _load_object(root / T5_RESULT_PATH)
    _validate_digest(t5, "result_sha256", "T5 result")
    if (
        t5.get("result_sha256") != T5_RESULT_CONTENT_SHA256
        or t5.get("winner") is not None
        or t5.get("status") != "ranker_gate_failed"
    ):
        raise ValueError("v2 must descend from the frozen T5 null result")

    positive = _load_object(root / POSITIVE_PATH)
    positive_rows = positive.get("records")
    if not isinstance(positive_rows, list) or len(positive_rows) != POSITIVE_COUNT:
        raise ValueError("positive denylist must contain exactly 153 rows")
    denied_identities: set[tuple[str, ...]] = set()
    denied_query_hashes: set[str] = set()
    for row in positive_rows:
        if not isinstance(row, dict) or not isinstance(row.get("expected_full_identity"), dict):
            raise TypeError("positive denylist row is malformed")
        denied_identities.add(_identity_key(row["expected_full_identity"], catalog=False))
        denied_query_hashes.add(
            hashlib.sha256(_string(row.get("query"), "query").encode()).hexdigest()
        )
    if len(denied_identities) != POSITIVE_COUNT or len(denied_query_hashes) != POSITIVE_COUNT:
        raise ValueError("positive denylist identities and queries must be unique")

    negatives = _load_object(root / NEGATIVE_HOLDOUT_PATH)
    negative_rows = negatives.get("records")
    if not isinstance(negative_rows, list) or len(negative_rows) != NEGATIVE_HOLDOUT_COUNT:
        raise ValueError("negative holdout must contain exactly 20 rows")
    for row in negative_rows:
        if not isinstance(row, dict):
            raise TypeError("negative holdout row is malformed")
        denied_query_hashes.add(
            hashlib.sha256(_string(row.get("query"), "query").encode()).hexdigest()
        )
    if len(denied_query_hashes) != POSITIVE_COUNT + NEGATIVE_HOLDOUT_COUNT:
        raise ValueError("combined query denylist must contain 173 unique hashes")

    catalog = _load_object(root / CATALOG_PATH)
    rows = catalog.get("records")
    counts = catalog.get("counts")
    if (
        catalog.get("schema_version") != "pvr-local-release-staging-v1"
        or catalog.get("status") != "review_only_local_staging_snapshot"
        or not isinstance(counts, dict)
        or counts.get("staged_observations") != CATALOG_COUNT
        or not isinstance(rows, list)
        or len(rows) != CATALOG_COUNT
    ):
        raise ValueError("catalog structure differs from the frozen v2 source contract")
    remaining = [
        row
        for row in rows
        if isinstance(row, dict) and _identity_key(row, catalog=True) not in denied_identities
    ]
    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in remaining:
        casting = normalize_text(_string(row.get("casting_name"), "catalog casting"))
        families[casting].append(row)
    eligible: list[dict[str, Any]] = []
    eligible_family_names: set[str] = set()
    for casting, family in families.items():
        if len(family) < MINIMUM_FAMILY_RELEASES:
            continue
        for row in family:
            exact_fields = (
                row.get("release_year"),
                row.get("series"),
                row.get("collector_number"),
                row.get("series_position"),
                row.get("toy_number"),
            )
            if sum(value not in (None, "") for value in exact_fields) >= 3:
                eligible.append(row)
                eligible_family_names.add(casting)
    if (
        len(remaining) != EXPECTED_REMAINING_ROWS
        or len(eligible) != EXPECTED_ELIGIBLE_ROWS
        or len(eligible_family_names) != EXPECTED_ELIGIBLE_FAMILIES
    ):
        raise ValueError("v2 source capacity differs from the frozen readiness audit")
    return {
        "catalog_record_count": len(rows),
        "positive_identity_denylist_count": len(denied_identities),
        "combined_query_denylist_count": len(denied_query_hashes),
        "remaining_catalog_rows": len(remaining),
        "eligible_catalog_rows": len(eligible),
        "eligible_casting_families": len(eligible_family_names),
        "minimum_family_release_count": MINIMUM_FAMILY_RELEASES,
        "authoring_capacity_passed": len(eligible) >= MINIMUM_QUERY_COUNT,
    }


def authoring_protocol() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_PROTOCOL,
        "version": VERSION,
        "source_projection": [
            "brand",
            "casting_name",
            "release_year",
            "series",
            "collector_number",
            "series_position",
            "toy_number",
        ],
        "excluded_source_fields": [
            "source_page_url",
            "source_page_title",
            "input_filename",
            "raw_fields",
            "collected_at",
        ],
        "query_templates": [
            "casting year toy_number collector_number",
            "year series series_position casting collector_number",
            "toy_number casting collector_number year",
        ],
        "normalization": "identity.normalize_text-v1",
        "selection_order": "sha256_salted_identity_key_ascending",
        "selection_salt": "pvr:domain-ranker-v2:owner-authored-query:v1",
        "required_query_count": MINIMUM_QUERY_COUNT,
        "minimum_partition_counts": {
            "ranker_train": MINIMUM_TRAIN_COUNT,
            "ranker_validation": MINIMUM_VALIDATION_COUNT,
            "ranker_selection": MINIMUM_SELECTION_COUNT,
        },
        "exact_density_gate": {
            "minimum_train_queries": MINIMUM_EXACT_DENSITY_QUERIES,
            "minimum_same_casting_wrong_release_negatives_per_query": MINIMUM_SAME_FAMILY_NEGATIVES,
            "ambiguous_sibling_action": "held_not_labeled",
        },
        "partition_unit": "connected_casting_alias_evidence_and_exact_identity_component",
        "target_injection_allowed": False,
        "resolver_output_access_during_authoring": False,
        "t5_error_or_prediction_access_during_authoring": False,
        "color_and_edition_label_authority": False,
        "row_level_output": "local_only_git_ignored",
    }


def build_authorization(root: Path, code_commit: str) -> dict[str, Any]:
    capacity = audit_source_capacity(root)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_AUTHORIZATION,
        "gate": "DRV2-T1",
        "authorization_date": "2026-10-09",
        "authorized_by": "project_owner",
        "owner_statement_sha256": OWNER_STATEMENT_SHA256,
        "decision": "approve_v2_source_and_owner_authored_query_governance_only",
        "authorized_actions": [
            "materialize_v2_source_and_authoring_governance",
            "prepare_future_local_only_180_query_authoring_run",
            "preserve_120_30_30_partition_minima",
            "use_one_future_pairwise_objective_after_later_gate",
        ],
        "prohibited_actions": [
            "execute_query_authoring_or_partitioning_in_T1",
            "read_or_use_v1_selection_errors_predictions_or_row_diagnostics",
            "read_or_use_53_positive_test_rows_as_training_or_selection",
            "read_or_use_20_negative_holdout_rows_as_training_or_selection",
            "use_52_no_match_rows_for_ranker_training",
            "candidate_scoring_or_model_training",
            "calibration_final_evaluation_or_runtime_activation",
            "claim_independently_verified_rights_or_manufacturer_truth",
        ],
        "bindings": {
            "catalog_file_sha256": CATALOG_SHA256,
            "positive_denylist_file_sha256": POSITIVE_SHA256,
            "negative_holdout_file_sha256": NEGATIVE_HOLDOUT_SHA256,
            "t5_result_file_sha256": T5_RESULT_SHA256,
            "t5_result_content_sha256": T5_RESULT_CONTENT_SHA256,
            "governance_code_commit": code_commit,
            "governance_module_sha256": _file_sha256(
                root / "src/product_variant_resolver/domain_ranker_v2_governance.py"
            ),
        },
        "approved_minima": {
            "new_query_count": MINIMUM_QUERY_COUNT,
            "ranker_train": MINIMUM_TRAIN_COUNT,
            "ranker_validation": MINIMUM_VALIDATION_COUNT,
            "ranker_selection": MINIMUM_SELECTION_COUNT,
            "exact_density_train_queries": MINIMUM_EXACT_DENSITY_QUERIES,
            "same_family_negatives_per_density_query": MINIMUM_SAME_FAMILY_NEGATIVES,
        },
        "capacity_audit": capacity,
        "rights_state": "owner_attested_not_independently_verified",
        "authority_scope": "frozen_community_catalog_relative_not_manufacturer_or_global_truth",
    }
    return {**body, "authorization_sha256": _content_sha256(body)}


def build_governance(
    authorization: Mapping[str, Any], protocol: Mapping[str, Any]
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": SCHEMA_GOVERNANCE,
        "version": VERSION,
        "status": "active_for_source_and_authoring_readiness_only",
        "authorization_sha256": authorization["authorization_sha256"],
        "protocol_sha256": protocol["protocol_sha256"],
        "bindings": authorization["bindings"],
        "capacity_audit": authorization["capacity_audit"],
        "permissions": {
            "future_local_owner_authored_query_materialization": True,
            "future_family_safe_partitioning_after_separate_gate": True,
            "candidate_pool_scoring": False,
            "hard_negative_mining": False,
            "pairwise_model_training": False,
            "calibration_or_threshold_selection": False,
            "fresh_final_evaluation": False,
            "runtime_activation": False,
            "public_row_level_queries_labels_or_predictions": False,
        },
        "permanent_denylist": {
            "positive_dataset_file_sha256": POSITIVE_SHA256,
            "positive_identity_count": POSITIVE_COUNT,
            "opened_positive_test_count": POSITIVE_TEST_COUNT,
            "negative_holdout_file_sha256": NEGATIVE_HOLDOUT_SHA256,
            "negative_holdout_count": NEGATIVE_HOLDOUT_COUNT,
            "t5_selection_predictions_and_errors": "prohibited",
        },
        "rights_state": authorization["rights_state"],
        "authority_scope": authorization["authority_scope"],
        "next_allowed_action": "DRV2-T2_requires_separate_owner_authorization",
    }
    return {**body, "governance_sha256": _content_sha256(body)}


def _contains_row_level_key(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            key in _ROW_LEVEL_KEYS or _contains_row_level_key(item) for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_row_level_key(item) for item in value)
    return False


def materialize(root: Path) -> dict[str, Any]:
    authorization = build_authorization(root, _current_git_commit(root))
    protocol_body = authoring_protocol()
    protocol = {**protocol_body, "protocol_sha256": _content_sha256(protocol_body)}
    governance = build_governance(authorization, protocol)
    directory = root / DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    for path, payload in (
        (root / AUTHORIZATION_PATH, authorization),
        (root / PROTOCOL_PATH, protocol),
        (root / GOVERNANCE_PATH, governance),
    ):
        path.write_bytes(_canonical_bytes(payload))
        path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    return check(root)


def check(root: Path) -> dict[str, Any]:
    capacity = audit_source_capacity(root)
    authorization = _load_object(root / AUTHORIZATION_PATH)
    protocol = _load_object(root / PROTOCOL_PATH)
    governance = _load_object(root / GOVERNANCE_PATH)
    _validate_digest(authorization, "authorization_sha256", "v2 authorization")
    _validate_digest(protocol, "protocol_sha256", "v2 protocol")
    _validate_digest(governance, "governance_sha256", "v2 governance")
    expected = build_governance(authorization, protocol)
    if governance != expected or authorization.get("capacity_audit") != capacity:
        raise ValueError("v2 governance differs from the frozen source audit")
    if any(_contains_row_level_key(item) for item in (authorization, protocol, governance)):
        raise ValueError("public v2 governance contains row-level material")
    if governance["permissions"]["pairwise_model_training"] is not False:
        raise ValueError("v2 T1 must not authorize model training")
    return governance


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Materialize or check DRV2-T1 governance")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = check(args.root.resolve()) if args.check else materialize(args.root.resolve())
    print(
        json.dumps(
            {
                "status": "valid" if args.check else "materialized",
                "governance_sha256": result["governance_sha256"],
                "next_allowed_action": result["next_allowed_action"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
