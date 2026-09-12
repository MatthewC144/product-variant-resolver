from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias
from uuid import UUID

from .identity import normalize_text
from .retrieval import HashingEmbedding
from .schemas import ExtractedSignals

FAMILY_SCHEMA_VERSION = "pvr-review-family-knowledge-v1"
FAMILY_KNOWLEDGE_VERSION = "review-family-knowledge-fandom-2025-r790665-v1"
FAMILY_MANIFEST_SCHEMA_VERSION = "pvr-review-family-knowledge-manifest-v1"
FAMILY_IDENTITY_NAMESPACE = (
    "product-variant-resolver:review-family:fandom-hot-wheels-wiki"
)
FAMILY_ELIGIBLE_FOR = ["human_knowledge_debug_retrieval"]
FAMILY_EXCLUDED_FROM = [
    "canonical_variant_response",
    "canonical_candidate_ranking",
    "canonical_confidence",
    "canonical_resolution_accuracy",
    "calibration_training",
    "threshold_selection",
    "evaluation_ground_truth",
    "variant_identity",
    "postgresql_ingestion",
]
FAMILY_SEARCHABLE_FIELDS = ["brand", "casting", "aliases"]
FAMILY_DOCUMENT_FIELDS = [
    "knowledge_type",
    "review_family_id",
    "review_family_uuid",
    "identity_level",
    "identity_status",
    "brand",
    "casting",
    "aliases",
    "source_record_ids",
]
FAMILY_PROJECTION_FIELDS = {
    "schema_version",
    "knowledge_version",
    "status",
    "eligible_for",
    "excluded_from",
    "searchable_fields",
    "source",
    "documents",
}
FAMILY_SOURCE_FIELDS = {
    "dataset_version",
    "license",
    "license_url",
    "page_title",
    "page_url",
    "revision_id",
    "revision_timestamp",
    "registry_version",
}
FAMILY_MANIFEST_FIELDS = {
    "schema_version",
    "knowledge_version",
    "inputs",
    "document_count",
    "knowledge_type_counts",
    "document_fields",
    "searchable_fields",
    "eligible_for",
    "excluded_from",
    "accepted_source_record_count",
    "skipped_merge_link_count",
    "skipped_merge_source_record_count",
    "skipped_hold_exclusion_count",
    "skipped_hold_source_record_count",
    "source_held_release_reference_count",
    "provisional_variant_document_count",
    "canonical_promotion_count",
    "postgresql_row_count",
    "projection_file",
    "projection_sha256",
}

HUMAN_KNOWLEDGE_V3_ARTIFACT_SCHEMA = "pvr-human-knowledge-retrieval-artifact-v1"
HUMAN_KNOWLEDGE_V3_RETRIEVER_VERSION = "human-knowledge-hybrid-v3"
HUMAN_KNOWLEDGE_CHARACTER_INDEX_VERSION = "human-knowledge-character-tfidf-v1"
HUMAN_KNOWLEDGE_DEVELOPMENT_VERSION = "family-retrieval-development-v1"
HUMAN_KNOWLEDGE_V3_ALLOWED_FIELDS = {
    "provisional_variant": ["casting", "human_label_names"],
    "review_family": ["casting", "aliases"],
}
HUMAN_KNOWLEDGE_V3_ELIGIBLE_FOR = ["human_knowledge_debug_retrieval"]
HUMAN_KNOWLEDGE_V3_EXCLUDED_FROM = [
    "calibration_training",
    "canonical_candidate_ranking",
    "canonical_confidence",
    "canonical_variant_response",
    "postgresql_ingestion",
    "production_accuracy_claim",
]
HUMAN_KNOWLEDGE_V3_FLOORS = {0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55}
HUMAN_KNOWLEDGE_V3_WEIGHTS = {0.5, 1.0, 1.5}


@dataclass(frozen=True, slots=True)
class HumanVariantKnowledgeDocument:
    casting_uuid: UUID
    casting_id: str
    provisional_variant_uuid: UUID
    provisional_variant_id: str
    brand: str
    casting: str
    series_label: str | None
    variant_label: str | None
    identity_status: str
    human_label_names: tuple[str, ...]
    pricing_keywords: tuple[str, ...]
    initial_names: tuple[str, ...]
    source_case_ids: tuple[str, ...]

    @property
    def knowledge_type(self) -> str:
        return "provisional_variant"

    @property
    def knowledge_uuid(self) -> UUID:
        return self.provisional_variant_uuid

    @property
    def knowledge_id(self) -> str:
        return self.provisional_variant_id

    @property
    def searchable_text(self) -> str:
        values = (
            self.brand,
            self.casting,
            self.series_label,
            self.variant_label,
            *self.human_label_names,
            *self.pricing_keywords,
            *self.initial_names,
        )
        return " ".join(value for value in values if value)

    @property
    def character_identity_texts(self) -> tuple[str, ...]:
        """Strict v3 allowlist: casting and human-verified labels only."""
        return (self.casting, *self.human_label_names)


@dataclass(frozen=True, slots=True)
class ReviewFamilyKnowledgeDocument:
    review_family_uuid: UUID
    review_family_id: str
    brand: str
    casting: str
    aliases: tuple[str, ...]
    source_record_ids: tuple[str, ...]
    identity_status: str

    @property
    def knowledge_type(self) -> str:
        return "review_family"

    @property
    def knowledge_uuid(self) -> UUID:
        return self.review_family_uuid

    @property
    def knowledge_id(self) -> str:
        return self.review_family_id

    @property
    def searchable_text(self) -> str:
        return " ".join((self.brand, self.casting, *self.aliases))

    @property
    def character_identity_texts(self) -> tuple[str, ...]:
        """Strict v3 allowlist: casting and approved aliases only."""
        return (self.casting, *self.aliases)


