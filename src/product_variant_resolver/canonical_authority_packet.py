"""Deterministic, output-blind CAR-T4 catalog proposal workspace.

This module deliberately does not import the resolver, FastAPI, a browser, or a network client.
It projects the repository catalog from its raw bytes, excludes every synthetic fixture, and
creates only *staged* catalog-record proposals for the owner to review locally.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, Literal, cast
from uuid import NAMESPACE_URL, UUID, uuid5

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.canonical_authority_review import (
    ApprovedSourceField,
    AuthorityCandidate,
    AuthorityContractError,
    CanonicalProductRecord,
    FieldValue,
    FrozenCatalogProduct,
    SourceRecordBinding,
    VariantField,
    content_sha256,
    stable_json_bytes,
    validate_authority_candidate,
    validate_authority_source_decisions,
)

CATALOG_REFERENCE: Literal["data/catalog.json"] = "data/catalog.json"
CANDIDATE_PLAN_REFERENCE = "data/authority-review/canonical-authority-review-v1/candidate-plan.json"
NORMALIZED_REFERENCE = "data/external/hot-wheels-wiki/pilot-2025/normalized.json"
MANIFEST_REFERENCE = (
    "data/authority-review/canonical-authority-review-v1/catalog-proposal-manifest.json"
)
LOCAL_PARENT_REFERENCE = "data/authority-review/canonical-authority-review-v1"
DEFAULT_LOCAL_NAME = "local-catalog-review-v1"
TASKS_REFERENCE = "specs/canonical-authority-review-v1/tasks.md"
CANDIDATE_PLAN_RAW_SHA256 = "a7d908a427caa255af000c4f46532f4b9d8bdb2e69c24fb8cbc85a487e1f6eaf"
EXPECTED_RAW_CATALOG_SHA256 = "0d3ea55eab414e3845bf3bf72635707210f2d5c20d96b3d6b5940eb0ffc7d261"
SOURCE_ID = "fandom-hot-wheels-2025-pilot-r790665-v1"

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
OpaqueId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:#-]{0,199}$")]
NonBlank = Annotated[str, Field(min_length=1)]


class PacketContract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, validate_assignment=True)


class RawAlias(PacketContract):
    alias_text: NonBlank
    alias_type: NonBlank
    source_id: NonBlank


class RawIdentifier(PacketContract):
    identifier_type: NonBlank
    identifier_value: NonBlank
    source_id: NonBlank


class RawProvenance(PacketContract):
    confidence_note: NonBlank
    field_name: str | None
    license_note: NonBlank
    retrieved_at: NonBlank
    source_name: NonBlank
    source_reference: NonBlank
    value_snapshot: NonBlank


class RawCatalogProduct(PacketContract):
    aliases: list[RawAlias]
    brand: NonBlank
    canonical_id: NonBlank
    canonical_uuid: UUID
    casting: NonBlank
    collector_number: str | None
    color: str | None
    edition: str | None
    identifiers: list[RawIdentifier]
    near_duplicate_group: NonBlank
    provenance: list[RawProvenance] = Field(min_length=1)
    rarity_tier: str | None
    release_year: int
    series: str | None
    series_position: str | None

    @property
    def is_synthetic_fixture(self) -> bool:
        return all(
            item.source_name == "synthetic_fixture"
            and item.source_reference.startswith("synthetic://fixture-v1/")
            and "synthetic test data" in item.license_note.casefold()
            for item in self.provenance
        )


class RawCatalog(PacketContract):
    catalog_version: Literal["fixture-v1"]
    dataset_version: Literal["fixture-v1"]
    products: list[RawCatalogProduct] = Field(min_length=1)
    source_note: Literal[
        "Deterministic synthetic records for architecture and test validation only; not an authoritative Hot Wheels catalog."
    ]

    @model_validator(mode="after")
    def identities_are_unique(self) -> RawCatalog:
        uuids = [item.canonical_uuid for item in self.products]
        ids = [item.canonical_id for item in self.products]
        if len(uuids) != len(set(uuids)) or len(ids) != len(set(ids)):
            raise ValueError("raw catalog identities must be unique")
        return self


class FrozenCatalogProjectionV2(PacketContract):
    """Raw-byte-bound eligibility projection; v1's nonempty-product contract stays untouched."""

    schema_version: Literal["pvr-canonical-authority-frozen-catalog-projection-v2"]
    raw_catalog_reference: Literal["data/catalog.json"]
    raw_catalog_version: Literal["fixture-v1"]
    raw_catalog_sha256: Sha256
    raw_product_count: Literal[120]
    raw_uuid_set_sha256: Sha256
    eligibility_policy: Literal["explicit_non_synthetic_exact_only"]
    eligible_products: list[FrozenCatalogProduct]
    eligible_product_count: int = Field(ge=0)
    excluded_synthetic_product_count: int = Field(ge=0)
    exclusion_reasons: dict[Literal["synthetic_fixture"], int]
    projection_sha256: Sha256

    @model_validator(mode="after")
    def counts_and_digest_are_self_consistent(self) -> FrozenCatalogProjectionV2:
        if self.eligible_product_count != len(self.eligible_products):
            raise ValueError("eligible product count is stale")
        if self.excluded_synthetic_product_count != self.exclusion_reasons.get(
            "synthetic_fixture", 0
        ):
            raise ValueError("synthetic exclusion count is stale")
        uuids = [item.canonical_uuid for item in self.eligible_products]
        if uuids != sorted(uuids, key=str) or len(uuids) != len(set(uuids)):
            raise ValueError("eligible products must be unique and ordered by UUID")
        expected = content_sha256(self.model_dump(mode="json", exclude={"projection_sha256"}))
        if self.projection_sha256 != expected:
            raise ValueError("catalog projection checksum is stale")
        return self


