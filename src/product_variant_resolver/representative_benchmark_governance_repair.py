"""Deterministic, non-authorizing RHB-T6 governance-repair proposal.

The proposal narrows future matched-label permission to one frozen query pack and
one frozen CAR authority bundle. It never mutates T1/T3, grants RHB-T6, or writes
labels. Materializing an executable overlay requires a separate owner decision.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.representative_benchmark import (
    CanonicalAuthorityArtifact,
    SourceAllowedLabelStatus,
    SourceDecisionArtifact,
    SourceInventory,
    content_sha256,
    stable_json_bytes,
    validate_source_decisions,
    validate_t1_inventory_files,
)
from product_variant_resolver.representative_benchmark_label_readiness import (
    build_rhb_t6_label_readiness,
)
from product_variant_resolver.representative_benchmark_query_authoring import (
    QueryPackManifest,
)
from product_variant_resolver.representative_benchmark_reaudit import CarT6ReauditManifest

RHB_DIRECTORY = Path("data/evaluation/representative-hard-benchmark-v1")
PROPOSAL_REFERENCE = RHB_DIRECTORY / "rhb-t6-governance-repair-proposal.json"
INVENTORY_REFERENCE = RHB_DIRECTORY / "source-inventory.json"
INVENTORY_MANIFEST_REFERENCE = RHB_DIRECTORY / "source-inventory-manifest.json"
SOURCE_DECISIONS_REFERENCE = RHB_DIRECTORY / "source-decisions.json"
QUERY_PACK_MANIFEST_REFERENCE = RHB_DIRECTORY / "query-pack-manifest.json"
AUTHORITY_REFERENCE = RHB_DIRECTORY / "canonical-authority-reaudit-v1.json"
AUTHORITY_MANIFEST_REFERENCE = RHB_DIRECTORY / "canonical-authority-reaudit-manifest-v1.json"
WIKI_SOURCE_REFERENCE = Path("data/external/hot-wheels-wiki/pilot-2025/normalized.json")

QUERY_SOURCE_ID = "human-labeled-real-noisy-v1"
AUTHORITY_EVIDENCE_SOURCE_ID = "fandom-hot-wheels-2025-pilot-r790665-v1"
SOURCE_REVISION_ID = 790665
PROHIBITED_ACTIONS = [
    "mutate_frozen_t1_t3_in_place",
    "promote_human_labels_to_canonical_authority",
    "promote_full_wiki_source_to_global_exact_authority",
    "materialize_governance_overlay_without_owner_approval",
    "RHB-T6_label_authoring",
    "RHB-T7_split_assignment",
    "resolver_evaluation",
    "manufacturer_or_global_truth_claim",
]

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
NonBlank = Annotated[str, Field(min_length=1)]


class GovernanceRepairError(ValueError):
    """Raised when the proposal inputs drift or an unsafe proposal is requested."""


class ProposalContract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ProposalInput(ProposalContract):
    path: NonBlank
    sha256: Sha256


class QueryLabelAdmissionProposal(ProposalContract):
    query_source_id: Literal["human-labeled-real-noisy-v1"]
    query_pack_sha256: Sha256
    query_pack_record_count: Literal[60]
    current_allowed_statuses: list[SourceAllowedLabelStatus]
    proposed_additional_status: Literal[SourceAllowedLabelStatus.matched]
    maximum_matched_labels: Literal[20]
    publication_scope: Literal["local_only"]
    admission_scope: Literal["bound_query_pack_only"]
    human_source_remains_ineligible_for_exact_authority: Literal[True]
    exact_admitted_authority_required_for_every_matched_label: Literal[True]
    owner_review_required_for_every_label: Literal[True]
    public_row_publication_authorized: Literal[False]

    @model_validator(mode="after")
    def admission_is_narrow(self) -> QueryLabelAdmissionProposal:
        if self.current_allowed_statuses != [
            SourceAllowedLabelStatus.ambiguous,
            SourceAllowedLabelStatus.no_match,
        ]:
            raise ValueError("query-source status baseline changed")
        return self


class AuthorityBundleAdmissionProposal(ProposalContract):
    authority_sha256: Sha256
    authority_manifest_sha256: Sha256
    authority_record_count: Literal[20]
    authority_record_ids: list[NonBlank] = Field(min_length=20, max_length=20)
    evidence_source_id: Literal["fandom-hot-wheels-2025-pilot-r790665-v1"]
    evidence_source_revision_id: Literal[790665]
    admission_scope: Literal["exact_records_in_bound_car_bundle_only"]
    source_wide_exact_authority_promotion: Literal[False]
    manufacturer_certification_claimed: Literal[False]
    color_or_edition_newly_verified: Literal[False]
    resolver_output_consulted: Literal[False]
    benchmark_labels_consulted: Literal[False]

    @model_validator(mode="after")
    def record_ids_are_unique_and_ordered(self) -> AuthorityBundleAdmissionProposal:
        if self.authority_record_ids != sorted(set(self.authority_record_ids)):
            raise ValueError("authority admission IDs must be unique and ordered")
        return self


class ChallengeReviewCarryForward(ProposalContract):
    provisional_shortfalls: dict[str, int]
    provisional_shortfall_total: Literal[16]
    owner_label_review_must_verify_or_hold: Literal[True]
    representative_pilot_preapproved: Literal[False]

    @model_validator(mode="after")
    def shortfalls_are_recomputable(self) -> ChallengeReviewCarryForward:
        if sum(self.provisional_shortfalls.values()) != self.provisional_shortfall_total:
            raise ValueError("challenge shortfall total is inconsistent")
        return self


class GovernanceRepairProposal(ProposalContract):
    schema_version: Literal["pvr-rhb-t6-governance-repair-proposal-v1"]
    proposal_version: Literal["rhb-t6-governance-repair-proposal-v1"]
    proposal_date: Literal["2026-10-05"]
    status: Literal["awaiting_owner_decision"]
    generated_by: Literal[
        "scripts/build_representative_hard_benchmark_governance_repair_proposal.py"
    ]
    readiness_sha256: Sha256
    inputs: list[ProposalInput] = Field(min_length=5)
    frozen_t1_t3_preserved_without_overwrite: Literal[True]
    query_label_admission: QueryLabelAdmissionProposal
    authority_bundle_admission: AuthorityBundleAdmissionProposal
    challenge_review_carry_forward: ChallengeReviewCarryForward
    proposal_only: Literal[True]
    owner_decision_required: Literal[True]
    governance_overlay_materialized: Literal[False]
    rhb_t6_authorized: Literal[False]
    rhb_t7_authorized: Literal[False]
    resolver_evaluation_authorized: Literal[False]
    network_requests: Literal[0]
    prohibited_actions: list[NonBlank]
    next_allowed_action: Literal["request_owner_decision_on_governance_repair_proposal"]
    proposal_sha256: Sha256

    @model_validator(mode="after")
    def proposal_is_narrow_and_hash_bound(self) -> GovernanceRepairProposal:
        paths = [item.path for item in self.inputs]
        if paths != sorted(set(paths)):
            raise ValueError("proposal inputs must be unique and ordered")
        if self.prohibited_actions != PROHIBITED_ACTIONS:
            raise ValueError("proposal prohibitions changed or are out of order")
        expected = content_sha256(self.model_dump(mode="json", exclude={"proposal_sha256"}))
        if self.proposal_sha256 != expected:
            raise ValueError("governance-repair proposal checksum is stale")
        return self


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GovernanceRepairError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise GovernanceRepairError(f"{path}: could not read strict JSON") from error
    if not isinstance(value, dict):
        raise GovernanceRepairError(f"{path}: JSON root must be an object")
    return value


def _raw_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise GovernanceRepairError(f"{path}: could not compute SHA-256") from error


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise GovernanceRepairError(message)


def _validate_governance_inputs(
    root: Path,
) -> tuple[
    SourceInventory,
    SourceDecisionArtifact,
    QueryPackManifest,
    CanonicalAuthorityArtifact,
    CarT6ReauditManifest,
]:
    inventory_payload = _load_object(root / INVENTORY_REFERENCE)
    inventory_manifest_payload = _load_object(root / INVENTORY_MANIFEST_REFERENCE)
    decisions_payload = _load_object(root / SOURCE_DECISIONS_REFERENCE)
    wiki_payload = _load_object(root / WIKI_SOURCE_REFERENCE)
    inventory, _manifest = validate_t1_inventory_files(
        inventory_payload, inventory_manifest_payload
    )
    decisions = validate_source_decisions(
        decisions_payload,
        inventory_payload=inventory_payload,
        wiki_source_payload=wiki_payload,
    )
    query_manifest = QueryPackManifest.model_validate(
        _load_object(root / QUERY_PACK_MANIFEST_REFERENCE)
    )
    authority = CanonicalAuthorityArtifact.model_validate(_load_object(root / AUTHORITY_REFERENCE))
    authority_manifest = CarT6ReauditManifest.model_validate(
        _load_object(root / AUTHORITY_MANIFEST_REFERENCE)
    )
    _expect(
        query_manifest.record_count == 60
        and query_manifest.non_sensitive_aggregate.source_id == QUERY_SOURCE_ID,
        "query-pack proposal parent changed",
    )
    _expect(
        authority_manifest.authority_sha256 == _raw_sha256(root / AUTHORITY_REFERENCE)
        and authority_manifest.approved_exact_variant_count == len(authority.records) == 20,
        "authority proposal parent changed",
    )
    return inventory, decisions, query_manifest, authority, authority_manifest


def build_governance_repair_proposal(root: Path) -> GovernanceRepairProposal:
    """Build the non-authorizing repair proposal from the exact blocked readiness state."""

    root = root.absolute()
    readiness = build_rhb_t6_label_readiness(root)
    _expect(
        readiness.status == "blocked_before_owner_gate"
        and readiness.maximum_source_permitted_matched_count == 0
        and readiness.matched_permission_shortfall == 20
        and not readiness.canonical_authority_t1_t3_compatible
        and readiness.provisional_challenge_shortfall_total == 16,
        "RHB-T6 blocked baseline changed; proposal requires re-review",
    )
    inventory, decisions, query_manifest, authority, authority_manifest = (
        _validate_governance_inputs(root)
    )
    query_decision = next(
        source for source in decisions.sources if source.source_id == QUERY_SOURCE_ID
    )
    authority_source = next(
        source for source in inventory.entries if source.source_id == AUTHORITY_EVIDENCE_SOURCE_ID
    )
    _expect(
        list(query_decision.allowed_label_statuses)
        == [SourceAllowedLabelStatus.ambiguous, SourceAllowedLabelStatus.no_match],
        "query-source label baseline changed",
    )
    _expect(
        authority_source.authority_eligibility.value == "prohibited"
        and authority_source.authority_evidence_level.value == "staging_only",
        "authority-source baseline changed",
    )

    input_references = (
        AUTHORITY_MANIFEST_REFERENCE,
        AUTHORITY_REFERENCE,
        QUERY_PACK_MANIFEST_REFERENCE,
        SOURCE_DECISIONS_REFERENCE,
        INVENTORY_REFERENCE,
    )
    inputs = [
        {"path": reference.as_posix(), "sha256": _raw_sha256(root / reference)}
        for reference in sorted(input_references, key=lambda item: item.as_posix())
    ]
    body: dict[str, Any] = {
        "schema_version": "pvr-rhb-t6-governance-repair-proposal-v1",
        "proposal_version": "rhb-t6-governance-repair-proposal-v1",
        "proposal_date": "2026-10-05",
        "status": "awaiting_owner_decision",
        "generated_by": (
            "scripts/build_representative_hard_benchmark_governance_repair_proposal.py"
        ),
        "readiness_sha256": readiness.readiness_sha256,
        "inputs": inputs,
        "frozen_t1_t3_preserved_without_overwrite": True,
        "query_label_admission": {
            "query_source_id": QUERY_SOURCE_ID,
            "query_pack_sha256": query_manifest.sha256,
            "query_pack_record_count": query_manifest.record_count,
            "current_allowed_statuses": list(query_decision.allowed_label_statuses),
            "proposed_additional_status": "matched",
            "maximum_matched_labels": 20,
            "publication_scope": "local_only",
            "admission_scope": "bound_query_pack_only",
            "human_source_remains_ineligible_for_exact_authority": True,
            "exact_admitted_authority_required_for_every_matched_label": True,
            "owner_review_required_for_every_label": True,
            "public_row_publication_authorized": False,
        },
        "authority_bundle_admission": {
            "authority_sha256": authority_manifest.authority_sha256,
            "authority_manifest_sha256": _raw_sha256(root / AUTHORITY_MANIFEST_REFERENCE),
            "authority_record_count": len(authority.records),
            "authority_record_ids": [record.authority_id for record in authority.records],
            "evidence_source_id": AUTHORITY_EVIDENCE_SOURCE_ID,
            "evidence_source_revision_id": SOURCE_REVISION_ID,
            "admission_scope": "exact_records_in_bound_car_bundle_only",
            "source_wide_exact_authority_promotion": False,
            "manufacturer_certification_claimed": False,
            "color_or_edition_newly_verified": False,
            "resolver_output_consulted": False,
            "benchmark_labels_consulted": False,
        },
        "challenge_review_carry_forward": {
            "provisional_shortfalls": readiness.provisional_challenge_shortfalls,
            "provisional_shortfall_total": readiness.provisional_challenge_shortfall_total,
            "owner_label_review_must_verify_or_hold": True,
            "representative_pilot_preapproved": False,
        },
        "proposal_only": True,
        "owner_decision_required": True,
        "governance_overlay_materialized": False,
        "rhb_t6_authorized": False,
        "rhb_t7_authorized": False,
        "resolver_evaluation_authorized": False,
        "network_requests": 0,
        "prohibited_actions": PROHIBITED_ACTIONS,
        "next_allowed_action": "request_owner_decision_on_governance_repair_proposal",
    }
    return GovernanceRepairProposal.model_validate(
        {**body, "proposal_sha256": content_sha256(body)}
    )


def materialize_governance_repair_proposal(
    root: Path, *, check: bool = False
) -> Literal["created", "unchanged"]:
    """Create or check the public proposal without authorizing its implementation."""

    root = root.absolute()
    proposal = build_governance_repair_proposal(root)
    target = root / PROPOSAL_REFERENCE
    expected = stable_json_bytes(proposal.model_dump(mode="json"))
    if target.exists():
        _expect(target.is_file() and not target.is_symlink(), "proposal path is unsafe")
        actual = GovernanceRepairProposal.model_validate(_load_object(target))
        _expect(actual == proposal, "materialized governance proposal is stale")
        _expect(target.read_bytes() == expected, "governance proposal bytes are non-canonical")
        return "unchanged"
    if check:
        raise GovernanceRepairError("governance-repair proposal is not materialized")
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(expected)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o644)
        os.replace(temp, target)
        os.chmod(target, 0o644)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    return "created"


__all__ = [
    "PROPOSAL_REFERENCE",
    "GovernanceRepairError",
    "GovernanceRepairProposal",
    "build_governance_repair_proposal",
    "materialize_governance_repair_proposal",
]
