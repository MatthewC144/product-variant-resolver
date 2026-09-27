from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from product_variant_resolver.representative_benchmark import (
    ContractError,
    SourceDecisionArtifact,
    canonical_record_sha256,
    content_sha256,
    validate_canonical_authority,
    validate_frozen_manifest,
    validate_label_blind_raw,
    validate_labels,
    validate_query_pack,
    validate_scored_results,
    validate_source_inventory,
    validate_source_inventory_manifest,
    validate_split,
)

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "evaluation" / "representative-hard-benchmark-v1"


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _approved_inventory_payload() -> dict[str, Any]:
    payload = _json(DATA_DIR / "source-inventory.json")
    source = next(
        entry for entry in payload["entries"] if entry["source_id"] == "human-labeled-real-noisy-v1"
    )
    source.update(
        {
            "access_permission_status": "approved",
            "benchmark_uses": ["query_provenance"],
            "content_license_status": "approved",
            "owner_decision": "approved",
            "privacy_review_status": "approved",
            "prospective_benchmark_use_status": "approved",
            "prospective_redistribution_status": "approved",
        }
    )
    source["known_rights_evidence"] = {
        "status": "approved",
        "evidence": ["owner-review://source-1"],
        "limitations": [],
    }
    source["owner_decision_metadata"] = {
        "current_use": "representative benchmark",
        "benchmark_use": "approved exact uses",
        "privacy_risk": "reviewed",
        "unresolved_conditions": [],
    }
    authority_source = copy.deepcopy(source)
    authority_source.update(
        {
            "source_id": "future-authorized-exact-v1",
            "source_kind": "authorized_export",
            "origin_reference": "owner-authorized-export://exact-variant-v1",
            "acquisition_method": "future owner-authorized exact-variant export",
            "local_sha256": "9" * 64,
            "benchmark_uses": ["exact_variant_authority"],
            "evidence_refs": ["owner-review://future-exact-source"],
            "record_count": 1,
            "record_count_kind": "independent_exact_variant_records",
            "authority_eligibility": "exact_variant_authority_candidate",
            "authority_evidence_level": "independent_exact_variant",
            "authority_boundary": "Candidate only; T4 still validates every exact record.",
        }
    )
    payload["entries"].append(authority_source)
    return payload


def _catalog() -> dict[str, Any]:
    return _json(ROOT / "data" / "catalog.json")


def _decisions_for_inventory(inventory: Any) -> SourceDecisionArtifact:
    inventory_payload = inventory.model_dump(mode="json", exclude_none=True)
    payload = _json(DATA_DIR / "source-decisions.json")
    payload["inventory_sha256"] = content_sha256(inventory_payload)
    payload["inventory_version"] = inventory.inventory_version
    if any(entry.source_id == "future-authorized-exact-v1" for entry in inventory.entries):
        payload["sources"].append(
            {
                "source_id": "future-authorized-exact-v1",
                "source_origin": "inventory",
                "authority_eligibility": "exact_variant_authority_candidate",
                "collection_status": "existing_rows_only_no_new_collection",
                "downstream_permissions": [
                    "query_pack",
                    "scored_labels",
                    "canonical_authority",
                ],
                "allowed_label_statuses": ["matched", "ambiguous", "no_match"],
                "decisions": [
                    {
                        "use": "query_text",
                        "status": "approved",
                        "effective_publication_scope": "public_rows",
                        "owner_confirmation_required": True,
                        "owner_confirmed": True,
                        "allowed_fields": ["query_text"],
                        "conditions": ["test_authorized_export_only"],
                    },
                    {
                        "use": "evidence_retention",
                        "status": "approved",
                        "effective_publication_scope": "public_rows",
                        "owner_confirmation_required": True,
                        "owner_confirmed": True,
                        "allowed_fields": ["exact_variant_evidence"],
                        "conditions": ["test_authorized_export_only"],
                    },
                    {
                        "use": "reviewer_identity",
                        "status": "approved",
                        "effective_publication_scope": "public_rows",
                        "owner_confirmation_required": True,
                        "owner_confirmed": True,
                        "allowed_fields": ["reviewer_role"],
                        "conditions": ["role_only_project_owner"],
                    },
                    {
                        "use": "local_only_benchmark_use",
                        "status": "approved",
                        "effective_publication_scope": "public_rows",
                        "owner_confirmation_required": True,
                        "owner_confirmed": True,
                        "allowed_fields": ["query_text", "scored_label"],
                        "conditions": ["test_authorized_export_only"],
                    },
                    {
                        "use": "public_git_artifacts",
                        "status": "approved",
                        "effective_publication_scope": "public_rows",
                        "owner_confirmation_required": True,
                        "owner_confirmed": True,
                        "allowed_fields": ["query_text", "scored_label", "reviewer_role"],
                        "conditions": ["test_authorized_export_only"],
                    },
                    {
                        "use": "exact_variant_authority",
                        "status": "approved",
                        "effective_publication_scope": "public_rows",
                        "owner_confirmation_required": True,
                        "owner_confirmed": True,
                        "allowed_fields": ["exact_variant_evidence"],
                        "conditions": ["test_authorized_export_only"],
                    },
                ],
            }
        )
    return SourceDecisionArtifact.model_validate(payload)


