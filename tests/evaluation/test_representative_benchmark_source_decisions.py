from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from product_variant_resolver.canonical_authority_packet import (
    reconstruct_frozen_parent_catalog,
)
from product_variant_resolver.representative_benchmark import (
    CanonicalAuthorityArtifact,
    ContractError,
    QueryPack,
    SourceDecisionArtifact,
    canonical_record_sha256,
    validate_canonical_authority,
    validate_labels,
    validate_query_pack,
    validate_source_decisions,
    validate_source_inventory,
)

ROOT = Path(__file__).resolve().parents[2]
DECISIONS_PATH = ROOT / "data/evaluation/representative-hard-benchmark-v1/source-decisions.json"
INVENTORY_PATH = ROOT / "data/evaluation/representative-hard-benchmark-v1/source-inventory.json"
WIKI_SOURCE_PATH = ROOT / "data/external/hot-wheels-wiki/pilot-2025/normalized.json"

EXPECTED_USES = {
    "query_text",
    "evidence_retention",
    "reviewer_identity",
    "local_only_benchmark_use",
    "public_git_artifacts",
    "exact_variant_authority",
}
BLOCKED_EXTERNAL_SOURCES = {
    "live-ebay",
    "live-mercari",
    "live-facebook-marketplace",
    "live-fandom",
    "live-other-network-source",
}


def _load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _validate_decisions(
    artifact: dict[str, Any], inventory: dict[str, Any]
) -> SourceDecisionArtifact:
    return validate_source_decisions(
        artifact,
        inventory_payload=inventory,
        wiki_source_payload=_load(WIKI_SOURCE_PATH),
    )


def _query_payload(
    source_id: str,
    *,
    publication_scope: str = "local_only",
    source_record_ref: str | None = "local-ref",
    authored_by: str = "project_owner",
) -> dict[str, Any]:
    return {
        "schema_version": "pvr-representative-hard-benchmark-query-pack-v1",
        "dataset_version": "decision-overlay-test-v1",
        "publication_scope": publication_scope,
        "representative_pilot": False,
        "cases": [
            {
                "case_id": "case-overlay-001",
                "query": "owner-reviewed benchmark query",
                "source_id": source_id,
                "source_record_ref": source_record_ref,
                "public_safe": True,
                "family_group_key": "family-001",
                "evidence_event_group_key": "event-001",
                "challenge_tags": ["missing_metadata"],
                "authored_by": authored_by,
                "authored_at": "2026-09-27T01:44:16Z",
                "resolver_output_viewed": False,
                "split": "development",
            }
        ],
    }


def _label_payload(
    *,
    source_id: str,
    expected_status: str,
    publication_scope: str = "local_only",
    reviewed_by: str = "project_owner",
    expected_canonical_uuid: str | None = None,
    canonical_authority_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "pvr-representative-hard-benchmark-labels-v1",
        "dataset_version": "decision-overlay-test-v1",
        "publication_scope": publication_scope,
        "records": [
            {
                "case_id": "case-overlay-001",
                "expected_status": expected_status,
                "expected_canonical_uuid": expected_canonical_uuid,
                "canonical_authority_id": canonical_authority_id,
                "family_label": "owner-reviewed family context",
                "failure_type": "none",
                "hard_negative": False,
                "hard_negative_kind": None,
                "source_id": source_id,
                "evidence_refs": ["local-evidence-ref"],
                "review_status": "approved",
                "reviewed_by": reviewed_by,
                "reviewed_at": "2026-09-27T02:00:00Z",
                "review_reason": "Negative contract test only.",
                "public_safe": True,
                "score_eligible": True,
            }
        ],
    }


def _empty_authority() -> CanonicalAuthorityArtifact:
    return CanonicalAuthorityArtifact.model_validate(
        {
            "schema_version": "pvr-representative-hard-benchmark-canonical-authority-v1",
            "authority_version": "empty-authority-v1",
            "publication_scope": "local_only",
            "records": [],
        }
    )


