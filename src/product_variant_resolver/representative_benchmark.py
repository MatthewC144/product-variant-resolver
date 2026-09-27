"""Strict offline contracts for the representative hard benchmark.

This module is deliberately separate from the resolver runtime.  It validates the
provenance, authority, label-blindness, ordering, and checksum boundaries used by
the benchmark artifacts; it never performs collection, retrieval, or HTTP work.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Annotated, Any, Literal, NoReturn
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, PrivateAttr, model_validator

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d ().-]{7,}\d)(?!\d)")
URL_RE = re.compile(r"\b[a-z][a-z0-9+.-]*://\S+", re.IGNORECASE)
FORBIDDEN_RAW_FIELD_PARTS = (
    "expected",
    "target",
    "correct",
    "metric",
    "winner",
    "quality_gate",
    "gold",
    "label",
)

Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
NonBlank = Annotated[str, Field(min_length=1)]


class ContractError(ValueError):
    """Raised when a benchmark artifact fails a cross-artifact invariant."""


class StrictContract(BaseModel):
    """Base class that rejects undeclared data instead of silently dropping it."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SourceKind(str, Enum):
    synthetic_fixture = "synthetic_fixture"
    owner_scan = "owner_scan"
    owner_export = "owner_export"
    licensed_text_derivative = "licensed_text_derivative"
    authorized_export = "authorized_export"
    other = "other"


class PermissionStatus(str, Enum):
    approved = "approved"
    blocked = "blocked"
    unknown = "unknown"
    not_applicable = "not_applicable"


class LicenseStatus(str, Enum):
    approved = "approved"
    blocked = "blocked"
    unknown = "unknown"


class RetentionScope(str, Enum):
    prohibited = "prohibited"
    local_only = "local_only"
    public = "public"


class RedistributionScope(str, Enum):
    prohibited = "prohibited"
    aggregate_only = "aggregate_only"
    public_rows = "public_rows"


class PrivacyStatus(str, Enum):
    approved = "approved"
    blocked = "blocked"
    pending = "pending"


class BenchmarkUse(str, Enum):
    query_provenance = "query_provenance"
    family_context = "family_context"
    exact_variant_authority = "exact_variant_authority"
    negative_control = "negative_control"
    none = "none"


class OwnerDecision(str, Enum):
    approved = "approved"
    rejected = "rejected"
    pending = "pending"


class PublicationScope(str, Enum):
    public = "public"
    local_only = "local_only"
    aggregate_only = "aggregate_only"


class RowPublicationScope(str, Enum):
    """Publication choices for artifacts that contain individual human-authored rows."""

    public = "public"
    local_only = "local_only"


class AuthorityEligibility(str, Enum):
    """Machine-enforced source eligibility for exact canonical authority."""

    prohibited = "prohibited"
    synthetic_regression_only = "synthetic_regression_only"
    exact_variant_authority_candidate = "exact_variant_authority_candidate"


class AuthorityEvidenceLevel(str, Enum):
    none = "none"
    family_only = "family_only"
    staging_only = "staging_only"
    synthetic_only = "synthetic_only"
    independent_exact_variant = "independent_exact_variant"


class RightsEvidence(StrictContract):
    status: NonBlank
    evidence: list[NonBlank]
    limitations: list[NonBlank]


class OwnerDecisionMetadata(StrictContract):
    current_use: NonBlank
    privacy_risk: NonBlank
    unresolved_conditions: list[NonBlank]
    benchmark_use: str | None = None
    representative_pilot_use: str | None = None
    new_collection: str | None = None


class SourceInventoryEntry(StrictContract):
    """One source with independent permission, use, and publication boundaries."""

    source_id: NonBlank
    source_kind: SourceKind
    origin_reference: NonBlank
    acquisition_method: NonBlank
    local_sha256: Sha256 | None
    access_permission_status: PermissionStatus
    content_license_status: LicenseStatus
    retention_scope: RetentionScope
    redistribution_scope: RedistributionScope
    privacy_review_status: PrivacyStatus
    benchmark_uses: list[BenchmarkUse] = Field(min_length=1)
    evidence_refs: list[NonBlank]
    owner_decision: OwnerDecision
    owner_decision_metadata: OwnerDecisionMetadata
    current_repository_state: NonBlank
    current_publication_state: NonBlank
    known_rights_evidence: RightsEvidence
    prospective_benchmark_use_status: NonBlank
    prospective_redistribution_status: NonBlank
    record_count: int = Field(ge=0)
    record_count_kind: NonBlank
    authority_eligibility: AuthorityEligibility
    authority_evidence_level: AuthorityEvidenceLevel
    authority_boundary: NonBlank

    @model_validator(mode="after")
    def source_boundaries_are_coherent(self) -> SourceInventoryEntry:
        uses = set(self.benchmark_uses)
        if BenchmarkUse.none in uses and len(uses) != 1:
            raise ValueError("benchmark use 'none' cannot be combined with another use")
        if self.retention_scope == RetentionScope.prohibited and self.local_sha256 is not None:
            raise ValueError("a prohibited source cannot claim a retained local artifact")
        if (
            self.redistribution_scope == RedistributionScope.public_rows
            and self.retention_scope != RetentionScope.public
        ):
            raise ValueError("public rows require public retention scope")
        if self.authority_eligibility == AuthorityEligibility.exact_variant_authority_candidate:
            if self.source_kind != SourceKind.authorized_export:
                raise ValueError(
                    "exact authority candidates must be new, explicit authorized_export sources"
                )
            if self.authority_evidence_level != AuthorityEvidenceLevel.independent_exact_variant:
                raise ValueError(
                    "exact authority candidates require independent exact-variant evidence"
                )
            if BenchmarkUse.exact_variant_authority not in uses:
                raise ValueError("exact authority candidates require exact_variant_authority use")
        elif self.authority_evidence_level == AuthorityEvidenceLevel.independent_exact_variant:
            raise ValueError(
                "independent exact-variant evidence requires candidate authority eligibility"
            )
        if (
            BenchmarkUse.exact_variant_authority in uses
            and self.authority_eligibility != AuthorityEligibility.exact_variant_authority_candidate
        ):
            raise ValueError("ineligible sources cannot declare exact_variant_authority use")
        if self.source_kind == SourceKind.synthetic_fixture and self.authority_eligibility not in {
            AuthorityEligibility.prohibited,
            AuthorityEligibility.synthetic_regression_only,
        }:
            raise ValueError("synthetic fixtures cannot become exact authority candidates")
        if self.owner_decision == OwnerDecision.approved:
            if self.owner_decision_metadata.unresolved_conditions:
                raise ValueError("an approved source cannot retain unresolved conditions")
            if self.privacy_review_status != PrivacyStatus.approved:
                raise ValueError("an approved source requires approved privacy review")
            if self.access_permission_status not in {
                PermissionStatus.approved,
                PermissionStatus.not_applicable,
            }:
                raise ValueError("an approved source requires access permission")
            if self.content_license_status != LicenseStatus.approved:
                raise ValueError("an approved source requires an approved content license")
        return self


class AlignmentSummary(StrictContract):
    exact_canonical: int = Field(ge=0)
    family_only: int = Field(ge=0)
    unmapped: int = Field(ge=0)


class SourceInventory(StrictContract):
    schema_version: Literal["pvr-representative-hard-benchmark-source-inventory-v1"]
    inventory_version: NonBlank
    baseline_date: NonBlank
    network_collection_performed: Literal[False]
    private_source_rows_copied: Literal[False]
    owner_source_gate: NonBlank
    alignment_summary: AlignmentSummary
    entries: list[SourceInventoryEntry] = Field(min_length=1)

    @model_validator(mode="after")
    def source_ids_are_unique_and_ordered(self) -> SourceInventory:
        source_ids = [entry.source_id for entry in self.entries]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source IDs must be unique")
        return self


class SourceDecisionStatus(str, Enum):
    approved = "approved"
    rejected = "rejected"
    held = "held"


class SourceDecisionScope(str, Enum):
    prohibited = "prohibited"
    local_only = "local_only"
    aggregate_only = "aggregate_only"
    public_rows = "public_rows"


class SourceDecisionUse(str, Enum):
    query_text = "query_text"
    evidence_retention = "evidence_retention"
    reviewer_identity = "reviewer_identity"
    local_only_benchmark_use = "local_only_benchmark_use"
    public_git_artifacts = "public_git_artifacts"
    exact_variant_authority = "exact_variant_authority"


class SourceDecisionOrigin(str, Enum):
    inventory = "inventory"
    blocked_external = "blocked_external"


class SourceDownstreamPermission(str, Enum):
    query_pack = "query_pack"
    scored_labels = "scored_labels"
    family_context = "family_context"
    canonical_authority = "canonical_authority"
    regression_only = "regression_only"
    none = "none"


class SourceAllowedLabelStatus(str, Enum):
    matched = "matched"
    ambiguous = "ambiguous"
    no_match = "no_match"


class SourceCollectionStatus(str, Enum):
    existing_repository_fixture_only = "existing_repository_fixture_only"
    existing_rows_only_no_new_collection = "existing_rows_only_no_new_collection"
    derived_existing_rows_only = "derived_existing_rows_only"
    owner_local_rows_untracked = "owner_local_rows_untracked"
    existing_revision_bound_derivative_only = "existing_revision_bound_derivative_only"
    no_source_specific_permission_no_collection = "no_source_specific_permission_no_collection"


