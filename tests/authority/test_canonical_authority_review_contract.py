from __future__ import annotations

import ast
import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from product_variant_resolver.canonical_authority_review import (
    AuthorityBundle,
    AuthorityBundleManifest,
    AuthorityCandidate,
    AuthorityContractError,
    AuthorityReviewEvent,
    CatalogRecordProposal,
    OwnerReviewPacket,
    VariantFieldEvidence,
    authority_bundle_parent_artifacts,
    content_sha256,
    validate_authority_bundle,
    validate_authority_candidate,
    validate_authority_source_decisions,
    validate_catalog_record_proposal,
    validate_owner_review_packet,
    validate_review_event_chain,
)

ROOT = Path(__file__).resolve().parents[2]
NORMALIZED = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025" / "normalized.json"
SHA_A = "a" * 64
SHA_B = "b" * 64
UUID_A = "11111111-1111-4111-8111-111111111111"
UUID_B = "22222222-2222-4222-8222-222222222222"


def _source_record_id() -> str:
    payload = json.loads(NORMALIZED.read_text(encoding="utf-8"))
    return str(payload["records"][0]["source_record_id"])


def _binding(source_record_id: str | None = None) -> dict[str, Any]:
    return {
        "source_id": "fandom-hot-wheels-2025-pilot-r790665-v1",
        "source_kind": "licensed_community_snapshot",
        "claim_tier": "community_reference_snapshot_exact",
        "source_page_title": "List of 2025 Hot Wheels",
        "source_page_url": (
            "https://hotwheels.fandom.com/wiki/List_of_2025_Hot_Wheels?oldid=790665"
        ),
        "source_revision_id": 790665,
        "source_revision_timestamp": "2026-07-17T05:50:26Z",
        "source_record_id": source_record_id or _source_record_id(),
        "normalized_snapshot_sha256": (
            "e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6"
        ),
        "license_name": "CC-BY-SA",
        "license_url": "https://www.fandom.com/licensing",
        "attribution": (
            "Source: Hot Wheels Wiki contributors, List of 2025 Hot Wheels, revision 790665; "
            "normalized derivative."
        ),
        "share_alike_required": True,
    }


def _candidate(*, existing_uuid: bool = True) -> dict[str, Any]:
    return {
        "schema_version": "pvr-canonical-authority-candidate-v1",
        "candidate_id": "candidate-001",
        "source_binding": _binding(),
        "family_group_key": "family-miata",
        "proposed_release_key": "release-2025-hyw18",
        "selection_context_refs": ["family-context:miata"],
        "selection_context_role": "candidate_selection_only",
        "catalog_lookup_state": "existing_uuid" if existing_uuid else "catalog_review_required",
        "canonical_uuid": UUID_A if existing_uuid else None,
        "resolver_output_consulted": False,
        "synthetic": False,
        "status": "staged",
    }


def _product() -> dict[str, Any]:
    return {
        "canonical_uuid": UUID_A,
        "casting": "Mazda MX-5 Miata",
        "release_year": 2025,
        "series": "HW Dream Garage",
        "color": None,
        "collector_number": "001",
        "series_position": "2/5",
        "edition": None,
        "identifiers": ["HYW18"],
        "family_group_key": "family-miata",
        "release_key": "release-2025-hyw18",
        "synthetic": False,
    }


def _catalog_parent() -> dict[str, Any]:
    product = _product()
    return {
        "schema_version": "pvr-canonical-authority-frozen-catalog-v1",
        "catalog_version": "catalog-v1",
        "products": [
            {
                "canonical_id": "hot-wheels-miata-2025-hyw18",
                "canonical_uuid": UUID_A,
                "record": product,
                "record_sha256": content_sha256(product),
            }
        ],
    }


def _catalog_sha() -> str:
    return content_sha256(_catalog_parent())


def _evidence() -> list[dict[str, Any]]:
    rows = [
        ("casting", "casting_name", "Mazda MX-5 Miata"),
        ("release_year", "release_year", 2025),
        ("series", "series", "HW Dream Garage"),
        ("collector_number", "collector_number", "001"),
        ("series_position", "series_position", "2/5"),
        ("identifiers", "toy_number", ["HYW18"]),
    ]
    return [
        {
            "schema_version": "pvr-canonical-authority-field-evidence-v1",
            "field": field,
            "source_field": source_field,
            "catalog_value": value,
            "reviewed_value": value,
            "evidence_refs": [f"evidence:{field}"],
            "source_bindings": [_binding()],
            "agreement": "agrees",
            "notes": None,
        }
        for field, source_field, value in rows
    ]


def _proposal(*, status: str = "approved") -> dict[str, Any]:
    product = _product()
    product["canonical_uuid"] = UUID_B
    reviewed = status != "staged"
    return {
        "schema_version": "pvr-canonical-catalog-record-proposal-v1",
        "proposal_id": "proposal-001",
        "candidate_id": "candidate-001",
        "parent_catalog_version": "catalog-v1",
        "parent_catalog_sha256": _catalog_sha(),
        "proposed_canonical_uuid": UUID_B,
        "proposed_product_record": product,
        "product_record_sha256": content_sha256(product),
        "source_decision_ids": ["fandom-hot-wheels-2025-pilot-r790665-v1"],
        "field_evidence": _evidence(),
        "review_status": status,
        "reviewed_by_role": "project_owner" if reviewed else None,
        "reviewed_at": "2026-09-28T10:00:00Z" if reviewed else None,
        "review_reason": "Evidence and product fields agree." if reviewed else None,
        "authority_approved": False,
    }


