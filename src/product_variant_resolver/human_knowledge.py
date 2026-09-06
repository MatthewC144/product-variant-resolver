from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from .identity import normalize_text
from .retrieval import HashingEmbedding
from .schemas import ExtractedSignals


@dataclass(frozen=True, slots=True)
class HumanKnowledgeDocument:
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


class HumanKnowledgeCatalog:
    def __init__(self, version: str, documents: list[HumanKnowledgeDocument]) -> None:
        self.version = version
        self.documents = tuple(documents)


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
    return tuple(value)


def load_human_knowledge_catalog(path: Path) -> HumanKnowledgeCatalog:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict) or not isinstance(payload.get("castings"), list):
        raise ValueError("human-backed catalog must contain castings[]")
    if payload.get("status") != "human_review_draft":
        raise ValueError("human-backed catalog has unsupported status")

    documents: list[HumanKnowledgeDocument] = []
    casting_ids: set[UUID] = set()
    variant_ids: set[UUID] = set()
    for casting_index, casting in enumerate(payload["castings"]):
        context = f"casting {casting_index}"
        try:
            casting_uuid = UUID(str(casting["casting_uuid"]))
            if casting_uuid in casting_ids:
                raise ValueError("duplicate casting UUID")
            casting_id = _required_string(
                casting["casting_id"], field="casting_id", context=context
            )
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
                if variant_uuid in variant_ids:
                    raise ValueError("duplicate provisional variant UUID")
                identity_status = _required_string(
                    variant["identity_status"],
                    field="identity_status",
                    context=variant_context,
                )
                if identity_status != "needs_canonical_review":
                    raise ValueError("variant bypasses canonical review")
                document = HumanKnowledgeDocument(
                    casting_uuid=casting_uuid,
                    casting_id=casting_id,
                    provisional_variant_uuid=variant_uuid,
                    provisional_variant_id=_required_string(
                        variant["provisional_variant_id"],
                        field="provisional_variant_id",
                        context=variant_context,
                    ),
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
            variant_ids.add(variant_uuid)
            documents.append(document)
        casting_ids.add(casting_uuid)
    if not documents:
        raise ValueError("human-backed catalog contains no provisional variants")
    version = str(payload.get("catalog_version") or "unknown")
    return HumanKnowledgeCatalog(version, documents)


class HumanKnowledgeRetriever:
    """Second, non-canonical RAG source backed by confirmed human labels."""

    version = "human-knowledge-hybrid-v1"

    def __init__(
        self,
        catalog: HumanKnowledgeCatalog,
        embedding: HashingEmbedding,
    ) -> None:
        self.catalog = catalog
        self.embedding = embedding
        self._tokens = {
            item.provisional_variant_uuid: set(normalize_text(item.searchable_text).split())
            for item in catalog.documents
        }
        self._vectors = {
            item.provisional_variant_uuid: embedding.encode(item.searchable_text)
            for item in catalog.documents
        }

    def retrieve(
        self,
        signals: ExtractedSignals,
        limit: int,
    ) -> list[HumanKnowledgeCandidate]:
        if not 1 <= limit <= 25:
            raise ValueError("human knowledge limit must be between 1 and 25")
        query_tokens = set(signals.tokens)
        if not query_tokens:
            return []

        eligible = [
            document
            for document in self.catalog.documents
            if query_tokens & self._tokens[document.provisional_variant_uuid]
        ]
        if not eligible:
            return []

        frequencies = {
            token: sum(
                token in self._tokens[document.provisional_variant_uuid]
                for document in self.catalog.documents
            )
            for token in query_tokens
        }
        total = len(self.catalog.documents)
        sparse_scores = {
            document.provisional_variant_uuid: sum(
                math.log((total + 1) / (frequencies[token] + 1)) + 1
                for token in query_tokens & self._tokens[document.provisional_variant_uuid]
            )
            for document in eligible
        }
        query_vector = self.embedding.encode(signals.normalized_title)
        dense_scores = {
            document.provisional_variant_uuid: sum(
                left * right
                for left, right in zip(
                    query_vector,
                    self._vectors[document.provisional_variant_uuid],
                    strict=True,
                )
            )
            for document in eligible
        }
        sparse_order = sorted(
            eligible,
            key=lambda item: (-sparse_scores[item.provisional_variant_uuid], str(item.provisional_variant_uuid)),
        )
        dense_order = sorted(
            eligible,
            key=lambda item: (-dense_scores[item.provisional_variant_uuid], str(item.provisional_variant_uuid)),
        )
        sparse_ranks = {
            item.provisional_variant_uuid: rank
            for rank, item in enumerate(sparse_order, start=1)
        }
        dense_ranks = {
            item.provisional_variant_uuid: rank for rank, item in enumerate(dense_order, start=1)
        }
        fused = sorted(
            eligible,
            key=lambda item: (
                -(1 / (60 + sparse_ranks[item.provisional_variant_uuid])
                  + 1 / (60 + dense_ranks[item.provisional_variant_uuid])),
                str(item.provisional_variant_uuid),
            ),
        )[:limit]
        candidates: list[HumanKnowledgeCandidate] = []
        for rank, document in enumerate(fused, start=1):
            item_uuid = document.provisional_variant_uuid
            candidates.append(
                HumanKnowledgeCandidate(
                    document=document,
                    sparse_rank=sparse_ranks[item_uuid],
                    sparse_score=sparse_scores[item_uuid],
                    dense_rank=dense_ranks[item_uuid],
                    dense_score=dense_scores[item_uuid],
                    rrf_rank=rank,
                    rrf_score=(1 / (60 + sparse_ranks[item_uuid])
                               + 1 / (60 + dense_ranks[item_uuid])),
                    matched_tokens=tuple(sorted(query_tokens & self._tokens[item_uuid])),
                )
            )
        return candidates