PUBLIC_AGGREGATE_FIELDS = frozenset(
    {
        "schema",
        "sha256",
        "record_count",
        "non_sensitive_aggregate",
        "non_sensitive_summary",
        "reviewer_role",
    }
)
SENSITIVE_FIELD_PARTS = (
    "seller",
    "contact",
    "account",
    "email",
    "phone",
    "personal_name",
    "pii",
)


class SourceDecisionCell(StrictContract):
    use: SourceDecisionUse
    status: SourceDecisionStatus
    effective_publication_scope: SourceDecisionScope
    owner_confirmation_required: bool
    owner_confirmed: bool
    allowed_fields: list[NonBlank]
    conditions: list[NonBlank] = Field(min_length=1)

    @model_validator(mode="after")
    def decision_cell_is_fail_closed(self) -> SourceDecisionCell:
        if self.status in {SourceDecisionStatus.rejected, SourceDecisionStatus.held}:
            if self.effective_publication_scope != SourceDecisionScope.prohibited:
                raise ValueError("rejected/held decisions must prohibit publication")
            if self.allowed_fields:
                raise ValueError("rejected/held decisions cannot retain allowed fields")
        elif not self.allowed_fields:
            raise ValueError("approved decisions require explicit allowed fields")
        if self.owner_confirmation_required and not self.owner_confirmed:
            raise ValueError("owner-confirmed decisions cannot retain an unanswered cell")
        if self.owner_confirmed and not self.owner_confirmation_required:
            raise ValueError("a cell cannot claim confirmation that was not required")
        normalized_fields = {field.casefold() for field in self.allowed_fields}
        if len(normalized_fields) != len(self.allowed_fields):
            raise ValueError("allowed fields must be unique")
        if self.effective_publication_scope == SourceDecisionScope.aggregate_only:
            unknown = normalized_fields - PUBLIC_AGGREGATE_FIELDS
            if unknown:
                raise ValueError(
                    "aggregate-only publication contains row-level or undeclared fields: "
                    + ", ".join(sorted(unknown))
                )
        if self.effective_publication_scope in {
            SourceDecisionScope.aggregate_only,
            SourceDecisionScope.public_rows,
        }:
            _reject_obvious_pii(
                [*self.allowed_fields, *self.conditions],
                context=f"source-decision {self.use.value}",
            )
            sensitive = sorted(
                field
                for field in normalized_fields
                if any(part in field for part in SENSITIVE_FIELD_PARTS)
            )
            if sensitive:
                raise ValueError(
                    "public/aggregate decisions cannot allow personal-information fields: "
                    + ", ".join(sensitive)
                )
        return self


class SourceRecordRefContract(StrictContract):
    source_file: Literal["data/external/hot-wheels-wiki/pilot-2025/normalized.json"]
    source_file_sha256: Sha256
    source_record_count: Literal[100]
    source_record_id_field: Literal["source_record_id"]
    source_revision_id: Literal[790665]


class SourceDecisionEntry(StrictContract):
    source_id: NonBlank
    source_origin: SourceDecisionOrigin
    authority_eligibility: AuthorityEligibility
    collection_status: SourceCollectionStatus
    downstream_permissions: list[SourceDownstreamPermission] = Field(min_length=1)
    allowed_label_statuses: list[SourceAllowedLabelStatus]
    record_ref_contract: SourceRecordRefContract | None = None
    decisions: list[SourceDecisionCell]

    @model_validator(mode="after")
    def uses_are_complete_and_unique(self) -> SourceDecisionEntry:
        uses = [decision.use for decision in self.decisions]
        expected = set(SourceDecisionUse)
        if len(uses) != len(expected) or set(uses) != expected:
            raise ValueError("each source must declare every source-decision use exactly once")
        permissions = set(self.downstream_permissions)
        if len(permissions) != len(self.downstream_permissions):
            raise ValueError("downstream permissions must be unique")
        if SourceDownstreamPermission.none in permissions and len(permissions) != 1:
            raise ValueError("downstream permission 'none' cannot be combined")
        statuses = set(self.allowed_label_statuses)
        if len(statuses) != len(self.allowed_label_statuses):
            raise ValueError("allowed label statuses must be unique")
        if statuses and SourceDownstreamPermission.scored_labels not in permissions:
            raise ValueError("label statuses require scored_labels downstream permission")
        if SourceDownstreamPermission.scored_labels in permissions and not statuses:
            raise ValueError("scored_labels permission requires explicit allowed statuses")
        return self


class SourceDecisionPolicy(StrictContract):
    status_enum: list[SourceDecisionStatus]
    publication_scope_enum: list[SourceDecisionScope]
    uses: list[SourceDecisionUse]
    owner_confirmation_rule: NonBlank
    network_rule: NonBlank

    @model_validator(mode="after")
    def declared_enums_match_the_contract(self) -> SourceDecisionPolicy:
        if self.status_enum != list(SourceDecisionStatus):
            raise ValueError("declared source-decision statuses are incomplete or reordered")
        if self.publication_scope_enum != list(SourceDecisionScope):
            raise ValueError("declared publication scopes are incomplete or reordered")
        if self.uses != list(SourceDecisionUse):
            raise ValueError("declared source-decision uses are incomplete or reordered")
        return self


class ReviewerIdentityPolicy(StrictContract):
    public_identity_mode: Literal["role_only"]
    reviewer_role: Literal["project_owner"]
    personal_name_allowed: Literal[False]
    contact_or_account_data_allowed: Literal[False]


class SourceDecisionArtifact(StrictContract):
    _wiki_source_record_refs: frozenset[str] = PrivateAttr(default_factory=frozenset)

    schema_version: Literal["pvr-representative-hard-benchmark-source-decisions-v1"]
    decision_version: Literal["representative-hard-benchmark-source-decisions-owner-confirmed-v1"]
    decision_stage: Literal["owner_confirmed"]
    owner_review_status: Literal["approved_for_declared_scopes"]
    owner_confirmed_by: Literal["project_owner"]
    owner_confirmed_at: AwareDatetime
    inventory_version: NonBlank
    inventory_sha256: Sha256
    network_collection_authorized: Literal[False]
    decision_policy: SourceDecisionPolicy
    reviewer_identity_policy: ReviewerIdentityPolicy
    sources: list[SourceDecisionEntry] = Field(min_length=1)
    gate_result: Literal["passed_for_approved_scopes"]
    next_allowed_step: Literal["RHB_T4_catalog_ground_truth_eligibility_audit"]
    prohibited_next_steps: list[NonBlank]

    @property
    def wiki_source_record_refs(self) -> frozenset[str]:
        """Exact record IDs derived from the checksum-validated Wiki revision."""

        return self._wiki_source_record_refs

    @model_validator(mode="after")
    def gate_is_complete_and_source_ids_are_unique(self) -> SourceDecisionArtifact:
        source_ids = [source.source_id for source in self.sources]
        if len(source_ids) != len(set(source_ids)):
            raise ValueError("source-decision source IDs must be unique")
        if any(
            decision.status == SourceDecisionStatus.held
            for source in self.sources
            for decision in source.decisions
        ):
            raise ValueError("a passed source Gate cannot contain held decisions")
        required_prohibitions = {
            "network_collection",
            "query_pack_authoring",
            "label_authoring",
            "RHB_T5",
        }
        if set(self.prohibited_next_steps) != required_prohibitions:
            raise ValueError("passed Gate must retain the exact downstream prohibitions")
        return self


class ArtifactDigest(StrictContract):
    path: NonBlank
    sha256: Sha256


class RepositoryTrackingContract(StrictContract):
    artifacts: list[ArtifactDigest]
    owner_private_rows: Literal["untracked_and_not_copied"]
    state: Literal["tracked_public_repository"]


class SourceInventoryManifest(StrictContract):
    schema_version: Literal["pvr-representative-hard-benchmark-source-inventory-manifest-v1"]
    inventory_version: NonBlank
    baseline_date: NonBlank
    generator: NonBlank
    inventory_file: Literal["source-inventory.json"]
    inventory_sha256: Sha256
    source_entry_count: int = Field(ge=1)
    network_requests: Literal[0]
    private_source_rows_copied: Literal[False]
    alignment_summary: AlignmentSummary
    input_artifacts: list[ArtifactDigest]
    external_content_digests: dict[str, Sha256]
    record_counts: dict[str, int]
    repository_tracking_contract: RepositoryTrackingContract


class AuthorityStatus(str, Enum):
    approved_exact = "approved_exact"
    insufficient = "insufficient"
    conflicted = "conflicted"
    revoked = "revoked"


class VariantField(str, Enum):
    casting = "casting"
    release_year = "release_year"
    series = "series"
    color = "color"
    collector_number = "collector_number"
    series_position = "series_position"
    edition = "edition"
    identifiers = "identifiers"


class CanonicalAuthorityRecord(StrictContract):
    authority_id: NonBlank
    canonical_uuid: UUID
    canonical_catalog_version: NonBlank
    catalog_record_sha256: Sha256
    variant_fields_verified: list[VariantField] = Field(min_length=1)
    independent_evidence_refs: list[NonBlank] = Field(min_length=1)
    evidence_source_ids: list[NonBlank] = Field(min_length=1)
    resolver_output_consulted: Literal[False]
    reviewed_by: NonBlank
    reviewed_at: AwareDatetime
    review_reason: NonBlank
    status: AuthorityStatus


