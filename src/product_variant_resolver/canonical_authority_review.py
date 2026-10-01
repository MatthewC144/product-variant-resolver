"""Strict, offline contracts for Canonical Authority Review v1.

The module is deliberately isolated from FastAPI and the resolver runtime.  It accepts only
explicit, versioned artifacts, re-validates the CAR-T1 source Gate, and fails closed whenever a
candidate, review event, or bundle could manufacture canonical truth.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, cast
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from product_variant_resolver.canonical_authority_source_gate import (
    DECISIONS_PATH,
    NORMALIZED_PATH,
    load_json,
    validate_source_gate_paths,
)

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
NonBlank = Annotated[str, Field(min_length=1)]
OpaqueId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:#-]{0,199}$")]
FieldValue = str | int | list[str] | None

EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d ().-]{7,}\d)(?!\d)")
URL_RE = re.compile(r"\b[a-z][a-z0-9+.-]*://\S+", re.IGNORECASE)
CREDENTIAL_RE = re.compile(
    r"\b(?:password|passwd|api[_ -]?key|access[_ -]?token|bearer[_ -]?token|"
    r"client[_ -]?secret|private[_ -]?key|secret)\b\s*(?::|=|#)?\s*\S+",
    re.IGNORECASE,
)
ACCOUNT_RE = re.compile(
    r"\b(?:seller|account|username|user[_ -]?id)\b\s*(?::|=|#)?\s*\S+",
    re.IGNORECASE,
)
ADDRESS_RE = re.compile(
    r"\b\d{1,6}[A-Za-z]?\s+[A-Za-z0-9.' -]{2,}\s+"
    r"(?:street|st|avenue|ave|road|rd|boulevard|blvd|lane|ln|drive|dr|court|ct|"
    r"loop|way|place|pl|parkway|pkwy|circle|cir|terrace|ter)\b",
    re.IGNORECASE,
)


class AuthorityContractError(ValueError):
    """Raised when separate CAR artifacts disagree or violate a Gate."""


class StrictContract(BaseModel):
    """Base contract: undeclared fields are rejected and strings are normalized."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class CandidateStatus(str, Enum):
    staged = "staged"
    held = "held"


class ReviewStatus(str, Enum):
    staged = "staged"
    reviewed = "reviewed"
    approved_exact = "approved_exact"
    conflicted = "conflicted"
    insufficient = "insufficient"
    held = "held"
    revoked = "revoked"


class CatalogLookupState(str, Enum):
    existing_uuid = "existing_uuid"
    catalog_review_required = "catalog_review_required"


class EvidenceAgreement(str, Enum):
    agrees = "agrees"
    conflicts = "conflicts"
    insufficient = "insufficient"


class VariantField(str, Enum):
    casting = "casting"
    release_year = "release_year"
    series = "series"
    color = "color"
    collector_number = "collector_number"
    series_position = "series_position"
    edition = "edition"
    identifiers = "identifiers"


class ApprovedSourceField(str, Enum):
    casting_name = "casting_name"
    release_year = "release_year"
    series = "series"
    collector_number = "collector_number"
    series_position = "series_position"
    toy_number = "toy_number"


SOURCE_TO_VARIANT_FIELD: Mapping[ApprovedSourceField, VariantField] = {
    ApprovedSourceField.casting_name: VariantField.casting,
    ApprovedSourceField.release_year: VariantField.release_year,
    ApprovedSourceField.series: VariantField.series,
    ApprovedSourceField.collector_number: VariantField.collector_number,
    ApprovedSourceField.series_position: VariantField.series_position,
    ApprovedSourceField.toy_number: VariantField.identifiers,
}


class SourceRecordBinding(StrictContract):
    """A row-level binding to the only CAR-T1-approved source revision."""

    source_id: Literal["fandom-hot-wheels-2025-pilot-r790665-v1"]
    source_kind: Literal["licensed_community_snapshot"]
    claim_tier: Literal["community_reference_snapshot_exact"]
    source_page_title: Literal["List of 2025 Hot Wheels"]
    source_page_url: Literal[
        "https://hotwheels.fandom.com/wiki/List_of_2025_Hot_Wheels?oldid=790665"
    ]
    source_revision_id: Literal[790665]
    source_revision_timestamp: Literal["2026-07-17T05:50:26Z"]
    source_record_id: OpaqueId
    normalized_snapshot_sha256: Literal[
        "e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6"
    ]
    license_name: Literal["CC-BY-SA"]
    license_url: Literal["https://www.fandom.com/licensing"]
    attribution: Literal[
        "Source: Hot Wheels Wiki contributors, List of 2025 Hot Wheels, revision 790665; normalized derivative."
    ]
    share_alike_required: Literal[True]


class AuthorityCandidate(StrictContract):
    schema_version: Literal["pvr-canonical-authority-candidate-v1"]
    candidate_id: OpaqueId
    source_binding: SourceRecordBinding
    family_group_key: OpaqueId
    proposed_release_key: OpaqueId
    selection_context_refs: list[OpaqueId]
    selection_context_role: Literal["candidate_selection_only"]
    catalog_lookup_state: CatalogLookupState
    canonical_uuid: UUID | None
    resolver_output_consulted: Literal[False]
    synthetic: Literal[False]
    status: CandidateStatus

    @model_validator(mode="after")
    def uuid_state_is_explicit(self) -> AuthorityCandidate:
        has_uuid = self.canonical_uuid is not None
        if has_uuid != (self.catalog_lookup_state == CatalogLookupState.existing_uuid):
            raise ValueError(
                "existing_uuid requires one UUID; a missing UUID requires catalog review"
            )
        if self.selection_context_refs != sorted(set(self.selection_context_refs)):
            raise ValueError("selection context references must be unique and ordered")
        for value in (
            self.candidate_id,
            self.family_group_key,
            self.proposed_release_key,
            *self.selection_context_refs,
        ):
            _reject_pii(value, context="candidate metadata")
        return self


class VariantFieldEvidence(StrictContract):
    schema_version: Literal["pvr-canonical-authority-field-evidence-v1"]
    field: VariantField
    source_field: ApprovedSourceField
    catalog_value: FieldValue
    reviewed_value: FieldValue
    evidence_refs: list[OpaqueId] = Field(min_length=1)
    source_bindings: list[SourceRecordBinding] = Field(min_length=1)
    agreement: EvidenceAgreement
    notes: str | None = None

    @model_validator(mode="after")
    def evidence_is_field_bound_and_non_inventive(self) -> VariantFieldEvidence:
        if SOURCE_TO_VARIANT_FIELD[self.source_field] != self.field:
            raise ValueError("source field is not approved for the declared catalog field")
        if self.evidence_refs != sorted(set(self.evidence_refs)):
            raise ValueError("evidence references must be unique and ordered")
        record_ids = [binding.source_record_id for binding in self.source_bindings]
        if record_ids != sorted(set(record_ids)):
            raise ValueError("source record bindings must be unique and ordered")
        if self.field in {VariantField.color, VariantField.edition}:
            raise ValueError("the approved snapshot supplies no color or edition evidence")
        if self.agreement == EvidenceAgreement.agrees:
            if _is_empty(self.catalog_value) or _is_empty(self.reviewed_value):
                raise ValueError("agreeing evidence cannot establish an empty value")
            if _normalized_value(self.catalog_value) != _normalized_value(self.reviewed_value):
                raise ValueError("agreeing evidence must reproduce the catalog value")
        if (
            self.field == VariantField.identifiers
            and self.source_field != ApprovedSourceField.toy_number
        ):
            raise ValueError("identifiers must be evidenced by toy_number")
        _reject_pii_tree(self.catalog_value, context=f"field evidence {self.field.value}")
        _reject_pii_tree(self.reviewed_value, context=f"field evidence {self.field.value}")
        _reject_pii(self.notes or "", context=f"field evidence {self.field.value}")
        return self


class CanonicalProductRecord(StrictContract):
    canonical_uuid: UUID
    casting: NonBlank
    release_year: int = Field(ge=1968, le=2200)
    series: str | None
    color: str | None
    collector_number: str | None
    series_position: str | None
    edition: str | None
    identifiers: list[NonBlank]
    family_group_key: OpaqueId
    release_key: OpaqueId
    synthetic: Literal[False]

    @model_validator(mode="after")
    def record_is_safe(self) -> CanonicalProductRecord:
        if self.identifiers != sorted(set(self.identifiers)):
            raise ValueError("product identifiers must be unique and ordered")
        for value in (
            self.casting,
            self.series or "",
            self.color or "",
            self.collector_number or "",
            self.series_position or "",
            self.edition or "",
            *self.identifiers,
        ):
            _reject_pii(value, context="catalog record")
        return self


class FrozenCatalogProduct(StrictContract):
    """One catalog member, preserving the repository's UUID-addressed products[] shape."""

    canonical_id: OpaqueId
    canonical_uuid: UUID
    record: CanonicalProductRecord
    record_sha256: Sha256

    @model_validator(mode="after")
    def record_is_bound_to_catalog_identity(self) -> FrozenCatalogProduct:
        if self.record.canonical_uuid != self.canonical_uuid:
            raise ValueError("catalog member UUID differs from its canonical record")
        if self.record_sha256 != content_sha256(self.record.model_dump(mode="json")):
            raise ValueError("catalog member record checksum is stale")
        return self