def _authority_payload(catalog: dict[str, Any]) -> dict[str, Any]:
    product = catalog["products"][0]
    return {
        "schema_version": "pvr-representative-hard-benchmark-canonical-authority-v1",
        "authority_version": "authority-v1",
        "publication_scope": "public",
        "records": [
            {
                "authority_id": "authority-001",
                "canonical_uuid": product["canonical_uuid"],
                "canonical_catalog_version": catalog["catalog_version"],
                "catalog_record_sha256": canonical_record_sha256(product),
                "variant_fields_verified": [
                    "casting",
                    "release_year",
                    "series",
                    "color",
                    "collector_number",
                    "series_position",
                    "identifiers",
                ],
                "independent_evidence_refs": ["owner-review://exact-1"],
                "evidence_source_ids": ["future-authorized-exact-v1"],
                "resolver_output_consulted": False,
                "reviewed_by": "project_owner",
                "reviewed_at": "2026-09-25T12:00:00Z",
                "review_reason": "Independently verified exact release fields.",
                "status": "approved_exact",
            }
        ],
    }


def _query_pack_payload(*, second_case: bool = False) -> dict[str, Any]:
    cases = [
        {
            "case_id": "case-001",
            "query": "2022 Nomad red 101",
            "source_id": "future-authorized-exact-v1",
            "source_record_ref": "owner-ref-001",
            "public_safe": True,
            "family_group_key": "chevy-nomad",
            "evidence_event_group_key": "event-001",
            "challenge_tags": ["same_casting_different_release"],
            "authored_by": "project_owner",
            "authored_at": "2026-09-26T12:00:00Z",
            "resolver_output_viewed": False,
            "split": "test",
        }
    ]
    if second_case:
        cases.append(
            {
                **cases[0],
                "case_id": "case-002",
                "query": "Nomad release unknown",
                "evidence_event_group_key": "event-002",
                "split": "test",
            }
        )
    return {
        "schema_version": "pvr-representative-hard-benchmark-query-pack-v1",
        "dataset_version": "pilot-v1",
        "publication_scope": "public",
        "representative_pilot": True,
        "cases": cases,
    }


def _label_payload(catalog: dict[str, Any], *, review_status: str = "approved") -> dict[str, Any]:
    product = catalog["products"][0]
    return {
        "schema_version": "pvr-representative-hard-benchmark-labels-v1",
        "dataset_version": "pilot-v1",
        "publication_scope": "public",
        "records": [
            {
                "case_id": "case-001",
                "expected_status": "matched",
                "expected_canonical_uuid": product["canonical_uuid"],
                "canonical_authority_id": "authority-001",
                "family_label": "Chevy Nomad",
                "failure_type": "none",
                "hard_negative": True,
                "hard_negative_kind": "same_casting_different_release",
                "source_id": "future-authorized-exact-v1",
                "evidence_refs": ["owner-review://label-1"],
                "review_status": review_status,
                "reviewed_by": "project_owner",
                "reviewed_at": "2026-09-27T12:00:00Z",
                "review_reason": "Exact variant confirmed without resolver output.",
                "public_safe": True,
                "score_eligible": review_status == "approved",
            }
        ],
    }