def test_owner_confirmed_source_decisions_are_complete_and_fail_closed() -> None:
    artifact = _load(DECISIONS_PATH)
    inventory = _load(INVENTORY_PATH)
    validated = _validate_decisions(artifact, inventory)

    assert artifact["schema_version"] == ("pvr-representative-hard-benchmark-source-decisions-v1")
    assert artifact["decision_stage"] == "owner_confirmed"
    assert artifact["owner_review_status"] == "approved_for_declared_scopes"
    assert artifact["owner_confirmed_by"] == "project_owner"
    assert artifact["owner_confirmed_at"] == "2026-09-27T01:44:16Z"
    assert artifact["network_collection_authorized"] is False
    assert artifact["gate_result"] == "passed_for_approved_scopes"
    assert validated.inventory_sha256 == artifact["inventory_sha256"]
    assert artifact["reviewer_identity_policy"] == {
        "public_identity_mode": "role_only",
        "reviewer_role": "project_owner",
        "personal_name_allowed": False,
        "contact_or_account_data_allowed": False,
    }

    sources = artifact["sources"]
    assert isinstance(sources, list)
    source_by_id = {source["source_id"]: source for source in sources}
    assert len(source_by_id) == len(sources) == 11

    inventory_ids = {entry["source_id"] for entry in inventory["entries"]}
    decision_inventory_ids = {
        source["source_id"] for source in sources if source["source_origin"] == "inventory"
    }
    assert decision_inventory_ids == inventory_ids
    assert BLOCKED_EXTERNAL_SOURCES <= set(source_by_id)

    allowed_statuses = {"approved", "rejected", "held"}
    allowed_scopes = {"prohibited", "local_only", "aggregate_only", "public_rows"}
    for source in sources:
        decisions = source["decisions"]
        assert len(decisions) == len(EXPECTED_USES)
        assert {decision["use"] for decision in decisions} == EXPECTED_USES
        for decision in decisions:
            assert decision["status"] in allowed_statuses
            assert decision["effective_publication_scope"] in allowed_scopes
            assert isinstance(decision["allowed_fields"], list)
            assert decision["conditions"]
            if decision["owner_confirmation_required"]:
                assert decision["owner_confirmed"] is True

    all_decisions = [decision for source in sources for decision in source["decisions"]]
    assert sum(decision["status"] == "approved" for decision in all_decisions) == 23
    assert sum(decision["status"] == "rejected" for decision in all_decisions) == 43
    assert not any(decision["status"] == "held" for decision in all_decisions)

    for source_id in BLOCKED_EXTERNAL_SOURCES:
        source = source_by_id[source_id]
        assert source["source_origin"] == "blocked_external"
        assert all(decision["status"] == "rejected" for decision in source["decisions"])
        assert all(
            decision["effective_publication_scope"] == "prohibited"
            for decision in source["decisions"]
        )

    for source in sources:
        exact_decision = next(
            decision
            for decision in source["decisions"]
            if decision["use"] == "exact_variant_authority"
        )
        assert exact_decision["status"] == "rejected"


def test_owner_package_preserves_local_public_and_field_boundaries() -> None:
    artifact = _load(DECISIONS_PATH)
    source_by_id = {source["source_id"]: source for source in artifact["sources"]}

    def decision(source_id: str, use: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            next(item for item in source_by_id[source_id]["decisions"] if item["use"] == use),
        )

    human = "human-labeled-real-noisy-v1"
    assert decision(human, "query_text")["effective_publication_scope"] == "local_only"
    assert decision(human, "evidence_retention")["effective_publication_scope"] == "local_only"
    assert (
        decision(human, "public_git_artifacts")["effective_publication_scope"] == "aggregate_only"
    )

    alignment = "human-labeled-to-fixture-alignment-v1"
    assert (
        decision(alignment, "local_only_benchmark_use")["effective_publication_scope"]
        == "local_only"
    )
    assert (
        decision(alignment, "public_git_artifacts")["effective_publication_scope"]
        == "aggregate_only"
    )

    workbook = "owner-local-release-snapshot-2023-2026-v1"
    workbook_fields = {
        "product_name",
        "year",
        "series",
        "color",
        "collector_number",
        "series_position",
    }
    assert decision(workbook, "query_text")["status"] == "rejected"
    assert decision(workbook, "query_text")["allowed_fields"] == []
    assert set(decision(workbook, "evidence_retention")["allowed_fields"]) == (workbook_fields)
    assert set(decision(workbook, "local_only_benchmark_use")["allowed_fields"]) == (
        workbook_fields
    )
    assert (
        decision(workbook, "public_git_artifacts")["effective_publication_scope"]
        == "aggregate_only"
    )
    assert "seller" not in workbook_fields
    assert "contact" not in workbook_fields
    assert "account" not in workbook_fields

    wiki = "fandom-hot-wheels-2025-pilot-r790665-v1"
    assert decision(wiki, "query_text")["effective_publication_scope"] == "public_rows"
    assert "no_new_collection" in decision(wiki, "query_text")["conditions"]
    assert "attribution" in decision(wiki, "query_text")["allowed_fields"]

    for source_id in (human, workbook, wiki):
        reviewer = decision(source_id, "reviewer_identity")
        assert reviewer["allowed_fields"] == ["reviewer_role"]
        assert "role_only_project_owner" in reviewer["conditions"]


