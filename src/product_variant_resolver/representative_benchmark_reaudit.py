"""CAR-T6 readiness and versioned RHB-T4 authority re-audit.

The historical blocked RHB-T4 checkpoint is immutable.  This module validates
the later CAR-T5F bundle and can publish a separate versioned re-audit only
after a fresh CAR-T6 owner authorization.  It never authorizes RHB-T5 or writes
query/label artifacts.
"""

from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.canonical_authority_decisions import (
    REVIEW_EVENTS_REFERENCE,
    AuthorityReviewEventFile,
)
from product_variant_resolver.canonical_authority_freeze import (
    AUTHORITY_BUNDLE_REFERENCE,
    AUTHORITY_MANIFEST_REFERENCE,
    FREEZE_AUTHORIZATION_REFERENCE,
    CarT5FFreezeAuthorization,
    freeze_authority_bundle,
)
from product_variant_resolver.canonical_authority_preparation import (
    PRIVATE_DIRECTORY,
    _fsync_directory,
    _require_ignore_rule,
    _safe_path,
    _strict_json,
    _write_temp,
)
from product_variant_resolver.canonical_authority_review import (
    ArtifactDigest,
    AuthorityBundle,
    AuthorityBundleManifest,
    AuthorityContractError,
    FamilyComposition,
    ReviewStatus,
    content_sha256,
    stable_json_bytes,
)
from product_variant_resolver.representative_benchmark import (
    AuthorityStatus,
    CanonicalAuthorityArtifact,
    CanonicalAuthorityManifest,
    CanonicalAuthorityRecord,
    RowPublicationScope,
    VariantField,
)

RHB_DIRECTORY = Path("data/evaluation/representative-hard-benchmark-v1")
HISTORICAL_AUTHORITY_REFERENCE = RHB_DIRECTORY / "canonical-authority.json"
HISTORICAL_MANIFEST_REFERENCE = RHB_DIRECTORY / "canonical-authority-manifest.json"
REAUDIT_AUTHORITY_REFERENCE = RHB_DIRECTORY / "canonical-authority-reaudit-v1.json"
REAUDIT_MANIFEST_REFERENCE = RHB_DIRECTORY / "canonical-authority-reaudit-manifest-v1.json"
CAR_T6_AUTHORIZATION_REFERENCE = PRIVATE_DIRECTORY / "car-t6-owner-authorization.json"
CATALOG_REFERENCE = Path("data/catalog.json")

AUDIT_VERSION: Literal["representative-hard-benchmark-car-t6-reaudit-v1"] = (
    "representative-hard-benchmark-car-t6-reaudit-v1"
)
AUTHORITY_VERSION: Literal["representative-hard-benchmark-canonical-authority-car-t6-v1"] = (
    "representative-hard-benchmark-canonical-authority-car-t6-v1"
)
CAR_T6_DECLARATION: Literal["owner_explicitly_authorized_car_t6_versioned_rhb_t4_reaudit_only"] = (
    "owner_explicitly_authorized_car_t6_versioned_rhb_t4_reaudit_only"
)

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class ReauditContract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class CarT6Authorization(ReauditContract):
    schema_version: Literal["pvr-car-t6-rhb-t4-reaudit-authorization-v1"]
    gate: Literal["CAR-T6"]
    authorization_scope: Literal["versioned_rhb_t4_authority_reaudit_only"]
    authorization_declaration: Literal[
        "owner_explicitly_authorized_car_t6_versioned_rhb_t4_reaudit_only"
    ]
    owner_response_verbatim: str = Field(min_length=1)
    authorized_car_t6_owner_response: str = Field(min_length=1)
    response_verbatim_sha256: Sha256
    car_t5f_authorization_sha256: Sha256
    car_authority_bundle_sha256: Sha256
    car_authority_manifest_sha256: Sha256
    historical_rhb_t4_authority_sha256: Sha256
    historical_rhb_t4_manifest_sha256: Sha256
    approved_exact_count: Literal[20]
    qualifying_family_count: int = Field(ge=4)
    confirmation_method: Literal["owner_attestation"]
    reviewed_by_role: Literal["project_owner"]
    authorized_at: datetime
    resolver_output_consulted: Literal[False]
    benchmark_labels_consulted: Literal[False]
    network_requests: Literal[0]
    rhb_t5_authorized: Literal[False]
    authorization_sha256: Sha256

    @model_validator(mode="after")
    def authorization_is_fresh_and_hash_bound(self) -> CarT6Authorization:
        if self.authorized_at.tzinfo is None or self.authorized_at.utcoffset() is None:
            raise ValueError("CAR-T6 authorization timestamp must be timezone-aware")
        if self.owner_response_verbatim != self.authorized_car_t6_owner_response:
            raise ValueError("CAR-T6 authorization must preserve the exact owner response")
        expected_response = hashlib.sha256(self.owner_response_verbatim.encode()).hexdigest()
        if self.response_verbatim_sha256 != expected_response:
            raise ValueError("CAR-T6 owner-response checksum is stale")
        expected = content_sha256(self.model_dump(mode="json", exclude={"authorization_sha256"}))
        if self.authorization_sha256 != expected:
            raise ValueError("CAR-T6 authorization checksum is stale")
        return self


