"""Append-only CAR-T5 owner-Gate decision recording.

This first recorder is intentionally bounded to T5-G1 family Batch 2.  It records three
``staged -> reviewed`` outcomes and cannot create exact authority or authorize RHB-T5.
"""

from __future__ import annotations

import hashlib
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
EXPECTED_ENTRY_ORDINALS = (2, 11, 18)
EXPECTED_TOY_IDENTIFIERS = ("HYW70", "HYX67", "HYY31")
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
    batch_authorization_sha256: Sha256
    attestations: list[OwnerAttestationV2] = Field(min_length=3, max_length=3)
    cumulative_attestation_sha256: Sha256
    ledger_sha256: Sha256

    @model_validator(mode="after")
    def attestations_are_ordered_and_batch_bound(self) -> OwnerAttestationLedger:
        ids = [item.candidate_id for item in self.attestations]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("owner attestations must be distinct and ordered")
        if any(
            item.batch_authorization_sha256 != self.batch_authorization_sha256
            for item in self.attestations
        ):
            raise ValueError("owner attestations must reference one batch authorization")
        hashes = [item.attestation_sha256 for item in self.attestations]
        if self.cumulative_attestation_sha256 != content_sha256(hashes):
            raise ValueError("owner attestation cumulative checksum is stale")
        expected = content_sha256(self.model_dump(mode="json", exclude={"ledger_sha256"}))
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
    events: list[AuthorityReviewEventV2] = Field(min_length=3, max_length=3)
    batch_authorization_count: Literal[1]
    owner_attestation_count: Literal[3]
    review_event_count: Literal[3]
    status_counts: dict[Literal["reviewed", "approved_exact"], int]
    cumulative_event_sha256: Sha256
    resolver_output_consulted: Literal[False]
    network_requests: Literal[0]
    rhb_t5_authorized: Literal[False]
    ledger_sha256: Sha256

    @model_validator(mode="after")
    def events_are_one_partial_batch(self) -> AuthorityReviewEventFile:
        ids = [event.candidate_id for event in self.events]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("review events must be distinct and ordered")
        batch_hashes = {event.batch_authorization_sha256 for event in self.events}
        if len(batch_hashes) != 1:
            raise ValueError("partial review events must reference one batch authorization")
        if any(
            event.from_status != ReviewStatus.staged or event.to_status != ReviewStatus.reviewed
            for event in self.events
        ):
            raise ValueError("T5-G1 partial events must be staged to reviewed")
        if self.status_counts != {"reviewed": 3, "approved_exact": 0}:
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


def _selected_batch(packet: AuthorityReviewPreparationPacket) -> tuple[Any, list[Any]]:
    batch = packet.family_batches[EXPECTED_BATCH_ORDINAL - 1]
    if (
        batch.batch_ordinal != EXPECTED_BATCH_ORDINAL
        or tuple(batch.entry_ordinals) != EXPECTED_ENTRY_ORDINALS
        or batch.family_group_key != "car-t3-family-draftnator"
    ):
        raise AuthorityContractError("T5-G1 authorization does not match frozen Batch 2")
    by_ordinal = {entry.ordinal: entry for entry in packet.entries}
    entries = [by_ordinal[ordinal] for ordinal in batch.entry_ordinals]
    identifiers = tuple(entry.catalog_record.identifiers[0] for entry in entries)
    if identifiers != EXPECTED_TOY_IDENTIFIERS:
        raise AuthorityContractError("T5-G1 Batch 2 toy identifiers are stale")
    if batch.candidate_ids != [entry.candidate.candidate_id for entry in entries]:
        raise AuthorityContractError("T5-G1 Batch 2 candidate order is stale")
    if batch.entry_sha256s != [entry.entry_sha256 for entry in entries]:
        raise AuthorityContractError("T5-G1 Batch 2 entry hashes are stale")
    return batch, entries