def _event(
    event_id: str,
    from_status: str,
    to_status: str,
    reviewed_at: str,
) -> dict[str, Any]:
    negative = to_status in {"held", "conflicted", "insufficient", "revoked"}
    event = {
        "schema_version": "pvr-canonical-authority-review-event-v1",
        "event_id": event_id,
        "candidate_id": "candidate-001",
        "from_status": from_status,
        "to_status": to_status,
        "packet_sha256": SHA_B,
        "catalog_version": "catalog-v1",
        "catalog_sha256": _catalog_sha(),
        "canonical_uuid": UUID_A,
        "catalog_record_sha256": content_sha256(_product()),
        "variant_field_evidence": _evidence(),
        "source_decision_ids": ["fandom-hot-wheels-2025-pilot-r790665-v1"],
        "confirmation_method": "owner_attestation",
        "attestation_sha256": "c" * 64,
        "resolver_output_consulted": False,
        "reviewed_by_role": "project_owner",
        "reviewed_at": reviewed_at,
        "review_reason": "Owner completed an output-blind evidence review.",
        "remediation_note": "Create a new version before reuse." if negative else None,
    }
    event["attestation_sha256"] = content_sha256(_attestation(event))
    return event


def _attestation(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "pvr-canonical-authority-owner-attestation-v1",
        "candidate_id": event["candidate_id"],
        "packet_sha256": event["packet_sha256"],
        "catalog_version": event["catalog_version"],
        "catalog_sha256": event["catalog_sha256"],
        "catalog_record_sha256": event["catalog_record_sha256"],
        "outcome": event["to_status"],
        "confirmation_method": "owner_attestation",
        "resolver_output_consulted": False,
        "reviewed_by_role": "project_owner",
        "reviewed_at": event["reviewed_at"],
        "review_reason": event["review_reason"],
    }