def _split_payload(*, second_case: bool = False) -> dict[str, Any]:
    records = [
        {
            "case_id": "case-001",
            "split": "test",
            "family_group_key": "chevy-nomad",
            "evidence_event_group_key": "event-001",
        }
    ]
    if second_case:
        records.append(
            {
                "case_id": "case-002",
                "split": "test",
                "family_group_key": "chevy-nomad",
                "evidence_event_group_key": "event-002",
            }
        )
    return {
        "schema_version": "pvr-representative-hard-benchmark-split-v1",
        "dataset_version": "pilot-v1",
        "seed": 17,
        "records": records,
    }


def _raw_payload(catalog: dict[str, Any]) -> dict[str, Any]:
    product = catalog["products"][0]
    return {
        "schema_version": "pvr-representative-hard-benchmark-test-raw-v1",
        "run_version": "run-v1",
        "collection_status": "complete",
        "labels_loaded": False,
        "parent_checksums": {"query-pack.json": "1" * 64},
        "results": [
            {
                "case_id": "case-001",
                "signals": {
                    "normalized_title": "2022 nomad red 101",
                    "tokens": ["2022", "nomad", "red", "101"],
                    "year": 2022,
                    "collector_number": "101",
                    "series_position": None,
                    "quantity": None,
                    "multipack_hint": False,
                    "color_hints": ["red"],
                    "series_hints": [],
                    "parse_warnings": [],
                },
                "candidates": [
                    {
                        "canonical_uuid": product["canonical_uuid"],
                        "canonical_id": product["canonical_id"],
                        "sparse_rank": 1,
                        "sparse_score": 1.0,
                        "similarity_rank": 1,
                        "similarity_score": 0.8,
                        "structured_rank": 1,
                        "structured_score": 1.0,
                        "rrf_rank": 1,
                        "rrf_score": 0.04,
                        "reranker_rank": None,
                        "reranker_score": None,
                    }
                ],
                "calibrated_probability": 0.95,
                "policy_status": "matched",
                "returned_canonical_uuid": product["canonical_uuid"],
                "timings_ms": {"total": 1.2},
                "errors": [],
                "runtime_hash": "2" * 64,
                "config_hash": "3" * 64,
            }
        ],
    }


def _valid_contracts() -> tuple[Any, ...]:
    catalog = _catalog()
    inventory = validate_source_inventory(_approved_inventory_payload())
    decisions = _decisions_for_inventory(inventory)
    authority = validate_canonical_authority(
        _authority_payload(catalog),
        inventory=inventory,
        catalog_payload=catalog,
        source_decisions=decisions,
    )
    queries = validate_query_pack(
        _query_pack_payload(), inventory=inventory, source_decisions=decisions
    )
    labels = validate_labels(
        _label_payload(catalog),
        query_pack=queries,
        authority=authority,
        catalog_payload=catalog,
        inventory=inventory,
        source_decisions=decisions,
    )
    split = validate_split(_split_payload(), query_pack=queries)
    raw = validate_label_blind_raw(_raw_payload(catalog), query_pack=queries, split=split)
    return catalog, inventory, authority, queries, labels, split, raw


def test_checked_in_t1_inventory_and_manifest_pass_the_strict_contract() -> None:
    inventory_payload = _json(DATA_DIR / "source-inventory.json")
    manifest_payload = _json(DATA_DIR / "source-inventory-manifest.json")

    inventory = validate_source_inventory(inventory_payload)
    manifest = validate_source_inventory_manifest(manifest_payload, inventory_payload)

    assert len(inventory.entries) == 6
    assert manifest.source_entry_count == 6


def test_unknown_fields_are_rejected_at_nested_boundaries() -> None:
    payload = _approved_inventory_payload()
    payload["entries"][0]["silent_extra"] = "not allowed"

    with pytest.raises(ValidationError, match="silent_extra"):
        validate_source_inventory(payload)


def test_query_pack_requires_the_owner_decision_overlay() -> None:
    inventory = validate_source_inventory(_json(DATA_DIR / "source-inventory.json"))

    with pytest.raises(TypeError, match="source_decisions"):
        cast(Any, validate_query_pack)(_query_pack_payload(), inventory=inventory)


def test_public_query_requires_publication_permission_and_no_pii() -> None:
    inventory = validate_source_inventory(_approved_inventory_payload())
    decisions = _decisions_for_inventory(inventory)
    query_payload = _query_pack_payload()
    query_payload["cases"][0]["query"] = "seller@example.com 2022 Nomad"
    with pytest.raises(ValidationError, match="personal information"):
        validate_query_pack(query_payload, inventory=inventory, source_decisions=decisions)

    local_payload = _query_pack_payload()
    local_payload["publication_scope"] = "local_only"
    local_payload["cases"][0]["public_safe"] = False
    local_payload["cases"][0]["query"] = "seller@example.com 2022 Nomad"
    assert (
        validate_query_pack(
            local_payload, inventory=inventory, source_decisions=decisions
        ).publication_scope
        == "local_only"
    )