def test_confirmed_gate_still_blocks_collection_and_case_authoring() -> None:
    artifact = _load(DECISIONS_PATH)

    prohibited = set(artifact["prohibited_next_steps"])
    assert "network_collection" in prohibited
    assert "query_pack_authoring" in prohibited
    assert "label_authoring" in prohibited
    assert "RHB_T5" in prohibited
    assert artifact["next_allowed_step"] == ("RHB_T4_catalog_ground_truth_eligibility_audit")


def test_unknown_top_level_source_decision_field_is_rejected() -> None:
    artifact = _load(DECISIONS_PATH)
    artifact["silent_extra"] = "not allowed"

    with pytest.raises(ValidationError, match="silent_extra"):
        _validate_decisions(artifact, _load(INVENTORY_PATH))


def test_public_seller_email_allowlist_is_rejected() -> None:
    artifact = _load(DECISIONS_PATH)
    source = next(
        source
        for source in artifact["sources"]
        if source["source_id"] == "human-labeled-real-noisy-v1"
    )
    public_cell = next(
        cell for cell in source["decisions"] if cell["use"] == "public_git_artifacts"
    )
    public_cell["allowed_fields"].append("seller_email")

    with pytest.raises(ValidationError, match="seller_email"):
        _validate_decisions(artifact, _load(INVENTORY_PATH))


def test_rejected_exact_authority_cannot_expose_raw_public_fields() -> None:
    artifact = _load(DECISIONS_PATH)
    source = next(
        source
        for source in artifact["sources"]
        if source["source_id"] == "human-labeled-real-noisy-v1"
    )
    exact = next(cell for cell in source["decisions"] if cell["use"] == "exact_variant_authority")
    exact["effective_publication_scope"] = "public_rows"
    exact["allowed_fields"] = ["raw_query_evidence"]

    with pytest.raises(ValidationError, match="rejected/held"):
        _validate_decisions(artifact, _load(INVENTORY_PATH))


def test_stale_inventory_checksum_is_rejected() -> None:
    artifact = _load(DECISIONS_PATH)
    artifact["inventory_sha256"] = "0" * 64

    with pytest.raises(ContractError, match="stale source-inventory checksum"):
        _validate_decisions(artifact, _load(INVENTORY_PATH))


@pytest.mark.parametrize("mutation", ["missing", "duplicate"])
def test_each_source_requires_every_use_exactly_once(mutation: str) -> None:
    artifact = _load(DECISIONS_PATH)
    decisions = artifact["sources"][0]["decisions"]
    if mutation == "missing":
        decisions.pop()
    else:
        decisions.append(copy.deepcopy(decisions[0]))

    with pytest.raises(ValidationError, match="every source-decision use exactly once"):
        _validate_decisions(artifact, _load(INVENTORY_PATH))


def test_owner_approved_scope_cannot_be_escalated() -> None:
    artifact = _load(DECISIONS_PATH)
    source = next(
        source
        for source in artifact["sources"]
        if source["source_id"] == "human-labeled-real-noisy-v1"
    )
    query_cell = next(cell for cell in source["decisions"] if cell["use"] == "query_text")
    query_cell["effective_publication_scope"] = "public_rows"

    with pytest.raises(ContractError, match="changed the owner-approved status/scope"):
        _validate_decisions(artifact, _load(INVENTORY_PATH))