def _attestations(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {event["event_id"]: _attestation(event) for event in events}


def _proposal_events() -> list[dict[str, Any]]:
    proposal = _proposal()
    events = _bundle_events("approved_exact")
    for event in events:
        event["canonical_uuid"] = UUID_B
        event["catalog_record_sha256"] = proposal["product_record_sha256"]
        event["attestation_sha256"] = content_sha256(_attestation(event))
    return events


def test_source_gate_is_reused_and_exposes_only_the_fixed_membership() -> None:
    context = validate_authority_source_decisions(ROOT)

    assert context.source_id == "fandom-hot-wheels-2025-pilot-r790665-v1"
    assert len(context.source_record_ids) == 100


def test_candidate_rejects_unknown_fields_output_consultation_and_unapproved_row() -> None:
    unknown = _candidate()
    unknown["predicted_winner"] = UUID_A
    with pytest.raises(ValidationError, match="Extra inputs"):
        AuthorityCandidate.model_validate(unknown)

    consulted = _candidate()
    consulted["resolver_output_consulted"] = True
    with pytest.raises(ValidationError):
        AuthorityCandidate.model_validate(consulted)

    foreign = _candidate()
    foreign["source_binding"]["source_record_id"] = "fandom-row-does-not-exist"
    with pytest.raises(AuthorityContractError, match="outside the approved 100-row"):
        validate_authority_candidate(foreign, root=ROOT)


def test_candidate_requires_catalog_review_when_uuid_is_absent() -> None:
    invalid = _candidate(existing_uuid=False)
    invalid["catalog_lookup_state"] = "existing_uuid"
    with pytest.raises(ValidationError, match="missing UUID requires catalog review"):
        AuthorityCandidate.model_validate(invalid)

    assert (
        validate_authority_candidate(_candidate(existing_uuid=False), root=ROOT).canonical_uuid
        is None
    )


def test_field_evidence_rejects_wrong_mapping_color_inference_and_duplicates() -> None:
    wrong = _evidence()[0]
    wrong["source_field"] = "toy_number"
    with pytest.raises(ValidationError, match="not approved"):
        VariantFieldEvidence.model_validate(wrong)

    color = _evidence()[0]
    color.update(
        field="color", source_field="casting_name", catalog_value="red", reviewed_value="red"
    )
    with pytest.raises(ValidationError):
        VariantFieldEvidence.model_validate(color)

    duplicate = _evidence()[0]
    duplicate["evidence_refs"] = ["evidence:casting", "evidence:casting"]
    with pytest.raises(ValidationError, match="unique"):
        VariantFieldEvidence.model_validate(duplicate)


def test_catalog_proposal_rejects_stale_hash_parent_and_auto_authority() -> None:
    stale = _proposal()
    stale["product_record_sha256"] = SHA_B
    with pytest.raises(ValidationError, match="checksum is stale"):
        CatalogRecordProposal.model_validate(stale)

    auto = _proposal()
    auto["authority_approved"] = True
    with pytest.raises(ValidationError):
        CatalogRecordProposal.model_validate(auto)

    with pytest.raises(AuthorityContractError, match="parent version is stale"):
        validate_catalog_record_proposal(
            _proposal(),
            root=ROOT,
            candidate_payload=_candidate(existing_uuid=False),
            catalog_parent_payload={**_catalog_parent(), "catalog_version": "other"},
        )


def test_approved_catalog_proposal_requires_every_nonempty_catalog_field() -> None:
    incomplete = _proposal()
    incomplete["field_evidence"].pop()
    with pytest.raises(ValidationError, match="coverage differs"):
        CatalogRecordProposal.model_validate(incomplete)


def test_owner_packet_is_local_only_output_blind_complete_and_pii_free() -> None:
    packet: dict[str, Any] = {
        "schema_version": "pvr-canonical-authority-owner-review-packet-v1",
        "packet_version": "packet-v1",
        "publication_scope": "local_only_git_ignored",
        "source_decisions_sha256": validate_authority_source_decisions(
            ROOT
        ).source_decisions_sha256,
        "catalog_version": "catalog-v1",
        "catalog_sha256": _catalog_sha(),
        "candidates": [_candidate()],
        "field_evidence": {"candidate-001": _evidence()},
        "owner_questions": {"candidate-001": ["Does each visible field agree?"]},
        "missing_or_conflicting_items": {"candidate-001": []},
        "resolver_output_consulted": False,
        "resolver_output_included": False,
        "predicted_uuid_included": False,
        "model_scores_included": False,
        "network_requests": 0,
    }
    assert (
        validate_owner_review_packet(
            packet, root=ROOT, catalog_parent_payload=_catalog_parent()
        ).network_requests
        == 0
    )

    leaked = copy.deepcopy(packet)
    leaked["owner_questions"]["candidate-001"] = ["Ask owner@example.com"]
    with pytest.raises(ValidationError, match="email-like"):
        OwnerReviewPacket.model_validate(leaked)


def test_review_events_forbid_direct_approval_and_require_attestation_metadata() -> None:
    direct = _event("event-001", "staged", "approved_exact", "2026-09-28T10:00:00Z")
    with pytest.raises(ValidationError, match="invalid authority transition"):
        AuthorityReviewEvent.model_validate(direct)

    blank_reason = _event("event-001", "staged", "reviewed", "2026-09-28T10:00:00Z")
    blank_reason["review_reason"] = " "
    with pytest.raises(ValidationError):
        AuthorityReviewEvent.model_validate(blank_reason)


def test_review_chain_is_append_only_and_existing_uuid_can_be_approved() -> None:
    events = [
        _event("event-001", "staged", "reviewed", "2026-09-28T10:00:00Z"),
        _event("event-002", "reviewed", "approved_exact", "2026-09-28T10:01:00Z"),
    ]
    validated = validate_review_event_chain(
        _candidate(),
        events,
        root=ROOT,
        catalog_record=_product(),
        attestations=_attestations(events),
        expected_packet_sha256=SHA_B,
        catalog_parent_payload=_catalog_parent(),
    )
    assert validated[-1].to_status.value == "approved_exact"

    broken = copy.deepcopy(events)
    broken[1]["from_status"] = "held"
    broken[1]["to_status"] = "reviewed"
    with pytest.raises(AuthorityContractError, match="append-only"):
        validate_review_event_chain(
            _candidate(),
            broken,
            root=ROOT,
            catalog_record=_product(),
            attestations=_attestations(broken),
            expected_packet_sha256=SHA_B,
            catalog_parent_payload=_catalog_parent(),
        )


def test_review_chain_rejects_stale_packet_and_attestation_hashes() -> None:
    events = [
        _event("event-001", "staged", "reviewed", "2026-09-28T10:00:00Z"),
        _event("event-002", "reviewed", "approved_exact", "2026-09-28T10:01:00Z"),
    ]
    with pytest.raises(AuthorityContractError, match="packet checksum is stale"):
        validate_review_event_chain(
            _candidate(),
            events,
            root=ROOT,
            catalog_record=_product(),
            attestations=_attestations(events),
            expected_packet_sha256=SHA_A,
            catalog_parent_payload=_catalog_parent(),
        )

    attestations = _attestations(events)
    attestations["event-002"]["review_reason"] = "A different owner decision."
    with pytest.raises(AuthorityContractError, match="attestation checksum is stale"):
        validate_review_event_chain(
            _candidate(),
            events,
            root=ROOT,
            catalog_record=_product(),
            attestations=attestations,
            expected_packet_sha256=SHA_B,
            catalog_parent_payload=_catalog_parent(),
        )


def test_missing_uuid_requires_separate_approved_catalog_proposal() -> None:
    events = [
        _event("event-001", "staged", "reviewed", "2026-09-28T10:00:00Z"),
        _event("event-002", "reviewed", "approved_exact", "2026-09-28T10:01:00Z"),
    ]
    with pytest.raises(AuthorityContractError, match="separately approved catalog proposal"):
        validate_review_event_chain(
            _candidate(existing_uuid=False),
            events,
            root=ROOT,
            catalog_record=_product(),
            attestations=_attestations(events),
            expected_packet_sha256=SHA_B,
            catalog_parent_payload=_catalog_parent(),
        )

    proposal_events = _proposal_events()
    validated = validate_review_event_chain(
        _candidate(existing_uuid=False),
        proposal_events,
        root=ROOT,
        approved_catalog_proposal=_proposal(),
        attestations=_attestations(proposal_events),
        expected_packet_sha256=SHA_B,
        catalog_parent_payload=_catalog_parent(),
    )
    assert len(validated) == 2


def test_preconstructed_models_are_revalidated_at_high_level_boundaries() -> None:
    valid = AuthorityCandidate.model_validate(_candidate())
    unsafe = AuthorityCandidate.model_construct(**valid.__dict__)
    unsafe.__dict__["resolver_output_consulted"] = True
    with pytest.raises(ValidationError):
        validate_authority_candidate(unsafe, root=ROOT)


def _bundle(status: str = "approved_exact") -> dict[str, Any]:
    return {
        "schema_version": "pvr-canonical-authority-bundle-v1",
        "bundle_version": "authority-bundle-v1",
        "records": [
            {
                "candidate_id": "candidate-001",
                "canonical_uuid": UUID_A,
                "family_group_key": "family-miata",
                "release_key": "release-2025-hyw18",
                "status": status,
                "synthetic": False,
                "latest_event_id": "event-003" if status == "revoked" else "event-002",
                "catalog_version": "catalog-v1",
                "catalog_record_sha256": content_sha256(_product()),
                "source_decision_ids": ["fandom-hot-wheels-2025-pilot-r790665-v1"],
                "evidence_sha256s": sorted(content_sha256(row) for row in _evidence()),
            }
        ],
        "resolver_output_consulted": False,
        "network_requests": 0,
        "rhb_t5_authorized": False,
    }


def _bundle_inputs(events: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "root": ROOT,
        "candidate_payloads": {"candidate-001": _candidate()},
        "catalog_records": {"candidate-001": _product()},
        "catalog_proposals": {},
        "review_events": events,
        "attestations": _attestations(events),
        "packet_sha256s": {"candidate-001": SHA_B},
        "catalog_parent_payload": _catalog_parent(),
    }


def _manifest(
    bundle: dict[str, Any],
    events: list[dict[str, Any]],
    status: str = "approved_exact",
) -> dict[str, Any]:
    counts = {
        name: int(name == status)
        for name in (
            "staged",
            "reviewed",
            "approved_exact",
            "conflicted",
            "insufficient",
            "held",
            "revoked",
        )
    }
    approved = status == "approved_exact"
    return {
        "schema_version": "pvr-canonical-authority-bundle-manifest-v1",
        "bundle_version": "authority-bundle-v1",
        "authority_bundle_sha256": content_sha256(bundle),
        "ordered_parent_artifacts": [
            item.model_dump(mode="json")
            for item in authority_bundle_parent_artifacts(**_bundle_inputs(events))
        ],
        "catalog_version": "catalog-v1",
        "catalog_sha256": _catalog_sha(),
        "source_decision_sha256s": [
            validate_authority_source_decisions(ROOT).source_decisions_sha256
        ],
        "counts_by_status": counts,
        "approved_distinct_variant_count": 1 if approved else 0,
        "qualifying_family_count": 0,
        "family_composition": [],
        "resolver_output_consulted": False,
        "network_requests": 0,
        "publication_scope": "safe_metadata_only",
        "gate_status": "blocked_insufficient_exact_authority",
        "shortfalls": {
            "exact_variant_shortfall": 19 if approved else 20,
            "qualifying_family_shortfall": 4,
        },
        "created_at": datetime(2026, 9, 28, tzinfo=UTC).isoformat(),
        "status": "complete",
        "rhb_t5_authorized": False,
    }


def _bundle_events(status: str) -> list[dict[str, Any]]:
    events = [
        _event("event-001", "staged", "reviewed", "2026-09-28T10:00:00Z"),
        _event("event-002", "reviewed", "approved_exact", "2026-09-28T10:01:00Z"),
    ]
    if status == "revoked":
        events.append(_event("event-003", "approved_exact", "revoked", "2026-09-28T10:02:00Z"))
    return events


def test_bundle_recomputes_hash_counts_shortfalls_and_excludes_revoked_rows() -> None:
    approved_bundle = _bundle()
    approved_events = _bundle_events("approved_exact")
    bundle, manifest = validate_authority_bundle(
        approved_bundle,
        _manifest(approved_bundle, approved_events),
        **_bundle_inputs(approved_events),
    )
    assert len(bundle.records) == 1
    assert manifest.approved_distinct_variant_count == 1

    revoked_bundle = _bundle("revoked")
    revoked_events = _bundle_events("revoked")
    revoked_manifest = _manifest(revoked_bundle, revoked_events, "revoked")
    _, validated = validate_authority_bundle(
        revoked_bundle, revoked_manifest, **_bundle_inputs(revoked_events)
    )
    assert validated.approved_distinct_variant_count == 0
    assert validated.shortfalls.exact_variant_shortfall == 20

    with pytest.raises(AuthorityContractError, match="latest review event"):
        validate_authority_bundle(
            approved_bundle,
            _manifest(approved_bundle, approved_events),
            **_bundle_inputs(revoked_events),
        )


def test_bundle_rejects_duplicate_uuid_stale_hash_count_padding_and_unsafe_parent() -> None:
    duplicated = _bundle()
    duplicate_record = copy.deepcopy(duplicated["records"][0])
    duplicate_record["candidate_id"] = "candidate-002"
    duplicated["records"].append(duplicate_record)
    with pytest.raises(ValidationError, match="UUIDs must be distinct"):
        AuthorityBundle.model_validate(duplicated)

    bundle = _bundle()
    events = _bundle_events("approved_exact")
    stale = _manifest(bundle, events)
    stale["authority_bundle_sha256"] = "f" * 64
    with pytest.raises(AuthorityContractError, match="checksum is stale"):
        validate_authority_bundle(bundle, stale, **_bundle_inputs(events))

    padded = _manifest(bundle, events)
    padded["approved_distinct_variant_count"] = 20
    with pytest.raises(AuthorityContractError, match="approved distinct count"):
        validate_authority_bundle(bundle, padded, **_bundle_inputs(events))

    unsafe = _manifest(bundle, events)
    unsafe["ordered_parent_artifacts"][0]["reference"] = "../private/evidence.json"
    with pytest.raises(ValidationError, match="path traversal"):
        AuthorityBundleManifest.model_validate(unsafe)


def test_qa_reproducer_rejects_unrelated_catalog_proposal_parent() -> None:
    events = _bundle_events("approved_exact")
    proposal = _proposal()
    proposal["parent_catalog_version"] = "unrelated-catalog"
    proposal["parent_catalog_sha256"] = "d" * 64

    with pytest.raises(AuthorityContractError, match="parent version is stale"):
        validate_review_event_chain(
            _candidate(existing_uuid=False),
            events,
            root=ROOT,
            approved_catalog_proposal=proposal,
            attestations=_attestations(events),
            expected_packet_sha256=SHA_B,
            catalog_parent_payload=_catalog_parent(),
        )


def test_qa_reproducer_rejects_proposal_evidence_outside_fixed_membership() -> None:
    events = _bundle_events("approved_exact")
    proposal = _proposal()
    for row in proposal["field_evidence"]:
        row["source_bindings"][0]["source_record_id"] = "fake-row-outside-100"

    with pytest.raises(AuthorityContractError, match="exactly the candidate source record"):
        validate_review_event_chain(
            _candidate(existing_uuid=False),
            events,
            root=ROOT,
            approved_catalog_proposal=proposal,
            attestations=_attestations(events),
            expected_packet_sha256=SHA_B,
            catalog_parent_payload=_catalog_parent(),
        )


def test_qa_reproducer_rejects_borrowed_evidence_from_another_approved_row() -> None:
    payload = json.loads(NORMALIZED.read_text(encoding="utf-8"))
    other_record_id = payload["records"][1]["source_record_id"]
    events = _bundle_events("approved_exact")
    for event in events:
        for row in event["variant_field_evidence"]:
            row["source_bindings"][0]["source_record_id"] = other_record_id

    with pytest.raises(AuthorityContractError, match="exactly the candidate source record"):
        validate_review_event_chain(
            _candidate(),
            events,
            root=ROOT,
            catalog_record=_product(),
            attestations=_attestations(events),
            expected_packet_sha256=SHA_B,
            catalog_parent_payload=_catalog_parent(),
        )


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("family_group_key", "family-other", "product family"),
        ("release_key", "release-other", "product release"),
    ],
)
def test_qa_reproducer_rejects_catalog_identity_different_from_candidate_release(
    field: str, replacement: str, message: str
) -> None:
    product = _product()
    product[field] = replacement
    product_sha = content_sha256(product)
    events = _bundle_events("approved_exact")
    for event in events:
        event["catalog_record_sha256"] = product_sha
        event["attestation_sha256"] = content_sha256(_attestation(event))

    with pytest.raises(AuthorityContractError, match=f"{message}|frozen catalog parent member"):
        validate_review_event_chain(
            _candidate(),
            events,
            root=ROOT,
            catalog_record=product,
            attestations=_attestations(events),
            expected_packet_sha256=SHA_B,
            catalog_parent_payload=_catalog_parent(),
        )


