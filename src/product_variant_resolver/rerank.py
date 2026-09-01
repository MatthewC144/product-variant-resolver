from __future__ import annotations

from typing import Protocol

from .identity import normalize_text
from .retrieval import Candidate
from .schemas import ExtractedSignals


class PointwiseModel(Protocol):
    version: str

    def score(self, query: str, document: str) -> float: ...


class HeuristicPointwiseModel:
    """CPU/offline pointwise baseline. A pinned cross-encoder can implement the same protocol."""

    version = "heuristic-v1"

    def score(self, query: str, document: str) -> float:
        query_tokens = set(normalize_text(query).split())
        document_tokens = set(normalize_text(document).split())
        if not query_tokens:
            return 0.0
        intersection = len(query_tokens & document_tokens)
        return intersection / len(query_tokens | document_tokens)


class PointwiseReranker:
    def __init__(self, model: PointwiseModel) -> None:
        self.model = model

    def rerank(self, signals: ExtractedSignals, candidates: list[Candidate]) -> list[Candidate]:
        if len(candidates) > 25:
            raise ValueError("reranker candidate count exceeds 25")
        for candidate in candidates:
            lexical = self.model.score(signals.normalized_title, candidate.product.searchable_text)
            source_support = len(candidate.source_ranks) / 3.0
            match_bonus = 0.10 * len(candidate.matches)
            conflict_penalty = 0.12 * len(candidate.conflicts)
            candidate.reranker_score = lexical + 0.18 * source_support + match_bonus - conflict_penalty
        ordered = sorted(
            candidates,
            key=lambda item: (-(item.reranker_score or 0.0), -(item.rrf_score),
                              str(item.product.canonical_uuid)),
        )
        for rank, candidate in enumerate(ordered, start=1):
            candidate.reranker_rank = rank
        return ordered

