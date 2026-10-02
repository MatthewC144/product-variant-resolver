"""Bounded CAR-T5 second-Gate exact-authority decision recording.

The recorder accepts only the supported T5-G2 family-batch prefix after the complete
T5-G1 state. It keeps second-Gate owner text in separate ignored ledgers, appends
``reviewed -> approved_exact`` events, and cannot freeze a bundle or authorize RHB-T5.
"""

from __future__ import annotations

import hashlib
import os
import stat
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.canonical_authority_decisions import (
    ATTESTATION_LEDGER_REFERENCE as G1_ATTESTATION_LEDGER_REFERENCE,
)
from product_variant_resolver.canonical_authority_decisions import (
    AUTHORITY_CANDIDATES_REFERENCE,
    FORBIDDEN_AUTHORITY_MANIFEST_REFERENCE,
    FORBIDDEN_AUTHORITY_REFERENCE,
    REVIEW_EVENTS_REFERENCE,
    AuthorityCandidateState,
    AuthorityCandidateStateFile,
    AuthorityReviewEventFile,
    BatchAuthorizationLedger,
    OwnerAttestationLedger,
)
from product_variant_resolver.canonical_authority_decisions import (
    AUTHORIZATION_LEDGER_REFERENCE as G1_AUTHORIZATION_LEDGER_REFERENCE,
)
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

EXACT_AUTHORIZATION_LEDGER_REFERENCE = PRIVATE_DIRECTORY / "exact-batch-authorizations.json"
EXACT_ATTESTATION_LEDGER_REFERENCE = PRIVATE_DIRECTORY / "exact-owner-attestations.json"
DECISION_VERSION: Literal["canonical-authority-review-t5-g2-v1"] = (
    "canonical-authority-review-t5-g2-v1"
)
SUPPORTED_BATCH_ORDINALS = (1, 2, 3, 4, 5)
DEFAULT_BATCH_ORDINAL: Literal[1] = 1
FROZEN_BATCHES: dict[int, tuple[str, tuple[int, ...], tuple[str, ...]]] = {
    1: ("car-t3-family-mazda-autozam", (1, 10, 16), ("HYX45", "HYY10", "HYW66")),
    2: ("car-t3-family-draftnator", (2, 11, 18), ("HYW70", "HYX67", "HYY31")),
    3: ("car-t3-family-subaru-brz", (3, 8, 14), ("JBB55", "HYY12", "HYW99")),
    4: (
        "car-t3-family-nissan-skyline-2000gt-r-lbwk",
        (4, 13, 20),
        ("HYX54", "HYW79", "HYY30"),
    ),
    5: (
        "car-t3-family-21-ford-bronco",
        (5, 7, 17),
        ("HYY32", "HYW73", "HYX50"),
    ),
}
G2_DECLARATION: Literal[
    "owner_explicitly_authorized_t5_g2_exact_authority_outcomes_for_every_covered_entry"
] = "owner_explicitly_authorized_t5_g2_exact_authority_outcomes_for_every_covered_entry"
EXACT_REASON: Literal[
    "Project owner explicitly approved the exact bound T5-G2 family batch relative to the frozen "
    "community snapshot; color and edition remain null; later Gates remain unauthorized."
] = (
    "Project owner explicitly approved the exact bound T5-G2 family batch relative to the frozen "
    "community snapshot; color and edition remain null; later Gates remain unauthorized."
)

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ExactDecisionContract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class ExactBatchAuthorizationLedger(ExactDecisionContract):
    schema_version: Literal["pvr-canonical-authority-exact-batch-authorization-ledger-v1"]
    ledger_version: Literal["canonical-authority-review-t5-g2-v1"]
    packet_sha256: Sha256
    authorizations: list[BatchOwnerAuthorization] = Field(min_length=1)
    cumulative_authorization_sha256: Sha256
    ledger_sha256: Sha256

    @model_validator(mode="after")
    def exact_authorizations_are_ordered_and_hash_bound(self) -> ExactBatchAuthorizationLedger:
        ordinals = [item.batch_ordinal for item in self.authorizations]
        if ordinals != sorted(set(ordinals)):
            raise ValueError("exact batch authorizations must be distinct and ordered")
        if any(item.gate != "T5-G2" for item in self.authorizations):
            raise ValueError("exact authorization ledger accepts only T5-G2")
        hashes = [item.authorization_sha256 for item in self.authorizations]
        if len(hashes) != len(set(hashes)):
            raise ValueError("exact authorization hashes must be distinct")
        if self.cumulative_authorization_sha256 != content_sha256(hashes):
            raise ValueError("exact authorization cumulative checksum is stale")
        expected = content_sha256(self.model_dump(mode="json", exclude={"ledger_sha256"}))
        if self.ledger_sha256 != expected:
            raise ValueError("exact authorization ledger checksum is stale")
        return self