def test_row_level_artifacts_reject_aggregate_only_scope() -> None:
    catalog = _catalog()
    inventory = validate_source_inventory(_approved_inventory_payload())
    decisions = _decisions_for_inventory(inventory)
    authority_payload = _authority_payload(catalog)
    authority_payload["publication_scope"] = "aggregate_only"
    with pytest.raises(ValidationError, match="public|local_only"):
        validate_canonical_authority(
            authority_payload,
            inventory=inventory,
            catalog_payload=catalog,
            source_decisions=decisions,
        )

    query_payload = _query_pack_payload()
    query_payload["publication_scope"] = "aggregate_only"
    with pytest.raises(ValidationError, match="public|local_only"):
        validate_query_pack(query_payload, inventory=inventory, source_decisions=decisions)

    _, valid_inventory, authority, queries, _, _, _ = _valid_contracts()
    valid_decisions = _decisions_for_inventory(valid_inventory)
    label_payload = _label_payload(catalog)
    label_payload["publication_scope"] = "aggregate_only"
    with pytest.raises(ValidationError, match="public|local_only"):
        validate_labels(
            label_payload,
            query_pack=queries,
            authority=authority,
            catalog_payload=catalog,
            inventory=valid_inventory,
            source_decisions=valid_decisions,
        )


def test_authority_requires_existing_catalog_uuid_and_exact_approved_source() -> None:
    catalog = _catalog()
    inventory = validate_source_inventory(_approved_inventory_payload())
    decisions = _decisions_for_inventory(inventory)
    payload = _authority_payload(catalog)
    payload["records"][0]["canonical_uuid"] = "3ad8aa8d-8f64-4b38-a9f5-bf76ac0476b6"
    with pytest.raises(ContractError, match="non-catalog UUID"):
        validate_canonical_authority(
            payload,
            inventory=inventory,
            catalog_payload=catalog,
            source_decisions=decisions,
        )

    payload = _authority_payload(catalog)
    inventory_payload = _approved_inventory_payload()
    source = next(
        entry
        for entry in inventory_payload["entries"]
        if entry["source_id"] == "future-authorized-exact-v1"
    )
    source["benchmark_uses"] = ["family_context"]
    with pytest.raises(ValidationError, match="require exact_variant_authority use"):
        validate_source_inventory(inventory_payload)

    consulted = _authority_payload(catalog)
    consulted["records"][0]["resolver_output_consulted"] = True
    consulted_inventory = validate_source_inventory(_approved_inventory_payload())
    with pytest.raises(ValidationError, match="False"):
        validate_canonical_authority(
            consulted,
            inventory=consulted_inventory,
            catalog_payload=catalog,
            source_decisions=_decisions_for_inventory(consulted_inventory),
        )


def test_authority_rejects_staged_or_family_only_claim_and_stale_record_hash() -> None:
    catalog = _catalog()
    inventory_payload = _approved_inventory_payload()
    payload = _authority_payload(catalog)
    payload["records"][0]["evidence_source_ids"] = ["owner-local-release-snapshot-2023-2026-v1"]
    inventory = validate_source_inventory(inventory_payload)
    decisions = _decisions_for_inventory(inventory)
    with pytest.raises(ContractError, match="lacks typed canonical_authority permission"):
        validate_canonical_authority(
            payload,
            inventory=inventory,
            catalog_payload=catalog,
            source_decisions=decisions,
        )

    staged = next(
        entry
        for entry in inventory_payload["entries"]
        if entry["source_id"] == "owner-local-release-snapshot-2023-2026-v1"
    )
    staged.update(
        {
            "access_permission_status": "approved",
            "benchmark_uses": ["family_context", "exact_variant_authority"],
            "content_license_status": "approved",
            "owner_decision": "approved",
            "privacy_review_status": "approved",
            "prospective_benchmark_use_status": "approved",
            "prospective_redistribution_status": "approved",
            "redistribution_scope": "public_rows",
            "retention_scope": "public",
        }
    )
    staged["owner_decision_metadata"]["unresolved_conditions"] = []
    with pytest.raises(ValidationError, match="ineligible sources"):
        validate_source_inventory(inventory_payload)

    payload = _authority_payload(catalog)
    payload["records"][0]["catalog_record_sha256"] = "0" * 64
    with pytest.raises(ContractError, match="stale catalog record checksum"):
        validate_canonical_authority(
            payload,
            inventory=inventory,
            catalog_payload=catalog,
            source_decisions=decisions,
        )


