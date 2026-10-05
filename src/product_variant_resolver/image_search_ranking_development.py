"""Development-only ranking comparison for the image-search release benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from .config import Settings
from .evaluation import percentile, safe_divide
from .human_knowledge import load_human_knowledge_catalog
from .identity import normalize_text
from .image_search_evaluation import (
    AUTHORITY_NOTE,
    DATASET,
    SOURCE,
    SOURCE_COUNT,
    bind_dataset_to_source,
    build_evaluation_catalog,
    load_frozen_split,
    load_image_search_dataset,
    load_source_records,
)
from .neural_reranker_comparison import LocalListwiseScorer, freeze_candidate
from .neural_reranking import (
    LocalPointwiseScorer,
    candidate_feature_vector,
    load_pointwise_model_config,
    rank_scores,
    render_candidate_text,
    validate_local_pointwise_model,
)
from .service import ResolverService
from .signals import extract_signals

ARMS = ("rrf", "release_heuristic", "neural_pointwise", "neural_listwise")
POINTWISE_CONFIG = Path("config/neural-reranker-comparison-v1.json")
POINTWISE_MODEL = Path("model-cache/neural-reranker-comparison-v1/pointwise")
LISTWISE_MANIFEST = Path(
    "data/evaluation/neural-reranker-comparison-v1/models/listwise-manifest.json"
)
LISTWISE_MODEL = Path(
    "data/evaluation/neural-reranker-comparison-v1/models/listwise-model.safetensors"
)


class PointwiseScorer(Protocol):
    version: str

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[float, ...]: ...


class ListwiseScorer(Protocol):
    version: str

    def score_set(self, features: Sequence[Sequence[float]]) -> tuple[float, ...]: ...


@dataclass(frozen=True, slots=True)
class RankingOutcome:
    casting_top1_correct: bool
    exact_release_rank: int | None
    latency_ms: float


@dataclass(frozen=True, slots=True)
class ArmMetrics:
    sample_count: int
    casting_top1_correct: int
    exact_release_top1_correct: int
    exact_release_retrieved_at_10: int
    exact_release_retrieved_at_25: int
    reciprocal_rank_sum_at_10: float
    casting_top1_accuracy: float
    exact_release_top1_accuracy: float
    exact_release_recall_at_10: float
    exact_release_recall_at_25: float
    exact_release_mrr_at_10: float
    rerank_p50_latency_ms: float
    rerank_p95_latency_ms: float


@dataclass(frozen=True, slots=True)
class DevelopmentComparisonReport:
    schema_version: str
    dataset_version: str
    split: str
    split_version: str
    split_assignment_sha256: str
    sample_count: int
    candidate_corpus_count: int
    candidate_limit: int
    arms: dict[str, ArmMetrics]
    winner_by_exact_top1: str
    metadata: dict[str, Any]


def summarize_outcomes(outcomes: Sequence[RankingOutcome]) -> ArmMetrics:
    count = len(outcomes)
    casting_top1 = sum(outcome.casting_top1_correct for outcome in outcomes)
    exact_top1 = sum(outcome.exact_release_rank == 1 for outcome in outcomes)
    recall10 = sum(
        outcome.exact_release_rank is not None and outcome.exact_release_rank <= 10
        for outcome in outcomes
    )
    recall25 = sum(
        outcome.exact_release_rank is not None and outcome.exact_release_rank <= 25
        for outcome in outcomes
    )
    reciprocal_sum = sum(
        1.0 / outcome.exact_release_rank
        for outcome in outcomes
        if outcome.exact_release_rank is not None and outcome.exact_release_rank <= 10
    )
    latencies = [outcome.latency_ms for outcome in outcomes]
    return ArmMetrics(
        sample_count=count,
        casting_top1_correct=casting_top1,
        exact_release_top1_correct=exact_top1,
        exact_release_retrieved_at_10=recall10,
        exact_release_retrieved_at_25=recall25,
        reciprocal_rank_sum_at_10=reciprocal_sum,
        casting_top1_accuracy=safe_divide(casting_top1, count),
        exact_release_top1_accuracy=safe_divide(exact_top1, count),
        exact_release_recall_at_10=safe_divide(recall10, count),
        exact_release_recall_at_25=safe_divide(recall25, count),
        exact_release_mrr_at_10=safe_divide(reciprocal_sum, count),
        rerank_p50_latency_ms=statistics.median(latencies) if latencies else 0.0,
        rerank_p95_latency_ms=percentile(latencies, 0.95),
    )


def _rank(identity: UUID, ranked_ids: Sequence[UUID]) -> int | None:
    return next(
        (index for index, value in enumerate(ranked_ids, start=1) if value == identity), None
    )


def _outcome(
    target: UUID,
    expected_casting: str,
    ranked_ids: Sequence[UUID],
    *,
    catalog_by_uuid: dict[UUID, Any],
    latency_ms: float,
) -> RankingOutcome:
    top1_casting = catalog_by_uuid[ranked_ids[0]].product.casting if ranked_ids else ""
    return RankingOutcome(
        casting_top1_correct=(normalize_text(top1_casting) == normalize_text(expected_casting)),
        exact_release_rank=_rank(target, ranked_ids),
        latency_ms=latency_ms,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_neural_scorers(root: Path) -> tuple[PointwiseScorer, ListwiseScorer]:
    config_path = root / POINTWISE_CONFIG
    model_path = root / POINTWISE_MODEL
    config = load_pointwise_model_config(config_path)
    validate_local_pointwise_model(config, model_path)
    pointwise = LocalPointwiseScorer.load(config, model_path)
    listwise = LocalListwiseScorer.load(
        root / LISTWISE_MANIFEST,
        root / LISTWISE_MODEL,
    )
    return pointwise, listwise


def compare_development_rankers(
    settings: Settings,
    *,
    root: Path,
    dataset_path: Path = DATASET,
    source_path: Path = SOURCE,
    source_expected_count: int = SOURCE_COUNT,
    pointwise: PointwiseScorer | None = None,
    listwise: ListwiseScorer | None = None,
) -> DevelopmentComparisonReport:
    dataset = load_image_search_dataset(dataset_path)
    frozen_split = load_frozen_split(dataset, dataset_path)
    development_ids = set(frozen_split.development_case_ids)
    cases = [case for case in dataset.records if case.id in development_ids]
    records = load_source_records(source_path, expected_count=source_expected_count)
    bindings = bind_dataset_to_source(dataset, records)
    target_by_case = {binding.case_id: binding.evaluation_uuid for binding in bindings}
    catalog = build_evaluation_catalog(records)
    human_catalog = load_human_knowledge_catalog(
        settings.human_catalog_path,
        settings.review_family_knowledge_path,
        settings.review_family_knowledge_manifest_path,
    )
    service = ResolverService(settings, catalog, human_catalog)
    active_pointwise, active_listwise = (
        (pointwise, listwise)
        if pointwise is not None and listwise is not None
        else load_neural_scorers(root)
    )
    if active_pointwise is None or active_listwise is None:
        raise ValueError("pointwise and listwise scorers must be supplied together")

    outcomes: dict[str, list[RankingOutcome]] = {arm: [] for arm in ARMS}
    for case in cases:
        signals = extract_signals(case.query, service.color_vocabulary, service.series_vocabulary)
        candidates = service.retrieval.retrieve(signals, settings.candidate_limit)
        target = target_by_case[case.id]
        rrf_ids = [candidate.product.canonical_uuid for candidate in candidates]
        outcomes["rrf"].append(
            _outcome(
                target,
                case.expected_casting,
                rrf_ids,
                catalog_by_uuid=catalog.by_uuid,
                latency_ms=0.0,
            )
        )
        frozen_candidates = tuple(freeze_candidate(candidate) for candidate in candidates)

        started = time.perf_counter()
        heuristic_candidates = service.reranker.rerank(signals, list(candidates))
        heuristic_ms = (time.perf_counter() - started) * 1000
        heuristic_ids = [candidate.product.canonical_uuid for candidate in heuristic_candidates]
        outcomes["release_heuristic"].append(
            _outcome(
                target,
                case.expected_casting,
                heuristic_ids,
                catalog_by_uuid=catalog.by_uuid,
                latency_ms=heuristic_ms,
            )
        )

        pairs = tuple(
            (case.query, render_candidate_text(candidate.text)) for candidate in frozen_candidates
        )
        started = time.perf_counter()
        pointwise_scores = active_pointwise.score_pairs(pairs)
        pointwise_ranked = rank_scores(frozen_candidates, pointwise_scores)
        pointwise_ms = (time.perf_counter() - started) * 1000
        pointwise_ids = [UUID(item.canonical_uuid) for item in pointwise_ranked]
        outcomes["neural_pointwise"].append(
            _outcome(
                target,
                case.expected_casting,
                pointwise_ids,
                catalog_by_uuid=catalog.by_uuid,
                latency_ms=pointwise_ms,
            )
        )

        features = tuple(
            candidate_feature_vector(candidate, score)
            for candidate, score in zip(frozen_candidates, pointwise_scores, strict=True)
        )
        started = time.perf_counter()
        listwise_scores = active_listwise.score_set(features)
        listwise_ranked = rank_scores(frozen_candidates, listwise_scores)
        listwise_ms = pointwise_ms + (time.perf_counter() - started) * 1000
        listwise_ids = [UUID(item.canonical_uuid) for item in listwise_ranked]
        outcomes["neural_listwise"].append(
            _outcome(
                target,
                case.expected_casting,
                listwise_ids,
                catalog_by_uuid=catalog.by_uuid,
                latency_ms=listwise_ms,
            )
        )

    arm_metrics = {arm: summarize_outcomes(outcomes[arm]) for arm in ARMS}
    winner = max(
        ARMS,
        key=lambda arm: (
            arm_metrics[arm].exact_release_top1_accuracy,
            arm_metrics[arm].exact_release_mrr_at_10,
            -arm_metrics[arm].rerank_p95_latency_ms,
        ),
    )
    return DevelopmentComparisonReport(
        schema_version="pvr-image-search-ranking-development-v1",
        dataset_version=dataset.dataset_version,
        split="development",
        split_version=frozen_split.version,
        split_assignment_sha256=frozen_split.assignment_sha256,
        sample_count=len(cases),
        candidate_corpus_count=len(catalog.products),
        candidate_limit=settings.candidate_limit,
        arms=arm_metrics,
        winner_by_exact_top1=winner,
        metadata={
            "test_cases_scored": 0,
            "row_level_output_persisted": False,
            "canonical_catalog_modified": False,
            "pointwise_model_version": active_pointwise.version,
            "listwise_model_version": active_listwise.version,
            "pointwise_model_manifest_sha256": _sha256(root / POINTWISE_MODEL / "manifest.json"),
            "listwise_model_sha256": _sha256(root / LISTWISE_MODEL),
            "model_reuse_note": (
                "Frozen models trained on the earlier fixture benchmark are evaluated zero-shot; "
                "the 100 image-search development labels were not used to fit either model."
            ),
            "score_semantics": "Ranking scores only; no neural score is a match probability.",
            "authority_note": AUTHORITY_NOTE,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare rankers on image-search development only")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--acknowledge-development-only", action="store_true")
    arguments = parser.parse_args()
    if not arguments.acknowledge_development_only:
        parser.error("--acknowledge-development-only is required")
    root = arguments.root.resolve()
    report = compare_development_rankers(Settings.from_env(), root=root)
    print(json.dumps(asdict(report), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
