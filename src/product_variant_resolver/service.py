from __future__ import annotations

import logging
import time
import uuid

from .calibration import (
    CalibrationArtifact, DEFAULT_HEURISTIC_ARTIFACT, DEFAULT_RRF_ARTIFACT, LogisticCalibrator,
)
from .catalog import Catalog, load_catalog
from .config import Settings
from .human_knowledge import (
    HumanKnowledgeCandidate, HumanKnowledgeCatalog, HumanKnowledgeRetriever,
    load_human_knowledge_catalog,
)
from .observability import Tracer, get_tracer, observed_stage
from .policy import DecisionPolicy
from .rerank import HeuristicPointwiseModel, PointwiseReranker
from .retrieval import (
    Candidate, CandidateRetrievalService, DenseRetriever, HashingEmbedding, SparseRetriever,
    StructuredRetriever,
)
from .schemas import (
    CandidateDebug, DebugPayload, HumanKnowledgeCandidateDebug, ResolveRequest, ResolveResponse,
)
from .signals import extract_signals


class DependencyUnavailable(RuntimeError):
    pass


LOGGER = logging.getLogger("product_variant_resolver.resolver")


class ResolverService:
    def __init__(
        self,
        settings: Settings,
        catalog: Catalog,
        human_catalog: HumanKnowledgeCatalog,
        tracer: Tracer | None = None,
    ) -> None:
        self.settings = settings
        self.catalog = catalog
        self.color_vocabulary = {
            item.product.color for item in catalog.products if item.product.color
        }
        self.series_vocabulary = {
            item.product.series for item in catalog.products if item.product.series
        }
        if settings.dense_provider != "hashing-v1":
            raise DependencyUnavailable("external dense provider is configured but not loaded")
        if settings.reranker_enabled and settings.reranker_provider != "heuristic-v1":
            raise DependencyUnavailable("external reranker provider is configured but not loaded")
        embedding = HashingEmbedding(settings.dense_dimensions)
        self.human_catalog = human_catalog
        self.human_knowledge = HumanKnowledgeRetriever(human_catalog, embedding)
        structured = StructuredRetriever(catalog)
        self.retrieval = CandidateRetrievalService(
            [SparseRetriever(catalog), DenseRetriever(catalog, embedding), structured], structured,
        )
        self.reranker = PointwiseReranker(HeuristicPointwiseModel())
        artifact = (CalibrationArtifact.load(settings.calibration_artifact)
                    if settings.calibration_artifact else None)
        default_artifact = (DEFAULT_HEURISTIC_ARTIFACT
                            if settings.reranker_enabled else DEFAULT_RRF_ARTIFACT)
        self.calibrator = LogisticCalibrator(artifact or default_artifact)
        self.policy = (DecisionPolicy.load(settings.policy_artifact) if settings.policy_artifact
                       else DecisionPolicy(version=settings.policy_version))
        self.tracer = tracer or get_tracer(settings.tracing_enabled)

    @classmethod
    def from_settings(cls, settings: Settings) -> "ResolverService":
        if settings.backend != "offline":
            raise DependencyUnavailable("postgres backend requires migrated database adapters")
        return cls(
            settings,
            load_catalog(settings.catalog_path),
            load_human_knowledge_catalog(settings.human_catalog_path),
        )

    def resolve(self, request: ResolveRequest, *, request_id: str | None = None) -> ResolveResponse:
        started = time.perf_counter()
        timings: dict[str, float] = {}
        correlation_id = request_id or str(uuid.uuid4())

        with self.tracer.start_as_current_span("pvr.resolve") as span:
            span.set_attribute("pvr.request_id", correlation_id)
            span.set_attribute("pvr.title_length", len(request.title))
            span.set_attribute("pvr.debug", request.debug)
            try:
                with observed_stage(self.tracer, "signal_extraction", timings):
                    signals = extract_signals(
                        request.title, self.color_vocabulary, self.series_vocabulary,
                    )

                with observed_stage(self.tracer, "human_knowledge_retrieval", timings) as human_span:
                    human_candidates = self.human_knowledge.retrieve(
                        signals, self.settings.candidate_limit,
                    )
                    human_span.set_attribute("pvr.candidate_count", len(human_candidates))

                candidates, retrieval_timings = self.retrieval.retrieve_with_timings(
                    signals, self.settings.candidate_limit, self.tracer,
                )
                timings.update(retrieval_timings)

                with observed_stage(self.tracer, "rerank", timings) as rerank_span:
                    if self.settings.reranker_enabled:
                        candidates = self.reranker.rerank(signals, candidates)
                    rerank_span.set_attribute("pvr.enabled", self.settings.reranker_enabled)
                    rerank_span.set_attribute("pvr.candidate_count", len(candidates))

                with observed_stage(self.tracer, "calibration", timings) as calibration_span:
                    confidence = self.calibrator.probability(candidates)
                    status, reason = self.policy.decide(candidates, confidence)
                    calibration_span.set_attribute("pvr.status", status.value)
                timings["total"] = _elapsed(started)
                span.set_attribute("pvr.status", status.value)
                span.set_attribute("pvr.candidate_count", len(candidates))
                span.set_attribute("pvr.duration_ms", timings["total"])
            except Exception as error:
                span.set_attribute("pvr.error_type", type(error).__name__)
                span.record_exception(error)
                LOGGER.warning(
                    "resolution_failed request_id=%s title_length=%d error_type=%s",
                    correlation_id, len(request.title), type(error).__name__,
                )
                raise

        selected = candidates[0] if status.value == "matched" else None
        debug = None
        if request.debug:
            debug = DebugPayload(
                signals=signals,
                candidates=[_candidate_debug(item) for item in candidates[:request.debug_candidate_limit]],
                human_knowledge_candidates=[
                    _human_candidate_debug(item)
                    for item in human_candidates[:request.debug_candidate_limit]
                ],
                timings_ms=timings,
                catalog_version=self.catalog.version,
                human_catalog_version=self.human_catalog.version,
                model_versions={
                    "dense": "hashing-v1",
                    "reranker": (
                        self.reranker.model.version
                        if self.settings.reranker_enabled else "disabled"
                    ),
                    "reranker_ablation": self.reranker.model.version,
                    "calibrator": self.calibrator.artifact.artifact_version,
                    "human_knowledge": self.human_knowledge.version,
                },
            )
        response = ResolveResponse(
            status=status,
            canonical_uuid=selected.product.canonical_uuid if selected else None,
            canonical_id=selected.product.canonical_id if selected else None,
            confidence=confidence,
            reason=reason,
            product=selected.product.product if selected else None,
            policy_version=self.policy.version,
            debug=debug,
        )
        LOGGER.info(
            "resolution_completed request_id=%s status=%s title_length=%d "
            "candidate_count=%d human_candidate_count=%d total_ms=%.4f",
            correlation_id, status.value, len(request.title), len(candidates),
            len(human_candidates), timings["total"],
        )
        return response