class FrozenCatalogParent(StrictContract):
    """Strict CAR projection of the repository catalog root and products array."""

    schema_version: Literal["pvr-canonical-authority-frozen-catalog-v1"]
    catalog_version: NonBlank
    products: list[FrozenCatalogProduct] = Field(min_length=1)

    @model_validator(mode="after")
    def members_are_unique_and_ordered(self) -> FrozenCatalogParent:
        uuids = [product.canonical_uuid for product in self.products]
        ids = [product.canonical_id for product in self.products]
        if uuids != sorted(uuids, key=str):
            raise ValueError("frozen catalog products must be ordered by canonical UUID")
        if len(uuids) != len(set(uuids)) or len(ids) != len(set(ids)):
            raise ValueError("frozen catalog UUIDs and canonical IDs must be unique")
        return self


class CatalogProposalStatus(str, Enum):
    staged = "staged"
    reviewed = "reviewed"
    approved = "approved"
    rejected = "rejected"


class CatalogRecordProposal(StrictContract):
    schema_version: Literal["pvr-canonical-catalog-record-proposal-v1"]
    proposal_id: OpaqueId
    candidate_id: OpaqueId
    parent_catalog_version: NonBlank
    parent_catalog_sha256: Sha256
    proposed_canonical_uuid: UUID
    proposed_product_record: CanonicalProductRecord
    product_record_sha256: Sha256
    source_decision_ids: list[Literal["fandom-hot-wheels-2025-pilot-r790665-v1"]] = Field(
        min_length=1
    )
    field_evidence: list[VariantFieldEvidence] = Field(min_length=1)
    review_status: CatalogProposalStatus
    reviewed_by_role: Literal["project_owner"] | None
    reviewed_at: AwareDatetime | None
    review_reason: str | None
    authority_approved: Literal[False]

    @model_validator(mode="after")
    def proposal_is_hash_bound_but_not_authority(self) -> CatalogRecordProposal:
        _require_canonical_evidence_order(self.field_evidence)
        if self.proposed_product_record.canonical_uuid != self.proposed_canonical_uuid:
            raise ValueError("proposed UUID differs from the proposed product record")
        if self.product_record_sha256 != content_sha256(
            self.proposed_product_record.model_dump(mode="json")
        ):
            raise ValueError("proposed product record checksum is stale")
        if self.source_decision_ids != sorted(set(self.source_decision_ids)):
            raise ValueError("source decision IDs must be unique and ordered")
        reviewed = self.review_status != CatalogProposalStatus.staged
        metadata_complete = all(
            value is not None
            for value in (self.reviewed_by_role, self.reviewed_at, self.review_reason)
        )
        if reviewed != metadata_complete:
            raise ValueError("non-staged catalog decisions require complete owner review metadata")
        if self.review_reason is not None:
            _reject_pii(self.review_reason, context="catalog proposal reason")
        if self.review_status == CatalogProposalStatus.approved:
            _require_complete_agreeing_evidence(self.proposed_product_record, self.field_evidence)
        return self


class OwnerReviewPacket(StrictContract):
    """Strict companion for the local-only, human-readable owner packet."""

    schema_version: Literal["pvr-canonical-authority-owner-review-packet-v1"]
    packet_version: NonBlank
    publication_scope: Literal["local_only_git_ignored"]
    source_decisions_sha256: Sha256
    catalog_version: NonBlank
    catalog_sha256: Sha256
    candidates: list[AuthorityCandidate] = Field(min_length=1)
    field_evidence: dict[OpaqueId, list[VariantFieldEvidence]]
    owner_questions: dict[OpaqueId, list[NonBlank]]
    missing_or_conflicting_items: dict[OpaqueId, list[NonBlank]]
    resolver_output_consulted: Literal[False]
    resolver_output_included: Literal[False]
    predicted_uuid_included: Literal[False]
    model_scores_included: Literal[False]
    network_requests: Literal[0]

    @model_validator(mode="after")
    def packet_is_complete_and_output_blind(self) -> OwnerReviewPacket:
        ids = [candidate.candidate_id for candidate in self.candidates]
        if ids != sorted(ids) or len(ids) != len(set(ids)):
            raise ValueError("packet candidates must be unique and ordered by candidate_id")
        expected = set(ids)
        if set(self.field_evidence) != expected:
            raise ValueError("packet field evidence must cover every candidate exactly once")
        if set(self.owner_questions) != expected:
            raise ValueError("packet owner questions must cover every candidate exactly once")
        if set(self.missing_or_conflicting_items) != expected:
            raise ValueError("packet issue lists must cover every candidate exactly once")
        for candidate in self.candidates:
            evidence = self.field_evidence[candidate.candidate_id]
            questions = self.owner_questions[candidate.candidate_id]
            issues = self.missing_or_conflicting_items[candidate.candidate_id]
            _require_canonical_evidence_order(evidence)
            if issues != sorted(set(issues)):
                raise ValueError("packet issues must be unique and ordered")
            if not questions:
                raise ValueError("each packet candidate requires a plain-language owner question")
            needs_issue = any(row.agreement != EvidenceAgreement.agrees for row in evidence)
            if needs_issue and not issues:
                raise ValueError(
                    "unreviewable or non-agreeing candidates require an explicit issue"
                )
        _reject_pii_tree(self.owner_questions, context="owner questions")
        _reject_pii_tree(self.missing_or_conflicting_items, context="packet issues")
        return self


class OwnerAttestation(StrictContract):
    """The owner's explicit decision, cryptographically bound to packet and catalog parents."""

    schema_version: Literal["pvr-canonical-authority-owner-attestation-v1"]
    candidate_id: OpaqueId
    packet_sha256: Sha256
    catalog_version: NonBlank
    catalog_sha256: Sha256
    catalog_record_sha256: Sha256 | None
    outcome: ReviewStatus
    confirmation_method: Literal["owner_attestation"]
    resolver_output_consulted: Literal[False]
    reviewed_by_role: Literal["project_owner"]
    reviewed_at: AwareDatetime
    review_reason: NonBlank

    @model_validator(mode="after")
    def attestation_is_an_explicit_human_outcome(self) -> OwnerAttestation:
        if self.outcome == ReviewStatus.staged:
            raise ValueError("owner attestation cannot preserve an unreviewed staged outcome")
        if (
            self.outcome in {ReviewStatus.reviewed, ReviewStatus.approved_exact}
            and self.catalog_record_sha256 is None
        ):
            raise ValueError("reviewed/exact attestation requires a catalog record checksum")
        _reject_pii(self.review_reason, context="owner attestation reason")
        return self


class CatalogResolutionBinding(StrictContract):
    """Immutable bridge from a frozen CAR-T4 proposal to one applied catalog-v2 row."""

    schema_version: Literal["pvr-canonical-authority-catalog-resolution-binding-v1"]
    ordinal: int = Field(ge=1, le=20)
    candidate_id: OpaqueId
    candidate_sha256: Sha256
    proposal_id: OpaqueId
    proposal_sha256: Sha256
    proposal_product_record_sha256: Sha256
    catalog_application_manifest_sha256: Sha256
    catalog_version: Literal["catalog-v2"]
    catalog_sha256: Sha256
    family_group_key: OpaqueId
    release_key: OpaqueId
    applied_canonical_uuid: UUID
    applied_canonical_id: OpaqueId
    applied_catalog_record_sha256: Sha256