def test_regression_fixture_cannot_gain_query_permission_through_a_cell_mutation() -> None:
    artifact = _load(DECISIONS_PATH)
    source = next(
        source for source in artifact["sources"] if source["source_id"] == "fixture-v1-benchmark"
    )
    query_cell = next(cell for cell in source["decisions"] if cell["use"] == "query_text")
    query_cell.update(
        {
            "status": "approved",
            "effective_publication_scope": "public_rows",
            "allowed_fields": ["query_text"],
        }
    )

    with pytest.raises(ContractError, match="changed the owner-approved status/scope"):
        _validate_decisions(artifact, _load(INVENTORY_PATH))


def test_downstream_query_use_requires_owner_approved_decision() -> None:
    inventory_payload = _load(INVENTORY_PATH)
    inventory = validate_source_inventory(inventory_payload)
    decisions = _validate_decisions(_load(DECISIONS_PATH), inventory_payload)
    query_payload = {
        "schema_version": "pvr-representative-hard-benchmark-query-pack-v1",
        "dataset_version": "decision-overlay-test-v1",
        "publication_scope": "local_only",
        "representative_pilot": False,
        "cases": [
            {
                "case_id": "case-overlay-001",
                "query": "family-only alignment is not query evidence",
                "source_id": "human-labeled-to-fixture-alignment-v1",
                "source_record_ref": "digest-only-ref",
                "public_safe": False,
                "family_group_key": "family-001",
                "evidence_event_group_key": "event-001",
                "challenge_tags": ["missing_metadata"],
                "authored_by": "project_owner",
                "authored_at": "2026-09-27T01:44:16Z",
                "resolver_output_viewed": False,
                "split": "development",
            }
        ],
    }

    with pytest.raises(ContractError, match="lacks typed query_pack permission"):
        validate_query_pack(
            query_payload,
            inventory=inventory,
            source_decisions=decisions,
        )


def test_downstream_exact_authority_requires_owner_approved_decision() -> None:
    inventory_payload = _load(INVENTORY_PATH)
    inventory = validate_source_inventory(inventory_payload)
    decisions = _validate_decisions(_load(DECISIONS_PATH), inventory_payload)
    catalog = reconstruct_frozen_parent_catalog(ROOT)[0].model_dump(mode="json")
    product = catalog["products"][0]
    authority_payload = {
        "schema_version": "pvr-representative-hard-benchmark-canonical-authority-v1",
        "authority_version": "decision-overlay-test-v1",
        "publication_scope": "local_only",
        "records": [
            {
                "authority_id": "authority-overlay-001",
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
                "independent_evidence_refs": ["local-evidence-ref"],
                "evidence_source_ids": ["human-labeled-real-noisy-v1"],
                "resolver_output_consulted": False,
                "reviewed_by": "project_owner",
                "reviewed_at": "2026-09-27T01:44:16Z",
                "review_reason": "Negative contract test only.",
                "status": "approved_exact",
            }
        ],
    }

    with pytest.raises(ContractError, match="lacks typed canonical_authority permission"):
        validate_canonical_authority(
            authority_payload,
            inventory=inventory,
            catalog_payload=catalog,
            source_decisions=decisions,
        )