HumanKnowledgeDocument: TypeAlias = (
    HumanVariantKnowledgeDocument | ReviewFamilyKnowledgeDocument
)


class HumanKnowledgeCatalog:
    def __init__(
        self,
        version: str,
        review_family_version: str,
        documents: list[HumanKnowledgeDocument],
    ) -> None:
        self.version = version
        self.review_family_version = review_family_version
        self.documents = tuple(documents)
        self.variant_document_count = sum(
            isinstance(item, HumanVariantKnowledgeDocument) for item in documents
        )
        self.review_family_document_count = sum(
            isinstance(item, ReviewFamilyKnowledgeDocument) for item in documents
        )


@dataclass(frozen=True, slots=True)
class HumanKnowledgeCandidate:
    document: HumanKnowledgeDocument
    sparse_rank: int | None
    sparse_score: float | None
    dense_rank: int | None
    dense_score: float | None
    rrf_rank: int
    rrf_score: float
    matched_tokens: tuple[str, ...]
    character_rank: int | None = None
    character_score: float | None = None


@dataclass(frozen=True, slots=True)
class HumanKnowledgeV3Config:
    artifact_version: str
    artifact_sha256: str
    character_score_floor: float
    character_rrf_weight: float
    sparse_rrf_weight: float
    dense_rrf_weight: float
    dense_dimensions: int
    rrf_k: int
    source_candidate_limit: int
    index_version: str


@dataclass(frozen=True, slots=True)
class CharacterIndexMetadata:
    version: str
    document_count: int
    posting_count: int
    posting_entry_count: int
    gram_sizes: tuple[int, ...]
    modes: tuple[str, ...]
    window_token_radius: int
    stable_tie_break: str
    allowed_fields: dict[str, list[str]]

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed_fields": self.allowed_fields,
            "document_count": self.document_count,
            "gram_sizes": list(self.gram_sizes),
            "modes": list(self.modes),
            "posting_count": self.posting_count,
            "posting_entry_count": self.posting_entry_count,
            "stable_tie_break": self.stable_tie_break,
            "version": self.version,
            "window_token_radius": self.window_token_radius,
        }


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} could not be read as valid JSON") from error
    if not isinstance(payload, dict):
        raise ValueError(f"{label} root must be an object")
    return payload


def _required_string(value: Any, *, field: str, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context}: {field} must be a non-empty string")
    return value


def _optional_string(value: Any, *, field: str, context: str) -> str | None:
    if value is None:
        return None
    return _required_string(value, field=field, context=context)


def _strings(
    value: Any,
    *,
    field: str,
    context: str,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or (not value and not allow_empty)
        or not all(isinstance(item, str) and item for item in value)
    ):
        raise ValueError(f"{context}: {field} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{context}: {field} contains duplicates")
    return tuple(value)


def _load_variant_documents(path: Path) -> tuple[str, list[HumanVariantKnowledgeDocument]]:
    payload = _load_json_object(path, label="human-backed catalog")
    if not isinstance(payload.get("castings"), list):
        raise ValueError("human-backed catalog must contain castings[]")
    if payload.get("status") != "human_review_draft":
        raise ValueError("human-backed catalog has unsupported status")

    documents: list[HumanVariantKnowledgeDocument] = []
    casting_uuids: set[UUID] = set()
    casting_ids: set[str] = set()
    variant_uuids: set[UUID] = set()
    variant_ids: set[str] = set()
    for casting_index, casting in enumerate(payload["castings"]):
        context = f"casting {casting_index}"
        try:
            casting_uuid = UUID(str(casting["casting_uuid"]))
            casting_id = _required_string(
                casting["casting_id"], field="casting_id", context=context
            )
            if casting_uuid in casting_uuids or casting_id in casting_ids:
                raise ValueError("duplicate casting identity")
            brand = _required_string(casting["brand"], field="brand", context=context)
            casting_name = _required_string(
                casting["casting"], field="casting", context=context
            )
            variants = casting["provisional_variants"]
        except Exception as error:
            raise ValueError(f"{context}: invalid casting") from error
        if not isinstance(variants, list) or not variants:
            raise ValueError(f"{context}: provisional_variants must be non-empty")
        for variant_index, variant in enumerate(variants):
            variant_context = f"{context} variant {variant_index}"
            try:
                variant_uuid = UUID(str(variant["provisional_variant_uuid"]))
                variant_id = _required_string(
                    variant["provisional_variant_id"],
                    field="provisional_variant_id",
                    context=variant_context,
                )
                if variant_uuid in variant_uuids or variant_id in variant_ids:
                    raise ValueError("duplicate provisional variant identity")
                identity_status = _required_string(
                    variant["identity_status"],
                    field="identity_status",
                    context=variant_context,
                )
                if identity_status != "needs_canonical_review":
                    raise ValueError("variant bypasses canonical review")
                document = HumanVariantKnowledgeDocument(
                    casting_uuid=casting_uuid,
                    casting_id=casting_id,
                    provisional_variant_uuid=variant_uuid,
                    provisional_variant_id=variant_id,
                    brand=brand,
                    casting=casting_name,
                    series_label=_optional_string(
                        variant.get("series_label"),
                        field="series_label",
                        context=variant_context,
                    ),
                    variant_label=_optional_string(
                        variant.get("variant_label"),
                        field="variant_label",
                        context=variant_context,
                    ),
                    identity_status=identity_status,
                    human_label_names=_strings(
                        variant.get("human_label_names"),
                        field="human_label_names",
                        context=variant_context,
                    ),
                    pricing_keywords=_strings(
                        variant.get("pricing_keywords"),
                        field="pricing_keywords",
                        context=variant_context,
                    ),
                    initial_names=_strings(
                        variant.get("initial_names", []),
                        field="initial_names",
                        context=variant_context,
                        allow_empty=True,
                    ),
                    source_case_ids=_strings(
                        variant.get("source_case_ids"),
                        field="source_case_ids",
                        context=variant_context,
                    ),
                )
            except Exception as error:
                raise ValueError(f"{variant_context}: invalid provisional variant") from error
            variant_uuids.add(variant_uuid)
            variant_ids.add(variant_id)
            documents.append(document)
        casting_uuids.add(casting_uuid)
        casting_ids.add(casting_id)
    if len(documents) != 100:
        raise ValueError("human-backed catalog must contain exactly 100 provisional variants")
    version = _required_string(
        payload.get("catalog_version"), field="catalog_version", context="human catalog"
    )
    if version != "human-backed-catalog-v1":
        raise ValueError("human-backed catalog has an unsupported version")
    return version, documents