class ExpectedBatchOwnerAuthorization(StrictContract):
    """External Gate expectation supplied independently of the stored authorization artifact."""

    gate: Literal["T5-G1", "T5-G2"]
    authorization_scope: Literal["staged_to_reviewed", "reviewed_to_approved_exact"]
    authorization_declaration: Literal[
        "owner_explicitly_authorized_t5_g1_review_outcomes_for_every_covered_entry",
        "owner_explicitly_authorized_t5_g2_exact_authority_outcomes_for_every_covered_entry",
    ]
    expected_outcome: ReviewStatus
    batch_ordinal: int = Field(ge=1)
    family_batch_sha256: Sha256
    catalog_application_manifest_sha256: Sha256
    exact_external_response: NonBlank
    exact_external_response_sha256: Sha256
    prior_gate_response_sha256s: list[Sha256]

    @model_validator(mode="after")
    def expectation_is_gate_specific_and_external(self) -> ExpectedBatchOwnerAuthorization:
        expected_scope = {
            "T5-G1": "staged_to_reviewed",
            "T5-G2": "reviewed_to_approved_exact",
        }
        expected_declaration = {
            "T5-G1": "owner_explicitly_authorized_t5_g1_review_outcomes_for_every_covered_entry",
            "T5-G2": (
                "owner_explicitly_authorized_t5_g2_exact_authority_outcomes_for_every_covered_entry"
            ),
        }
        if self.authorization_scope != expected_scope[self.gate]:
            raise ValueError("external authorization scope differs from the expected Gate")
        if self.authorization_declaration != expected_declaration[self.gate]:
            raise ValueError("external authorization declaration differs from the expected Gate")
        allowed_outcomes = {
            "T5-G1": {
                ReviewStatus.reviewed,
                ReviewStatus.held,
                ReviewStatus.conflicted,
                ReviewStatus.insufficient,
            },
            "T5-G2": {
                ReviewStatus.approved_exact,
                ReviewStatus.held,
                ReviewStatus.conflicted,
                ReviewStatus.insufficient,
            },
        }
        if self.expected_outcome not in allowed_outcomes[self.gate]:
            raise ValueError("external expected outcome differs from the expected Gate")
        response_sha = hashlib.sha256(self.exact_external_response.encode("utf-8")).hexdigest()
        if self.exact_external_response_sha256 != response_sha:
            raise ValueError("external owner response checksum is stale")
        if self.prior_gate_response_sha256s != sorted(set(self.prior_gate_response_sha256s)):
            raise ValueError("prior Gate response hashes must be unique and ordered")
        if self.gate == "T5-G1" and self.prior_gate_response_sha256s:
            raise ValueError("T5-G1 cannot declare a prior authority-review Gate response")
        if self.gate == "T5-G2" and not self.prior_gate_response_sha256s:
            raise ValueError("T5-G2 requires the independently committed T5-G1 response hash")
        if self.exact_external_response_sha256 in self.prior_gate_response_sha256s:
            raise ValueError("one external owner response cannot authorize both Gates")
        return self


class BatchOwnerAuthorization(StrictContract):
    """Future-Gate exact external authorization; preparation never creates this contract."""

    schema_version: Literal["pvr-canonical-authority-batch-owner-authorization-v1"]
    gate: Literal["T5-G1", "T5-G2"]
    authorization_scope: Literal["staged_to_reviewed", "reviewed_to_approved_exact"]
    authorization_declaration: Literal[
        "owner_explicitly_authorized_t5_g1_review_outcomes_for_every_covered_entry",
        "owner_explicitly_authorized_t5_g2_exact_authority_outcomes_for_every_covered_entry",
    ]
    packet_sha256: Sha256
    batch_ordinal: int = Field(ge=1)
    family_batch_sha256: Sha256
    catalog_application_manifest_sha256: Sha256
    catalog_version: Literal["catalog-v2"]
    catalog_sha256: Sha256
    ordered_candidate_ids: list[OpaqueId] = Field(min_length=1)
    ordered_entry_sha256s: list[Sha256] = Field(min_length=1)
    declared_outcome: ReviewStatus
    owner_response_verbatim: NonBlank
    authorized_exact_owner_response: NonBlank
    response_verbatim_sha256: Sha256
    prior_gate_response_sha256s: list[Sha256]
    confirmation_method: Literal["owner_attestation"]
    reviewed_by_role: Literal["project_owner"]
    authorized_at: AwareDatetime
    resolver_output_consulted: Literal[False]
    authorization_sha256: Sha256

    @model_validator(mode="after")
    def authorization_is_exact_and_gate_scoped(self) -> BatchOwnerAuthorization:
        if self.owner_response_verbatim != self.authorized_exact_owner_response:
            raise ValueError("batch authorization must match the exact external owner response")
        if len(self.ordered_candidate_ids) != len(self.ordered_entry_sha256s):
            raise ValueError("batch authorization must bind every covered entry")
        if self.ordered_candidate_ids != sorted(set(self.ordered_candidate_ids)):
            raise ValueError("batch authorization candidates must be unique and ordered")
        response_sha = hashlib.sha256(self.owner_response_verbatim.encode("utf-8")).hexdigest()
        if self.response_verbatim_sha256 != response_sha:
            raise ValueError("batch owner response checksum is stale")
        if self.authorized_at.utcoffset() != UTC.utcoffset(self.authorized_at):
            raise ValueError("batch authorization timestamp must be UTC")
        if self.authorized_at.microsecond:
            raise ValueError("batch authorization timestamp must use whole-second precision")
        expected_scope = {
            "T5-G1": "staged_to_reviewed",
            "T5-G2": "reviewed_to_approved_exact",
        }
        expected_declaration = {
            "T5-G1": "owner_explicitly_authorized_t5_g1_review_outcomes_for_every_covered_entry",
            "T5-G2": (
                "owner_explicitly_authorized_t5_g2_exact_authority_outcomes_for_every_covered_entry"
            ),
        }
        if self.authorization_scope != expected_scope[self.gate]:
            raise ValueError("batch authorization scope differs from its Gate")
        if self.authorization_declaration != expected_declaration[self.gate]:
            raise ValueError("batch authorization declaration differs from its Gate")
        if self.prior_gate_response_sha256s != sorted(set(self.prior_gate_response_sha256s)):
            raise ValueError("prior Gate response hashes must be unique and ordered")
        if self.gate == "T5-G1" and self.prior_gate_response_sha256s:
            raise ValueError("T5-G1 cannot declare a prior Gate response")
        if self.gate == "T5-G2" and not self.prior_gate_response_sha256s:
            raise ValueError("T5-G2 requires the T5-G1 response hash")
        if self.response_verbatim_sha256 in self.prior_gate_response_sha256s:
            raise ValueError("one owner response cannot authorize both Gates")
        expected_outcomes = {
            "staged_to_reviewed": {
                ReviewStatus.reviewed,
                ReviewStatus.held,
                ReviewStatus.conflicted,
                ReviewStatus.insufficient,
            },
            "reviewed_to_approved_exact": {
                ReviewStatus.approved_exact,
                ReviewStatus.held,
                ReviewStatus.conflicted,
                ReviewStatus.insufficient,
            },
        }
        if self.declared_outcome not in expected_outcomes[self.authorization_scope]:
            raise ValueError("declared outcome is invalid for the selected owner Gate")
        expected = content_sha256(self.model_dump(mode="json", exclude={"authorization_sha256"}))
        if self.authorization_sha256 != expected:
            raise ValueError("batch authorization checksum is stale")
        return self


def validate_batch_owner_authorization(
    payload: BatchOwnerAuthorization | Mapping[str, Any],
    *,
    expected: ExpectedBatchOwnerAuthorization | Mapping[str, Any],
) -> BatchOwnerAuthorization:
    """Validate a stored batch only against independently supplied external authorization."""

    authorization_payload = (
        payload.model_dump(mode="json") if isinstance(payload, BatchOwnerAuthorization) else payload
    )
    expected_payload = (
        expected.model_dump(mode="json")
        if isinstance(expected, ExpectedBatchOwnerAuthorization)
        else expected
    )
    authorization = BatchOwnerAuthorization.model_validate(authorization_payload)
    external = ExpectedBatchOwnerAuthorization.model_validate(expected_payload)
    if (
        authorization.gate != external.gate
        or authorization.authorization_scope != external.authorization_scope
        or authorization.authorization_declaration != external.authorization_declaration
        or authorization.declared_outcome != external.expected_outcome
        or authorization.batch_ordinal != external.batch_ordinal
        or authorization.family_batch_sha256 != external.family_batch_sha256
        or authorization.catalog_application_manifest_sha256
        != external.catalog_application_manifest_sha256
        or authorization.owner_response_verbatim != external.exact_external_response
        or authorization.authorized_exact_owner_response != external.exact_external_response
        or authorization.response_verbatim_sha256 != external.exact_external_response_sha256
        or authorization.prior_gate_response_sha256s != external.prior_gate_response_sha256s
    ):
        raise AuthorityContractError(
            "stored batch authorization differs from the independent external Gate expectation"
        )
    return authorization


class OwnerAttestationV2(StrictContract):
    schema_version: Literal["pvr-canonical-authority-owner-attestation-v2"]
    candidate_id: OpaqueId
    packet_sha256: Sha256
    catalog_version: Literal["catalog-v2"]
    catalog_sha256: Sha256
    catalog_record_sha256: Sha256 | None
    outcome: ReviewStatus
    confirmation_method: Literal["owner_attestation"]
    resolver_output_consulted: Literal[False]
    reviewed_by_role: Literal["project_owner"]
    reviewed_at: AwareDatetime
    review_reason: NonBlank
    batch_authorization_sha256: Sha256
    attestation_sha256: Sha256

    @model_validator(mode="after")
    def attestation_is_explicit_and_batch_bound(self) -> OwnerAttestationV2:
        if self.outcome == ReviewStatus.staged:
            raise ValueError("owner attestation cannot preserve staged")
        if self.outcome in {ReviewStatus.reviewed, ReviewStatus.approved_exact} and (
            self.catalog_record_sha256 is None
        ):
            raise ValueError("reviewed/exact attestation requires a catalog record checksum")
        _reject_pii(self.review_reason, context="owner attestation reason")
        expected = content_sha256(self.model_dump(mode="json", exclude={"attestation_sha256"}))
        if self.attestation_sha256 != expected:
            raise ValueError("owner attestation checksum is stale")
        return self