def _build_outputs(
    root: Path,
    *,
    owner_response_verbatim: str,
    authorized_exact_owner_response: str,
    reviewed_at: datetime,
    batch_ordinal: int,
    expected_outcome: str,
) -> dict[Path, bytes]:
    if batch_ordinal != EXPECTED_BATCH_ORDINAL:
        raise AuthorityContractError("this bounded recorder accepts only T5-G1 Batch 2")
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
    batch, entries = _selected_batch(packet)
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
    authorization = BatchOwnerAuthorization.model_validate(
        _with_hash(authorization_body, "authorization_sha256")
    )
    validate_batch_owner_authorization(authorization, expected=expected)
    auth_ledger_body = {
        "schema_version": "pvr-canonical-authority-batch-authorization-ledger-v1",
        "ledger_version": DECISION_VERSION,
        "packet_sha256": packet_sha,
        "authorizations": [authorization.model_dump(mode="json")],
        "cumulative_authorization_sha256": content_sha256([authorization.authorization_sha256]),
    }
    auth_ledger = BatchAuthorizationLedger.model_validate(
        _with_hash(auth_ledger_body, "ledger_sha256")
    )

    attestations: list[OwnerAttestationV2] = []
    events: list[AuthorityReviewEventV2] = []
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
            "event_id": f"car-t5-g1-batch-2-ordinal-{entry.ordinal:02d}",
            "candidate_id": entry.candidate.candidate_id,
            "from_status": "staged",
            "to_status": "reviewed",
            "packet_sha256": packet_sha,
            "catalog_version": packet.catalog_version,
            "catalog_sha256": packet.catalog_sha256,
            "canonical_uuid": str(entry.candidate.canonical_uuid),
            "catalog_record_sha256": entry.catalog_record_sha256,
            "variant_field_evidence": [row.model_dump(mode="json") for row in entry.field_evidence],
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
        events.append(AuthorityReviewEventV2.model_validate(_with_hash(event_body, "event_sha256")))

    attestations.sort(key=lambda item: item.candidate_id)
    events.sort(key=lambda item: item.candidate_id)
    attestation_ledger_body = {
        "schema_version": "pvr-canonical-authority-owner-attestation-ledger-v1",
        "ledger_version": DECISION_VERSION,
        "packet_sha256": packet_sha,
        "batch_authorization_sha256": authorization.authorization_sha256,
        "attestations": [item.model_dump(mode="json") for item in attestations],
        "cumulative_attestation_sha256": content_sha256(
            [item.attestation_sha256 for item in attestations]
        ),
    }
    attestation_ledger = OwnerAttestationLedger.model_validate(
        _with_hash(attestation_ledger_body, "ledger_sha256")
    )

    event_by_candidate = {event.candidate_id: event for event in events}
    candidate_states: list[AuthorityCandidateState] = []
    reviewed_ids = set(batch.candidate_ids)
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
    state_body = {
        "schema_version": "pvr-canonical-authority-candidate-state-v1",
        "state_version": DECISION_VERSION,
        "packet_sha256": packet_sha,
        "catalog_version": packet.catalog_version,
        "catalog_sha256": packet.catalog_sha256,
        "candidates": [item.model_dump(mode="json") for item in candidate_states],
        "status_counts": {"staged": 17, "reviewed": 3, "approved_exact": 0},
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
        "batch_authorization_count": 1,
        "owner_attestation_count": 3,
        "review_event_count": 3,
        "status_counts": {"reviewed": 3, "approved_exact": 0},
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
        ATTESTATION_LEDGER_REFERENCE: stable_json_bytes(attestation_ledger.model_dump(mode="json")),
        AUTHORITY_CANDIDATES_REFERENCE: stable_json_bytes(candidate_file.model_dump(mode="json")),
        REVIEW_EVENTS_REFERENCE: stable_json_bytes(event_file.model_dump(mode="json")),
    }
    _validate_public_outputs(
        outputs[AUTHORITY_CANDIDATES_REFERENCE],
        outputs[REVIEW_EVENTS_REFERENCE],
        owner_response_verbatim,
    )
    return outputs


def _validate_public_outputs(candidates: bytes, events: bytes, owner_response: str) -> None:
    combined = candidates + events
    if owner_response.encode("utf-8") in combined:
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
    if check and not all(states.values()):
        raise AuthorityContractError("CAR-T5 Batch 2 decision artifacts are not materialized")

    timestamp = reviewed_at
    if all(states.values()) and timestamp is None:
        private_payload, _ = _strict_json(root / AUTHORIZATION_LEDGER_REFERENCE)
        ledger = BatchAuthorizationLedger.model_validate(private_payload)
        if len(ledger.authorizations) != 1:
            raise AuthorityContractError("bounded T5-G1 recorder requires one authorization")
        timestamp = ledger.authorizations[0].authorized_at
    timestamp = timestamp or datetime.now(UTC).replace(microsecond=0)
    outputs = _build_outputs(
        root,
        owner_response_verbatim=owner_response_verbatim,
        authorized_exact_owner_response=authorized_exact_owner_response,
        reviewed_at=timestamp,
        batch_ordinal=batch_ordinal,
        expected_outcome=expected_outcome,
    )
    targets = {
        reference: _safe_path(root, reference, allow_missing_leaf=True) for reference in outputs
    }
    if all(states.values()):
        if stat.S_IMODE((root / PRIVATE_DIRECTORY).stat().st_mode) != 0o700:
            raise AuthorityContractError("CAR-T5 private workspace permissions are unsafe")
        for reference, target in targets.items():
            if (
                target.is_symlink()
                or not target.is_file()
                or target.read_bytes() != outputs[reference]
            ):
                raise AuthorityContractError("conflicting or tampered CAR-T5 decision replay")
            if (
                reference.parent == PRIVATE_DIRECTORY
                and stat.S_IMODE(target.stat().st_mode) != 0o600
            ):
                raise AuthorityContractError("CAR-T5 private decision permissions are unsafe")
        return "unchanged"
    if check:
        raise AuthorityContractError("CAR-T5 Batch 2 decision artifacts are not materialized")

    temps: list[Path] = []
    installed: list[Path] = []
    try:
        for reference, payload in outputs.items():
            target = targets[reference]
            mode = 0o600 if reference.parent == PRIVATE_DIRECTORY else 0o644
            temps.append(_write_temp(target, payload, mode))
        for (reference, target), temp in zip(targets.items(), temps, strict=True):
            os.replace(temp, target)
            installed.append(target)
            if reference.parent == PRIVATE_DIRECTORY:
                os.chmod(target, 0o600)
            _fsync_directory(target.parent)
    except BaseException:
        for temp in temps:
            if temp.exists() and not temp.is_symlink():
                temp.unlink()
        for target in installed:
            if target.exists() and not target.is_symlink():
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
