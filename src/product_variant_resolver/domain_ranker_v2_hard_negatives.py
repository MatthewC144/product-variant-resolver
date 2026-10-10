"""DRV2-T4 evidence-gated, train-only pairwise hard-negative mining."""

from __future__ import annotations

import argparse
import json
import re
import stat
import subprocess
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .domain_ranker_v2_authoring import LOCAL_QUERY_PACK_PATH
from .domain_ranker_v2_candidate_pools import LOCAL_POOLS_PATH, _contains_public_row_level_data
from .domain_ranker_v2_governance import (
    _canonical_bytes,
    _content_sha256,
    _file_sha256,
    _load_object,
    _require_file,
    _string,
    _validate_digest,
)
from .domain_ranker_v2_latency_repair import RESULT_PATH as T3R_RESULT_PATH
from .domain_ranker_v2_latency_repair import check as check_t3r

SCHEMA_AUTHORIZATION = "pvr-drv2-t4-owner-authorization-v1"
SCHEMA_LOCAL_TRIPLES = "pvr-drv2-local-pairwise-hard-negatives-v1"
SCHEMA_MANIFEST = "pvr-drv2-pairwise-hard-negative-manifest-v1"

DIRECTORY = Path("data/evaluation/domain-ranker-v2-remediation")
LOCAL_DIRECTORY = DIRECTORY / "local-t4"
LOCAL_TRIPLES_PATH = LOCAL_DIRECTORY / "pairwise-triples.json"
AUTHORIZATION_PATH = DIRECTORY / "t4-owner-authorization.json"
MANIFEST_PATH = DIRECTORY / "hard-negative-manifest.json"

T2_QUERY_PACK_FILE_SHA256 = "8f52043d615c1422018e5abe01670ba867c1908a6b268ce85754c71a9528d1fa"
T2_QUERY_PACK_CONTENT_SHA256 = "149d7d867b9e270ffb805906aec64685d6823f11efcd68a59e9e74ba60134e6f"
T3_LOCAL_POOLS_FILE_SHA256 = "0c889bfc06755a49ba779f2df64a4e4d87d3de676bf47063fcfcdec454022b24"
T3_LOCAL_POOLS_CONTENT_SHA256 = "7beb612fd5834a2886d8946e01cb88a966de4bf95db14dbe7e42fbbaa5dd5d7b"
T3R_AUTHORIZATION_FILE_SHA256 = "3133eed503fa9c5d28079a91b2e0c761ea78dcdfb227f51f7e7be4c53c73596a"
T3R_ONNX_MANIFEST_FILE_SHA256 = "86f0dbec1839e6529bbdd7b99c4eff0c58db476583177e55440a2915af49cc87"
T3R_RESULT_FILE_SHA256 = "d70c207157b82aeb11d8718232e1b00a22fbab3d6c4d6119738a52e89786ad10"
T3R_RESULT_CONTENT_SHA256 = "f95095a1f710fedc5c8d98a2d1e72b7fda25b2d3a3c3edeaa3f5b469850b47f7"
OWNER_STATEMENT_SHA256 = "37e6c4a73e7b5f0bafa28453bc8756ef3d45f87162d0d1f802d1ff4bc2b26389"

TRAIN_PARTITION = "ranker_train"
EXPECTED_TRAIN_QUERY_COUNT = 120
MINIMUM_QUALIFYING_QUERY_COUNT = 60
MINIMUM_NEGATIVES_PER_QUERY = 2

SUPPORTED_FIELDS_BY_TEMPLATE: dict[str, tuple[str, ...]] = {
    "casting_year_toy_collector": (
        "release_year",
        "toy_number",
        "collector_number",
    ),
    "year_series_position_casting_collector": (
        "release_year",
        "series",
        "series_position",
        "collector_number",
    ),
    "toy_casting_collector_year": (
        "toy_number",
        "collector_number",
        "release_year",
    ),
}

_TOY_NUMBER = re.compile(r"[a-z]{3}\d{2}", re.IGNORECASE)
_COLLECTOR_NUMBER = re.compile(r"\d{1,3}")


def _write(path: Path, payload: object, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(payload))
    path.chmod(mode)


def _normalize(value: object) -> str:
    return " ".join(str(value).casefold().split())


def _optional(value: str | None) -> str | None:
    if value is None or value == "<missing>":
        return None
    return value