class AuthorityReviewEvent(StrictContract):
    schema_version: Literal["pvr-canonical-authority-review-event-v1"]
    event_id: OpaqueId
    candidate_id: OpaqueId
    from_status: ReviewStatus
    to_status: ReviewStatus
    packet_sha256: Sha256
    catalog_version: NonBlank
    catalog_sha256: Sha256
    canonical_uuid: UUID | None
    catalog_record_sha256: Sha256 | None
    variant_field_evidence: list[VariantFieldEvidence]
    source_decision_ids: list[Literal["fandom-hot-wheels-2025-pilot-r790665-v1"]] = Field(
        min_length=1
    )
    confirmation_method: Literal["owner_attestation"]
    attestation_sha256: Sha256
    resolver_output_consulted: Literal[False]
    reviewed_by_role: Literal["project_owner"]
    reviewed_at: AwareDatetime
    review_reason: NonBlank
    remediation_note: str | None

    @model_validator(mode="after")
    def transition_and_outcome_fail_closed(self) -> AuthorityReviewEvent:
        _require_canonical_evidence_order(self.variant_field_evidence)
        if self.to_status not in ALLOWED_TRANSITIONS[self.from_status]:
            raise ValueError(f"invalid authority transition {self.from_status}->{self.to_status}")
        if self.source_decision_ids != sorted(set(self.source_decision_ids)):
            raise ValueError("source decision IDs must be unique and ordered")
        if (self.canonical_uuid is None) != (self.catalog_record_sha256 is None):
            raise ValueError("canonical UUID and catalog record checksum must be present together")
        if self.to_status in {ReviewStatus.reviewed, ReviewStatus.approved_exact}:
            if self.canonical_uuid is None:
                raise ValueError("reviewed/exact events require a catalog UUID")
            if not self.variant_field_evidence:
                raise ValueError("reviewed/exact events require field evidence")
        if self.to_status == ReviewStatus.approved_exact and any(
            evidence.agreement != EvidenceAgreement.agrees
            for evidence in self.variant_field_evidence
        ):
            raise ValueError("approved_exact cannot retain conflicting or insufficient evidence")
        needs_remediation = self.to_status in {
            ReviewStatus.held,
            ReviewStatus.conflicted,
            ReviewStatus.insufficient,
            ReviewStatus.revoked,
        }
        if needs_remediation != bool(self.remediation_note and self.remediation_note.strip()):
            raise ValueError("non-approved outcomes require remediation; positive states forbid it")
        _reject_pii(self.review_reason, context="review reason")
        _reject_pii(self.remediation_note or "", context="remediation note")
        return self


class AuthorityReviewEventV2(StrictContract):
    schema_version: Literal["pvr-canonical-authority-review-event-v2"]
    event_id: OpaqueId
    candidate_id: OpaqueId
    from_status: ReviewStatus
    to_status: ReviewStatus
    packet_sha256: Sha256
    catalog_version: Literal["catalog-v2"]
    catalog_sha256: Sha256
    canonical_uuid: UUID | None
    catalog_record_sha256: Sha256 | None
    variant_field_evidence: list[VariantFieldEvidence]
    source_decision_ids: list[Literal["fandom-hot-wheels-2025-pilot-r790665-v1"]] = Field(
        min_length=1
    )
    confirmation_method: Literal["owner_attestation"]
    attestation_sha256: Sha256
    batch_authorization_sha256: Sha256
    resolver_output_consulted: Literal[False]
    reviewed_by_role: Literal["project_owner"]
    reviewed_at: AwareDatetime
    review_reason: NonBlank
    remediation_note: str | None
    event_sha256: Sha256

    @model_validator(mode="after")
    def transition_is_two_gate_and_hash_bound(self) -> AuthorityReviewEventV2:
        allowed = {
            ReviewStatus.staged: {
                ReviewStatus.reviewed,
                ReviewStatus.held,
                ReviewStatus.conflicted,
                ReviewStatus.insufficient,
            },
            ReviewStatus.held: {ReviewStatus.reviewed},
            ReviewStatus.conflicted: {ReviewStatus.reviewed},
            ReviewStatus.insufficient: {ReviewStatus.reviewed},
            ReviewStatus.reviewed: {
                ReviewStatus.approved_exact,
                ReviewStatus.held,
                ReviewStatus.conflicted,
                ReviewStatus.insufficient,
            },
            ReviewStatus.approved_exact: {ReviewStatus.revoked},
            ReviewStatus.revoked: set(),
        }
        if self.to_status not in allowed[self.from_status]:
            raise ValueError(f"invalid authority transition {self.from_status}->{self.to_status}")
        if (
            self.from_status == ReviewStatus.staged
            and self.to_status == ReviewStatus.approved_exact
        ):
            raise ValueError("exact authority requires a separate reviewed Gate")
        _require_canonical_evidence_order(self.variant_field_evidence)
        if self.source_decision_ids != sorted(set(self.source_decision_ids)):
            raise ValueError("source decision IDs must be unique and ordered")
        if (self.canonical_uuid is None) != (self.catalog_record_sha256 is None):
            raise ValueError("canonical UUID and catalog checksum must be present together")
        positive = self.to_status in {ReviewStatus.reviewed, ReviewStatus.approved_exact}
        if positive and (self.canonical_uuid is None or not self.variant_field_evidence):
            raise ValueError("reviewed/exact events require catalog identity and evidence")
        if self.to_status == ReviewStatus.approved_exact and any(
            row.agreement != EvidenceAgreement.agrees for row in self.variant_field_evidence
        ):
            raise ValueError("approved_exact requires complete agreeing evidence")
        needs_remediation = self.to_status in {
            ReviewStatus.held,
            ReviewStatus.conflicted,
            ReviewStatus.insufficient,
            ReviewStatus.revoked,
        }
        if needs_remediation != bool(self.remediation_note and self.remediation_note.strip()):
            raise ValueError("non-approved outcomes require remediation; positive states forbid it")
        _reject_pii(self.review_reason, context="review reason")
        _reject_pii(self.remediation_note or "", context="remediation note")
        expected = content_sha256(self.model_dump(mode="json", exclude={"event_sha256"}))
        if self.event_sha256 != expected:
            raise ValueError("authority review event checksum is stale")
        return self


ALLOWED_TRANSITIONS: Mapping[ReviewStatus, frozenset[ReviewStatus]] = {
    ReviewStatus.staged: frozenset({ReviewStatus.reviewed, ReviewStatus.held}),
    ReviewStatus.held: frozenset({ReviewStatus.reviewed}),
    ReviewStatus.conflicted: frozenset({ReviewStatus.reviewed}),
    ReviewStatus.insufficient: frozenset({ReviewStatus.reviewed}),
    ReviewStatus.reviewed: frozenset(
        {
            ReviewStatus.approved_exact,
            ReviewStatus.conflicted,
            ReviewStatus.insufficient,
            ReviewStatus.held,
        }
    ),
    ReviewStatus.approved_exact: frozenset({ReviewStatus.revoked}),
    ReviewStatus.revoked: frozenset(),
}


class AuthorityBundleRecord(StrictContract):
    candidate_id: OpaqueId
    canonical_uuid: UUID
    family_group_key: OpaqueId
    release_key: OpaqueId
    status: ReviewStatus
    synthetic: Literal[False]
    latest_event_id: OpaqueId
    catalog_version: NonBlank
    catalog_record_sha256: Sha256
    source_decision_ids: list[Literal["fandom-hot-wheels-2025-pilot-r790665-v1"]]
    evidence_sha256s: list[Sha256] = Field(min_length=1)

    @model_validator(mode="after")
    def record_references_are_unique_and_ordered(self) -> AuthorityBundleRecord:
        if self.status not in {
            ReviewStatus.approved_exact,
            ReviewStatus.conflicted,
            ReviewStatus.insufficient,
            ReviewStatus.held,
            ReviewStatus.revoked,
        }:
            raise ValueError("bundle records must have a resolved review outcome")
        if self.source_decision_ids != sorted(set(self.source_decision_ids)):
            raise ValueError("source decision IDs must be unique and ordered")
        if self.evidence_sha256s != sorted(set(self.evidence_sha256s)):
            raise ValueError("evidence checksums must be unique and ordered")
        return self


class AuthorityBundle(StrictContract):
    schema_version: Literal["pvr-canonical-authority-bundle-v1"]
    bundle_version: NonBlank
    records: list[AuthorityBundleRecord]
    resolver_output_consulted: Literal[False]
    network_requests: Literal[0]
    rhb_t5_authorized: Literal[False]

    @model_validator(mode="after")
    def records_are_stably_ordered_and_distinct(self) -> AuthorityBundle:
        candidate_ids = [record.candidate_id for record in self.records]
        if candidate_ids != sorted(candidate_ids):
            raise ValueError("bundle records must be ordered by candidate_id")
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("bundle candidate IDs must be unique")
        uuids = [record.canonical_uuid for record in self.records]
        if len(uuids) != len(set(uuids)):
            raise ValueError("bundle canonical UUIDs must be distinct")
        return self


