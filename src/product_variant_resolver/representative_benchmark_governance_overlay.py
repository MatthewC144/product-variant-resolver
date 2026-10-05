"""Materialize the owner-approved, bundle-specific RHB-T6 governance overlay."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.representative_benchmark import (
    CanonicalAuthorityArtifact,
    RhbT6GovernanceOverlay,
    SourceDecisionArtifact,
    content_sha256,
    stable_json_bytes,
    validate_rhb_t6_governance_overlay,
    validate_source_decisions,
    validate_t1_inventory_files,
)
from product_variant_resolver.representative_benchmark_governance_repair import (
    AUTHORITY_REFERENCE,
    INVENTORY_MANIFEST_REFERENCE,
    INVENTORY_REFERENCE,
    PROPOSAL_REFERENCE,
    QUERY_PACK_MANIFEST_REFERENCE,
    SOURCE_DECISIONS_REFERENCE,
    WIKI_SOURCE_REFERENCE,
    GovernanceRepairProposal,
    build_governance_repair_proposal,
)
from product_variant_resolver.representative_benchmark_query_authoring import (
    PRIVATE_AUTHORING_DIRECTORY,
    validate_materialized_query_pack,
)

OVERLAY_REFERENCE = (
    Path("data/evaluation/representative-hard-benchmark-v1") / "rhb-t6-governance-overlay-v1.json"
)
OWNER_AUTHORIZATION_REFERENCE = (
    PRIVATE_AUTHORING_DIRECTORY / "rhb-t6-governance-repair-owner-authorization.json"
)
RHB_T6_AUTHORIZATION_REFERENCE = PRIVATE_AUTHORING_DIRECTORY / "rhb-t6-owner-authorization.json"
LABEL_REFERENCES = (
    PRIVATE_AUTHORING_DIRECTORY / "labels.json",
    PRIVATE_AUTHORING_DIRECTORY / "held-labels.json",
    Path("data/evaluation/representative-hard-benchmark-v1") / "labels-manifest.json",
)
OWNER_RESPONSE_SHA256 = "d7498e7dc5e24a36878e0297da1fd3989e9cb5418d9fb1aa3a4b583ef1e983f0"
ALLOWED_ACTIONS = ["materialize_versioned_governance_overlay"]
PROHIBITED_ACTIONS = [
    "RHB-T6_label_authoring",
    "RHB-T7_split_assignment",
    "resolver_evaluation",
]

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
NonBlank = Annotated[str, Field(min_length=1)]


class GovernanceOverlayError(ValueError):
    """Raised when authorization, proposal, or overlay state is unsafe or stale."""


class OwnerAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    schema_version: Literal["pvr-rhb-t6-governance-repair-owner-authorization-v1"]
    gate: Literal["RHB-T6-GOVERNANCE-REPAIR"]
    authorized_by: Literal["project_owner"]
    authorization_date: Literal["2026-10-05"]
    authorization_text: NonBlank
    authorization_text_sha256: Sha256
    proposal_sha256: Sha256
    proposal_file_sha256: Sha256
    query_pack_sha256: Sha256
    authority_sha256: Sha256
    allowed_actions: list[NonBlank]
    prohibited_actions: list[NonBlank]
    rhb_t6_label_authoring_authorized: Literal[False]
    rhb_t7_authorized: Literal[False]
    resolver_evaluation_authorized: Literal[False]
    authorization_sha256: Sha256

    @model_validator(mode="after")
    def authorization_is_exact_narrow_and_hash_bound(self) -> OwnerAuthorization:
        actual_text_sha256 = hashlib.sha256(self.authorization_text.encode()).hexdigest()
        if (
            actual_text_sha256 != OWNER_RESPONSE_SHA256
            or self.authorization_text_sha256 != OWNER_RESPONSE_SHA256
        ):
            raise ValueError("governance-repair owner response is generic or mismatched")
        if self.allowed_actions != ALLOWED_ACTIONS:
            raise ValueError("governance-repair allowed actions changed")
        if self.prohibited_actions != PROHIBITED_ACTIONS:
            raise ValueError("governance-repair prohibited actions changed")
        expected = content_sha256(self.model_dump(mode="json", exclude={"authorization_sha256"}))
        if self.authorization_sha256 != expected:
            raise ValueError("governance-repair authorization checksum is stale")
        return self


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GovernanceOverlayError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise GovernanceOverlayError(f"{path}: could not read strict JSON") from error
    if not isinstance(value, dict):
        raise GovernanceOverlayError(f"{path}: JSON root must be an object")
    return value


def _raw_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise GovernanceOverlayError(f"{path}: could not compute SHA-256") from error


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise GovernanceOverlayError(message)


def _load_authorization(root: Path, proposal: GovernanceRepairProposal) -> OwnerAuthorization:
    private_directory = root / PRIVATE_AUTHORING_DIRECTORY
    authorization_path = root / OWNER_AUTHORIZATION_REFERENCE
    _expect(
        private_directory.is_dir()
        and not private_directory.is_symlink()
        and stat.S_IMODE(private_directory.stat().st_mode) == 0o700,
        "private authoring directory must remain a real 0700 directory",
    )
    _expect(
        authorization_path.is_file()
        and not authorization_path.is_symlink()
        and stat.S_IMODE(authorization_path.stat().st_mode) == 0o600,
        "governance-repair authorization must be a real 0600 file",
    )
    authorization = OwnerAuthorization.model_validate(_load_object(authorization_path))
    _expect(
        authorization.proposal_sha256 == proposal.proposal_sha256
        and authorization.proposal_file_sha256 == _raw_sha256(root / PROPOSAL_REFERENCE),
        "owner authorization references a different proposal",
    )
    _expect(
        authorization.query_pack_sha256 == proposal.query_label_admission.query_pack_sha256
        and authorization.authority_sha256 == proposal.authority_bundle_admission.authority_sha256,
        "owner authorization references different governed parents",
    )
    return authorization


def _validated_context(
    root: Path,
) -> tuple[
    GovernanceRepairProposal,
    OwnerAuthorization,
    CanonicalAuthorityArtifact,
    SourceDecisionArtifact,
]:
    proposal = GovernanceRepairProposal.model_validate(_load_object(root / PROPOSAL_REFERENCE))
    _expect(
        proposal == build_governance_repair_proposal(root),
        "materialized governance-repair proposal is stale",
    )
    authorization = _load_authorization(root, proposal)
    _expect(
        not (root / RHB_T6_AUTHORIZATION_REFERENCE).exists(),
        "RHB-T6 label authorization already exists",
    )
    _expect(
        not any((root / reference).exists() for reference in LABEL_REFERENCES),
        "label artifacts already exist before governance repair",
    )

    inventory_payload = _load_object(root / INVENTORY_REFERENCE)
    inventory_manifest_payload = _load_object(root / INVENTORY_MANIFEST_REFERENCE)
    decisions_payload = _load_object(root / SOURCE_DECISIONS_REFERENCE)
    wiki_payload = _load_object(root / WIKI_SOURCE_REFERENCE)
    _inventory, _manifest = validate_t1_inventory_files(
        inventory_payload, inventory_manifest_payload
    )
    decisions = validate_source_decisions(
        decisions_payload,
        inventory_payload=inventory_payload,
        wiki_source_payload=wiki_payload,
    )
    authority = CanonicalAuthorityArtifact.model_validate(_load_object(root / AUTHORITY_REFERENCE))
    return proposal, authorization, authority, decisions


def build_governance_overlay(root: Path) -> RhbT6GovernanceOverlay:
    """Build the exact public overlay authorized by the private owner ledger."""

    root = root.absolute()
    proposal, authorization, authority, decisions = _validated_context(root)
    query_pack, _query_manifest = validate_materialized_query_pack(root)
    input_references = (
        AUTHORITY_REFERENCE,
        INVENTORY_REFERENCE,
        PROPOSAL_REFERENCE,
        QUERY_PACK_MANIFEST_REFERENCE,
        SOURCE_DECISIONS_REFERENCE,
    )
    inputs = [
        {"path": reference.as_posix(), "sha256": _raw_sha256(root / reference)}
        for reference in sorted(input_references, key=lambda item: item.as_posix())
    ]
    body: dict[str, Any] = {
        "schema_version": "pvr-rhb-t6-governance-overlay-v1",
        "overlay_version": "rhb-t6-governance-overlay-v1",
        "materialization_date": "2026-10-05",
        "status": "active_for_bound_artifacts",
        "materialized_by": ("scripts/build_representative_hard_benchmark_governance_overlay.py"),
        "proposal_sha256": proposal.proposal_sha256,
        "owner_response_sha256": authorization.authorization_text_sha256,
        "owner_authorization_sha256": authorization.authorization_sha256,
        "input_artifacts": inputs,
        "frozen_t1_t3_preserved_without_overwrite": True,
        "query_label_admission": {
            "query_source_id": proposal.query_label_admission.query_source_id,
            "query_pack_sha256": proposal.query_label_admission.query_pack_sha256,
            "query_pack_record_count": proposal.query_label_admission.query_pack_record_count,
            "additional_allowed_status": "matched",
            "maximum_matched_labels": proposal.query_label_admission.maximum_matched_labels,
            "publication_scope": "local_only",
            "admission_scope": "bound_query_pack_only",
            "human_source_remains_ineligible_for_exact_authority": True,
            "exact_admitted_authority_required_for_every_matched_label": True,
            "owner_review_required_for_every_label": True,
            "public_row_publication_authorized": False,
        },
        "authority_bundle_admission": {
            "authority_sha256": proposal.authority_bundle_admission.authority_sha256,
            "authority_record_count": proposal.authority_bundle_admission.authority_record_count,
            "authority_record_ids": proposal.authority_bundle_admission.authority_record_ids,
            "evidence_source_id": proposal.authority_bundle_admission.evidence_source_id,
            "evidence_source_revision_id": (
                proposal.authority_bundle_admission.evidence_source_revision_id
            ),
            "admission_scope": "exact_records_in_bound_car_bundle_only",
            "source_wide_exact_authority_promotion": False,
            "manufacturer_certification_claimed": False,
            "color_or_edition_newly_verified": False,
            "resolver_output_consulted": False,
            "benchmark_labels_consulted": False,
        },
        "challenge_review_carry_forward": {
            "provisional_shortfalls": (
                proposal.challenge_review_carry_forward.provisional_shortfalls
            ),
            "provisional_shortfall_total": (
                proposal.challenge_review_carry_forward.provisional_shortfall_total
            ),
            "owner_label_review_must_verify_or_hold": True,
            "representative_pilot_preapproved": False,
        },
        "governance_overlay_materialized": True,
        "rhb_t6_label_authoring_authorized": False,
        "rhb_t7_authorized": False,
        "resolver_evaluation_authorized": False,
        "network_requests": 0,
        "next_allowed_action": (
            "rerun_rhb_t6_readiness_then_request_separate_label_authoring_gate"
        ),
    }
    overlay = RhbT6GovernanceOverlay.model_validate(
        {**body, "overlay_sha256": content_sha256(body)}
    )
    validate_rhb_t6_governance_overlay(
        overlay.model_dump(mode="json"),
        query_pack=query_pack,
        authority=authority,
        source_decisions=decisions,
    )
    return overlay


def validate_materialized_governance_overlay(root: Path) -> RhbT6GovernanceOverlay:
    """Validate public overlay bytes against the private authorization and all parents."""

    root = root.absolute()
    expected = build_governance_overlay(root)
    target = root / OVERLAY_REFERENCE
    _expect(target.is_file() and not target.is_symlink(), "governance overlay is absent or unsafe")
    _expect(stat.S_IMODE(target.stat().st_mode) == 0o644, "governance overlay must use mode 0644")
    actual = RhbT6GovernanceOverlay.model_validate(_load_object(target))
    _expect(actual == expected, "materialized governance overlay is stale or tampered")
    _expect(
        target.read_bytes() == stable_json_bytes(expected.model_dump(mode="json")),
        "governance overlay bytes are non-canonical",
    )
    return actual


def materialize_governance_overlay(
    root: Path, *, check: bool = False
) -> Literal["created", "unchanged"]:
    """Create or check the approved overlay without creating label authority."""

    root = root.absolute()
    overlay = build_governance_overlay(root)
    target = root / OVERLAY_REFERENCE
    expected = stable_json_bytes(overlay.model_dump(mode="json"))
    if target.exists():
        validate_materialized_governance_overlay(root)
        if target.read_bytes() == expected:
            return "unchanged"
        raise GovernanceOverlayError("materialized overlay differs from canonical bytes")
    if check:
        raise GovernanceOverlayError("governance overlay is not materialized")
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
        validate_materialized_governance_overlay(root)
    except BaseException:
        temp.unlink(missing_ok=True)
        if target.exists() and not target.is_symlink():
            target.unlink()
        raise
    return "created"


__all__ = [
    "OVERLAY_REFERENCE",
    "OWNER_AUTHORIZATION_REFERENCE",
    "GovernanceOverlayError",
    "OwnerAuthorization",
    "build_governance_overlay",
    "materialize_governance_overlay",
    "validate_materialized_governance_overlay",
]
