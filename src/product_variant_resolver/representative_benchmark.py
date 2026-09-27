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
from enum import Enum
from typing import Annotated, Any, Literal, Mapping, NoReturn, Sequence
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

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
        if self.redistribution_scope == RedistributionScope.public_rows:
            if self.retention_scope != RetentionScope.public:
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


def _approved_source_for_use(
    source: SourceInventoryEntry,
    use: BenchmarkUse,
    *,
    public_rows: bool,
) -> None:
    if source.owner_decision != OwnerDecision.approved:
        _raise(f"source {source.source_id!r} has no approved owner decision")
    if use not in source.benchmark_uses:
        _raise(f"source {source.source_id!r} is not approved for {use.value}")
    if source.prospective_benchmark_use_status != "approved":
        _raise(f"source {source.source_id!r} prospective benchmark use is not approved")
    if source.privacy_review_status != PrivacyStatus.approved:
        _raise(f"source {source.source_id!r} has no approved privacy review")
    if source.access_permission_status not in {
        PermissionStatus.approved,
        PermissionStatus.not_applicable,
    }:
        _raise(f"source {source.source_id!r} lacks access permission")
    if source.content_license_status != LicenseStatus.approved:
        _raise(f"source {source.source_id!r} lacks approved content rights")
    if public_rows and (
        source.retention_scope != RetentionScope.public
        or source.redistribution_scope != RedistributionScope.public_rows
    ):
        _raise(f"source {source.source_id!r} is not approved for public row publication")
    if public_rows and source.prospective_redistribution_status != "approved":
        _raise(f"source {source.source_id!r} prospective redistribution is not approved")


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
) -> CanonicalAuthorityArtifact:
    """Validate exact-variant authority against approved sources and the frozen catalog."""

    artifact = CanonicalAuthorityArtifact.model_validate(payload)
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
                _approved_source_for_use(
                    source,
                    BenchmarkUse.exact_variant_authority,
                    public_rows=artifact.publication_scope == RowPublicationScope.public,
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


def validate_query_pack(payload: Mapping[str, Any], *, inventory: SourceInventory) -> QueryPack:
    """Validate output-blind cases and their exact source/publication permission."""

    artifact = QueryPack.model_validate(payload)
    sources = _source_map(inventory)
    for case in artifact.cases:
        source = sources.get(case.source_id)
        if source is None:
            _raise(f"query {case.case_id!r} references unknown source {case.source_id!r}")
        _approved_source_for_use(
            source,
            BenchmarkUse.query_provenance,
            public_rows=artifact.publication_scope == RowPublicationScope.public
            or case.public_safe,
        )
        if artifact.representative_pilot and source.source_kind == SourceKind.synthetic_fixture:
            _raise("synthetic queries cannot count toward the representative pilot")
        if artifact.publication_scope == RowPublicationScope.public and not case.public_safe:
            _raise("a public query pack cannot contain a non-public-safe row")
        if source.retention_scope == RetentionScope.local_only and case.source_record_ref:
            if artifact.publication_scope == RowPublicationScope.public:
                _raise("public query packs cannot expose local-only source references")
    return artifact


def validate_labels(
    payload: Mapping[str, Any],
    *,
    query_pack: QueryPack,
    authority: CanonicalAuthorityArtifact,
    catalog_payload: Mapping[str, Any],
) -> LabelArtifact:
    """Validate label semantics and prohibit non-canonical identities from becoming truth."""

    artifact = LabelArtifact.model_validate(payload)
    queries = {case.case_id: case for case in query_pack.cases}
    authorities = {record.authority_id: record for record in authority.records}
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
    "CanonicalAuthorityRecord",
    "ContractError",
    "FrozenArtifactManifest",
    "LabelArtifact",
    "LabelBlindRawArtifact",
    "QueryPack",
    "ScoredResultsArtifact",
    "SourceInventory",
    "SourceInventoryEntry",
    "SplitArtifact",
    "canonical_record_sha256",
    "content_sha256",
    "stable_json_bytes",
    "validate_canonical_authority",
    "validate_frozen_manifest",
    "validate_label_blind_raw",
    "validate_labels",
    "validate_query_pack",
    "validate_scored_results",
    "validate_source_inventory",
    "validate_source_inventory_manifest",
    "validate_split",
    "validate_t1_inventory_files",
]