class ArtifactDigest(StrictContract):
    reference: NonBlank
    sha256: Sha256

    @model_validator(mode="after")
    def reference_is_safe(self) -> ArtifactDigest:
        _reject_unsafe_reference(self.reference)
        return self


class FamilyComposition(StrictContract):
    family_group_key: OpaqueId
    release_keys: list[OpaqueId] = Field(min_length=2)
    approved_variant_count: int = Field(ge=2)

    @model_validator(mode="after")
    def releases_are_distinct_and_ordered(self) -> FamilyComposition:
        if self.release_keys != sorted(set(self.release_keys)):
            raise ValueError("family releases must be unique and ordered")
        if self.approved_variant_count != len(self.release_keys):
            raise ValueError("family count must equal distinct releases")
        return self


class AuthorityShortfalls(StrictContract):
    exact_variant_shortfall: int = Field(ge=0)
    qualifying_family_shortfall: int = Field(ge=0)


class AuthorityBundleManifest(StrictContract):
    schema_version: Literal["pvr-canonical-authority-bundle-manifest-v1"]
    bundle_version: NonBlank
    authority_bundle_sha256: Sha256
    ordered_parent_artifacts: list[ArtifactDigest] = Field(min_length=1)
    catalog_version: NonBlank
    catalog_sha256: Sha256
    source_decision_sha256s: list[Sha256] = Field(min_length=1)
    counts_by_status: dict[ReviewStatus, int]
    approved_distinct_variant_count: int = Field(ge=0)
    qualifying_family_count: int = Field(ge=0)
    family_composition: list[FamilyComposition]
    resolver_output_consulted: Literal[False]
    network_requests: Literal[0]
    publication_scope: Literal["safe_metadata_only"]
    gate_status: Literal["eligible_for_rhb_t4_reaudit", "blocked_insufficient_exact_authority"]
    shortfalls: AuthorityShortfalls
    created_at: AwareDatetime
    status: Literal["complete"]
    rhb_t5_authorized: Literal[False]

    @model_validator(mode="after")
    def manifest_shape_is_stable(self) -> AuthorityBundleManifest:
        refs = [parent.reference for parent in self.ordered_parent_artifacts]
        if refs != sorted(refs) or len(refs) != len(set(refs)):
            raise ValueError("parent artifacts must be unique and ordered by reference")
        if self.source_decision_sha256s != sorted(set(self.source_decision_sha256s)):
            raise ValueError("source decision checksums must be unique and ordered")
        families = [item.family_group_key for item in self.family_composition]
        if families != sorted(families) or len(families) != len(set(families)):
            raise ValueError("family composition must be unique and ordered")
        return self


class ApprovedSourceContext(StrictContract):
    """Validated facts derived from CAR-T1; callers cannot broaden them."""

    source_id: Literal["fandom-hot-wheels-2025-pilot-r790665-v1"]
    normalized_snapshot_sha256: Literal[
        "e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6"
    ]
    source_decisions_sha256: Sha256
    source_record_ids: frozenset[OpaqueId]
    source_records: dict[OpaqueId, dict[str, FieldValue]]


def stable_json_bytes(value: Any) -> bytes:
    """Canonical JSON encoding used for every CAR v1 content checksum."""

    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def content_sha256(value: Any) -> str:
    """Return the SHA-256 of a JSON-compatible value in CAR canonical encoding."""

    return hashlib.sha256(stable_json_bytes(value)).hexdigest()


def validate_authority_source_decisions(root: Path) -> ApprovedSourceContext:
    """Reuse CAR-T1 validation and derive the exact approved 100-row membership set."""

    root = root.resolve()
    validate_source_gate_paths(root)
    normalized = load_json(root / NORMALIZED_PATH)
    if not isinstance(normalized, dict):
        raise AuthorityContractError("validated normalized snapshot has no record list")
    raw_records = normalized.get("records")
    if not isinstance(raw_records, list):
        raise AuthorityContractError("validated normalized snapshot has no record list")
    record_ids: set[str] = set()
    source_records: dict[str, dict[str, FieldValue]] = {}
    for record in raw_records:
        if isinstance(record, dict):
            source_record_id = record.get("source_record_id")
            if isinstance(source_record_id, str):
                record_ids.add(source_record_id)
                row: dict[str, FieldValue] = {}
                for source_field in ApprovedSourceField:
                    value = record.get(source_field.value)
                    if not (
                        value is None
                        or isinstance(value, (str, int))
                        or (
                            isinstance(value, list) and all(isinstance(item, str) for item in value)
                        )
                    ):
                        raise AuthorityContractError(
                            f"approved source row has invalid {source_field.value} value"
                        )
                    row[source_field.value] = cast(FieldValue, value)
                source_records[source_record_id] = row
    if len(record_ids) != 100:
        raise AuthorityContractError("approved source membership must contain exactly 100 rows")
    return ApprovedSourceContext(
        source_id="fandom-hot-wheels-2025-pilot-r790665-v1",
        normalized_snapshot_sha256=(
            "e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6"
        ),
        source_decisions_sha256=content_sha256(load_json(root / DECISIONS_PATH)),
        source_record_ids=frozenset(record_ids),
        source_records=source_records,
    )


def _fresh[T: BaseModel](model: type[T], value: T | Mapping[str, Any]) -> T:
    """Re-parse nested models so ``model_construct`` cannot bypass high-level checks."""

    _reject_preconstructed_extras(value)
    payload: Any = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return model.model_validate(payload)


def validate_frozen_catalog_parent(
    payload: FrozenCatalogParent | Mapping[str, Any],
) -> FrozenCatalogParent:
    """Validate one self-contained catalog parent before deriving its version or digest."""

    return _fresh(FrozenCatalogParent, payload)


def validate_authority_candidate(
    payload: AuthorityCandidate | Mapping[str, Any], *, root: Path
) -> AuthorityCandidate:
    candidate = _fresh(AuthorityCandidate, payload)
    context = validate_authority_source_decisions(root)
    _validate_binding(candidate.source_binding, context)
    return candidate


def validate_field_evidence(
    payload: VariantFieldEvidence | Mapping[str, Any], *, root: Path
) -> VariantFieldEvidence:
    evidence = _fresh(VariantFieldEvidence, payload)
    context = validate_authority_source_decisions(root)
    for binding in evidence.source_bindings:
        _validate_binding(binding, context)
    return evidence


def validate_catalog_record_proposal(
    payload: CatalogRecordProposal | Mapping[str, Any],
    *,
    root: Path,
    candidate_payload: AuthorityCandidate | Mapping[str, Any],
    catalog_parent_payload: FrozenCatalogParent | Mapping[str, Any],
) -> CatalogRecordProposal:
    proposal = _fresh(CatalogRecordProposal, payload)
    candidate = validate_authority_candidate(candidate_payload, root=root)
    catalog_parent = validate_frozen_catalog_parent(catalog_parent_payload)
    parent_sha256 = content_sha256(catalog_parent.model_dump(mode="json"))
    if candidate.catalog_lookup_state != CatalogLookupState.catalog_review_required:
        raise AuthorityContractError("catalog proposal requires a candidate with a missing UUID")
    if proposal.candidate_id != candidate.candidate_id:
        raise AuthorityContractError("catalog proposal belongs to another candidate")
    if proposal.parent_catalog_version != catalog_parent.catalog_version:
        raise AuthorityContractError("catalog proposal parent version is stale")
    if proposal.parent_catalog_sha256 != parent_sha256:
        raise AuthorityContractError("catalog proposal parent checksum is stale")
    if any(
        member.canonical_uuid == proposal.proposed_canonical_uuid
        for member in catalog_parent.products
    ):
        raise AuthorityContractError(
            "catalog proposal UUID already exists in the frozen parent and is not a creation"
        )
    context = validate_authority_source_decisions(root)
    _validate_product_candidate_identity(proposal.proposed_product_record, candidate)
    for evidence in proposal.field_evidence:
        _validate_evidence_for_candidate(evidence, candidate, context)
    return proposal