def test_qa_reproducer_rejects_proposal_product_for_another_release() -> None:
    proposal = _proposal()
    proposal["proposed_product_record"]["release_key"] = "release-other"
    proposal["product_record_sha256"] = content_sha256(proposal["proposed_product_record"])

    with pytest.raises(AuthorityContractError, match="product release"):
        validate_catalog_record_proposal(
            proposal,
            root=ROOT,
            candidate_payload=_candidate(existing_uuid=False),
            catalog_parent_payload=_catalog_parent(),
        )


def test_qa_reproducer_rejects_incomplete_approved_bundle_evidence_and_empty_digests() -> None:
    bundle = _bundle()
    bundle["records"][0]["evidence_sha256s"] = []
    with pytest.raises(ValidationError, match="at least 1 item"):
        AuthorityBundle.model_validate(bundle)

    events = _bundle_events("approved_exact")
    events[-1]["variant_field_evidence"] = [events[-1]["variant_field_evidence"][0]]
    bundle = _bundle()
    bundle["records"][0]["evidence_sha256s"] = [
        content_sha256(events[-1]["variant_field_evidence"][0])
    ]
    manifest = _manifest(bundle, events)
    with pytest.raises(AuthorityContractError, match="coverage differs"):
        validate_authority_bundle(bundle, manifest, **_bundle_inputs(events))


