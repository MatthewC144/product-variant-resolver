from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal, TypeAlias
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResolutionStatus(str, Enum):
    matched = "matched"
    ambiguous = "ambiguous"
    no_match = "no_match"


class ResolveRequest(StrictModel):
    title: str = Field(min_length=1, max_length=500)
    debug: bool = False
    debug_candidate_limit: int = Field(default=10, ge=1, le=25)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must contain 1 to 500 characters")
        return value


class ProductView(StrictModel):
    brand: str
    casting: str
    release_year: int | None = None
    series: str | None = None
    color: str | None = None
    collector_number: str | None = None
    series_position: str | None = None
    rarity_tier: str | None = None
    edition: str | None = None


class ExtractedSignals(StrictModel):
    normalized_title: str
    tokens: list[str]
    year: int | None = None
    collector_number: str | None = None
    series_position: str | None = None
    quantity: int | None = None
    multipack_hint: bool = False
    color_hints: list[str] = Field(default_factory=list)
    series_hints: list[str] = Field(default_factory=list)
    parse_warnings: list[str] = Field(default_factory=list)


class CandidateDebug(StrictModel):
    canonical_uuid: UUID
    canonical_id: str
    sparse_rank: int | None = None
    sparse_score: float | None = None
    dense_rank: int | None = None
    dense_score: float | None = None
    structured_rank: int | None = None
    structured_score: float | None = None
    rrf_rank: int | None = None
    rrf_score: float | None = None
    reranker_rank: int | None = None
    reranker_score: float | None = None
    structured_matches: list[str] = Field(default_factory=list)
    structured_conflicts: list[str] = Field(default_factory=list)


class HumanKnowledgeCandidateRankDebug(StrictModel):
    identity_status: str
    brand: str
    casting: str
    sparse_rank: int | None = None
    sparse_score: float | None = None
    dense_rank: int | None = None
    dense_score: float | None = None
    character_rank: int | None = None
    character_score: float | None = None
    rrf_rank: int
    rrf_score: float
    matched_tokens: list[str] = Field(default_factory=list)


class HumanVariantKnowledgeCandidateDebug(HumanKnowledgeCandidateRankDebug):
    knowledge_type: Literal["provisional_variant"]
    casting_uuid: UUID
    casting_id: str
    provisional_variant_uuid: UUID
    provisional_variant_id: str
    series_label: str | None = None
    variant_label: str | None = None
    human_label_names: list[str]
    example_initial_names: list[str]
    source_case_ids: list[str]


class ReviewFamilyKnowledgeCandidateDebug(HumanKnowledgeCandidateRankDebug):
    knowledge_type: Literal["review_family"]
    review_family_uuid: UUID
    review_family_id: str
    aliases: list[str]
    source_record_ids: list[str]


HumanKnowledgeCandidateDebug: TypeAlias = Annotated[
    HumanVariantKnowledgeCandidateDebug | ReviewFamilyKnowledgeCandidateDebug,
    Field(discriminator="knowledge_type"),
]


class HumanKnowledgeCharacterIndexDebug(StrictModel):
    version: str
    document_count: int = Field(ge=1)
    posting_count: int = Field(ge=1)
    posting_entry_count: int = Field(ge=1)
    gram_sizes: list[int]
    modes: list[str]
    window_token_radius: int = Field(ge=0)
    stable_tie_break: str
    allowed_fields: dict[str, list[str]]
    form_count: int | None = Field(default=None, ge=1, exclude_if=lambda value: value is None)
    posting_definition: str | None = Field(default=None, exclude_if=lambda value: value is None)


class HumanKnowledgeIdentityWorkDebug(StrictModel):
    policy_version: Literal["identity-core-policy-v1"]
    query_forms: int = Field(ge=0, le=258)
    posting_entries_visited: int = Field(ge=0, le=1_000_000)
    scored_forms: int = Field(ge=0)
    exact_candidates: int = Field(ge=0, le=25)
    character_candidates: int = Field(ge=0, le=25)
    dense_union: int = Field(ge=0, le=50)
    abstention_reason: Literal["query_limit", "noise_only", "window_limit", "posting_limit"] | None = None


class DebugPayload(StrictModel):
    signals: ExtractedSignals
    candidates: list[CandidateDebug]
    human_knowledge_candidates: list[HumanKnowledgeCandidateDebug]
    timings_ms: dict[str, float]
    catalog_version: str
    human_catalog_version: str
    review_family_knowledge_version: str
    human_knowledge_retrieval_artifact_version: str | None = None
    human_knowledge_retrieval_artifact_sha256: str | None = None
    human_knowledge_character_index: HumanKnowledgeCharacterIndexDebug | None = None
    human_knowledge_identity_work: HumanKnowledgeIdentityWorkDebug | None = Field(
        default=None, exclude_if=lambda value: value is None,
    )
    model_versions: dict[str, str]


class ResolveResponse(StrictModel):
    status: ResolutionStatus
    canonical_uuid: UUID | None
    canonical_id: str | None
    confidence: float = Field(ge=0, le=1)
    reason: str
    product: ProductView | None
    policy_version: str
    debug: DebugPayload | None = Field(default=None, exclude_if=lambda value: value is None)


class DependencyHealth(StrictModel):
    ready: bool
    version: str | None = None
    detail: str | None = None


class HealthResponse(StrictModel):
    alive: bool = True
    ready: bool
    dependencies: dict[str, DependencyHealth]


class ErrorBody(StrictModel):
    code: str
    message: str
    request_id: str
    details: list[Any] = Field(default_factory=list)


class ErrorResponse(StrictModel):
    error: ErrorBody