def validate_owner_review_packet(
    payload: OwnerReviewPacket | Mapping[str, Any],
    *,
    root: Path,
    catalog_parent_payload: FrozenCatalogParent | Mapping[str, Any],
    approved_catalog_proposals: Mapping[str, CatalogRecordProposal | Mapping[str, Any]]
    | None = None,
) -> OwnerReviewPacket:
    packet = _fresh(OwnerReviewPacket, payload)
    context = validate_authority_source_decisions(root)
    catalog_parent = validate_frozen_catalog_parent(catalog_parent_payload)
    catalog_sha256 = content_sha256(catalog_parent.model_dump(mode="json"))
    proposals = approved_catalog_proposals or {}
    if packet.source_decisions_sha256 != context.source_decisions_sha256:
        raise AuthorityContractError("owner packet source-decision checksum is stale")
    if packet.catalog_version != catalog_parent.catalog_version:
        raise AuthorityContractError("owner packet catalog version is stale")
    if packet.catalog_sha256 != catalog_sha256:
        raise AuthorityContractError("owner packet catalog checksum is stale")
    expected_proposal_ids = {
        candidate.candidate_id
        for candidate in packet.candidates
        if candidate.catalog_lookup_state == CatalogLookupState.catalog_review_required
    }
    if set(proposals) != expected_proposal_ids:
        raise AuthorityContractError(
            "owner packet approved proposals must match candidates requiring catalog review"
        )
    for candidate in packet.candidates:
        _validate_binding(candidate.source_binding, context)
        if candidate.catalog_lookup_state == CatalogLookupState.existing_uuid:
            member = next(
                (
                    item
                    for item in catalog_parent.products
                    if item.canonical_uuid == candidate.canonical_uuid
                ),
                None,
            )
            if member is None:
                raise AuthorityContractError(
                    "packet candidate UUID is not a member of the frozen catalog parent"
                )
            product = member.record
            _validate_product_candidate_identity(product, candidate)
        else:
            proposal = validate_catalog_record_proposal(
                proposals[candidate.candidate_id],
                root=root,
                candidate_payload=candidate,
                catalog_parent_payload=catalog_parent,
            )
            if proposal.review_status != CatalogProposalStatus.approved:
                raise AuthorityContractError("owner packet requires an approved catalog proposal")
            product = proposal.proposed_product_record
        evidence_rows = packet.field_evidence[candidate.candidate_id]
        for evidence in evidence_rows:
            _validate_evidence_for_candidate(evidence, candidate, context)
        fields = [row.field for row in evidence_rows]
        if len(fields) != len(set(fields)):
            raise AuthorityContractError("owner packet has duplicate field evidence")
        required = _required_fields(product)
        missing = required - set(fields)
        conflicts = {
            row.field for row in evidence_rows if row.agreement != EvidenceAgreement.agrees
        }
        expected_issues = sorted(
            {
                *(f"missing:{field.value}" for field in missing),
                *(f"conflicting:{field.value}" for field in conflicts),
            }
        )
        actual_issues = packet.missing_or_conflicting_items[candidate.candidate_id]
        if actual_issues != expected_issues:
            raise AuthorityContractError(
                "packet issues must exactly enumerate missing/conflicting catalog fields"
            )
        for row in evidence_rows:
            expected_value = _product_field_values(product)[row.field]
            if _normalized_value(row.catalog_value) != _normalized_value(expected_value):
                raise AuthorityContractError(
                    f"packet evidence catalog value is stale for {row.field.value}"
                )
    return packet


def validate_review_event_chain(
    candidate_payload: AuthorityCandidate | Mapping[str, Any],
    event_payloads: Sequence[AuthorityReviewEvent | Mapping[str, Any]],
    *,
    root: Path,
    catalog_record: CanonicalProductRecord | Mapping[str, Any] | None = None,
    approved_catalog_proposal: CatalogRecordProposal | Mapping[str, Any] | None = None,
    attestations: Mapping[str, OwnerAttestation | Mapping[str, Any]] | None = None,
    expected_packet_sha256: str,
    catalog_parent_payload: FrozenCatalogParent | Mapping[str, Any],
) -> tuple[AuthorityReviewEvent, ...]:
    """Validate an append-only chain and the separate catalog/authority approval boundary."""

    candidate = validate_authority_candidate(candidate_payload, root=root)
    events = tuple(_fresh(AuthorityReviewEvent, event) for event in event_payloads)
    if not events:
        raise AuthorityContractError("review event chain must not be empty")
    if attestations is None:
        raise AuthorityContractError("review event chain requires owner attestation artifacts")
    event_ids = [event.event_id for event in events]
    if len(event_ids) != len(set(event_ids)):
        raise AuthorityContractError("review event IDs must be unique")
    timestamps = [event.reviewed_at for event in events]
    if timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
        raise AuthorityContractError("review events must have strictly increasing aware timestamps")
    state = ReviewStatus(candidate.status.value)
    context = validate_authority_source_decisions(root)
    catalog_parent = validate_frozen_catalog_parent(catalog_parent_payload)
    catalog_sha256 = content_sha256(catalog_parent.model_dump(mode="json"))
    product = _fresh(CanonicalProductRecord, catalog_record) if catalog_record is not None else None
    proposal: CatalogRecordProposal | None = None
    if candidate.catalog_lookup_state == CatalogLookupState.catalog_review_required:
        if approved_catalog_proposal is None:
            raise AuthorityContractError(
                "a missing UUID requires a separately approved catalog proposal"
            )
        proposal = validate_catalog_record_proposal(
            approved_catalog_proposal,
            root=root,
            candidate_payload=candidate,
            catalog_parent_payload=catalog_parent,
        )
        if proposal.review_status != CatalogProposalStatus.approved:
            raise AuthorityContractError(
                "a missing UUID requires a separately approved catalog proposal"
            )
        product = proposal.proposed_product_record
    elif approved_catalog_proposal is not None:
        raise AuthorityContractError("an existing catalog UUID must not use a creation proposal")
    if product is None:
        raise AuthorityContractError("review chain requires the frozen catalog product record")
    if candidate.catalog_lookup_state == CatalogLookupState.existing_uuid:
        _require_catalog_membership(product, candidate, catalog_parent)
    expected_uuid = product.canonical_uuid
    if candidate.canonical_uuid is not None and candidate.canonical_uuid != expected_uuid:
        raise AuthorityContractError("candidate UUID differs from the frozen catalog record")
    _validate_product_candidate_identity(product, candidate)
    for event in events:
        if event.candidate_id != candidate.candidate_id:
            raise AuthorityContractError("review event belongs to another candidate")
        if event.from_status != state:
            raise AuthorityContractError("review event chain is not append-only from prior state")
        if event.packet_sha256 != expected_packet_sha256:
            raise AuthorityContractError("review event packet checksum is stale")
        if event.catalog_version != catalog_parent.catalog_version:
            raise AuthorityContractError("review event catalog version is stale")
        if event.catalog_sha256 != catalog_sha256:
            raise AuthorityContractError("review event catalog checksum is stale")
        if event.canonical_uuid is not None and event.canonical_uuid != expected_uuid:
            raise AuthorityContractError("review event UUID differs from the frozen catalog record")
        expected_record_sha = content_sha256(product.model_dump(mode="json"))
        if (
            event.catalog_record_sha256 is not None
            and event.catalog_record_sha256 != expected_record_sha
        ):
            raise AuthorityContractError("review event catalog record checksum is stale")
        for evidence in event.variant_field_evidence:
            _validate_evidence_for_candidate(evidence, candidate, context)
        if event.to_status == ReviewStatus.approved_exact:
            _require_complete_agreeing_evidence(product, event.variant_field_evidence)
        raw_attestation = attestations.get(event.event_id)
        if raw_attestation is None:
            raise AuthorityContractError("every review event requires an owner attestation")
        attestation = _fresh(OwnerAttestation, raw_attestation)
        if event.attestation_sha256 != content_sha256(attestation.model_dump(mode="json")):
            raise AuthorityContractError("review event attestation checksum is stale")
        if (
            attestation.candidate_id != event.candidate_id
            or attestation.packet_sha256 != event.packet_sha256
            or attestation.catalog_version != event.catalog_version
            or attestation.catalog_sha256 != event.catalog_sha256
            or attestation.catalog_record_sha256 != event.catalog_record_sha256
            or attestation.outcome != event.to_status
            or attestation.reviewed_at != event.reviewed_at
            or attestation.review_reason != event.review_reason
        ):
            raise AuthorityContractError("owner attestation does not bind the review event")
        state = event.to_status
    if set(attestations) != set(event_ids):
        raise AuthorityContractError("attestation set must cover review events exactly once")
    return events


