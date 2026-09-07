from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from .catalog import Catalog, CatalogProduct, catalog_tokens
from .identity import normalize_text
from .observability import NOOP_TRACER, Tracer, observed_stage
from .schemas import ExtractedSignals


@dataclass(slots=True)
class Candidate:
    product: CatalogProduct
    source_ranks: dict[str, int] = field(default_factory=dict)
    source_scores: dict[str, float] = field(default_factory=dict)
    matches: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    rrf_score: float = 0.0
    rrf_rank: int | None = None
    reranker_score: float | None = None
    reranker_rank: int | None = None


class Retriever(Protocol):
    name: str
    version: str

    def retrieve(self, signals: ExtractedSignals, limit: int) -> list[tuple[CatalogProduct, float]]: ...


class EmbeddingModel(Protocol):
    version: str

    def encode(self, text: str) -> tuple[float, ...]: ...


def _rank(items: list[tuple[CatalogProduct, float]], limit: int) -> list[tuple[CatalogProduct, float]]:
    items.sort(key=lambda item: (-item[1], str(item[0].canonical_uuid)))
    return items[:limit]


class SparseRetriever:
    """Deterministic token baseline; PostgresSparseRetriever is the production adapter boundary."""

    name = "sparse"
    version = "token-index-v1"

    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog
        self._documents = {item.canonical_uuid: catalog_tokens(item) for item in catalog.products}

    def retrieve(self, signals: ExtractedSignals, limit: int) -> list[tuple[CatalogProduct, float]]:
        query = set(signals.tokens)
        if not query:
            return []
        frequencies = {
            token: sum(token in document for document in self._documents.values()) for token in query
        }
        results = []
        total = len(self._documents)
        for product in self.catalog.products:
            document = self._documents[product.canonical_uuid]
            score = sum(math.log((total + 1) / (frequencies[token] + 1)) + 1
                        for token in query & document)
            if score > 0:
                results.append((product, score))
        return _rank(results, limit)


class HashingEmbedding:
    """Dependency-free offline embedding, versioned and deterministic; not a neural model."""

    version = "hashing-v1"

    def __init__(self, dimensions: int = 192) -> None:
        self.dimensions = dimensions

    def encode(self, text: str) -> tuple[float, ...]:
        vector = [0.0] * self.dimensions
        normalized = normalize_text(text)
        tokens = normalized.split()
        features = tokens + [normalized[index:index + 3] for index in range(max(0, len(normalized) - 2))]
        for feature in features:
            digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] & 1 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return tuple(value / norm for value in vector)


class DenseRetriever:
    name = "dense"

    def __init__(self, catalog: Catalog, embedding: EmbeddingModel) -> None:
        self.catalog = catalog
        self.embedding = embedding
        self._vectors = {item.canonical_uuid: embedding.encode(item.searchable_text)
                         for item in catalog.products}

    def retrieve(self, signals: ExtractedSignals, limit: int) -> list[tuple[CatalogProduct, float]]:
        query = self.embedding.encode(signals.normalized_title)
        results = []
        for product in self.catalog.products:
            score = sum(a * b for a, b in zip(query, self._vectors[product.canonical_uuid], strict=True))
            if score > 0:
                results.append((product, score))
        return _rank(results, limit)


class StructuredRetriever:
    name = "structured"

    def __init__(self, catalog: Catalog) -> None:
        self.catalog = catalog

    @staticmethod
    def features(product: CatalogProduct, signals: ExtractedSignals) -> tuple[list[str], list[str], float]:
        value = product.product
        matches: list[str] = []
        conflicts: list[str] = []
        score = 0.0
        checks = [
            ("year", str(signals.year) if signals.year else None,
             str(value.release_year) if value.release_year else None, 2.0),
            ("collector_number", signals.collector_number, value.collector_number, 5.0),
            ("series_position", signals.series_position, value.series_position, 3.0),
        ]
        for name, query, candidate, weight in checks:
            if query and candidate:
                if normalize_text(query) == normalize_text(candidate):
                    matches.append(name)
                    score += weight
                else:
                    conflicts.append(name)
                    score -= weight * 0.35
        if signals.color_hints and value.color:
            if normalize_text(value.color) in signals.color_hints:
                matches.append("color")
                score += 2.0
            else:
                conflicts.append("color")
                score -= 0.7
        if signals.series_hints and value.series:
            if normalize_text(value.series) in signals.series_hints:
                matches.append("series")
                score += 2.0
            else:
                conflicts.append("series")
                score -= 0.7
        return matches, conflicts, score

    def retrieve(self, signals: ExtractedSignals, limit: int) -> list[tuple[CatalogProduct, float]]:
        results = []
        for product in self.catalog.products:
            _, _, score = self.features(product, signals)
            if score > 0:
                results.append((product, score))
        return _rank(results, limit)


