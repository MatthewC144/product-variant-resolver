"""Fail-closed CAR-T5F readiness and authority-bundle freezing.

The module validates the complete two-Gate CAR-T5 event chain before it can
materialize a tracked authority bundle.  A generic continuation instruction is
not authorization: freezing requires a fresh, explicitly scoped CAR-T5F owner
response, which is retained only in the Git-ignored private workspace.
"""

from __future__ import annotations

import hashlib
import os
import stat
from collections import Counter, defaultdict
from dataclasses import dataclass
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
    AuthorityCandidateStateFile,
    AuthorityReviewEventFile,
    BatchAuthorizationLedger,
    OwnerAttestationLedger,
)
from product_variant_resolver.canonical_authority_decisions import (
    AUTHORIZATION_LEDGER_REFERENCE as G1_AUTHORIZATION_LEDGER_REFERENCE,
)
from product_variant_resolver.canonical_authority_exact_decisions import (
    EXACT_ATTESTATION_LEDGER_REFERENCE,
    EXACT_AUTHORIZATION_LEDGER_REFERENCE,
    ExactBatchAuthorizationLedger,
    ExactOwnerAttestationLedger,
    _load_exact_state,
    _load_required_state,
    _validate_g1_and_public_state,
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
    ArtifactDigest,
    AuthorityBundle,
    AuthorityBundleManifest,
    AuthorityBundleRecord,
    AuthorityContractError,
    AuthorityShortfalls,
    FamilyComposition,
    ReviewStatus,
    content_sha256,
    stable_json_bytes,
    validate_authority_source_decisions,
)

FREEZE_AUTHORIZATION_REFERENCE = PRIVATE_DIRECTORY / "car-t5f-owner-authorization.json"
AUTHORITY_BUNDLE_REFERENCE = FORBIDDEN_AUTHORITY_REFERENCE
AUTHORITY_MANIFEST_REFERENCE = FORBIDDEN_AUTHORITY_MANIFEST_REFERENCE
CATALOG_REFERENCE = Path("data/catalog.json")
PREPARATION_MANIFEST_REFERENCE = Path(
    "data/authority-review/canonical-authority-review-v1/authority-review-packet-manifest.json"
)
SOURCE_DECISIONS_REFERENCE = Path(
    "data/authority-review/canonical-authority-review-v1/source-decisions.json"
)

BUNDLE_VERSION: Literal["canonical-authority-review-car-t5f-v1"] = (
    "canonical-authority-review-car-t5f-v1"
)
FREEZE_DECLARATION: Literal[
    "owner_explicitly_authorized_car_t5f_bundle_freeze_or_exact_shortfall_publication"
] = "owner_explicitly_authorized_car_t5f_bundle_freeze_or_exact_shortfall_publication"

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class FreezeContract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class CarT5FFreezeAuthorization(FreezeContract):
    schema_version: Literal["pvr-canonical-authority-car-t5f-authorization-v1"]
    gate: Literal["CAR-T5F"]
    authorization_scope: Literal[
        "freeze_validated_event_chain_and_authority_bundle_or_publish_exact_shortfalls"
    ]
    authorization_declaration: Literal[
        "owner_explicitly_authorized_car_t5f_bundle_freeze_or_exact_shortfall_publication"
    ]
    owner_response_verbatim: str = Field(min_length=1)
    authorized_car_t5f_owner_response: str = Field(min_length=1)
    response_verbatim_sha256: Sha256
    packet_sha256: Sha256
    candidate_state_sha256: Sha256
    review_event_ledger_sha256: Sha256
    exact_authorization_ledger_sha256: Sha256
    exact_attestation_ledger_sha256: Sha256
    approved_exact_count: Literal[20]
    qualifying_family_count: int = Field(ge=4)
    confirmation_method: Literal["owner_attestation"]
    reviewed_by_role: Literal["project_owner"]
    authorized_at: datetime
    resolver_output_consulted: Literal[False]
    network_requests: Literal[0]
    car_t6_authorized: Literal[False]
    rhb_t5_authorized: Literal[False]
    authorization_sha256: Sha256

    @model_validator(mode="after")
    def authorization_is_exact_and_hash_bound(self) -> CarT5FFreezeAuthorization:
        if self.authorized_at.tzinfo is None or self.authorized_at.utcoffset() is None:
            raise ValueError("CAR-T5F authorization timestamp must be timezone-aware")
        if self.owner_response_verbatim != self.authorized_car_t5f_owner_response:
            raise ValueError("CAR-T5F authorization must preserve the exact owner response")
        expected_response = hashlib.sha256(self.owner_response_verbatim.encode()).hexdigest()
        if self.response_verbatim_sha256 != expected_response:
            raise ValueError("CAR-T5F owner-response checksum is stale")
        expected = content_sha256(self.model_dump(mode="json", exclude={"authorization_sha256"}))
        if self.authorization_sha256 != expected:
            raise ValueError("CAR-T5F authorization checksum is stale")
        return self