def validate_authority_bundle(
    bundle_payload: AuthorityBundle | Mapping[str, Any],
    manifest_payload: AuthorityBundleManifest | Mapping[str, Any],
    *,
    root: Path,
    candidate_payloads: Mapping[str, AuthorityCandidate | Mapping[str, Any]],
    catalog_records: Mapping[str, CanonicalProductRecord | Mapping[str, Any]],
    catalog_proposals: Mapping[str, CatalogRecordProposal | Mapping[str, Any]],
    review_events: Sequence[AuthorityReviewEvent | Mapping[str, Any]],
    attestations: Mapping[str, OwnerAttestation | Mapping[str, Any]],
    packet_sha256s: Mapping[str, str],
    catalog_parent_payload: FrozenCatalogParent | Mapping[str, Any],
) -> tuple[AuthorityBundle, AuthorityBundleManifest]:
    """Revalidate every parent, then recompute revocation, composition and the 20/4 Gate."""

    bundle = _fresh(AuthorityBundle, bundle_payload)
    manifest = _fresh(AuthorityBundleManifest, manifest_payload)
    context = validate_authority_source_decisions(root)
    catalog_parent = validate_frozen_catalog_parent(catalog_parent_payload)
    expected_catalog_sha256 = content_sha256(catalog_parent.model_dump(mode="json"))
    if manifest.bundle_version != bundle.bundle_version:
        raise AuthorityContractError("bundle version differs from its manifest")
    if manifest.authority_bundle_sha256 != content_sha256(bundle.model_dump(mode="json")):
        raise AuthorityContractError("authority bundle checksum is stale")
    if manifest.catalog_version != catalog_parent.catalog_version:
        raise AuthorityContractError("bundle manifest catalog version is stale")
    if manifest.catalog_sha256 != expected_catalog_sha256:
        raise AuthorityContractError("bundle manifest catalog checksum is stale")
    if manifest.source_decision_sha256s != [context.source_decisions_sha256]:
        raise AuthorityContractError("bundle manifest source-decision checksum is stale")

    records_by_candidate = {record.candidate_id: record for record in bundle.records}
    candidate_ids = set(records_by_candidate)
    if set(candidate_payloads) != candidate_ids:
        raise AuthorityContractError("bundle requires exactly one candidate artifact per record")
    candidates = {
        candidate_id: validate_authority_candidate(payload, root=root)
        for candidate_id, payload in candidate_payloads.items()
    }
    if any(candidate.candidate_id != key for key, candidate in candidates.items()):
        raise AuthorityContractError("candidate artifact map key differs from candidate_id")
    expected_existing = {
        candidate_id
        for candidate_id, candidate in candidates.items()
        if candidate.catalog_lookup_state == CatalogLookupState.existing_uuid
    }
    expected_proposals = candidate_ids - expected_existing
    if set(catalog_records) != expected_existing or set(catalog_proposals) != expected_proposals:
        raise AuthorityContractError(
            "catalog record/proposal inputs do not match candidate lookup states"
        )

    events = tuple(_fresh(AuthorityReviewEvent, event) for event in review_events)
    canonical_events = tuple(
        sorted(events, key=lambda event: (event.candidate_id, event.reviewed_at, event.event_id))
    )
    if events != canonical_events:
        raise AuthorityContractError(
            "bundle review events must use canonical candidate/time/event ordering"
        )
    grouped_events: defaultdict[str, list[AuthorityReviewEvent]] = defaultdict(list)
    event_ids: set[str] = set()
    for event in events:
        if event.event_id in event_ids:
            raise AuthorityContractError("bundle review events contain duplicate event IDs")
        event_ids.add(event.event_id)
        grouped_events[event.candidate_id].append(event)
    if set(grouped_events) != candidate_ids:
        raise AuthorityContractError("bundle records and review-event candidates differ")
    for record in bundle.records:
        chain = grouped_events[record.candidate_id]
        chain_event_ids = {event.event_id for event in chain}
        chain_attestations = {
            event_id: payload
            for event_id, payload in attestations.items()
            if event_id in chain_event_ids
        }
        candidate = candidates[record.candidate_id]
        validated_chain = validate_review_event_chain(
            candidate,
            chain,
            root=root,
            catalog_record=catalog_records.get(record.candidate_id),
            approved_catalog_proposal=catalog_proposals.get(record.candidate_id),
            attestations=chain_attestations,
            expected_packet_sha256=packet_sha256s.get(record.candidate_id, ""),
            catalog_parent_payload=catalog_parent,
        )
        latest = validated_chain[-1]
        product = (
            _fresh(CanonicalProductRecord, catalog_records[record.candidate_id])
            if record.candidate_id in catalog_records
            else _fresh(
                CatalogRecordProposal, catalog_proposals[record.candidate_id]
            ).proposed_product_record
        )
        if (
            latest.event_id != record.latest_event_id
            or latest.to_status != record.status
            or latest.canonical_uuid != record.canonical_uuid
            or latest.catalog_version != record.catalog_version
            or latest.catalog_record_sha256 != record.catalog_record_sha256
            or record.family_group_key != candidate.family_group_key
            or record.release_key != candidate.proposed_release_key
            or record.family_group_key != product.family_group_key
            or record.release_key != product.release_key
            or record.source_decision_ids != latest.source_decision_ids
        ):
            raise AuthorityContractError("bundle record does not match its latest review event")
        evidence_sha256s = sorted(
            content_sha256(evidence.model_dump(mode="json"))
            for evidence in latest.variant_field_evidence
        )
        if record.evidence_sha256s != evidence_sha256s:
            raise AuthorityContractError(
                "bundle evidence checksums do not match the complete latest event evidence"
            )

    if set(attestations) != event_ids:
        raise AuthorityContractError("bundle attestation set must cover review events exactly once")
    if set(packet_sha256s) != candidate_ids:
        raise AuthorityContractError("bundle packet checksums must cover candidates exactly once")

    expected_parents = authority_bundle_parent_artifacts(
        root=root,
        candidate_payloads=candidate_payloads,
        catalog_records=catalog_records,
        catalog_proposals=catalog_proposals,
        review_events=review_events,
        attestations=attestations,
        packet_sha256s=packet_sha256s,
        catalog_parent_payload=catalog_parent,
    )
    if manifest.ordered_parent_artifacts != expected_parents:
        raise AuthorityContractError("bundle manifest parents do not match the complete input set")

    actual_counts = Counter(record.status for record in bundle.records)
    expected_counts = {status: actual_counts[status] for status in ReviewStatus}
    if manifest.counts_by_status != expected_counts:
        raise AuthorityContractError("manifest status counts do not match bundle records")

    approved = [record for record in bundle.records if record.status == ReviewStatus.approved_exact]
    if manifest.approved_distinct_variant_count != len(approved):
        raise AuthorityContractError("approved distinct count does not match eligible bundle rows")
    release_identities = [(record.family_group_key, record.release_key) for record in approved]
    if len(release_identities) != len(set(release_identities)):
        raise AuthorityContractError("aliases cannot repeat one family/release identity")
    approved_evidence = [sha for record in approved for sha in record.evidence_sha256s]
    if len(approved_evidence) != len(set(approved_evidence)):
        raise AuthorityContractError("repeated evidence cannot pad approved exact counts")
    releases: defaultdict[str, set[str]] = defaultdict(set)
    for record in approved:
        releases[record.family_group_key].add(record.release_key)
    expected_families = [
        FamilyComposition(
            family_group_key=family,
            release_keys=sorted(keys),
            approved_variant_count=len(keys),
        )
        for family, keys in sorted(releases.items())
        if len(keys) >= 2
    ]
    if manifest.family_composition != expected_families:
        raise AuthorityContractError("family composition does not match distinct approved releases")
    if manifest.qualifying_family_count != len(expected_families):
        raise AuthorityContractError("qualifying family count is stale")

    variant_shortfall = max(0, 20 - len(approved))
    family_shortfall = max(0, 4 - len(expected_families))
    if manifest.shortfalls != AuthorityShortfalls(
        exact_variant_shortfall=variant_shortfall,
        qualifying_family_shortfall=family_shortfall,
    ):
        raise AuthorityContractError("authority shortfalls were not recomputed")
    expected_gate = (
        "eligible_for_rhb_t4_reaudit"
        if variant_shortfall == 0 and family_shortfall == 0
        else "blocked_insufficient_exact_authority"
    )
    if manifest.gate_status != expected_gate:
        raise AuthorityContractError("authority Gate result is inconsistent with 20/4 composition")
    return bundle, manifest


def authority_bundle_parent_artifacts(
    *,
    root: Path,
    candidate_payloads: Mapping[str, AuthorityCandidate | Mapping[str, Any]],
    catalog_records: Mapping[str, CanonicalProductRecord | Mapping[str, Any]],
    catalog_proposals: Mapping[str, CatalogRecordProposal | Mapping[str, Any]],
    review_events: Sequence[AuthorityReviewEvent | Mapping[str, Any]],
    attestations: Mapping[str, OwnerAttestation | Mapping[str, Any]],
    packet_sha256s: Mapping[str, str],
    catalog_parent_payload: FrozenCatalogParent | Mapping[str, Any],
) -> list[ArtifactDigest]:
    """Return the exact deterministic parent set required by a bundle manifest."""

    candidates = {
        key: _fresh(AuthorityCandidate, value).model_dump(mode="json")
        for key, value in sorted(candidate_payloads.items())
    }
    records = {
        key: _fresh(CanonicalProductRecord, value).model_dump(mode="json")
        for key, value in sorted(catalog_records.items())
    }
    proposals = {
        key: _fresh(CatalogRecordProposal, value).model_dump(mode="json")
        for key, value in sorted(catalog_proposals.items())
    }
    event_rows = [
        _fresh(AuthorityReviewEvent, event).model_dump(mode="json") for event in review_events
    ]
    attestation_rows = {
        key: _fresh(OwnerAttestation, value).model_dump(mode="json")
        for key, value in sorted(attestations.items())
    }
    catalog_parent = validate_frozen_catalog_parent(catalog_parent_payload)
    parents: dict[str, Any] = {
        "authority-candidates.json": candidates,
        "catalog-parent.json": catalog_parent.model_dump(mode="json"),
        "catalog-records-and-proposals.json": {
            "catalog_records": records,
            "catalog_proposals": proposals,
        },
        "owner-attestations.json": attestation_rows,
        "owner-packet-sha256s.json": dict(sorted(packet_sha256s.items())),
        "review-events.json": event_rows,
        "source-decisions.json": load_json(root.resolve() / DECISIONS_PATH),
    }
    return [
        ArtifactDigest(reference=reference, sha256=content_sha256(payload))
        for reference, payload in sorted(parents.items())
    ]