def test_qa_reproducer_rejects_truncated_review_history() -> None:
    bundle = _bundle()
    events = [_bundle_events("approved_exact")[-1]]
    manifest = _manifest(bundle, events)

    with pytest.raises(AuthorityContractError, match="append-only from prior state"):
        validate_authority_bundle(bundle, manifest, **_bundle_inputs(events))


def test_qa_reproducer_rejects_manifest_catalog_and_parent_digest_mismatch() -> None:
    bundle = _bundle()
    events = _bundle_events("approved_exact")
    manifest = _manifest(bundle, events)
    manifest["catalog_version"] = "other"
    manifest["catalog_sha256"] = "d" * 64
    with pytest.raises(AuthorityContractError, match="catalog version is stale"):
        validate_authority_bundle(bundle, manifest, **_bundle_inputs(events))

    manifest = _manifest(bundle, events)
    manifest["ordered_parent_artifacts"][0]["sha256"] = "d" * 64
    with pytest.raises(AuthorityContractError, match="complete input set"):
        validate_authority_bundle(bundle, manifest, **_bundle_inputs(events))


def test_qa_reproducer_rejects_empty_owner_packet_content() -> None:
    packet = {
        "schema_version": "pvr-canonical-authority-owner-review-packet-v1",
        "packet_version": "v1",
        "publication_scope": "local_only_git_ignored",
        "source_decisions_sha256": validate_authority_source_decisions(
            ROOT
        ).source_decisions_sha256,
        "catalog_version": "catalog-v1",
        "catalog_sha256": _catalog_sha(),
        "candidates": [_candidate()],
        "field_evidence": {"candidate-001": []},
        "owner_questions": {"candidate-001": []},
        "missing_or_conflicting_items": {"candidate-001": []},
        "resolver_output_consulted": False,
        "resolver_output_included": False,
        "predicted_uuid_included": False,
        "model_scores_included": False,
        "network_requests": 0,
    }
    with pytest.raises(ValidationError, match="plain-language owner question"):
        OwnerReviewPacket.model_validate(packet)


@pytest.mark.parametrize(
    "private_value",
    [
        "owner@example.com",
        "+1 (212) 555-0199",
        "seller: private_handle",
        "account=#private_user",
        "api_key=do-not-publish",
        "123 Example Street",
    ],
)
def test_qa_reproducer_rejects_private_data_in_field_values(private_value: str) -> None:
    row = _evidence()[0]
    row["agreement"] = "conflicts"
    row["reviewed_value"] = private_value
    with pytest.raises(ValidationError, match="personal|private|identity"):
        VariantFieldEvidence.model_validate(row)