class CarT5FReadiness(FreezeContract):
    schema_version: Literal["pvr-canonical-authority-car-t5f-readiness-v1"]
    gate: Literal["CAR-T5F"]
    status: Literal["ready_for_separate_owner_authorization"]
    packet_sha256: Sha256
    candidate_state_sha256: Sha256
    review_event_ledger_sha256: Sha256
    exact_authorization_ledger_sha256: Sha256
    exact_attestation_ledger_sha256: Sha256
    approved_exact_count: Literal[20]
    reviewed_count: Literal[0]
    staged_count: Literal[0]
    family_count: int = Field(ge=4)
    qualifying_family_count: int = Field(ge=4)
    family_composition: list[FamilyComposition]
    proposed_gate_status: Literal["eligible_for_rhb_t4_reaudit"]
    exact_variant_shortfall: Literal[0]
    qualifying_family_shortfall: Literal[0]
    authority_bundle_present: bool
    authority_manifest_present: bool
    freeze_authorization_present: bool
    resolver_output_consulted: Literal[False]
    network_requests: Literal[0]
    car_t6_authorized: Literal[False]
    rhb_t5_authorized: Literal[False]
    readiness_sha256: Sha256

    @model_validator(mode="after")
    def readiness_is_hash_bound(self) -> CarT5FReadiness:
        expected = content_sha256(self.model_dump(mode="json", exclude={"readiness_sha256"}))
        if self.readiness_sha256 != expected:
            raise ValueError("CAR-T5F readiness checksum is stale")
        present = {
            self.authority_bundle_present,
            self.authority_manifest_present,
            self.freeze_authorization_present,
        }
        if len(present) != 1:
            raise ValueError("CAR-T5F output state is partial")
        return self


@dataclass(frozen=True)
class FreezeContext:
    packet: AuthorityReviewPreparationPacket
    packet_sha256: str
    candidates: AuthorityCandidateStateFile
    events: AuthorityReviewEventFile
    g1_authorizations: BatchAuthorizationLedger
    g1_attestations: OwnerAttestationLedger
    exact_authorizations: ExactBatchAuthorizationLedger
    exact_attestations: ExactOwnerAttestationLedger
    bundle: AuthorityBundle
    family_composition: list[FamilyComposition]


def _raw_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _with_hash(body: dict[str, Any], key: str) -> dict[str, Any]:
    return {**body, key: content_sha256(body)}


def _output_states(root: Path) -> dict[Path, bool]:
    return {
        reference: (_safe_path(root, reference, allow_missing_leaf=True).exists())
        for reference in (
            FREEZE_AUTHORIZATION_REFERENCE,
            AUTHORITY_BUNDLE_REFERENCE,
            AUTHORITY_MANIFEST_REFERENCE,
        )
    }