class PendingVariantFieldEvidence(PacketContract):
    """A source-to-proposal mapping, explicitly not a human-reviewed evidence decision."""

    schema_version: Literal["pvr-canonical-catalog-pending-field-evidence-v1"]
    field: VariantField
    source_field: ApprovedSourceField
    source_value: FieldValue
    proposed_value: FieldValue
    evidence_refs: list[OpaqueId] = Field(min_length=1)
    source_binding: SourceRecordBinding
    mapping_status: Literal["source_to_proposal_mapping_only_pending_owner_review"]
    owner_reviewed: Literal[False]
    authority_approved: Literal[False]
    notes: Literal[
        "Agreement means deterministic source-to-proposal mapping only; it is not owner approval."
    ]

    @model_validator(mode="after")
    def mapping_is_non_inventive(self) -> PendingVariantFieldEvidence:
        expected = {
            ApprovedSourceField.casting_name: VariantField.casting,
            ApprovedSourceField.release_year: VariantField.release_year,
            ApprovedSourceField.series: VariantField.series,
            ApprovedSourceField.collector_number: VariantField.collector_number,
            ApprovedSourceField.series_position: VariantField.series_position,
            ApprovedSourceField.toy_number: VariantField.identifiers,
        }[self.source_field]
        if self.field != expected:
            raise ValueError("pending evidence source field does not map to target field")
        proposed = self.proposed_value
        if self.field == VariantField.identifiers:
            if not isinstance(self.source_value, str) or proposed != [self.source_value]:
                raise ValueError("toy_number must map to a one-item identifiers list")
        elif proposed != self.source_value:
            raise ValueError("pending evidence must reproduce the frozen source value")
        if self.evidence_refs != sorted(set(self.evidence_refs)):
            raise ValueError("pending evidence references must be unique and ordered")
        return self


class CatalogRecordProposalV2(PacketContract):
    schema_version: Literal["pvr-canonical-catalog-record-proposal-v2"]
    proposal_id: OpaqueId
    candidate_id: OpaqueId
    parent_catalog_reference: Literal["data/catalog.json"]
    parent_catalog_version: Literal["fixture-v1"]
    parent_raw_catalog_sha256: Sha256
    parent_projection_sha256: Sha256
    proposed_canonical_uuid: UUID
    proposed_product_record: CanonicalProductRecord
    product_record_sha256: Sha256
    source_decision_ids: list[Literal["fandom-hot-wheels-2025-pilot-r790665-v1"]]
    pending_field_evidence: list[PendingVariantFieldEvidence] = Field(min_length=1)
    review_warnings: list[OpaqueId]
    review_status: Literal["staged"]
    reviewed_by_role: None
    reviewed_at: None
    review_reason: None
    catalog_record_applied: Literal[False]
    authority_approved: Literal[False]

    @model_validator(mode="after")
    def remains_staged_and_hash_bound(self) -> CatalogRecordProposalV2:
        if self.proposed_product_record.canonical_uuid != self.proposed_canonical_uuid:
            raise ValueError("proposal UUID and product UUID differ")
        if self.product_record_sha256 != content_sha256(
            self.proposed_product_record.model_dump(mode="json")
        ):
            raise ValueError("proposal product checksum is stale")
        fields = [row.field for row in self.pending_field_evidence]
        expected = [
            VariantField.casting,
            VariantField.release_year,
            VariantField.series,
            VariantField.collector_number,
            VariantField.series_position,
            VariantField.identifiers,
        ]
        if fields != expected:
            raise ValueError("proposal requires the six supported nonempty field mappings")
        if self.proposed_product_record.color is not None:
            raise ValueError("CAR-T4 cannot infer color")
        if self.proposed_product_record.edition is not None:
            raise ValueError("CAR-T4 cannot infer edition")
        if self.source_decision_ids != [SOURCE_ID]:
            raise ValueError("proposal must use only the approved source decision")
        if self.review_warnings != sorted(set(self.review_warnings)):
            raise ValueError("review warnings must be unique and ordered")
        return self


class CatalogProposalBundle(PacketContract):
    schema_version: Literal["pvr-canonical-catalog-proposal-bundle-v1"]
    bundle_version: Literal["canonical-catalog-proposals-car-t4-v1"]
    publication_scope: Literal["local_only_git_ignored"]
    candidate_plan_sha256: Sha256
    source_decisions_sha256: Sha256
    catalog_projection: FrozenCatalogProjectionV2
    proposals: list[CatalogRecordProposalV2] = Field(min_length=1)
    resolver_output_consulted: Literal[False]
    network_requests: Literal[0]
    catalog_mutated: Literal[False]
    approved_count: Literal[0]
    applied_count: Literal[0]
    authority_approved_count: Literal[0]
    rhb_t5_authorized: Literal[False]

    @model_validator(mode="after")
    def proposals_are_distinct_and_ordered(self) -> CatalogProposalBundle:
        ids = [item.candidate_id for item in self.proposals]
        uuids = [item.proposed_canonical_uuid for item in self.proposals]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("proposals must be unique and ordered by candidate_id")
        if len(uuids) != len(set(uuids)):
            raise ValueError("proposed UUIDs must be unique")
        return self


class CatalogProposalPacketEntry(PacketContract):
    candidate: AuthorityCandidate
    proposal: CatalogRecordProposalV2
    proposal_sha256: Sha256
    variant_note_context: str | None
    variant_note_role: Literal["context_only_not_color_or_edition_evidence"]
    missing_or_conflicting_items: list[OpaqueId] = Field(min_length=1)
    owner_question: NonBlank

    @model_validator(mode="after")
    def entry_is_pending(self) -> CatalogProposalPacketEntry:
        if self.candidate.candidate_id != self.proposal.candidate_id:
            raise ValueError("packet candidate and proposal differ")
        if self.proposal_sha256 != content_sha256(self.proposal.model_dump(mode="json")):
            raise ValueError("packet proposal checksum is stale")
        if self.missing_or_conflicting_items != sorted(set(self.missing_or_conflicting_items)):
            raise ValueError("packet issues must be unique and ordered")
        if self.variant_note_context is not None and not self.variant_note_context:
            raise ValueError("variant-note context cannot be blank")
        return self