def _elapsed(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 4)


def _candidate_debug(item: Candidate) -> CandidateDebug:
    return CandidateDebug(
        canonical_uuid=item.product.canonical_uuid,
        canonical_id=item.product.canonical_id,
        sparse_rank=item.source_ranks.get("sparse"), sparse_score=item.source_scores.get("sparse"),
        dense_rank=item.source_ranks.get("dense"), dense_score=item.source_scores.get("dense"),
        structured_rank=item.source_ranks.get("structured"),
        structured_score=item.source_scores.get("structured"),
        rrf_rank=item.rrf_rank, rrf_score=item.rrf_score,
        reranker_rank=item.reranker_rank, reranker_score=item.reranker_score,
        structured_matches=item.matches, structured_conflicts=item.conflicts,
    )


def _human_candidate_debug(item: HumanKnowledgeCandidate) -> HumanKnowledgeCandidateDebug:
    document = item.document
    return HumanKnowledgeCandidateDebug(
        casting_uuid=document.casting_uuid,
        casting_id=document.casting_id,
        provisional_variant_uuid=document.provisional_variant_uuid,
        provisional_variant_id=document.provisional_variant_id,
        identity_status=document.identity_status,
        brand=document.brand,
        casting=document.casting,
        series_label=document.series_label,
        variant_label=document.variant_label,
        human_label_names=list(document.human_label_names[:3]),
        example_initial_names=list(document.initial_names[:3]),
        source_case_ids=list(document.source_case_ids[:5]),
        sparse_rank=item.sparse_rank,
        sparse_score=item.sparse_score,
        dense_rank=item.dense_rank,
        dense_score=item.dense_score,
        rrf_rank=item.rrf_rank,
        rrf_score=item.rrf_score,
        matched_tokens=list(item.matched_tokens),
    )