@pytest.mark.parametrize(
    "source_id",
    [
        "fixture-v1-benchmark",
        "fixture-v1-catalog",
        "human-labeled-real-noisy-v1",
        "human-labeled-to-fixture-alignment-v1",
        "owner-local-release-snapshot-2023-2026-v1",
        "fandom-hot-wheels-2025-pilot-r790665-v1",
    ],
)
def test_current_t1_sources_cannot_be_reclassified_as_exact_authority(source_id: str) -> None:
    payload = _json(DATA_DIR / "source-inventory.json")
    source = next(entry for entry in payload["entries"] if entry["source_id"] == source_id)
    source.update(
        {
            "access_permission_status": "approved",
            "authority_eligibility": "exact_variant_authority_candidate",
            "authority_evidence_level": "independent_exact_variant",
            "benchmark_uses": ["exact_variant_authority"],
            "content_license_status": "approved",
            "owner_decision": "approved",
            "privacy_review_status": "approved",
            "prospective_benchmark_use_status": "approved",
            "prospective_redistribution_status": "approved",
        }
    )
    source["owner_decision_metadata"]["unresolved_conditions"] = []

    with pytest.raises(ValidationError, match="new, explicit authorized_export"):
        validate_source_inventory(payload)


@pytest.mark.parametrize(
    "field",
    [
        "casting",
        "release_year",
        "series",
        "color",
        "collector_number",
        "series_position",
        "identifiers",
    ],
)
def test_approved_exact_requires_every_populated_variant_field(field: str) -> None:
    catalog = _catalog()
    inventory = validate_source_inventory(_approved_inventory_payload())
    payload = _authority_payload(catalog)
    payload["records"][0]["variant_fields_verified"].remove(field)
    decisions = _decisions_for_inventory(inventory)

    with pytest.raises(ContractError, match=field):
        validate_canonical_authority(
            payload,
            inventory=inventory,
            catalog_payload=catalog,
            source_decisions=decisions,
        )


def test_approved_exact_requires_edition_when_catalog_edition_is_populated() -> None:
    catalog = _catalog()
    catalog["products"][0]["edition"] = "Limited Edition"
    inventory = validate_source_inventory(_approved_inventory_payload())
    decisions = _decisions_for_inventory(inventory)
    payload = _authority_payload(catalog)

    with pytest.raises(ContractError, match="edition"):
        validate_canonical_authority(
            payload,
            inventory=inventory,
            catalog_payload=catalog,
            source_decisions=decisions,
        )


def test_label_status_uuid_and_exact_authority_rules() -> None:
    catalog, inventory, authority, queries, _, _, _ = _valid_contracts()
    decisions = _decisions_for_inventory(inventory)
    ambiguous = _label_payload(catalog)
    ambiguous["records"][0]["expected_status"] = "ambiguous"
    with pytest.raises(ValidationError, match="cannot carry canonical identity"):
        validate_labels(
            ambiguous,
            query_pack=queries,
            authority=authority,
            catalog_payload=catalog,
            inventory=inventory,
            source_decisions=decisions,
        )

    missing_authority = _label_payload(catalog)
    missing_authority["records"][0]["canonical_authority_id"] = "review-family-7"
    with pytest.raises(ContractError, match="lacks approved exact authority"):
        validate_labels(
            missing_authority,
            query_pack=queries,
            authority=authority,
            catalog_payload=catalog,
            inventory=inventory,
            source_decisions=decisions,
        )


def test_labels_revalidate_nested_authority_mutations() -> None:
    catalog, inventory, authority, queries, _, _, _ = _valid_contracts()
    authority.records[0].reviewed_by = "individual_reviewer"

    with pytest.raises(ContractError, match="role-only reviewer project_owner"):
        validate_labels(
            _label_payload(catalog),
            query_pack=queries,
            authority=authority,
            catalog_payload=catalog,
            inventory=inventory,
            source_decisions=_decisions_for_inventory(inventory),
        )