class CanonicalAuthorityArtifact(StrictContract):
    schema_version: Literal["pvr-representative-hard-benchmark-canonical-authority-v1"]
    authority_version: NonBlank
    publication_scope: RowPublicationScope
    records: list[CanonicalAuthorityRecord]

    @model_validator(mode="after")
    def authority_ids_are_unique_and_ordered(self) -> CanonicalAuthorityArtifact:
        ids = [record.authority_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("authority IDs must be unique")
        if ids != sorted(ids):
            raise ValueError("authority records must be ordered by authority_id")
        return self


class AuthorityAuditInput(StrictContract):
    path: NonBlank
    sha256: Sha256


class AuthorityAuditCatalogSummary(StrictContract):
    catalog_path: Literal["data/catalog.json"]
    catalog_version: NonBlank
    catalog_sha256: Sha256
    product_count: int = Field(ge=0)
    synthetic_regression_only_excluded_count: int = Field(ge=0)
    independently_supported_exact_count: int = Field(ge=0)


class AuthorityAuditSupportingCatalogSummary(StrictContract):
    catalog_path: Literal["data/human_backed_catalog.json"]
    catalog_version: NonBlank
    catalog_sha256: Sha256
    casting_count: int = Field(ge=0)
    provisional_variant_count: int = Field(ge=0)
    exact_variant_count: int = Field(ge=0)
    exclusion_reasons: list[NonBlank] = Field(min_length=1)


class AuthorityAuditSourceSummary(StrictContract):
    source_id: NonBlank
    authority_eligibility: AuthorityEligibility
    exact_authority_decision: Literal["rejected"]
    eligible_exact_variant_count: Literal[0]
    exclusion_reasons: list[NonBlank] = Field(min_length=1)


class AuthorityAuditThresholds(StrictContract):
    minimum_pilot_usable_exact_variants: Literal[20]
    observed_pilot_usable_exact_variants: int = Field(ge=0)
    exact_variant_shortfall: int = Field(ge=0)
    minimum_same_casting_multi_release_families: Literal[4]
    observed_same_casting_multi_release_families: int = Field(ge=0)
    family_shortfall: int = Field(ge=0)


class CanonicalAuthorityManifest(StrictContract):
    """Frozen RHB-T4 audit summary; it contains no row-level private evidence."""

    schema_version: Literal["pvr-representative-hard-benchmark-canonical-authority-manifest-v1"]
    manifest_version: Literal["representative-hard-benchmark-canonical-authority-audit-v1"]
    status: Literal["complete"]
    generated_by: Literal["scripts/build_representative_hard_benchmark_canonical_authority.py"]
    generated_at: AwareDatetime
    network_requests: Literal[0]
    resolver_output_consulted: Literal[False]
    benchmark_labels_consulted: Literal[False]
    authority_file: Literal["canonical-authority.json"]
    authority_sha256: Sha256
    authority_version: NonBlank
    authority_record_order: list[NonBlank]
    input_artifacts: list[AuthorityAuditInput] = Field(min_length=1)
    canonical_catalog: AuthorityAuditCatalogSummary
    supporting_human_catalog: AuthorityAuditSupportingCatalogSummary
    source_audit: list[AuthorityAuditSourceSummary] = Field(min_length=1)
    current_source_count: int = Field(ge=1)
    current_source_exact_authority_rejected_count: int = Field(ge=0)
    eligible_exact_variant_count: int = Field(ge=0)
    pilot_usable_exact_variant_count: int = Field(ge=0)
    same_casting_multi_release_family_count: int = Field(ge=0)
    thresholds: AuthorityAuditThresholds
    gate_result: Literal["blocked_insufficient_exact_authority"]
    next_allowed_step: Literal["obtain_new_authorized_exact_variant_evidence"]
    prohibited_next_steps: list[NonBlank] = Field(min_length=1)
    exclusion_summary: list[NonBlank] = Field(min_length=1)

    @model_validator(mode="after")
    def audit_counts_and_gate_are_coherent(self) -> CanonicalAuthorityManifest:
        if self.authority_record_order != sorted(self.authority_record_order):
            raise ValueError("authority record order must be sorted")
        if len(self.authority_record_order) != len(set(self.authority_record_order)):
            raise ValueError("authority record order must be unique")
        if self.current_source_count != len(self.source_audit):
            raise ValueError("current source count must equal the source audit")
        rejected = sum(
            source.exact_authority_decision == "rejected" for source in self.source_audit
        )
        if self.current_source_exact_authority_rejected_count != rejected:
            raise ValueError("source rejection count must equal the source audit")
        if self.eligible_exact_variant_count != self.pilot_usable_exact_variant_count:
            raise ValueError("all eligible exact variants must be pilot-usable in this audit")
        thresholds = self.thresholds
        if thresholds.observed_pilot_usable_exact_variants != self.pilot_usable_exact_variant_count:
            raise ValueError("exact-variant threshold observation does not match the audit")
        if (
            thresholds.observed_same_casting_multi_release_families
            != self.same_casting_multi_release_family_count
        ):
            raise ValueError("family threshold observation does not match the audit")
        if thresholds.exact_variant_shortfall != max(
            0,
            thresholds.minimum_pilot_usable_exact_variants
            - thresholds.observed_pilot_usable_exact_variants,
        ):
            raise ValueError("exact-variant threshold shortfall is inconsistent")
        if thresholds.family_shortfall != max(
            0,
            thresholds.minimum_same_casting_multi_release_families
            - thresholds.observed_same_casting_multi_release_families,
        ):
            raise ValueError("family threshold shortfall is inconsistent")
        if not thresholds.exact_variant_shortfall and not thresholds.family_shortfall:
            raise ValueError("a blocked authority Gate requires a threshold shortfall")
        required_prohibitions = {
            "RHB_T5",
            "matched_pilot_construction",
            "query_pack_authoring",
            "label_authoring",
            "canonical_uuid_inference",
            "network_collection",
        }
        if set(self.prohibited_next_steps) != required_prohibitions:
            raise ValueError("blocked authority Gate must retain every downstream prohibition")
        return self


class SplitName(str, Enum):
    development = "development"
    test = "test"


class ChallengeTag(str, Enum):
    same_casting_different_release = "same_casting_different_release"
    alias_or_abbreviation = "alias_or_abbreviation"
    missing_metadata = "missing_metadata"
    conflicting_year = "conflicting_year"
    conflicting_color = "conflicting_color"
    conflicting_series = "conflicting_series"
    conflicting_identifier = "conflicting_identifier"
    distractor_quantity_or_lot = "distractor_quantity_or_lot"
    unknown_to_catalog = "unknown_to_catalog"


class BenchmarkQuery(StrictContract):
    case_id: NonBlank
    query: NonBlank
    source_id: NonBlank
    source_record_ref: str | None = None
    public_safe: bool
    family_group_key: NonBlank
    evidence_event_group_key: NonBlank
    challenge_tags: list[ChallengeTag] = Field(min_length=1)
    authored_by: NonBlank
    authored_at: AwareDatetime
    resolver_output_viewed: Literal[False]
    split: SplitName

    @model_validator(mode="after")
    def public_query_has_no_obvious_pii(self) -> BenchmarkQuery:
        # This is intentionally conservative; provenance review remains authoritative.
        if self.public_safe:
            _reject_obvious_pii(
                [self.query, self.authored_by, self.source_record_ref or ""],
                context=f"query {self.case_id}",
            )
        return self


class QueryPack(StrictContract):
    schema_version: Literal["pvr-representative-hard-benchmark-query-pack-v1"]
    dataset_version: NonBlank
    publication_scope: RowPublicationScope
    representative_pilot: bool
    cases: list[BenchmarkQuery]

    @model_validator(mode="after")
    def case_ids_are_unique_and_ordered(self) -> QueryPack:
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("query case IDs must be unique")
        if case_ids != sorted(case_ids):
            raise ValueError("query cases must be ordered by case_id")
        return self


class ExpectedStatus(str, Enum):
    matched = "matched"
    ambiguous = "ambiguous"
    no_match = "no_match"


class ReviewStatus(str, Enum):
    approved = "approved"
    held = "held"
    rejected = "rejected"


class FailureType(str, Enum):
    none = "none"
    retrieval_miss = "retrieval_miss"
    variant_confusion = "variant_confusion"
    alias_failure = "alias_failure"
    parser_error = "parser_error"
    year_conflict = "year_conflict"
    color_conflict = "color_conflict"
    identifier_conflict = "identifier_conflict"
    unknown_product_false_match = "unknown_product_false_match"
    under_abstention = "under_abstention"
    over_abstention = "over_abstention"
    hard_negative_failure = "hard_negative_failure"


class HardNegativeKind(str, Enum):
    same_casting_different_release = "same_casting_different_release"
    other = "other"


class BenchmarkLabel(StrictContract):
    case_id: NonBlank
    expected_status: ExpectedStatus
    expected_canonical_uuid: UUID | None
    canonical_authority_id: str | None
    family_label: NonBlank
    failure_type: FailureType
    hard_negative: bool
    hard_negative_kind: HardNegativeKind | None
    source_id: NonBlank
    evidence_refs: list[NonBlank] = Field(min_length=1)
    review_status: ReviewStatus
    reviewed_by: NonBlank
    reviewed_at: AwareDatetime
    review_reason: NonBlank
    public_safe: bool
    score_eligible: bool

    @model_validator(mode="after")
    def label_semantics_are_coherent(self) -> BenchmarkLabel:
        if self.expected_status == ExpectedStatus.matched:
            if self.expected_canonical_uuid is None or not self.canonical_authority_id:
                raise ValueError("matched labels require canonical UUID and authority ID")
        elif self.expected_canonical_uuid is not None or self.canonical_authority_id is not None:
            raise ValueError("ambiguous/no_match labels cannot carry canonical identity")
        if self.hard_negative != (self.hard_negative_kind is not None):
            raise ValueError("hard_negative and hard_negative_kind must agree")
        if self.review_status != ReviewStatus.approved and self.score_eligible:
            raise ValueError("held/rejected labels cannot be score eligible")
        if self.review_status == ReviewStatus.approved and not self.score_eligible:
            raise ValueError("approved labels must be score eligible")
        return self


class LabelArtifact(StrictContract):
    schema_version: Literal["pvr-representative-hard-benchmark-labels-v1"]
    dataset_version: NonBlank
    publication_scope: RowPublicationScope
    records: list[BenchmarkLabel]

    @model_validator(mode="after")
    def label_ids_are_unique_and_ordered(self) -> LabelArtifact:
        ids = [record.case_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("label case IDs must be unique")
        if ids != sorted(ids):
            raise ValueError("labels must be ordered by case_id")
        return self


class SplitRecord(StrictContract):
    case_id: NonBlank
    split: SplitName
    family_group_key: NonBlank
    evidence_event_group_key: NonBlank


class SplitArtifact(StrictContract):
    schema_version: Literal["pvr-representative-hard-benchmark-split-v1"]
    dataset_version: NonBlank
    seed: int = Field(ge=0)
    records: list[SplitRecord]

    @model_validator(mode="after")
    def split_ids_are_unique_and_ordered(self) -> SplitArtifact:
        ids = [record.case_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("split case IDs must be unique")
        if ids != sorted(ids):
            raise ValueError("split records must be ordered by case_id")
        return self


class FrozenArtifactManifest(StrictContract):
    """Generic complete manifest binding one ordered artifact to all parents."""

    schema_version: Literal["pvr-representative-hard-benchmark-manifest-v1"]
    artifact_version: NonBlank
    artifact_path: NonBlank
    artifact_sha256: Sha256
    parent_artifacts: list[ArtifactDigest]
    record_count: int = Field(ge=0)
    ordered_case_ids: list[NonBlank]
    counts: dict[str, int]
    publication_scope: PublicationScope
    created_by: NonBlank
    created_at: AwareDatetime
    status: Literal["complete"]
    configuration_versions: dict[str, NonBlank]
    model_versions: dict[str, NonBlank]
    index_versions: dict[str, NonBlank]

    @model_validator(mode="after")
    def manifest_counts_and_order_are_coherent(self) -> FrozenArtifactManifest:
        if self.record_count != len(self.ordered_case_ids):
            raise ValueError("manifest record count does not match ordered case IDs")
        if len(self.ordered_case_ids) != len(set(self.ordered_case_ids)):
            raise ValueError("manifest ordered case IDs contain duplicates")
        if any(count < 0 for count in self.counts.values()):
            raise ValueError("manifest counts cannot be negative")
        parent_paths = [item.path for item in self.parent_artifacts]
        if len(parent_paths) != len(set(parent_paths)):
            raise ValueError("manifest parent paths must be unique")
        if parent_paths != sorted(parent_paths):
            raise ValueError("manifest parents must be ordered by path")
        return self


class RawCandidate(StrictContract):
    canonical_uuid: UUID
    canonical_id: NonBlank
    sparse_rank: int | None = Field(default=None, ge=1)
    sparse_score: float | None = None
    similarity_rank: int | None = Field(default=None, ge=1)
    similarity_score: float | None = None
    structured_rank: int | None = Field(default=None, ge=1)
    structured_score: float | None = None
    rrf_rank: int | None = Field(default=None, ge=1)
    rrf_score: float | None = None
    reranker_rank: int | None = Field(default=None, ge=1)
    reranker_score: float | None = None


class RawSignals(StrictContract):
    normalized_title: str
    tokens: list[str]
    year: int | None = None
    collector_number: str | None = None
    series_position: str | None = None
    quantity: int | None = None
    multipack_hint: bool = False
    color_hints: list[str]
    series_hints: list[str]
    parse_warnings: list[str]


class LabelBlindRawResult(StrictContract):
    case_id: NonBlank
    signals: RawSignals
    candidates: list[RawCandidate] = Field(max_length=50)
    calibrated_probability: float = Field(ge=0, le=1)
    policy_status: ExpectedStatus
    returned_canonical_uuid: UUID | None
    timings_ms: dict[str, float]
    errors: list[NonBlank]
    runtime_hash: Sha256
    config_hash: Sha256

    @model_validator(mode="after")
    def returned_identity_matches_policy(self) -> LabelBlindRawResult:
        if self.policy_status == ExpectedStatus.matched:
            if self.returned_canonical_uuid is None:
                raise ValueError("matched raw policy result requires a returned UUID")
        elif self.returned_canonical_uuid is not None:
            raise ValueError("abstaining raw policy result cannot return a UUID")
        if any(value < 0 for value in self.timings_ms.values()):
            raise ValueError("timings cannot be negative")
        return self


class LabelBlindRawArtifact(StrictContract):
    schema_version: Literal["pvr-representative-hard-benchmark-test-raw-v1"]
    run_version: NonBlank
    collection_status: Literal["complete"]
    labels_loaded: Literal[False]
    parent_checksums: dict[str, Sha256]
    results: list[LabelBlindRawResult]

    @model_validator(mode="after")
    def raw_ids_are_unique_and_ordered(self) -> LabelBlindRawArtifact:
        ids = [result.case_id for result in self.results]
        if len(ids) != len(set(ids)):
            raise ValueError("raw result case IDs must be unique")
        if ids != sorted(ids):
            raise ValueError("raw results must be ordered by case_id")
        return self


class ScoredCaseResult(StrictContract):
    case_id: NonBlank
    expected_status: ExpectedStatus
    expected_canonical_uuid: UUID | None
    policy_status: ExpectedStatus
    returned_canonical_uuid: UUID | None
    target_ranks: dict[str, int | None]
    decision_correct: bool
    failure_type: FailureType
    calibration_target: Literal[0, 1]
    numerator_contributions: dict[str, int]


class AggregateMetric(StrictContract):
    value: float | None
    numerator: int = Field(ge=0)
    denominator: int = Field(ge=0)
    status: Literal["measured", "not_applicable"]

    @model_validator(mode="after")
    def denominator_controls_metric_status(self) -> AggregateMetric:
        if self.denominator == 0:
            if self.status != "not_applicable" or self.value is not None:
                raise ValueError("zero denominator must be not_applicable with null value")
        elif self.status != "measured" or self.value is None:
            raise ValueError("non-zero denominator must have a measured value")
        return self


class ScoredResultsArtifact(StrictContract):
    schema_version: Literal["pvr-representative-hard-benchmark-scored-results-v1"]
    run_version: NonBlank
    scoring_status: Literal["complete"]
    parent_checksums: dict[str, Sha256]
    results: list[ScoredCaseResult]
    metrics: dict[str, AggregateMetric]

    @model_validator(mode="after")
    def scored_ids_are_unique_and_ordered(self) -> ScoredResultsArtifact:
        ids = [result.case_id for result in self.results]
        if len(ids) != len(set(ids)):
            raise ValueError("scored result case IDs must be unique")
        if ids != sorted(ids):
            raise ValueError("scored results must be ordered by case_id")
        return self


def stable_json_bytes(value: Any) -> bytes:
    """Return the canonical UTF-8 representation used by benchmark SHA-256 manifests."""

    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def content_sha256(value: Any) -> str:
    """Hash an in-memory JSON-compatible artifact with the benchmark canonical encoding."""

    return hashlib.sha256(stable_json_bytes(value)).hexdigest()


def canonical_record_sha256(record: Mapping[str, Any]) -> str:
    """Hash one exact catalog record without deriving identity from retrieval output."""

    return content_sha256(dict(record))


def _raise(message: str) -> NoReturn:
    raise ContractError(message)


def _contains_obvious_pii(value: str) -> bool:
    """Detect obvious contact data while ignoring digits inside URI references."""

    if EMAIL_RE.search(value):
        return True
    without_urls = URL_RE.sub("", value)
    return PHONE_RE.search(without_urls) is not None


def _reject_obvious_pii(values: Sequence[str], *, context: str) -> None:
    if any(_contains_obvious_pii(value) for value in values):
        _raise(f"public {context} contains email or phone-like personal information")


def _source_map(inventory: SourceInventory) -> dict[str, SourceInventoryEntry]:
    return {entry.source_id: entry for entry in inventory.entries}


def validate_source_inventory(payload: Mapping[str, Any]) -> SourceInventory:
    """Parse a source inventory and reject undeclared fields or incoherent boundaries."""

    return SourceInventory.model_validate(payload)


def validate_source_inventory_manifest(
    payload: Mapping[str, Any], inventory_payload: Mapping[str, Any]
) -> SourceInventoryManifest:
    """Validate the checked-in T1 manifest against the exact source-inventory bytes."""

    manifest = SourceInventoryManifest.model_validate(payload)
    inventory = validate_source_inventory(inventory_payload)
    if manifest.inventory_version != inventory.inventory_version:
        _raise("source inventory version does not match its manifest")
    if manifest.source_entry_count != len(inventory.entries):
        _raise("source inventory entry count does not match its manifest")
    if manifest.inventory_sha256 != content_sha256(inventory_payload):
        _raise("source inventory checksum does not match its manifest")
    if manifest.alignment_summary != inventory.alignment_summary:
        _raise("source inventory alignment summary does not match its manifest")
    return manifest


BLOCKED_EXTERNAL_SOURCE_IDS = frozenset(
    {
        "live-ebay",
        "live-mercari",
        "live-facebook-marketplace",
        "live-fandom",
        "live-other-network-source",
    }
)
WORKBOOK_ALLOWED_FIELDS = frozenset(
    {
        "product_name",
        "year",
        "series",
        "color",
        "collector_number",
        "series_position",
    }
)
HUMAN_SOURCE_ID = "human-labeled-real-noisy-v1"
ALIGNMENT_SOURCE_ID = "human-labeled-to-fixture-alignment-v1"
WORKBOOK_SOURCE_ID = "owner-local-release-snapshot-2023-2026-v1"
WIKI_SOURCE_ID = "fandom-hot-wheels-2025-pilot-r790665-v1"


def _decision_map(source: SourceDecisionEntry) -> dict[SourceDecisionUse, SourceDecisionCell]:
    return {decision.use: decision for decision in source.decisions}


def _expect_decision(
    sources: Mapping[str, SourceDecisionEntry],
    source_id: str,
    use: SourceDecisionUse,
    status: SourceDecisionStatus,
    scope: SourceDecisionScope,
    *,
    allowed_fields: set[str] | frozenset[str] | None = None,
) -> SourceDecisionCell:
    cell = _decision_map(sources[source_id])[use]
    if cell.status != status or cell.effective_publication_scope != scope:
        _raise(f"source decision {source_id!r}/{use.value} changed the owner-approved status/scope")
    if allowed_fields is not None and set(cell.allowed_fields) != set(allowed_fields):
        _raise(f"source decision {source_id!r}/{use.value} changed its allowed fields")
    return cell


def validate_source_decisions(
    payload: Mapping[str, Any],
    *,
    inventory_payload: Mapping[str, Any],
    wiki_source_payload: Mapping[str, Any],
) -> SourceDecisionArtifact:
    """Validate the owner-confirmed T3 decision overlay against the exact T1 inventory."""

    artifact = SourceDecisionArtifact.model_validate(payload)
    inventory = validate_source_inventory(inventory_payload)
    if artifact.inventory_version != inventory.inventory_version:
        _raise("source decisions reference the wrong inventory version")
    if artifact.inventory_sha256 != content_sha256(inventory_payload):
        _raise("source decisions contain a stale source-inventory checksum")

    _validate_decision_package(artifact, inventory)
    wiki_source = next(source for source in artifact.sources if source.source_id == WIKI_SOURCE_ID)
    assert wiki_source.record_ref_contract is not None
    wiki_contract = wiki_source.record_ref_contract
    if content_sha256(wiki_source_payload) != wiki_contract.source_file_sha256:
        _raise("Wiki source-record reference file checksum is stale")
    records = wiki_source_payload.get("records")
    if not isinstance(records, list) or len(records) != wiki_contract.source_record_count:
        _raise("Wiki source-record reference file has the wrong record count")
    record_refs: list[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, Mapping):
            _raise(f"Wiki source record {index} must be an object")
        raw_ref = record.get(wiki_contract.source_record_id_field)
        source_metadata = record.get("source")
        if not isinstance(raw_ref, str) or not raw_ref:
            _raise(f"Wiki source record {index} has no source_record_id")
        if not isinstance(source_metadata, Mapping) or (
            source_metadata.get("revision_id") != wiki_contract.source_revision_id
        ):
            _raise(f"Wiki source record {raw_ref!r} has the wrong source revision")
        record_refs.append(raw_ref)
    if len(record_refs) != len(set(record_refs)):
        _raise("Wiki source-record IDs must be unique")
    artifact._wiki_source_record_refs = frozenset(record_refs)
    return artifact


def _validate_decision_package(
    artifact: SourceDecisionArtifact, inventory: SourceInventory
) -> None:
    """Recheck the immutable owner package before every downstream use."""

    inventory_sources = _source_map(inventory)
    sources = {source.source_id: source for source in artifact.sources}
    inventory_decision_ids = {
        source.source_id
        for source in artifact.sources
        if source.source_origin == SourceDecisionOrigin.inventory
    }
    if inventory_decision_ids != set(inventory_sources):
        _raise("source decisions must cover every inventory source exactly once")
    blocked_ids = {
        source.source_id
        for source in artifact.sources
        if source.source_origin == SourceDecisionOrigin.blocked_external
    }
    if blocked_ids != BLOCKED_EXTERNAL_SOURCE_IDS:
        _raise("source decisions must enumerate every blocked live external source")

    expected_permissions = {
        "fixture-v1-benchmark": {SourceDownstreamPermission.regression_only},
        "fixture-v1-catalog": {SourceDownstreamPermission.regression_only},
        HUMAN_SOURCE_ID: {
            SourceDownstreamPermission.query_pack,
            SourceDownstreamPermission.scored_labels,
        },
        ALIGNMENT_SOURCE_ID: {SourceDownstreamPermission.family_context},
        WORKBOOK_SOURCE_ID: {SourceDownstreamPermission.family_context},
        WIKI_SOURCE_ID: {
            SourceDownstreamPermission.query_pack,
            SourceDownstreamPermission.family_context,
        },
    }
    for source_id, permissions in expected_permissions.items():
        if set(sources[source_id].downstream_permissions) != permissions:
            _raise(f"source {source_id!r} changed its typed downstream permissions")
    if set(sources[HUMAN_SOURCE_ID].allowed_label_statuses) != {
        SourceAllowedLabelStatus.ambiguous,
        SourceAllowedLabelStatus.no_match,
    }:
        _raise("human source labels must remain limited to ambiguous/no_match")
    for source_id in set(expected_permissions) - {HUMAN_SOURCE_ID}:
        if sources[source_id].allowed_label_statuses:
            _raise(f"source {source_id!r} cannot produce scored labels")

    fixture_cells = {
        "fixture-v1-benchmark": {
            SourceDecisionUse.evidence_retention: {
                "existing_fixture_rows",
            },
            SourceDecisionUse.local_only_benchmark_use: {
                "synthetic_query",
                "synthetic_expected_status",
            },
            SourceDecisionUse.public_git_artifacts: {
                "existing_fixture_rows",
                "fixture_manifests",
                "regression_results",
            },
        },
        "fixture-v1-catalog": {
            SourceDecisionUse.evidence_retention: {
                "existing_fixture_catalog_rows",
            },
            SourceDecisionUse.local_only_benchmark_use: {
                "synthetic_catalog_record",
            },
            SourceDecisionUse.public_git_artifacts: {
                "existing_fixture_catalog_rows",
                "fixture_manifests",
                "regression_results",
            },
        },
    }
    for source_id, approved_cells in fixture_cells.items():
        for use in {SourceDecisionUse.query_text, SourceDecisionUse.reviewer_identity}:
            _expect_decision(
                sources,
                source_id,
                use,
                SourceDecisionStatus.rejected,
                SourceDecisionScope.prohibited,
                allowed_fields=set(),
            )
        for use, allowed_fields in approved_cells.items():
            _expect_decision(
                sources,
                source_id,
                use,
                SourceDecisionStatus.approved,
                (
                    SourceDecisionScope.local_only
                    if use == SourceDecisionUse.local_only_benchmark_use
                    else SourceDecisionScope.public_rows
                ),
                allowed_fields=allowed_fields,
            )

    for source_id, inventory_source in inventory_sources.items():
        decision_source = sources[source_id]
        if decision_source.authority_eligibility != inventory_source.authority_eligibility:
            _raise(f"source decision {source_id!r} changed inventory authority eligibility")
        if source_id in expected_permissions:
            exact = _decision_map(decision_source)[SourceDecisionUse.exact_variant_authority]
            if (
                exact.status != SourceDecisionStatus.rejected
                or exact.effective_publication_scope != SourceDecisionScope.prohibited
            ):
                _raise(f"current source {source_id!r} cannot be exact variant authority")

    for source_id in BLOCKED_EXTERNAL_SOURCE_IDS:
        source = sources[source_id]
        if source.authority_eligibility != AuthorityEligibility.prohibited:
            _raise(f"blocked external source {source_id!r} changed authority eligibility")
        if (
            source.collection_status
            != SourceCollectionStatus.no_source_specific_permission_no_collection
        ):
            _raise(f"blocked external source {source_id!r} changed collection status")
        if any(
            decision.status != SourceDecisionStatus.rejected
            or decision.effective_publication_scope != SourceDecisionScope.prohibited
            or decision.allowed_fields
            for decision in source.decisions
        ):
            _raise(f"blocked external source {source_id!r} must remain fully rejected")
        if source.downstream_permissions != [SourceDownstreamPermission.none]:
            _raise(f"blocked external source {source_id!r} cannot have downstream permission")
        if source.allowed_label_statuses or source.record_ref_contract is not None:
            _raise(f"blocked external source {source_id!r} cannot expose rows or labels")

    _expect_decision(
        sources,
        HUMAN_SOURCE_ID,
        SourceDecisionUse.query_text,
        SourceDecisionStatus.approved,
        SourceDecisionScope.local_only,
        allowed_fields={"query_text"},
    )
    _expect_decision(
        sources,
        HUMAN_SOURCE_ID,
        SourceDecisionUse.evidence_retention,
        SourceDecisionStatus.approved,
        SourceDecisionScope.local_only,
        allowed_fields={"raw_query_evidence"},
    )
    _expect_decision(
        sources,
        HUMAN_SOURCE_ID,
        SourceDecisionUse.local_only_benchmark_use,
        SourceDecisionStatus.approved,
        SourceDecisionScope.local_only,
        allowed_fields={"query_text", "human_label", "family_label"},
    )
    _expect_decision(
        sources,
        HUMAN_SOURCE_ID,
        SourceDecisionUse.public_git_artifacts,
        SourceDecisionStatus.approved,
        SourceDecisionScope.aggregate_only,
        allowed_fields={
            "schema",
            "sha256",
            "record_count",
            "non_sensitive_aggregate",
            "non_sensitive_summary",
            "reviewer_role",
        },
    )

    _expect_decision(
        sources,
        ALIGNMENT_SOURCE_ID,
        SourceDecisionUse.evidence_retention,
        SourceDecisionStatus.approved,
        SourceDecisionScope.local_only,
        allowed_fields={"alignment_status", "review_family_id", "source_record_digest"},
    )
    _expect_decision(
        sources,
        ALIGNMENT_SOURCE_ID,
        SourceDecisionUse.local_only_benchmark_use,
        SourceDecisionStatus.approved,
        SourceDecisionScope.local_only,
        allowed_fields={"alignment_status", "review_family_id", "source_record_digest"},
    )
    _expect_decision(
        sources,
        ALIGNMENT_SOURCE_ID,
        SourceDecisionUse.public_git_artifacts,
        SourceDecisionStatus.approved,
        SourceDecisionScope.aggregate_only,
        allowed_fields={
            "schema",
            "sha256",
            "record_count",
            "non_sensitive_aggregate",
            "non_sensitive_summary",
        },
    )
    for use in {SourceDecisionUse.query_text, SourceDecisionUse.reviewer_identity}:
        _expect_decision(
            sources,
            ALIGNMENT_SOURCE_ID,
            use,
            SourceDecisionStatus.rejected,
            SourceDecisionScope.prohibited,
            allowed_fields=set(),
        )

    _expect_decision(
        sources,
        WORKBOOK_SOURCE_ID,
        SourceDecisionUse.query_text,
        SourceDecisionStatus.rejected,
        SourceDecisionScope.prohibited,
        allowed_fields=set(),
    )
    for use in {
        SourceDecisionUse.evidence_retention,
        SourceDecisionUse.local_only_benchmark_use,
    }:
        _expect_decision(
            sources,
            WORKBOOK_SOURCE_ID,
            use,
            SourceDecisionStatus.approved,
            SourceDecisionScope.local_only,
            allowed_fields=WORKBOOK_ALLOWED_FIELDS,
        )
    _expect_decision(
        sources,
        WORKBOOK_SOURCE_ID,
        SourceDecisionUse.public_git_artifacts,
        SourceDecisionStatus.approved,
        SourceDecisionScope.aggregate_only,
        allowed_fields={
            "schema",
            "sha256",
            "record_count",
            "non_sensitive_aggregate",
            "non_sensitive_summary",
            "reviewer_role",
        },
    )

    wiki_query = _expect_decision(
        sources,
        WIKI_SOURCE_ID,
        SourceDecisionUse.query_text,
        SourceDecisionStatus.approved,
        SourceDecisionScope.public_rows,
        allowed_fields={"existing_revision_bound_text_derivative", "attribution"},
    )
    if not {"no_new_collection", "existing_checked_in_100_rows_only"}.issubset(
        wiki_query.conditions
    ):
        _raise("Wiki query approval must remain revision-bound with no new collection")
    _expect_decision(
        sources,
        WIKI_SOURCE_ID,
        SourceDecisionUse.local_only_benchmark_use,
        SourceDecisionStatus.approved,
        SourceDecisionScope.local_only,
        allowed_fields={"existing_revision_bound_text_derivative", "attribution"},
    )
    wiki_ref_contract = sources[WIKI_SOURCE_ID].record_ref_contract
    if wiki_ref_contract is None:
        _raise("Wiki query permission requires a typed source-record reference contract")
    wiki_inventory = inventory_sources[WIKI_SOURCE_ID]
    if (
        wiki_inventory.local_sha256 != wiki_ref_contract.source_file_sha256
        or wiki_inventory.record_count != wiki_ref_contract.source_record_count
    ):
        _raise("Wiki record-reference contract disagrees with the inventory digest/count")
    for source_id, source in sources.items():
        if source_id != WIKI_SOURCE_ID and source.record_ref_contract is not None:
            _raise(f"source {source_id!r} cannot declare a Wiki record-reference contract")
    for use in {
        SourceDecisionUse.evidence_retention,
        SourceDecisionUse.public_git_artifacts,
    }:
        wiki_cell = _decision_map(sources[WIKI_SOURCE_ID])[use]
        if (
            wiki_cell.status != SourceDecisionStatus.approved
            or wiki_cell.effective_publication_scope != SourceDecisionScope.public_rows
            or "attribution" not in wiki_cell.allowed_fields
            or "no_new_collection" not in wiki_cell.conditions
        ):
            _raise("Wiki public approval requires attribution and no-new-collection boundaries")

    for source_id in {HUMAN_SOURCE_ID, WORKBOOK_SOURCE_ID, WIKI_SOURCE_ID}:
        _expect_decision(
            sources,
            source_id,
            SourceDecisionUse.reviewer_identity,
            SourceDecisionStatus.approved,
            SourceDecisionScope.public_rows,
            allowed_fields={"reviewer_role"},
        )
        if (
            "role_only_project_owner"
            not in _decision_map(sources[source_id])[SourceDecisionUse.reviewer_identity].conditions
        ):
            _raise(f"source {source_id!r} reviewer identity must remain role-only")


def _assert_decisions_match_inventory(
    decisions: SourceDecisionArtifact, inventory: SourceInventory
) -> None:
    _validate_decision_package(decisions, inventory)
    normalized_inventory = inventory.model_dump(mode="json", exclude_none=True)
    if decisions.inventory_sha256 != content_sha256(normalized_inventory):
        _raise("source-decision overlay checksum does not match the supplied inventory")
    if decisions.inventory_version != inventory.inventory_version:
        _raise("source-decision overlay does not match the supplied inventory version")
    inventory_sources = _source_map(inventory)
    decision_sources = {
        source.source_id: source
        for source in decisions.sources
        if source.source_origin == SourceDecisionOrigin.inventory
    }
    if set(decision_sources) != set(inventory_sources):
        _raise("source-decision overlay does not match the supplied inventory IDs")
    for source_id, inventory_source in inventory_sources.items():
        if (
            decision_sources[source_id].authority_eligibility
            != inventory_source.authority_eligibility
        ):
            _raise("source-decision overlay changed inventory authority eligibility")


def _require_downstream_permission(
    decisions: SourceDecisionArtifact,
    source_id: str,
    permission: SourceDownstreamPermission,
) -> SourceDecisionEntry:
    source = next(
        (source for source in decisions.sources if source.source_id == source_id),
        None,
    )
    if source is None or permission not in source.downstream_permissions:
        _raise(f"source {source_id!r} lacks typed {permission.value} permission")
    return source


def _approved_decision_for_use(
    decisions: SourceDecisionArtifact,
    source_id: str,
    use: SourceDecisionUse,
    *,
    required_scope: SourceDecisionScope,
) -> SourceDecisionCell:
    sources = {source.source_id: source for source in decisions.sources}
    source = sources.get(source_id)
    if source is None:
        _raise(f"source {source_id!r} has no owner-confirmed source decision")
    cell = _decision_map(source)[use]
    if cell.status != SourceDecisionStatus.approved:
        _raise(f"source {source_id!r} is not owner-approved for {use.value}")
    allowed_scopes = {required_scope}
    if required_scope == SourceDecisionScope.local_only:
        allowed_scopes.add(SourceDecisionScope.public_rows)
    if cell.effective_publication_scope not in allowed_scopes:
        _raise(f"source {source_id!r}/{use.value} cannot satisfy {required_scope.value} scope")
    return cell


def _catalog_index(
    catalog_payload: Mapping[str, Any],
) -> tuple[str, dict[UUID, Mapping[str, Any]]]:
    raw_version = catalog_payload.get("catalog_version") or catalog_payload.get("dataset_version")
    raw_products = catalog_payload.get("products")
    if not isinstance(raw_version, str) or not raw_version or not isinstance(raw_products, list):
        _raise("canonical catalog must declare a version and products[]")
    version = raw_version
    products = raw_products
    indexed: dict[UUID, Mapping[str, Any]] = {}
    for index, raw in enumerate(products):
        if not isinstance(raw, Mapping):
            _raise(f"canonical catalog product {index} must be an object")
        try:
            canonical_uuid = UUID(str(raw["canonical_uuid"]))
        except (KeyError, TypeError, ValueError) as error:
            raise ContractError(f"canonical catalog product {index} has invalid UUID") from error
        if canonical_uuid in indexed:
            _raise(f"canonical catalog contains duplicate UUID {canonical_uuid}")
        indexed[canonical_uuid] = raw
    return version, indexed


def validate_canonical_authority(
    payload: Mapping[str, Any],
    *,
    inventory: SourceInventory,
    catalog_payload: Mapping[str, Any],
    source_decisions: SourceDecisionArtifact,
) -> CanonicalAuthorityArtifact:
    """Validate exact-variant authority against approved sources and the frozen catalog."""

    artifact = CanonicalAuthorityArtifact.model_validate(payload)
    _assert_decisions_match_inventory(source_decisions, inventory)
    catalog_version, catalog = _catalog_index(catalog_payload)
    sources = _source_map(inventory)
    for record in artifact.records:
        if artifact.publication_scope == RowPublicationScope.public:
            _reject_obvious_pii(
                [
                    record.authority_id,
                    record.reviewed_by,
                    record.review_reason,
                    *record.independent_evidence_refs,
                ],
                context=f"authority {record.authority_id!r}",
            )
        if record.reviewed_by != source_decisions.reviewer_identity_policy.reviewer_role:
            _raise("authority reviews must use role-only reviewer project_owner")
        if record.canonical_catalog_version != catalog_version:
            _raise(f"authority {record.authority_id!r} references the wrong catalog version")
        product = catalog.get(record.canonical_uuid)
        if product is None:
            _raise(f"authority {record.authority_id!r} references a non-catalog UUID")
        if record.catalog_record_sha256 != canonical_record_sha256(product):
            _raise(f"authority {record.authority_id!r} has a stale catalog record checksum")
        for source_id in record.evidence_source_ids:
            source = sources.get(source_id)
            if source is None:
                _raise(f"authority {record.authority_id!r} references unknown source {source_id!r}")
            if record.status == AuthorityStatus.approved_exact:
                _require_downstream_permission(
                    source_decisions,
                    source.source_id,
                    SourceDownstreamPermission.canonical_authority,
                )
                _approved_decision_for_use(
                    source_decisions,
                    source.source_id,
                    SourceDecisionUse.exact_variant_authority,
                    required_scope=(
                        SourceDecisionScope.public_rows
                        if artifact.publication_scope == RowPublicationScope.public
                        else SourceDecisionScope.local_only
                    ),
                )
                if (
                    source.authority_eligibility
                    != AuthorityEligibility.exact_variant_authority_candidate
                    or source.authority_evidence_level
                    != AuthorityEvidenceLevel.independent_exact_variant
                    or source.source_kind != SourceKind.authorized_export
                ):
                    _raise(
                        f"source {source.source_id!r} is permanently ineligible for exact authority"
                    )
        if record.status == AuthorityStatus.approved_exact:
            catalog_field_map = {
                VariantField.casting: "casting",
                VariantField.release_year: "release_year",
                VariantField.series: "series",
                VariantField.color: "color",
                VariantField.collector_number: "collector_number",
                VariantField.series_position: "series_position",
                VariantField.edition: "edition",
                VariantField.identifiers: "identifiers",
            }
            required = {
                field
                for field, catalog_key in catalog_field_map.items()
                if product.get(catalog_key) not in (None, "", [])
            }
            verified = set(record.variant_fields_verified)
            missing = sorted(field.value for field in required - verified)
            if missing:
                _raise(
                    f"authority {record.authority_id!r} omits available variant fields: "
                    + ", ".join(missing)
                )
    return artifact


def validate_canonical_authority_manifest(
    payload: Mapping[str, Any],
    *,
    authority_payload: Mapping[str, Any],
    catalog_payload: Mapping[str, Any],
    human_catalog_payload: Mapping[str, Any],
    inventory: SourceInventory,
    source_decisions: SourceDecisionArtifact,
    input_sha256: Mapping[str, str],
) -> CanonicalAuthorityManifest:
    """Validate the frozen T4 audit and fail closed on stale or incomplete parents."""

    manifest = CanonicalAuthorityManifest.model_validate(payload)
    authority = validate_canonical_authority(
        authority_payload,
        inventory=inventory,
        catalog_payload=catalog_payload,
        source_decisions=source_decisions,
    )
    if manifest.authority_sha256 != content_sha256(authority_payload):
        _raise("canonical authority checksum does not match its manifest")
    if manifest.authority_version != authority.authority_version:
        _raise("canonical authority version does not match its manifest")
    if manifest.authority_record_order != [record.authority_id for record in authority.records]:
        _raise("canonical authority record order does not match its manifest")
    if manifest.eligible_exact_variant_count != len(
        [record for record in authority.records if record.status == AuthorityStatus.approved_exact]
    ):
        _raise("eligible exact-variant count does not match approved authority records")

    catalog_version, catalog = _catalog_index(catalog_payload)
    catalog_summary = manifest.canonical_catalog
    if catalog_summary.catalog_version != catalog_version:
        _raise("canonical catalog version does not match the authority audit")
    if catalog_summary.catalog_sha256 != content_sha256(catalog_payload):
        _raise("canonical catalog checksum does not match the authority audit")
    if catalog_summary.product_count != len(catalog):
        _raise("canonical catalog count does not match the authority audit")
    if (
        catalog_summary.synthetic_regression_only_excluded_count
        + catalog_summary.independently_supported_exact_count
        != catalog_summary.product_count
    ):
        _raise("canonical catalog eligibility counts do not cover every product")
    if catalog_summary.independently_supported_exact_count != manifest.eligible_exact_variant_count:
        _raise("catalog exact count does not match the authority audit")

    human_summary = manifest.supporting_human_catalog
    if human_summary.catalog_sha256 != content_sha256(human_catalog_payload):
        _raise("supporting human catalog checksum does not match the authority audit")
    if human_summary.catalog_version != human_catalog_payload.get("catalog_version"):
        _raise("supporting human catalog version does not match the authority audit")
    castings = human_catalog_payload.get("castings")
    if not isinstance(castings, list):
        _raise("supporting human catalog must declare castings[]")
    provisional_variants = sum(
        len(casting.get("provisional_variants", []))
        for casting in castings
        if isinstance(casting, Mapping)
    )
    if human_summary.casting_count != len(castings):
        _raise("supporting human catalog casting count does not match the audit")
    if human_summary.provisional_variant_count != provisional_variants:
        _raise("supporting human catalog provisional count does not match the audit")
    if human_summary.exact_variant_count != 0:
        _raise("supporting human catalog cannot supply exact canonical variants")

    decision_sources = {source.source_id: source for source in source_decisions.sources}
    inventory_sources = _source_map(inventory)
    if {source.source_id for source in manifest.source_audit} != set(decision_sources):
        _raise("source audit must cover every owner-confirmed source exactly once")
    if [source.source_id for source in manifest.source_audit] != sorted(decision_sources):
        _raise("source audit must use stable source-id ordering")
    for source_summary in manifest.source_audit:
        decision = decision_sources[source_summary.source_id]
        exact_cell = _decision_map(decision)[SourceDecisionUse.exact_variant_authority]
        if exact_cell.status != SourceDecisionStatus.rejected:
            _raise(f"source {source_summary.source_id!r} exact authority is not rejected")
        if SourceDownstreamPermission.canonical_authority in decision.downstream_permissions:
            _raise(f"source {source_summary.source_id!r} unexpectedly grants exact authority")
        if source_summary.authority_eligibility != decision.authority_eligibility:
            _raise(f"source {source_summary.source_id!r} eligibility changed in the audit")
        inventory_source = inventory_sources.get(source_summary.source_id)
        if inventory_source is not None and (
            inventory_source.authority_eligibility != source_summary.authority_eligibility
        ):
            _raise(f"source {source_summary.source_id!r} disagrees with the source inventory")

    inputs = {item.path: item.sha256 for item in manifest.input_artifacts}
    if len(inputs) != len(manifest.input_artifacts):
        _raise("authority audit input paths must be unique")
    if list(inputs) != sorted(inputs):
        _raise("authority audit inputs must use stable path ordering")
    if inputs != dict(input_sha256):
        _raise("authority audit input set or checksum is stale")
    return manifest


def validate_query_pack(
    payload: Mapping[str, Any],
    *,
    inventory: SourceInventory,
    source_decisions: SourceDecisionArtifact,
) -> QueryPack:
    """Validate output-blind cases and their exact source/publication permission."""

    artifact = QueryPack.model_validate(payload)
    _assert_decisions_match_inventory(source_decisions, inventory)
    sources = _source_map(inventory)
    for case in artifact.cases:
        source = sources.get(case.source_id)
        if source is None:
            _raise(f"query {case.case_id!r} references unknown source {case.source_id!r}")
        decision_source = _require_downstream_permission(
            source_decisions,
            source.source_id,
            SourceDownstreamPermission.query_pack,
        )
        required_scope = (
            SourceDecisionScope.public_rows
            if artifact.publication_scope == RowPublicationScope.public
            else SourceDecisionScope.local_only
        )
        _approved_decision_for_use(
            source_decisions,
            source.source_id,
            SourceDecisionUse.query_text,
            required_scope=required_scope,
        )
        if case.authored_by != source_decisions.reviewer_identity_policy.reviewer_role:
            _raise("queries must use role-only author project_owner")
        if artifact.publication_scope == RowPublicationScope.public:
            _approved_decision_for_use(
                source_decisions,
                source.source_id,
                SourceDecisionUse.public_git_artifacts,
                required_scope=SourceDecisionScope.public_rows,
            )
        if source.source_id == WIKI_SOURCE_ID:
            if decision_source.record_ref_contract is None:
                _raise("Wiki query source has no record-reference contract")
            if case.source_record_ref not in source_decisions.wiki_source_record_refs:
                _raise("Wiki query source_record_ref is outside the approved 100-row revision")
        if artifact.representative_pilot and source.source_kind == SourceKind.synthetic_fixture:
            _raise("synthetic queries cannot count toward the representative pilot")
        if artifact.publication_scope == RowPublicationScope.public and not case.public_safe:
            _raise("a public query pack cannot contain a non-public-safe row")
        if (
            source.retention_scope == RetentionScope.local_only
            and case.source_record_ref
            and artifact.publication_scope == RowPublicationScope.public
        ):
            _raise("public query packs cannot expose local-only source references")
    return artifact


def validate_labels(
    payload: Mapping[str, Any],
    *,
    query_pack: QueryPack,
    authority: CanonicalAuthorityArtifact,
    catalog_payload: Mapping[str, Any],
    inventory: SourceInventory,
    source_decisions: SourceDecisionArtifact,
) -> LabelArtifact:
    """Validate label semantics and prohibit non-canonical identities from becoming truth."""

    artifact = LabelArtifact.model_validate(payload)
    validated_query_pack = validate_query_pack(
        query_pack.model_dump(mode="json"),
        inventory=inventory,
        source_decisions=source_decisions,
    )
    validated_authority = validate_canonical_authority(
        authority.model_dump(mode="json"),
        inventory=inventory,
        catalog_payload=catalog_payload,
        source_decisions=source_decisions,
    )
    _assert_decisions_match_inventory(source_decisions, inventory)
    queries = {case.case_id: case for case in validated_query_pack.cases}
    authorities = {record.authority_id: record for record in validated_authority.records}
    _, catalog = _catalog_index(catalog_payload)
    for label in artifact.records:
        if artifact.publication_scope == RowPublicationScope.public:
            _reject_obvious_pii(
                [
                    label.family_label,
                    label.reviewed_by,
                    label.review_reason,
                    *label.evidence_refs,
                ],
                context=f"label {label.case_id!r}",
            )
        query = queries.get(label.case_id)
        if query is None:
            _raise(f"label {label.case_id!r} has no query")
        if label.source_id != query.source_id:
            _raise(f"label {label.case_id!r} changed the query source")
        decision_source = _require_downstream_permission(
            source_decisions,
            label.source_id,
            SourceDownstreamPermission.scored_labels,
        )
        if (
            SourceAllowedLabelStatus(label.expected_status.value)
            not in decision_source.allowed_label_statuses
        ):
            _raise(
                f"source {label.source_id!r} cannot produce {label.expected_status.value} labels"
            )
        _approved_decision_for_use(
            source_decisions,
            label.source_id,
            SourceDecisionUse.local_only_benchmark_use,
            required_scope=SourceDecisionScope.local_only,
        )
        reviewer = _approved_decision_for_use(
            source_decisions,
            label.source_id,
            SourceDecisionUse.reviewer_identity,
            required_scope=SourceDecisionScope.public_rows,
        )
        if (
            label.reviewed_by != source_decisions.reviewer_identity_policy.reviewer_role
            or reviewer.allowed_fields != ["reviewer_role"]
        ):
            _raise("owner-confirmed labels must use role-only reviewer project_owner")
        if artifact.publication_scope == RowPublicationScope.public:
            _approved_decision_for_use(
                source_decisions,
                label.source_id,
                SourceDecisionUse.public_git_artifacts,
                required_scope=SourceDecisionScope.public_rows,
            )
        if artifact.publication_scope == RowPublicationScope.public and (
            not label.public_safe or not query.public_safe
        ):
            _raise("public labels require public-safe label and query rows")
        if label.reviewed_at < query.authored_at:
            _raise(f"label {label.case_id!r} predates its query")
        if label.expected_status == ExpectedStatus.matched:
            assert label.expected_canonical_uuid is not None
            assert label.canonical_authority_id is not None
            record = authorities.get(label.canonical_authority_id)
            if record is None or record.status != AuthorityStatus.approved_exact:
                _raise(f"matched label {label.case_id!r} lacks approved exact authority")
            if record.canonical_uuid != label.expected_canonical_uuid:
                _raise(f"matched label {label.case_id!r} does not match its authority UUID")
            if label.expected_canonical_uuid not in catalog:
                _raise(f"matched label {label.case_id!r} UUID does not exist in catalog")
            if record.reviewed_at > label.reviewed_at:
                _raise(f"matched label {label.case_id!r} predates its authority review")
    return artifact


def validate_split(payload: Mapping[str, Any], *, query_pack: QueryPack) -> SplitArtifact:
    """Validate exact case coverage and prevent family/evidence groups crossing splits."""

    artifact = SplitArtifact.model_validate(payload)
    query_by_id = {case.case_id: case for case in query_pack.cases}
    split_ids = {record.case_id for record in artifact.records}
    if split_ids != set(query_by_id):
        _raise("split must contain every query exactly once and no extra cases")
    family_splits: dict[str, set[SplitName]] = defaultdict(set)
    event_splits: dict[str, set[SplitName]] = defaultdict(set)
    for record in artifact.records:
        query = query_by_id[record.case_id]
        if (
            record.family_group_key != query.family_group_key
            or record.evidence_event_group_key != query.evidence_event_group_key
            or record.split != query.split
        ):
            _raise(f"split record {record.case_id!r} disagrees with its query")
        family_splits[record.family_group_key].add(record.split)
        event_splits[record.evidence_event_group_key].add(record.split)
    if any(len(splits) > 1 for splits in family_splits.values()):
        _raise("a family group crosses Development/Test")
    if any(len(splits) > 1 for splits in event_splits.values()):
        _raise("an evidence event group crosses Development/Test")
    return artifact


def _walk_keys(value: Any, path: str = "$") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower()
            # The one permitted label-related field is negative collection telemetry.
            allowed_negative_telemetry = path == "$" and normalized == "labels_loaded"
            if not allowed_negative_telemetry and any(
                part in normalized for part in FORBIDDEN_RAW_FIELD_PARTS
            ):
                _raise(f"label-blind raw contains forbidden field {path}.{key}")
            _walk_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_keys(child, f"{path}[{index}]")


def validate_label_blind_raw(
    payload: Mapping[str, Any], *, query_pack: QueryPack, split: SplitArtifact
) -> LabelBlindRawArtifact:
    """Validate Test raw recursively before any label artifact is allowed to load."""

    _walk_keys(payload)
    artifact = LabelBlindRawArtifact.model_validate(payload)
    split_by_id = {record.case_id: record.split for record in split.records}
    expected_ids = sorted(
        case.case_id for case in query_pack.cases if split_by_id.get(case.case_id) == SplitName.test
    )
    if [result.case_id for result in artifact.results] != expected_ids:
        _raise("raw result order/count must exactly match frozen Test queries")
    return artifact


def validate_scored_results(
    payload: Mapping[str, Any],
    *,
    raw: LabelBlindRawArtifact,
    labels: LabelArtifact,
) -> ScoredResultsArtifact:
    """Validate the one-time label join; held/rejected rows can never enter scoring."""

    artifact = ScoredResultsArtifact.model_validate(payload)
    raw_by_id = {result.case_id: result for result in raw.results}
    label_by_id = {label.case_id: label for label in labels.records}
    if [result.case_id for result in artifact.results] != [
        result.case_id for result in raw.results
    ]:
        _raise("scored result order/count must exactly match frozen raw results")
    for result in artifact.results:
        label = label_by_id.get(result.case_id)
        raw_result = raw_by_id[result.case_id]
        if label is None:
            _raise(f"scored result {result.case_id!r} has no label")
        if label.review_status != ReviewStatus.approved or not label.score_eligible:
            _raise(f"held/rejected label {result.case_id!r} cannot be scored")
        if (
            result.expected_status != label.expected_status
            or result.expected_canonical_uuid != label.expected_canonical_uuid
        ):
            _raise(f"scored result {result.case_id!r} changed its frozen label")
        if (
            result.policy_status != raw_result.policy_status
            or result.returned_canonical_uuid != raw_result.returned_canonical_uuid
        ):
            _raise(f"scored result {result.case_id!r} changed its frozen raw decision")
    return artifact


def validate_frozen_manifest(
    payload: Mapping[str, Any],
    *,
    artifact_payload: Mapping[str, Any],
    ordered_case_ids: Sequence[str],
    parent_checksums: Mapping[str, str],
) -> FrozenArtifactManifest:
    """Reject stale, reordered, partial, or parent-incomplete frozen artifacts."""

    manifest = FrozenArtifactManifest.model_validate(payload)
    if manifest.artifact_sha256 != content_sha256(artifact_payload):
        _raise("artifact checksum does not match manifest")
    if manifest.ordered_case_ids != list(ordered_case_ids):
        _raise("artifact order does not match manifest")
    if manifest.record_count != len(ordered_case_ids):
        _raise("artifact record count does not match manifest")
    declared = {item.path: item.sha256 for item in manifest.parent_artifacts}
    if declared != dict(parent_checksums):
        _raise("manifest parent set/checksums are stale or incomplete")
    return manifest


def validate_t1_inventory_files(
    inventory_payload: Mapping[str, Any], manifest_payload: Mapping[str, Any]
) -> tuple[SourceInventory, SourceInventoryManifest]:
    """Layered convenience API for the read-only RHB-T1 upstream artifacts."""

    inventory = validate_source_inventory(inventory_payload)
    manifest = validate_source_inventory_manifest(manifest_payload, inventory_payload)
    return inventory, manifest


__all__ = [
    "AggregateMetric",
    "BenchmarkLabel",
    "BenchmarkQuery",
    "CanonicalAuthorityArtifact",
    "CanonicalAuthorityManifest",
    "CanonicalAuthorityRecord",
    "ContractError",
    "FrozenArtifactManifest",
    "LabelArtifact",
    "LabelBlindRawArtifact",
    "QueryPack",
    "ScoredResultsArtifact",
    "SourceDecisionArtifact",
    "SourceDecisionCell",
    "SourceDecisionEntry",
    "SourceInventory",
    "SourceInventoryEntry",
    "SplitArtifact",
    "canonical_record_sha256",
    "content_sha256",
    "stable_json_bytes",
    "validate_canonical_authority",
    "validate_canonical_authority_manifest",
    "validate_frozen_manifest",
    "validate_label_blind_raw",
    "validate_labels",
    "validate_query_pack",
    "validate_scored_results",
    "validate_source_decisions",
    "validate_source_inventory",
    "validate_source_inventory_manifest",
    "validate_split",
    "validate_t1_inventory_files",
]