def reciprocal_rank_fusion(
    results: dict[str, list[tuple[CatalogProduct, float]]], limit: int, k: int = 60,
    structured: StructuredRetriever | None = None, signals: ExtractedSignals | None = None,
) -> list[Candidate]:
    if limit < 1 or limit > 25:
        raise ValueError("fusion limit must be between 1 and 25")
    merged: dict[UUID, Candidate] = {}
    for source, source_results in sorted(results.items()):
        for rank, (product, score) in enumerate(source_results, start=1):
            candidate = merged.setdefault(product.canonical_uuid, Candidate(product=product))
            candidate.source_ranks[source] = rank
            candidate.source_scores[source] = score
            candidate.rrf_score += 1.0 / (k + rank)
    if structured and signals:
        for candidate in merged.values():
            candidate.matches, candidate.conflicts, _ = structured.features(candidate.product, signals)
    ordered = sorted(merged.values(), key=lambda c: (-c.rrf_score, str(c.product.canonical_uuid)))[:limit]
    for rank, candidate in enumerate(ordered, start=1):
        candidate.rrf_rank = rank
    return ordered


class CandidateRetrievalService:
    def __init__(self, retrievers: list[Retriever], structured: StructuredRetriever) -> None:
        self.retrievers = retrievers
        self.structured = structured

    def retrieve(self, signals: ExtractedSignals, limit: int) -> list[Candidate]:
        candidates, _timings = self.retrieve_with_timings(signals, limit)
        return candidates

    def retrieve_with_timings(
        self, signals: ExtractedSignals, limit: int, tracer: Tracer = NOOP_TRACER,
    ) -> tuple[list[Candidate], dict[str, float]]:
        source_results: dict[str, list[tuple[CatalogProduct, float]]] = {}
        timings: dict[str, float] = {}
        for retriever in self.retrievers:
            with observed_stage(tracer, retriever.name, timings) as span:
                try:
                    results = retriever.retrieve(signals, limit)
                except Exception as error:
                    raise RetrievalUnavailable(f"retriever {retriever.name} failed") from error
                source_results[retriever.name] = results
                span.set_attribute("pvr.candidate_count", len(results))
        with observed_stage(tracer, "fusion", timings) as span:
            candidates = reciprocal_rank_fusion(
                source_results, limit, structured=self.structured, signals=signals,
            )
            span.set_attribute("pvr.candidate_count", len(candidates))
        return candidates, timings


class RetrievalUnavailable(RuntimeError):
    pass


POSTGRES_FTS_SQL = """
SELECT canonical_uuid,
       ts_rank_cd(search_document, websearch_to_tsquery('simple', :query)) AS score
FROM product_search
WHERE search_document @@ websearch_to_tsquery('simple', :query)
ORDER BY score DESC, canonical_uuid ASC
LIMIT :limit
""".strip()

PGVECTOR_EXACT_SQL = """
SELECT canonical_uuid, 1 - (embedding <=> CAST(:embedding AS vector)) AS score
FROM product_embedding
WHERE embedding_version = :embedding_version
ORDER BY embedding <=> CAST(:embedding AS vector), canonical_uuid ASC
LIMIT :limit
""".strip()


class PostgresRetrieverAdapter(Protocol):
    def execute_ranked(self, statement: str, parameters: dict[str, object]) -> list[tuple[UUID, float]]:
        ...


class PostgresSparseRetriever:
    """Canonical sparse candidates from PostgreSQL full-text search."""

    name = "sparse"
    version = "postgres-fts-simple-v1"

    def __init__(self, catalog: Catalog, adapter: PostgresRetrieverAdapter) -> None:
        self.catalog = catalog
        self.adapter = adapter

    def retrieve(
        self, signals: ExtractedSignals, limit: int
    ) -> list[tuple[CatalogProduct, float]]:
        if not 1 <= limit <= 25:
            raise ValueError("PostgreSQL sparse limit must be between 1 and 25")
        if not signals.tokens:
            return []
        # websearch_to_tsquery understands OR, while the value remains a bound SQL
        # parameter. Quoting each normalized token keeps punctuation out of tsquery syntax.
        query = " OR ".join(f'"{token}"' for token in dict.fromkeys(signals.tokens))
        rows = self.adapter.execute_ranked(
            POSTGRES_FTS_SQL,
            {"query": query, "limit": limit},
        )
        results: list[tuple[CatalogProduct, float]] = []
        for canonical_uuid, score in rows:
            product = self.catalog.by_uuid.get(canonical_uuid)
            if product is None:
                raise RuntimeError(
                    "PostgreSQL returned an identity absent from the loaded catalog"
                )
            results.append((product, score))
        return results