def test_public_authority_and_labels_reject_contact_pii_but_allow_urls() -> None:
    catalog = _catalog()
    inventory = validate_source_inventory(_approved_inventory_payload())
    decisions = _decisions_for_inventory(inventory)

    authority_payload = _authority_payload(catalog)
    authority_payload["records"][0]["reviewed_by"] = "person@example.com"
    with pytest.raises(ContractError, match="personal information"):
        validate_canonical_authority(
            authority_payload,
            inventory=inventory,
            catalog_payload=catalog,
            source_decisions=decisions,
        )

    authority_payload = _authority_payload(catalog)
    authority_payload["records"][0]["review_reason"] = "Call +1 (212) 555-0123"
    with pytest.raises(ContractError, match="personal information"):
        validate_canonical_authority(
            authority_payload,
            inventory=inventory,
            catalog_payload=catalog,
            source_decisions=decisions,
        )

    authority_payload = _authority_payload(catalog)
    authority_payload["records"][0]["independent_evidence_refs"] = [
        "https://example.com/releases/2022-101-555-0123"
    ]
    authority = validate_canonical_authority(
        authority_payload,
        inventory=inventory,
        catalog_payload=catalog,
        source_decisions=decisions,
    )
    queries = validate_query_pack(
        _query_pack_payload(), inventory=inventory, source_decisions=decisions
    )

    label_payload = _label_payload(catalog)
    label_payload["records"][0]["family_label"] = "person@example.com"
    with pytest.raises(ContractError, match="personal information"):
        validate_labels(
            label_payload,
            query_pack=queries,
            authority=authority,
            catalog_payload=catalog,
            inventory=inventory,
            source_decisions=decisions,
        )

    local_label_payload = _label_payload(catalog)
    local_label_payload["publication_scope"] = "local_only"
    local_label_payload["records"][0]["public_safe"] = False
    local_label_payload["records"][0]["review_reason"] = "Call +1 (212) 555-0123"
    assert (
        validate_labels(
            local_label_payload,
            query_pack=queries,
            authority=authority,
            catalog_payload=catalog,
            inventory=inventory,
            source_decisions=decisions,
        ).publication_scope
        == "local_only"
    )


def test_held_and_rejected_labels_cannot_be_score_eligible() -> None:
    catalog = _catalog()
    payload = _label_payload(catalog, review_status="held")
    payload["records"][0]["score_eligible"] = True

    with pytest.raises(ValidationError, match="cannot be score eligible"):
        _valid_contracts()[4].model_validate(payload)


def test_split_rejects_missing_cases_and_cross_family_leakage() -> None:
    inventory = validate_source_inventory(_approved_inventory_payload())
    decisions = _decisions_for_inventory(inventory)
    queries = validate_query_pack(
        _query_pack_payload(second_case=True),
        inventory=inventory,
        source_decisions=decisions,
    )
    missing = _split_payload()
    with pytest.raises(ContractError, match="every query"):
        validate_split(missing, query_pack=queries)

    leaking = _split_payload(second_case=True)
    leaking["records"][1]["split"] = "development"
    queries_payload = _query_pack_payload(second_case=True)
    queries_payload["cases"][1]["split"] = "development"
    queries = validate_query_pack(queries_payload, inventory=inventory, source_decisions=decisions)
    with pytest.raises(ContractError, match="family group crosses"):
        validate_split(leaking, query_pack=queries)


@pytest.mark.parametrize(
    "forbidden_key",
    ["expected_status", "target_rank", "is_correct", "aggregate_metrics", "winner"],
)
def test_test_raw_recursively_rejects_label_and_quality_fields(forbidden_key: str) -> None:
    catalog, _, _, queries, _, split, _ = _valid_contracts()
    payload = _raw_payload(catalog)
    payload["results"][0]["signals"][forbidden_key] = "leak"

    with pytest.raises(ContractError, match="forbidden field"):
        validate_label_blind_raw(payload, query_pack=queries, split=split)