def _parse_candidate(text: str) -> dict[str, object]:
    rendered: dict[str, str] = {}
    for part in text.split(" | "):
        if "=" not in part:
            raise ValueError("candidate text contains an unparseable field")
        key, value = part.split("=", 1)
        rendered[key] = value
    required = {
        "casting",
        "year",
        "series",
        "collector",
        "series_position",
        "identifiers",
    }
    if not required.issubset(rendered):
        raise ValueError("candidate text is missing an exact-release field")
    identifiers = [item.strip() for item in rendered["identifiers"].split(";")]
    toy_numbers = [item.upper() for item in identifiers if _TOY_NUMBER.fullmatch(item)]
    collector_numbers = [item for item in identifiers if _COLLECTOR_NUMBER.fullmatch(item)]
    if len(toy_numbers) != 1 or len(collector_numbers) != 1:
        raise ValueError("candidate identifiers do not contain one toy and collector number")
    year = _optional(rendered["year"])
    if year is None or not year.isdigit():
        raise ValueError("candidate release year is invalid")
    collector = _optional(rendered["collector"])
    if collector is None or collector != collector_numbers[0]:
        raise ValueError("candidate collector rendering and identifiers disagree")
    return {
        "casting": _optional(rendered["casting"]),
        "release_year": int(year),
        "series": _optional(rendered["series"]),
        "series_position": _optional(rendered["series_position"]),
        "collector_number": collector,
        "toy_number": toy_numbers[0],
    }


def _conflicting_fields(
    target: Mapping[str, Any], candidate: Mapping[str, object], supported_fields: Sequence[str]
) -> list[str]:
    conflicts: list[str] = []
    for field in supported_fields:
        target_value = target.get(field)
        candidate_value = candidate.get(field)
        if target_value is None or candidate_value is None:
            continue
        if _normalize(target_value) != _normalize(candidate_value):
            conflicts.append(field)
    return sorted(conflicts)


def _validate_parent_chain(root: Path) -> dict[str, Any]:
    for path, digest, label in (
        (LOCAL_QUERY_PACK_PATH, T2_QUERY_PACK_FILE_SHA256, "T2 local query pack"),
        (LOCAL_POOLS_PATH, T3_LOCAL_POOLS_FILE_SHA256, "T3 local candidate pools"),
        (
            DIRECTORY / "t3r-owner-authorization.json",
            T3R_AUTHORIZATION_FILE_SHA256,
            "T3R authorization",
        ),
        (
            DIRECTORY / "onnx-manifest.json",
            T3R_ONNX_MANIFEST_FILE_SHA256,
            "T3R ONNX manifest",
        ),
        (T3R_RESULT_PATH, T3R_RESULT_FILE_SHA256, "T3R result"),
    ):
        _require_file(root / path, digest, label)
    result = check_t3r(root)
    if (
        result.get("result_sha256") != T3R_RESULT_CONTENT_SHA256
        or result.get("status") != "latency_repair_passed"
        or result.get("latency", {}).get("gate_passed") is not True
        or result.get("next_allowed_action") != "DRV2-T4_requires_separate_owner_authorization"
    ):
        raise ValueError("T3R does not authorize the separate T4 owner Gate")
    return result