def _validate_family_manifest(
    projection_path: Path,
    projection: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    if set(projection) != FAMILY_PROJECTION_FIELDS:
        raise ValueError("review-family projection fields differ from contract")
    if set(manifest) != FAMILY_MANIFEST_FIELDS:
        raise ValueError("review-family projection manifest fields differ from contract")
    if projection.get("schema_version") != FAMILY_SCHEMA_VERSION:
        raise ValueError("review-family projection has an unsupported schema")
    if projection.get("knowledge_version") != FAMILY_KNOWLEDGE_VERSION:
        raise ValueError("review-family projection has an unsupported version")
    if projection.get("status") != "debug_retrieval_only":
        raise ValueError("review-family projection has an unsupported status")
    if projection.get("eligible_for") != FAMILY_ELIGIBLE_FOR:
        raise ValueError("review-family projection eligibility boundary was widened")
    if projection.get("excluded_from") != FAMILY_EXCLUDED_FROM:
        raise ValueError("review-family projection exclusion boundary was widened")
    if projection.get("searchable_fields") != FAMILY_SEARCHABLE_FIELDS:
        raise ValueError("review-family projection searchable fields were widened")

    if manifest.get("schema_version") != FAMILY_MANIFEST_SCHEMA_VERSION:
        raise ValueError("review-family projection manifest has an unsupported schema")
    if manifest.get("knowledge_version") != FAMILY_KNOWLEDGE_VERSION:
        raise ValueError("review-family projection manifest has an unsupported version")
    if manifest.get("projection_file") != projection_path.name:
        raise ValueError("review-family projection filename differs from manifest")
    try:
        projection_sha256 = hashlib.sha256(projection_path.read_bytes()).hexdigest()
    except OSError as error:
        raise ValueError("review-family projection checksum could not be read") from error
    if manifest.get("projection_sha256") != projection_sha256:
        raise ValueError("review-family projection checksum differs from manifest")
    if manifest.get("document_fields") != FAMILY_DOCUMENT_FIELDS:
        raise ValueError("review-family projection document fields were widened")
    if manifest.get("searchable_fields") != FAMILY_SEARCHABLE_FIELDS:
        raise ValueError("review-family manifest searchable fields were widened")
    if manifest.get("eligible_for") != FAMILY_ELIGIBLE_FOR:
        raise ValueError("review-family manifest eligibility boundary was widened")
    if manifest.get("excluded_from") != FAMILY_EXCLUDED_FROM:
        raise ValueError("review-family manifest exclusion boundary was widened")

    expected_values: dict[str, Any] = {
        "document_count": 42,
        "knowledge_type_counts": {"review_family": 42},
        "accepted_source_record_count": 79,
        "skipped_merge_link_count": 4,
        "skipped_merge_source_record_count": 9,
        "skipped_hold_exclusion_count": 7,
        "skipped_hold_source_record_count": 12,
        "source_held_release_reference_count": 100,
        "provisional_variant_document_count": 0,
        "canonical_promotion_count": 0,
        "postgresql_row_count": 0,
    }
    for field, expected in expected_values.items():
        if manifest.get(field) != expected:
            raise ValueError(f"review-family projection manifest {field} differs from contract")

    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != {
        "review_family_registry",
        "review_family_registry_manifest",
    }:
        raise ValueError("review-family projection input references differ from contract")
    registry = inputs["review_family_registry"]
    registry_manifest = inputs["review_family_registry_manifest"]
    if not isinstance(registry, dict) or set(registry) != {"file", "sha256", "version"}:
        raise ValueError("review-family registry reference differs from contract")
    if not isinstance(registry_manifest, dict) or set(registry_manifest) != {"file", "sha256"}:
        raise ValueError("review-family registry-manifest reference differs from contract")
    if registry.get("file") != "review_family_registry.json" or registry.get(
        "version"
    ) != "fandom-2025-review-families-r790665-v1":
        raise ValueError("review-family registry reference has an unsupported identity")
    if registry_manifest.get("file") != "review_family_registry_manifest.json":
        raise ValueError("review-family registry-manifest filename differs from contract")
    for reference in (registry, registry_manifest):
        if not isinstance(reference.get("sha256"), str) or not re.fullmatch(
            r"[0-9a-f]{64}", reference["sha256"]
        ):
            raise ValueError("review-family input reference has an invalid checksum")


def _load_family_documents(
    projection_path: Path, manifest_path: Path
) -> tuple[str, list[ReviewFamilyKnowledgeDocument]]:
    projection = _load_json_object(projection_path, label="review-family projection")
    manifest = _load_json_object(manifest_path, label="review-family projection manifest")
    _validate_family_manifest(projection_path, projection, manifest)

    source = projection.get("source")
    if not isinstance(source, dict) or set(source) != FAMILY_SOURCE_FIELDS:
        raise ValueError("review-family projection source fields differ from contract")
    for field in (
        "dataset_version",
        "license",
        "license_url",
        "page_title",
        "page_url",
        "revision_timestamp",
        "registry_version",
    ):
        _required_string(source.get(field), field=field, context="family source")
    if (
        source.get("dataset_version") != "fandom-hot-wheels-2025-pilot-r790665-v1"
        or source.get("revision_id") != 790665
        or source.get("registry_version") != "fandom-2025-review-families-r790665-v1"
        or source.get("license") != "CC-BY-SA"
    ):
        raise ValueError("review-family projection source identity differs from contract")

    values = projection.get("documents")
    if not isinstance(values, list) or len(values) != 42:
        raise ValueError("review-family projection must contain exactly 42 documents")
    documents: list[ReviewFamilyKnowledgeDocument] = []
    ids: set[str] = set()
    uuids: set[UUID] = set()
    normalized_keys: set[tuple[str, str]] = set()
    source_record_ids: set[str] = set()
    encountered_ids: list[str] = []
    for index, value in enumerate(values):
        context = f"review-family document {index}"
        if not isinstance(value, dict):
            raise ValueError(f"{context}: document must be an object")
        if set(value) != set(FAMILY_DOCUMENT_FIELDS):
            raise ValueError(f"{context}: fields differ from contract")
        family_id = _required_string(
            value.get("review_family_id"), field="review_family_id", context=context
        )
        if not re.fullmatch(r"fandom-family-[0-9a-f]{16}", family_id):
            raise ValueError(f"{context}: review-family ID differs from contract")
        try:
            family_uuid = UUID(
                _required_string(
                    value.get("review_family_uuid"),
                    field="review_family_uuid",
                    context=family_id,
                )
            )
        except ValueError as error:
            raise ValueError(f"{family_id}: review-family UUID is invalid") from error
        expected_uuid = UUID(
            str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"{FAMILY_IDENTITY_NAMESPACE}:{family_id}",
                )
            )
        )
        if family_uuid != expected_uuid:
            raise ValueError(f"{family_id}: review-family UUID is not source-stable")
        if family_id in ids or family_uuid in uuids:
            raise ValueError("review-family projection contains duplicate identity")
        if value.get("knowledge_type") != "review_family":
            raise ValueError(f"{family_id}: unsupported knowledge type")
        if value.get("identity_level") != "casting_family_only":
            raise ValueError(f"{family_id}: unsupported identity level")
        if value.get("identity_status") != "family_accepted_variants_unreviewed":
            raise ValueError(f"{family_id}: unsupported identity status")
        brand = _required_string(value.get("brand"), field="brand", context=family_id)
        casting = _required_string(
            value.get("casting"), field="casting", context=family_id
        )
        aliases = _strings(value.get("aliases"), field="aliases", context=family_id)
        if aliases != (casting,):
            raise ValueError(f"{family_id}: aliases differ from the frozen v1 contract")
        document_source_ids = _strings(
            value.get("source_record_ids"),
            field="source_record_ids",
            context=family_id,
        )
        if tuple(sorted(document_source_ids)) != document_source_ids:
            raise ValueError(f"{family_id}: source record IDs are not sorted")
        if any(
            not re.fullmatch(r"fandom-row-[0-9a-f]{16}", item)
            for item in document_source_ids
        ):
            raise ValueError(f"{family_id}: source record ID differs from contract")
        if source_record_ids & set(document_source_ids):
            raise ValueError("review-family projection contains duplicate source records")
        normalized_key = (normalize_text(brand), normalize_text(casting))
        if not all(normalized_key):
            raise ValueError(f"{family_id}: normalized family identity is empty")
        if normalized_key in normalized_keys:
            raise ValueError("review-family projection contains duplicate family identity")

        documents.append(
            ReviewFamilyKnowledgeDocument(
                review_family_uuid=family_uuid,
                review_family_id=family_id,
                brand=brand,
                casting=casting,
                aliases=aliases,
                source_record_ids=document_source_ids,
                identity_status="family_accepted_variants_unreviewed",
            )
        )
        ids.add(family_id)
        uuids.add(family_uuid)
        normalized_keys.add(normalized_key)
        source_record_ids.update(document_source_ids)
        encountered_ids.append(family_id)
    if encountered_ids != sorted(encountered_ids):
        raise ValueError("review-family projection documents are not deterministically ordered")
    if len(source_record_ids) != 79:
        raise ValueError("review-family projection must reference exactly 79 accepted source rows")
    return FAMILY_KNOWLEDGE_VERSION, documents