class ExactOwnerAttestationLedger(ExactDecisionContract):
    schema_version: Literal["pvr-canonical-authority-exact-owner-attestation-ledger-v1"]
    ledger_version: Literal["canonical-authority-review-t5-g2-v1"]
    packet_sha256: Sha256
    batch_authorization_sha256s: list[Sha256] = Field(min_length=1)
    attestations: list[OwnerAttestationV2] = Field(min_length=1)
    cumulative_attestation_sha256: Sha256
    ledger_sha256: Sha256

    @model_validator(mode="after")
    def exact_attestations_are_ordered_and_hash_bound(self) -> ExactOwnerAttestationLedger:
        ids = [item.candidate_id for item in self.attestations]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("exact owner attestations must be distinct and ordered")
        hashes = self.batch_authorization_sha256s
        if hashes != sorted(set(hashes)):
            raise ValueError("exact attestation authorization hashes must be distinct and ordered")
        if {item.batch_authorization_sha256 for item in self.attestations} != set(hashes):
            raise ValueError("exact attestations must reference every declared authorization")
        if any(item.outcome != ReviewStatus.approved_exact for item in self.attestations):
            raise ValueError("exact attestation ledger accepts only approved_exact")
        attestation_hashes = [item.attestation_sha256 for item in self.attestations]
        if self.cumulative_attestation_sha256 != content_sha256(attestation_hashes):
            raise ValueError("exact attestation cumulative checksum is stale")
        expected = content_sha256(self.model_dump(mode="json", exclude={"ledger_sha256"}))
        if self.ledger_sha256 != expected:
            raise ValueError("exact attestation ledger checksum is stale")
        return self


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _with_hash(body: dict[str, Any], key: str) -> dict[str, Any]:
    return {**body, key: content_sha256(body)}


def _selected_batch(
    packet: AuthorityReviewPreparationPacket, batch_ordinal: int
) -> tuple[Any, list[Any]]:
    expected = FROZEN_BATCHES.get(batch_ordinal)
    if expected is None:
        raise AuthorityContractError("this bounded exact recorder accepts only T5-G2 Batches 1-5")
    family_group_key, entry_ordinals, toy_identifiers = expected
    batch = packet.family_batches[batch_ordinal - 1]
    if (
        batch.batch_ordinal != batch_ordinal
        or batch.family_group_key != family_group_key
        or tuple(batch.entry_ordinals) != entry_ordinals
    ):
        raise AuthorityContractError(
            f"T5-G2 Batch {batch_ordinal} differs from the frozen family batch"
        )
    entries_by_ordinal = {entry.ordinal: entry for entry in packet.entries}
    entries = [entries_by_ordinal[ordinal] for ordinal in batch.entry_ordinals]
    identifiers = tuple(entry.catalog_record.identifiers[0] for entry in entries)
    if identifiers != toy_identifiers:
        raise AuthorityContractError(f"T5-G2 Batch {batch_ordinal} toy identifiers are stale")
    if batch.candidate_ids != [entry.candidate.candidate_id for entry in entries]:
        raise AuthorityContractError(f"T5-G2 Batch {batch_ordinal} candidate order is stale")
    if batch.entry_sha256s != [entry.entry_sha256 for entry in entries]:
        raise AuthorityContractError(f"T5-G2 Batch {batch_ordinal} entry hashes are stale")
    return batch, entries


