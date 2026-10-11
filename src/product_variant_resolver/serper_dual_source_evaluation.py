"""Frozen grouped split contract for the Serper dual-source benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import time
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator, model_validator

from .config import Settings
from .evaluation import percentile, safe_divide
from .human_knowledge import load_human_knowledge_catalog
from .identity import normalize_text
from .image_search_evaluation import (
    SOURCE,
    SOURCE_COUNT,
    ExpectedFullIdentity,
    ImageSearchCase,
    ImageSearchDataset,
    bind_dataset_to_source,
    build_evaluation_catalog,
    load_source_records,
)
from .image_search_ranking_development import (
    POINTWISE_CONFIG,
    POINTWISE_MODEL,
    SELECTION,
    check_development_selection,
)
from .neural_reranking import (
    LocalPointwiseScorer,
    load_pointwise_model_config,
    validate_local_pointwise_model,
)
from .rerank import NeuralPointwiseReranker
from .retrieval import Candidate
from .schemas import ResolutionStatus, ResolveRequest, StrictModel
from .service import ResolverService
from .signals import extract_signals

DATASET = Path("data/evaluation/serper-dual-source-query-v1/dataset.json")
DEVELOPMENT_BASELINE = Path(
    "data/evaluation/serper-dual-source-evaluation-v1/development-baseline.json"
)
RAW_POINTWISE_DEVELOPMENT = Path(
    "data/evaluation/serper-dual-source-evaluation-v1/raw-pointwise-development.json"
)
SDSE_T4_OWNER_AUTHORIZATION = Path(
    "data/evaluation/serper-dual-source-evaluation-v1/sdse-t4-owner-authorization.json"
)
RAW_POINTWISE_FINAL_TEST = Path(
    "data/evaluation/serper-dual-source-evaluation-v1/raw-pointwise-final-test.json"
)
FROZEN_DATASET_SHA256 = "05213c4c8d101d844b179359aef63264b8579c2f728b14f5adbe7a3a75a56034"
FROZEN_DEVELOPMENT_BASELINE_SHA256 = (
    "8ffb7758fd344bc632747432be1232efed49cbf8155721867bb747086481932c"
)
FROZEN_RAW_POINTWISE_DEVELOPMENT_SHA256 = (
    "f760d733ecc6cbee2124d42ad539d81b2f810bff2842ee26b2a2e6b2946df362"
)
FROZEN_SDSE_T4_OWNER_AUTHORIZATION_SHA256 = (
    "b22e32384961d0f5be469baa641bbdab7be6393dbbf74484a48cfce097fcfc14"
)
FROZEN_RAW_POINTWISE_FINAL_TEST_SHA256 = (
    "ba06ef6db36e86d436205af82b7d96f2af902c4f082194acfe006af470ba37e2"
)
FROZEN_CATALOG_SHA256 = "b4e0747450a5447c2bf66b0838c91f3f723a19ac97c90c7ac3636cf3a9a709d4"
FROZEN_TARGET_COUNT = 150
FROZEN_RECORD_COUNT = 300
FROZEN_DEVELOPMENT_TARGET_COUNT = 100
FROZEN_TEST_TARGET_COUNT = 50
FROZEN_SPLIT_VERSION = "serper-dual-source-year-stratified-grouped-split-v1"
FROZEN_SPLIT_SALT = (
    "pvr:serper-dual-source-query:year-stratified-grouped-development-test:v1"
)
FROZEN_SPLIT_SHA256 = "4831d72b8b5ced2550e1dc1c35498781279d6e1ea866c4b3669638035b73ef13"
AUTHORITY_SCOPE = "frozen-community-catalog-relative-not-manufacturer-truth"

SourceType = Literal["image_search", "shopping"]
QueryVariant = Literal["raw", "cleaned"]

ARM_DEFINITIONS: tuple[tuple[str, SourceType, QueryVariant], ...] = (
    ("image_search_raw", "image_search", "raw"),
    ("image_search_cleaned", "image_search", "cleaned"),
    ("shopping_raw", "shopping", "raw"),
    ("shopping_cleaned", "shopping", "cleaned"),
)


class SerperDualSourceCase(StrictModel):
    id: str = Field(pattern=r"^sds-[0-9]{4}$")
    target_id: str = Field(pattern=r"^sds-target-[0-9]{4}$")
    source_type: SourceType
    query_raw: str = Field(min_length=1, max_length=512)
    query_cleaned: str = Field(min_length=1, max_length=512)
    expected_casting: str = Field(min_length=1)
    expected_full_identity: ExpectedFullIdentity

    @field_validator("query_raw", "query_cleaned", "expected_casting")
    @classmethod
    def strip_text_and_reject_urls(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("query and casting text must not be blank")
        if "http://" in stripped.casefold() or "https://" in stripped.casefold():
            raise ValueError("tracked benchmark text must not contain URLs")
        return stripped

    @model_validator(mode="after")
    def casting_agrees(self) -> SerperDualSourceCase:
        if normalize_text(self.expected_casting) != normalize_text(
            self.expected_full_identity.casting
        ):
            raise ValueError("expected_casting differs from expected_full_identity.casting")
        return self


class SerperDualSourceDataset(StrictModel):
    model_config = ConfigDict(extra="forbid")

    dataset_version: Literal["serper-dual-source-query-v1"]
    catalog_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authority_scope: Literal[
        "frozen-community-catalog-relative-not-manufacturer-truth"
    ]
    target_count: int = Field(gt=0)
    record_count: int = Field(gt=0)
    records: list[SerperDualSourceCase] = Field(min_length=2)

    @model_validator(mode="after")
    def validate_paired_contract(self) -> SerperDualSourceDataset:
        if self.record_count != len(self.records):
            raise ValueError("record_count differs from records length")
        expected_ids = [f"sds-{index:04d}" for index in range(1, len(self.records) + 1)]
        if [case.id for case in self.records] != expected_ids:
            raise ValueError("record IDs must be contiguous and ordered")

        grouped: dict[str, list[SerperDualSourceCase]] = defaultdict(list)
        for case in self.records:
            grouped[case.target_id].append(case)
        if self.target_count != len(grouped):
            raise ValueError("target_count differs from unique target IDs")

        expected_target_ids = [
            f"sds-target-{index:04d}" for index in range(1, len(grouped) + 1)
        ]
        if list(grouped) != expected_target_ids:
            raise ValueError("target IDs must be contiguous and ordered")

        castings: list[str] = []
        for target_id, pair in grouped.items():
            if len(pair) != 2 or [case.source_type for case in pair] != [
                "image_search",
                "shopping",
            ]:
                raise ValueError(f"{target_id} must contain one ordered record per source")
            if pair[0].expected_full_identity != pair[1].expected_full_identity:
                raise ValueError(f"{target_id} source records disagree on expected identity")
            if normalize_text(pair[0].expected_casting) != normalize_text(
                pair[1].expected_casting
            ):
                raise ValueError(f"{target_id} source records disagree on expected casting")
            castings.append(normalize_text(pair[0].expected_casting))

        if len(castings) != len(set(castings)):
            raise ValueError("normalized target castings must be unique")
        for source_type in ("image_search", "shopping"):
            source_records = [case for case in self.records if case.source_type == source_type]
            for field_name in ("query_raw", "query_cleaned"):
                values = [
                    normalize_text(getattr(case, field_name)) for case in source_records
                ]
                if len(values) != len(set(values)):
                    raise ValueError(f"{source_type} {field_name} values must be unique")
        return self

    def target_pairs(self) -> tuple[tuple[SerperDualSourceCase, SerperDualSourceCase], ...]:
        return tuple(
            (self.records[index], self.records[index + 1])
            for index in range(0, len(self.records), 2)
        )


@dataclass(frozen=True, slots=True)
class FrozenGroupedSplit:
    version: str
    development_target_ids: tuple[str, ...]
    test_target_ids: tuple[str, ...]
    assignment_sha256: str


@dataclass(frozen=True, slots=True)
class FourArmMetrics:
    source_type: SourceType
    query_variant: QueryVariant
    sample_count: int
    casting_top1_accuracy: float
    exact_release_top1_accuracy: float
    exact_release_recall_at_10: float
    exact_release_recall_at_25: float
    exact_release_mrr_at_10: float
    policy_exact_accuracy: float
    policy_precision: float
    policy_coverage: float
    policy_abstention_rate: float
    policy_status_counts: dict[str, int]
    pipeline_p50_latency_ms: float
    pipeline_p95_latency_ms: float
    raw_counts: dict[str, int | float]


@dataclass(frozen=True, slots=True)
class FourArmDevelopmentReport:
    schema_version: str
    status: str
    dataset_version: str
    dataset_sha256: str
    catalog_sha256: str
    split_version: str
    split_assignment_sha256: str
    full_target_count: int
    full_record_count: int
    development_target_count: int
    development_record_count: int
    test_target_count: int
    test_record_count: int
    candidate_count: int
    source_binding_count_per_arm: int
    arms: dict[str, FourArmMetrics]
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RawRankingMetrics:
    source_type: SourceType
    ranker: Literal["rrf", "neural_pointwise"]
    sample_count: int
    casting_top1_accuracy: float
    exact_release_top1_accuracy: float
    exact_release_recall_at_10: float
    exact_release_recall_at_25: float
    exact_release_mrr_at_10: float
    rerank_p50_latency_ms: float
    rerank_p95_latency_ms: float
    raw_counts: dict[str, int | float]


@dataclass(frozen=True, slots=True)
class RawPointwiseDevelopmentReport:
    schema_version: str
    status: str
    dataset_sha256: str
    catalog_sha256: str
    split_version: str
    split_assignment_sha256: str
    development_target_count: int
    test_target_count: int
    candidate_count: int
    candidate_limit: int
    arms: dict[str, RawRankingMetrics]
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RawPointwiseFinalTestReport:
    schema_version: str
    status: str
    dataset_sha256: str
    catalog_sha256: str
    split_version: str
    split_assignment_sha256: str
    test_target_count: int
    candidate_count: int
    candidate_limit: int
    arms: dict[str, RawRankingMetrics]
    metadata: dict[str, Any]


@dataclass(slots=True)
class _RankingAccumulator:
    casting_top1_correct: int = 0
    exact_release_top1_correct: int = 0
    exact_release_retrieved_at_10: int = 0
    exact_release_retrieved_at_25: int = 0
    exact_release_reciprocal_rank_sum_at_10: float = 0.0
    sample_count: int = 0
    latencies_ms: list[float] | None = None

    def __post_init__(self) -> None:
        if self.latencies_ms is None:
            self.latencies_ms = []

    def add(
        self,
        candidates: Sequence[Candidate],
        *,
        target: UUID,
        expected_casting: str,
        latency_ms: float,
    ) -> None:
        self.sample_count += 1
        assert self.latencies_ms is not None
        self.latencies_ms.append(latency_ms)
        rank = next(
            (
                index
                for index, candidate in enumerate(candidates, start=1)
                if candidate.product.canonical_uuid == target
            ),
            None,
        )
        if candidates:
            self.casting_top1_correct += normalize_text(
                candidates[0].product.product.casting
            ) == normalize_text(expected_casting)
            self.exact_release_top1_correct += (
                candidates[0].product.canonical_uuid == target
            )
        self.exact_release_retrieved_at_10 += rank is not None and rank <= 10
        self.exact_release_retrieved_at_25 += rank is not None and rank <= 25
        if rank is not None and rank <= 10:
            self.exact_release_reciprocal_rank_sum_at_10 += 1.0 / rank

    def summarize(
        self,
        *,
        source_type: SourceType,
        ranker: Literal["rrf", "neural_pointwise"],
    ) -> RawRankingMetrics:
        if self.sample_count < 1 or self.latencies_ms is None:
            raise ValueError("ranking metrics require at least one sample")
        return RawRankingMetrics(
            source_type=source_type,
            ranker=ranker,
            sample_count=self.sample_count,
            casting_top1_accuracy=safe_divide(
                self.casting_top1_correct, self.sample_count
            ),
            exact_release_top1_accuracy=safe_divide(
                self.exact_release_top1_correct, self.sample_count
            ),
            exact_release_recall_at_10=safe_divide(
                self.exact_release_retrieved_at_10, self.sample_count
            ),
            exact_release_recall_at_25=safe_divide(
                self.exact_release_retrieved_at_25, self.sample_count
            ),
            exact_release_mrr_at_10=safe_divide(
                self.exact_release_reciprocal_rank_sum_at_10, self.sample_count
            ),
            rerank_p50_latency_ms=statistics.median(self.latencies_ms),
            rerank_p95_latency_ms=percentile(self.latencies_ms, 0.95),
            raw_counts={
                "casting_top1_correct": self.casting_top1_correct,
                "exact_release_top1_correct": self.exact_release_top1_correct,
                "exact_release_retrieved_at_10": self.exact_release_retrieved_at_10,
                "exact_release_retrieved_at_25": self.exact_release_retrieved_at_25,
                "exact_release_reciprocal_rank_sum_at_10": round(
                    self.exact_release_reciprocal_rank_sum_at_10, 12
                ),
            },
        )


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return payload


def load_serper_dual_source_dataset(
    path: Path = DATASET,
) -> SerperDualSourceDataset:
    return SerperDualSourceDataset.model_validate(_read_object(path))


def _target_rows(
    dataset: SerperDualSourceDataset,
) -> tuple[SerperDualSourceCase, ...]:
    return tuple(pair[0] for pair in dataset.target_pairs())


def build_year_stratified_grouped_split(
    dataset: SerperDualSourceDataset,
    *,
    development_target_count: int,
    salt: str,
    version: str,
) -> FrozenGroupedSplit:
    targets = _target_rows(dataset)
    if not 1 <= development_target_count < len(targets):
        raise ValueError("development_target_count must leave at least one test target")
    if not salt.strip() or not version.strip():
        raise ValueError("split salt and version must not be blank")

    strata: dict[int, list[SerperDualSourceCase]] = defaultdict(list)
    for target in targets:
        strata[target.expected_full_identity.release_year].append(target)

    exact_quotas = {
        year: len(members) * development_target_count / len(targets)
        for year, members in strata.items()
    }
    quotas = {year: math.floor(value) for year, value in exact_quotas.items()}
    remainder = development_target_count - sum(quotas.values())
    ranked_remainders = sorted(
        strata,
        key=lambda year: (-(exact_quotas[year] - quotas[year]), year),
    )
    for year in ranked_remainders[:remainder]:
        quotas[year] += 1

    development_ids: set[str] = set()
    for year, members in sorted(strata.items()):
        keyed = sorted(
            members,
            key=lambda case: hashlib.sha256(
                (
                    f"{salt}\0{case.target_id}\0"
                    f"{normalize_text(case.expected_casting)}"
                ).encode()
            ).hexdigest(),
        )
        development_ids.update(case.target_id for case in keyed[: quotas[year]])

    target_ids = [target.target_id for target in targets]
    test_ids = set(target_ids) - development_ids
    if (
        len(development_ids) != development_target_count
        or development_ids & test_ids
        or len(development_ids | test_ids) != len(targets)
    ):
        raise ValueError("grouped split must be disjoint and exhaustive")

    assignments = [
        {
            "target_id": target_id,
            "split": "development" if target_id in development_ids else "test",
        }
        for target_id in target_ids
    ]
    assignment_bytes = json.dumps(
        assignments,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return FrozenGroupedSplit(
        version=version,
        development_target_ids=tuple(
            target_id for target_id in target_ids if target_id in development_ids
        ),
        test_target_ids=tuple(target_id for target_id in target_ids if target_id in test_ids),
        assignment_sha256=hashlib.sha256(assignment_bytes).hexdigest(),
    )


def load_frozen_grouped_split(
    dataset: SerperDualSourceDataset,
    dataset_path: Path = DATASET,
) -> FrozenGroupedSplit:
    if hashlib.sha256(dataset_path.read_bytes()).hexdigest() != FROZEN_DATASET_SHA256:
        raise ValueError("dataset bytes differ from the frozen grouped-split contract")
    if (
        dataset.catalog_sha256 != FROZEN_CATALOG_SHA256
        or dataset.authority_scope != AUTHORITY_SCOPE
        or dataset.target_count != FROZEN_TARGET_COUNT
        or dataset.record_count != FROZEN_RECORD_COUNT
    ):
        raise ValueError("dataset metadata differs from the frozen grouped-split contract")
    split = build_year_stratified_grouped_split(
        dataset,
        development_target_count=FROZEN_DEVELOPMENT_TARGET_COUNT,
        salt=FROZEN_SPLIT_SALT,
        version=FROZEN_SPLIT_VERSION,
    )
    if (
        len(split.development_target_ids) != FROZEN_DEVELOPMENT_TARGET_COUNT
        or len(split.test_target_ids) != FROZEN_TEST_TARGET_COUNT
        or split.assignment_sha256 != FROZEN_SPLIT_SHA256
    ):
        raise ValueError("grouped split differs from the frozen assignment")
    return split


def split_year_counts(
    dataset: SerperDualSourceDataset,
    split: FrozenGroupedSplit,
) -> dict[str, dict[str, int]]:
    development_ids = set(split.development_target_ids)
    counts: dict[str, Counter[int]] = {
        "development": Counter(),
        "test": Counter(),
    }
    for target in _target_rows(dataset):
        name = "development" if target.target_id in development_ids else "test"
        counts[name][target.expected_full_identity.release_year] += 1
    return {
        name: {str(year): count for year, count in sorted(year_counts.items())}
        for name, year_counts in counts.items()
    }


def _project_arm_dataset(
    dataset: SerperDualSourceDataset,
    target_ids: Sequence[str],
    *,
    source_type: SourceType,
    query_variant: QueryVariant,
) -> ImageSearchDataset:
    pairs = {pair[0].target_id: pair for pair in dataset.target_pairs()}
    cases: list[ImageSearchCase] = []
    for index, target_id in enumerate(target_ids, start=1):
        pair = pairs.get(target_id)
        if pair is None:
            raise ValueError(f"selected target {target_id} is absent from the dataset")
        selected = pair[0] if source_type == "image_search" else pair[1]
        if selected.source_type != source_type:
            raise ValueError(f"{target_id} does not contain the requested source type")
        query = selected.query_raw if query_variant == "raw" else selected.query_cleaned
        cases.append(
            ImageSearchCase(
                id=f"isr-{index:04d}",
                query=query,
                expected_casting=selected.expected_casting,
                expected_full_identity=selected.expected_full_identity,
            )
        )
    return ImageSearchDataset(
        dataset_version="image-search-resolver-v2",
        records=cases,
    )


def _evaluate_arm(
    settings: Settings,
    service: ResolverService,
    arm_dataset: ImageSearchDataset,
    source_records: list[dict[str, Any]],
    *,
    source_type: SourceType,
    query_variant: QueryVariant,
) -> FourArmMetrics:
    bindings = bind_dataset_to_source(arm_dataset, source_records)
    target_by_case = {binding.case_id: binding.evaluation_uuid for binding in bindings}
    casting_top1 = 0
    exact_top1 = 0
    recall_at_10 = 0
    recall_at_25 = 0
    reciprocal_rank_sum_at_10 = 0.0
    policy_exact = 0
    policy_matches = 0
    status_counts = {status.value: 0 for status in ResolutionStatus}
    latencies: list[float] = []

    for case in arm_dataset.records:
        signals = extract_signals(case.query, service.color_vocabulary, service.series_vocabulary)
        candidates = service.retrieval.retrieve(signals, settings.candidate_limit)
        if settings.reranker_enabled:
            candidates = service.reranker.rerank(signals, candidates)
        target = target_by_case[case.id]
        rank = next(
            (
                index
                for index, candidate in enumerate(candidates, start=1)
                if candidate.product.canonical_uuid == target
            ),
            None,
        )
        if candidates:
            casting_top1 += normalize_text(
                candidates[0].product.product.casting
            ) == normalize_text(case.expected_casting)
            exact_top1 += candidates[0].product.canonical_uuid == target
        recall_at_10 += rank is not None and rank <= 10
        recall_at_25 += rank is not None and rank <= 25
        if rank is not None and rank <= 10:
            reciprocal_rank_sum_at_10 += 1.0 / rank

        started = time.perf_counter()
        response = service.resolve(ResolveRequest(title=case.query))
        latencies.append((time.perf_counter() - started) * 1000)
        status_counts[response.status.value] += 1
        if response.status is ResolutionStatus.matched:
            policy_matches += 1
            policy_exact += response.canonical_uuid == target

    sample_count = len(arm_dataset.records)
    return FourArmMetrics(
        source_type=source_type,
        query_variant=query_variant,
        sample_count=sample_count,
        casting_top1_accuracy=safe_divide(casting_top1, sample_count),
        exact_release_top1_accuracy=safe_divide(exact_top1, sample_count),
        exact_release_recall_at_10=safe_divide(recall_at_10, sample_count),
        exact_release_recall_at_25=safe_divide(recall_at_25, sample_count),
        exact_release_mrr_at_10=safe_divide(reciprocal_rank_sum_at_10, sample_count),
        policy_exact_accuracy=safe_divide(policy_exact, sample_count),
        policy_precision=safe_divide(policy_exact, policy_matches),
        policy_coverage=safe_divide(policy_matches, sample_count),
        policy_abstention_rate=safe_divide(sample_count - policy_matches, sample_count),
        policy_status_counts=status_counts,
        pipeline_p50_latency_ms=statistics.median(latencies) if latencies else 0.0,
        pipeline_p95_latency_ms=percentile(latencies, 0.95),
        raw_counts={
            "casting_top1_correct": casting_top1,
            "exact_release_top1_correct": exact_top1,
            "exact_release_retrieved_at_10": recall_at_10,
            "exact_release_retrieved_at_25": recall_at_25,
            "exact_release_reciprocal_rank_sum_at_10": round(
                reciprocal_rank_sum_at_10, 12
            ),
            "policy_matches": policy_matches,
            "policy_exact_correct": policy_exact,
        },
    )


def evaluate_four_development_arms(
    settings: Settings,
    dataset: SerperDualSourceDataset,
    split: FrozenGroupedSplit,
    source_records: list[dict[str, Any]],
    *,
    dataset_sha256: str,
) -> FourArmDevelopmentReport:
    if set(split.development_target_ids) & set(split.test_target_ids):
        raise ValueError("development and test targets must be disjoint")
    if len(split.development_target_ids) + len(split.test_target_ids) != dataset.target_count:
        raise ValueError("split must cover every target exactly once")

    catalog = build_evaluation_catalog(source_records)
    human_catalog = load_human_knowledge_catalog(
        settings.human_catalog_path,
        settings.review_family_knowledge_path,
        settings.review_family_knowledge_manifest_path,
    )
    service = ResolverService(settings, catalog, human_catalog)
    arms: dict[str, FourArmMetrics] = {}
    for arm_name, source_type, query_variant in ARM_DEFINITIONS:
        arm_dataset = _project_arm_dataset(
            dataset,
            split.development_target_ids,
            source_type=source_type,
            query_variant=query_variant,
        )
        arms[arm_name] = _evaluate_arm(
            settings,
            service,
            arm_dataset,
            source_records,
            source_type=source_type,
            query_variant=query_variant,
        )

    sample_counts = {metrics.sample_count for metrics in arms.values()}
    if sample_counts != {len(split.development_target_ids)}:
        raise ValueError("four-arm sample membership is not symmetric")
    return FourArmDevelopmentReport(
        schema_version="pvr-serper-dual-source-development-evaluation-v1",
        status="development_only_test_unopened",
        dataset_version=dataset.dataset_version,
        dataset_sha256=dataset_sha256,
        catalog_sha256=dataset.catalog_sha256,
        split_version=split.version,
        split_assignment_sha256=split.assignment_sha256,
        full_target_count=dataset.target_count,
        full_record_count=dataset.record_count,
        development_target_count=len(split.development_target_ids),
        development_record_count=len(split.development_target_ids) * 2,
        test_target_count=len(split.test_target_ids),
        test_record_count=len(split.test_target_ids) * 2,
        candidate_count=len(catalog.products),
        source_binding_count_per_arm=len(split.development_target_ids),
        arms=arms,
        metadata={
            "candidate_limit": settings.candidate_limit,
            "reranker_enabled": settings.reranker_enabled,
            "reranker_provider": settings.reranker_provider,
            "test_targets_scored": 0,
            "row_level_output_persisted": False,
            "catalog_modified": False,
            "model_or_threshold_changed": False,
            "arm_membership_symmetric": True,
            "only_query_text_differs_between_arms": True,
            "authority_note": (
                "Expected identities are relative to the frozen third-party community catalog; "
                "they are not Mattel/manufacturer-certified or global truth."
            ),
        },
    )


def evaluate_frozen_development_arms(
    settings: Settings,
    *,
    dataset_path: Path = DATASET,
    source_path: Path = SOURCE,
) -> FourArmDevelopmentReport:
    dataset = load_serper_dual_source_dataset(dataset_path)
    split = load_frozen_grouped_split(dataset, dataset_path)
    source_records = load_source_records(source_path, expected_count=SOURCE_COUNT)
    return evaluate_four_development_arms(
        settings,
        dataset,
        split,
        source_records,
        dataset_sha256=hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
    )


def _evaluate_raw_pointwise_arms(
    settings: Settings,
    dataset: SerperDualSourceDataset,
    target_ids: Sequence[str],
    source_records: list[dict[str, Any]],
    pointwise_reranker: NeuralPointwiseReranker,
) -> tuple[dict[str, RawRankingMetrics], int]:
    if settings.reranker_enabled:
        raise ValueError("raw Pointwise comparison requires the RRF runtime default")
    if not target_ids or len(target_ids) != len(set(target_ids)):
        raise ValueError("raw Pointwise target IDs must be nonempty and unique")

    catalog = build_evaluation_catalog(source_records)
    human_catalog = load_human_knowledge_catalog(
        settings.human_catalog_path,
        settings.review_family_knowledge_path,
        settings.review_family_knowledge_manifest_path,
    )
    service = ResolverService(settings, catalog, human_catalog)
    arms: dict[str, RawRankingMetrics] = {}
    for source_type in ("image_search", "shopping"):
        arm_dataset = _project_arm_dataset(
            dataset,
            target_ids,
            source_type=source_type,
            query_variant="raw",
        )
        bindings = bind_dataset_to_source(arm_dataset, source_records)
        target_by_case = {binding.case_id: binding.evaluation_uuid for binding in bindings}
        rrf = _RankingAccumulator()
        pointwise = _RankingAccumulator()
        for case in arm_dataset.records:
            signals = extract_signals(
                case.query,
                service.color_vocabulary,
                service.series_vocabulary,
            )
            candidates = service.retrieval.retrieve(signals, settings.candidate_limit)
            target = target_by_case[case.id]
            rrf.add(
                candidates,
                target=target,
                expected_casting=case.expected_casting,
                latency_ms=0.0,
            )
            candidate_ids = tuple(
                candidate.product.canonical_uuid for candidate in candidates
            )
            started = time.perf_counter()
            reranked = pointwise_reranker.rerank(
                signals,
                list(candidates),
                query=case.query,
            )
            rerank_latency_ms = (time.perf_counter() - started) * 1000
            reranked_ids = tuple(
                candidate.product.canonical_uuid for candidate in reranked
            )
            if len(reranked_ids) != len(candidate_ids) or set(reranked_ids) != set(
                candidate_ids
            ):
                raise ValueError("Pointwise must only reorder the frozen RRF candidate set")
            pointwise.add(
                reranked,
                target=target,
                expected_casting=case.expected_casting,
                latency_ms=rerank_latency_ms,
            )
        arms[f"{source_type}_rrf"] = rrf.summarize(
            source_type=source_type,
            ranker="rrf",
        )
        arms[f"{source_type}_neural_pointwise"] = pointwise.summarize(
            source_type=source_type,
            ranker="neural_pointwise",
        )

    if {metrics.sample_count for metrics in arms.values()} != {len(target_ids)}:
        raise ValueError("raw Pointwise arm membership is not symmetric")
    return arms, len(catalog.products)


def evaluate_raw_pointwise_development(
    settings: Settings,
    dataset: SerperDualSourceDataset,
    split: FrozenGroupedSplit,
    source_records: list[dict[str, Any]],
    pointwise_reranker: NeuralPointwiseReranker,
    *,
    dataset_sha256: str,
    model_binding: dict[str, Any] | None = None,
) -> RawPointwiseDevelopmentReport:
    if set(split.development_target_ids) & set(split.test_target_ids):
        raise ValueError("development and test targets must be disjoint")
    if len(split.development_target_ids) + len(split.test_target_ids) != dataset.target_count:
        raise ValueError("split must cover every target exactly once")
    arms, candidate_count = _evaluate_raw_pointwise_arms(
        settings,
        dataset,
        split.development_target_ids,
        source_records,
        pointwise_reranker,
    )
    return RawPointwiseDevelopmentReport(
        schema_version="pvr-serper-dual-source-raw-pointwise-development-v1",
        status="development_only_raw_pointwise_test_unopened",
        dataset_sha256=dataset_sha256,
        catalog_sha256=dataset.catalog_sha256,
        split_version=split.version,
        split_assignment_sha256=split.assignment_sha256,
        development_target_count=len(split.development_target_ids),
        test_target_count=len(split.test_target_ids),
        candidate_count=candidate_count,
        candidate_limit=settings.candidate_limit,
        arms=arms,
        metadata={
            "query_representation": "raw_only",
            "cleaned_arms_scored": 0,
            "test_targets_scored": 0,
            "row_level_output_persisted": False,
            "candidate_membership_changed_by_pointwise": False,
            "calibration_or_policy_evaluated": False,
            "model_refit": False,
            "thresholds_changed": False,
            "runtime_default_changed": False,
            "pointwise_model_version": pointwise_reranker.version,
            "model_binding": model_binding or {},
            "authority_note": (
                "Expected identities are relative to the frozen third-party community catalog; "
                "they are not Mattel/manufacturer-certified or global truth."
            ),
        },
    )


def evaluate_raw_pointwise_final_test(
    settings: Settings,
    dataset: SerperDualSourceDataset,
    split: FrozenGroupedSplit,
    source_records: list[dict[str, Any]],
    pointwise_reranker: NeuralPointwiseReranker,
    *,
    dataset_sha256: str,
    owner_authorization_sha256: str,
    model_binding: dict[str, Any] | None = None,
) -> RawPointwiseFinalTestReport:
    if set(split.development_target_ids) & set(split.test_target_ids):
        raise ValueError("development and test targets must be disjoint")
    if len(split.development_target_ids) + len(split.test_target_ids) != dataset.target_count:
        raise ValueError("split must cover every target exactly once")
    arms, candidate_count = _evaluate_raw_pointwise_arms(
        settings,
        dataset,
        split.test_target_ids,
        source_records,
        pointwise_reranker,
    )
    return RawPointwiseFinalTestReport(
        schema_version="pvr-serper-dual-source-raw-pointwise-final-test-v1",
        status="final_test_evaluated_once_aggregate_only",
        dataset_sha256=dataset_sha256,
        catalog_sha256=dataset.catalog_sha256,
        split_version=split.version,
        split_assignment_sha256=split.assignment_sha256,
        test_target_count=len(split.test_target_ids),
        candidate_count=candidate_count,
        candidate_limit=settings.candidate_limit,
        arms=arms,
        metadata={
            "owner_authorization_sha256": owner_authorization_sha256,
            "query_representation": "raw_only",
            "selected_ranker": "neural_pointwise",
            "development_targets_scored_in_final_run": 0,
            "test_targets_scored": len(split.test_target_ids),
            "test_run_count": 1,
            "row_level_output_persisted": False,
            "candidate_membership_changed_by_pointwise": False,
            "calibration_or_policy_evaluated": False,
            "model_refit": False,
            "thresholds_changed": False,
            "runtime_default_changed": False,
            "pointwise_model_version": pointwise_reranker.version,
            "model_binding": model_binding or {},
            "authority_note": (
                "Expected identities are relative to the frozen third-party community catalog; "
                "they are not Mattel/manufacturer-certified or global truth."
            ),
        },
    )


def _assert_rrf_reproduces_frozen_baseline(
    report: RawPointwiseDevelopmentReport,
    baseline: dict[str, Any],
) -> None:
    keys = {
        "casting_top1_correct",
        "exact_release_top1_correct",
        "exact_release_retrieved_at_10",
        "exact_release_retrieved_at_25",
        "exact_release_reciprocal_rank_sum_at_10",
    }
    for source_type in ("image_search", "shopping"):
        actual = report.arms[f"{source_type}_rrf"].raw_counts
        expected = baseline["arms"][f"{source_type}_raw"]["raw_counts"]
        for key in keys:
            actual_value = actual[key]
            expected_value = expected[key]
            if not math.isclose(float(actual_value), float(expected_value), abs_tol=1e-12):
                raise ValueError(f"{source_type} RRF baseline did not reproduce for {key}")


def evaluate_frozen_raw_pointwise_development(
    settings: Settings,
    *,
    root: Path,
    dataset_path: Path = DATASET,
    source_path: Path = SOURCE,
) -> RawPointwiseDevelopmentReport:
    dataset = load_serper_dual_source_dataset(dataset_path)
    split = load_frozen_grouped_split(dataset, dataset_path)
    baseline = load_frozen_development_baseline(root / DEVELOPMENT_BASELINE)
    source_records = load_source_records(source_path, expected_count=SOURCE_COUNT)
    selection = check_development_selection(root)
    config_path = root / POINTWISE_CONFIG
    model_path = root / POINTWISE_MODEL
    config = load_pointwise_model_config(config_path)
    validate_local_pointwise_model(config, model_path)
    scorer = LocalPointwiseScorer.load(config, model_path)
    model_manifest_path = model_path / "manifest.json"
    model_manifest_sha256 = hashlib.sha256(model_manifest_path.read_bytes()).hexdigest()
    if model_manifest_sha256 != selection.model_bindings.pointwise.local_manifest_sha256:
        raise ValueError("Pointwise model differs from the frozen development winner")
    report = evaluate_raw_pointwise_development(
        settings,
        dataset,
        split,
        source_records,
        NeuralPointwiseReranker(scorer),
        dataset_sha256=hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        model_binding={
            "selection_path": str(SELECTION),
            "selection_sha256": hashlib.sha256((root / SELECTION).read_bytes()).hexdigest(),
            "selection_winner": selection.winner,
            "config_path": str(POINTWISE_CONFIG),
            "config_sha256": config.config_sha256,
            "model_manifest_path": str(POINTWISE_MODEL / "manifest.json"),
            "model_manifest_sha256": model_manifest_sha256,
            "model_id": config.model_id,
            "revision": config.revision,
        },
    )
    _assert_rrf_reproduces_frozen_baseline(report, baseline)
    report.metadata["rrf_baseline_reproduced"] = True
    report.metadata["baseline_sha256"] = FROZEN_DEVELOPMENT_BASELINE_SHA256
    return report


def _artifact_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            keys.add(str(key))
            keys.update(_artifact_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.update(_artifact_keys(nested))
    return keys


def load_frozen_development_baseline(
    path: Path = DEVELOPMENT_BASELINE,
) -> dict[str, Any]:
    if hashlib.sha256(path.read_bytes()).hexdigest() != FROZEN_DEVELOPMENT_BASELINE_SHA256:
        raise ValueError("development baseline bytes differ from the frozen artifact")
    payload = _read_object(path)
    if (
        payload.get("schema_version")
        != "pvr-serper-dual-source-development-baseline-v1"
        or payload.get("status") != "development_baseline_frozen_test_unopened"
    ):
        raise ValueError("unexpected development baseline schema or status")
    dataset = payload.get("dataset")
    split = payload.get("split")
    catalog = payload.get("catalog")
    configuration = payload.get("configuration")
    if not all(isinstance(value, dict) for value in (dataset, split, catalog, configuration)):
        raise ValueError("development baseline bindings must be objects")
    assert isinstance(dataset, dict)
    assert isinstance(split, dict)
    assert isinstance(catalog, dict)
    assert isinstance(configuration, dict)
    if dataset != {
        "path": str(DATASET),
        "sha256": FROZEN_DATASET_SHA256,
        "target_count": FROZEN_TARGET_COUNT,
        "record_count": FROZEN_RECORD_COUNT,
    }:
        raise ValueError("development baseline dataset binding changed")
    if (
        split.get("version") != FROZEN_SPLIT_VERSION
        or split.get("assignment_sha256") != FROZEN_SPLIT_SHA256
        or split.get("development_target_count") != FROZEN_DEVELOPMENT_TARGET_COUNT
        or split.get("development_record_count") != FROZEN_DEVELOPMENT_TARGET_COUNT * 2
        or split.get("test_target_count") != FROZEN_TEST_TARGET_COUNT
        or split.get("test_record_count") != FROZEN_TEST_TARGET_COUNT * 2
    ):
        raise ValueError("development baseline split binding changed")
    if catalog != {"sha256": FROZEN_CATALOG_SHA256, "candidate_count": SOURCE_COUNT}:
        raise ValueError("development baseline catalog binding changed")
    if configuration != {
        "backend": "offline",
        "dense_provider": "hashing-v1",
        "dense_dimensions": 192,
        "candidate_limit": 25,
        "reranker_enabled": False,
        "reranker_provider": "heuristic-v1",
        "policy_version": "fixture-v1-rrf-trained-v2",
    }:
        raise ValueError("development baseline configuration changed")

    arms = payload.get("arms")
    if not isinstance(arms, dict) or set(arms) != {name for name, _, _ in ARM_DEFINITIONS}:
        raise ValueError("development baseline arm set changed")
    for arm_name, source_type, query_variant in ARM_DEFINITIONS:
        arm = arms[arm_name]
        if not isinstance(arm, dict):
            raise TypeError(f"{arm_name} must be an object")
        if (
            arm.get("source_type") != source_type
            or arm.get("query_variant") != query_variant
            or arm.get("sample_count") != FROZEN_DEVELOPMENT_TARGET_COUNT
        ):
            raise ValueError(f"{arm_name} binding changed")
        metrics = arm.get("metrics")
        counts = arm.get("raw_counts")
        if not isinstance(metrics, dict) or not isinstance(counts, dict):
            raise TypeError(f"{arm_name} metrics and raw counts must be objects")
        status_counts = counts.get("policy_status_counts")
        if not isinstance(status_counts, dict) or sum(status_counts.values()) != 100:
            raise ValueError(f"{arm_name} policy statuses must total 100")
        policy_matches = counts.get("policy_matches")
        policy_exact = counts.get("policy_exact_correct")
        if not isinstance(policy_matches, int) or not isinstance(policy_exact, int):
            raise TypeError(f"{arm_name} policy counts must be integers")
        expected_metrics = {
            "casting_top1_accuracy": safe_divide(counts["casting_top1_correct"], 100),
            "exact_release_top1_accuracy": safe_divide(
                counts["exact_release_top1_correct"], 100
            ),
            "exact_release_recall_at_10": safe_divide(
                counts["exact_release_retrieved_at_10"], 100
            ),
            "exact_release_recall_at_25": safe_divide(
                counts["exact_release_retrieved_at_25"], 100
            ),
            "exact_release_mrr_at_10": safe_divide(
                counts["exact_release_reciprocal_rank_sum_at_10"], 100
            ),
            "policy_exact_accuracy": safe_divide(policy_exact, 100),
            "policy_precision": safe_divide(policy_exact, policy_matches),
            "policy_coverage": safe_divide(policy_matches, 100),
            "policy_abstention_rate": safe_divide(100 - policy_matches, 100),
        }
        for metric_name, expected in expected_metrics.items():
            actual = metrics.get(metric_name)
            if not isinstance(actual, int | float) or not math.isclose(
                actual, expected, abs_tol=1e-12
            ):
                raise ValueError(f"{arm_name} {metric_name} is not traceable to raw counts")
        if status_counts.get("matched") != policy_matches:
            raise ValueError(f"{arm_name} matched status count changed")

    comparisons = payload.get("comparisons")
    if not isinstance(comparisons, dict):
        raise TypeError("development comparisons must be an object")
    comparison_contract = {
        "image_search_cleaned_minus_raw": ("image_search_cleaned", "image_search_raw"),
        "shopping_cleaned_minus_raw": ("shopping_cleaned", "shopping_raw"),
        "shopping_raw_minus_image_search_raw": ("shopping_raw", "image_search_raw"),
    }
    for comparison_name, (left_name, right_name) in comparison_contract.items():
        values = comparisons.get(comparison_name)
        if not isinstance(values, dict):
            raise TypeError(f"{comparison_name} must be an object")
        for metric_name, actual in values.items():
            left = arms[left_name]["metrics"].get(metric_name)
            right = arms[right_name]["metrics"].get(metric_name)
            if not isinstance(left, int | float) or not isinstance(right, int | float):
                raise TypeError(f"{comparison_name} references an invalid metric")
            if not isinstance(actual, int | float) or not math.isclose(
                actual, left - right, abs_tol=1e-12
            ):
                raise ValueError(f"{comparison_name} is not traceable to arm metrics")

    decision = payload.get("decision")
    guardrails = payload.get("guardrails")
    if not isinstance(decision, dict) or not isinstance(guardrails, dict):
        raise TypeError("development decision and guardrails must be objects")
    if (
        decision.get("development_leader") != "shopping_raw"
        or decision.get("primary_representation_by_source")
        != {"image_search": "raw", "shopping": "raw"}
        or decision.get("runtime_activation_allowed") is not False
        or decision.get("threshold_retuning_allowed") is not False
        or decision.get("test_evaluation_allowed") is not False
    ):
        raise ValueError("development decision changed")
    if guardrails != {
        "test_targets_scored": 0,
        "row_level_output_persisted": False,
        "model_changed": False,
        "features_changed": False,
        "thresholds_changed": False,
        "runtime_changed": False,
    }:
        raise ValueError("development guardrails changed")
    forbidden_keys = {
        "query",
        "query_raw",
        "query_cleaned",
        "target_id",
        "expected_casting",
        "expected_full_identity",
        "candidate",
        "candidates",
        "prediction",
        "predictions",
    }
    leaked = forbidden_keys & _artifact_keys(payload)
    if leaked:
        raise ValueError(f"development baseline contains row-level fields: {sorted(leaked)}")
    return payload


def load_frozen_raw_pointwise_development(
    path: Path = RAW_POINTWISE_DEVELOPMENT,
) -> dict[str, Any]:
    if (
        hashlib.sha256(path.read_bytes()).hexdigest()
        != FROZEN_RAW_POINTWISE_DEVELOPMENT_SHA256
    ):
        raise ValueError("raw Pointwise artifact bytes differ from the frozen result")
    payload = _read_object(path)
    if (
        payload.get("schema_version")
        != "pvr-serper-dual-source-raw-pointwise-development-v1"
        or payload.get("status") != "development_pointwise_selected_test_unopened"
    ):
        raise ValueError("unexpected raw Pointwise schema or status")
    if payload.get("dataset") != {
        "path": str(DATASET),
        "sha256": FROZEN_DATASET_SHA256,
        "target_count": FROZEN_TARGET_COUNT,
        "record_count": FROZEN_RECORD_COUNT,
    }:
        raise ValueError("raw Pointwise dataset binding changed")
    if payload.get("split") != {
        "version": FROZEN_SPLIT_VERSION,
        "assignment_sha256": FROZEN_SPLIT_SHA256,
        "development_target_count": FROZEN_DEVELOPMENT_TARGET_COUNT,
        "test_target_count": FROZEN_TEST_TARGET_COUNT,
    }:
        raise ValueError("raw Pointwise split binding changed")
    if payload.get("catalog") != {
        "sha256": FROZEN_CATALOG_SHA256,
        "candidate_count": SOURCE_COUNT,
        "candidate_limit": 25,
    }:
        raise ValueError("raw Pointwise catalog binding changed")
    if payload.get("pointwise_model") != {
        "model_id": "cross-encoder/ms-marco-MiniLM-L6-v2",
        "revision": "233902d25c440f23af6f7d6e94d2946bac0bee0a",
        "config_sha256": "3a88163cc7abc84468024f5e6410e0ca489a80a710b67b4c2474c4b4f7d7fad6",
        "model_manifest_sha256": (
            "32f889bb415ef5a56760a299da0635e8e1704d46fe0b11ded06c563de896feb8"
        ),
        "prior_selection_sha256": (
            "1f241ae3513572b0b85dd24aa5bc1dffb1efeb95275ce9f0f30ca799358399c7"
        ),
        "prior_selection_winner": "neural_pointwise",
        "refit_for_this_dataset": False,
    }:
        raise ValueError("raw Pointwise model binding changed")

    arms = payload.get("arms")
    arm_contract: dict[str, tuple[SourceType, Literal["rrf", "neural_pointwise"]]] = {
        "image_search_rrf": ("image_search", "rrf"),
        "image_search_neural_pointwise": ("image_search", "neural_pointwise"),
        "shopping_rrf": ("shopping", "rrf"),
        "shopping_neural_pointwise": ("shopping", "neural_pointwise"),
    }
    if not isinstance(arms, dict) or set(arms) != set(arm_contract):
        raise ValueError("raw Pointwise arm set changed")
    for arm_name, (source_type, ranker) in arm_contract.items():
        arm = arms[arm_name]
        if not isinstance(arm, dict):
            raise TypeError(f"{arm_name} must be an object")
        if (
            arm.get("source_type") != source_type
            or arm.get("ranker") != ranker
            or arm.get("sample_count") != FROZEN_DEVELOPMENT_TARGET_COUNT
        ):
            raise ValueError(f"{arm_name} binding changed")
        metrics = arm.get("metrics")
        counts = arm.get("raw_counts")
        if not isinstance(metrics, dict) or not isinstance(counts, dict):
            raise TypeError(f"{arm_name} metrics and counts must be objects")
        expected_metrics = {
            "casting_top1_accuracy": safe_divide(
                counts["casting_top1_correct"], FROZEN_DEVELOPMENT_TARGET_COUNT
            ),
            "exact_release_top1_accuracy": safe_divide(
                counts["exact_release_top1_correct"], FROZEN_DEVELOPMENT_TARGET_COUNT
            ),
            "exact_release_recall_at_10": safe_divide(
                counts["exact_release_retrieved_at_10"], FROZEN_DEVELOPMENT_TARGET_COUNT
            ),
            "exact_release_recall_at_25": safe_divide(
                counts["exact_release_retrieved_at_25"], FROZEN_DEVELOPMENT_TARGET_COUNT
            ),
            "exact_release_mrr_at_10": safe_divide(
                counts["exact_release_reciprocal_rank_sum_at_10"],
                FROZEN_DEVELOPMENT_TARGET_COUNT,
            ),
        }
        for metric_name, expected in expected_metrics.items():
            actual = metrics.get(metric_name)
            if not isinstance(actual, int | float) or not math.isclose(
                actual, expected, abs_tol=1e-12
            ):
                raise ValueError(f"{arm_name} {metric_name} is not traceable to counts")
        for latency_name in ("rerank_p50_latency_ms", "rerank_p95_latency_ms"):
            latency = metrics.get(latency_name)
            if not isinstance(latency, int | float) or latency < 0:
                raise ValueError(f"{arm_name} {latency_name} is invalid")

    deltas = payload.get("pointwise_minus_rrf")
    if not isinstance(deltas, dict):
        raise TypeError("raw Pointwise deltas must be an object")
    for source_type in ("image_search", "shopping"):
        source_deltas = deltas.get(source_type)
        if not isinstance(source_deltas, dict):
            raise TypeError(f"{source_type} deltas must be an object")
        pointwise_metrics = arms[f"{source_type}_neural_pointwise"]["metrics"]
        rrf_metrics = arms[f"{source_type}_rrf"]["metrics"]
        for metric_name, actual in source_deltas.items():
            expected = pointwise_metrics[metric_name] - rrf_metrics[metric_name]
            if not isinstance(actual, int | float) or not math.isclose(
                actual, expected, abs_tol=1e-12
            ):
                raise ValueError(f"{source_type} {metric_name} delta is not traceable")

    decision = payload.get("decision")
    guardrails = payload.get("guardrails")
    if not isinstance(decision, dict) or not isinstance(guardrails, dict):
        raise TypeError("raw Pointwise decision and guardrails must be objects")
    if (
        decision.get("selected_development_ranker") != "neural_pointwise"
        or decision.get("selected_query_representation") != "raw"
        or decision.get("development_leader")
        != "shopping_raw_neural_pointwise"
        or decision.get("policy_or_calibration_selected") is not False
        or decision.get("runtime_activation_allowed") is not False
        or decision.get("test_evaluation_allowed") is not False
    ):
        raise ValueError("raw Pointwise decision changed")
    if guardrails != {
        "rrf_baseline_reproduced": True,
        "cleaned_arms_scored": 0,
        "test_targets_scored": 0,
        "row_level_output_persisted": False,
        "candidate_membership_changed": False,
        "model_refit": False,
        "calibration_or_policy_evaluated": False,
        "thresholds_changed": False,
        "runtime_changed": False,
    }:
        raise ValueError("raw Pointwise guardrails changed")
    forbidden_keys = {
        "query",
        "query_raw",
        "query_cleaned",
        "target_id",
        "expected_casting",
        "expected_full_identity",
        "candidate",
        "candidates",
        "prediction",
        "predictions",
    }
    leaked = forbidden_keys & _artifact_keys(payload)
    if leaked:
        raise ValueError(f"raw Pointwise artifact contains row-level fields: {sorted(leaked)}")
    return payload


def load_sdse_t4_owner_authorization(
    path: Path = SDSE_T4_OWNER_AUTHORIZATION,
) -> dict[str, Any]:
    if (
        hashlib.sha256(path.read_bytes()).hexdigest()
        != FROZEN_SDSE_T4_OWNER_AUTHORIZATION_SHA256
    ):
        raise ValueError("SDSE-T4 owner authorization bytes changed")
    payload = _read_object(path)
    if (
        payload.get("schema_version")
        != "pvr-serper-dual-source-t4-owner-authorization-v1"
        or payload.get("gate") != "SDSE-T4"
        or payload.get("authorized_by") != "project_owner"
        or payload.get("owner_statement_sha256")
        != "37e6c4a73e7b5f0bafa28453bc8756ef3d45f87162d0d1f802d1ff4bc2b26389"
        or payload.get("decision") != "execute_one_time_aggregate_final_test"
    ):
        raise ValueError("SDSE-T4 owner authorization contract changed")
    bindings = payload.get("bindings")
    if bindings != {
        "dataset_sha256": FROZEN_DATASET_SHA256,
        "split_assignment_sha256": FROZEN_SPLIT_SHA256,
        "development_selection_sha256": FROZEN_RAW_POINTWISE_DEVELOPMENT_SHA256,
        "selected_query_representation": "raw",
        "selected_ranker": "neural_pointwise",
        "test_target_count": FROZEN_TEST_TARGET_COUNT,
        "source_count": 2,
    }:
        raise ValueError("SDSE-T4 authorization bindings changed")
    return payload


def evaluate_frozen_raw_pointwise_final_test(
    settings: Settings,
    *,
    root: Path,
    dataset_path: Path = DATASET,
    source_path: Path = SOURCE,
    output_path: Path = RAW_POINTWISE_FINAL_TEST,
) -> RawPointwiseFinalTestReport:
    active_output_path = output_path if output_path.is_absolute() else root / output_path
    if active_output_path.exists():
        raise FileExistsError("SDSE-T4 final test artifact already exists; rerun is prohibited")
    load_sdse_t4_owner_authorization(root / SDSE_T4_OWNER_AUTHORIZATION)
    development_selection = load_frozen_raw_pointwise_development(
        root / RAW_POINTWISE_DEVELOPMENT
    )
    if development_selection["decision"]["selected_development_ranker"] != (
        "neural_pointwise"
    ):
        raise ValueError("SDSE-T4 requires the frozen Pointwise development winner")
    dataset = load_serper_dual_source_dataset(dataset_path)
    split = load_frozen_grouped_split(dataset, dataset_path)
    source_records = load_source_records(source_path, expected_count=SOURCE_COUNT)
    prior_selection = check_development_selection(root)
    config_path = root / POINTWISE_CONFIG
    model_path = root / POINTWISE_MODEL
    config = load_pointwise_model_config(config_path)
    validate_local_pointwise_model(config, model_path)
    scorer = LocalPointwiseScorer.load(config, model_path)
    model_manifest_path = model_path / "manifest.json"
    model_manifest_sha256 = hashlib.sha256(model_manifest_path.read_bytes()).hexdigest()
    if (
        model_manifest_sha256
        != prior_selection.model_bindings.pointwise.local_manifest_sha256
    ):
        raise ValueError("Pointwise model differs from the frozen development winner")
    return evaluate_raw_pointwise_final_test(
        settings,
        dataset,
        split,
        source_records,
        NeuralPointwiseReranker(scorer),
        dataset_sha256=hashlib.sha256(dataset_path.read_bytes()).hexdigest(),
        owner_authorization_sha256=FROZEN_SDSE_T4_OWNER_AUTHORIZATION_SHA256,
        model_binding={
            "development_selection_sha256": FROZEN_RAW_POINTWISE_DEVELOPMENT_SHA256,
            "prior_selection_sha256": hashlib.sha256(
                (root / SELECTION).read_bytes()
            ).hexdigest(),
            "config_sha256": config.config_sha256,
            "model_manifest_sha256": model_manifest_sha256,
            "model_id": config.model_id,
            "revision": config.revision,
        },
    )


def load_frozen_raw_pointwise_final_test(
    path: Path = RAW_POINTWISE_FINAL_TEST,
) -> dict[str, Any]:
    if (
        hashlib.sha256(path.read_bytes()).hexdigest()
        != FROZEN_RAW_POINTWISE_FINAL_TEST_SHA256
    ):
        raise ValueError("raw Pointwise final-test bytes differ from the frozen result")
    payload = _read_object(path)
    if (
        payload.get("schema_version")
        != "pvr-serper-dual-source-raw-pointwise-final-test-v1"
        or payload.get("status") != "final_test_evaluated_once_aggregate_only"
    ):
        raise ValueError("unexpected raw Pointwise final-test schema or status")
    if payload.get("owner_authorization") != {
        "path": str(SDSE_T4_OWNER_AUTHORIZATION),
        "sha256": FROZEN_SDSE_T4_OWNER_AUTHORIZATION_SHA256,
    }:
        raise ValueError("final-test owner authorization binding changed")
    if payload.get("dataset") != {
        "path": str(DATASET),
        "sha256": FROZEN_DATASET_SHA256,
        "target_count": FROZEN_TARGET_COUNT,
        "record_count": FROZEN_RECORD_COUNT,
    }:
        raise ValueError("final-test dataset binding changed")
    if payload.get("split") != {
        "version": FROZEN_SPLIT_VERSION,
        "assignment_sha256": FROZEN_SPLIT_SHA256,
        "development_target_count": FROZEN_DEVELOPMENT_TARGET_COUNT,
        "test_target_count": FROZEN_TEST_TARGET_COUNT,
    }:
        raise ValueError("final-test split binding changed")
    if payload.get("catalog") != {
        "sha256": FROZEN_CATALOG_SHA256,
        "candidate_count": SOURCE_COUNT,
        "candidate_limit": 25,
    }:
        raise ValueError("final-test catalog binding changed")
    if payload.get("pointwise_model") != {
        "development_selection_sha256": FROZEN_RAW_POINTWISE_DEVELOPMENT_SHA256,
        "model_id": "cross-encoder/ms-marco-MiniLM-L6-v2",
        "revision": "233902d25c440f23af6f7d6e94d2946bac0bee0a",
        "config_sha256": "3a88163cc7abc84468024f5e6410e0ca489a80a710b67b4c2474c4b4f7d7fad6",
        "model_manifest_sha256": (
            "32f889bb415ef5a56760a299da0635e8e1704d46fe0b11ded06c563de896feb8"
        ),
        "refit_for_final_test": False,
    }:
        raise ValueError("final-test Pointwise model binding changed")

    arms = payload.get("arms")
    arm_contract: dict[str, tuple[SourceType, Literal["rrf", "neural_pointwise"]]] = {
        "image_search_rrf": ("image_search", "rrf"),
        "image_search_neural_pointwise": ("image_search", "neural_pointwise"),
        "shopping_rrf": ("shopping", "rrf"),
        "shopping_neural_pointwise": ("shopping", "neural_pointwise"),
    }
    if not isinstance(arms, dict) or set(arms) != set(arm_contract):
        raise ValueError("final-test arm set changed")
    for arm_name, (source_type, ranker) in arm_contract.items():
        arm = arms[arm_name]
        if not isinstance(arm, dict):
            raise TypeError(f"{arm_name} must be an object")
        if (
            arm.get("source_type") != source_type
            or arm.get("ranker") != ranker
            or arm.get("sample_count") != FROZEN_TEST_TARGET_COUNT
        ):
            raise ValueError(f"{arm_name} final-test binding changed")
        metrics = arm.get("metrics")
        counts = arm.get("raw_counts")
        if not isinstance(metrics, dict) or not isinstance(counts, dict):
            raise TypeError(f"{arm_name} final-test metrics and counts must be objects")
        expected_metrics = {
            "casting_top1_accuracy": safe_divide(
                counts["casting_top1_correct"], FROZEN_TEST_TARGET_COUNT
            ),
            "exact_release_top1_accuracy": safe_divide(
                counts["exact_release_top1_correct"], FROZEN_TEST_TARGET_COUNT
            ),
            "exact_release_recall_at_10": safe_divide(
                counts["exact_release_retrieved_at_10"], FROZEN_TEST_TARGET_COUNT
            ),
            "exact_release_recall_at_25": safe_divide(
                counts["exact_release_retrieved_at_25"], FROZEN_TEST_TARGET_COUNT
            ),
            "exact_release_mrr_at_10": safe_divide(
                counts["exact_release_reciprocal_rank_sum_at_10"],
                FROZEN_TEST_TARGET_COUNT,
            ),
        }
        for metric_name, expected in expected_metrics.items():
            actual = metrics.get(metric_name)
            if not isinstance(actual, int | float) or not math.isclose(
                actual, expected, abs_tol=1e-12
            ):
                raise ValueError(
                    f"{arm_name} final-test {metric_name} is not traceable"
                )

    deltas = payload.get("pointwise_minus_rrf")
    if not isinstance(deltas, dict):
        raise TypeError("final-test deltas must be an object")
    for source_type in ("image_search", "shopping"):
        source_deltas = deltas.get(source_type)
        if not isinstance(source_deltas, dict):
            raise TypeError(f"{source_type} final-test deltas must be an object")
        pointwise_metrics = arms[f"{source_type}_neural_pointwise"]["metrics"]
        rrf_metrics = arms[f"{source_type}_rrf"]["metrics"]
        for metric_name, actual in source_deltas.items():
            expected = pointwise_metrics[metric_name] - rrf_metrics[metric_name]
            if not isinstance(actual, int | float) or not math.isclose(
                actual, expected, abs_tol=1e-12
            ):
                raise ValueError(f"{source_type} final-test delta is not traceable")

    combined = payload.get("combined_metrics")
    if not isinstance(combined, dict) or combined.get("sample_count") != 100:
        raise ValueError("final-test combined metric denominator changed")
    for ranker in ("rrf", "neural_pointwise"):
        metrics = combined.get(ranker)
        if not isinstance(metrics, dict):
            raise TypeError(f"combined {ranker} metrics must be an object")
        left = arms[f"image_search_{ranker}"]["raw_counts"]
        right = arms[f"shopping_{ranker}"]["raw_counts"]
        combined_expected = {
            "casting_top1_accuracy": safe_divide(
                left["casting_top1_correct"] + right["casting_top1_correct"], 100
            ),
            "exact_release_top1_accuracy": safe_divide(
                left["exact_release_top1_correct"]
                + right["exact_release_top1_correct"],
                100,
            ),
            "exact_release_recall_at_10": safe_divide(
                left["exact_release_retrieved_at_10"]
                + right["exact_release_retrieved_at_10"],
                100,
            ),
            "exact_release_recall_at_25": safe_divide(
                left["exact_release_retrieved_at_25"]
                + right["exact_release_retrieved_at_25"],
                100,
            ),
            "exact_release_mrr_at_10": safe_divide(
                left["exact_release_reciprocal_rank_sum_at_10"]
                + right["exact_release_reciprocal_rank_sum_at_10"],
                100,
            ),
        }
        for metric_name, expected in combined_expected.items():
            actual = metrics.get(metric_name)
            if not isinstance(actual, int | float) or not math.isclose(
                actual, expected, abs_tol=1e-12
            ):
                raise ValueError(f"combined {ranker} {metric_name} is not traceable")

    conclusion = payload.get("conclusion")
    guardrails = payload.get("guardrails")
    if not isinstance(conclusion, dict) or not isinstance(guardrails, dict):
        raise TypeError("final-test conclusion and guardrails must be objects")
    if (
        conclusion.get("selected_ranker_supported_on_final_test") is not True
        or conclusion.get("runtime_activation_allowed") is not False
        or conclusion.get("policy_claim_allowed") is not False
    ):
        raise ValueError("final-test conclusion changed")
    if guardrails != {
        "authorized_test_run_count": 1,
        "completed_test_run_count": 1,
        "development_targets_scored_in_final_run": 0,
        "test_targets_scored": FROZEN_TEST_TARGET_COUNT,
        "cleaned_arms_scored": 0,
        "row_level_output_persisted": False,
        "candidate_membership_changed": False,
        "model_refit": False,
        "calibration_or_policy_evaluated": False,
        "thresholds_changed": False,
        "runtime_changed": False,
        "rerun_allowed": False,
    }:
        raise ValueError("final-test guardrails changed")
    forbidden_keys = {
        "query",
        "query_raw",
        "query_cleaned",
        "target_id",
        "expected_casting",
        "expected_full_identity",
        "candidate",
        "candidates",
        "prediction",
        "predictions",
    }
    leaked = forbidden_keys & _artifact_keys(payload)
    if leaked:
        raise ValueError(f"final-test artifact contains row-level fields: {sorted(leaked)}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the frozen Serper dual-source split or evaluate development arms."
    )
    parser.add_argument("--dataset", type=Path, default=DATASET)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--evaluate-development", action="store_true")
    parser.add_argument("--acknowledge-source-relative-evaluation", action="store_true")
    arguments = parser.parse_args()
    dataset = load_serper_dual_source_dataset(arguments.dataset)
    split = load_frozen_grouped_split(dataset, arguments.dataset)
    if arguments.evaluate_development:
        if not arguments.acknowledge_source_relative_evaluation:
            parser.error(
                "--acknowledge-source-relative-evaluation is required for development scoring"
            )
        evaluation = evaluate_frozen_development_arms(
            Settings.from_env(),
            dataset_path=arguments.dataset,
            source_path=arguments.source,
        )
        print(json.dumps(asdict(evaluation), ensure_ascii=False, indent=2, sort_keys=True))
        return
    report = {
        "schema_version": "pvr-serper-dual-source-split-readiness-v1",
        "dataset_sha256": FROZEN_DATASET_SHA256,
        "split_version": split.version,
        "split_assignment_sha256": split.assignment_sha256,
        "target_count": dataset.target_count,
        "record_count": dataset.record_count,
        "development_target_count": len(split.development_target_ids),
        "development_record_count": len(split.development_target_ids) * 2,
        "test_target_count": len(split.test_target_ids),
        "test_record_count": len(split.test_target_ids) * 2,
        "year_counts": split_year_counts(dataset, split),
        "pair_leakage_count": 0,
        "row_level_assignment_persisted": False,
        "resolver_evaluation_executed": False,
        "authority_scope": AUTHORITY_SCOPE,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