def test_high_level_proposal_revalidates_preconstructed_nested_source_binding() -> None:
    valid = CatalogRecordProposal.model_validate(_proposal())
    valid.field_evidence[0].source_bindings[0].__dict__["source_record_id"] = "fake-row-outside-100"
    unsafe = CatalogRecordProposal.model_construct(**valid.__dict__)

    with pytest.raises(AuthorityContractError, match="exactly the candidate source record"):
        validate_catalog_record_proposal(
            unsafe,
            root=ROOT,
            candidate_payload=_candidate(existing_uuid=False),
            catalog_parent_payload=_catalog_parent(),
        )


def test_review_evidence_value_must_match_the_bound_source_row() -> None:
    events = _bundle_events("approved_exact")
    for event in events:
        evidence = event["variant_field_evidence"][0]
        evidence["catalog_value"] = "Invented Casting"
        evidence["reviewed_value"] = "Invented Casting"

    with pytest.raises(AuthorityContractError, match="does not match candidate source row"):
        validate_review_event_chain(
            _candidate(),
            events,
            root=ROOT,
            catalog_record=_product(),
            attestations=_attestations(events),
            expected_packet_sha256=SHA_B,
            catalog_parent_payload=_catalog_parent(),
        )


def test_packet_candidate_requiring_catalog_review_uses_separately_approved_proposal() -> None:
    packet = {
        "schema_version": "pvr-canonical-authority-owner-review-packet-v1",
        "packet_version": "v1",
        "publication_scope": "local_only_git_ignored",
        "source_decisions_sha256": validate_authority_source_decisions(
            ROOT
        ).source_decisions_sha256,
        "catalog_version": "catalog-v1",
        "catalog_sha256": _catalog_sha(),
        "candidates": [_candidate(existing_uuid=False)],
        "field_evidence": {"candidate-001": _evidence()},
        "owner_questions": {"candidate-001": ["Should catalog review be completed?"]},
        "missing_or_conflicting_items": {"candidate-001": []},
        "resolver_output_consulted": False,
        "resolver_output_included": False,
        "predicted_uuid_included": False,
        "model_scores_included": False,
        "network_requests": 0,
    }
    validated = validate_owner_review_packet(
        packet,
        root=ROOT,
        catalog_parent_payload=_catalog_parent(),
        approved_catalog_proposals={"candidate-001": _proposal()},
    )
    assert validated.candidates[0].canonical_uuid is None


def test_second_qa_rejects_catalog_parent_without_products_or_uuid_membership() -> None:
    events = _bundle_events("approved_exact")
    with pytest.raises(ValidationError, match="products|Extra inputs"):
        validate_review_event_chain(
            _candidate(),
            events,
            root=ROOT,
            catalog_record=_product(),
            attestations=_attestations(events),
            expected_packet_sha256=SHA_B,
            catalog_parent_payload={"catalog_version": "catalog-v1", "frozen": True},
        )

    unrelated = _catalog_parent()
    unrelated["products"][0]["canonical_uuid"] = "22222222-2222-4222-8222-222222222222"
    unrelated["products"][0]["record"]["canonical_uuid"] = "22222222-2222-4222-8222-222222222222"
    unrelated["products"][0]["record_sha256"] = content_sha256(unrelated["products"][0]["record"])
    with pytest.raises(AuthorityContractError, match="not a member"):
        validate_review_event_chain(
            _candidate(),
            events,
            root=ROOT,
            catalog_record=_product(),
            attestations=_attestations(events),
            expected_packet_sha256=SHA_B,
            catalog_parent_payload=unrelated,
        )


def test_second_qa_packet_rejects_stale_catalog_and_requires_exact_missing_markers() -> None:
    packet: dict[str, Any] = {
        "schema_version": "pvr-canonical-authority-owner-review-packet-v1",
        "packet_version": "packet-v1",
        "publication_scope": "local_only_git_ignored",
        "source_decisions_sha256": validate_authority_source_decisions(
            ROOT
        ).source_decisions_sha256,
        "catalog_version": "stale-catalog",
        "catalog_sha256": "d" * 64,
        "candidates": [_candidate()],
        "field_evidence": {"candidate-001": [_evidence()[0]]},
        "owner_questions": {"candidate-001": ["Which fields are still missing?"]},
        "missing_or_conflicting_items": {"candidate-001": []},
        "resolver_output_consulted": False,
        "resolver_output_included": False,
        "predicted_uuid_included": False,
        "model_scores_included": False,
        "network_requests": 0,
    }
    with pytest.raises(AuthorityContractError, match="catalog version is stale"):
        validate_owner_review_packet(packet, root=ROOT, catalog_parent_payload=_catalog_parent())

    packet["catalog_version"] = "catalog-v1"
    packet["catalog_sha256"] = _catalog_sha()
    with pytest.raises(AuthorityContractError, match="exactly enumerate"):
        validate_owner_review_packet(packet, root=ROOT, catalog_parent_payload=_catalog_parent())

    packet["missing_or_conflicting_items"]["candidate-001"] = sorted(
        {
            "missing:release_year",
            "missing:series",
            "missing:collector_number",
            "missing:series_position",
            "missing:identifiers",
        }
    )
    assert (
        validate_owner_review_packet(
            packet, root=ROOT, catalog_parent_payload=_catalog_parent()
        ).catalog_version
        == "catalog-v1"
    )


def test_second_qa_rejects_preconstructed_unknown_fields_recursively() -> None:
    candidate = AuthorityCandidate.model_validate(_candidate())
    candidate.__dict__["predicted_winner"] = UUID_A
    with pytest.raises(AuthorityContractError, match="undeclared preconstructed fields"):
        validate_authority_candidate(candidate, root=ROOT)

    candidate = AuthorityCandidate.model_validate(_candidate())
    candidate.source_binding.__dict__["seller_account"] = "private_handle"
    with pytest.raises(AuthorityContractError, match="undeclared preconstructed fields"):
        validate_authority_candidate(candidate, root=ROOT)