def _validate_permissions(root: Path) -> None:
    if stat.S_IMODE((root / PRIVATE_DIRECTORY).stat().st_mode) != 0o700:
        raise AuthorityContractError("CAR-T5F private workspace permissions are unsafe")
    private_inputs = (
        G1_AUTHORIZATION_LEDGER_REFERENCE,
        G1_ATTESTATION_LEDGER_REFERENCE,
        EXACT_AUTHORIZATION_LEDGER_REFERENCE,
        EXACT_ATTESTATION_LEDGER_REFERENCE,
        PRIVATE_DIRECTORY / "authority-review-packet.json",
    )
    public_inputs = (
        AUTHORITY_CANDIDATES_REFERENCE,
        REVIEW_EVENTS_REFERENCE,
        PREPARATION_MANIFEST_REFERENCE,
        CATALOG_REFERENCE,
        SOURCE_DECISIONS_REFERENCE,
    )
    for reference in private_inputs + public_inputs:
        path = _safe_path(root, reference, allow_missing_leaf=False)
        if path.is_symlink() or not path.is_file():
            raise AuthorityContractError("CAR-T5F requires complete regular input artifacts")
        mode = stat.S_IMODE(path.stat().st_mode)
        allowed_modes = {0o600} if reference in private_inputs else {0o600, 0o644}
        if mode not in allowed_modes:
            raise AuthorityContractError("CAR-T5F input artifact permissions are unsafe")


def _family_composition(bundle: AuthorityBundle) -> list[FamilyComposition]:
    releases: defaultdict[str, set[str]] = defaultdict(set)
    for record in bundle.records:
        if record.status == ReviewStatus.approved_exact:
            releases[record.family_group_key].add(record.release_key)
    return [
        FamilyComposition(
            family_group_key=family,
            release_keys=sorted(keys),
            approved_variant_count=len(keys),
        )
        for family, keys in sorted(releases.items())
        if len(keys) >= 2
    ]


def _build_bundle(
    packet: AuthorityReviewPreparationPacket,
    candidates: AuthorityCandidateStateFile,
    events: AuthorityReviewEventFile,
) -> AuthorityBundle:
    entries = {entry.candidate.candidate_id: entry for entry in packet.entries}
    states = {item.candidate_id: item for item in candidates.candidates}
    latest: dict[str, Any] = {}
    for event in events.events:
        latest[event.candidate_id] = event
    if set(entries) != set(states) or set(entries) != set(latest):
        raise AuthorityContractError("CAR-T5F candidate, packet and event coverage differ")

    records: list[AuthorityBundleRecord] = []
    for candidate_id in sorted(entries):
        entry = entries[candidate_id]
        state = states[candidate_id]
        event = latest[candidate_id]
        if (
            state.status != ReviewStatus.approved_exact
            or event.to_status != ReviewStatus.approved_exact
            or state.latest_event_id != event.event_id
            or state.latest_event_sha256 != event.event_sha256
            or state.canonical_uuid != event.canonical_uuid
            or state.canonical_uuid != entry.candidate.canonical_uuid
            or state.catalog_record_sha256 != event.catalog_record_sha256
            or state.catalog_record_sha256 != entry.catalog_record_sha256
            or event.packet_sha256 != candidates.packet_sha256
            or event.catalog_sha256 != candidates.catalog_sha256
            or event.variant_field_evidence != entry.field_evidence
        ):
            raise AuthorityContractError("CAR-T5F latest exact event differs from frozen inputs")
        evidence_hashes = sorted(
            content_sha256(item.model_dump(mode="json")) for item in event.variant_field_evidence
        )
        if len(evidence_hashes) != 6 or len(set(evidence_hashes)) != 6:
            raise AuthorityContractError("CAR-T5F exact event requires six distinct evidence rows")
        records.append(
            AuthorityBundleRecord(
                candidate_id=candidate_id,
                canonical_uuid=state.canonical_uuid,
                family_group_key=entry.candidate.family_group_key,
                release_key=entry.candidate.proposed_release_key,
                status=state.status,
                synthetic=False,
                latest_event_id=event.event_id,
                catalog_version=candidates.catalog_version,
                catalog_record_sha256=state.catalog_record_sha256,
                source_decision_ids=event.source_decision_ids,
                evidence_sha256s=evidence_hashes,
            )
        )
    return AuthorityBundle(
        schema_version="pvr-canonical-authority-bundle-v1",
        bundle_version=BUNDLE_VERSION,
        records=records,
        resolver_output_consulted=False,
        network_requests=0,
        rhb_t5_authorized=False,
    )