class HistoricalAuditBinding(ReauditContract):
    authority_sha256: Sha256
    manifest_sha256: Sha256
    authority_record_count: Literal[0]
    gate_result: Literal["blocked_insufficient_exact_authority"]
    preserved_without_overwrite: Literal[True]


class ReauditThresholds(ReauditContract):
    minimum_exact_variants: Literal[20]
    observed_exact_variants: Literal[20]
    exact_variant_shortfall: Literal[0]
    minimum_qualifying_families: Literal[4]
    observed_qualifying_families: int = Field(ge=4)
    qualifying_family_shortfall: Literal[0]


class CarT6ReauditManifest(ReauditContract):
    schema_version: Literal["pvr-representative-hard-benchmark-car-t6-reaudit-manifest-v1"]
    audit_version: Literal["representative-hard-benchmark-car-t6-reaudit-v1"]
    status: Literal["complete"]
    generated_by: Literal["scripts/build_representative_hard_benchmark_authority_reaudit.py"]
    generated_at: datetime
    authority_file: Literal["canonical-authority-reaudit-v1.json"]
    authority_sha256: Sha256
    authority_version: Literal["representative-hard-benchmark-canonical-authority-car-t6-v1"]
    authority_record_order: list[str] = Field(min_length=20, max_length=20)
    ordered_input_artifacts: list[ArtifactDigest] = Field(min_length=1)
    historical_rhb_t4: HistoricalAuditBinding
    catalog_version: Literal["catalog-v2"]
    catalog_sha256: Sha256
    approved_exact_variant_count: Literal[20]
    qualifying_family_count: int = Field(ge=4)
    family_composition: list[FamilyComposition] = Field(min_length=4)
    thresholds: ReauditThresholds
    gate_result: Literal["passed_exact_authority_gate"]
    next_allowed_step: Literal["owner_gate_rhb_t5_separate_authorization_required"]
    prohibited_next_steps: list[Literal["RHB_T5", "query_pack_authoring", "label_authoring"]]
    publication_scope: Literal["safe_metadata_and_authority_records"]
    network_requests: Literal[0]
    resolver_output_consulted: Literal[False]
    benchmark_labels_consulted: Literal[False]
    rhb_t5_authorized: Literal[False]
    car_t6_authorization_sha256: Sha256
    manifest_sha256: Sha256

    @model_validator(mode="after")
    def manifest_is_ordered_and_hash_bound(self) -> CarT6ReauditManifest:
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("CAR-T6 audit timestamp must be timezone-aware")
        if self.authority_record_order != sorted(set(self.authority_record_order)):
            raise ValueError("CAR-T6 authority record order must be unique and sorted")
        refs = [item.reference for item in self.ordered_input_artifacts]
        if refs != sorted(set(refs)):
            raise ValueError("CAR-T6 input artifacts must be unique and sorted")
        families = [item.family_group_key for item in self.family_composition]
        if families != sorted(set(families)):
            raise ValueError("CAR-T6 family composition must be unique and sorted")
        expected = content_sha256(self.model_dump(mode="json", exclude={"manifest_sha256"}))
        if self.manifest_sha256 != expected:
            raise ValueError("CAR-T6 re-audit manifest checksum is stale")
        return self