@pytest.mark.parametrize(
    "private_value",
    [
        "seller private_handle",
        "account private_user",
        "api key do-not-publish",
        "221B Baker Street",
    ],
)
def test_second_qa_pii_patterns_without_punctuation_are_rejected(private_value: str) -> None:
    row = _evidence()[0]
    row["agreement"] = "conflicts"
    row["reviewed_value"] = private_value
    with pytest.raises(ValidationError, match="private|identity|address"):
        VariantFieldEvidence.model_validate(row)


def test_second_qa_iso_date_is_not_a_phone_false_positive() -> None:
    packet = {
        "schema_version": "pvr-canonical-authority-owner-review-packet-v1",
        "packet_version": "packet-v1",
        "publication_scope": "local_only_git_ignored",
        "source_decisions_sha256": validate_authority_source_decisions(
            ROOT
        ).source_decisions_sha256,
        "catalog_version": "catalog-v1",
        "catalog_sha256": _catalog_sha(),
        "candidates": [_candidate()],
        "field_evidence": {"candidate-001": _evidence()},
        "owner_questions": {"candidate-001": ["Confirm the 2026-09-28 review?"]},
        "missing_or_conflicting_items": {"candidate-001": []},
        "resolver_output_consulted": False,
        "resolver_output_included": False,
        "predicted_uuid_included": False,
        "model_scores_included": False,
        "network_requests": 0,
    }
    assert (
        validate_owner_review_packet(
            packet, root=ROOT, catalog_parent_payload=_catalog_parent()
        ).network_requests
        == 0
    )


def test_second_qa_bundle_rejects_catalog_version_different_from_parent() -> None:
    bundle = _bundle()
    events = _bundle_events("approved_exact")
    parent = _catalog_parent()
    parent["catalog_version"] = "different-catalog"
    inputs = _bundle_inputs(events)
    inputs["catalog_parent_payload"] = parent
    manifest = _manifest(bundle, events)
    manifest["catalog_version"] = "different-catalog"
    manifest["catalog_sha256"] = content_sha256(parent)
    manifest["ordered_parent_artifacts"] = [
        item.model_dump(mode="json") for item in authority_bundle_parent_artifacts(**inputs)
    ]

    with pytest.raises(AuthorityContractError, match="catalog version is stale"):
        validate_authority_bundle(bundle, manifest, **inputs)


def test_second_qa_bundle_rejects_noncanonical_global_event_order() -> None:
    uuid_b = "22222222-2222-4222-8222-222222222222"
    candidate_two = copy.deepcopy(_candidate())
    candidate_two.update(
        candidate_id="candidate-002",
        canonical_uuid=uuid_b,
        family_group_key="family-miata-two",
        proposed_release_key="release-2025-hyw18-two",
    )
    product_two = copy.deepcopy(_product())
    product_two.update(
        canonical_uuid=uuid_b,
        family_group_key="family-miata-two",
        release_key="release-2025-hyw18-two",
    )
    parent = _catalog_parent()
    parent["products"].append(
        {
            "canonical_id": "hot-wheels-miata-2025-hyw18-two",
            "canonical_uuid": uuid_b,
            "record": product_two,
            "record_sha256": content_sha256(product_two),
        }
    )
    catalog_sha = content_sha256(parent)

    first_events = _bundle_events("approved_exact")
    for event in first_events:
        event["catalog_sha256"] = catalog_sha
        event["attestation_sha256"] = content_sha256(_attestation(event))
    second_events = copy.deepcopy(first_events)
    for index, event in enumerate(second_events, start=1):
        event.update(
            event_id=f"event-10{index}",
            candidate_id="candidate-002",
            canonical_uuid=uuid_b,
            catalog_record_sha256=content_sha256(product_two),
        )
        event["attestation_sha256"] = content_sha256(_attestation(event))
    reordered_events = [*second_events, *first_events]

    bundle = _bundle()
    bundle["records"].append(
        {
            "candidate_id": "candidate-002",
            "canonical_uuid": uuid_b,
            "family_group_key": "family-miata-two",
            "release_key": "release-2025-hyw18-two",
            "status": "approved_exact",
            "synthetic": False,
            "latest_event_id": "event-102",
            "catalog_version": "catalog-v1",
            "catalog_record_sha256": content_sha256(product_two),
            "source_decision_ids": ["fandom-hot-wheels-2025-pilot-r790665-v1"],
            "evidence_sha256s": sorted(content_sha256(row) for row in _evidence()),
        }
    )
    inputs: dict[str, Any] = {
        "root": ROOT,
        "candidate_payloads": {
            "candidate-001": _candidate(),
            "candidate-002": candidate_two,
        },
        "catalog_records": {
            "candidate-001": _product(),
            "candidate-002": product_two,
        },
        "catalog_proposals": {},
        "review_events": reordered_events,
        "attestations": _attestations(reordered_events),
        "packet_sha256s": {"candidate-001": SHA_B, "candidate-002": SHA_B},
        "catalog_parent_payload": parent,
    }
    manifest = {
        "schema_version": "pvr-canonical-authority-bundle-manifest-v1",
        "bundle_version": "authority-bundle-v1",
        "authority_bundle_sha256": content_sha256(bundle),
        "ordered_parent_artifacts": [
            item.model_dump(mode="json") for item in authority_bundle_parent_artifacts(**inputs)
        ],
        "catalog_version": "catalog-v1",
        "catalog_sha256": catalog_sha,
        "source_decision_sha256s": [
            validate_authority_source_decisions(ROOT).source_decisions_sha256
        ],
        "counts_by_status": {
            "staged": 0,
            "reviewed": 0,
            "approved_exact": 2,
            "conflicted": 0,
            "insufficient": 0,
            "held": 0,
            "revoked": 0,
        },
        "approved_distinct_variant_count": 2,
        "qualifying_family_count": 0,
        "family_composition": [],
        "resolver_output_consulted": False,
        "network_requests": 0,
        "publication_scope": "safe_metadata_only",
        "gate_status": "blocked_insufficient_exact_authority",
        "shortfalls": {
            "exact_variant_shortfall": 18,
            "qualifying_family_shortfall": 4,
        },
        "created_at": datetime(2026, 9, 28, tzinfo=UTC).isoformat(),
        "status": "complete",
        "rhb_t5_authorized": False,
    }
    with pytest.raises(AuthorityContractError, match="canonical candidate/time/event ordering"):
        validate_authority_bundle(bundle, manifest, **inputs)