def _load_context(root: Path) -> FreezeContext:
    root = root.absolute()
    _require_ignore_rule(root)
    _validate_permissions(root)
    if prepare_authority_review(root, check=True) != "unchanged":
        raise AuthorityContractError("CAR-T5F preparation packet is not frozen")
    packet, _owner_markdown, preparation_manifest = build_authority_review_preparation(root)
    packet_sha = content_sha256(packet.model_dump(mode="json"))
    if packet_sha != preparation_manifest.private_packet_sha256:
        raise AuthorityContractError("CAR-T5F preparation packet checksum is stale")

    g1_authorizations, g1_attestations, candidates, events = _load_required_state(root)
    exact_authorizations, exact_attestations = _load_exact_state(root)
    _validate_g1_and_public_state(
        packet,
        packet_sha,
        g1_authorizations,
        g1_attestations,
        candidates,
        events,
        (exact_authorizations, exact_attestations),
        7,
    )
    if [item.batch_ordinal for item in exact_authorizations.authorizations] != list(range(1, 8)):
        raise AuthorityContractError("CAR-T5F requires all seven T5-G2 authorizations")
    if len(exact_attestations.attestations) != 20:
        raise AuthorityContractError("CAR-T5F requires all 20 T5-G2 attestations")
    if candidates.status_counts != {"staged": 0, "reviewed": 0, "approved_exact": 20}:
        raise AuthorityContractError("CAR-T5F requires exactly 20 approved exact candidates")
    if events.status_counts != {"reviewed": 0, "approved_exact": 20}:
        raise AuthorityContractError("CAR-T5F event terminal counts are stale")
    if len(events.events) != 40 or events.batch_authorization_count != 14:
        raise AuthorityContractError("CAR-T5F requires the complete two-Gate event chain")

    bundle = _build_bundle(packet, candidates, events)
    composition = _family_composition(bundle)
    if len(bundle.records) != 20 or len(composition) < 4:
        raise AuthorityContractError("CAR-T5F current state does not satisfy 20/4 composition")
    return FreezeContext(
        packet=packet,
        packet_sha256=packet_sha,
        candidates=candidates,
        events=events,
        g1_authorizations=g1_authorizations,
        g1_attestations=g1_attestations,
        exact_authorizations=exact_authorizations,
        exact_attestations=exact_attestations,
        bundle=bundle,
        family_composition=composition,
    )