def _load_required_state(
    root: Path,
) -> tuple[
    BatchAuthorizationLedger,
    OwnerAttestationLedger,
    AuthorityCandidateStateFile,
    AuthorityReviewEventFile,
]:
    authorization_payload, _ = _strict_json(root / G1_AUTHORIZATION_LEDGER_REFERENCE)
    attestation_payload, _ = _strict_json(root / G1_ATTESTATION_LEDGER_REFERENCE)
    candidate_payload, _ = _strict_json(root / AUTHORITY_CANDIDATES_REFERENCE)
    event_payload, _ = _strict_json(root / REVIEW_EVENTS_REFERENCE)
    return (
        BatchAuthorizationLedger.model_validate(authorization_payload),
        OwnerAttestationLedger.model_validate(attestation_payload),
        AuthorityCandidateStateFile.model_validate(candidate_payload),
        AuthorityReviewEventFile.model_validate(event_payload),
    )


def _load_exact_state(
    root: Path,
) -> tuple[ExactBatchAuthorizationLedger, ExactOwnerAttestationLedger]:
    authorization_payload, _ = _strict_json(root / EXACT_AUTHORIZATION_LEDGER_REFERENCE)
    attestation_payload, _ = _strict_json(root / EXACT_ATTESTATION_LEDGER_REFERENCE)
    return (
        ExactBatchAuthorizationLedger.model_validate(authorization_payload),
        ExactOwnerAttestationLedger.model_validate(attestation_payload),
    )