class CatalogProposalReviewPacket(PacketContract):
    """CAR-T4 packet for staged catalog proposals; never an authority approval packet."""

    schema_version: Literal["pvr-canonical-catalog-proposal-review-packet-v1"]
    packet_version: Literal["canonical-catalog-proposal-review-car-t4-v1"]
    packet_purpose: Literal[
        "catalog_proposal_review_only_not_authority_review_or_catalog_application"
    ]
    publication_scope: Literal["local_only_git_ignored"]
    candidate_plan_sha256: Sha256
    source_decisions_sha256: Sha256
    raw_catalog_version: Literal["fixture-v1"]
    raw_catalog_sha256: Sha256
    catalog_projection_sha256: Sha256
    entries: list[CatalogProposalPacketEntry] = Field(min_length=1)
    pending_owner_question_count: int = Field(ge=1)
    resolver_output_consulted: Literal[False]
    resolver_output_included: Literal[False]
    predicted_uuid_included: Literal[False]
    model_scores_included: Literal[False]
    network_requests: Literal[0]
    catalog_approved_count: Literal[0]
    catalog_applied_count: Literal[0]
    authority_approved_count: Literal[0]
    rhb_t5_authorized: Literal[False]

    @model_validator(mode="after")
    def entries_are_pending_and_ordered(self) -> CatalogProposalReviewPacket:
        ids = [entry.candidate.candidate_id for entry in self.entries]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("packet entries must be unique and ordered")
        if self.pending_owner_question_count != len(self.entries):
            raise ValueError("packet must contain exactly one pending owner question per entry")
        return self


class BlankCatalogDecision(PacketContract):
    candidate_id: OpaqueId
    proposal_id: OpaqueId
    catalog_decision: Literal["approved", "rejected", "held"] | None
    reviewed_by_role: Literal["project_owner"] | None
    reviewed_at: str | None
    review_reason: str | None


class BlankCatalogDecisionTemplate(PacketContract):
    schema_version: Literal["pvr-canonical-catalog-decision-template-v1"]
    instructions: Literal[
        "Complete each decision independently; catalog approval does not approve authority."
    ]
    packet_sha256: Sha256
    decisions: list[BlankCatalogDecision] = Field(min_length=1)

    @model_validator(mode="after")
    def template_is_blank_and_ordered(self) -> BlankCatalogDecisionTemplate:
        ids = [item.candidate_id for item in self.decisions]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("decision rows must be unique and ordered")
        for item in self.decisions:
            if any(
                value is not None
                for value in (
                    item.catalog_decision,
                    item.reviewed_by_role,
                    item.reviewed_at,
                    item.review_reason,
                )
            ):
                raise ValueError("CAR-T4 decision template must remain blank")
        return self


class CatalogProposalManifest(PacketContract):
    schema_version: Literal["pvr-canonical-catalog-proposal-manifest-v1"]
    manifest_version: Literal["canonical-catalog-proposal-manifest-car-t4-v1"]
    publication_scope: Literal["safe_aggregate_and_hash_metadata_only"]
    local_packet_scope: Literal["local_only_git_ignored"]
    raw_catalog_reference: Literal["data/catalog.json"]
    raw_catalog_version: Literal["fixture-v1"]
    raw_catalog_sha256: Sha256
    raw_product_count: Literal[120]
    raw_uuid_set_sha256: Sha256
    eligibility_policy: Literal["explicit_non_synthetic_exact_only"]
    catalog_projection_sha256: Sha256
    candidate_plan_sha256: Sha256
    source_decisions_sha256: Sha256
    local_proposal_bundle_sha256: Sha256
    local_review_packet_sha256: Sha256
    local_owner_markdown_sha256: Sha256
    local_blank_decision_template_sha256: Sha256
    primary_candidate_count: Literal[20]
    primary_family_count: Literal[7]
    surplus_excluded_count: Literal[9]
    eligible_catalog_product_count: Literal[0]
    excluded_synthetic_product_count: Literal[120]
    existing_eligible_exact_match_count: Literal[0]
    missing_catalog_record_count: Literal[20]
    staged_catalog_proposal_count: Literal[20]
    approved_catalog_proposal_count: Literal[0]
    applied_catalog_proposal_count: Literal[0]
    exact_authority_count: Literal[0]
    resolver_output_consulted: Literal[False]
    resolver_output_included: Literal[False]
    model_output_included: Literal[False]
    network_requests: Literal[0]
    browser_sessions: Literal[0]
    catalog_mutated: Literal[False]
    rhb_t5_authorized: Literal[False]
    next_gate: Literal[
        "separate_owner_review_required_for_each_catalog_proposal_before_catalog_application"
    ]


class WorkspaceArtifacts(PacketContract):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

    projection: FrozenCatalogProjectionV2
    proposal_bundle: CatalogProposalBundle
    review_packet: CatalogProposalReviewPacket
    decision_template: BlankCatalogDecisionTemplate
    owner_markdown: str
    manifest: CatalogProposalManifest