class CarT6Readiness(ReauditContract):
    schema_version: Literal["pvr-car-t6-rhb-t4-reaudit-readiness-v1"]
    gate: Literal["CAR-T6"]
    status: Literal["ready_for_separate_owner_authorization"]
    historical_gate_result: Literal["blocked_insufficient_exact_authority"]
    historical_checkpoint_preserved: Literal[True]
    car_t5f_gate_result: Literal["eligible_for_rhb_t4_reaudit"]
    proposed_reaudit_gate_result: Literal["passed_exact_authority_gate"]
    approved_exact_variant_count: Literal[20]
    qualifying_family_count: int = Field(ge=4)
    exact_variant_shortfall: Literal[0]
    qualifying_family_shortfall: Literal[0]
    reaudited_authority_present: bool
    reaudited_manifest_present: bool
    car_t6_authorization_present: bool
    resolver_output_consulted: Literal[False]
    benchmark_labels_consulted: Literal[False]
    network_requests: Literal[0]
    rhb_t5_authorized: Literal[False]
    readiness_sha256: Sha256

    @model_validator(mode="after")
    def readiness_is_hash_bound(self) -> CarT6Readiness:
        states = {
            self.reaudited_authority_present,
            self.reaudited_manifest_present,
            self.car_t6_authorization_present,
        }
        if len(states) != 1:
            raise ValueError("CAR-T6 output state is partial")
        expected = content_sha256(self.model_dump(mode="json", exclude={"readiness_sha256"}))
        if self.readiness_sha256 != expected:
            raise ValueError("CAR-T6 readiness checksum is stale")
        return self


@dataclass(frozen=True)
class ReauditContext:
    car_authorization: CarT5FFreezeAuthorization
    car_bundle: AuthorityBundle
    car_manifest: AuthorityBundleManifest
    review_events: AuthorityReviewEventFile
    historical_authority: CanonicalAuthorityArtifact
    historical_manifest: CanonicalAuthorityManifest
    authority: CanonicalAuthorityArtifact


def _raw_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _with_hash(body: dict[str, Any], key: str) -> dict[str, Any]:
    return {**body, key: content_sha256(body)}


def _load_model(root: Path, reference: Path, model: type[BaseModel]) -> BaseModel:
    payload, _raw = _strict_json(_safe_path(root, reference, allow_missing_leaf=False))
    return model.model_validate(payload)


def _output_states(root: Path) -> dict[Path, bool]:
    return {
        reference: _safe_path(root, reference, allow_missing_leaf=True).exists()
        for reference in (
            CAR_T6_AUTHORIZATION_REFERENCE,
            REAUDIT_AUTHORITY_REFERENCE,
            REAUDIT_MANIFEST_REFERENCE,
        )
    }


def _validate_historical_checkpoint(
    historical_authority: CanonicalAuthorityArtifact,
    historical_manifest: CanonicalAuthorityManifest,
) -> None:
    if historical_authority.records:
        raise AuthorityContractError("historical RHB-T4 authority must remain empty")
    if (
        historical_manifest.gate_result != "blocked_insufficient_exact_authority"
        or historical_manifest.eligible_exact_variant_count != 0
        or historical_manifest.pilot_usable_exact_variant_count != 0
        or historical_manifest.same_casting_multi_release_family_count != 0
    ):
        raise AuthorityContractError("historical RHB-T4 blocked checkpoint changed")