def test_public_human_labels_cannot_bypass_aggregate_only_git_scope() -> None:
    inventory_payload = _load(INVENTORY_PATH)
    inventory = validate_source_inventory(inventory_payload)
    decisions = _validate_decisions(_load(DECISIONS_PATH), inventory_payload)
    query_payload = {
        "schema_version": "pvr-representative-hard-benchmark-query-pack-v1",
        "dataset_version": "decision-overlay-test-v1",
        "publication_scope": "local_only",
        "representative_pilot": False,
        "cases": [
            {
                "case_id": "case-overlay-label-001",
                "query": "local human query",
                "source_id": "human-labeled-real-noisy-v1",
                "source_record_ref": "local-ref",
                "public_safe": True,
                "family_group_key": "family-001",
                "evidence_event_group_key": "event-001",
                "challenge_tags": ["missing_metadata"],
                "authored_by": "project_owner",
                "authored_at": "2026-09-27T01:44:16Z",
                "resolver_output_viewed": False,
                "split": "development",
            }
        ],
    }
    query_pack = validate_query_pack(
        query_payload,
        inventory=inventory,
        source_decisions=decisions,
    )
    authority = CanonicalAuthorityArtifact.model_validate(
        {
            "schema_version": "pvr-representative-hard-benchmark-canonical-authority-v1",
            "authority_version": "empty-authority-v1",
            "publication_scope": "local_only",
            "records": [],
        }
    )
    label_payload = {
        "schema_version": "pvr-representative-hard-benchmark-labels-v1",
        "dataset_version": "decision-overlay-test-v1",
        "publication_scope": "public",
        "records": [
            {
                "case_id": "case-overlay-label-001",
                "expected_status": "ambiguous",
                "expected_canonical_uuid": None,
                "canonical_authority_id": None,
                "family_label": "family context",
                "failure_type": "none",
                "hard_negative": False,
                "hard_negative_kind": None,
                "source_id": "human-labeled-real-noisy-v1",
                "evidence_refs": ["local-evidence-ref"],
                "review_status": "approved",
                "reviewed_by": "project_owner",
                "reviewed_at": "2026-09-27T02:00:00Z",
                "review_reason": "Negative publication contract test only.",
                "public_safe": True,
                "score_eligible": True,
            }
        ],
    }

    with pytest.raises(ContractError, match="cannot satisfy public_rows scope"):
        validate_labels(
            label_payload,
            query_pack=query_pack,
            authority=authority,
            catalog_payload=_load(ROOT / "data/catalog.json"),
            inventory=inventory,
            source_decisions=decisions,
        )


def test_canonical_authority_cannot_omit_owner_decisions() -> None:
    inventory = validate_source_inventory(_load(INVENTORY_PATH))

    with pytest.raises(TypeError, match="source_decisions"):
        cast(Any, validate_canonical_authority)(
            {
                "schema_version": ("pvr-representative-hard-benchmark-canonical-authority-v1"),
                "authority_version": "omission-test-v1",
                "publication_scope": "local_only",
                "records": [],
            },
            inventory=inventory,
            catalog_payload=_load(ROOT / "data/catalog.json"),
        )


def test_query_pack_cannot_omit_owner_decisions() -> None:
    inventory = validate_source_inventory(_load(INVENTORY_PATH))

    with pytest.raises(TypeError, match="source_decisions"):
        cast(Any, validate_query_pack)(
            _query_payload("human-labeled-real-noisy-v1"),
            inventory=inventory,
        )


def test_labels_cannot_omit_owner_decisions() -> None:
    inventory_payload = _load(INVENTORY_PATH)
    inventory = validate_source_inventory(inventory_payload)
    decisions = _validate_decisions(_load(DECISIONS_PATH), inventory_payload)
    query_pack = validate_query_pack(
        _query_payload("human-labeled-real-noisy-v1"),
        inventory=inventory,
        source_decisions=decisions,
    )

    with pytest.raises(TypeError, match="source_decisions"):
        cast(Any, validate_labels)(
            _label_payload(
                source_id="human-labeled-real-noisy-v1",
                expected_status="ambiguous",
            ),
            query_pack=query_pack,
            authority=_empty_authority(),
            catalog_payload=_load(ROOT / "data/catalog.json"),
            inventory=inventory,
        )


def test_labels_revalidate_a_preconstructed_public_human_query_pack() -> None:
    inventory_payload = _load(INVENTORY_PATH)
    inventory = validate_source_inventory(inventory_payload)
    decisions = _validate_decisions(_load(DECISIONS_PATH), inventory_payload)
    bypass_query_pack = QueryPack.model_validate(
        _query_payload(
            "human-labeled-real-noisy-v1",
            publication_scope="public",
            source_record_ref="private-human-row-ref",
            authored_by="individual_reviewer",
        )
    )

    with pytest.raises(ContractError, match="cannot satisfy public_rows scope"):
        validate_labels(
            _label_payload(
                source_id="human-labeled-real-noisy-v1",
                expected_status="ambiguous",
            ),
            query_pack=bypass_query_pack,
            authority=_empty_authority(),
            catalog_payload=_load(ROOT / "data/catalog.json"),
            inventory=inventory,
            source_decisions=decisions,
        )