def build_car_t5f_readiness(root: Path) -> CarT5FReadiness:
    """Validate all CAR-T5F inputs without creating an authorization or bundle."""

    root = root.absolute()
    context = _load_context(root)
    states = _output_states(root)
    if any(states.values()) and not all(states.values()):
        raise AuthorityContractError("partial CAR-T5F output state")
    if all(states.values()):
        raise AuthorityContractError("CAR-T5F is already materialized; use freeze check mode")
    body: dict[str, Any] = {
        "schema_version": "pvr-canonical-authority-car-t5f-readiness-v1",
        "gate": "CAR-T5F",
        "status": "ready_for_separate_owner_authorization",
        "packet_sha256": context.packet_sha256,
        "candidate_state_sha256": context.candidates.state_sha256,
        "review_event_ledger_sha256": context.events.ledger_sha256,
        "exact_authorization_ledger_sha256": context.exact_authorizations.ledger_sha256,
        "exact_attestation_ledger_sha256": context.exact_attestations.ledger_sha256,
        "approved_exact_count": 20,
        "reviewed_count": 0,
        "staged_count": 0,
        "family_count": len(context.packet.family_batches),
        "qualifying_family_count": len(context.family_composition),
        "family_composition": [item.model_dump(mode="json") for item in context.family_composition],
        "proposed_gate_status": "eligible_for_rhb_t4_reaudit",
        "exact_variant_shortfall": 0,
        "qualifying_family_shortfall": 0,
        "authority_bundle_present": states[AUTHORITY_BUNDLE_REFERENCE],
        "authority_manifest_present": states[AUTHORITY_MANIFEST_REFERENCE],
        "freeze_authorization_present": states[FREEZE_AUTHORIZATION_REFERENCE],
        "resolver_output_consulted": False,
        "network_requests": 0,
        "car_t6_authorized": False,
        "rhb_t5_authorized": False,
    }
    return CarT5FReadiness.model_validate(_with_hash(body, "readiness_sha256"))


def _validate_freeze_response(response: str) -> None:
    compact = " ".join(response.split())
    required = ("CAR-T5F", "authority bundle", "CAR-T6", "RHB-T5")
    if any(token not in compact for token in required):
        raise AuthorityContractError(
            "CAR-T5F requires a fresh explicit authority-bundle authorization with later-Gate boundaries"
        )
    negative_car_t6 = "不授權 CAR-T6" in compact or "does not authorize CAR-T6" in compact
    negative_rhb_t5 = "不授權 RHB-T5" in compact or "does not authorize RHB-T5" in compact
    if not negative_car_t6 or not negative_rhb_t5:
        raise AuthorityContractError(
            "CAR-T5F authorization must keep CAR-T6 and RHB-T5 unauthorized"
        )


def _authorization(
    context: FreezeContext,
    *,
    owner_response_verbatim: str,
    authorized_car_t5f_owner_response: str,
    authorized_at: datetime,
) -> CarT5FFreezeAuthorization:
    if owner_response_verbatim != authorized_car_t5f_owner_response:
        raise AuthorityContractError("CAR-T5F owner response differs from the authorized response")
    _validate_freeze_response(authorized_car_t5f_owner_response)
    timestamp = authorized_at.astimezone(UTC).replace(microsecond=0)
    if timestamp != authorized_at:
        raise AuthorityContractError("CAR-T5F authorization timestamp must be whole-second UTC")
    response_sha = hashlib.sha256(owner_response_verbatim.encode()).hexdigest()
    earlier = {
        item.response_verbatim_sha256 for item in context.g1_authorizations.authorizations
    } | {item.response_verbatim_sha256 for item in context.exact_authorizations.authorizations}
    if response_sha in earlier:
        raise AuthorityContractError("CAR-T5F authorization cannot reuse a prior owner response")
    body: dict[str, Any] = {
        "schema_version": "pvr-canonical-authority-car-t5f-authorization-v1",
        "gate": "CAR-T5F",
        "authorization_scope": (
            "freeze_validated_event_chain_and_authority_bundle_or_publish_exact_shortfalls"
        ),
        "authorization_declaration": FREEZE_DECLARATION,
        "owner_response_verbatim": owner_response_verbatim,
        "authorized_car_t5f_owner_response": authorized_car_t5f_owner_response,
        "response_verbatim_sha256": response_sha,
        "packet_sha256": context.packet_sha256,
        "candidate_state_sha256": context.candidates.state_sha256,
        "review_event_ledger_sha256": context.events.ledger_sha256,
        "exact_authorization_ledger_sha256": context.exact_authorizations.ledger_sha256,
        "exact_attestation_ledger_sha256": context.exact_attestations.ledger_sha256,
        "approved_exact_count": 20,
        "qualifying_family_count": len(context.family_composition),
        "confirmation_method": "owner_attestation",
        "reviewed_by_role": "project_owner",
        "authorized_at": timestamp.isoformat().replace("+00:00", "Z"),
        "resolver_output_consulted": False,
        "network_requests": 0,
        "car_t6_authorized": False,
        "rhb_t5_authorized": False,
    }
    return CarT5FFreezeAuthorization.model_validate(_with_hash(body, "authorization_sha256"))