def _build_reaudited_authority(
    root: Path,
    bundle: AuthorityBundle,
    car_manifest: AuthorityBundleManifest,
    events: AuthorityReviewEventFile,
) -> CanonicalAuthorityArtifact:
    catalog_payload, _raw = _strict_json(root / CATALOG_REFERENCE)
    if catalog_payload.get("catalog_version") != "catalog-v2":
        raise AuthorityContractError("CAR-T6 requires catalog-v2")
    products = catalog_payload.get("products")
    if not isinstance(products, list) or len(products) != 140:
        raise AuthorityContractError("CAR-T6 requires the complete 140-row catalog-v2")
    by_uuid = {
        str(item.get("canonical_uuid")): item
        for item in products
        if isinstance(item, dict) and item.get("canonical_uuid")
    }
    latest = {event.candidate_id: event for event in events.events}
    records: list[CanonicalAuthorityRecord] = []
    supported_fields = [
        VariantField.casting,
        VariantField.release_year,
        VariantField.series,
        VariantField.collector_number,
        VariantField.series_position,
        VariantField.identifiers,
    ]
    for bundle_record in bundle.records:
        product = by_uuid.get(str(bundle_record.canonical_uuid))
        event = latest.get(bundle_record.candidate_id)
        if product is None or event is None:
            raise AuthorityContractError("CAR-T6 bundle record lacks catalog or event input")
        event_fields = [item.field.value for item in event.variant_field_evidence]
        evidence_hashes = sorted(
            content_sha256(item.model_dump(mode="json")) for item in event.variant_field_evidence
        )
        if (
            content_sha256(product) != bundle_record.catalog_record_sha256
            or event.event_id != bundle_record.latest_event_id
            or event.to_status != ReviewStatus.approved_exact
            or event.catalog_record_sha256 != bundle_record.catalog_record_sha256
            or event_fields != [field.value for field in supported_fields]
            or evidence_hashes != bundle_record.evidence_sha256s
            or product.get("color") is not None
            or product.get("edition") is not None
        ):
            raise AuthorityContractError("CAR-T6 authority record differs from CAR-T5F evidence")
        records.append(
            CanonicalAuthorityRecord(
                authority_id=f"car-t6-{bundle_record.candidate_id}",
                canonical_uuid=bundle_record.canonical_uuid,
                canonical_catalog_version=bundle_record.catalog_version,
                catalog_record_sha256=bundle_record.catalog_record_sha256,
                variant_fields_verified=supported_fields,
                independent_evidence_refs=[f"sha256:{value}" for value in evidence_hashes],
                evidence_source_ids=list(bundle_record.source_decision_ids),
                resolver_output_consulted=False,
                reviewed_by=event.reviewed_by_role,
                reviewed_at=event.reviewed_at,
                review_reason=event.review_reason,
                status=AuthorityStatus.approved_exact,
            )
        )
    records.sort(key=lambda item: item.authority_id)
    authority = CanonicalAuthorityArtifact(
        schema_version="pvr-representative-hard-benchmark-canonical-authority-v1",
        authority_version=AUTHORITY_VERSION,
        publication_scope=RowPublicationScope.public,
        records=records,
    )
    if len(authority.records) != 20 or car_manifest.qualifying_family_count < 4:
        raise AuthorityContractError("CAR-T6 re-audit does not satisfy the 20/4 Gate")
    if len({record.canonical_uuid for record in authority.records}) != 20:
        raise AuthorityContractError("CAR-T6 re-audit contains duplicate canonical UUIDs")
    return authority


def _load_context(root: Path) -> ReauditContext:
    root = root.absolute()
    _require_ignore_rule(root)
    private_auth = CarT5FFreezeAuthorization.model_validate(
        _load_model(root, FREEZE_AUTHORIZATION_REFERENCE, CarT5FFreezeAuthorization)
    )
    freeze_authority_bundle(
        root,
        owner_response_verbatim=private_auth.owner_response_verbatim,
        authorized_car_t5f_owner_response=private_auth.authorized_car_t5f_owner_response,
        check=True,
    )
    car_bundle = AuthorityBundle.model_validate(
        _load_model(root, AUTHORITY_BUNDLE_REFERENCE, AuthorityBundle)
    )
    car_manifest = AuthorityBundleManifest.model_validate(
        _load_model(root, AUTHORITY_MANIFEST_REFERENCE, AuthorityBundleManifest)
    )
    events = AuthorityReviewEventFile.model_validate(
        _load_model(root, REVIEW_EVENTS_REFERENCE, AuthorityReviewEventFile)
    )
    historical_authority = CanonicalAuthorityArtifact.model_validate(
        _load_model(root, HISTORICAL_AUTHORITY_REFERENCE, CanonicalAuthorityArtifact)
    )
    historical_manifest = CanonicalAuthorityManifest.model_validate(
        _load_model(root, HISTORICAL_MANIFEST_REFERENCE, CanonicalAuthorityManifest)
    )
    _validate_historical_checkpoint(historical_authority, historical_manifest)
    authority = _build_reaudited_authority(root, car_bundle, car_manifest, events)
    return ReauditContext(
        car_authorization=private_auth,
        car_bundle=car_bundle,
        car_manifest=car_manifest,
        review_events=events,
        historical_authority=historical_authority,
        historical_manifest=historical_manifest,
        authority=authority,
    )