def test_third_qa_rejects_reordered_evidence_in_proposal_packet_and_event() -> None:
    proposal = _proposal()
    proposal["field_evidence"] = list(reversed(proposal["field_evidence"]))
    with pytest.raises(ValidationError, match="canonical VariantField order"):
        CatalogRecordProposal.model_validate(proposal)

    packet = {
        "schema_version": "pvr-canonical-authority-owner-review-packet-v1",
        "packet_version": "packet-v1",
        "publication_scope": "local_only_git_ignored",
        "source_decisions_sha256": validate_authority_source_decisions(
            ROOT
        ).source_decisions_sha256,
        "catalog_version": "catalog-v1",
        "catalog_sha256": _catalog_sha(),
        "candidates": [_candidate()],
        "field_evidence": {"candidate-001": list(reversed(_evidence()))},
        "owner_questions": {"candidate-001": ["Does each visible field agree?"]},
        "missing_or_conflicting_items": {"candidate-001": []},
        "resolver_output_consulted": False,
        "resolver_output_included": False,
        "predicted_uuid_included": False,
        "model_scores_included": False,
        "network_requests": 0,
    }
    with pytest.raises(ValidationError, match="canonical VariantField order"):
        validate_owner_review_packet(packet, root=ROOT, catalog_parent_payload=_catalog_parent())

    event = _event("event-001", "staged", "reviewed", "2026-09-28T10:00:00Z")
    event["variant_field_evidence"] = list(reversed(event["variant_field_evidence"]))
    with pytest.raises(ValidationError, match="canonical VariantField order"):
        AuthorityReviewEvent.model_validate(event)


def test_third_qa_packet_issues_are_sorted_and_unique() -> None:
    evidence = _evidence()
    evidence[0]["agreement"] = "conflicts"
    packet = {
        "schema_version": "pvr-canonical-authority-owner-review-packet-v1",
        "packet_version": "packet-v1",
        "publication_scope": "local_only_git_ignored",
        "source_decisions_sha256": validate_authority_source_decisions(
            ROOT
        ).source_decisions_sha256,
        "catalog_version": "catalog-v1",
        "catalog_sha256": _catalog_sha(),
        "candidates": [_candidate()],
        "field_evidence": {"candidate-001": evidence},
        "owner_questions": {"candidate-001": ["Resolve the casting conflict?"]},
        "missing_or_conflicting_items": {
            "candidate-001": ["conflicting:casting", "conflicting:casting"]
        },
        "resolver_output_consulted": False,
        "resolver_output_included": False,
        "predicted_uuid_included": False,
        "model_scores_included": False,
        "network_requests": 0,
    }
    with pytest.raises(ValidationError, match="unique and ordered"):
        OwnerReviewPacket.model_validate(packet)


@pytest.mark.parametrize(
    "private_value",
    [
        "seller johndoe",
        "account 123456",
        "username alice",
        "api key abc",
        "password foo",
        "1 Infinite Loop",
    ],
)
def test_third_qa_rejects_short_account_credential_and_address_pii(
    private_value: str,
) -> None:
    row = _evidence()[0]
    row["agreement"] = "conflicts"
    row["reviewed_value"] = private_value
    with pytest.raises(ValidationError, match="private|identity|address"):
        VariantFieldEvidence.model_validate(row)


@pytest.mark.parametrize("safe_value", ["2026-09-28", "250/250", "001", "2/5", "HYW18"])
def test_third_qa_preserves_safe_catalog_tokens(safe_value: str) -> None:
    row = _evidence()[0]
    row["agreement"] = "conflicts"
    row["reviewed_value"] = safe_value
    assert VariantFieldEvidence.model_validate(row).reviewed_value == safe_value


def test_third_qa_hash_bearing_set_like_sequences_require_canonical_order() -> None:
    candidate = _candidate()
    candidate["selection_context_refs"] = ["context:z", "context:a"]
    with pytest.raises(ValidationError, match="unique and ordered"):
        AuthorityCandidate.model_validate(candidate)

    evidence = _evidence()[0]
    evidence["evidence_refs"] = ["evidence:z", "evidence:a"]
    with pytest.raises(ValidationError, match="unique and ordered"):
        VariantFieldEvidence.model_validate(evidence)

    proposal = _proposal()
    proposal["proposed_product_record"]["identifiers"] = ["ZZZ", "AAA"]
    proposal["product_record_sha256"] = content_sha256(proposal["proposed_product_record"])
    with pytest.raises(ValidationError, match="unique and ordered"):
        CatalogRecordProposal.model_validate(proposal)


def test_contract_module_has_no_runtime_or_network_imports() -> None:
    source = (ROOT / "src/product_variant_resolver/canonical_authority_review.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    imports = {
        alias.name.casefold()
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").casefold()
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    for forbidden in ("fastapi", "requests", "httpx", "selenium"):
        assert all(forbidden not in imported for imported in imports)
    assert all(not imported.endswith((".service", ".retrieval")) for imported in imports)