def _parent_artifacts(root: Path, authorization: CarT5FFreezeAuthorization) -> list[ArtifactDigest]:
    references: dict[str, Path] = {
        "authority-candidates.json": AUTHORITY_CANDIDATES_REFERENCE,
        "authority-review-packet-manifest.json": PREPARATION_MANIFEST_REFERENCE,
        "catalog.json": CATALOG_REFERENCE,
        "private-authority-review-packet.json": PRIVATE_DIRECTORY / "authority-review-packet.json",
        "private-t5-g1-authorizations.json": G1_AUTHORIZATION_LEDGER_REFERENCE,
        "private-t5-g1-attestations.json": G1_ATTESTATION_LEDGER_REFERENCE,
        "private-t5-g2-authorizations.json": EXACT_AUTHORIZATION_LEDGER_REFERENCE,
        "private-t5-g2-attestations.json": EXACT_ATTESTATION_LEDGER_REFERENCE,
        "review-events.json": REVIEW_EVENTS_REFERENCE,
        "source-decisions.json": SOURCE_DECISIONS_REFERENCE,
    }
    parents = [
        ArtifactDigest(reference=reference, sha256=_raw_sha(root / path))
        for reference, path in sorted(references.items())
    ]
    parents.append(
        ArtifactDigest(
            reference="private-car-t5f-owner-authorization.json",
            sha256=authorization.authorization_sha256,
        )
    )
    return sorted(parents, key=lambda item: item.reference)


def _manifest(
    root: Path,
    context: FreezeContext,
    authorization: CarT5FFreezeAuthorization,
) -> AuthorityBundleManifest:
    counts = Counter(record.status for record in context.bundle.records)
    count_payload = {status: counts[status] for status in ReviewStatus}
    source_sha = validate_authority_source_decisions(root).source_decisions_sha256
    return AuthorityBundleManifest(
        schema_version="pvr-canonical-authority-bundle-manifest-v1",
        bundle_version=BUNDLE_VERSION,
        authority_bundle_sha256=content_sha256(context.bundle.model_dump(mode="json")),
        ordered_parent_artifacts=_parent_artifacts(root, authorization),
        catalog_version=context.packet.catalog_version,
        catalog_sha256=context.packet.catalog_sha256,
        source_decision_sha256s=[source_sha],
        counts_by_status=count_payload,
        approved_distinct_variant_count=20,
        qualifying_family_count=len(context.family_composition),
        family_composition=context.family_composition,
        resolver_output_consulted=False,
        network_requests=0,
        publication_scope="safe_metadata_only",
        gate_status="eligible_for_rhb_t4_reaudit",
        shortfalls=AuthorityShortfalls(
            exact_variant_shortfall=0,
            qualifying_family_shortfall=0,
        ),
        created_at=authorization.authorized_at,
        status="complete",
        rhb_t5_authorized=False,
    )


def _public_outputs_are_private_text_free(
    authorization: CarT5FFreezeAuthorization, bundle: bytes, manifest: bytes
) -> None:
    public = bundle + manifest
    for response in (
        authorization.owner_response_verbatim,
        authorization.authorized_car_t5f_owner_response,
    ):
        if response.encode() in public:
            raise AuthorityContractError("CAR-T5F public output contains private owner text")


