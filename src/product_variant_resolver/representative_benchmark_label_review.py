"""Materialize the owner-authorized, local-only RHB-T6 review workspace.

The builder uses only the frozen query pack, canonical catalog, admitted CAR
authority bundle and governance overlay. It creates evidence and proposals, not
approved labels, and never imports or executes the resolver.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from collections import Counter
from pathlib import Path
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.representative_benchmark import (
    ArtifactDigest,
    CanonicalAuthorityArtifact,
    QueryPack,
    RhbT6GovernanceOverlay,
    SourceDecisionArtifact,
    SourceInventory,
    canonical_record_sha256,
    content_sha256,
    stable_json_bytes,
    validate_canonical_authority,
    validate_source_decisions,
    validate_t1_inventory_files,
)
from product_variant_resolver.representative_benchmark_governance_overlay import (
    OVERLAY_REFERENCE,
    validate_materialized_governance_overlay,
)
from product_variant_resolver.representative_benchmark_governance_repair import (
    AUTHORITY_REFERENCE,
    INVENTORY_MANIFEST_REFERENCE,
    INVENTORY_REFERENCE,
    SOURCE_DECISIONS_REFERENCE,
    WIKI_SOURCE_REFERENCE,
)
from product_variant_resolver.representative_benchmark_query_authoring import (
    PRIVATE_AUTHORING_DIRECTORY,
    QUERY_PACK_REFERENCE,
    validate_materialized_query_pack,
)

RHB_DIRECTORY = Path("data/evaluation/representative-hard-benchmark-v1")
CATALOG_REFERENCE = Path("data/catalog.json")
AUTHORIZATION_REFERENCE = PRIVATE_AUTHORING_DIRECTORY / "rhb-t6-owner-authorization.json"
WORKSPACE_REFERENCE = PRIVATE_AUTHORING_DIRECTORY / "rhb-t6-label-review-v1"
EVIDENCE_REFERENCE = WORKSPACE_REFERENCE / "evidence-packets.json"
PROPOSALS_REFERENCE = WORKSPACE_REFERENCE / "staged-label-proposals.json"
MANIFEST_REFERENCE = RHB_DIRECTORY / "rhb-t6-label-review-manifest-v1.json"

OWNER_RESPONSE_SHA256 = "750df65ed78bc1ef5784c9c504fd3f8860aed9f8e5d9bdce62e4630297d18781"
QUERY_PACK_SHA256 = "97f7f0dd61cf619bb16b198778356d8ef53c7a504086f11542922f90706a858a"
OVERLAY_SHA256 = "7f3a87ea250f38245ba4ba376290c370f0ccc9d96fffadc9bf7f8c479da67cbe"
AUTHORITY_SHA256 = "72c11aeb8db03267a8deca4f50eb09d89c2c423a7e9ca983f498f76e80553117"

ALLOWED_ACTIONS = [
    "create_local_review_workspace",
    "create_evidence_packets",
    "create_staged_label_proposals",
]
PROHIBITED_ACTIONS = [
    "read_historical_human_labels",
    "read_historical_failure_categories",
    "read_resolver_output",
    "read_or_assign_split",
    "preapprove_any_label",
    "publish_row_level_query_or_label_data",
    "RHB-T7_split_assignment",
    "resolver_or_reranker_evaluation",
    "scoring",
]
FOREIGN_BRAND_MARKERS = ("m2 machines", "matchbox", "racing champions")
GENERIC_SURFACES = {"car", "cars", "hot wheels", "diecast", "die cast"}

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
NonBlank = Annotated[str, Field(min_length=1)]


class LabelReviewError(ValueError):
    """Raised when the label-review inputs, authorization or outputs are unsafe."""


class StrictReviewModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LabelReviewAuthorization(StrictReviewModel):
    schema_version: Literal["pvr-rhb-t6-label-review-owner-authorization-v1"]
    gate: Literal["RHB-T6-LABEL-REVIEW"]
    authorized_by: Literal["project_owner"]
    authorization_date: Literal["2026-10-05"]
    authorization_text: NonBlank
    authorization_text_sha256: Sha256
    query_pack_sha256: Literal["97f7f0dd61cf619bb16b198778356d8ef53c7a504086f11542922f90706a858a"]
    governance_overlay_sha256: Literal[
        "7f3a87ea250f38245ba4ba376290c370f0ccc9d96fffadc9bf7f8c479da67cbe"
    ]
    authority_sha256: Literal["72c11aeb8db03267a8deca4f50eb09d89c2c423a7e9ca983f498f76e80553117"]
    allowed_actions: list[NonBlank]
    prohibited_actions: list[NonBlank]
    per_record_owner_review_required: Literal[True]
    quota_forcing_prohibited: Literal[True]
    rhb_t7_authorized: Literal[False]
    resolver_evaluation_authorized: Literal[False]
    authorization_sha256: Sha256

    @model_validator(mode="after")
    def authorization_is_exact_and_non_approving(self) -> LabelReviewAuthorization:
        actual_text_sha256 = hashlib.sha256(self.authorization_text.encode()).hexdigest()
        if actual_text_sha256 != OWNER_RESPONSE_SHA256:
            raise ValueError("RHB-T6 owner response is generic or mismatched")
        if self.authorization_text_sha256 != OWNER_RESPONSE_SHA256:
            raise ValueError("RHB-T6 owner-response checksum changed")
        if self.allowed_actions != ALLOWED_ACTIONS:
            raise ValueError("RHB-T6 allowed actions changed")
        if self.prohibited_actions != PROHIBITED_ACTIONS:
            raise ValueError("RHB-T6 prohibited actions changed")
        expected = content_sha256(self.model_dump(mode="json", exclude={"authorization_sha256"}))
        if self.authorization_sha256 != expected:
            raise ValueError("RHB-T6 authorization checksum is stale")
        return self


MatchEvidence = Literal[
    "alias_exact_surface",
    "casting_exact_surface",
    "release_year_surface",
    "series_exact_surface",
    "toy_identifier_exact",
]


class CatalogEvidenceCandidate(StrictReviewModel):
    canonical_uuid: UUID
    catalog_version: Literal["catalog-v2"]
    catalog_record_sha256: Sha256
    casting: NonBlank
    release_year: int
    series: NonBlank
    collector_number: str | None
    series_position: str | None
    identifiers: list[NonBlank]
    authority_admitted: bool
    authority_id: str | None
    authority_verified_fields: list[NonBlank]
    match_evidence: list[MatchEvidence] = Field(min_length=1)

    @model_validator(mode="after")
    def authority_fields_are_coherent(self) -> CatalogEvidenceCandidate:
        if self.authority_admitted != (self.authority_id is not None):
            raise ValueError("candidate authority flag and ID disagree")
        if not self.authority_admitted and self.authority_verified_fields:
            raise ValueError("non-authority candidate cannot claim verified fields")
        if self.match_evidence != sorted(set(self.match_evidence)):
            raise ValueError("candidate evidence must be unique and ordered")
        return self


class ReviewEvidencePacket(StrictReviewModel):
    case_id: NonBlank
    query: NonBlank
    source_id: Literal["human-labeled-real-noisy-v1"]
    source_record_ref: NonBlank
    family_group_key: NonBlank
    evidence_event_group_key: NonBlank
    provisional_challenge_tags: list[NonBlank]
    catalog_candidates: list[CatalogEvidenceCandidate]
    catalog_candidate_count: int = Field(ge=0)
    admitted_authority_candidate_count: int = Field(ge=0)
    candidate_order: Literal["canonical_uuid_ascending_not_ranked"]
    resolver_output_consulted: Literal[False]
    historical_labels_consulted: Literal[False]
    historical_failure_categories_consulted: Literal[False]
    split_consulted: Literal[False]
    owner_review_required: Literal[True]

    @model_validator(mode="after")
    def evidence_counts_are_recomputable(self) -> ReviewEvidencePacket:
        if self.catalog_candidate_count != len(self.catalog_candidates):
            raise ValueError("catalog candidate count is inconsistent")
        admitted = sum(candidate.authority_admitted for candidate in self.catalog_candidates)
        if self.admitted_authority_candidate_count != admitted:
            raise ValueError("authority candidate count is inconsistent")
        uuids = [str(candidate.canonical_uuid) for candidate in self.catalog_candidates]
        if uuids != sorted(set(uuids)):
            raise ValueError("catalog candidates must use stable UUID ordering")
        return self


class EvidencePacketFile(StrictReviewModel):
    schema_version: Literal["pvr-rhb-t6-review-evidence-v1"]
    dataset_version: Literal["representative-hard-benchmark-rhb-t6-review-v1"]
    publication_scope: Literal["local_only"]
    prepared_date: Literal["2026-10-05"]
    prepared_by: Literal["deterministic_catalog_evidence_builder"]
    query_pack_sha256: Literal["97f7f0dd61cf619bb16b198778356d8ef53c7a504086f11542922f90706a858a"]
    governance_overlay_sha256: Literal[
        "7f3a87ea250f38245ba4ba376290c370f0ccc9d96fffadc9bf7f8c479da67cbe"
    ]
    authority_sha256: Literal["72c11aeb8db03267a8deca4f50eb09d89c2c423a7e9ca983f498f76e80553117"]
    candidate_generation_policy: Literal[
        "exact_catalog_surface_or_toy_identifier_evidence_without_resolver_ranking"
    ]
    packets: list[ReviewEvidencePacket] = Field(min_length=60, max_length=60)
    evidence_sha256: Sha256

    @model_validator(mode="after")
    def packet_file_is_ordered_and_hash_bound(self) -> EvidencePacketFile:
        case_ids = [packet.case_id for packet in self.packets]
        if case_ids != sorted(set(case_ids)):
            raise ValueError("evidence packets must have 60 unique ordered case IDs")
        expected = content_sha256(self.model_dump(mode="json", exclude={"evidence_sha256"}))
        if self.evidence_sha256 != expected:
            raise ValueError("evidence packet checksum is stale")
        return self


ProposalStatus = Literal["matched", "ambiguous", "no_match"] | None
ProposalBasis = Literal[
    "catalog_surface_without_unique_admitted_authority",
    "explicit_out_of_scope_brand_without_catalog_candidate",
    "insufficient_evidence_hold",
    "unique_admitted_identifier_and_surface",
]


class StagedLabelProposal(StrictReviewModel):
    case_id: NonBlank
    stage: Literal["staged_pending_owner_review"]
    suggested_expected_status: ProposalStatus
    suggested_canonical_uuid: UUID | None
    suggested_authority_id: str | None
    suggested_family_label: str | None
    proposal_basis: ProposalBasis
    failure_type_suggestion: None
    hard_negative_suggestion: None
    verified_challenge_tags: list[NonBlank] = Field(max_length=0)
    challenge_review_status: Literal["pending_owner_review"]
    owner_decision_recorded: Literal[False]
    score_eligible: Literal[False]

    @model_validator(mode="after")
    def staged_proposal_never_pretends_to_be_approved(self) -> StagedLabelProposal:
        has_identity = (
            self.suggested_canonical_uuid is not None or self.suggested_authority_id is not None
        )
        if self.suggested_expected_status == "matched":
            if (
                self.suggested_canonical_uuid is None
                or self.suggested_authority_id is None
                or self.proposal_basis != "unique_admitted_identifier_and_surface"
            ):
                raise ValueError("matched proposal requires one admitted authority identity")
        elif has_identity:
            raise ValueError("non-matched proposal cannot carry canonical identity")
        if (
            self.suggested_expected_status is None
            and self.proposal_basis != "insufficient_evidence_hold"
        ):
            raise ValueError("empty status must remain held for insufficient evidence")
        return self


class StagedProposalFile(StrictReviewModel):
    schema_version: Literal["pvr-rhb-t6-staged-label-proposals-v1"]
    dataset_version: Literal["representative-hard-benchmark-rhb-t6-review-v1"]
    publication_scope: Literal["local_only"]
    prepared_date: Literal["2026-10-05"]
    authorization_sha256: Sha256
    evidence_sha256: Sha256
    labels_preapproved: Literal[False]
    quota_forcing_prohibited: Literal[True]
    proposals: list[StagedLabelProposal] = Field(min_length=60, max_length=60)
    proposals_sha256: Sha256

    @model_validator(mode="after")
    def proposals_are_ordered_and_hash_bound(self) -> StagedProposalFile:
        case_ids = [proposal.case_id for proposal in self.proposals]
        if case_ids != sorted(set(case_ids)):
            raise ValueError("staged proposals must have 60 unique ordered case IDs")
        if any(proposal.owner_decision_recorded for proposal in self.proposals):
            raise ValueError("staging cannot contain owner decisions")
        expected = content_sha256(self.model_dump(mode="json", exclude={"proposals_sha256"}))
        if self.proposals_sha256 != expected:
            raise ValueError("staged proposal checksum is stale")
        return self


class LabelReviewManifest(StrictReviewModel):
    schema_version: Literal["pvr-rhb-t6-label-review-manifest-v1"]
    review_version: Literal["representative-hard-benchmark-rhb-t6-review-v1"]
    prepared_date: Literal["2026-10-05"]
    status: Literal["staged_awaiting_owner_review"]
    generated_by: Literal["scripts/build_representative_hard_benchmark_label_review.py"]
    publication_scope: Literal["aggregate_only"]
    authorization_sha256: Sha256
    input_artifacts: list[ArtifactDigest] = Field(min_length=4, max_length=4)
    evidence_packet_sha256: Sha256
    staged_proposals_sha256: Sha256
    record_count: Literal[60]
    suggested_status_counts: dict[str, int]
    owner_approved_label_count: Literal[0]
    held_pending_owner_count: int = Field(ge=0, le=60)
    labels_materialized: Literal[False]
    row_level_data_public: Literal[False]
    historical_labels_consulted: Literal[False]
    resolver_output_consulted: Literal[False]
    split_consulted: Literal[False]
    rhb_t7_authorized: Literal[False]
    resolver_evaluation_authorized: Literal[False]
    next_allowed_action: Literal["present_staged_proposals_to_owner_in_batches"]
    manifest_sha256: Sha256

    @model_validator(mode="after")
    def manifest_is_safe_and_recomputable(self) -> LabelReviewManifest:
        paths = [item.path for item in self.input_artifacts]
        if paths != sorted(set(paths)):
            raise ValueError("manifest inputs must be unique and ordered")
        required_counts = {"ambiguous", "held", "matched", "no_match"}
        if set(self.suggested_status_counts) != required_counts:
            raise ValueError("manifest status-count keys changed")
        if sum(self.suggested_status_counts.values()) != self.record_count:
            raise ValueError("manifest status counts do not cover 60 rows")
        if self.held_pending_owner_count != self.suggested_status_counts["held"]:
            raise ValueError("held count is inconsistent")
        expected = content_sha256(self.model_dump(mode="json", exclude={"manifest_sha256"}))
        if self.manifest_sha256 != expected:
            raise ValueError("label-review manifest checksum is stale")
        return self


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise LabelReviewError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise LabelReviewError(f"{path}: could not read strict JSON") from error
    if not isinstance(value, dict):
        raise LabelReviewError(f"{path}: JSON root must be an object")
    return value


def _raw_sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise LabelReviewError(f"{path}: could not compute SHA-256") from error


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise LabelReviewError(message)


def _validate_authorization(root: Path) -> LabelReviewAuthorization:
    private_directory = root / PRIVATE_AUTHORING_DIRECTORY
    authorization_path = root / AUTHORIZATION_REFERENCE
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
        "RHB-T6 authorization must remain a real 0600 file",
    )
    return LabelReviewAuthorization.model_validate(_load_object(authorization_path))


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def _contains_surface(normalized_query: str, surface: str) -> bool:
    normalized_surface = _normalize(surface)
    return (
        normalized_surface not in GENERIC_SURFACES
        and len(normalized_surface) >= 4
        and f" {normalized_surface} " in f" {normalized_query} "
    )


def _identifier_values(product: dict[str, Any]) -> list[str]:
    raw_identifiers = product.get("identifiers", [])
    if not isinstance(raw_identifiers, list):
        return []
    values = [
        str(item.get("identifier_value"))
        for item in raw_identifiers
        if isinstance(item, dict) and item.get("identifier_value")
    ]
    return sorted(set(values))


def _toy_identifier_matches(normalized_query: str, values: list[str]) -> list[str]:
    matches: list[str] = []
    for value in values:
        normalized = _normalize(value)
        if (
            len(normalized) >= 4
            and re.search(r"[a-z]", normalized)
            and (f" {normalized} " in f" {normalized_query} ")
        ):
            matches.append(value)
    return matches


def _candidate_for_product(
    query: str,
    product: dict[str, Any],
    authority_by_uuid: dict[str, Any],
) -> CatalogEvidenceCandidate | None:
    normalized_query = _normalize(query)
    casting = str(product.get("casting", ""))
    aliases = [str(value) for value in product.get("aliases", []) if str(value).strip()]
    casting_match = _contains_surface(normalized_query, casting)
    alias_match = any(_contains_surface(normalized_query, alias) for alias in aliases)
    identifiers = _identifier_values(product)
    identifier_match = _toy_identifier_matches(normalized_query, identifiers)
    if not casting_match and not alias_match and not identifier_match:
        return None
    evidence: set[MatchEvidence] = set()
    if casting_match:
        evidence.add("casting_exact_surface")
    if alias_match:
        evidence.add("alias_exact_surface")
    if identifier_match:
        evidence.add("toy_identifier_exact")
    release_year = int(product["release_year"])
    if str(release_year) in re.findall(r"\b(?:19|20)\d{2}\b", query):
        evidence.add("release_year_surface")
    series = str(product.get("series", ""))
    if series and _contains_surface(normalized_query, series):
        evidence.add("series_exact_surface")
    canonical_uuid = str(product["canonical_uuid"])
    authority = authority_by_uuid.get(canonical_uuid)
    return CatalogEvidenceCandidate(
        canonical_uuid=UUID(canonical_uuid),
        catalog_version="catalog-v2",
        catalog_record_sha256=canonical_record_sha256(product),
        casting=casting,
        release_year=release_year,
        series=series,
        collector_number=(
            str(product["collector_number"])
            if product.get("collector_number") is not None
            else None
        ),
        series_position=(
            str(product["series_position"]) if product.get("series_position") is not None else None
        ),
        identifiers=identifiers,
        authority_admitted=authority is not None,
        authority_id=(str(authority.authority_id) if authority is not None else None),
        authority_verified_fields=(
            sorted(field.value for field in authority.variant_fields_verified)
            if authority is not None
            else []
        ),
        match_evidence=sorted(evidence),
    )


def _evidence_packet(
    case: Any,
    products: list[dict[str, Any]],
    authority_by_uuid: dict[str, Any],
) -> ReviewEvidencePacket:
    candidates = [
        candidate
        for product in products
        if (candidate := _candidate_for_product(case.query, product, authority_by_uuid)) is not None
    ]
    candidates.sort(key=lambda item: str(item.canonical_uuid))
    return ReviewEvidencePacket(
        case_id=case.case_id,
        query=case.query,
        source_id=case.source_id,
        source_record_ref=case.source_record_ref,
        family_group_key=case.family_group_key,
        evidence_event_group_key=case.evidence_event_group_key,
        provisional_challenge_tags=sorted(tag.value for tag in case.challenge_tags),
        catalog_candidates=candidates,
        catalog_candidate_count=len(candidates),
        admitted_authority_candidate_count=sum(
            candidate.authority_admitted for candidate in candidates
        ),
        candidate_order="canonical_uuid_ascending_not_ranked",
        resolver_output_consulted=False,
        historical_labels_consulted=False,
        historical_failure_categories_consulted=False,
        split_consulted=False,
        owner_review_required=True,
    )


def _staged_proposal(packet: ReviewEvidencePacket) -> StagedLabelProposal:
    direct_authority = [
        candidate
        for candidate in packet.catalog_candidates
        if candidate.authority_admitted
        and "toy_identifier_exact" in candidate.match_evidence
        and (
            "casting_exact_surface" in candidate.match_evidence
            or "alias_exact_surface" in candidate.match_evidence
        )
    ]
    if len(direct_authority) == 1:
        candidate = direct_authority[0]
        status: ProposalStatus = "matched"
        basis: ProposalBasis = "unique_admitted_identifier_and_surface"
        canonical_uuid: UUID | None = candidate.canonical_uuid
        authority_id = candidate.authority_id
    elif packet.catalog_candidates:
        status = "ambiguous"
        basis = "catalog_surface_without_unique_admitted_authority"
        canonical_uuid = None
        authority_id = None
    else:
        normalized_query = _normalize(packet.query)
        explicit_foreign_brand = any(marker in normalized_query for marker in FOREIGN_BRAND_MARKERS)
        if explicit_foreign_brand and "hot wheels" not in normalized_query:
            status = "no_match"
            basis = "explicit_out_of_scope_brand_without_catalog_candidate"
        else:
            status = None
            basis = "insufficient_evidence_hold"
        canonical_uuid = None
        authority_id = None
    castings = sorted({candidate.casting for candidate in packet.catalog_candidates})
    family_label = castings[0] if len(castings) == 1 else None
    return StagedLabelProposal(
        case_id=packet.case_id,
        stage="staged_pending_owner_review",
        suggested_expected_status=status,
        suggested_canonical_uuid=canonical_uuid,
        suggested_authority_id=authority_id,
        suggested_family_label=family_label,
        proposal_basis=basis,
        failure_type_suggestion=None,
        hard_negative_suggestion=None,
        verified_challenge_tags=[],
        challenge_review_status="pending_owner_review",
        owner_decision_recorded=False,
        score_eligible=False,
    )


def _validated_inputs(
    root: Path,
) -> tuple[
    LabelReviewAuthorization,
    QueryPack,
    RhbT6GovernanceOverlay,
    CanonicalAuthorityArtifact,
    SourceInventory,
    SourceDecisionArtifact,
    dict[str, Any],
]:
    authorization = _validate_authorization(root)
    query_pack, query_manifest = validate_materialized_query_pack(root)
    overlay = validate_materialized_governance_overlay(root)
    _expect(query_manifest.sha256 == authorization.query_pack_sha256, "query pack binding drift")
    _expect(
        overlay.overlay_sha256 == authorization.governance_overlay_sha256, "overlay binding drift"
    )

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
    catalog_payload = _load_object(root / CATALOG_REFERENCE)
    authority_payload = _load_object(root / AUTHORITY_REFERENCE)
    authority = validate_canonical_authority(
        authority_payload,
        inventory=inventory,
        catalog_payload=catalog_payload,
        source_decisions=decisions,
        governance_overlay=overlay,
    )
    _expect(
        content_sha256(authority.model_dump(mode="json")) == authorization.authority_sha256,
        "authority binding drift",
    )
    products = catalog_payload.get("products")
    _expect(
        catalog_payload.get("catalog_version") == "catalog-v2"
        and isinstance(products, list)
        and len(products) == 140
        and all(isinstance(product, dict) for product in products),
        "RHB-T6 review requires the complete 140-row catalog-v2",
    )
    return authorization, query_pack, overlay, authority, inventory, decisions, catalog_payload


def build_label_review_artifacts(
    root: Path,
) -> tuple[EvidencePacketFile, StagedProposalFile, LabelReviewManifest]:
    """Build evidence, non-approved proposals and a public-safe aggregate manifest."""

    root = root.absolute()
    authorization, query_pack, overlay, authority, _inventory, _decisions, catalog_payload = (
        _validated_inputs(root)
    )
    products = [product for product in catalog_payload["products"] if isinstance(product, dict)]
    authority_by_uuid = {str(record.canonical_uuid): record for record in authority.records}
    packets = [_evidence_packet(case, products, authority_by_uuid) for case in query_pack.cases]
    evidence_body: dict[str, Any] = {
        "schema_version": "pvr-rhb-t6-review-evidence-v1",
        "dataset_version": "representative-hard-benchmark-rhb-t6-review-v1",
        "publication_scope": "local_only",
        "prepared_date": "2026-10-05",
        "prepared_by": "deterministic_catalog_evidence_builder",
        "query_pack_sha256": authorization.query_pack_sha256,
        "governance_overlay_sha256": overlay.overlay_sha256,
        "authority_sha256": authorization.authority_sha256,
        "candidate_generation_policy": (
            "exact_catalog_surface_or_toy_identifier_evidence_without_resolver_ranking"
        ),
        "packets": [packet.model_dump(mode="json") for packet in packets],
    }
    evidence = EvidencePacketFile.model_validate(
        {**evidence_body, "evidence_sha256": content_sha256(evidence_body)}
    )

    proposals = [_staged_proposal(packet) for packet in evidence.packets]
    proposals_body: dict[str, Any] = {
        "schema_version": "pvr-rhb-t6-staged-label-proposals-v1",
        "dataset_version": "representative-hard-benchmark-rhb-t6-review-v1",
        "publication_scope": "local_only",
        "prepared_date": "2026-10-05",
        "authorization_sha256": authorization.authorization_sha256,
        "evidence_sha256": evidence.evidence_sha256,
        "labels_preapproved": False,
        "quota_forcing_prohibited": True,
        "proposals": [proposal.model_dump(mode="json") for proposal in proposals],
    }
    proposal_file = StagedProposalFile.model_validate(
        {**proposals_body, "proposals_sha256": content_sha256(proposals_body)}
    )

    counts: Counter[str] = Counter(
        proposal.suggested_expected_status or "held" for proposal in proposal_file.proposals
    )
    input_references = (
        AUTHORITY_REFERENCE,
        CATALOG_REFERENCE,
        OVERLAY_REFERENCE,
        QUERY_PACK_REFERENCE,
    )
    manifest_body: dict[str, Any] = {
        "schema_version": "pvr-rhb-t6-label-review-manifest-v1",
        "review_version": "representative-hard-benchmark-rhb-t6-review-v1",
        "prepared_date": "2026-10-05",
        "status": "staged_awaiting_owner_review",
        "generated_by": "scripts/build_representative_hard_benchmark_label_review.py",
        "publication_scope": "aggregate_only",
        "authorization_sha256": authorization.authorization_sha256,
        "input_artifacts": [
            {"path": reference.as_posix(), "sha256": _raw_sha256(root / reference)}
            for reference in sorted(input_references, key=lambda item: item.as_posix())
        ],
        "evidence_packet_sha256": evidence.evidence_sha256,
        "staged_proposals_sha256": proposal_file.proposals_sha256,
        "record_count": 60,
        "suggested_status_counts": {
            status: counts.get(status, 0) for status in ("ambiguous", "held", "matched", "no_match")
        },
        "owner_approved_label_count": 0,
        "held_pending_owner_count": counts.get("held", 0),
        "labels_materialized": False,
        "row_level_data_public": False,
        "historical_labels_consulted": False,
        "resolver_output_consulted": False,
        "split_consulted": False,
        "rhb_t7_authorized": False,
        "resolver_evaluation_authorized": False,
        "next_allowed_action": "present_staged_proposals_to_owner_in_batches",
    }
    manifest = LabelReviewManifest.model_validate(
        {**manifest_body, "manifest_sha256": content_sha256(manifest_body)}
    )
    return evidence, proposal_file, manifest


def _validate_file(path: Path, expected: BaseModel, mode: int) -> None:
    _expect(path.is_file() and not path.is_symlink(), f"{path}: output is absent or unsafe")
    _expect(stat.S_IMODE(path.stat().st_mode) == mode, f"{path}: unexpected file mode")
    _expect(
        path.read_bytes() == stable_json_bytes(expected.model_dump(mode="json")),
        f"{path}: output is stale or non-canonical",
    )


def validate_materialized_label_review(
    root: Path,
) -> tuple[EvidencePacketFile, StagedProposalFile, LabelReviewManifest]:
    """Validate all private/public staging artifacts against the current parents."""

    root = root.absolute()
    evidence, proposals, manifest = build_label_review_artifacts(root)
    workspace = root / WORKSPACE_REFERENCE
    _expect(
        workspace.is_dir()
        and not workspace.is_symlink()
        and stat.S_IMODE(workspace.stat().st_mode) == 0o700,
        "RHB-T6 review workspace must remain a real 0700 directory",
    )
    _validate_file(root / EVIDENCE_REFERENCE, evidence, 0o600)
    _validate_file(root / PROPOSALS_REFERENCE, proposals, 0o600)
    _validate_file(root / MANIFEST_REFERENCE, manifest, 0o644)
    return evidence, proposals, manifest


def _atomic_write(path: Path, payload: bytes, mode: int) -> None:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, mode)
        os.replace(temp, path)
        os.chmod(path, mode)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise


def materialize_label_review(root: Path, *, check: bool = False) -> Literal["created", "unchanged"]:
    """Create or validate local-only staging without approving any label."""

    root = root.absolute()
    evidence, proposals, manifest = build_label_review_artifacts(root)
    targets = {
        root / EVIDENCE_REFERENCE: (evidence, 0o600),
        root / PROPOSALS_REFERENCE: (proposals, 0o600),
        root / MANIFEST_REFERENCE: (manifest, 0o644),
    }
    existence = {path: path.exists() for path in targets}
    if all(existence.values()):
        validate_materialized_label_review(root)
        return "unchanged"
    if any(existence.values()):
        raise LabelReviewError("RHB-T6 review outputs are partial; refusing overwrite")
    if check:
        raise LabelReviewError("RHB-T6 review workspace is not materialized")

    workspace = root / WORKSPACE_REFERENCE
    workspace.mkdir(parents=False, exist_ok=False, mode=0o700)
    os.chmod(workspace, 0o700)
    created: list[Path] = []
    try:
        for path, (artifact, mode) in targets.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(path, stable_json_bytes(artifact.model_dump(mode="json")), mode)
            created.append(path)
        validate_materialized_label_review(root)
    except BaseException:
        for path in created:
            path.unlink(missing_ok=True)
        try:
            workspace.rmdir()
        except OSError:
            pass
        raise
    return "created"


__all__ = [
    "AUTHORIZATION_REFERENCE",
    "EVIDENCE_REFERENCE",
    "MANIFEST_REFERENCE",
    "PROPOSALS_REFERENCE",
    "WORKSPACE_REFERENCE",
    "EvidencePacketFile",
    "LabelReviewAuthorization",
    "LabelReviewError",
    "LabelReviewManifest",
    "StagedProposalFile",
    "build_label_review_artifacts",
    "materialize_label_review",
    "validate_materialized_label_review",
]
