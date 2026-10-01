"""Append-only CAR-T5 owner-Gate decision recording.

The recorder is intentionally bounded to the frozen T5-G1 family batches that have an
implemented owner-review workflow.  It records only ``staged -> reviewed`` outcomes and
cannot create exact authority or authorize RHB-T5.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.canonical_authority_preparation import (
    PRIVATE_DIRECTORY,
    AuthorityReviewPreparationPacket,
    _fsync_directory,
    _require_ignore_rule,
    _safe_path,
    _strict_json,
    _write_temp,
    build_authority_review_preparation,
    prepare_authority_review,
)
from product_variant_resolver.canonical_authority_review import (
    AuthorityContractError,
    AuthorityReviewEventV2,
    BatchOwnerAuthorization,
    ExpectedBatchOwnerAuthorization,
    OwnerAttestationV2,
    ReviewStatus,
    content_sha256,
    stable_json_bytes,
    validate_batch_owner_authorization,
)

AUTHORIZATION_LEDGER_REFERENCE = PRIVATE_DIRECTORY / "batch-owner-authorizations.json"
ATTESTATION_LEDGER_REFERENCE = PRIVATE_DIRECTORY / "owner-attestations.json"
AUTHORITY_CANDIDATES_REFERENCE = Path(
    "data/authority-review/canonical-authority-review-v1/authority-candidates.json"
)
REVIEW_EVENTS_REFERENCE = Path(
    "data/authority-review/canonical-authority-review-v1/review-events.json"
)
FORBIDDEN_AUTHORITY_REFERENCE = Path(
    "data/authority-review/canonical-authority-review-v1/approved-authority.json"
)
FORBIDDEN_AUTHORITY_MANIFEST_REFERENCE = Path(
    "data/authority-review/canonical-authority-review-v1/authority-manifest.json"
)

DECISION_VERSION: Literal["canonical-authority-review-t5-g1-v1"] = (
    "canonical-authority-review-t5-g1-v1"
)
EXPECTED_BATCH_ORDINAL = 2
SUPPORTED_BATCHES = {
    2: {
        "family_group_key": "car-t3-family-draftnator",
        "entry_ordinals": (2, 11, 18),
        "toy_identifiers": ("HYW70", "HYX67", "HYY31"),
    },
    3: {
        "family_group_key": "car-t3-family-subaru-brz",
        "entry_ordinals": (3, 8, 14),
        "toy_identifiers": ("JBB55", "HYY12", "HYW99"),
    },
}
REVIEW_REASON: Literal[
    "Project owner explicitly reviewed the exact bound T5-G1 family batch; all six evidence "
    "rows agree, color and edition remain null, and exact authority remains unauthorized."
] = (
    "Project owner explicitly reviewed the exact bound T5-G1 family batch; all six evidence "
    "rows agree, color and edition remain null, and exact authority remains unauthorized."
)
G1_DECLARATION: Literal[
    "owner_explicitly_authorized_t5_g1_review_outcomes_for_every_covered_entry"
] = "owner_explicitly_authorized_t5_g1_review_outcomes_for_every_covered_entry"

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
OpaqueId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:#-]{0,199}$")]


class DecisionContract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class BatchAuthorizationLedger(DecisionContract):
    schema_version: Literal["pvr-canonical-authority-batch-authorization-ledger-v1"]
    ledger_version: Literal["canonical-authority-review-t5-g1-v1"]
    packet_sha256: Sha256
    authorizations: list[BatchOwnerAuthorization] = Field(min_length=1)
    cumulative_authorization_sha256: Sha256
    ledger_sha256: Sha256

    @model_validator(mode="after")
    def ledger_is_append_only_and_hash_bound(self) -> BatchAuthorizationLedger:
        ordinals = [item.batch_ordinal for item in self.authorizations]
        if ordinals != sorted(set(ordinals)):
            raise ValueError("batch authorizations must be distinct and ordered")
        hashes = [item.authorization_sha256 for item in self.authorizations]
        if len(hashes) != len(set(hashes)):
            raise ValueError("batch authorization hashes must be distinct")
        if self.cumulative_authorization_sha256 != content_sha256(hashes):
            raise ValueError("batch authorization cumulative checksum is stale")
        expected = content_sha256(self.model_dump(mode="json", exclude={"ledger_sha256"}))
        if self.ledger_sha256 != expected:
            raise ValueError("batch authorization ledger checksum is stale")
        return self


class OwnerAttestationLedger(DecisionContract):
    schema_version: Literal["pvr-canonical-authority-owner-attestation-ledger-v1"]
    ledger_version: Literal["canonical-authority-review-t5-g1-v1"]
    packet_sha256: Sha256
    batch_authorization_sha256: Sha256 | None = None
    batch_authorization_sha256s: list[Sha256] | None = None
    attestations: list[OwnerAttestationV2] = Field(min_length=3)
    cumulative_attestation_sha256: Sha256
    ledger_sha256: Sha256

    @property
    def authorization_hashes(self) -> list[str]:
        if self.batch_authorization_sha256 is not None:
            return [self.batch_authorization_sha256]
        return list(self.batch_authorization_sha256s or [])

    @model_validator(mode="after")
    def attestations_are_ordered_and_batch_bound(self) -> OwnerAttestationLedger:
        ids = [item.candidate_id for item in self.attestations]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("owner attestations must be distinct and ordered")
        has_single = self.batch_authorization_sha256 is not None
        has_multiple = self.batch_authorization_sha256s is not None
        if has_single == has_multiple:
            raise ValueError("owner attestation ledger requires exactly one authorization shape")
        authorization_hashes = self.authorization_hashes
        if not authorization_hashes or len(authorization_hashes) != len(set(authorization_hashes)):
            raise ValueError("owner attestation batch authorizations must be distinct")
        if {item.batch_authorization_sha256 for item in self.attestations} != set(
            authorization_hashes
        ):
            raise ValueError("owner attestations must reference every declared batch authorization")
        hashes = [item.attestation_sha256 for item in self.attestations]
        if self.cumulative_attestation_sha256 != content_sha256(hashes):
            raise ValueError("owner attestation cumulative checksum is stale")
        expected = content_sha256(
            self.model_dump(mode="json", exclude={"ledger_sha256"}, exclude_none=True)
        )
        if self.ledger_sha256 != expected:
            raise ValueError("owner attestation ledger checksum is stale")
        return self


class AuthorityCandidateState(DecisionContract):
    ordinal: int = Field(ge=1, le=20)
    candidate_id: OpaqueId
    canonical_uuid: UUID
    entry_sha256: Sha256
    catalog_record_sha256: Sha256
    status: ReviewStatus
    latest_event_id: OpaqueId | None
    latest_event_sha256: Sha256 | None

    @model_validator(mode="after")
    def status_and_event_are_consistent(self) -> AuthorityCandidateState:
        reviewed = self.status == ReviewStatus.reviewed
        if reviewed != (self.latest_event_id is not None and self.latest_event_sha256 is not None):
            raise ValueError(
                "reviewed candidates require one latest event; staged candidates forbid it"
            )
        if self.status not in {ReviewStatus.staged, ReviewStatus.reviewed}:
            raise ValueError("T5-G1 partial candidate state may only be staged or reviewed")
        return self


class AuthorityCandidateStateFile(DecisionContract):
    schema_version: Literal["pvr-canonical-authority-candidate-state-v1"]
    state_version: Literal["canonical-authority-review-t5-g1-v1"]
    packet_sha256: Sha256
    catalog_version: Literal["catalog-v2"]
    catalog_sha256: Sha256
    candidates: list[AuthorityCandidateState] = Field(min_length=20, max_length=20)
    status_counts: dict[Literal["staged", "reviewed", "approved_exact"], int]
    resolver_output_consulted: Literal[False]
    network_requests: Literal[0]
    rhb_t5_authorized: Literal[False]
    state_sha256: Sha256

    @model_validator(mode="after")
    def candidate_state_is_complete_and_safe(self) -> AuthorityCandidateStateFile:
        if [item.ordinal for item in self.candidates] != list(range(1, 21)):
            raise ValueError("candidate state must preserve packet order")
        ids = [item.candidate_id for item in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate state IDs must be unique")
        observed = {
            "staged": sum(item.status == ReviewStatus.staged for item in self.candidates),
            "reviewed": sum(item.status == ReviewStatus.reviewed for item in self.candidates),
            "approved_exact": sum(
                item.status == ReviewStatus.approved_exact for item in self.candidates
            ),
        }
        if self.status_counts != observed:
            raise ValueError("candidate state counts are stale")
        expected = content_sha256(self.model_dump(mode="json", exclude={"state_sha256"}))
        if self.state_sha256 != expected:
            raise ValueError("candidate state checksum is stale")
        return self


class AuthorityReviewEventFile(DecisionContract):
    schema_version: Literal["pvr-canonical-authority-review-event-ledger-v1"]
    ledger_version: Literal["canonical-authority-review-t5-g1-v1"]
    packet_sha256: Sha256
    catalog_version: Literal["catalog-v2"]
    catalog_sha256: Sha256
    events: list[AuthorityReviewEventV2] = Field(min_length=3)
    batch_authorization_count: int = Field(ge=1)
    owner_attestation_count: int = Field(ge=3)
    review_event_count: int = Field(ge=3)
    status_counts: dict[Literal["reviewed", "approved_exact"], int]
    cumulative_event_sha256: Sha256
    resolver_output_consulted: Literal[False]
    network_requests: Literal[0]
    rhb_t5_authorized: Literal[False]
    ledger_sha256: Sha256

    @model_validator(mode="after")
    def events_are_append_only_partial_batches(self) -> AuthorityReviewEventFile:
        ids = [event.candidate_id for event in self.events]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("review events must be distinct and ordered")
        batch_hashes = {event.batch_authorization_sha256 for event in self.events}
        if len(batch_hashes) != self.batch_authorization_count:
            raise ValueError("review-event batch authorization count is stale")
        if any(
            event.from_status != ReviewStatus.staged or event.to_status != ReviewStatus.reviewed
            for event in self.events
        ):
            raise ValueError("T5-G1 partial events must be staged to reviewed")
        if self.owner_attestation_count != len(self.events):
            raise ValueError("review-event owner attestation count is stale")
        if self.review_event_count != len(self.events):
            raise ValueError("review-event count is stale")
        if self.status_counts != {"reviewed": len(self.events), "approved_exact": 0}:
            raise ValueError("partial event status counts are stale")
        hashes = [event.event_sha256 for event in self.events]
        if self.cumulative_event_sha256 != content_sha256(hashes):
            raise ValueError("review event cumulative checksum is stale")
        expected = content_sha256(self.model_dump(mode="json", exclude={"ledger_sha256"}))
        if self.ledger_sha256 != expected:
            raise ValueError("review event ledger checksum is stale")
        return self


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _with_hash(body: dict[str, Any], key: str) -> dict[str, Any]:
    return {**body, key: content_sha256(body)}


def _selected_batch(
    packet: AuthorityReviewPreparationPacket, batch_ordinal: int
) -> tuple[Any, list[Any]]:
    specification = SUPPORTED_BATCHES.get(batch_ordinal)
    if specification is None:
        raise AuthorityContractError("this bounded recorder accepts only T5-G1 Batch 2 or Batch 3")
    batch = packet.family_batches[batch_ordinal - 1]
    if (
        batch.batch_ordinal != batch_ordinal
        or tuple(batch.entry_ordinals) != specification["entry_ordinals"]
        or batch.family_group_key != specification["family_group_key"]
    ):
        raise AuthorityContractError(
            f"T5-G1 authorization does not match frozen Batch {batch_ordinal}"
        )
    by_ordinal = {entry.ordinal: entry for entry in packet.entries}
    entries = [by_ordinal[ordinal] for ordinal in batch.entry_ordinals]
    identifiers = tuple(entry.catalog_record.identifiers[0] for entry in entries)
    if identifiers != specification["toy_identifiers"]:
        raise AuthorityContractError(f"T5-G1 Batch {batch_ordinal} toy identifiers are stale")
    if batch.candidate_ids != [entry.candidate.candidate_id for entry in entries]:
        raise AuthorityContractError(f"T5-G1 Batch {batch_ordinal} candidate order is stale")
    if batch.entry_sha256s != [entry.entry_sha256 for entry in entries]:
        raise AuthorityContractError(f"T5-G1 Batch {batch_ordinal} entry hashes are stale")
    return batch, entries


def _load_existing_outputs(
    root: Path,
) -> tuple[
    BatchAuthorizationLedger,
    OwnerAttestationLedger,
    AuthorityCandidateStateFile,
    AuthorityReviewEventFile,
]:
    authorization_payload, _ = _strict_json(root / AUTHORIZATION_LEDGER_REFERENCE)
    attestation_payload, _ = _strict_json(root / ATTESTATION_LEDGER_REFERENCE)
    candidate_payload, _ = _strict_json(root / AUTHORITY_CANDIDATES_REFERENCE)
    event_payload, _ = _strict_json(root / REVIEW_EVENTS_REFERENCE)
    return (
        BatchAuthorizationLedger.model_validate(authorization_payload),
        OwnerAttestationLedger.model_validate(attestation_payload),
        AuthorityCandidateStateFile.model_validate(candidate_payload),
        AuthorityReviewEventFile.model_validate(event_payload),
    )


def _validate_existing_outputs(
    packet: AuthorityReviewPreparationPacket,
    packet_sha: str,
    authorization_ledger: BatchAuthorizationLedger,
    attestation_ledger: OwnerAttestationLedger,
    candidate_file: AuthorityCandidateStateFile,
    event_file: AuthorityReviewEventFile,
) -> None:
    common = (packet_sha, packet.catalog_version, packet.catalog_sha256)
    if authorization_ledger.packet_sha256 != packet_sha:
        raise AuthorityContractError("existing authorization ledger differs from frozen packet")
    if attestation_ledger.packet_sha256 != packet_sha:
        raise AuthorityContractError("existing attestation ledger differs from frozen packet")
    if (
        candidate_file.packet_sha256,
        candidate_file.catalog_version,
        candidate_file.catalog_sha256,
    ) != common:
        raise AuthorityContractError("existing candidate state differs from frozen packet")
    if (event_file.packet_sha256, event_file.catalog_version, event_file.catalog_sha256) != common:
        raise AuthorityContractError("existing review events differ from frozen packet")

    ordinals = [item.batch_ordinal for item in authorization_ledger.authorizations]
    if ordinals not in ([2], [2, 3]):
        raise AuthorityContractError("existing T5-G1 authorizations are not the supported prefix")
    authorization_hashes = [
        item.authorization_sha256 for item in authorization_ledger.authorizations
    ]
    if attestation_ledger.authorization_hashes != authorization_hashes:
        raise AuthorityContractError("existing attestations differ from authorization order")

    entry_by_candidate = {entry.candidate.candidate_id: entry for entry in packet.entries}
    authorization_by_candidate: dict[str, BatchOwnerAuthorization] = {}
    for authorization in authorization_ledger.authorizations:
        batch, entries = _selected_batch(packet, authorization.batch_ordinal)
        if (
            authorization.gate != "T5-G1"
            or authorization.authorization_scope != "staged_to_reviewed"
            or authorization.authorization_declaration != G1_DECLARATION
            or authorization.packet_sha256 != packet_sha
            or authorization.family_batch_sha256 != batch.batch_sha256
            or authorization.catalog_application_manifest_sha256
            != packet.catalog_application_manifest_sha256
            or authorization.catalog_version != packet.catalog_version
            or authorization.catalog_sha256 != packet.catalog_sha256
            or authorization.ordered_candidate_ids != batch.candidate_ids
            or authorization.ordered_entry_sha256s != batch.entry_sha256s
            or authorization.declared_outcome != ReviewStatus.reviewed
            or authorization.prior_gate_response_sha256s
            or authorization.resolver_output_consulted
        ):
            raise AuthorityContractError("existing batch authorization differs from frozen batch")
        for entry in entries:
            candidate_id = entry.candidate.candidate_id
            if candidate_id in authorization_by_candidate:
                raise AuthorityContractError("existing authorizations overlap candidates")
            authorization_by_candidate[candidate_id] = authorization

    attestations = {item.candidate_id: item for item in attestation_ledger.attestations}
    events = {item.candidate_id: item for item in event_file.events}
    expected_ids = set(authorization_by_candidate)
    if set(attestations) != expected_ids or set(events) != expected_ids:
        raise AuthorityContractError("existing decision ledgers do not cover the same candidates")
    for candidate_id, authorization in authorization_by_candidate.items():
        entry = entry_by_candidate[candidate_id]
        attestation = attestations[candidate_id]
        event = events[candidate_id]
        expected_event_id = (
            f"car-t5-g1-batch-{authorization.batch_ordinal}-ordinal-{entry.ordinal:02d}"
        )
        if (
            attestation.packet_sha256 != packet_sha
            or attestation.catalog_version != packet.catalog_version
            or attestation.catalog_sha256 != packet.catalog_sha256
            or attestation.catalog_record_sha256 != entry.catalog_record_sha256
            or attestation.outcome != ReviewStatus.reviewed
            or attestation.batch_authorization_sha256 != authorization.authorization_sha256
            or event.event_id != expected_event_id
            or event.from_status != ReviewStatus.staged
            or event.to_status != ReviewStatus.reviewed
            or event.packet_sha256 != packet_sha
            or event.catalog_version != packet.catalog_version
            or event.catalog_sha256 != packet.catalog_sha256
            or event.canonical_uuid != entry.candidate.canonical_uuid
            or event.catalog_record_sha256 != entry.catalog_record_sha256
            or event.variant_field_evidence != entry.field_evidence
            or event.attestation_sha256 != attestation.attestation_sha256
            or event.batch_authorization_sha256 != authorization.authorization_sha256
        ):
            raise AuthorityContractError("existing attestation or event differs from frozen entry")

    states = {item.candidate_id: item for item in candidate_file.candidates}
    if set(states) != set(entry_by_candidate):
        raise AuthorityContractError("existing candidate state coverage differs from frozen packet")
    for entry in packet.entries:
        candidate_id = entry.candidate.candidate_id
        state = states[candidate_id]
        candidate_event = events.get(candidate_id)
        expected_status = ReviewStatus.reviewed if candidate_event else ReviewStatus.staged
        if (
            state.ordinal != entry.ordinal
            or state.canonical_uuid != entry.candidate.canonical_uuid
            or state.entry_sha256 != entry.entry_sha256
            or state.catalog_record_sha256 != entry.catalog_record_sha256
            or state.status != expected_status
            or state.latest_event_id != (candidate_event.event_id if candidate_event else None)
            or state.latest_event_sha256
            != (candidate_event.event_sha256 if candidate_event else None)
        ):
            raise AuthorityContractError("existing candidate state differs from review events")


def _build_outputs(
    root: Path,
    *,
    owner_response_verbatim: str,
    authorized_exact_owner_response: str,
    reviewed_at: datetime,
    batch_ordinal: int,
    expected_outcome: str,
    existing: tuple[
        BatchAuthorizationLedger,
        OwnerAttestationLedger,
        AuthorityCandidateStateFile,
        AuthorityReviewEventFile,
    ]
    | None,
) -> dict[Path, bytes]:
    if batch_ordinal not in SUPPORTED_BATCHES:
        raise AuthorityContractError("this bounded recorder accepts only T5-G1 Batch 2 or Batch 3")
    if expected_outcome != "reviewed":
        raise AuthorityContractError("this bounded recorder accepts only staged to reviewed")
    if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
        raise AuthorityContractError("review timestamp must be timezone-aware")
    timestamp = reviewed_at.astimezone(UTC).replace(microsecond=0)
    if timestamp != reviewed_at:
        raise AuthorityContractError("review timestamp must already be whole-second UTC")

    if prepare_authority_review(root, check=True) != "unchanged":
        raise AuthorityContractError("CAR-T5 preparation is not frozen")
    packet, _owner_markdown, preparation_manifest = build_authority_review_preparation(root)
    packet_sha = content_sha256(packet.model_dump(mode="json"))
    if packet_sha != preparation_manifest.private_packet_sha256:
        raise AuthorityContractError("CAR-T5 preparation packet checksum is stale")
    batch, entries = _selected_batch(packet, batch_ordinal)
    if existing is None:
        authorizations: list[BatchOwnerAuthorization] = []
        attestations: list[OwnerAttestationV2] = []
        events: list[AuthorityReviewEventV2] = []
    else:
        _validate_existing_outputs(packet, packet_sha, *existing)
        authorizations = list(existing[0].authorizations)
        attestations = list(existing[1].attestations)
        events = list(existing[3].events)

    existing_authorization = next(
        (item for item in authorizations if item.batch_ordinal == batch_ordinal), None
    )
    if (
        existing_authorization is None
        and batch_ordinal == 3
        and [item.batch_ordinal for item in authorizations] != [2]
    ):
        raise AuthorityContractError("T5-G1 Batch 3 requires the complete Batch 2 decision state")
    response_sha = _sha256_text(authorized_exact_owner_response)
    expected = ExpectedBatchOwnerAuthorization(
        gate="T5-G1",
        authorization_scope="staged_to_reviewed",
        authorization_declaration=G1_DECLARATION,
        expected_outcome=ReviewStatus.reviewed,
        batch_ordinal=batch.batch_ordinal,
        family_batch_sha256=batch.batch_sha256,
        catalog_application_manifest_sha256=(packet.catalog_application_manifest_sha256),
        exact_external_response=authorized_exact_owner_response,
        exact_external_response_sha256=response_sha,
        prior_gate_response_sha256s=[],
    )
    authorization_body: dict[str, Any] = {
        "schema_version": "pvr-canonical-authority-batch-owner-authorization-v1",
        "gate": "T5-G1",
        "authorization_scope": "staged_to_reviewed",
        "authorization_declaration": G1_DECLARATION,
        "packet_sha256": packet_sha,
        "batch_ordinal": batch.batch_ordinal,
        "family_batch_sha256": batch.batch_sha256,
        "catalog_application_manifest_sha256": (packet.catalog_application_manifest_sha256),
        "catalog_version": packet.catalog_version,
        "catalog_sha256": packet.catalog_sha256,
        "ordered_candidate_ids": batch.candidate_ids,
        "ordered_entry_sha256s": batch.entry_sha256s,
        "declared_outcome": "reviewed",
        "owner_response_verbatim": owner_response_verbatim,
        "authorized_exact_owner_response": authorized_exact_owner_response,
        "response_verbatim_sha256": _sha256_text(owner_response_verbatim),
        "prior_gate_response_sha256s": [],
        "confirmation_method": "owner_attestation",
        "reviewed_by_role": "project_owner",
        "authorized_at": timestamp.isoformat().replace("+00:00", "Z"),
        "resolver_output_consulted": False,
    }
    proposed_authorization = BatchOwnerAuthorization.model_validate(
        _with_hash(authorization_body, "authorization_sha256")
    )
    validate_batch_owner_authorization(proposed_authorization, expected=expected)
    if existing_authorization is not None:
        validate_batch_owner_authorization(existing_authorization, expected=expected)
        if existing_authorization != proposed_authorization:
            raise AuthorityContractError("conflicting or tampered T5-G1 batch replay")
        authorization = existing_authorization
    else:
        authorization = proposed_authorization
        authorizations.append(authorization)
        authorizations.sort(key=lambda item: item.batch_ordinal)

    auth_ledger_body = {
        "schema_version": "pvr-canonical-authority-batch-authorization-ledger-v1",
        "ledger_version": DECISION_VERSION,
        "packet_sha256": packet_sha,
        "authorizations": [item.model_dump(mode="json") for item in authorizations],
        "cumulative_authorization_sha256": content_sha256(
            [item.authorization_sha256 for item in authorizations]
        ),
    }
    auth_ledger = BatchAuthorizationLedger.model_validate(
        _with_hash(auth_ledger_body, "ledger_sha256")
    )

    if existing_authorization is None:
        for entry in entries:
            attestation_body: dict[str, Any] = {
                "schema_version": "pvr-canonical-authority-owner-attestation-v2",
                "candidate_id": entry.candidate.candidate_id,
                "packet_sha256": packet_sha,
                "catalog_version": packet.catalog_version,
                "catalog_sha256": packet.catalog_sha256,
                "catalog_record_sha256": entry.catalog_record_sha256,
                "outcome": "reviewed",
                "confirmation_method": "owner_attestation",
                "resolver_output_consulted": False,
                "reviewed_by_role": "project_owner",
                "reviewed_at": timestamp.isoformat().replace("+00:00", "Z"),
                "review_reason": REVIEW_REASON,
                "batch_authorization_sha256": authorization.authorization_sha256,
            }
            attestation = OwnerAttestationV2.model_validate(
                _with_hash(attestation_body, "attestation_sha256")
            )
            attestations.append(attestation)
            event_body: dict[str, Any] = {
                "schema_version": "pvr-canonical-authority-review-event-v2",
                "event_id": (f"car-t5-g1-batch-{batch_ordinal}-ordinal-{entry.ordinal:02d}"),
                "candidate_id": entry.candidate.candidate_id,
                "from_status": "staged",
                "to_status": "reviewed",
                "packet_sha256": packet_sha,
                "catalog_version": packet.catalog_version,
                "catalog_sha256": packet.catalog_sha256,
                "canonical_uuid": str(entry.candidate.canonical_uuid),
                "catalog_record_sha256": entry.catalog_record_sha256,
                "variant_field_evidence": [
                    row.model_dump(mode="json") for row in entry.field_evidence
                ],
                "source_decision_ids": ["fandom-hot-wheels-2025-pilot-r790665-v1"],
                "confirmation_method": "owner_attestation",
                "attestation_sha256": attestation.attestation_sha256,
                "batch_authorization_sha256": authorization.authorization_sha256,
                "resolver_output_consulted": False,
                "reviewed_by_role": "project_owner",
                "reviewed_at": timestamp.isoformat().replace("+00:00", "Z"),
                "review_reason": REVIEW_REASON,
                "remediation_note": None,
            }
            events.append(
                AuthorityReviewEventV2.model_validate(_with_hash(event_body, "event_sha256"))
            )

    attestations.sort(key=lambda item: item.candidate_id)
    events.sort(key=lambda item: item.candidate_id)
    attestation_ledger_body = {
        "schema_version": "pvr-canonical-authority-owner-attestation-ledger-v1",
        "ledger_version": DECISION_VERSION,
        "packet_sha256": packet_sha,
        "attestations": [item.model_dump(mode="json") for item in attestations],
        "cumulative_attestation_sha256": content_sha256(
            [item.attestation_sha256 for item in attestations]
        ),
    }
    if len(authorizations) == 1:
        attestation_ledger_body["batch_authorization_sha256"] = authorizations[
            0
        ].authorization_sha256
    else:
        attestation_ledger_body["batch_authorization_sha256s"] = [
            item.authorization_sha256 for item in authorizations
        ]
    attestation_ledger = OwnerAttestationLedger.model_validate(
        _with_hash(attestation_ledger_body, "ledger_sha256")
    )

    event_by_candidate = {event.candidate_id: event for event in events}
    candidate_states: list[AuthorityCandidateState] = []
    reviewed_ids = set(event_by_candidate)
    for entry in packet.entries:
        event = event_by_candidate.get(entry.candidate.candidate_id)
        if entry.candidate.canonical_uuid is None:
            raise AuthorityContractError("T5-G1 candidate lost its applied catalog UUID")
        candidate_states.append(
            AuthorityCandidateState(
                ordinal=entry.ordinal,
                candidate_id=entry.candidate.candidate_id,
                canonical_uuid=entry.candidate.canonical_uuid,
                entry_sha256=entry.entry_sha256,
                catalog_record_sha256=entry.catalog_record_sha256,
                status=(
                    ReviewStatus.reviewed
                    if entry.candidate.candidate_id in reviewed_ids
                    else ReviewStatus.staged
                ),
                latest_event_id=event.event_id if event else None,
                latest_event_sha256=event.event_sha256 if event else None,
            )
        )
    reviewed_count = len(events)
    state_body = {
        "schema_version": "pvr-canonical-authority-candidate-state-v1",
        "state_version": DECISION_VERSION,
        "packet_sha256": packet_sha,
        "catalog_version": packet.catalog_version,
        "catalog_sha256": packet.catalog_sha256,
        "candidates": [item.model_dump(mode="json") for item in candidate_states],
        "status_counts": {
            "staged": len(packet.entries) - reviewed_count,
            "reviewed": reviewed_count,
            "approved_exact": 0,
        },
        "resolver_output_consulted": False,
        "network_requests": 0,
        "rhb_t5_authorized": False,
    }
    candidate_file = AuthorityCandidateStateFile.model_validate(
        _with_hash(state_body, "state_sha256")
    )
    event_file_body = {
        "schema_version": "pvr-canonical-authority-review-event-ledger-v1",
        "ledger_version": DECISION_VERSION,
        "packet_sha256": packet_sha,
        "catalog_version": packet.catalog_version,
        "catalog_sha256": packet.catalog_sha256,
        "events": [event.model_dump(mode="json") for event in events],
        "batch_authorization_count": len(authorizations),
        "owner_attestation_count": len(attestations),
        "review_event_count": len(events),
        "status_counts": {"reviewed": reviewed_count, "approved_exact": 0},
        "cumulative_event_sha256": content_sha256([event.event_sha256 for event in events]),
        "resolver_output_consulted": False,
        "network_requests": 0,
        "rhb_t5_authorized": False,
    }
    event_file = AuthorityReviewEventFile.model_validate(
        _with_hash(event_file_body, "ledger_sha256")
    )
    outputs = {
        AUTHORIZATION_LEDGER_REFERENCE: stable_json_bytes(auth_ledger.model_dump(mode="json")),
        ATTESTATION_LEDGER_REFERENCE: stable_json_bytes(
            attestation_ledger.model_dump(mode="json", exclude_none=True)
        ),
        AUTHORITY_CANDIDATES_REFERENCE: stable_json_bytes(candidate_file.model_dump(mode="json")),
        REVIEW_EVENTS_REFERENCE: stable_json_bytes(event_file.model_dump(mode="json")),
    }
    _validate_public_outputs(
        outputs[AUTHORITY_CANDIDATES_REFERENCE],
        outputs[REVIEW_EVENTS_REFERENCE],
        authorizations,
    )
    return outputs


def _validate_public_outputs(
    candidates: bytes,
    events: bytes,
    authorizations: list[BatchOwnerAuthorization],
) -> None:
    combined = candidates + events
    private_responses = {
        encoded
        for authorization in authorizations
        for response in (
            authorization.owner_response_verbatim,
            authorization.authorized_exact_owner_response,
        )
        for encoded in (
            response.encode("utf-8"),
            json.dumps(response, ensure_ascii=False)[1:-1].encode("utf-8"),
        )
    }
    if any(response in combined for response in private_responses):
        raise AuthorityContractError("public decision artifact contains owner verbatim")
    for forbidden in (
        b"owner_response_verbatim",
        b"authorized_exact_owner_response",
        b"response_verbatim_sha256",
        b"approved-authority",
        b"authority-manifest",
    ):
        if forbidden in combined:
            raise AuthorityContractError("public decision artifact contains private authorization")
    if b"@example.com" in combined:
        raise AuthorityContractError("public decision artifact contains PII")


def _target_states(root: Path) -> dict[Path, bool]:
    return {
        reference: (_safe_path(root, reference, allow_missing_leaf=True).exists())
        for reference in (
            AUTHORIZATION_LEDGER_REFERENCE,
            ATTESTATION_LEDGER_REFERENCE,
            AUTHORITY_CANDIDATES_REFERENCE,
            REVIEW_EVENTS_REFERENCE,
        )
    }


def record_t5_g1_batch_review(
    root: Path,
    *,
    owner_response_verbatim: str,
    authorized_exact_owner_response: str,
    batch_ordinal: int = EXPECTED_BATCH_ORDINAL,
    expected_outcome: str = "reviewed",
    reviewed_at: datetime | None = None,
    check: bool = False,
) -> Literal["created", "unchanged"]:
    root = root.absolute()
    _require_ignore_rule(root)
    for forbidden in (FORBIDDEN_AUTHORITY_REFERENCE, FORBIDDEN_AUTHORITY_MANIFEST_REFERENCE):
        path = _safe_path(root, forbidden, allow_missing_leaf=True)
        if path.exists() or path.is_symlink():
            raise AuthorityContractError("T5-G1 cannot coexist with a frozen authority bundle")
    states = _target_states(root)
    if any(states.values()) and not all(states.values()):
        raise AuthorityContractError("partial CAR-T5 decision artifact state")
    materialized = all(states.values())
    if check and not materialized:
        raise AuthorityContractError(
            f"CAR-T5 Batch {batch_ordinal} decision artifacts are not materialized"
        )

    existing = _load_existing_outputs(root) if materialized else None
    if materialized:
        if existing is None:  # pragma: no cover - materialized and loader result are coupled
            raise AuthorityContractError("CAR-T5 decision artifacts could not be loaded")
        if stat.S_IMODE((root / PRIVATE_DIRECTORY).stat().st_mode) != 0o700:
            raise AuthorityContractError("CAR-T5 private workspace permissions are unsafe")
        for reference in states:
            target = _safe_path(root, reference, allow_missing_leaf=False)
            expected_mode = 0o600 if reference.parent == PRIVATE_DIRECTORY else 0o644
            if target.is_symlink() or not target.is_file():
                raise AuthorityContractError("CAR-T5 decision target is not a regular file")
            if stat.S_IMODE(target.stat().st_mode) != expected_mode:
                raise AuthorityContractError("CAR-T5 decision artifact permissions are unsafe")
        recorded_batches = {item.batch_ordinal for item in existing[0].authorizations}
        if check and batch_ordinal not in recorded_batches:
            raise AuthorityContractError(
                f"CAR-T5 Batch {batch_ordinal} decision is not materialized"
            )

    timestamp = reviewed_at
    if existing is not None and timestamp is None:
        recorded = next(
            (item for item in existing[0].authorizations if item.batch_ordinal == batch_ordinal),
            None,
        )
        if recorded is not None:
            timestamp = recorded.authorized_at
    timestamp = timestamp or datetime.now(UTC).replace(microsecond=0)
    outputs = _build_outputs(
        root,
        owner_response_verbatim=owner_response_verbatim,
        authorized_exact_owner_response=authorized_exact_owner_response,
        reviewed_at=timestamp,
        batch_ordinal=batch_ordinal,
        expected_outcome=expected_outcome,
        existing=existing,
    )
    targets = {
        reference: _safe_path(root, reference, allow_missing_leaf=True) for reference in outputs
    }
    if materialized and all(
        targets[reference].read_bytes() == outputs[reference] for reference in outputs
    ):
        return "unchanged"
    if check:
        raise AuthorityContractError(
            f"CAR-T5 Batch {batch_ordinal} decision artifacts differ from the expected state"
        )

    temps: list[Path] = []
    installed: list[Path] = []
    original_bytes = {
        reference: targets[reference].read_bytes() for reference in outputs if materialized
    }
    try:
        for reference, payload in outputs.items():
            target = targets[reference]
            mode = 0o600 if reference.parent == PRIVATE_DIRECTORY else 0o644
            temps.append(_write_temp(target, payload, mode))
        for (reference, target), temp in zip(targets.items(), temps, strict=True):
            os.replace(temp, target)
            installed.append(target)
            mode = 0o600 if reference.parent == PRIVATE_DIRECTORY else 0o644
            os.chmod(target, mode)
            _fsync_directory(target.parent)
    except BaseException:
        for temp in temps:
            if temp.exists() and not temp.is_symlink():
                temp.unlink()
        for target in reversed(installed):
            reference = next(item for item, path in targets.items() if path == target)
            if materialized:
                mode = 0o600 if reference.parent == PRIVATE_DIRECTORY else 0o644
                rollback = _write_temp(target, original_bytes[reference], mode)
                os.replace(rollback, target)
                os.chmod(target, mode)
                _fsync_directory(target.parent)
            elif target.exists() and not target.is_symlink():
                target.unlink()
                _fsync_directory(target.parent)
        raise
    return "created"


__all__ = [
    "ATTESTATION_LEDGER_REFERENCE",
    "AUTHORITY_CANDIDATES_REFERENCE",
    "AUTHORIZATION_LEDGER_REFERENCE",
    "REVIEW_EVENTS_REFERENCE",
    "AuthorityCandidateStateFile",
    "AuthorityReviewEventFile",
    "BatchAuthorizationLedger",
    "OwnerAttestationLedger",
    "record_t5_g1_batch_review",
]