def load_human_knowledge_catalog(
    human_catalog_path: Path,
    review_family_path: Path,
    review_family_manifest_path: Path,
) -> HumanKnowledgeCatalog:
    version, variant_documents = _load_variant_documents(human_catalog_path)
    family_version, family_documents = _load_family_documents(
        review_family_path, review_family_manifest_path
    )
    documents: list[HumanKnowledgeDocument] = [*variant_documents, *family_documents]
    knowledge_ids = [item.knowledge_id for item in documents]
    knowledge_uuids = [item.knowledge_uuid for item in documents]
    if len(knowledge_ids) != len(set(knowledge_ids)):
        raise ValueError("human knowledge contains duplicate global knowledge IDs")
    if len(knowledge_uuids) != len(set(knowledge_uuids)):
        raise ValueError("human knowledge contains duplicate global knowledge UUIDs")
    if len(documents) != 142:
        raise ValueError("human knowledge must contain exactly 142 documents")
    return HumanKnowledgeCatalog(version, family_version, documents)


def _file_sha256(path: Path, *, label: str) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ValueError(f"{label} checksum could not be read") from error


def _artifact_reference(
    value: Any,
    *,
    label: str,
    path: Path,
    version: str,
) -> None:
    if not isinstance(value, dict) or set(value) != {"file", "sha256", "version"}:
        raise ValueError(f"v3 artifact {label} reference differs from contract")
    if (
        Path(str(value.get("file"))).name != path.name
        or value.get("version") != version
        or value.get("sha256") != _file_sha256(path, label=label)
    ):
        raise ValueError(f"v3 artifact {label} reference is stale or mismatched")