def build_car_t6_readiness(root: Path) -> CarT6Readiness:
    """Validate a possible v2 RHB-T4 re-audit without writing its authorization or outputs."""

    root = root.absolute()
    context = _load_context(root)
    states = _output_states(root)
    if any(states.values()) and not all(states.values()):
        raise AuthorityContractError("partial CAR-T6 re-audit output state")
    if all(states.values()):
        raise AuthorityContractError("CAR-T6 re-audit is already materialized; use check mode")
    body: dict[str, Any] = {
        "schema_version": "pvr-car-t6-rhb-t4-reaudit-readiness-v1",
        "gate": "CAR-T6",
        "status": "ready_for_separate_owner_authorization",
        "historical_gate_result": "blocked_insufficient_exact_authority",
        "historical_checkpoint_preserved": True,
        "car_t5f_gate_result": context.car_manifest.gate_status,
        "proposed_reaudit_gate_result": "passed_exact_authority_gate",
        "approved_exact_variant_count": len(context.authority.records),
        "qualifying_family_count": context.car_manifest.qualifying_family_count,
        "exact_variant_shortfall": 0,
        "qualifying_family_shortfall": 0,
        "reaudited_authority_present": states[REAUDIT_AUTHORITY_REFERENCE],
        "reaudited_manifest_present": states[REAUDIT_MANIFEST_REFERENCE],
        "car_t6_authorization_present": states[CAR_T6_AUTHORIZATION_REFERENCE],
        "resolver_output_consulted": False,
        "benchmark_labels_consulted": False,
        "network_requests": 0,
        "rhb_t5_authorized": False,
    }
    return CarT6Readiness.model_validate(_with_hash(body, "readiness_sha256"))


def _validate_car_t6_response(response: str) -> None:
    compact = " ".join(response.split())
    required = ("CAR-T6", "RHB-T4", "re-audit", "RHB-T5", "query pack", "labels")
    if any(token not in compact for token in required):
        raise AuthorityContractError(
            "CAR-T6 requires a fresh explicit versioned RHB-T4 re-audit authorization"
        )
    if "不授權 RHB-T5" not in compact and "does not authorize RHB-T5" not in compact:
        raise AuthorityContractError("CAR-T6 authorization must keep RHB-T5 unauthorized")


def _authorization(
    root: Path,
    context: ReauditContext,
    *,
    owner_response_verbatim: str,
    authorized_car_t6_owner_response: str,
    authorized_at: datetime,
) -> CarT6Authorization:
    if owner_response_verbatim != authorized_car_t6_owner_response:
        raise AuthorityContractError("CAR-T6 owner response differs from the authorized response")
    _validate_car_t6_response(authorized_car_t6_owner_response)
    timestamp = authorized_at.astimezone(UTC).replace(microsecond=0)
    if timestamp != authorized_at:
        raise AuthorityContractError("CAR-T6 authorization timestamp must be whole-second UTC")
    response_sha = hashlib.sha256(owner_response_verbatim.encode()).hexdigest()
    if response_sha == context.car_authorization.response_verbatim_sha256:
        raise AuthorityContractError("CAR-T6 authorization cannot reuse CAR-T5F owner response")
    body: dict[str, Any] = {
        "schema_version": "pvr-car-t6-rhb-t4-reaudit-authorization-v1",
        "gate": "CAR-T6",
        "authorization_scope": "versioned_rhb_t4_authority_reaudit_only",
        "authorization_declaration": CAR_T6_DECLARATION,
        "owner_response_verbatim": owner_response_verbatim,
        "authorized_car_t6_owner_response": authorized_car_t6_owner_response,
        "response_verbatim_sha256": response_sha,
        "car_t5f_authorization_sha256": context.car_authorization.authorization_sha256,
        "car_authority_bundle_sha256": _raw_sha(root / AUTHORITY_BUNDLE_REFERENCE),
        "car_authority_manifest_sha256": _raw_sha(root / AUTHORITY_MANIFEST_REFERENCE),
        "historical_rhb_t4_authority_sha256": _raw_sha(root / HISTORICAL_AUTHORITY_REFERENCE),
        "historical_rhb_t4_manifest_sha256": _raw_sha(root / HISTORICAL_MANIFEST_REFERENCE),
        "approved_exact_count": 20,
        "qualifying_family_count": context.car_manifest.qualifying_family_count,
        "confirmation_method": "owner_attestation",
        "reviewed_by_role": "project_owner",
        "authorized_at": timestamp.isoformat().replace("+00:00", "Z"),
        "resolver_output_consulted": False,
        "benchmark_labels_consulted": False,
        "network_requests": 0,
        "rhb_t5_authorized": False,
    }
    return CarT6Authorization.model_validate(_with_hash(body, "authorization_sha256"))