def test_test_raw_rejects_partial_collection_and_wrong_order() -> None:
    catalog, _, _, queries, _, split, _ = _valid_contracts()
    partial = _raw_payload(catalog)
    partial["collection_status"] = "partial"
    with pytest.raises(ValidationError, match="complete"):
        validate_label_blind_raw(partial, query_pack=queries, split=split)

    second_inventory = validate_source_inventory(_approved_inventory_payload())
    second_queries = validate_query_pack(
        _query_pack_payload(second_case=True),
        inventory=second_inventory,
        source_decisions=_decisions_for_inventory(second_inventory),
    )
    second_split = validate_split(_split_payload(second_case=True), query_pack=second_queries)
    with pytest.raises(ContractError, match="order/count"):
        validate_label_blind_raw(
            _raw_payload(catalog), query_pack=second_queries, split=second_split
        )


def test_scored_results_reject_held_rows_and_raw_mutation() -> None:
    catalog, _, _, _, approved_labels, _, raw = _valid_contracts()
    product = catalog["products"][0]
    scored: dict[str, Any] = {
        "schema_version": "pvr-representative-hard-benchmark-scored-results-v1",
        "run_version": "run-v1",
        "scoring_status": "complete",
        "parent_checksums": {"test-raw.json": "4" * 64},
        "results": [
            {
                "case_id": "case-001",
                "expected_status": "matched",
                "expected_canonical_uuid": product["canonical_uuid"],
                "policy_status": "matched",
                "returned_canonical_uuid": product["canonical_uuid"],
                "target_ranks": {"rrf": 1},
                "decision_correct": True,
                "failure_type": "none",
                "calibration_target": 1,
                "numerator_contributions": {"correct_match": 1},
            }
        ],
        "metrics": {
            "precision": {"value": 1.0, "numerator": 1, "denominator": 1, "status": "measured"},
            "empty": {
                "value": None,
                "numerator": 0,
                "denominator": 0,
                "status": "not_applicable",
            },
        },
    }
    validate_scored_results(scored, raw=raw, labels=approved_labels)

    held_payload = _label_payload(catalog, review_status="held")
    held_labels = approved_labels.model_validate(held_payload)
    with pytest.raises(ContractError, match="cannot be scored"):
        validate_scored_results(scored, raw=raw, labels=held_labels)

    changed = copy.deepcopy(scored)
    changed["results"][0]["returned_canonical_uuid"] = None
    with pytest.raises(ContractError, match="changed its frozen raw decision"):
        validate_scored_results(changed, raw=raw, labels=approved_labels)


def test_manifest_rejects_stale_hash_parent_set_order_and_partial_state() -> None:
    artifact = {"records": [{"case_id": "case-001"}]}
    base = {
        "schema_version": "pvr-representative-hard-benchmark-manifest-v1",
        "artifact_version": "artifact-v1",
        "artifact_path": "query-pack.json",
        "artifact_sha256": content_sha256(artifact),
        "parent_artifacts": [{"path": "source.json", "sha256": "a" * 64}],
        "record_count": 1,
        "ordered_case_ids": ["case-001"],
        "counts": {"total": 1},
        "publication_scope": "public",
        "created_by": "benchmark-builder",
        "created_at": "2026-09-27T12:00:00Z",
        "status": "complete",
        "configuration_versions": {"resolver": "v1"},
        "model_versions": {"embedding": "hashing-v1"},
        "index_versions": {"catalog": "fixture-v1"},
    }
    validate_frozen_manifest(
        base,
        artifact_payload=artifact,
        ordered_case_ids=["case-001"],
        parent_checksums={"source.json": "a" * 64},
    )

    mutations = [
        ("artifact_sha256", "b" * 64, "checksum"),
        ("ordered_case_ids", ["case-002"], "order"),
        ("parent_artifacts", [], "parent"),
        ("status", "partial", "complete"),
    ]
    for field, value, message in mutations:
        changed = copy.deepcopy(base)
        changed[field] = value
        with pytest.raises((ContractError, ValidationError), match=message):
            validate_frozen_manifest(
                changed,
                artifact_payload=artifact,
                ordered_case_ids=["case-001"],
                parent_checksums={"source.json": "a" * 64},
            )


def test_contract_module_has_no_network_browser_or_runtime_import() -> None:
    source = (ROOT / "src" / "product_variant_resolver" / "representative_benchmark.py").read_text(
        encoding="utf-8"
    )
    forbidden = (
        "import requests",
        "import httpx",
        "import urllib",
        "import socket",
        "import selenium",
        "import playwright",
        "from .service",
        "from .api",
    )
    assert not any(token in source for token in forbidden)