def _validate_g1_and_public_state(
    packet: AuthorityReviewPreparationPacket,
    packet_sha: str,
    g1_authorizations: BatchAuthorizationLedger,
    g1_attestations: OwnerAttestationLedger,
    candidates: AuthorityCandidateStateFile,
    events: AuthorityReviewEventFile,
    exact_state: tuple[ExactBatchAuthorizationLedger, ExactOwnerAttestationLedger] | None,
    target_batch_ordinal: int,
) -> None:
    if [item.batch_ordinal for item in g1_authorizations.authorizations] != list(range(1, 8)):
        raise AuthorityContractError("T5-G2 requires all seven T5-G1 authorizations")
    if any(item.gate != "T5-G1" for item in g1_authorizations.authorizations):
        raise AuthorityContractError("T5-G1 authorization ledger contains a different Gate")
    if len(g1_attestations.attestations) != 20:
        raise AuthorityContractError("T5-G2 requires all 20 T5-G1 attestations")
    if (
        g1_authorizations.packet_sha256 != packet_sha
        or g1_attestations.packet_sha256 != packet_sha
        or candidates.packet_sha256 != packet_sha
        or events.packet_sha256 != packet_sha
    ):
        raise AuthorityContractError("T5-G2 inputs differ from the frozen packet")
    if (
        candidates.catalog_sha256 != packet.catalog_sha256
        or events.catalog_sha256 != packet.catalog_sha256
    ):
        raise AuthorityContractError("T5-G2 public state differs from the frozen catalog")

    g1_events = [event for event in events.events if event.event_id.startswith("car-t5-g1-")]
    exact_events = [event for event in events.events if event.event_id.startswith("car-t5-g2-")]
    if len(g1_events) != 20:
        raise AuthorityContractError("T5-G2 requires exactly 20 T5-G1 events")
    if len({event.candidate_id for event in g1_events}) != 20:
        raise AuthorityContractError("T5-G1 events do not cover 20 distinct candidates")

    g1_attestation_by_id = {item.candidate_id: item for item in g1_attestations.attestations}
    g1_authorization_hashes = {
        item.authorization_sha256 for item in g1_authorizations.authorizations
    }
    for event in g1_events:
        attestation = g1_attestation_by_id.get(event.candidate_id)
        if (
            event.from_status != ReviewStatus.staged
            or event.to_status != ReviewStatus.reviewed
            or attestation is None
            or event.attestation_sha256 != attestation.attestation_sha256
            or event.batch_authorization_sha256 != attestation.batch_authorization_sha256
            or event.batch_authorization_sha256 not in g1_authorization_hashes
        ):
            raise AuthorityContractError("T5-G1 event chain is incomplete or inconsistent")

    latest_by_candidate: dict[str, AuthorityReviewEventV2] = {}
    for event in events.events:
        latest_by_candidate[event.candidate_id] = event
    if set(latest_by_candidate) != {item.candidate_id for item in candidates.candidates}:
        raise AuthorityContractError("candidate state and review-event coverage differ")
    for candidate in candidates.candidates:
        latest = latest_by_candidate[candidate.candidate_id]
        if (
            candidate.status != latest.to_status
            or candidate.latest_event_id != latest.event_id
            or candidate.latest_event_sha256 != latest.event_sha256
        ):
            raise AuthorityContractError("candidate state differs from its latest review event")

    if exact_state is None:
        if target_batch_ordinal != 1:
            raise AuthorityContractError("T5-G2 exact batches must be appended in prefix order")
        if exact_events or candidates.status_counts != {
            "staged": 0,
            "reviewed": 20,
            "approved_exact": 0,
        }:
            raise AuthorityContractError("T5-G2 requires the complete untouched T5-G1 state")
        return

    exact_authorizations, exact_attestations = exact_state
    if (
        exact_authorizations.packet_sha256 != packet_sha
        or exact_attestations.packet_sha256 != packet_sha
    ):
        raise AuthorityContractError("existing T5-G2 private state differs from the packet")
    exact_ordinals = [item.batch_ordinal for item in exact_authorizations.authorizations]
    if exact_ordinals != list(range(1, len(exact_ordinals) + 1)) or any(
        ordinal not in SUPPORTED_BATCH_ORDINALS for ordinal in exact_ordinals
    ):
        raise AuthorityContractError("existing T5-G2 authorizations are not the supported prefix")
    if (
        target_batch_ordinal not in exact_ordinals
        and target_batch_ordinal != len(exact_ordinals) + 1
    ):
        raise AuthorityContractError("T5-G2 exact batches must be appended in prefix order")

    g1_by_ordinal = {item.batch_ordinal: item for item in g1_authorizations.authorizations}
    expected_entries: dict[str, tuple[Any, str, int]] = {}
    for authorization in exact_authorizations.authorizations:
        batch, entries = _selected_batch(packet, authorization.batch_ordinal)
        prior_response_hashes = [
            g1_by_ordinal[authorization.batch_ordinal].response_verbatim_sha256
        ]
        expected = ExpectedBatchOwnerAuthorization(
            gate="T5-G2",
            authorization_scope="reviewed_to_approved_exact",
            authorization_declaration=G2_DECLARATION,
            expected_outcome=ReviewStatus.approved_exact,
            batch_ordinal=batch.batch_ordinal,
            family_batch_sha256=batch.batch_sha256,
            catalog_application_manifest_sha256=packet.catalog_application_manifest_sha256,
            exact_external_response=authorization.authorized_exact_owner_response,
            exact_external_response_sha256=_sha256_text(
                authorization.authorized_exact_owner_response
            ),
            prior_gate_response_sha256s=prior_response_hashes,
        )
        validate_batch_owner_authorization(authorization, expected=expected)
        if (
            authorization.ordered_candidate_ids != batch.candidate_ids
            or authorization.ordered_entry_sha256s != batch.entry_sha256s
        ):
            raise AuthorityContractError("existing T5-G2 authorization differs from frozen batch")
        for entry in entries:
            if entry.candidate.candidate_id in expected_entries:
                raise AuthorityContractError("existing T5-G2 batches overlap candidates")
            expected_entries[entry.candidate.candidate_id] = (
                entry,
                authorization.authorization_sha256,
                authorization.batch_ordinal,
            )

    expected_exact_count = len(expected_entries)
    if (
        len(exact_attestations.attestations) != expected_exact_count
        or len(exact_events) != expected_exact_count
    ):
        raise AuthorityContractError("existing T5-G2 prefix has incomplete decisions")
    exact_attestation_by_id = {item.candidate_id: item for item in exact_attestations.attestations}
    exact_event_by_id = {item.candidate_id: item for item in exact_events}
    if set(exact_attestation_by_id) != set(expected_entries) or set(exact_event_by_id) != set(
        expected_entries
    ):
        raise AuthorityContractError("existing T5-G2 decisions differ from frozen prefix")
    for candidate_id, (entry, authorization_sha256, batch_ordinal) in expected_entries.items():
        attestation = exact_attestation_by_id[candidate_id]
        event = exact_event_by_id[candidate_id]
        expected_event_id = f"car-t5-g2-batch-{batch_ordinal}-ordinal-{entry.ordinal:02d}"
        if (
            event.from_status != ReviewStatus.reviewed
            or event.to_status != ReviewStatus.approved_exact
            or event.event_id != expected_event_id
            or event.packet_sha256 != packet_sha
            or event.catalog_version != packet.catalog_version
            or event.catalog_sha256 != packet.catalog_sha256
            or event.canonical_uuid != entry.candidate.canonical_uuid
            or event.catalog_record_sha256 != entry.catalog_record_sha256
            or event.variant_field_evidence != entry.field_evidence
            or event.attestation_sha256 != attestation.attestation_sha256
            or event.batch_authorization_sha256 != attestation.batch_authorization_sha256
            or event.batch_authorization_sha256 != authorization_sha256
            or event.reviewed_at != attestation.reviewed_at
            or event.review_reason != EXACT_REASON
            or event.remediation_note is not None
            or attestation.packet_sha256 != packet_sha
            or attestation.catalog_version != packet.catalog_version
            or attestation.catalog_sha256 != packet.catalog_sha256
            or attestation.catalog_record_sha256 != entry.catalog_record_sha256
            or attestation.outcome != ReviewStatus.approved_exact
            or attestation.review_reason != EXACT_REASON
        ):
            raise AuthorityContractError("existing T5-G2 event chain is inconsistent")
    if candidates.status_counts != {
        "staged": 0,
        "reviewed": 20 - expected_exact_count,
        "approved_exact": expected_exact_count,
    }:
        raise AuthorityContractError("existing T5-G2 candidate counts are stale")