def load_human_knowledge_v3_config(
    artifact_path: Path,
    *,
    human_catalog_path: Path,
    review_family_path: Path,
    development_pack_path: Path,
    development_manifest_path: Path,
    dense_dimensions: int,
) -> HumanKnowledgeV3Config:
    """Load a selected v3 runtime config; arbitrary environment floats are not accepted."""
    artifact = _load_json_object(artifact_path, label="human knowledge v3 artifact")
    if set(artifact) != {
        "artifact_version",
        "character_index",
        "configuration",
        "eligible_for",
        "excluded_from",
        "implementation",
        "retriever_version",
        "schema_version",
        "sources",
        "status",
    }:
        raise ValueError("v3 artifact fields differ from contract")
    artifact_version = _required_string(
        artifact.get("artifact_version"),
        field="artifact_version",
        context="v3 artifact",
    )
    if not re.fullmatch(r"human-knowledge-retrieval-v3-[a-z0-9-]+", artifact_version):
        raise ValueError("v3 artifact version differs from contract")
    if (
        artifact.get("schema_version") != HUMAN_KNOWLEDGE_V3_ARTIFACT_SCHEMA
        or artifact.get("retriever_version") != HUMAN_KNOWLEDGE_V3_RETRIEVER_VERSION
        or artifact.get("status") != "selected_development_configuration"
        or artifact.get("eligible_for") != HUMAN_KNOWLEDGE_V3_ELIGIBLE_FOR
        or artifact.get("excluded_from") != HUMAN_KNOWLEDGE_V3_EXCLUDED_FROM
    ):
        raise ValueError("v3 artifact identity or usage boundary differs from contract")

    character_index = artifact.get("character_index")
    expected_index = {
        "allowed_fields": HUMAN_KNOWLEDGE_V3_ALLOWED_FIELDS,
        "gram_sizes": [2, 3],
        "modes": ["spaced", "compact"],
        "stable_tie_break": "knowledge_uuid",
        "version": HUMAN_KNOWLEDGE_CHARACTER_INDEX_VERSION,
        "window_token_radius": 1,
    }
    if character_index != expected_index:
        raise ValueError("v3 artifact character-index contract differs from implementation")

    configuration = artifact.get("configuration")
    if not isinstance(configuration, dict) or set(configuration) != {
        "character_rrf_weight",
        "character_score_floor",
        "dense_dimensions",
        "dense_rrf_weight",
        "rrf_k",
        "selection_candidate_limit",
        "source_candidate_limit",
        "sparse_rrf_weight",
    }:
        raise ValueError("v3 artifact configuration fields differ from contract")
    try:
        floor = float(configuration["character_score_floor"])
        character_weight = float(configuration["character_rrf_weight"])
        sparse_weight = float(configuration["sparse_rrf_weight"])
        dense_weight = float(configuration["dense_rrf_weight"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("v3 artifact numeric configuration is invalid") from error
    if (
        not all(
            math.isfinite(value)
            for value in (floor, character_weight, sparse_weight, dense_weight)
        )
        or floor not in HUMAN_KNOWLEDGE_V3_FLOORS
        or character_weight not in HUMAN_KNOWLEDGE_V3_WEIGHTS
        or sparse_weight != 1.0
        or dense_weight != 1.0
        or configuration.get("rrf_k") != 60
        or configuration.get("selection_candidate_limit") != 5
        or configuration.get("source_candidate_limit") != 25
        or configuration.get("dense_dimensions") != dense_dimensions
    ):
        raise ValueError("v3 artifact configuration is unsupported or mismatched")

    development = _load_json_object(development_pack_path, label="development pack")
    development_manifest = _load_json_object(
        development_manifest_path, label="development pack manifest"
    )
    if (
        development.get("development_version") != HUMAN_KNOWLEDGE_DEVELOPMENT_VERSION
        or development.get("status") != "frozen_development_only"
        or development.get("split") != "dev"
        or development.get("retrieval_executed") is not False
        or development.get("configuration_output_viewed") is not False
        or len(development.get("cases", [])) != 199
    ):
        raise ValueError("development pack is not a valid pre-output freeze")
    development_sha256 = _file_sha256(development_pack_path, label="development pack")
    if (
        development_manifest.get("development_version")
        != HUMAN_KNOWLEDGE_DEVELOPMENT_VERSION
        or development_manifest.get("status") != "frozen_before_configuration_execution"
        or development_manifest.get("development_sha256") != development_sha256
        or development_manifest.get("retrieval_executed") is not False
        or development_manifest.get("configuration_output_viewed") is not False
    ):
        raise ValueError("development manifest is stale, widened, or post-output")

    sources = artifact.get("sources")
    if not isinstance(sources, dict) or set(sources) != {
        "development_manifest",
        "development_pack",
        "human_catalog",
        "review_family_knowledge",
    }:
        raise ValueError("v3 artifact source references differ from contract")
    _artifact_reference(
        sources["human_catalog"],
        label="human catalog",
        path=human_catalog_path,
        version="human-backed-catalog-v1",
    )
    _artifact_reference(
        sources["review_family_knowledge"],
        label="review-family knowledge",
        path=review_family_path,
        version=FAMILY_KNOWLEDGE_VERSION,
    )
    _artifact_reference(
        sources["development_pack"],
        label="development pack",
        path=development_pack_path,
        version=HUMAN_KNOWLEDGE_DEVELOPMENT_VERSION,
    )
    _artifact_reference(
        sources["development_manifest"],
        label="development manifest",
        path=development_manifest_path,
        version=HUMAN_KNOWLEDGE_DEVELOPMENT_VERSION,
    )

    implementation = artifact.get("implementation")
    implementation_path = Path(__file__)
    if not isinstance(implementation, dict) or set(implementation) != {"file", "sha256"}:
        raise ValueError("v3 artifact implementation reference differs from contract")
    if (
        implementation.get("file") != implementation_path.name
        or implementation.get("sha256")
        != _file_sha256(implementation_path, label="human knowledge implementation")
    ):
        raise ValueError("v3 artifact implementation reference is stale or mismatched")

    return HumanKnowledgeV3Config(
        artifact_version=artifact_version,
        artifact_sha256=_file_sha256(artifact_path, label="v3 artifact"),
        character_score_floor=floor,
        character_rrf_weight=character_weight,
        sparse_rrf_weight=sparse_weight,
        dense_rrf_weight=dense_weight,
        dense_dimensions=dense_dimensions,
        rrf_k=60,
        source_candidate_limit=25,
        index_version=HUMAN_KNOWLEDGE_CHARACTER_INDEX_VERSION,
    )


@dataclass(frozen=True, slots=True)
class _CharacterForm:
    mode: str
    token_count: int
    weights: dict[str, float]
    norm: float


def _character_grams(value: str) -> Counter[str]:
    return Counter(
        value[index : index + size]
        for size in (2, 3)
        for index in range(max(0, len(value) - size + 1))
    )


class CharacterIdentityIndex:
    """In-memory character TF-IDF posting index over allowlisted identity fields."""

    def __init__(self, documents: tuple[HumanKnowledgeDocument, ...]) -> None:
        if not documents:
            raise ValueError("character index requires at least one document")
        self._documents = {item.knowledge_uuid: item for item in documents}
        if len(self._documents) != len(documents):
            raise ValueError("character index contains duplicate knowledge UUIDs")

        raw_forms: dict[UUID, list[tuple[str, int, Counter[str]]]] = {}
        document_grams: dict[UUID, set[tuple[str, str]]] = {}
        identity_lengths: set[int] = set()
        for document in documents:
            forms: list[tuple[str, int, Counter[str]]] = []
            seen: set[tuple[str, str]] = set()
            for value in document.character_identity_texts:
                normalized = normalize_text(value)
                if not normalized:
                    raise ValueError("character identity text normalizes to empty")
                token_count = len(normalized.split())
                identity_lengths.add(token_count)
                for mode, text in (
                    ("spaced", normalized),
                    ("compact", normalized.replace(" ", "")),
                ):
                    if (mode, text) in seen:
                        continue
                    seen.add((mode, text))
                    grams = _character_grams(text)
                    if not grams:
                        raise ValueError("character identity text is too short for bigrams")
                    forms.append((mode, token_count, grams))
            if not forms:
                raise ValueError("character index document has no identity forms")
            raw_forms[document.knowledge_uuid] = forms
            document_grams[document.knowledge_uuid] = {
                (mode, gram) for mode, _, grams in forms for gram in grams
            }

        total = len(documents)
        frequencies = Counter(
            key for keys in document_grams.values() for key in keys
        )
        self._idf = {
            key: math.log((total + 1) / (frequency + 1)) + 1
            for key, frequency in frequencies.items()
        }
        postings: dict[tuple[str, str], set[UUID]] = {}
        for document_uuid, keys in document_grams.items():
            for key in keys:
                postings.setdefault(key, set()).add(document_uuid)
        self._postings = {
            key: tuple(sorted(values, key=str)) for key, values in postings.items()
        }
        self._forms = {
            document_uuid: tuple(
                self._weighted_form(mode, token_count, grams)
                for mode, token_count, grams in forms
            )
            for document_uuid, forms in raw_forms.items()
        }
        self._identity_lengths = tuple(sorted(identity_lengths))
        self.metadata = CharacterIndexMetadata(
            version=HUMAN_KNOWLEDGE_CHARACTER_INDEX_VERSION,
            document_count=total,
            posting_count=len(self._postings),
            posting_entry_count=sum(len(values) for values in self._postings.values()),
            gram_sizes=(2, 3),
            modes=("spaced", "compact"),
            window_token_radius=1,
            stable_tie_break="knowledge_uuid",
            allowed_fields={
                key: list(value) for key, value in HUMAN_KNOWLEDGE_V3_ALLOWED_FIELDS.items()
            },
        )

    def _weighted_form(
        self, mode: str, token_count: int, grams: Counter[str]
    ) -> _CharacterForm:
        weights = {
            gram: count * self._idf[(mode, gram)]
            for gram, count in grams.items()
            if (mode, gram) in self._idf
        }
        norm = math.sqrt(sum(weight * weight for weight in weights.values()))
        return _CharacterForm(mode, token_count, weights, norm)

    def _query_forms(self, query: str) -> tuple[_CharacterForm, ...]:
        tokens = normalize_text(query).split()
        if not tokens:
            return ()
        windows: set[str] = set()
        for identity_length in self._identity_lengths:
            for size in range(max(1, identity_length - 1), identity_length + 2):
                if size > len(tokens):
                    continue
                windows.update(
                    " ".join(tokens[index : index + size])
                    for index in range(len(tokens) - size + 1)
                )
        forms: list[_CharacterForm] = []
        for window in sorted(windows):
            token_count = len(window.split())
            for mode, text in (("spaced", window), ("compact", window.replace(" ", ""))):
                form = self._weighted_form(mode, token_count, _character_grams(text))
                if form.norm > 0:
                    forms.append(form)
        return tuple(forms)

    @staticmethod
    def _cosine(left: _CharacterForm, right: _CharacterForm) -> float:
        if left.mode != right.mode or left.norm <= 0 or right.norm <= 0:
            return 0.0
        smaller, larger = (
            (left.weights, right.weights)
            if len(left.weights) <= len(right.weights)
            else (right.weights, left.weights)
        )
        dot = sum(weight * larger.get(gram, 0.0) for gram, weight in smaller.items())
        return dot / (left.norm * right.norm)

    def rank(self, query: str, *, score_floor: float) -> list[tuple[HumanKnowledgeDocument, float]]:
        if not math.isfinite(score_floor) or not 0 < score_floor <= 1:
            raise ValueError("character score floor must be finite and between 0 and 1")
        query_forms = self._query_forms(query)
        candidate_ids: set[UUID] = set()
        for form in query_forms:
            candidate_ids.update(
                document_uuid
                for gram in form.weights
                for document_uuid in self._postings.get((form.mode, gram), ())
            )
        scored: list[tuple[HumanKnowledgeDocument, float]] = []
        for document_uuid in candidate_ids:
            score = max(
                (
                    self._cosine(query_form, document_form)
                    for query_form in query_forms
                    for document_form in self._forms[document_uuid]
                ),
                default=0.0,
            )
            if not math.isfinite(score):
                raise ValueError("character index produced a non-finite score")
            if score >= score_floor:
                scored.append((self._documents[document_uuid], score))
        return sorted(scored, key=lambda item: (-item[1], str(item[0].knowledge_uuid)))


class HumanKnowledgeRetriever:
    """Second, non-canonical RAG source backed by reviewed human knowledge."""

    version = "human-knowledge-hybrid-v2"

    def __init__(
        self,
        catalog: HumanKnowledgeCatalog,
        embedding: HashingEmbedding,
        v3_config: HumanKnowledgeV3Config | None = None,
    ) -> None:
        self.catalog = catalog
        self.embedding = embedding
        self.v3_config = v3_config
        if v3_config is not None and (
            v3_config.index_version != HUMAN_KNOWLEDGE_CHARACTER_INDEX_VERSION
            or v3_config.character_score_floor not in HUMAN_KNOWLEDGE_V3_FLOORS
            or v3_config.character_rrf_weight not in HUMAN_KNOWLEDGE_V3_WEIGHTS
            or v3_config.sparse_rrf_weight != 1.0
            or v3_config.dense_rrf_weight != 1.0
            or v3_config.dense_dimensions != embedding.dimensions
            or v3_config.rrf_k != 60
            or v3_config.source_candidate_limit != 25
        ):
            raise ValueError("human knowledge v3 configuration is unsupported")
        self.version = (
            HUMAN_KNOWLEDGE_V3_RETRIEVER_VERSION
            if v3_config is not None
            else "human-knowledge-hybrid-v2"
        )
        self.artifact_version = v3_config.artifact_version if v3_config else None
        self.artifact_sha256 = v3_config.artifact_sha256 if v3_config else None
        self._tokens = {
            item.knowledge_uuid: set(normalize_text(item.searchable_text).split())
            for item in catalog.documents
        }
        self._vectors = {
            item.knowledge_uuid: embedding.encode(item.searchable_text)
            for item in catalog.documents
        }
        self.character_index = (
            CharacterIdentityIndex(catalog.documents) if v3_config is not None else None
        )

    @property
    def character_index_metadata(self) -> dict[str, Any] | None:
        return self.character_index.metadata.as_dict() if self.character_index else None

    def retrieve(
        self,
        signals: ExtractedSignals,
        limit: int,
    ) -> list[HumanKnowledgeCandidate]:
        if not 1 <= limit <= 25:
            raise ValueError("human knowledge limit must be between 1 and 25")
        if self.v3_config is not None:
            return self._retrieve_v3(signals, limit)
        return self._retrieve_v2(signals, limit)

    def _retrieve_v2(
        self,
        signals: ExtractedSignals,
        limit: int,
    ) -> list[HumanKnowledgeCandidate]:
        query_tokens = set(signals.tokens)
        if not query_tokens:
            return []

        eligible = [
            document
            for document in self.catalog.documents
            if query_tokens & self._tokens[document.knowledge_uuid]
        ]
        if not eligible:
            return []

        frequencies = {
            token: sum(
                token in self._tokens[document.knowledge_uuid]
                for document in self.catalog.documents
            )
            for token in query_tokens
        }
        total = len(self.catalog.documents)
        sparse_scores = {
            document.knowledge_uuid: sum(
                math.log((total + 1) / (frequencies[token] + 1)) + 1
                for token in query_tokens & self._tokens[document.knowledge_uuid]
            )
            for document in eligible
        }
        query_vector = self.embedding.encode(signals.normalized_title)
        dense_scores = {
            document.knowledge_uuid: sum(
                left * right
                for left, right in zip(
                    query_vector,
                    self._vectors[document.knowledge_uuid],
                    strict=True,
                )
            )
            for document in eligible
        }
        sparse_order = sorted(
            eligible,
            key=lambda item: (
                -sparse_scores[item.knowledge_uuid],
                str(item.knowledge_uuid),
            ),
        )
        dense_order = sorted(
            eligible,
            key=lambda item: (
                -dense_scores[item.knowledge_uuid],
                str(item.knowledge_uuid),
            ),
        )
        sparse_ranks = {
            item.knowledge_uuid: rank for rank, item in enumerate(sparse_order, start=1)
        }
        dense_ranks = {
            item.knowledge_uuid: rank for rank, item in enumerate(dense_order, start=1)
        }
        fused = sorted(
            eligible,
            key=lambda item: (
                -(
                    1 / (60 + sparse_ranks[item.knowledge_uuid])
                    + 1 / (60 + dense_ranks[item.knowledge_uuid])
                ),
                str(item.knowledge_uuid),
            ),
        )[:limit]
        candidates: list[HumanKnowledgeCandidate] = []
        for rank, document in enumerate(fused, start=1):
            item_uuid = document.knowledge_uuid
            candidates.append(
                HumanKnowledgeCandidate(
                    document=document,
                    sparse_rank=sparse_ranks[item_uuid],
                    sparse_score=sparse_scores[item_uuid],
                    dense_rank=dense_ranks[item_uuid],
                    dense_score=dense_scores[item_uuid],
                    character_rank=None,
                    character_score=None,
                    rrf_rank=rank,
                    rrf_score=(
                        1 / (60 + sparse_ranks[item_uuid])
                        + 1 / (60 + dense_ranks[item_uuid])
                    ),
                    matched_tokens=tuple(sorted(query_tokens & self._tokens[item_uuid])),
                )
            )
        return candidates

    def _retrieve_v3(
        self,
        signals: ExtractedSignals,
        limit: int,
    ) -> list[HumanKnowledgeCandidate]:
        config = self.v3_config
        character_index = self.character_index
        if config is None or character_index is None:
            raise RuntimeError("v3 retrieval was requested without a ready character index")
        query_tokens = set(signals.tokens)
        if not query_tokens:
            return []

        frequencies = {
            token: sum(
                token in self._tokens[document.knowledge_uuid]
                for document in self.catalog.documents
            )
            for token in query_tokens
        }
        total = len(self.catalog.documents)
        sparse_scores = {
            document.knowledge_uuid: sum(
                math.log((total + 1) / (frequencies[token] + 1)) + 1
                for token in query_tokens & self._tokens[document.knowledge_uuid]
            )
            for document in self.catalog.documents
            if query_tokens & self._tokens[document.knowledge_uuid]
        }
        sparse_order = sorted(
            (
                document
                for document in self.catalog.documents
                if document.knowledge_uuid in sparse_scores
            ),
            key=lambda item: (-sparse_scores[item.knowledge_uuid], str(item.knowledge_uuid)),
        )[: config.source_candidate_limit]
        sparse_scores = {
            item.knowledge_uuid: sparse_scores[item.knowledge_uuid] for item in sparse_order
        }

        character_order_with_scores = character_index.rank(
            signals.normalized_title,
            score_floor=config.character_score_floor,
        )[: config.source_candidate_limit]
        character_scores = {
            item.knowledge_uuid: score for item, score in character_order_with_scores
        }
        document_by_uuid = {
            item.knowledge_uuid: item for item in self.catalog.documents
        }
        union_ids = set(sparse_scores) | set(character_scores)
        if not union_ids:
            return []
        eligible = [document_by_uuid[item_uuid] for item_uuid in sorted(union_ids, key=str)]

        query_vector = self.embedding.encode(signals.normalized_title)
        dense_scores = {
            document.knowledge_uuid: sum(
                left * right
                for left, right in zip(
                    query_vector,
                    self._vectors[document.knowledge_uuid],
                    strict=True,
                )
            )
            for document in eligible
        }
        if any(not math.isfinite(score) for score in dense_scores.values()):
            raise ValueError("human knowledge dense retrieval produced a non-finite score")
        dense_order = sorted(
            eligible,
            key=lambda item: (-dense_scores[item.knowledge_uuid], str(item.knowledge_uuid)),
        )
        sparse_ranks = {
            item.knowledge_uuid: rank for rank, item in enumerate(sparse_order, start=1)
        }
        dense_ranks = {
            item.knowledge_uuid: rank for rank, item in enumerate(dense_order, start=1)
        }
        character_ranks = {
            item.knowledge_uuid: rank
            for rank, (item, _) in enumerate(character_order_with_scores, start=1)
        }

        def fused_score(document: HumanKnowledgeDocument) -> float:
            item_uuid = document.knowledge_uuid
            score = config.dense_rrf_weight / (config.rrf_k + dense_ranks[item_uuid])
            if sparse_rank := sparse_ranks.get(item_uuid):
                score += config.sparse_rrf_weight / (config.rrf_k + sparse_rank)
            if character_rank := character_ranks.get(item_uuid):
                score += config.character_rrf_weight / (
                    config.rrf_k + character_rank
                )
            return score

        rrf_scores = {item.knowledge_uuid: fused_score(item) for item in eligible}
        if any(not math.isfinite(score) for score in rrf_scores.values()):
            raise ValueError("human knowledge fusion produced a non-finite score")
        fused = sorted(
            eligible,
            key=lambda item: (-rrf_scores[item.knowledge_uuid], str(item.knowledge_uuid)),
        )[:limit]
        return [
            HumanKnowledgeCandidate(
                document=document,
                sparse_rank=sparse_ranks.get(document.knowledge_uuid),
                sparse_score=sparse_scores.get(document.knowledge_uuid),
                dense_rank=dense_ranks[document.knowledge_uuid],
                dense_score=dense_scores[document.knowledge_uuid],
                character_rank=character_ranks.get(document.knowledge_uuid),
                character_score=character_scores.get(document.knowledge_uuid),
                rrf_rank=rank,
                rrf_score=rrf_scores[document.knowledge_uuid],
                matched_tokens=tuple(
                    sorted(query_tokens & self._tokens[document.knowledge_uuid])
                ),
            )
            for rank, document in enumerate(fused, start=1)
        ]