def _reject_preconstructed_extras(value: Any) -> None:
    if isinstance(value, BaseModel):
        unexpected = set(value.__dict__) - set(type(value).model_fields)
        if getattr(value, "__pydantic_extra__", None) or unexpected:
            raise AuthorityContractError("preconstructed contract contains undeclared fields")
        for field_name in type(value).model_fields:
            _reject_preconstructed_extras(getattr(value, field_name))
    elif isinstance(value, Mapping):
        for item in value.values():
            _reject_preconstructed_extras(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_preconstructed_extras(item)


def _fresh[T: BaseModel](model: type[T], value: T | Mapping[str, Any]) -> T:
    _reject_preconstructed_extras(value)
    payload: Any = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return model.model_validate(payload)


def _duplicate_rejecting_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuthorityContractError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_strict_json(path: Path) -> tuple[Any, bytes]:
    if path.is_symlink() or not path.is_file():
        raise AuthorityContractError(f"required artifact is not a regular file: {path.name}")
    raw = path.read_bytes()
    try:
        value = json.loads(raw, object_pairs_hook=_duplicate_rejecting_object)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise AuthorityContractError(f"invalid JSON artifact: {path.name}") from error
    return value, raw


def _raw_sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def build_catalog_projection(root: Path) -> tuple[FrozenCatalogProjectionV2, RawCatalog]:
    """Rebuild the eligibility projection from strict, duplicate-key-safe raw catalog bytes."""

    raw_payload, raw = _read_strict_json(root / CATALOG_REFERENCE)
    catalog = RawCatalog.model_validate(raw_payload)
    raw_sha = _raw_sha256(raw)
    if raw_sha != EXPECTED_RAW_CATALOG_SHA256:
        raise AuthorityContractError("raw catalog checksum differs from the approved CAR-T4 parent")
    if len(catalog.products) != 120:
        raise AuthorityContractError("raw catalog product count differs from 120")
    raw_uuids = sorted(str(item.canonical_uuid) for item in catalog.products)
    synthetic = [item for item in catalog.products if item.is_synthetic_fixture]
    if len(synthetic) != len(catalog.products):
        raise AuthorityContractError(
            "catalog contains a non-synthetic row without an explicit exact-eligibility contract"
        )
    partial: dict[str, Any] = {
        "schema_version": "pvr-canonical-authority-frozen-catalog-projection-v2",
        "raw_catalog_reference": CATALOG_REFERENCE,
        "raw_catalog_version": catalog.catalog_version,
        "raw_catalog_sha256": raw_sha,
        "raw_product_count": len(catalog.products),
        "raw_uuid_set_sha256": content_sha256(raw_uuids),
        "eligibility_policy": "explicit_non_synthetic_exact_only",
        "eligible_products": [],
        "eligible_product_count": 0,
        "excluded_synthetic_product_count": len(synthetic),
        "exclusion_reasons": {"synthetic_fixture": len(synthetic)},
    }
    partial["projection_sha256"] = content_sha256(partial)
    projection = FrozenCatalogProjectionV2.model_validate(partial)
    return projection, catalog


def validate_catalog_projection(
    root: Path, payload: FrozenCatalogProjectionV2 | Mapping[str, Any]
) -> FrozenCatalogProjectionV2:
    supplied = _fresh(FrozenCatalogProjectionV2, payload)
    expected, _ = build_catalog_projection(root)
    if supplied != expected:
        raise AuthorityContractError("catalog projection differs from strict raw-catalog rebuild")
    return supplied


def validate_proposal_bundle(
    root: Path, payload: CatalogProposalBundle | Mapping[str, Any]
) -> CatalogProposalBundle:
    supplied = _fresh(CatalogProposalBundle, payload)
    expected = derive_workspace(root).proposal_bundle
    if supplied != expected:
        raise AuthorityContractError("proposal bundle differs from deterministic CAR-T4 inputs")
    return supplied


def validate_proposal_review_packet(
    root: Path, payload: CatalogProposalReviewPacket | Mapping[str, Any]
) -> CatalogProposalReviewPacket:
    supplied = _fresh(CatalogProposalReviewPacket, payload)
    expected = derive_workspace(root).review_packet
    if supplied != expected:
        raise AuthorityContractError("review packet differs from deterministic CAR-T4 inputs")
    return supplied


def validate_catalog_proposal_manifest(
    root: Path, payload: CatalogProposalManifest | Mapping[str, Any]
) -> CatalogProposalManifest:
    supplied = _fresh(CatalogProposalManifest, payload)
    expected = derive_workspace(root).manifest
    if supplied != expected:
        raise AuthorityContractError("public manifest differs from deterministic CAR-T4 inputs")
    return supplied


def _validate_candidate_plan(root: Path) -> tuple[dict[str, Any], str]:
    raw_payload, raw = _read_strict_json(root / CANDIDATE_PLAN_REFERENCE)
    if not isinstance(raw_payload, dict):
        raise AuthorityContractError("candidate plan must be an object")
    sha = _raw_sha256(raw)
    if sha != CANDIDATE_PLAN_RAW_SHA256:
        raise AuthorityContractError("candidate plan checksum differs from owner-approved CAR-T3")
    if raw_payload.get("approval_status") != "approved":
        raise AuthorityContractError("candidate plan is not owner approved")
    owner_gate = raw_payload.get("owner_gate")
    guardrails = raw_payload.get("guardrails")
    if not isinstance(owner_gate, dict) or not isinstance(guardrails, dict):
        raise AuthorityContractError("candidate plan approval metadata is incomplete")
    if (
        owner_gate.get("decision_status") != "approved"
        or owner_gate.get("reviewer_role") != "project_owner"
        or owner_gate.get("confirmation_method") != "owner_attestation"
        or owner_gate.get("resolver_output_consulted") is not False
        or guardrails.get("exact_authority_rows_created") != 0
        or guardrails.get("rhb_t5_authorized") is not False
    ):
        raise AuthorityContractError("candidate plan owner Gate or guardrails are invalid")
    tasks = (root / TASKS_REFERENCE).read_text(encoding="utf-8")
    if "- [x] Propose at least four multi-release families" not in tasks:
        raise AuthorityContractError("CAR-T3 is not checked in tasks.md")
    return cast(dict[str, Any], raw_payload), sha


def _source_binding(record_id: str) -> dict[str, Any]:
    return {
        "source_id": SOURCE_ID,
        "source_kind": "licensed_community_snapshot",
        "claim_tier": "community_reference_snapshot_exact",
        "source_page_title": "List of 2025 Hot Wheels",
        "source_page_url": (
            "https://hotwheels.fandom.com/wiki/List_of_2025_Hot_Wheels?oldid=790665"
        ),
        "source_revision_id": 790665,
        "source_revision_timestamp": "2026-07-17T05:50:26Z",
        "source_record_id": record_id,
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


def _safe_key(value: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    if not key:
        raise AuthorityContractError("source value cannot produce an empty release key")
    return key


def _proposal_for_candidate(
    *,
    root: Path,
    candidate_plan_row: Mapping[str, Any],
    family: Mapping[str, Any],
    source_row: Mapping[str, FieldValue],
    projection: FrozenCatalogProjectionV2,
    raw_uuid_set: set[UUID],
) -> tuple[AuthorityCandidate, CatalogRecordProposalV2]:
    candidate_id = str(candidate_plan_row["candidate_id"])
    record_id = str(candidate_plan_row["source_record_id"])
    family_key = str(family["family_plan_id"])
    if source_row.get("casting_name") != family.get("source_family_label"):
        raise AuthorityContractError("candidate family label differs from the frozen source row")
    toy_number = source_row.get("toy_number")
    release_year = source_row.get("release_year")
    if not isinstance(toy_number, str) or not isinstance(release_year, int):
        raise AuthorityContractError("candidate source row lacks release identity")
    release_key = f"release-{release_year}-{_safe_key(toy_number)}"
    binding = _source_binding(record_id)
    candidate = validate_authority_candidate(
        {
            "schema_version": "pvr-canonical-authority-candidate-v1",
            "candidate_id": candidate_id,
            "source_binding": binding,
            "family_group_key": family_key,
            "proposed_release_key": release_key,
            "selection_context_refs": [f"candidate-plan:{candidate_id}"],
            "selection_context_role": "candidate_selection_only",
            "catalog_lookup_state": "catalog_review_required",
            "canonical_uuid": None,
            "resolver_output_consulted": False,
            "synthetic": False,
            "status": "staged",
        },
        root=root,
    )
    proposed_uuid = uuid5(
        NAMESPACE_URL,
        f"https://product-variant-resolver.local/catalog-proposal/{SOURCE_ID}/{record_id}",
    )
    if proposed_uuid in raw_uuid_set:
        raise AuthorityContractError("deterministic proposal UUID collides with the raw catalog")
    identifiers = [toy_number]
    product = CanonicalProductRecord.model_validate(
        {
            "canonical_uuid": proposed_uuid,
            "casting": source_row["casting_name"],
            "release_year": release_year,
            "series": source_row["series"],
            "color": None,
            "collector_number": source_row["collector_number"],
            "series_position": source_row["series_position"],
            "edition": None,
            "identifiers": identifiers,
            "family_group_key": family_key,
            "release_key": release_key,
            "synthetic": False,
        }
    )
    fields = [
        (VariantField.casting, ApprovedSourceField.casting_name, source_row["casting_name"]),
        (VariantField.release_year, ApprovedSourceField.release_year, release_year),
        (VariantField.series, ApprovedSourceField.series, source_row["series"]),
        (
            VariantField.collector_number,
            ApprovedSourceField.collector_number,
            source_row["collector_number"],
        ),
        (
            VariantField.series_position,
            ApprovedSourceField.series_position,
            source_row["series_position"],
        ),
        (VariantField.identifiers, ApprovedSourceField.toy_number, toy_number),
    ]
    evidence: list[PendingVariantFieldEvidence] = []
    for target, source_field, source_value in fields:
        proposed_value: FieldValue = (
            identifiers if target == VariantField.identifiers else source_value
        )
        evidence.append(
            PendingVariantFieldEvidence.model_validate(
                {
                    "schema_version": "pvr-canonical-catalog-pending-field-evidence-v1",
                    "field": target.value,
                    "source_field": source_field.value,
                    "source_value": source_value,
                    "proposed_value": proposed_value,
                    "evidence_refs": [f"snapshot:{record_id}:{source_field.value}"],
                    "source_binding": binding,
                    "mapping_status": ("source_to_proposal_mapping_only_pending_owner_review"),
                    "owner_reviewed": False,
                    "authority_approved": False,
                    "notes": (
                        "Agreement means deterministic source-to-proposal mapping only; it is not "
                        "owner approval."
                    ),
                }
            )
        )
    warnings = set(cast(list[str], family.get("review_risks", [])))
    warnings.update({"catalog_record_missing", "color_unverified", "edition_unverified"})
    proposal_payload: dict[str, Any] = {
        "schema_version": "pvr-canonical-catalog-record-proposal-v2",
        "proposal_id": f"car-t4-proposal-{record_id.removeprefix('fandom-row-')}",
        "candidate_id": candidate_id,
        "parent_catalog_reference": CATALOG_REFERENCE,
        "parent_catalog_version": projection.raw_catalog_version,
        "parent_raw_catalog_sha256": projection.raw_catalog_sha256,
        "parent_projection_sha256": projection.projection_sha256,
        "proposed_canonical_uuid": proposed_uuid,
        "proposed_product_record": product.model_dump(mode="json"),
        "product_record_sha256": content_sha256(product.model_dump(mode="json")),
        "source_decision_ids": [SOURCE_ID],
        "pending_field_evidence": [item.model_dump(mode="json") for item in evidence],
        "review_warnings": sorted(warnings),
        "review_status": "staged",
        "reviewed_by_role": None,
        "reviewed_at": None,
        "review_reason": None,
        "catalog_record_applied": False,
        "authority_approved": False,
    }
    return candidate, CatalogRecordProposalV2.model_validate(proposal_payload)


def _owner_markdown(packet: CatalogProposalReviewPacket) -> str:
    lines = [
        "# CAR-T4 local catalog proposal review",
        "",
        "This packet contains 20 staged catalog-record proposals. It is local-only and output-blind.",
        "Approving a catalog record does not approve exact authority. Every proposal needs its own",
        "owner decision and a later separate commit before catalog application.",
        "",
        "Current decisions: **0**. Catalog records applied: **0**. Exact authority rows: **0**.",
        "",
    ]
    for entry in packet.entries:
        product = entry.proposal.proposed_product_record
        evidence_lines: list[str] = []
        for evidence in entry.proposal.pending_field_evidence:
            source_value = json.dumps(evidence.source_value, ensure_ascii=False, sort_keys=True)
            proposed_value = json.dumps(evidence.proposed_value, ensure_ascii=False, sort_keys=True)
            references = ", ".join(f"`{item}`" for item in evidence.evidence_refs)
            evidence_lines.append(
                f"- Pending field `{evidence.field.value}`: source value `{source_value}`; "
                f"proposed value `{proposed_value}`; evidence refs: {references}"
            )
        lines.extend(
            [
                f"## {entry.candidate.candidate_id}",
                "",
                f"- Source row: `{entry.candidate.source_binding.source_record_id}`",
                f"- Proposed casting: `{product.casting}`",
                (
                    f"- Proposed release: `{product.release_year}` / `{product.series}` / "
                    f"`{product.collector_number}` / `{product.series_position}`"
                ),
                f"- Toy identifier: `{', '.join(product.identifiers)}`",
                "- Color: `null` (not inferred)",
                "- Edition: `null` (not inferred)",
                f"- Proposed UUID: `{entry.proposal.proposed_canonical_uuid}`",
                f"- Review warnings: `{', '.join(entry.proposal.review_warnings)}`",
                *evidence_lines,
                (
                    "- Missing/conflicting items: `"
                    + "`, `".join(entry.missing_or_conflicting_items)
                    + "`"
                ),
                *(
                    [
                        (
                            f"- Variant note: `{entry.variant_note_context}` — "
                            f"`{entry.variant_note_role}`"
                        )
                    ]
                    if entry.variant_note_context is not None
                    else []
                ),
                f"- Pending owner question: {entry.owner_question}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def derive_workspace(root: Path) -> WorkspaceArtifacts:
    root = root.resolve()
    context = validate_authority_source_decisions(root)
    normalized_payload, _ = _read_strict_json(root / NORMALIZED_REFERENCE)
    if not isinstance(normalized_payload, dict) or not isinstance(
        normalized_payload.get("records"), list
    ):
        raise AuthorityContractError("normalized snapshot records are unavailable")
    normalized_rows = {
        str(item["source_record_id"]): item
        for item in normalized_payload["records"]
        if isinstance(item, dict) and "source_record_id" in item
    }
    plan, plan_sha = _validate_candidate_plan(root)
    projection, raw_catalog = build_catalog_projection(root)
    raw_uuid_set = {item.canonical_uuid for item in raw_catalog.products}
    primary = cast(dict[str, Any], plan["primary_queue"])
    surplus = cast(dict[str, Any], plan["surplus_queue"])
    if (
        primary.get("candidate_count") != 20
        or primary.get("family_count") != 7
        or surplus.get("candidate_count") != 9
        or surplus.get("included_in_primary_target") is not False
    ):
        raise AuthorityContractError("candidate plan queue counts differ from the owner approval")
    proposals: list[CatalogRecordProposalV2] = []
    packet_entries: list[CatalogProposalPacketEntry] = []
    seen_plan_rows: set[str] = set()
    for family in cast(list[dict[str, Any]], primary["families"]):
        for row in cast(list[dict[str, Any]], family["candidates"]):
            record_id = str(row["source_record_id"])
            candidate_id = str(row["candidate_id"])
            if record_id in seen_plan_rows or candidate_id != f"car-t3-{record_id}":
                raise AuthorityContractError(
                    "candidate plan contains a duplicate or mismatched row"
                )
            seen_plan_rows.add(record_id)
            if record_id not in context.source_records:
                raise AuthorityContractError("candidate is outside the approved source membership")
            normalized_row = normalized_rows.get(record_id)
            if normalized_row is None:
                raise AuthorityContractError("candidate normalized source row is unavailable")
            variant_note = normalized_row.get("variant_note")
            if variant_note is not None and not isinstance(variant_note, str):
                raise AuthorityContractError("candidate variant note is not text")
            candidate, proposal = _proposal_for_candidate(
                root=root,
                candidate_plan_row=row,
                family=family,
                source_row=context.source_records[record_id],
                projection=projection,
                raw_uuid_set=raw_uuid_set,
            )
            proposals.append(proposal)
            packet_entries.append(
                CatalogProposalPacketEntry(
                    candidate=candidate,
                    proposal=proposal,
                    proposal_sha256=content_sha256(proposal.model_dump(mode="json")),
                    variant_note_context=variant_note,
                    variant_note_role="context_only_not_color_or_edition_evidence",
                    missing_or_conflicting_items=[
                        "canonical_catalog_record_missing",
                        "color_unverified",
                        "edition_unverified",
                    ],
                    owner_question=(
                        "Does this frozen source row identify one exact release, and do all six "
                        "source-to-proposal mappings support a new catalog record?"
                    ),
                )
            )
    proposals.sort(key=lambda item: item.candidate_id)
    packet_entries.sort(key=lambda item: item.candidate.candidate_id)
    if len(proposals) != 20:
        raise AuthorityContractError("CAR-T4 must prepare exactly 20 primary proposals")
    proposed_uuids = {item.proposed_canonical_uuid for item in proposals}
    if proposed_uuids & raw_uuid_set:
        raise AuthorityContractError("a proposed UUID collides with the complete raw catalog")
    bundle = CatalogProposalBundle(
        schema_version="pvr-canonical-catalog-proposal-bundle-v1",
        bundle_version="canonical-catalog-proposals-car-t4-v1",
        publication_scope="local_only_git_ignored",
        candidate_plan_sha256=plan_sha,
        source_decisions_sha256=context.source_decisions_sha256,
        catalog_projection=projection,
        proposals=proposals,
        resolver_output_consulted=False,
        network_requests=0,
        catalog_mutated=False,
        approved_count=0,
        applied_count=0,
        authority_approved_count=0,
        rhb_t5_authorized=False,
    )
    packet = CatalogProposalReviewPacket(
        schema_version="pvr-canonical-catalog-proposal-review-packet-v1",
        packet_version="canonical-catalog-proposal-review-car-t4-v1",
        packet_purpose=("catalog_proposal_review_only_not_authority_review_or_catalog_application"),
        publication_scope="local_only_git_ignored",
        candidate_plan_sha256=plan_sha,
        source_decisions_sha256=context.source_decisions_sha256,
        raw_catalog_version=projection.raw_catalog_version,
        raw_catalog_sha256=projection.raw_catalog_sha256,
        catalog_projection_sha256=projection.projection_sha256,
        entries=packet_entries,
        pending_owner_question_count=20,
        resolver_output_consulted=False,
        resolver_output_included=False,
        predicted_uuid_included=False,
        model_scores_included=False,
        network_requests=0,
        catalog_approved_count=0,
        catalog_applied_count=0,
        authority_approved_count=0,
        rhb_t5_authorized=False,
    )
    packet_payload = packet.model_dump(mode="json")
    packet_sha = content_sha256(packet_payload)
    template = BlankCatalogDecisionTemplate(
        schema_version="pvr-canonical-catalog-decision-template-v1",
        instructions=(
            "Complete each decision independently; catalog approval does not approve authority."
        ),
        packet_sha256=packet_sha,
        decisions=[
            BlankCatalogDecision(
                candidate_id=entry.candidate.candidate_id,
                proposal_id=entry.proposal.proposal_id,
                catalog_decision=None,
                reviewed_by_role=None,
                reviewed_at=None,
                review_reason=None,
            )
            for entry in packet.entries
        ],
    )
    markdown = _owner_markdown(packet)
    manifest = CatalogProposalManifest(
        schema_version="pvr-canonical-catalog-proposal-manifest-v1",
        manifest_version="canonical-catalog-proposal-manifest-car-t4-v1",
        publication_scope="safe_aggregate_and_hash_metadata_only",
        local_packet_scope="local_only_git_ignored",
        raw_catalog_reference=CATALOG_REFERENCE,
        raw_catalog_version=projection.raw_catalog_version,
        raw_catalog_sha256=projection.raw_catalog_sha256,
        raw_product_count=projection.raw_product_count,
        raw_uuid_set_sha256=projection.raw_uuid_set_sha256,
        eligibility_policy=projection.eligibility_policy,
        catalog_projection_sha256=projection.projection_sha256,
        candidate_plan_sha256=plan_sha,
        source_decisions_sha256=context.source_decisions_sha256,
        local_proposal_bundle_sha256=content_sha256(bundle.model_dump(mode="json")),
        local_review_packet_sha256=packet_sha,
        local_owner_markdown_sha256=_raw_sha256(markdown.encode("utf-8")),
        local_blank_decision_template_sha256=content_sha256(template.model_dump(mode="json")),
        primary_candidate_count=20,
        primary_family_count=7,
        surplus_excluded_count=9,
        eligible_catalog_product_count=0,
        excluded_synthetic_product_count=120,
        existing_eligible_exact_match_count=0,
        missing_catalog_record_count=20,
        staged_catalog_proposal_count=20,
        approved_catalog_proposal_count=0,
        applied_catalog_proposal_count=0,
        exact_authority_count=0,
        resolver_output_consulted=False,
        resolver_output_included=False,
        model_output_included=False,
        network_requests=0,
        browser_sessions=0,
        catalog_mutated=False,
        rhb_t5_authorized=False,
        next_gate=(
            "separate_owner_review_required_for_each_catalog_proposal_before_catalog_application"
        ),
    )
    return WorkspaceArtifacts(
        projection=projection,
        proposal_bundle=bundle,
        review_packet=packet,
        decision_template=template,
        owner_markdown=markdown,
        manifest=manifest,
    )


def _local_files(artifacts: WorkspaceArtifacts) -> dict[str, bytes]:
    return {
        "catalog-proposals.json": stable_json_bytes(
            artifacts.proposal_bundle.model_dump(mode="json")
        ),
        "catalog-proposal-review-packet.json": stable_json_bytes(
            artifacts.review_packet.model_dump(mode="json")
        ),
        "OWNER-REVIEW.md": artifacts.owner_markdown.encode("utf-8"),
        "catalog-decision-template.json": stable_json_bytes(
            artifacts.decision_template.model_dump(mode="json")
        ),
    }


def _lexical_root(root: Path) -> Path:
    lexical = Path(os.path.abspath(os.fspath(root)))
    try:
        metadata = lexical.lstat()
    except OSError as error:
        raise AuthorityContractError("repository root is unavailable") from error
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
        raise AuthorityContractError("repository root must be a real directory, not a symlink")
    return lexical


def _validate_output_path_chain(root: Path, target: Path, *, allow_missing_leaf: bool) -> None:
    """Reject lexical escapes and every symlink from repository root through the target."""

    root = _lexical_root(root)
    target = Path(os.path.abspath(os.fspath(target)))
    try:
        relative = target.relative_to(root)
    except ValueError as error:
        raise AuthorityContractError("output path escapes the repository root") from error
    if any(part in {"", ".", ".."} for part in relative.parts):
        raise AuthorityContractError("output path has unsafe lexical components")
    current = root
    for index, part in enumerate(relative.parts):
        current = current / part
        is_leaf = index == len(relative.parts) - 1
        try:
            metadata = current.lstat()
        except FileNotFoundError:
            if not (is_leaf and allow_missing_leaf):
                raise AuthorityContractError("output path has a missing ancestor") from None
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise AuthorityContractError("output path contains a symlink ancestor")
    resolved_root = root.resolve(strict=True)
    resolved_parent = target.parent.resolve(strict=True)
    try:
        resolved_parent.relative_to(resolved_root)
    except ValueError as error:
        raise AuthorityContractError("resolved output path escapes the repository root") from error
    if target.exists():
        try:
            target.resolve(strict=True).relative_to(resolved_root)
        except ValueError as error:
            raise AuthorityContractError(
                "resolved output target escapes the repository root"
            ) from error


def _validated_output_dir(root: Path, output_dir: Path | None) -> Path:
    relative = output_dir or (Path(LOCAL_PARENT_REFERENCE) / DEFAULT_LOCAL_NAME)
    if relative.is_absolute():
        raise AuthorityContractError("local output path must be repository-relative")
    expected_parent_parts = Path(LOCAL_PARENT_REFERENCE).parts
    if (
        relative.parts[:-1] != expected_parent_parts
        or len(relative.parts) != len(expected_parent_parts) + 1
        or not re.fullmatch(r"local-[a-z0-9][a-z0-9-]{0,62}", relative.name)
    ):
        raise AuthorityContractError(
            "local output must be a safe direct child of the CAR directory"
        )
    parent = root / LOCAL_PARENT_REFERENCE
    target = root / relative
    _validate_output_path_chain(root, target, allow_missing_leaf=True)
    if not parent.is_dir():
        raise AuthorityContractError("local packet parent must be a real directory")
    ignore_line = f"/{LOCAL_PARENT_REFERENCE}/{target.name}/"
    ignore_path = root / ".gitignore"
    _validate_output_path_chain(root, ignore_path, allow_missing_leaf=False)
    if ignore_line not in ignore_path.read_text(encoding="utf-8").splitlines():
        raise AuthorityContractError("local output directory is not exactly Git-ignored")
    return target


def _matches_directory(path: Path, expected: Mapping[str, bytes]) -> bool:
    if path.is_symlink() or not path.is_dir():
        return False
    actual_names = {item.name for item in path.iterdir()}
    expected_names = set(expected)
    # CAR-T4's base workspace remains immutable after review begins.  Its one recognized private
    # append-only ledger is validated by canonical_catalog_decisions; allowing that exact regular
    # file here keeps the original packet builder's --check useful without accepting arbitrary
    # local drift.
    allowed_names = expected_names | {"catalog-decision-ledger.json"}
    if actual_names not in (expected_names, allowed_names):
        return False
    if "catalog-decision-ledger.json" in actual_names:
        ledger = path / "catalog-decision-ledger.json"
        if ledger.is_symlink() or not ledger.is_file():
            return False
    return all(
        not (path / name).is_symlink()
        and (path / name).is_file()
        and (path / name).read_bytes() == payload
        for name, payload in expected.items()
    )


def _write_staged_directory(parent: Path, expected: Mapping[str, bytes]) -> Path:
    staged = Path(tempfile.mkdtemp(prefix=".car-t4-local-", dir=parent))
    try:
        for name, payload in expected.items():
            target = staged / name
            with target.open("xb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
        directory_fd = os.open(staged, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except Exception:
        shutil.rmtree(staged)
        raise
    return staged


def _write_staged_file(parent: Path, payload: bytes) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=".car-t4-manifest-", dir=parent)
    staged = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        staged.unlink(missing_ok=True)
        raise
    return staged


def publish_workspace(
    root: Path,
    *,
    output_dir: Path | None = None,
    check: bool = False,
) -> Literal["created", "unchanged"]:
    """Create or verify the private workspace and safe public manifest without overwriting drift."""

    root = _lexical_root(root)
    output = _validated_output_dir(root, output_dir)
    manifest_path = root / MANIFEST_REFERENCE
    _validate_output_path_chain(root, manifest_path, allow_missing_leaf=True)
    artifacts = derive_workspace(root)
    local_expected = _local_files(artifacts)
    manifest_expected = stable_json_bytes(artifacts.manifest.model_dump(mode="json"))
    local_exists = output.exists() or output.is_symlink()
    manifest_exists = manifest_path.exists() or manifest_path.is_symlink()
    if local_exists != manifest_exists:
        raise AuthorityContractError(
            "asymmetric partial CAR-T4 publication detected; refusing repair"
        )
    local_matches = local_exists and _matches_directory(output, local_expected)
    manifest_matches = (
        manifest_exists
        and manifest_path.is_file()
        and not manifest_path.is_symlink()
        and manifest_path.read_bytes() == manifest_expected
    )
    if local_exists and not local_matches:
        raise AuthorityContractError("existing local packet drift or partial output detected")
    if manifest_exists and not manifest_matches:
        raise AuthorityContractError("existing public manifest drift detected")
    if check:
        if not local_matches or not manifest_matches:
            raise AuthorityContractError("CAR-T4 workspace is missing; --check never writes")
        return "unchanged"
    if local_matches and manifest_matches:
        return "unchanged"
    staged_dir: Path | None = None
    staged_manifest: Path | None = None
    published_local = False
    published_manifest = False
    try:
        if not local_exists:
            staged_dir = _write_staged_directory(output.parent, local_expected)
        if not manifest_exists:
            staged_manifest = _write_staged_file(manifest_path.parent, manifest_expected)
        if staged_dir is not None:
            os.replace(staged_dir, output)
            staged_dir = None
            published_local = True
        if staged_manifest is not None:
            os.replace(staged_manifest, manifest_path)
            staged_manifest = None
            published_manifest = True
        parent_fd = os.open(output.parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except Exception:
        if published_manifest and not manifest_exists:
            manifest_path.unlink(missing_ok=True)
        if published_local and not manifest_exists and output.is_dir() and not output.is_symlink():
            rollback = Path(tempfile.mkdtemp(prefix=".car-t4-rollback-", dir=output.parent))
            rollback.rmdir()
            os.replace(output, rollback)
            shutil.rmtree(rollback)
        raise
    finally:
        if staged_dir is not None:
            shutil.rmtree(staged_dir, ignore_errors=True)
        if staged_manifest is not None:
            staged_manifest.unlink(missing_ok=True)
    return "created"
