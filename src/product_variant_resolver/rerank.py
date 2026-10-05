from __future__ import annotations

import math
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from .identity import normalize_text
from .neural_reranking import (
    CandidateTextFields,
    LocalPointwiseScorer,
    load_pointwise_model_config,
    render_candidate_text,
)
from .retrieval import Candidate
from .schemas import ExtractedSignals


class PointwiseModel(Protocol):
    version: str

    def score(self, query: str, document: str) -> float: ...


class PairScorer(Protocol):
    version: str

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[float, ...]: ...


class CandidateReranker(Protocol):
    @property
    def version(self) -> str: ...

    def rerank(
        self, signals: ExtractedSignals, candidates: list[Candidate], *, query: str | None = None,
    ) -> list[Candidate]: ...


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

    @property
    def version(self) -> str:
        return self.model.version

    def rerank(
        self, signals: ExtractedSignals, candidates: list[Candidate], *, query: str | None = None,
    ) -> list[Candidate]:
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


def _render_candidate(candidate: Candidate) -> str:
    product = candidate.product
    view = product.product
    return render_candidate_text(CandidateTextFields(
        brand=view.brand, casting=view.casting, release_year=view.release_year,
        series=view.series, color=view.color, collector_number=view.collector_number,
        series_position=view.series_position, edition=view.edition,
        aliases=product.aliases, identifiers=product.identifiers,
    ))


class NeuralPointwiseReranker:
    """Batch local CrossEncoder adapter with frozen comparison ordering semantics."""

    def __init__(self, scorer: PairScorer) -> None:
        self.scorer = scorer

    @property
    def version(self) -> str:
        return self.scorer.version

    def rerank(
        self, signals: ExtractedSignals, candidates: list[Candidate], *, query: str | None = None,
    ) -> list[Candidate]:
        if len(candidates) > 25:
            raise ValueError("reranker candidate count exceeds 25")
        if not candidates:
            return []
        if any(candidate.rrf_rank is None for candidate in candidates):
            raise ValueError("neural reranker requires every candidate to have an RRF rank")
        query_text = query.strip() if query and query.strip() else signals.normalized_title
        pairs = tuple((query_text, _render_candidate(candidate)) for candidate in candidates)
        scores = self.scorer.score_pairs(pairs)
        if len(scores) != len(candidates):
            raise ValueError("neural reranker returned the wrong score count")
        if any(not math.isfinite(float(score)) for score in scores):
            raise ValueError("neural reranker returned a non-finite score")
        scored = list(zip(candidates, scores, strict=True))
        scored.sort(key=lambda item: (
            -float(item[1]), item[0].rrf_rank if item[0].rrf_rank is not None else 26,
            str(item[0].product.canonical_uuid),
        ))
        ordered = []
        for rank, (candidate, score) in enumerate(scored, start=1):
            candidate.reranker_score = float(score)
            candidate.reranker_rank = rank
            ordered.append(candidate)
        return ordered


def load_neural_pointwise_reranker(
    config_path: Path, model_path: Path,
) -> NeuralPointwiseReranker:
    config = load_pointwise_model_config(config_path)
    return NeuralPointwiseReranker(LocalPointwiseScorer.load(config, model_path))
