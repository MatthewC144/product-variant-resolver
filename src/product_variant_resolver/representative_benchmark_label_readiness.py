"""Read-only RHB-T6 label-authoring readiness validation.

The validator proves whether the frozen RHB-T5 query pack can enter owner labeling.
It creates no authorization or label, does not import the resolver, and reports
source/authority contract blockers instead of weakening them.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.representative_benchmark import (
    AuthorityEligibility,
    AuthorityEvidenceLevel,
    AuthorityStatus,
    CanonicalAuthorityArtifact,
    SourceAllowedLabelStatus,
    SourceDecisionStatus,
    SourceDecisionUse,
    SourceDownstreamPermission,
    SourceKind,
    content_sha256,
    validate_source_decisions,
    validate_t1_inventory_files,
)
from product_variant_resolver.representative_benchmark_governance_overlay import (
    OVERLAY_REFERENCE,
    validate_materialized_governance_overlay,
)
from product_variant_resolver.representative_benchmark_query_authoring import (
    PRIVATE_AUTHORING_DIRECTORY,
    validate_materialized_query_pack,
)
from product_variant_resolver.representative_benchmark_reaudit import (
    REAUDIT_AUTHORITY_REFERENCE,
    REAUDIT_MANIFEST_REFERENCE,
    CarT6ReauditManifest,
)

RHB_DIRECTORY = Path("data/evaluation/representative-hard-benchmark-v1")
INVENTORY_REFERENCE = RHB_DIRECTORY / "source-inventory.json"
INVENTORY_MANIFEST_REFERENCE = RHB_DIRECTORY / "source-inventory-manifest.json"
SOURCE_DECISIONS_REFERENCE = RHB_DIRECTORY / "source-decisions.json"
WIKI_SOURCE_REFERENCE = Path("data/external/hot-wheels-wiki/pilot-2025/normalized.json")
RHB_T6_AUTHORIZATION_REFERENCE = PRIVATE_AUTHORING_DIRECTORY / "rhb-t6-owner-authorization.json"
LABEL_REFERENCES = (
    PRIVATE_AUTHORING_DIRECTORY / "labels.json",
    PRIVATE_AUTHORING_DIRECTORY / "held-labels.json",
    RHB_DIRECTORY / "labels-manifest.json",
)

TARGET_PER_STATUS = 20
READINESS_REQUIREMENTS = [
    "owner_review_each_label_and_bind_exact_authority",
    "verify_or_hold_provisional_challenge_coverage",
    "separate_rhb_t6_label_authoring_owner_gate_required",
]

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class LabelReadinessError(ValueError):
    """Raised when an RHB-T6 input is stale, partial, or prematurely materialized."""


class LabelReadiness(BaseModel):
    """Safe deterministic summary before the separate RHB-T6 owner Gate."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["pvr-rhb-t6-label-readiness-v2"]
    gate: Literal["RHB-T6"]
    status: Literal["ready_for_separate_owner_authorization"]
    query_pack_sha256: Sha256
    query_pack_record_count: Literal[60]
    query_pack_core_validator_passed: Literal[True]
    query_pack_representative_pilot: Literal[False]
    query_source_ids: list[str]
    query_source_allowed_label_statuses: dict[str, list[SourceAllowedLabelStatus]]
    target_matched_count: Literal[20]
    maximum_source_permitted_matched_count: int = Field(ge=0, le=60)
    maximum_overlay_permitted_matched_count: Literal[20]
    matched_permission_shortfall: int = Field(ge=0, le=20)
    canonical_authority_sha256: Sha256
    canonical_authority_record_count: Literal[20]
    canonical_authority_source_ids: list[str]
    canonical_authority_t1_t3_compatible: Literal[False]
    incompatible_authority_source_ids: list[str] = Field(min_length=1)
    governance_overlay_reference: Literal[
        "data/evaluation/representative-hard-benchmark-v1/rhb-t6-governance-overlay-v1.json"
    ]
    governance_overlay_sha256: Sha256
    governance_overlay_valid: Literal[True]
    canonical_authority_admitted_by_overlay: Literal[True]
    matched_labels_admitted_by_overlay: Literal[True]
    provisional_challenge_shortfalls: dict[str, int]
    provisional_challenge_shortfall_total: int = Field(ge=1)
    challenge_coverage_verified: Literal[False]
    label_artifact_count: Literal[0]
    rhb_t6_owner_authorization_present: Literal[False]
    rhb_t6_authorized: Literal[False]
    rhb_t7_authorized: Literal[False]
    resolver_evaluation_authorized: Literal[False]
    resolver_output_consulted: Literal[False]
    benchmark_labels_consulted: Literal[False]
    network_requests: Literal[0]
    owner_gate_requestable: Literal[True]
    blockers: list[str] = Field(max_length=0)
    remaining_requirements: list[str]
    next_allowed_action: Literal["request_separate_rhb_t6_label_authoring_owner_gate"]
    readiness_sha256: Sha256

    @model_validator(mode="after")
    def readiness_is_coherent_and_hash_bound(self) -> LabelReadiness:
        expected_matched_shortfall = max(
            0,
            self.target_matched_count
            - max(
                self.maximum_source_permitted_matched_count,
                self.maximum_overlay_permitted_matched_count,
            ),
        )
        if self.matched_permission_shortfall != expected_matched_shortfall:
            raise ValueError("matched permission shortfall is inconsistent")
        if self.provisional_challenge_shortfall_total != sum(
            self.provisional_challenge_shortfalls.values()
        ):
            raise ValueError("challenge shortfall total is inconsistent")
        if self.blockers:
            raise ValueError("ready RHB-T6 state cannot retain a blocker")
        if self.remaining_requirements != READINESS_REQUIREMENTS:
            raise ValueError("RHB-T6 review requirements changed or are out of order")
        expected_sha256 = content_sha256(self.model_dump(mode="json", exclude={"readiness_sha256"}))
        if self.readiness_sha256 != expected_sha256:
            raise ValueError("RHB-T6 readiness checksum is stale")
        return self


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LabelReadinessError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise LabelReadinessError(f"{path}: could not read strict JSON") from error
    if not isinstance(value, dict):
        raise LabelReadinessError(f"{path}: JSON root must be an object")
    return value