def _validate_binding(binding: SourceRecordBinding, context: ApprovedSourceContext) -> None:
    binding = _fresh(SourceRecordBinding, binding)
    if binding.source_id != context.source_id:
        raise AuthorityContractError("source binding is not CAR-T1 approved")
    if binding.normalized_snapshot_sha256 != context.normalized_snapshot_sha256:
        raise AuthorityContractError("source binding checksum is stale")
    if binding.source_record_id not in context.source_record_ids:
        raise AuthorityContractError("source record is outside the approved 100-row membership set")


def _validate_product_candidate_identity(
    product: CanonicalProductRecord, candidate: AuthorityCandidate
) -> None:
    if product.family_group_key != candidate.family_group_key:
        raise AuthorityContractError("catalog product family differs from the candidate family")
    if product.release_key != candidate.proposed_release_key:
        raise AuthorityContractError("catalog product release differs from the candidate release")


def _require_catalog_membership(
    product: CanonicalProductRecord,
    candidate: AuthorityCandidate,
    catalog_parent: FrozenCatalogParent,
) -> FrozenCatalogProduct:
    member = next(
        (
            item
            for item in catalog_parent.products
            if item.canonical_uuid == candidate.canonical_uuid
        ),
        None,
    )
    if member is None:
        raise AuthorityContractError("candidate UUID is not a member of the frozen catalog parent")
    if member.record != product:
        raise AuthorityContractError("catalog record differs from the frozen catalog parent member")
    expected_sha = content_sha256(product.model_dump(mode="json"))
    if member.record_sha256 != expected_sha:
        raise AuthorityContractError("catalog record hash differs from its frozen parent member")
    return member


def _validate_evidence_for_candidate(
    evidence: VariantFieldEvidence,
    candidate: AuthorityCandidate,
    context: ApprovedSourceContext,
) -> None:
    evidence = _fresh(VariantFieldEvidence, evidence)
    candidate_record_id = candidate.source_binding.source_record_id
    binding_ids = {binding.source_record_id for binding in evidence.source_bindings}
    if binding_ids != {candidate_record_id}:
        raise AuthorityContractError(
            "CAR-v1 field evidence must bind exactly the candidate source record"
        )
    for binding in evidence.source_bindings:
        _validate_binding(binding, context)
    source_value = context.source_records[candidate_record_id][evidence.source_field.value]
    expected_reviewed: FieldValue = (
        [source_value]
        if evidence.field == VariantField.identifiers and isinstance(source_value, str)
        else source_value
    )
    if _normalized_value(evidence.reviewed_value) != _normalized_value(expected_reviewed):
        raise AuthorityContractError(
            f"reviewed value does not match candidate source row for {evidence.field.value}"
        )


def _required_fields(record: CanonicalProductRecord) -> set[VariantField]:
    return {field for field, value in _product_field_values(record).items() if not _is_empty(value)}


def _require_canonical_evidence_order(
    evidence_rows: Sequence[VariantFieldEvidence],
) -> None:
    """Require the declared VariantField order for every hash-bearing evidence list."""

    field_order = {field: index for index, field in enumerate(VariantField)}
    fields = [row.field for row in evidence_rows]
    if len(fields) != len(set(fields)):
        raise ValueError("field evidence must contain unique catalog fields")
    if fields != sorted(fields, key=field_order.__getitem__):
        raise ValueError("field evidence must follow canonical VariantField order")


def _product_field_values(record: CanonicalProductRecord) -> Mapping[VariantField, FieldValue]:
    return {
        VariantField.casting: record.casting,
        VariantField.release_year: record.release_year,
        VariantField.series: record.series,
        VariantField.color: record.color,
        VariantField.collector_number: record.collector_number,
        VariantField.series_position: record.series_position,
        VariantField.edition: record.edition,
        VariantField.identifiers: record.identifiers,
    }


def _require_complete_agreeing_evidence(
    record: CanonicalProductRecord, evidence_rows: Sequence[VariantFieldEvidence]
) -> None:
    reparsed = [_fresh(VariantFieldEvidence, row) for row in evidence_rows]
    _require_canonical_evidence_order(reparsed)
    fields = [row.field for row in reparsed]
    if len(fields) != len(set(fields)):
        raise AuthorityContractError("field evidence cannot contain duplicate catalog fields")
    expected = _required_fields(record)
    if set(fields) != expected:
        missing = sorted(field.value for field in expected - set(fields))
        extra = sorted(field.value for field in set(fields) - expected)
        raise AuthorityContractError(
            f"field evidence coverage differs; missing={missing}, extra={extra}"
        )
    record_values = _product_field_values(record)
    for row in reparsed:
        if row.agreement != EvidenceAgreement.agrees:
            raise AuthorityContractError("complete authority evidence must agree field by field")
        if _normalized_value(row.catalog_value) != _normalized_value(record_values[row.field]):
            raise AuthorityContractError(f"evidence catalog value is stale for {row.field.value}")


def _normalized_value(value: FieldValue) -> str | int | tuple[str, ...] | None:
    if isinstance(value, list):
        return tuple(value)
    return value


def _reject_preconstructed_extras(value: Any, *, path: str = "artifact") -> None:
    if isinstance(value, BaseModel):
        unknown = set(value.__dict__) - set(type(value).model_fields)
        extra = value.__pydantic_extra__ or {}
        if unknown or extra:
            names = sorted(unknown | set(extra))
            raise AuthorityContractError(
                f"{path} contains undeclared preconstructed fields: {names}"
            )
        for field, child in value.__dict__.items():
            _reject_preconstructed_extras(child, path=f"{path}.{field}")
    elif isinstance(value, Mapping):
        for key, child in value.items():
            _reject_preconstructed_extras(child, path=f"{path}.{key}")
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for index, child in enumerate(value):
            _reject_preconstructed_extras(child, path=f"{path}[{index}]")


def _is_empty(value: FieldValue) -> bool:
    return value is None or value == "" or value == []


def _reject_unsafe_reference(value: str) -> None:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value or "\x00" in value:
        raise ValueError("artifact reference is absolute or contains path traversal")
    _reject_pii(value, context="artifact reference")


def _reject_pii(value: str, *, context: str) -> None:
    if EMAIL_RE.search(value):
        raise AuthorityContractError(f"{context} contains email-like personal information")
    without_urls = URL_RE.sub("", value)
    phone_match = PHONE_RE.search(without_urls)
    if phone_match is not None and len(re.sub(r"\D", "", phone_match.group())) >= 10:
        raise AuthorityContractError(f"{context} contains phone-like personal information")
    if CREDENTIAL_RE.search(value):
        raise AuthorityContractError(f"{context} contains credential-like private information")
    if ACCOUNT_RE.search(value):
        raise AuthorityContractError(f"{context} contains seller/account identity")
    if ADDRESS_RE.search(value):
        raise AuthorityContractError(f"{context} contains address-like personal information")


def _reject_pii_tree(value: Any, *, context: str) -> None:
    if isinstance(value, str):
        _reject_pii(value, context=context)
    elif isinstance(value, Mapping):
        for key, child in value.items():
            _reject_pii(str(key), context=context)
            _reject_pii_tree(child, context=context)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for child in value:
            _reject_pii_tree(child, context=context)


__all__ = [
    "ApprovedSourceContext",
    "ArtifactDigest",
    "AuthorityBundle",
    "AuthorityBundleManifest",
    "AuthorityBundleRecord",
    "AuthorityCandidate",
    "AuthorityContractError",
    "AuthorityReviewEvent",
    "AuthorityReviewEventV2",
    "AuthorityShortfalls",
    "BatchOwnerAuthorization",
    "CanonicalProductRecord",
    "CatalogRecordProposal",
    "CatalogResolutionBinding",
    "EvidenceAgreement",
    "ExpectedBatchOwnerAuthorization",
    "FamilyComposition",
    "FrozenCatalogParent",
    "FrozenCatalogProduct",
    "OwnerAttestation",
    "OwnerAttestationV2",
    "OwnerReviewPacket",
    "ReviewStatus",
    "SourceRecordBinding",
    "VariantField",
    "VariantFieldEvidence",
    "authority_bundle_parent_artifacts",
    "content_sha256",
    "stable_json_bytes",
    "validate_authority_bundle",
    "validate_authority_candidate",
    "validate_authority_source_decisions",
    "validate_batch_owner_authorization",
    "validate_catalog_record_proposal",
    "validate_field_evidence",
    "validate_frozen_catalog_parent",
    "validate_owner_review_packet",
    "validate_review_event_chain",
]