def test_labels_revalidate_nested_query_mutations() -> None:
    inventory_payload = _load(INVENTORY_PATH)
    inventory = validate_source_inventory(inventory_payload)
    decisions = _validate_decisions(_load(DECISIONS_PATH), inventory_payload)
    query_pack = validate_query_pack(
        _query_payload("human-labeled-real-noisy-v1"),
        inventory=inventory,
        source_decisions=decisions,
    )
    query_pack.cases[0].authored_by = "individual_reviewer"

    with pytest.raises(ContractError, match="role-only author project_owner"):
        validate_labels(
            _label_payload(
                source_id="human-labeled-real-noisy-v1",
                expected_status="ambiguous",
            ),
            query_pack=query_pack,
            authority=_empty_authority(),
            catalog_payload=_load(ROOT / "data/catalog.json"),
            inventory=inventory,
            source_decisions=decisions,
        )


def test_mutated_inventory_cannot_elevate_a_current_source() -> None:
    inventory_payload = _load(INVENTORY_PATH)
    decisions = _validate_decisions(_load(DECISIONS_PATH), inventory_payload)
    elevated_payload = copy.deepcopy(inventory_payload)
    human = next(
        entry
        for entry in elevated_payload["entries"]
        if entry["source_id"] == "human-labeled-real-noisy-v1"
    )
    human["source_kind"] = "authorized_export"
    human["authority_eligibility"] = "exact_variant_authority_candidate"
    human["authority_evidence_level"] = "independent_exact_variant"
    human["benchmark_uses"] = ["exact_variant_authority"]
    inventory = validate_source_inventory(elevated_payload)

    with pytest.raises(ContractError, match="changed inventory authority eligibility"):
        validate_query_pack(
            _query_payload("human-labeled-real-noisy-v1"),
            inventory=inventory,
            source_decisions=decisions,
        )


def test_queries_require_project_owner_as_role_only_author() -> None:
    inventory_payload = _load(INVENTORY_PATH)
    inventory = validate_source_inventory(inventory_payload)
    decisions = _validate_decisions(_load(DECISIONS_PATH), inventory_payload)

    with pytest.raises(ContractError, match="role-only author project_owner"):
        validate_query_pack(
            _query_payload(
                "human-labeled-real-noisy-v1",
                authored_by="individual_reviewer",
            ),
            inventory=inventory,
            source_decisions=decisions,
        )


def test_labels_require_project_owner_as_role_only_reviewer() -> None:
    inventory_payload = _load(INVENTORY_PATH)
    inventory = validate_source_inventory(inventory_payload)
    decisions = _validate_decisions(_load(DECISIONS_PATH), inventory_payload)
    query_pack = validate_query_pack(
        _query_payload("human-labeled-real-noisy-v1"),
        inventory=inventory,
        source_decisions=decisions,
    )

    with pytest.raises(ContractError, match="role-only reviewer project_owner"):
        validate_labels(
            _label_payload(
                source_id="human-labeled-real-noisy-v1",
                expected_status="ambiguous",
                reviewed_by="individual_reviewer",
            ),
            query_pack=query_pack,
            authority=_empty_authority(),
            catalog_payload=_load(ROOT / "data/catalog.json"),
            inventory=inventory,
            source_decisions=decisions,
        )


def test_authority_requires_project_owner_as_role_only_reviewer() -> None:
    inventory_payload = _load(INVENTORY_PATH)
    inventory = validate_source_inventory(inventory_payload)
    decisions = _validate_decisions(_load(DECISIONS_PATH), inventory_payload)
    catalog = _load(ROOT / "data/catalog.json")
    product = catalog["products"][0]
    payload = {
        "schema_version": "pvr-representative-hard-benchmark-canonical-authority-v1",
        "authority_version": "reviewer-role-test-v1",
        "publication_scope": "local_only",
        "records": [
            {
                "authority_id": "authority-overlay-001",
                "canonical_uuid": product["canonical_uuid"],
                "canonical_catalog_version": catalog["catalog_version"],
                "catalog_record_sha256": canonical_record_sha256(product),
                "variant_fields_verified": ["casting"],
                "independent_evidence_refs": ["local-evidence-ref"],
                "evidence_source_ids": ["human-labeled-real-noisy-v1"],
                "resolver_output_consulted": False,
                "reviewed_by": "individual_reviewer",
                "reviewed_at": "2026-09-27T02:00:00Z",
                "review_reason": "Negative role-only contract test.",
                "status": "insufficient",
            }
        ],
    }

    with pytest.raises(ContractError, match="role-only reviewer project_owner"):
        validate_canonical_authority(
            payload,
            inventory=inventory,
            catalog_payload=catalog,
            source_decisions=decisions,
        )