def _build_outputs(
    root: Path,
    *,
    owner_response_verbatim: str,
    authorized_exact_owner_response: str,
    reviewed_at: datetime,
    batch_ordinal: int,
    expected_outcome: str,
    exact_state: tuple[ExactBatchAuthorizationLedger, ExactOwnerAttestationLedger] | None,
) -> dict[Path, bytes]:
    if batch_ordinal not in SUPPORTED_BATCH_ORDINALS:
        raise AuthorityContractError("this bounded exact recorder accepts only T5-G2 Batches 1-5")
    if expected_outcome != "approved_exact":
        raise AuthorityContractError("this bounded exact recorder accepts only approved_exact")
    if reviewed_at.tzinfo is None or reviewed_at.utcoffset() is None:
        raise AuthorityContractError("exact review timestamp must be timezone-aware")
    timestamp = reviewed_at.astimezone(UTC).replace(microsecond=0)
    if timestamp != reviewed_at:
        raise AuthorityContractError("exact review timestamp must already be whole-second UTC")

    if prepare_authority_review(root, check=True) != "unchanged":
        raise AuthorityContractError("CAR-T5 preparation is not frozen")
    packet, _owner_markdown, preparation_manifest = build_authority_review_preparation(root)
    packet_sha = content_sha256(packet.model_dump(mode="json"))
    if packet_sha != preparation_manifest.private_packet_sha256:
        raise AuthorityContractError("CAR-T5 preparation packet checksum is stale")
    batch, entries = _selected_batch(packet, batch_ordinal)
    g1_authorizations, g1_attestations, candidates, events = _load_required_state(root)
    _validate_g1_and_public_state(
        packet,
        packet_sha,
        g1_authorizations,
        g1_attestations,
        candidates,
        events,
        exact_state,
        batch_ordinal,
    )

    prior_g1 = next(
        item for item in g1_authorizations.authorizations if item.batch_ordinal == batch_ordinal
    )
    prior_response_hashes = [prior_g1.response_verbatim_sha256]
    response_sha = _sha256_text(authorized_exact_owner_response)
    expected = ExpectedBatchOwnerAuthorization(
        gate="T5-G2",
        authorization_scope="reviewed_to_approved_exact",
        authorization_declaration=G2_DECLARATION,
        expected_outcome=ReviewStatus.approved_exact,
        batch_ordinal=batch.batch_ordinal,
        family_batch_sha256=batch.batch_sha256,
        catalog_application_manifest_sha256=packet.catalog_application_manifest_sha256,
        exact_external_response=authorized_exact_owner_response,
        exact_external_response_sha256=response_sha,
        prior_gate_response_sha256s=prior_response_hashes,
    )
    authorization_body: dict[str, Any] = {
        "schema_version": "pvr-canonical-authority-batch-owner-authorization-v1",
        "gate": "T5-G2",
        "authorization_scope": "reviewed_to_approved_exact",
        "authorization_declaration": G2_DECLARATION,
        "packet_sha256": packet_sha,
        "batch_ordinal": batch.batch_ordinal,
        "family_batch_sha256": batch.batch_sha256,
        "catalog_application_manifest_sha256": packet.catalog_application_manifest_sha256,
        "catalog_version": packet.catalog_version,
        "catalog_sha256": packet.catalog_sha256,
        "ordered_candidate_ids": batch.candidate_ids,
        "ordered_entry_sha256s": batch.entry_sha256s,
        "declared_outcome": "approved_exact",
        "owner_response_verbatim": owner_response_verbatim,
        "authorized_exact_owner_response": authorized_exact_owner_response,
        "response_verbatim_sha256": _sha256_text(owner_response_verbatim),
        "prior_gate_response_sha256s": prior_response_hashes,
        "confirmation_method": "owner_attestation",
        "reviewed_by_role": "project_owner",
        "authorized_at": timestamp.isoformat().replace("+00:00", "Z"),
        "resolver_output_consulted": False,
    }
    proposed_authorization = BatchOwnerAuthorization.model_validate(
        _with_hash(authorization_body, "authorization_sha256")
    )
    validate_batch_owner_authorization(proposed_authorization, expected=expected)

    existing_authorizations = list(exact_state[0].authorizations) if exact_state is not None else []
    existing_authorization = next(
        (item for item in existing_authorizations if item.batch_ordinal == batch_ordinal), None
    )
    exact_attestations: list[OwnerAttestationV2] = []
    if existing_authorization is not None:
        validate_batch_owner_authorization(existing_authorization, expected=expected)
        if existing_authorization != proposed_authorization:
            raise AuthorityContractError(
                f"conflicting or tampered T5-G2 Batch {batch_ordinal} replay"
            )
    if exact_state is not None:
        exact_attestations = list(exact_state[1].attestations)
    authorization = existing_authorization or proposed_authorization
    if existing_authorization is None:
        existing_authorizations.append(authorization)
    existing_authorizations.sort(key=lambda item: item.batch_ordinal)

    authorization_ledger_body = {
        "schema_version": "pvr-canonical-authority-exact-batch-authorization-ledger-v1",
        "ledger_version": DECISION_VERSION,
        "packet_sha256": packet_sha,
        "authorizations": [item.model_dump(mode="json") for item in existing_authorizations],
        "cumulative_authorization_sha256": content_sha256(
            [item.authorization_sha256 for item in existing_authorizations]
        ),
    }
    authorization_ledger = ExactBatchAuthorizationLedger.model_validate(
        _with_hash(authorization_ledger_body, "ledger_sha256")
    )

    public_events = list(events.events)
    if existing_authorization is None:
        for entry in entries:
            attestation_body: dict[str, Any] = {
                "schema_version": "pvr-canonical-authority-owner-attestation-v2",
                "candidate_id": entry.candidate.candidate_id,
                "packet_sha256": packet_sha,
                "catalog_version": packet.catalog_version,
                "catalog_sha256": packet.catalog_sha256,
                "catalog_record_sha256": entry.catalog_record_sha256,
                "outcome": "approved_exact",
                "confirmation_method": "owner_attestation",
                "resolver_output_consulted": False,
                "reviewed_by_role": "project_owner",
                "reviewed_at": timestamp.isoformat().replace("+00:00", "Z"),
                "review_reason": EXACT_REASON,
                "batch_authorization_sha256": authorization.authorization_sha256,
            }
            attestation = OwnerAttestationV2.model_validate(
                _with_hash(attestation_body, "attestation_sha256")
            )
            exact_attestations.append(attestation)
            event_body: dict[str, Any] = {
                "schema_version": "pvr-canonical-authority-review-event-v2",
                "event_id": (f"car-t5-g2-batch-{batch_ordinal}-ordinal-{entry.ordinal:02d}"),
                "candidate_id": entry.candidate.candidate_id,
                "from_status": "reviewed",
                "to_status": "approved_exact",
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
                "review_reason": EXACT_REASON,
                "remediation_note": None,
            }
            public_events.append(
                AuthorityReviewEventV2.model_validate(_with_hash(event_body, "event_sha256"))
            )

    exact_attestations.sort(key=lambda item: item.candidate_id)
    exact_attestation_ledger_body = {
        "schema_version": "pvr-canonical-authority-exact-owner-attestation-ledger-v1",
        "ledger_version": DECISION_VERSION,
        "packet_sha256": packet_sha,
        "batch_authorization_sha256s": sorted(
            item.authorization_sha256 for item in existing_authorizations
        ),
        "attestations": [item.model_dump(mode="json") for item in exact_attestations],
        "cumulative_attestation_sha256": content_sha256(
            [item.attestation_sha256 for item in exact_attestations]
        ),
    }
    exact_attestation_ledger = ExactOwnerAttestationLedger.model_validate(
        _with_hash(exact_attestation_ledger_body, "ledger_sha256")
    )

    public_events.sort(key=lambda item: (item.candidate_id, item.reviewed_at, item.event_id))
    latest_by_candidate: dict[str, AuthorityReviewEventV2] = {}
    for event in public_events:
        latest_by_candidate[event.candidate_id] = event
    candidate_states: list[AuthorityCandidateState] = []
    for entry in packet.entries:
        latest = latest_by_candidate[entry.candidate.candidate_id]
        if entry.candidate.canonical_uuid is None:
            raise AuthorityContractError("T5-G2 candidate lost its applied catalog UUID")
        candidate_states.append(
            AuthorityCandidateState(
                ordinal=entry.ordinal,
                candidate_id=entry.candidate.candidate_id,
                canonical_uuid=entry.candidate.canonical_uuid,
                entry_sha256=entry.entry_sha256,
                catalog_record_sha256=entry.catalog_record_sha256,
                status=latest.to_status,
                latest_event_id=latest.event_id,
                latest_event_sha256=latest.event_sha256,
            )
        )
    terminal_counts = {
        "staged": 0,
        "reviewed": sum(item.status == ReviewStatus.reviewed for item in candidate_states),
        "approved_exact": sum(
            item.status == ReviewStatus.approved_exact for item in candidate_states
        ),
    }
    candidate_body = {
        "schema_version": "pvr-canonical-authority-candidate-state-v1",
        "state_version": DECISION_VERSION,
        "packet_sha256": packet_sha,
        "catalog_version": packet.catalog_version,
        "catalog_sha256": packet.catalog_sha256,
        "candidates": [item.model_dump(mode="json") for item in candidate_states],
        "status_counts": terminal_counts,
        "resolver_output_consulted": False,
        "network_requests": 0,
        "rhb_t5_authorized": False,
    }
    candidate_file = AuthorityCandidateStateFile.model_validate(
        _with_hash(candidate_body, "state_sha256")
    )

    all_authorization_hashes = {event.batch_authorization_sha256 for event in public_events}
    event_body = {
        "schema_version": "pvr-canonical-authority-review-event-ledger-v1",
        "ledger_version": DECISION_VERSION,
        "packet_sha256": packet_sha,
        "catalog_version": packet.catalog_version,
        "catalog_sha256": packet.catalog_sha256,
        "events": [event.model_dump(mode="json") for event in public_events],
        "batch_authorization_count": len(all_authorization_hashes),
        "owner_attestation_count": len(g1_attestations.attestations) + len(exact_attestations),
        "review_event_count": len(public_events),
        "status_counts": {
            "reviewed": terminal_counts["reviewed"],
            "approved_exact": terminal_counts["approved_exact"],
        },
        "cumulative_event_sha256": content_sha256([event.event_sha256 for event in public_events]),
        "resolver_output_consulted": False,
        "network_requests": 0,
        "rhb_t5_authorized": False,
    }
    event_file = AuthorityReviewEventFile.model_validate(_with_hash(event_body, "ledger_sha256"))

    outputs = {
        EXACT_AUTHORIZATION_LEDGER_REFERENCE: stable_json_bytes(
            authorization_ledger.model_dump(mode="json")
        ),
        EXACT_ATTESTATION_LEDGER_REFERENCE: stable_json_bytes(
            exact_attestation_ledger.model_dump(mode="json")
        ),
        AUTHORITY_CANDIDATES_REFERENCE: stable_json_bytes(candidate_file.model_dump(mode="json")),
        REVIEW_EVENTS_REFERENCE: stable_json_bytes(event_file.model_dump(mode="json")),
    }
    combined_public = outputs[AUTHORITY_CANDIDATES_REFERENCE] + outputs[REVIEW_EVENTS_REFERENCE]
    private_responses = [
        item.owner_response_verbatim for item in g1_authorizations.authorizations
    ] + [item.owner_response_verbatim for item in existing_authorizations]
    if any(response.encode("utf-8") in combined_public for response in private_responses):
        raise AuthorityContractError("public exact decision artifact contains owner verbatim")
    if b"@example.com" in combined_public:
        raise AuthorityContractError("public exact decision artifact contains PII")
    return outputs