def freeze_authority_bundle(
    root: Path,
    *,
    owner_response_verbatim: str,
    authorized_car_t5f_owner_response: str,
    authorized_at: datetime | None = None,
    check: bool = False,
) -> Literal["created", "unchanged"]:
    """Freeze the CAR-T5F bundle only with a fresh, explicit owner authorization."""

    root = root.absolute()
    context = _load_context(root)
    states = _output_states(root)
    if any(states.values()) and not all(states.values()):
        raise AuthorityContractError("partial CAR-T5F output state")
    materialized = all(states.values())
    if check and not materialized:
        raise AuthorityContractError("CAR-T5F bundle is not materialized")
    if materialized:
        for reference in states:
            path = _safe_path(root, reference, allow_missing_leaf=False)
            expected_mode = 0o600 if reference == FREEZE_AUTHORIZATION_REFERENCE else 0o644
            if (
                path.is_symlink()
                or not path.is_file()
                or stat.S_IMODE(path.stat().st_mode) != expected_mode
            ):
                raise AuthorityContractError("CAR-T5F output artifact permissions are unsafe")

    timestamp = authorized_at
    if materialized and timestamp is None:
        payload, _raw = _strict_json(root / FREEZE_AUTHORIZATION_REFERENCE)
        timestamp = CarT5FFreezeAuthorization.model_validate(payload).authorized_at
    timestamp = timestamp or datetime.now(UTC).replace(microsecond=0)
    authorization = _authorization(
        context,
        owner_response_verbatim=owner_response_verbatim,
        authorized_car_t5f_owner_response=authorized_car_t5f_owner_response,
        authorized_at=timestamp,
    )
    manifest = _manifest(root, context, authorization)
    outputs = {
        FREEZE_AUTHORIZATION_REFERENCE: stable_json_bytes(authorization.model_dump(mode="json")),
        AUTHORITY_BUNDLE_REFERENCE: stable_json_bytes(context.bundle.model_dump(mode="json")),
        AUTHORITY_MANIFEST_REFERENCE: stable_json_bytes(manifest.model_dump(mode="json")),
    }
    _public_outputs_are_private_text_free(
        authorization,
        outputs[AUTHORITY_BUNDLE_REFERENCE],
        outputs[AUTHORITY_MANIFEST_REFERENCE],
    )
    targets = {
        reference: _safe_path(root, reference, allow_missing_leaf=True) for reference in outputs
    }
    if materialized and all(targets[ref].read_bytes() == raw for ref, raw in outputs.items()):
        return "unchanged"
    if check:
        raise AuthorityContractError("CAR-T5F outputs differ from the expected frozen state")

    original = {
        reference: path.read_bytes() for reference, path in targets.items() if path.exists()
    }
    temps: list[Path] = []
    installed: list[Path] = []
    try:
        for reference, raw in outputs.items():
            mode = 0o600 if reference == FREEZE_AUTHORIZATION_REFERENCE else 0o644
            temps.append(_write_temp(targets[reference], raw, mode))
        for (reference, target), temp in zip(targets.items(), temps, strict=True):
            os.replace(temp, target)
            installed.append(target)
            os.chmod(target, 0o600 if reference == FREEZE_AUTHORIZATION_REFERENCE else 0o644)
            _fsync_directory(target.parent)
    except BaseException:
        for temp in temps:
            if temp.exists() and not temp.is_symlink():
                temp.unlink()
        for target in reversed(installed):
            reference = next(ref for ref, path in targets.items() if path == target)
            if reference in original:
                mode = 0o600 if reference == FREEZE_AUTHORIZATION_REFERENCE else 0o644
                rollback = _write_temp(target, original[reference], mode)
                os.replace(rollback, target)
                os.chmod(target, mode)
                _fsync_directory(target.parent)
            elif target.exists() and not target.is_symlink():
                target.unlink()
                _fsync_directory(target.parent)
        raise
    return "created"


__all__ = [
    "AUTHORITY_BUNDLE_REFERENCE",
    "AUTHORITY_MANIFEST_REFERENCE",
    "FREEZE_AUTHORIZATION_REFERENCE",
    "CarT5FFreezeAuthorization",
    "CarT5FReadiness",
    "build_car_t5f_readiness",
    "freeze_authority_bundle",
]