def build_authorization(root: Path, code_commit: str) -> dict[str, Any]:
    _validate_parent_chain(root)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_AUTHORIZATION,
        "gate": "DRV2-T4",
        "authorization_date": "2026-10-10",
        "authorized_by": "project_owner",
        "owner_statement_sha256": OWNER_STATEMENT_SHA256,
        "decision": "mine_train_only_evidence_gated_exact_release_pairwise_triples",
        "authorized_actions": [
            "read_train_partition_queries_expected_identities_and_frozen_top25_pools",
            "label_same_casting_siblings_only_when_query_supported_exact_fields_conflict",
            "require_at_least_two_defensible_negatives_for_each_admitted_train_query",
            "hold_ambiguous_or_insufficient_density_siblings",
            "publish_aggregate_mining_manifest_only",
        ],
        "prohibited_actions": [
            "read_validation_or_selection_labels_for_mining",
            "infer_negative_labels_from_generic_score_or_rank_alone",
            "force_ambiguous_siblings_into_binary_labels",
            "model_training_checkpoint_creation_or_selection_scoring",
            "calibration_final_evaluation_or_runtime_activation",
            "public_row_level_queries_identities_candidates_or_triples",
        ],
        "bindings": {
            "t2_query_pack_file_sha256": T2_QUERY_PACK_FILE_SHA256,
            "t2_query_pack_content_sha256": T2_QUERY_PACK_CONTENT_SHA256,
            "t3_local_pools_file_sha256": T3_LOCAL_POOLS_FILE_SHA256,
            "t3_local_pools_content_sha256": T3_LOCAL_POOLS_CONTENT_SHA256,
            "t3r_result_file_sha256": T3R_RESULT_FILE_SHA256,
            "t3r_result_content_sha256": T3R_RESULT_CONTENT_SHA256,
            "implementation_commit": code_commit,
            "implementation_module_sha256": _file_sha256(
                root / "src/product_variant_resolver/domain_ranker_v2_hard_negatives.py"
            ),
        },
        "mining_protocol": {
            "partition": TRAIN_PARTITION,
            "expected_train_query_count": EXPECTED_TRAIN_QUERY_COUNT,
            "minimum_qualifying_query_count": MINIMUM_QUALIFYING_QUERY_COUNT,
            "minimum_negatives_per_query": MINIMUM_NEGATIVES_PER_QUERY,
            "negative_category": "same_casting_wrong_exact_release",
            "supported_fields_by_template": {
                key: list(value) for key, value in SUPPORTED_FIELDS_BY_TEMPLATE.items()
            },
            "negative_selection": "all_defensible_siblings_for_qualifying_queries",
            "hardness_signal_use": "audit_order_only_never_label_authority",
        },
    }
    result = {**body, "authorization_sha256": _content_sha256(body)}
    if _contains_public_row_level_data(result):
        raise ValueError("T4 authorization contains row-level material")
    return result


def _target_candidate(row: Mapping[str, Any]) -> Mapping[str, Any]:
    target_uuid = _string(row.get("target_uuid"), "target UUID")
    candidates = row.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 25:
        raise ValueError("T4 requires an unchanged Top-25 pool")
    matches = [
        candidate
        for candidate in candidates
        if isinstance(candidate, dict) and candidate.get("canonical_uuid") == target_uuid
    ]
    if len(matches) != 1 or row.get("target_retrieved") is not True:
        raise ValueError("T4 train target is not uniquely present in its frozen pool")
    return matches[0]