def _manifest(
    root: Path,
    context: ReauditContext,
    authorization: CarT6Authorization,
) -> CarT6ReauditManifest:
    public_inputs = {
        "car-t5f-approved-authority.json": AUTHORITY_BUNDLE_REFERENCE,
        "car-t5f-authority-manifest.json": AUTHORITY_MANIFEST_REFERENCE,
        "catalog.json": CATALOG_REFERENCE,
        "historical-rhb-t4-authority.json": HISTORICAL_AUTHORITY_REFERENCE,
        "historical-rhb-t4-manifest.json": HISTORICAL_MANIFEST_REFERENCE,
        "review-events.json": REVIEW_EVENTS_REFERENCE,
    }
    parents = [
        ArtifactDigest(reference=reference, sha256=_raw_sha(root / path))
        for reference, path in sorted(public_inputs.items())
    ]
    parents.append(
        ArtifactDigest(
            reference="private-car-t6-owner-authorization.json",
            sha256=authorization.authorization_sha256,
        )
    )
    body: dict[str, Any] = {
        "schema_version": "pvr-representative-hard-benchmark-car-t6-reaudit-manifest-v1",
        "audit_version": AUDIT_VERSION,
        "status": "complete",
        "generated_by": "scripts/build_representative_hard_benchmark_authority_reaudit.py",
        "generated_at": authorization.authorized_at.isoformat().replace("+00:00", "Z"),
        "authority_file": "canonical-authority-reaudit-v1.json",
        "authority_sha256": content_sha256(context.authority.model_dump(mode="json")),
        "authority_version": AUTHORITY_VERSION,
        "authority_record_order": [item.authority_id for item in context.authority.records],
        "ordered_input_artifacts": [
            item.model_dump(mode="json")
            for item in sorted(parents, key=lambda item: item.reference)
        ],
        "historical_rhb_t4": {
            "authority_sha256": _raw_sha(root / HISTORICAL_AUTHORITY_REFERENCE),
            "manifest_sha256": _raw_sha(root / HISTORICAL_MANIFEST_REFERENCE),
            "authority_record_count": 0,
            "gate_result": "blocked_insufficient_exact_authority",
            "preserved_without_overwrite": True,
        },
        "catalog_version": "catalog-v2",
        "catalog_sha256": _raw_sha(root / CATALOG_REFERENCE),
        "approved_exact_variant_count": 20,
        "qualifying_family_count": context.car_manifest.qualifying_family_count,
        "family_composition": [
            item.model_dump(mode="json") for item in context.car_manifest.family_composition
        ],
        "thresholds": {
            "minimum_exact_variants": 20,
            "observed_exact_variants": 20,
            "exact_variant_shortfall": 0,
            "minimum_qualifying_families": 4,
            "observed_qualifying_families": context.car_manifest.qualifying_family_count,
            "qualifying_family_shortfall": 0,
        },
        "gate_result": "passed_exact_authority_gate",
        "next_allowed_step": "owner_gate_rhb_t5_separate_authorization_required",
        "prohibited_next_steps": ["RHB_T5", "query_pack_authoring", "label_authoring"],
        "publication_scope": "safe_metadata_and_authority_records",
        "network_requests": 0,
        "resolver_output_consulted": False,
        "benchmark_labels_consulted": False,
        "rhb_t5_authorized": False,
        "car_t6_authorization_sha256": authorization.authorization_sha256,
    }
    return CarT6ReauditManifest.model_validate(_with_hash(body, "manifest_sha256"))