def test_wiki_query_reference_must_belong_to_the_bound_100_row_revision() -> None:
    inventory_payload = _load(INVENTORY_PATH)
    inventory = validate_source_inventory(inventory_payload)
    decisions = _validate_decisions(_load(DECISIONS_PATH), inventory_payload)
    wiki_payload = _load(WIKI_SOURCE_PATH)
    approved_ref = cast(str, wiki_payload["records"][0]["source_record_id"])
    valid_payload = _query_payload(
        "fandom-hot-wheels-2025-pilot-r790665-v1",
        publication_scope="public",
        source_record_ref=approved_ref,
    )

    validate_query_pack(valid_payload, inventory=inventory, source_decisions=decisions)
    invalid_payload = copy.deepcopy(valid_payload)
    invalid_payload["cases"][0]["source_record_ref"] = "fandom-row-not-in-revision"
    with pytest.raises(ContractError, match="outside the approved 100-row revision"):
        validate_query_pack(
            invalid_payload,
            inventory=inventory,
            source_decisions=decisions,
        )


def test_wiki_public_query_cannot_become_an_ambiguous_scored_label() -> None:
    inventory_payload = _load(INVENTORY_PATH)
    inventory = validate_source_inventory(inventory_payload)
    decisions = _validate_decisions(_load(DECISIONS_PATH), inventory_payload)
    wiki_payload = _load(WIKI_SOURCE_PATH)
    approved_ref = cast(str, wiki_payload["records"][0]["source_record_id"])
    query_pack = validate_query_pack(
        _query_payload(
            "fandom-hot-wheels-2025-pilot-r790665-v1",
            publication_scope="public",
            source_record_ref=approved_ref,
        ),
        inventory=inventory,
        source_decisions=decisions,
    )

    with pytest.raises(ContractError, match="lacks typed scored_labels permission"):
        validate_labels(
            _label_payload(
                source_id="fandom-hot-wheels-2025-pilot-r790665-v1",
                expected_status="ambiguous",
                publication_scope="public",
            ),
            query_pack=query_pack,
            authority=_empty_authority(),
            catalog_payload=_load(ROOT / "data/catalog.json"),
            inventory=inventory,
            source_decisions=decisions,
        )


def test_workbook_family_context_cannot_reach_the_labels_gate() -> None:
    inventory_payload = _load(INVENTORY_PATH)
    inventory = validate_source_inventory(inventory_payload)
    decisions = _validate_decisions(_load(DECISIONS_PATH), inventory_payload)
    # Low-level schema construction is intentional: the query validator already rejects
    # workbook rows. This isolates and proves the independent labels gate also fails closed.
    query_pack = QueryPack.model_validate(
        _query_payload("owner-local-release-snapshot-2023-2026-v1")
    )

    with pytest.raises(ContractError, match="lacks typed query_pack permission"):
        validate_labels(
            _label_payload(
                source_id="owner-local-release-snapshot-2023-2026-v1",
                expected_status="no_match",
            ),
            query_pack=query_pack,
            authority=_empty_authority(),
            catalog_payload=_load(ROOT / "data/catalog.json"),
            inventory=inventory,
            source_decisions=decisions,
        )


def test_human_source_cannot_produce_matched_labels() -> None:
    inventory_payload = _load(INVENTORY_PATH)
    inventory = validate_source_inventory(inventory_payload)
    decisions = _validate_decisions(_load(DECISIONS_PATH), inventory_payload)
    query_pack = validate_query_pack(
        _query_payload("human-labeled-real-noisy-v1"),
        inventory=inventory,
        source_decisions=decisions,
    )
    product = _load(ROOT / "data/catalog.json")["products"][0]

    with pytest.raises(ContractError, match="cannot produce matched labels"):
        validate_labels(
            _label_payload(
                source_id="human-labeled-real-noisy-v1",
                expected_status="matched",
                expected_canonical_uuid=cast(str, product["canonical_uuid"]),
                canonical_authority_id="authority-not-approved",
            ),
            query_pack=query_pack,
            authority=_empty_authority(),
            catalog_payload=_load(ROOT / "data/catalog.json"),
            inventory=inventory,
            source_decisions=decisions,
        )
