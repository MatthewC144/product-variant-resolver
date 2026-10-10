"""DRV2-T2 deterministic query authoring and family-safe partition freeze."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .domain_ranker_v2_governance import (
    AUTHORIZATION_PATH,
    CATALOG_PATH,
    CATALOG_SHA256,
    GOVERNANCE_PATH,
    NEGATIVE_HOLDOUT_PATH,
    POSITIVE_PATH,
    PROTOCOL_PATH,
    _canonical_bytes,
    _content_sha256,
    _identity_key,
    _load_object,
    _require_file,
    _string,
    _validate_digest,
)
from .domain_ranker_v2_governance import (
    check as check_t1_governance,
)
from .identity import normalize_text

SCHEMA_AUTHORIZATION = "pvr-drv2-t2-owner-authorization-v1"
SCHEMA_QUERY_PACK = "pvr-drv2-local-query-pack-v1"
SCHEMA_QUERY_MANIFEST = "pvr-drv2-query-pack-manifest-v1"
SCHEMA_SPLIT_MANIFEST = "pvr-drv2-split-manifest-v1"

DIRECTORY = Path("data/evaluation/domain-ranker-v2-remediation")
LOCAL_DIRECTORY = DIRECTORY / "local-t2"
LOCAL_QUERY_PACK_PATH = LOCAL_DIRECTORY / "query-pack.json"
AUTHORIZATION_T2_PATH = DIRECTORY / "t2-owner-authorization.json"
QUERY_MANIFEST_PATH = DIRECTORY / "query-pack-manifest.json"
SPLIT_MANIFEST_PATH = DIRECTORY / "split-manifest.json"

T1_AUTHORIZATION_FILE_SHA256 = (
    "d42ab9415c66c24b986731292ff9a9d02f4dd46a974b57c9cd0a4b3bfa8e3fab"
)
T1_PROTOCOL_FILE_SHA256 = "9d56b2d2ad524159b5334b9b1a3aab321954e6153a3ae5afe5ca9935806be4fc"
T1_GOVERNANCE_FILE_SHA256 = (
    "66bbe6f660492a372e2a7dce70ba126b849913efd25c952e389886dbc73ca3d6"
)
T1_GOVERNANCE_CONTENT_SHA256 = (
    "5b981e79df16510210b529a299932dc52c54b3b776808f792433f002eb7d03f8"
)
T2_OWNER_STATEMENT_SHA256 = (
    "37e6c4a73e7b5f0bafa28453bc8756ef3d45f87162d0d1f802d1ff4bc2b26389"
)
QUERY_COUNT = 180
PARTITION_COUNTS = {
    "ranker_train": 120,
    "ranker_validation": 30,
    "ranker_selection": 30,
}
SELECTION_SALT = "pvr:domain-ranker-v2:owner-authored-query:v1"
TARGET_SALT = "pvr:domain-ranker-v2:target-row:v1"
TEMPLATE_SALT = "pvr:domain-ranker-v2:query-template:v1"

_PUBLIC_ROW_LEVEL_KEYS = {
    "case_id",
    "casting",
    "expected_full_identity",
    "family_group_sha256",
    "partition",
    "query",
    "records",
    "rows",
    "source_record_sha256",
}


def _salted_hash(salt: str, value: str) -> str:
    return hashlib.sha256(f"{salt}\0{value}".encode()).hexdigest()


def _family_key(row: Mapping[str, Any]) -> str:
    return normalize_text(_string(row.get("casting_name"), "catalog casting"))


def _identity_string(row: Mapping[str, Any]) -> str:
    return "\x1f".join(_identity_key(row, catalog=True))


def _load_denylists(root: Path) -> tuple[set[tuple[str, ...]], set[str]]:
    positives = _load_object(root / POSITIVE_PATH).get("records")
    negatives = _load_object(root / NEGATIVE_HOLDOUT_PATH).get("records")
    if not isinstance(positives, list) or not isinstance(negatives, list):
        raise TypeError("legacy denylist datasets are malformed")
    identities: set[tuple[str, ...]] = set()
    query_hashes: set[str] = set()
    for row in positives:
        if not isinstance(row, dict) or not isinstance(row.get("expected_full_identity"), dict):
            raise TypeError("positive denylist row is malformed")
        identities.add(_identity_key(row["expected_full_identity"], catalog=False))
        query_hashes.add(hashlib.sha256(_string(row.get("query"), "query").encode()).hexdigest())
    for row in negatives:
        if not isinstance(row, dict):
            raise TypeError("negative denylist row is malformed")
        query_hashes.add(hashlib.sha256(_string(row.get("query"), "query").encode()).hexdigest())
    if len(identities) != 153 or len(query_hashes) != 173:
        raise ValueError("legacy denylist cardinality changed")
    return identities, query_hashes


def _eligible_families(root: Path) -> dict[str, list[dict[str, Any]]]:
    denied_identities, _ = _load_denylists(root)
    rows = _load_object(root / CATALOG_PATH).get("records")
    if not isinstance(rows, list):
        raise TypeError("catalog records are malformed")
    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if not isinstance(row, dict) or _identity_key(row, catalog=True) in denied_identities:
            continue
        exact_fields = (
            row.get("release_year"),
            row.get("series"),
            row.get("collector_number"),
            row.get("series_position"),
            row.get("toy_number"),
        )
        if sum(value not in (None, "") for value in exact_fields) >= 3:
            families[_family_key(row)].append(row)
    eligible = {key: value for key, value in families.items() if len(value) >= 3}
    if len(eligible) != 269 or sum(map(len, eligible.values())) != 1041:
        raise ValueError("eligible v2 authoring population changed")
    return eligible


def _template(row: Mapping[str, Any], family: str) -> tuple[str, str]:
    common = {
        "casting": _string(row.get("casting_name"), "casting"),
        "year": str(row.get("release_year")),
        "series": _string(row.get("series"), "series"),
        "series_position": _string(row.get("series_position"), "series position"),
        "toy_number": _string(row.get("toy_number"), "toy number"),
        "collector_number": _string(row.get("collector_number"), "collector number"),
    }
    templates = (
        ("casting_year_toy_collector", "{casting} {year} {toy_number} {collector_number}"),
        (
            "year_series_position_casting_collector",
            "{year} {series} {series_position} {casting} {collector_number}",
        ),
        ("toy_casting_collector_year", "{toy_number} {casting} {collector_number} {year}"),
    )
    index = int(_salted_hash(TEMPLATE_SALT, family), 16) % len(templates)
    template_id, template = templates[index]
    return template_id, " ".join(template.format(**common).split())


def _expected_identity(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "brand": _string(row.get("brand"), "brand"),
        "casting": _string(row.get("casting_name"), "casting"),
        "release_year": row.get("release_year"),
        "series": _string(row.get("series"), "series"),
        "collector_number": _string(row.get("collector_number"), "collector number"),
        "series_position": _string(row.get("series_position"), "series position"),
        "toy_number": _string(row.get("toy_number"), "toy number"),
    }


def build_query_pack(root: Path) -> dict[str, Any]:
    check_t1_governance(root)
    families = _eligible_families(root)
    _, denied_query_hashes = _load_denylists(root)
    selected_families = sorted(
        families, key=lambda family: (_salted_hash(SELECTION_SALT, family), family)
    )[:QUERY_COUNT]
    rows: list[dict[str, Any]] = []
    boundaries = (120, 150, 180)
    for index, family in enumerate(selected_families):
        candidates = sorted(
            families[family],
            key=lambda row: (_salted_hash(TARGET_SALT, _identity_string(row)), _identity_string(row)),
        )
        target = candidates[0]
        template_id, query = _template(target, family)
        query_hash = hashlib.sha256(query.encode()).hexdigest()
        if query_hash in denied_query_hashes:
            raise ValueError("authored query overlaps the permanent legacy denylist")
        partition = (
            "ranker_train"
            if index < boundaries[0]
            else "ranker_validation"
            if index < boundaries[1]
            else "ranker_selection"
        )
        rows.append(
            {
                "case_id": f"drv2-q{index + 1:03d}",
                "query": query,
                "expected_full_identity": _expected_identity(target),
                "authoring_template_id": template_id,
                "family_group_sha256": hashlib.sha256(family.encode()).hexdigest(),
                "source_record_sha256": hashlib.sha256(
                    _string(target.get("source_record_id"), "source record id").encode()
                ).hexdigest(),
                "partition": partition,
            }
        )
    body: dict[str, Any] = {
        "schema_version": SCHEMA_QUERY_PACK,
        "status": "frozen_local_only",
        "authority_scope": "frozen_community_catalog_relative_not_manufacturer_or_global_truth",
        "source_catalog_file_sha256": CATALOG_SHA256,
        "t1_governance_content_sha256": T1_GOVERNANCE_CONTENT_SHA256,
        "records": rows,
    }
    return {**body, "query_pack_sha256": _content_sha256(body)}


def build_t2_authorization(root: Path) -> dict[str, Any]:
    body: dict[str, Any] = {
        "schema_version": SCHEMA_AUTHORIZATION,
        "gate": "DRV2-T2",
        "authorization_date": "2026-10-09",
        "authorized_by": "project_owner",
        "owner_statement_sha256": T2_OWNER_STATEMENT_SHA256,
        "decision": "authorize_local_query_authoring_and_family_safe_partitioning_only",
        "authorized_actions": [
            "author_exactly_180_new_queries_from_t1_eligible_capacity",
            "freeze_120_30_30_family_disjoint_partitions",
            "publish_aggregate_manifests_and_hashes_only",
        ],
        "prohibited_actions": [
            "candidate_pool_generation_or_scoring",
            "hard_negative_mining_or_labeling",
            "model_training_or_checkpoint_creation",
            "calibration_final_evaluation_or_runtime_activation",
            "public_row_level_queries_answers_or_membership",
        ],
        "bindings": {
            "t1_authorization_file_sha256": T1_AUTHORIZATION_FILE_SHA256,
            "t1_protocol_file_sha256": T1_PROTOCOL_FILE_SHA256,
            "t1_governance_file_sha256": T1_GOVERNANCE_FILE_SHA256,
            "t1_governance_content_sha256": T1_GOVERNANCE_CONTENT_SHA256,
        },
    }
    return {**body, "authorization_sha256": _content_sha256(body)}


def _partition_sets(records: list[dict[str, Any]], key: str) -> dict[str, set[str]]:
    output: dict[str, set[str]] = defaultdict(set)
    for row in records:
        value: object
        if key == "identity":
            value = _content_sha256(row["expected_full_identity"])
        elif key == "query":
            value = hashlib.sha256(row["query"].encode()).hexdigest()
        else:
            value = row[key]
        output[row["partition"]].add(str(value))
    return output


def _overlap_count(groups: Mapping[str, set[str]]) -> int:
    names = tuple(PARTITION_COUNTS)
    return sum(len(groups[names[i]] & groups[names[j]]) for i in range(3) for j in range(i + 1, 3))


def _contains_public_row_level_key(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            key in _PUBLIC_ROW_LEVEL_KEYS or _contains_public_row_level_key(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_public_row_level_key(item) for item in value)
    return False


def build_manifests(
    root: Path, query_pack: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    records = query_pack.get("records")
    if not isinstance(records, list) or not all(isinstance(row, dict) for row in records):
        raise TypeError("local query pack records are malformed")
    typed_records = [row for row in records if isinstance(row, dict)]
    partition_counts = Counter(row["partition"] for row in typed_records)
    template_counts = Counter(row["authoring_template_id"] for row in typed_records)
    query_sets = _partition_sets(typed_records, "query")
    identity_sets = _partition_sets(typed_records, "identity")
    family_sets = _partition_sets(typed_records, "family_group_sha256")
    common: dict[str, Any] = {
        "query_pack_sha256": query_pack["query_pack_sha256"],
        "local_query_pack_file_sha256": _content_sha256(query_pack),
        "t2_authorization_sha256": build_t2_authorization(root)["authorization_sha256"],
    }
    query_body: dict[str, Any] = {
        "schema_version": SCHEMA_QUERY_MANIFEST,
        "status": "frozen_aggregate_only",
        **common,
        "counts": {
            "authored_queries": len(typed_records),
            "unique_queries": len(set().union(*query_sets.values())),
            "unique_exact_identities": len(set().union(*identity_sets.values())),
            "unique_casting_families": len(set().union(*family_sets.values())),
            "legacy_query_denylist_overlaps": 0,
            "source_url_fields": 0,
            "color_fields": 0,
            "edition_fields": 0,
        },
        "template_counts": dict(sorted(template_counts.items())),
        "row_level_publication": False,
        "rights_state": "owner_attested_not_independently_verified",
        "authority_scope": "frozen_community_catalog_relative_not_manufacturer_or_global_truth",
    }
    split_body: dict[str, Any] = {
        "schema_version": SCHEMA_SPLIT_MANIFEST,
        "status": "frozen_family_safe_aggregate_only",
        **common,
        "partition_counts": dict(sorted(partition_counts.items())),
        "cross_partition_overlap_counts": {
            "normalized_query": _overlap_count(query_sets),
            "exact_identity": _overlap_count(identity_sets),
            "casting_family": _overlap_count(family_sets),
        },
        "exact_density_readiness": {
            "train_queries_with_at_least_two_same_family_siblings": len(
                family_sets["ranker_train"]
            ),
            "minimum_required": 60,
            "candidate_labels_created": 0,
        },
        "selection_partition_use": "untouched_until_DRV2_T6",
        "next_allowed_action": "DRV2-T3_requires_separate_owner_authorization",
    }
    return (
        {**query_body, "manifest_sha256": _content_sha256(query_body)},
        {**split_body, "manifest_sha256": _content_sha256(split_body)},
    )


def materialize(root: Path) -> dict[str, Any]:
    for path, digest in (
        (AUTHORIZATION_PATH, T1_AUTHORIZATION_FILE_SHA256),
        (PROTOCOL_PATH, T1_PROTOCOL_FILE_SHA256),
        (GOVERNANCE_PATH, T1_GOVERNANCE_FILE_SHA256),
    ):
        _require_file(root / path, digest, "T1 governance artifact")
    query_pack = build_query_pack(root)
    authorization = build_t2_authorization(root)
    query_manifest, split_manifest = build_manifests(root, query_pack)
    local_directory = root / LOCAL_DIRECTORY
    local_directory.mkdir(parents=True, exist_ok=True)
    local_path = root / LOCAL_QUERY_PACK_PATH
    local_path.write_bytes(_canonical_bytes(query_pack))
    local_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    (root / DIRECTORY).mkdir(parents=True, exist_ok=True)
    for path, payload in (
        (AUTHORIZATION_T2_PATH, authorization),
        (QUERY_MANIFEST_PATH, query_manifest),
        (SPLIT_MANIFEST_PATH, split_manifest),
    ):
        output = root / path
        output.write_bytes(_canonical_bytes(payload))
        output.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    return check(root)


def check(root: Path) -> dict[str, Any]:
    query_pack = _load_object(root / LOCAL_QUERY_PACK_PATH)
    authorization = _load_object(root / AUTHORIZATION_T2_PATH)
    query_manifest = _load_object(root / QUERY_MANIFEST_PATH)
    split_manifest = _load_object(root / SPLIT_MANIFEST_PATH)
    _validate_digest(query_pack, "query_pack_sha256", "local v2 query pack")
    _validate_digest(authorization, "authorization_sha256", "T2 authorization")
    _validate_digest(query_manifest, "manifest_sha256", "query manifest")
    _validate_digest(split_manifest, "manifest_sha256", "split manifest")
    if build_query_pack(root) != query_pack:
        raise ValueError("local v2 query pack is not deterministically reproducible")
    expected_query, expected_split = build_manifests(root, query_pack)
    if query_manifest != expected_query or split_manifest != expected_split:
        raise ValueError("public T2 manifests do not match the private pack")
    if authorization != build_t2_authorization(root):
        raise ValueError("T2 authorization differs from the frozen owner gate")
    if any(_contains_public_row_level_key(value) for value in (authorization, query_manifest, split_manifest)):
        raise ValueError("public T2 artifact contains row-level material")
    if split_manifest["partition_counts"] != dict(sorted(PARTITION_COUNTS.items())):
        raise ValueError("T2 partition counts differ from 120/30/30")
    mode = stat.S_IMODE((root / LOCAL_QUERY_PACK_PATH).stat().st_mode)
    if mode != stat.S_IRUSR | stat.S_IWUSR:
        raise ValueError("local T2 query pack must use mode 0600")
    return split_manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Materialize or check DRV2-T2 query partitions")
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
                "split_manifest_sha256": result["manifest_sha256"],
                "next_allowed_action": result["next_allowed_action"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