def _raw_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise LabelReadinessError(f"{path}: could not compute SHA-256") from error


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise LabelReadinessError(message)


def build_rhb_t6_label_readiness(root: Path) -> LabelReadiness:
    """Validate the RHB-T6 boundary without writing labels or authorization."""

    root = root.absolute()
    owner_authorization_present = (root / RHB_T6_AUTHORIZATION_REFERENCE).exists()
    label_artifact_count = sum((root / reference).exists() for reference in LABEL_REFERENCES)
    _expect(
        not owner_authorization_present,
        "an unvalidated RHB-T6 owner authorization already exists",
    )
    _expect(label_artifact_count == 0, "RHB-T6 label artifacts already exist")

    query_pack, query_manifest = validate_materialized_query_pack(root)
    _expect(len(query_pack.cases) == 60, "RHB-T6 requires exactly 60 query cases")
    _expect(not query_pack.representative_pilot, "blocked query pack cannot claim pilot acceptance")

    inventory_payload = _load_object(root / INVENTORY_REFERENCE)
    inventory_manifest_payload = _load_object(root / INVENTORY_MANIFEST_REFERENCE)
    decisions_payload = _load_object(root / SOURCE_DECISIONS_REFERENCE)
    wiki_payload = _load_object(root / WIKI_SOURCE_REFERENCE)
    inventory, _inventory_manifest = validate_t1_inventory_files(
        inventory_payload, inventory_manifest_payload
    )
    decisions = validate_source_decisions(
        decisions_payload,
        inventory_payload=inventory_payload,
        wiki_source_payload=wiki_payload,
    )
    query_source_ids = sorted({case.source_id for case in query_pack.cases})
    decision_sources = {source.source_id: source for source in decisions.sources}
    allowed_statuses = {
        source_id: list(decision_sources[source_id].allowed_label_statuses)
        for source_id in query_source_ids
    }
    maximum_matched = sum(
        SourceAllowedLabelStatus.matched in decision_sources[case.source_id].allowed_label_statuses
        and SourceDownstreamPermission.scored_labels
        in decision_sources[case.source_id].downstream_permissions
        for case in query_pack.cases
    )

    authority_path = root / REAUDIT_AUTHORITY_REFERENCE
    authority = CanonicalAuthorityArtifact.model_validate(_load_object(authority_path))
    authority_manifest = CarT6ReauditManifest.model_validate(
        _load_object(root / REAUDIT_MANIFEST_REFERENCE)
    )
    _expect(
        authority_manifest.authority_sha256 == _raw_sha256(authority_path),
        "CAR-T6 authority checksum drift",
    )
    _expect(
        authority_manifest.gate_result == "passed_exact_authority_gate"
        and len(authority.records) == authority_manifest.approved_exact_variant_count == 20,
        "CAR-T6 authority no longer passes its 20-record Gate",
    )
    _expect(
        all(record.status == AuthorityStatus.approved_exact for record in authority.records),
        "CAR-T6 authority contains a non-exact record",
    )
    governance_overlay = validate_materialized_governance_overlay(root)

    inventory_sources = {source.source_id: source for source in inventory.entries}
    authority_source_ids = sorted(
        {source_id for record in authority.records for source_id in record.evidence_source_ids}
    )
    incompatible_authority_sources: list[str] = []
    for source_id in authority_source_ids:
        source = inventory_sources.get(source_id)
        decision = decision_sources.get(source_id)
        exact_cell = (
            next(
                (
                    cell
                    for cell in decision.decisions
                    if cell.use == SourceDecisionUse.exact_variant_authority
                ),
                None,
            )
            if decision is not None
            else None
        )
        compatible = (
            source is not None
            and decision is not None
            and source.source_kind == SourceKind.authorized_export
            and source.authority_eligibility
            == AuthorityEligibility.exact_variant_authority_candidate
            and source.authority_evidence_level == AuthorityEvidenceLevel.independent_exact_variant
            and SourceDownstreamPermission.canonical_authority in decision.downstream_permissions
            and exact_cell is not None
            and exact_cell.status == SourceDecisionStatus.approved
        )
        if not compatible:
            incompatible_authority_sources.append(source_id)
    _expect(
        bool(incompatible_authority_sources),
        "RHB-T6 readiness contract changed; authority admission must be re-reviewed",
    )

    shortfalls = query_manifest.non_sensitive_aggregate.provisional_challenge_tag_shortfalls
    _expect(any(shortfalls.values()), "RHB-T6 readiness expected declared challenge shortfalls")
    _expect(
        governance_overlay.query_label_admission.query_pack_sha256 == query_manifest.sha256,
        "governance overlay query-pack binding drift",
    )
    _expect(
        governance_overlay.authority_bundle_admission.authority_sha256
        == authority_manifest.authority_sha256,
        "governance overlay authority binding drift",
    )
    body: dict[str, Any] = {
        "schema_version": "pvr-rhb-t6-label-readiness-v2",
        "gate": "RHB-T6",
        "status": "ready_for_separate_owner_authorization",
        "query_pack_sha256": query_manifest.sha256,
        "query_pack_record_count": len(query_pack.cases),
        "query_pack_core_validator_passed": True,
        "query_pack_representative_pilot": query_pack.representative_pilot,
        "query_source_ids": query_source_ids,
        "query_source_allowed_label_statuses": allowed_statuses,
        "target_matched_count": TARGET_PER_STATUS,
        "maximum_source_permitted_matched_count": maximum_matched,
        "maximum_overlay_permitted_matched_count": (
            governance_overlay.query_label_admission.maximum_matched_labels
        ),
        "matched_permission_shortfall": 0,
        "canonical_authority_sha256": authority_manifest.authority_sha256,
        "canonical_authority_record_count": len(authority.records),
        "canonical_authority_source_ids": authority_source_ids,
        "canonical_authority_t1_t3_compatible": False,
        "incompatible_authority_source_ids": incompatible_authority_sources,
        "governance_overlay_reference": OVERLAY_REFERENCE.as_posix(),
        "governance_overlay_sha256": governance_overlay.overlay_sha256,
        "governance_overlay_valid": True,
        "canonical_authority_admitted_by_overlay": True,
        "matched_labels_admitted_by_overlay": True,
        "provisional_challenge_shortfalls": shortfalls,
        "provisional_challenge_shortfall_total": sum(shortfalls.values()),
        "challenge_coverage_verified": False,
        "label_artifact_count": label_artifact_count,
        "rhb_t6_owner_authorization_present": owner_authorization_present,
        "rhb_t6_authorized": False,
        "rhb_t7_authorized": False,
        "resolver_evaluation_authorized": False,
        "resolver_output_consulted": False,
        "benchmark_labels_consulted": False,
        "network_requests": 0,
        "owner_gate_requestable": True,
        "blockers": [],
        "remaining_requirements": READINESS_REQUIREMENTS,
        "next_allowed_action": "request_separate_rhb_t6_label_authoring_owner_gate",
    }
    return LabelReadiness.model_validate({**body, "readiness_sha256": content_sha256(body)})


__all__ = [
    "LABEL_REFERENCES",
    "RHB_T6_AUTHORIZATION_REFERENCE",
    "LabelReadiness",
    "LabelReadinessError",
    "build_rhb_t6_label_readiness",
]