def run_car_t6_reaudit(
    root: Path,
    *,
    owner_response_verbatim: str,
    authorized_car_t6_owner_response: str,
    authorized_at: datetime | None = None,
    check: bool = False,
) -> Literal["created", "unchanged"]:
    """Materialize a new RHB-T4 re-audit only after explicit CAR-T6 authorization."""

    root = root.absolute()
    context = _load_context(root)
    states = _output_states(root)
    if any(states.values()) and not all(states.values()):
        raise AuthorityContractError("partial CAR-T6 re-audit output state")
    materialized = all(states.values())
    if check and not materialized:
        raise AuthorityContractError("CAR-T6 re-audit is not materialized")
    if materialized:
        for reference in states:
            path = _safe_path(root, reference, allow_missing_leaf=False)
            expected_mode = 0o600 if reference == CAR_T6_AUTHORIZATION_REFERENCE else 0o644
            if (
                path.is_symlink()
                or not path.is_file()
                or stat.S_IMODE(path.stat().st_mode) != expected_mode
            ):
                raise AuthorityContractError("CAR-T6 output artifact permissions are unsafe")
    timestamp = authorized_at
    if materialized and timestamp is None:
        payload, _raw = _strict_json(root / CAR_T6_AUTHORIZATION_REFERENCE)
        timestamp = CarT6Authorization.model_validate(payload).authorized_at
    timestamp = timestamp or datetime.now(UTC).replace(microsecond=0)
    authorization = _authorization(
        root,
        context,
        owner_response_verbatim=owner_response_verbatim,
        authorized_car_t6_owner_response=authorized_car_t6_owner_response,
        authorized_at=timestamp,
    )
    manifest = _manifest(root, context, authorization)
    outputs = {
        CAR_T6_AUTHORIZATION_REFERENCE: stable_json_bytes(authorization.model_dump(mode="json")),
        REAUDIT_AUTHORITY_REFERENCE: stable_json_bytes(context.authority.model_dump(mode="json")),
        REAUDIT_MANIFEST_REFERENCE: stable_json_bytes(manifest.model_dump(mode="json")),
    }
    public = outputs[REAUDIT_AUTHORITY_REFERENCE] + outputs[REAUDIT_MANIFEST_REFERENCE]
    if authorization.owner_response_verbatim.encode() in public:
        raise AuthorityContractError("CAR-T6 public output contains private owner text")
    targets = {
        reference: _safe_path(root, reference, allow_missing_leaf=True) for reference in outputs
    }
    if materialized and all(targets[ref].read_bytes() == raw for ref, raw in outputs.items()):
        return "unchanged"
    if check:
        raise AuthorityContractError("CAR-T6 outputs differ from expected re-audit state")
    original = {
        reference: path.read_bytes() for reference, path in targets.items() if path.exists()
    }
    temps: list[Path] = []
    installed: list[Path] = []
    try:
        for reference, raw in outputs.items():
            mode = 0o600 if reference == CAR_T6_AUTHORIZATION_REFERENCE else 0o644
            temps.append(_write_temp(targets[reference], raw, mode))
        for (reference, target), temp in zip(targets.items(), temps, strict=True):
            os.replace(temp, target)
            installed.append(target)
            os.chmod(target, 0o600 if reference == CAR_T6_AUTHORIZATION_REFERENCE else 0o644)
            _fsync_directory(target.parent)
    except BaseException:
        for temp in temps:
            if temp.exists() and not temp.is_symlink():
                temp.unlink()
        for target in reversed(installed):
            reference = next(ref for ref, path in targets.items() if path == target)
            if reference in original:
                mode = 0o600 if reference == CAR_T6_AUTHORIZATION_REFERENCE else 0o644
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
    "CAR_T6_AUTHORIZATION_REFERENCE",
    "REAUDIT_AUTHORITY_REFERENCE",
    "REAUDIT_MANIFEST_REFERENCE",
    "CarT6Authorization",
    "CarT6Readiness",
    "CarT6ReauditManifest",
    "build_car_t6_readiness",
    "run_car_t6_reaudit",
]