def build_mining_artifacts(
    root: Path, authorization: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    query_pack = _load_object(root / LOCAL_QUERY_PACK_PATH)
    pools = _load_object(root / LOCAL_POOLS_PATH)
    _validate_digest(query_pack, "query_pack_sha256", "T2 local query pack")
    _validate_digest(pools, "content_sha256", "T3 local candidate pools")
    if query_pack.get("query_pack_sha256") != T2_QUERY_PACK_CONTENT_SHA256:
        raise ValueError("T2 query pack content binding changed")
    if pools.get("content_sha256") != T3_LOCAL_POOLS_CONTENT_SHA256:
        raise ValueError("T3 candidate-pool content binding changed")
    query_records = query_pack.get("records")
    pool_rows = pools.get("rows")
    if not isinstance(query_records, list) or not isinstance(pool_rows, list):
        raise TypeError("T4 parent row collections are malformed")

    train_queries = {
        _string(record.get("case_id"), "train case ID"): record
        for record in query_records
        if isinstance(record, dict) and record.get("partition") == TRAIN_PARTITION
    }
    train_pools = {
        _string(row.get("case_id"), "train pool case ID"): row
        for row in pool_rows
        if isinstance(row, dict) and row.get("partition") == TRAIN_PARTITION
    }
    if (
        len(train_queries) != EXPECTED_TRAIN_QUERY_COUNT
        or len(train_pools) != EXPECTED_TRAIN_QUERY_COUNT
        or train_queries.keys() != train_pools.keys()
    ):
        raise ValueError("T4 requires exactly 120 aligned train queries and pools")

    triples: list[dict[str, Any]] = []
    held: list[dict[str, Any]] = []
    held_reasons: Counter[str] = Counter()
    qualifying_query_count = 0
    defensible_sibling_count = 0
    ambiguous_sibling_count = 0
    template_qualifying_counts: Counter[str] = Counter()

    for case_id in sorted(train_queries):
        query_record = train_queries[case_id]
        pool = train_pools[case_id]
        expected = query_record.get("expected_full_identity")
        if not isinstance(expected, dict):
            raise TypeError("T4 train expected identity is malformed")
        if pool.get("query") != query_record.get("query"):
            raise ValueError("T4 query and frozen pool disagree")
        template = _string(query_record.get("authoring_template_id"), "authoring template")
        supported_fields = SUPPORTED_FIELDS_BY_TEMPLATE.get(template)
        if supported_fields is None:
            raise ValueError("T4 encountered an unsupported authoring template")
        target = _target_candidate(pool)
        target_text = _string(target.get("rendered_text"), "positive text")
        parsed_target = _parse_candidate(target_text)
        for field in (
            "casting",
            "release_year",
            "series",
            "series_position",
            "collector_number",
            "toy_number",
        ):
            if _normalize(parsed_target.get(field)) != _normalize(expected.get(field)):
                raise ValueError("T4 positive candidate differs from the frozen expected identity")

        defensible: list[tuple[Mapping[str, Any], list[str]]] = []
        ambiguous: list[Mapping[str, Any]] = []
        candidates = pool["candidates"]
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise TypeError("T4 candidate is malformed")
            candidate_uuid = _string(candidate.get("canonical_uuid"), "candidate UUID")
            if candidate_uuid == pool["target_uuid"]:
                continue
            candidate_text = _string(candidate.get("rendered_text"), "candidate text")
            parsed = _parse_candidate(candidate_text)
            if _normalize(parsed.get("casting")) != _normalize(expected.get("casting")):
                continue
            conflicts = _conflicting_fields(expected, parsed, supported_fields)
            if conflicts:
                defensible.append((candidate, conflicts))
            else:
                ambiguous.append(candidate)
        defensible.sort(
            key=lambda item: (
                int(item[0]["generic_pointwise_rank"]),
                _string(item[0].get("canonical_uuid"), "candidate UUID"),
            )
        )
        ambiguous.sort(
            key=lambda candidate: (
                int(candidate["generic_pointwise_rank"]),
                _string(candidate.get("canonical_uuid"), "candidate UUID"),
            )
        )
        defensible_sibling_count += len(defensible)
        ambiguous_sibling_count += len(ambiguous)
        for candidate in ambiguous:
            held_reasons["no_query_supported_exact_field_conflict"] += 1
            held.append(
                {
                    "case_id": case_id,
                    "candidate_uuid": candidate["canonical_uuid"],
                    "reason": "no_query_supported_exact_field_conflict",
                }
            )
        if len(defensible) < MINIMUM_NEGATIVES_PER_QUERY:
            for candidate, conflicts in defensible:
                held_reasons["query_has_fewer_than_two_defensible_siblings"] += 1
                held.append(
                    {
                        "case_id": case_id,
                        "candidate_uuid": candidate["canonical_uuid"],
                        "reason": "query_has_fewer_than_two_defensible_siblings",
                        "conflicting_query_fields": conflicts,
                    }
                )
            continue
        qualifying_query_count += 1
        template_qualifying_counts[template] += 1
        for candidate, conflicts in defensible:
            triple_body: dict[str, Any] = {
                "case_id": case_id,
                "query": query_record["query"],
                "authoring_template_id": template,
                "positive_uuid": pool["target_uuid"],
                "positive_text": target_text,
                "negative_uuid": candidate["canonical_uuid"],
                "negative_text": candidate["rendered_text"],
                "negative_generic_rank": candidate["generic_pointwise_rank"],
                "negative_category": "same_casting_wrong_exact_release",
                "conflicting_query_fields": conflicts,
            }
            triples.append({"triple_id": _content_sha256(triple_body), **triple_body})

    if qualifying_query_count < MINIMUM_QUALIFYING_QUERY_COUNT:
        raise ValueError("T4 exact-release evidence density Gate failed")
    if any(len(triple["conflicting_query_fields"]) == 0 for triple in triples):
        raise ValueError("T4 created a negative without explicit query-supported conflict evidence")

    local_body: dict[str, Any] = {
        "schema_version": SCHEMA_LOCAL_TRIPLES,
        "status": "frozen_local_only",
        "authorization_sha256": authorization["authorization_sha256"],
        "query_pack_sha256": T2_QUERY_PACK_CONTENT_SHA256,
        "candidate_pool_sha256": T3_LOCAL_POOLS_CONTENT_SHA256,
        "partition": TRAIN_PARTITION,
        "label_semantics": "frozen_community_catalog_relative_not_manufacturer_global_truth",
        "triples": triples,
        "held_siblings": held,
    }
    local = {**local_body, "content_sha256": _content_sha256(local_body)}
    public_body: dict[str, Any] = {
        "schema_version": SCHEMA_MANIFEST,
        "status": "pairwise_mining_ready",
        "authorization_sha256": authorization["authorization_sha256"],
        "bindings": {
            "query_pack_sha256": T2_QUERY_PACK_CONTENT_SHA256,
            "candidate_pool_sha256": T3_LOCAL_POOLS_CONTENT_SHA256,
            "latency_repair_sha256": T3R_RESULT_CONTENT_SHA256,
            "private_pairwise_artifact_sha256": _content_sha256(local),
        },
        "protocol": authorization["mining_protocol"],
        "aggregate_counts": {
            "train_pool_count": len(train_pools),
            "qualifying_train_query_count": qualifying_query_count,
            "ineligible_train_query_count": len(train_pools) - qualifying_query_count,
            "defensible_same_casting_sibling_count": defensible_sibling_count,
            "pairwise_triple_count": len(triples),
            "ambiguous_same_casting_sibling_count": ambiguous_sibling_count,
            "held_sibling_count": len(held),
            "held_sibling_counts_by_reason": dict(sorted(held_reasons.items())),
            "qualifying_query_counts_by_template": dict(sorted(template_qualifying_counts.items())),
            "validation_label_read_count": 0,
            "selection_label_read_count": 0,
            "model_training_run_count": 0,
            "selection_quality_evaluation_count": 0,
        },
        "privacy": {
            "row_level_artifact_public": False,
            "public_report": "aggregate_only",
        },
        "next_allowed_action": "DRV2-T5_requires_separate_owner_authorization",
    }
    public = {**public_body, "manifest_sha256": _content_sha256(public_body)}
    if _contains_public_row_level_data(public):
        raise ValueError("T4 manifest contains row-level material")
    return local, public


def materialize(root: Path, code_commit: str) -> dict[str, Any]:
    output_paths = (AUTHORIZATION_PATH, MANIFEST_PATH, LOCAL_TRIPLES_PATH)
    if any((root / path).exists() for path in output_paths):
        raise FileExistsError("DRV2-T4 artifacts already exist")
    authorization = build_authorization(root, code_commit)
    local, manifest = build_mining_artifacts(root, authorization)
    _write(root / LOCAL_TRIPLES_PATH, local, 0o600)
    _write(root / AUTHORIZATION_PATH, authorization, 0o644)
    _write(root / MANIFEST_PATH, manifest, 0o644)
    return manifest


def check(root: Path) -> dict[str, Any]:
    _validate_parent_chain(root)
    authorization = _load_object(root / AUTHORIZATION_PATH)
    local = _load_object(root / LOCAL_TRIPLES_PATH)
    manifest = _load_object(root / MANIFEST_PATH)
    _validate_digest(authorization, "authorization_sha256", "T4 authorization")
    _validate_digest(local, "content_sha256", "T4 local triples")
    _validate_digest(manifest, "manifest_sha256", "T4 manifest")
    if authorization.get("bindings", {}).get("implementation_module_sha256") != _file_sha256(
        root / "src/product_variant_resolver/domain_ranker_v2_hard_negatives.py"
    ):
        raise ValueError("T4 implementation binding changed")
    expected_local, expected_manifest = build_mining_artifacts(root, authorization)
    if local != expected_local or manifest != expected_manifest:
        raise ValueError("T4 materialized artifacts differ from deterministic replay")
    if _contains_public_row_level_data(authorization) or _contains_public_row_level_data(manifest):
        raise ValueError("T4 public artifact contains row-level material")
    if stat.S_IMODE((root / LOCAL_TRIPLES_PATH).stat().st_mode) != 0o600:
        raise ValueError("T4 local triples must use mode 0600")
    for path in (AUTHORIZATION_PATH, MANIFEST_PATH):
        if stat.S_IMODE((root / path).stat().st_mode) != 0o644:
            raise ValueError("T4 public artifacts must use mode 0644")
    return manifest


def _current_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    )
    commit = result.stdout.strip()
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise ValueError("could not resolve T4 implementation commit")
    return commit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize or check DRV2-T4 hard negatives")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--acknowledge-owner-authorization", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.run:
        if not args.acknowledge_owner_authorization:
            parser.error("--run requires --acknowledge-owner-authorization")
        result = materialize(root, _current_commit(root))
    elif args.check:
        result = check(root)
    else:
        parser.error("choose --run or --check")
    print(
        json.dumps(
            {
                "status": result["status"],
                "qualifying_train_query_count": result["aggregate_counts"][
                    "qualifying_train_query_count"
                ],
                "pairwise_triple_count": result["aggregate_counts"]["pairwise_triple_count"],
                "next_allowed_action": result["next_allowed_action"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