def _target_states(root: Path) -> dict[Path, bool]:
    return {
        reference: _safe_path(root, reference, allow_missing_leaf=True).exists()
        for reference in (
            EXACT_AUTHORIZATION_LEDGER_REFERENCE,
            EXACT_ATTESTATION_LEDGER_REFERENCE,
        )
    }


def record_t5_g2_batch_exact(
    root: Path,
    *,
    owner_response_verbatim: str,
    authorized_exact_owner_response: str,
    batch_ordinal: int = DEFAULT_BATCH_ORDINAL,
    expected_outcome: str = "approved_exact",
    reviewed_at: datetime | None = None,
    check: bool = False,
) -> Literal["created", "unchanged"]:
    root = root.absolute()
    _require_ignore_rule(root)
    for forbidden in (FORBIDDEN_AUTHORITY_REFERENCE, FORBIDDEN_AUTHORITY_MANIFEST_REFERENCE):
        path = _safe_path(root, forbidden, allow_missing_leaf=True)
        if path.exists() or path.is_symlink():
            raise AuthorityContractError("T5-G2 cannot coexist with a frozen authority bundle")

    for reference in (
        G1_AUTHORIZATION_LEDGER_REFERENCE,
        G1_ATTESTATION_LEDGER_REFERENCE,
        AUTHORITY_CANDIDATES_REFERENCE,
        REVIEW_EVENTS_REFERENCE,
    ):
        target = _safe_path(root, reference, allow_missing_leaf=False)
        if target.is_symlink() or not target.is_file():
            raise AuthorityContractError("T5-G2 requires complete regular T5-G1 artifacts")
        expected_mode = 0o600 if reference.parent == PRIVATE_DIRECTORY else 0o644
        if stat.S_IMODE(target.stat().st_mode) != expected_mode:
            raise AuthorityContractError("T5-G2 input artifact permissions are unsafe")
    if stat.S_IMODE((root / PRIVATE_DIRECTORY).stat().st_mode) != 0o700:
        raise AuthorityContractError("T5-G2 private workspace permissions are unsafe")

    states = _target_states(root)
    if any(states.values()) and not all(states.values()):
        raise AuthorityContractError("partial T5-G2 private decision state")
    materialized = all(states.values())
    if check and not materialized:
        raise AuthorityContractError("requested T5-G2 exact decision is not materialized")
    exact_state = _load_exact_state(root) if materialized else None

    timestamp = reviewed_at
    if exact_state is not None and timestamp is None:
        existing = next(
            (item for item in exact_state[0].authorizations if item.batch_ordinal == batch_ordinal),
            None,
        )
        if existing is not None:
            timestamp = existing.authorized_at
    timestamp = timestamp or datetime.now(UTC).replace(microsecond=0)
    outputs = _build_outputs(
        root,
        owner_response_verbatim=owner_response_verbatim,
        authorized_exact_owner_response=authorized_exact_owner_response,
        reviewed_at=timestamp,
        batch_ordinal=batch_ordinal,
        expected_outcome=expected_outcome,
        exact_state=exact_state,
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
            f"T5-G2 Batch {batch_ordinal} artifacts differ from the expected state"
        )

    original_bytes = {
        reference: target.read_bytes() for reference, target in targets.items() if target.exists()
    }
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
            mode = 0o600 if reference.parent == PRIVATE_DIRECTORY else 0o644
            os.chmod(target, mode)
            _fsync_directory(target.parent)
    except BaseException:
        for temp in temps:
            if temp.exists() and not temp.is_symlink():
                temp.unlink()
        for target in reversed(installed):
            reference = next(item for item, path in targets.items() if path == target)
            if reference in original_bytes:
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
    "EXACT_ATTESTATION_LEDGER_REFERENCE",
    "EXACT_AUTHORIZATION_LEDGER_REFERENCE",
    "ExactBatchAuthorizationLedger",
    "ExactOwnerAttestationLedger",
    "record_t5_g2_batch_exact",
]
