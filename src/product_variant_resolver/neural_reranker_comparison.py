"""Immutable protocol and label-blind candidate-pool lifecycle for neural reranker v1.

This module owns experiment orchestration only.  It reuses the unchanged canonical retrieval
components and writes no formal artifact unless an explicit freeze function is called.
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import math
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, cast

from .catalog import Catalog, catalog_checksum, load_catalog
from .neural_reranking import (
    ARMS,
    FEATURE_SCHEMA,
    LISTWISE_ARCHITECTURE,
    LISTWISE_BATCH_SIZE,
    LISTWISE_LEARNING_RATE,
    LISTWISE_MAX_EPOCHS,
    LISTWISE_PATIENCE,
    LISTWISE_SEED,
    LISTWISE_WEIGHT_DECAY,
    POINTWISE_LICENSE,
    POINTWISE_MODEL_ID,
    POINTWISE_REVISION,
    SOURCE_NAMES,
    STRUCTURED_NAMES,
    CandidatePoolRow,
    CandidateTextFields,
    FeatureNormalizer,
    FrozenCandidate,
    FrozenSignals,
    ListwiseExample,
    ListwiseTrainingResult,
    LocalPointwiseScorer,
    MetricValue,
    ScoredCase,
    TrainingEpoch,
    acquire_pointwise_model,
    build_candidate_set_reranker,
    candidate_feature_vector,
    canonical_json_bytes,
    fit_train_feature_normalizer,
    load_pointwise_model_config,
    paired_rank_transitions,
    rank_scores,
    ranking_metrics,
    render_candidate_text,
    save_listwise_checkpoint,
    score_listwise_features,
    select_early_stopping_epoch,
    sha256_bytes,
    sha256_path,
    train_listwise_model,
    validate_benchmark_contract,
    validate_candidate_pool_payload,
    validate_label_blind_payload,
    validate_listwise_checkpoint,
    validate_local_pointwise_model,
    validate_raw_test_payload,
)
from .retrieval import (
    Candidate,
    CandidateRetrievalService,
    DenseRetriever,
    HashingEmbedding,
    Retriever,
    SparseRetriever,
    StructuredRetriever,
)
from .schemas import ExtractedSignals
from .signals import extract_signals

EXPERIMENT_ID = "neural-reranker-comparison-v1"
EXPERIMENT_DIRECTORY = Path("data/evaluation/neural-reranker-comparison-v1")
PROTOCOL_SCHEMA = "pvr-neural-reranker-protocol-v1"
PROTOCOL_MANIFEST_SCHEMA = "pvr-neural-reranker-protocol-manifest-v1"
POOL_SCHEMA = "pvr-neural-reranker-train-dev-pool-v1"
POOL_MANIFEST_SCHEMA = "pvr-neural-reranker-train-dev-pool-manifest-v1"
POINTWISE_MANIFEST_SCHEMA = "pvr-neural-pointwise-selection-v1"
LISTWISE_MANIFEST_SCHEMA = "pvr-neural-listwise-selection-v1"
RAW_SCHEMA = "pvr-neural-reranker-test-raw-v1"
RAW_MANIFEST_SCHEMA = "pvr-neural-reranker-test-raw-manifest-v1"
REPORT_SCHEMA = "pvr-neural-reranker-comparison-report-v1"
REPORT_MANIFEST_SCHEMA = "pvr-neural-reranker-comparison-report-manifest-v1"
REPORT_DIRECTORY = Path("reports/neural-reranker-comparison-v1")
CANDIDATE_LIMIT = 25
RRF_K = 60
RETRIEVAL_TIMING_NAMES = ("sparse", "dense", "structured", "fusion")
EXPECTED_TRAIN_DEV_COUNTS = {"train": 58, "dev": 21}
FROZEN_BENCHMARK_CONTRACT = {
    "total_count": 100,
    "split_counts": {"train": 58, "dev": 21, "test": 21},
    "status_counts": {
        "train": {"matched": 36, "ambiguous": 12, "no_match": 10},
        "dev": {"matched": 12, "ambiguous": 4, "no_match": 5},
        "test": {"matched": 12, "ambiguous": 4, "no_match": 5},
    },
    "hard_negative_counts": {"train": 34, "dev": 13, "test": 13},
    "matched_hard_negative_counts": {"train": 12, "dev": 4, "test": 4},
    "family_count": 14,
}
FreezeStatus = Literal["created", "unchanged"]


class CandidatePoolRetriever(Protocol):
    def retrieve_with_timings(
        self,
        signals: ExtractedSignals,
        limit: int,
    ) -> tuple[list[Candidate], dict[str, float]]: ...


class PointwiseScorer(Protocol):
    version: str

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[float, ...]: ...


class ListwiseTrainer(Protocol):
    def __call__(
        self,
        train_examples: Sequence[ListwiseExample],
        dev_examples: Sequence[ListwiseExample],
    ) -> ListwiseTrainingResult: ...


class ListwiseScorer(Protocol):
    version: str

    def score_set(self, features: Sequence[Sequence[float]]) -> tuple[float, ...]: ...


class ListwiseCheckpointBackend(Protocol):
    def save(
        self,
        checkpoint_path: Path,
        result: ListwiseTrainingResult,
    ) -> Mapping[str, object]: ...

    def validate(
        self,
        checkpoint_path: Path,
        manifest: Mapping[str, object],
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class ProtocolSourcePaths:
    config: Path
    benchmark: Path
    catalog: Path
    implementation_files: tuple[tuple[str, Path], ...]

    def __post_init__(self) -> None:
        labels = [label for label, _path in self.implementation_files]
        if len(labels) != len(set(labels)) or any(not label.strip() for label in labels):
            raise ValueError("protocol implementation source labels must be unique and nonblank")


@dataclass(frozen=True, slots=True)
class PointwiseModelBinding:
    model_id: str
    revision: str
    license: str
    manifest_sha256: str

    def __post_init__(self) -> None:
        if (
            self.model_id != POINTWISE_MODEL_ID
            or self.revision != POINTWISE_REVISION
            or self.license != POINTWISE_LICENSE
        ):
            raise ValueError("pointwise model binding differs from the approved v1 model")
        _require_sha256(self.manifest_sha256, "pointwise model manifest")


@dataclass(frozen=True, slots=True)
class TrainDevLabel:
    case_id: str
    split: Literal["train", "dev"]
    expected_status: str
    expected_canonical_uuid: str | None

    def __post_init__(self) -> None:
        if not self.case_id.strip() or self.expected_status not in {
            "matched",
            "ambiguous",
            "no_match",
        }:
            raise ValueError("Train/Dev label is invalid")
        if (self.expected_status == "matched") != (self.expected_canonical_uuid is not None):
            raise ValueError("matched Train/Dev labels require exactly one target UUID")


@dataclass(frozen=True, slots=True)
class EligibilitySummary:
    total_cases: int
    matched_cases: int
    eligible_cases: int
    retrieval_misses: int
    excluded_non_matched: int


class CoreListwiseCheckpointBackend:
    """Adapt the core safetensors contract to the experiment's three-file model layout."""

    def save(
        self,
        checkpoint_path: Path,
        result: ListwiseTrainingResult,
    ) -> Mapping[str, object]:
        generated_manifest = save_listwise_checkpoint(checkpoint_path, result)
        payload = _read_object(generated_manifest, "generated listwise checkpoint manifest")
        generated_manifest.unlink()
        return payload

    def validate(
        self,
        checkpoint_path: Path,
        manifest: Mapping[str, object],
    ) -> None:
        with tempfile.TemporaryDirectory(prefix="pvr-listwise-check-") as temporary_name:
            temporary = Path(temporary_name)
            copied_checkpoint = temporary / "listwise-model.safetensors"
            shutil.copyfile(checkpoint_path, copied_checkpoint)
            copied_checkpoint.with_suffix(".manifest.json").write_bytes(
                canonical_json_bytes(manifest)
            )
            validate_listwise_checkpoint(copied_checkpoint)


def default_protocol_sources(root: Path) -> ProtocolSourcePaths:
    return ProtocolSourcePaths(
        config=root / "config/neural-reranker-comparison-v1.json",
        benchmark=root / "data/benchmark.json",
        catalog=root / "data/catalog.json",
        implementation_files=(
            (
                "src/product_variant_resolver/neural_reranking.py",
                root / "src/product_variant_resolver/neural_reranking.py",
            ),
            (
                "src/product_variant_resolver/neural_reranker_comparison.py",
                root / "src/product_variant_resolver/neural_reranker_comparison.py",
            ),
        ),
    )


def build_offline_canonical_retriever(
    catalog: Catalog,
    *,
    dense_dimensions: int = 192,
) -> CandidateRetrievalService:
    """Build the existing sparse+dense+structured→RRF path without runtime policy layers."""

    structured = StructuredRetriever(catalog)
    return CandidateRetrievalService(
        [
            SparseRetriever(catalog),
            DenseRetriever(catalog, HashingEmbedding(dense_dimensions)),
            cast(Retriever, structured),
        ],
        structured,
    )


def _require_sha256(value: str, name: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")


def _read_object(path: Path, name: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {name}: {path}") from error
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a JSON object")
    return cast(dict[str, Any], value)


def _source_hashes(sources: ProtocolSourcePaths) -> dict[str, str]:
    files = (
        ("config/neural-reranker-comparison-v1.json", sources.config),
        ("data/benchmark.json", sources.benchmark),
        ("data/catalog.json", sources.catalog),
        *sources.implementation_files,
    )
    labels = [label for label, _path in files]
    if len(labels) != len(set(labels)):
        raise ValueError("protocol source labels collide")
    hashes: dict[str, str] = {}
    for label, path in files:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"protocol source is missing or unsafe: {label}")
        hashes[label] = sha256_path(path)
    return hashes


def _dependency_payload(dependencies: Sequence[tuple[str, str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for name, version in dependencies:
        if not name.strip() or not version.strip() or name in result:
            raise ValueError("protocol dependencies must be unique nonblank name/version pairs")
        result[name] = version
    if not result:
        raise ValueError("protocol requires dependency bindings")
    return dict(sorted(result.items()))


def build_protocol_payload(
    sources: ProtocolSourcePaths,
    model_binding: PointwiseModelBinding,
    dependencies: Sequence[tuple[str, str]],
) -> tuple[dict[str, object], Catalog, dict[str, Any]]:
    config = load_pointwise_model_config(sources.config)
    benchmark = _read_object(sources.benchmark, "benchmark")
    contract = validate_benchmark_contract(benchmark)
    catalog = load_catalog(sources.catalog)
    source_hashes = _source_hashes(sources)
    payload: dict[str, object] = {
        "schema_version": PROTOCOL_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "status": "frozen_pre_test",
        "candidate_limit": CANDIDATE_LIMIT,
        "rrf_k": RRF_K,
        "retrieval": {
            "path": "canonical_sparse_dense_structured_rrf",
            "sparse_version": "token-index-v1",
            "dense_version": "hashing-v1",
            "dense_dimensions": 192,
            "structured_version": "structured-features-v1",
            "timing_names": list(RETRIEVAL_TIMING_NAMES),
            "reranker_enabled": False,
        },
        "benchmark_contract": {
            "total_count": contract.total_count,
            "split_counts": dict(contract.split_counts),
            "status_counts": {split: dict(counts) for split, counts in contract.status_counts},
            "hard_negative_counts": dict(contract.hard_negative_counts),
            "matched_hard_negative_counts": dict(contract.matched_hard_negative_counts),
            "family_count": contract.family_count,
        },
        "train_dev_contract": {
            "split_counts": EXPECTED_TRAIN_DEV_COUNTS,
            "case_count": sum(EXPECTED_TRAIN_DEV_COUNTS.values()),
            "label_blind": True,
        },
        "catalog": {
            "version": catalog.version,
            "product_count": len(catalog.products),
            "semantic_checksum": catalog_checksum(catalog),
        },
        "pointwise_model": {
            "model_id": model_binding.model_id,
            "revision": model_binding.revision,
            "license": model_binding.license,
            "manifest_sha256": model_binding.manifest_sha256,
            "config_sha256": config.config_sha256,
        },
        "dependencies": _dependency_payload(dependencies),
        "source_sha256": source_hashes,
        "test_collection_executed": False,
        "training_executed": False,
    }
    return payload, catalog, benchmark


def _freeze_signals(signals: ExtractedSignals) -> FrozenSignals:
    return FrozenSignals(
        normalized_title=signals.normalized_title,
        tokens=tuple(signals.tokens),
        year=signals.year,
        collector_number=signals.collector_number,
        series_position=signals.series_position,
        quantity=signals.quantity,
        multipack_hint=signals.multipack_hint,
        color_hints=tuple(signals.color_hints),
        series_hints=tuple(signals.series_hints),
        parse_warnings=tuple(signals.parse_warnings),
    )


def _ordered_evidence(values: Sequence[str]) -> tuple[str, ...]:
    value_set = set(values)
    if len(value_set) != len(values) or value_set - set(STRUCTURED_NAMES):
        raise ValueError("retrieval candidate contains invalid structured evidence")
    return tuple(name for name in STRUCTURED_NAMES if name in value_set)


def freeze_candidate(candidate: Candidate) -> FrozenCandidate:
    if candidate.rrf_rank is None:
        raise ValueError("retrieval candidate is missing its RRF rank")
    if (
        not isinstance(candidate.rrf_rank, int)
        or isinstance(candidate.rrf_rank, bool)
        or not 1 <= candidate.rrf_rank <= CANDIDATE_LIMIT
    ):
        raise ValueError("retrieval candidate RRF rank is invalid")
    if (
        not isinstance(candidate.rrf_score, (int, float))
        or isinstance(candidate.rrf_score, bool)
        or not math.isfinite(float(candidate.rrf_score))
    ):
        raise ValueError("retrieval candidate RRF score is invalid")
    rank_names = set(candidate.source_ranks)
    score_names = set(candidate.source_scores)
    if not rank_names or rank_names != score_names or rank_names - set(SOURCE_NAMES):
        raise ValueError("retrieval candidate source ranks/scores are incomplete")
    if any(
        not isinstance(rank, int) or isinstance(rank, bool) or not 1 <= rank <= CANDIDATE_LIMIT
        for rank in candidate.source_ranks.values()
    ):
        raise ValueError("retrieval candidate source rank is invalid")
    if any(
        not isinstance(score, (int, float))
        or isinstance(score, bool)
        or not math.isfinite(float(score))
        for score in candidate.source_scores.values()
    ):
        raise ValueError("retrieval candidate source score is invalid")
    expected_rrf_score = sum(1.0 / (RRF_K + rank) for rank in candidate.source_ranks.values())
    if not math.isclose(candidate.rrf_score, expected_rrf_score, rel_tol=0.0, abs_tol=1e-15):
        raise ValueError("retrieval candidate RRF score differs from its source ranks")
    product = candidate.product
    view = product.product
    return FrozenCandidate(
        canonical_uuid=str(product.canonical_uuid),
        canonical_id=product.canonical_id,
        text=CandidateTextFields(
            brand=view.brand,
            casting=view.casting,
            release_year=view.release_year,
            series=view.series,
            color=view.color,
            collector_number=view.collector_number,
            series_position=view.series_position,
            edition=view.edition,
            aliases=tuple(product.aliases),
            identifiers=tuple(product.identifiers),
        ),
        source_ranks=tuple(
            (name, candidate.source_ranks[name]) for name in SOURCE_NAMES if name in rank_names
        ),
        source_scores=tuple(
            (name, candidate.source_scores[name]) for name in SOURCE_NAMES if name in score_names
        ),
        structured_matches=_ordered_evidence(candidate.matches),
        structured_conflicts=_ordered_evidence(candidate.conflicts),
        rrf_rank=candidate.rrf_rank,
        rrf_score=candidate.rrf_score,
    )


def _validate_timings(timings: Mapping[str, float]) -> tuple[tuple[str, float], ...]:
    if set(timings) != set(RETRIEVAL_TIMING_NAMES):
        raise ValueError("retrieval timings must contain sparse, dense, structured and fusion")
    result: list[tuple[str, float]] = []
    for name in RETRIEVAL_TIMING_NAMES:
        value = float(timings[name])
        if not math.isfinite(value) or value < 0:
            raise ValueError("retrieval timing must be finite and nonnegative")
        result.append((name, value))
    return tuple(result)


def collect_train_dev_pool(
    benchmark: Mapping[str, object],
    catalog: Catalog,
    retriever: CandidatePoolRetriever,
) -> tuple[CandidatePoolRow, ...]:
    validate_benchmark_contract(benchmark)
    cases_value = benchmark.get("cases")
    if not isinstance(cases_value, list):  # pragma: no cover - validator owns this path
        raise TypeError("benchmark requires cases[]")
    colors = frozenset(
        item.product.color for item in catalog.products if item.product.color is not None
    )
    series = frozenset(
        item.product.series for item in catalog.products if item.product.series is not None
    )
    rows: list[CandidatePoolRow] = []
    seen: set[str] = set()
    split_counts = {"train": 0, "dev": 0}
    for raw in cases_value:
        if not isinstance(raw, Mapping):  # pragma: no cover - validator owns this path
            raise TypeError("benchmark case must be an object")
        split = raw.get("split")
        if split == "test":
            continue
        if split not in split_counts:
            raise ValueError("candidate pool may only contain train/dev cases")
        case_id = raw.get("case_id")
        query = raw.get("query")
        if not isinstance(case_id, str) or not isinstance(query, str):
            raise TypeError("benchmark train/dev case requires case_id and query")
        if case_id in seen:
            raise ValueError("candidate pool contains a duplicate case_id")
        seen.add(case_id)
        signals = extract_signals(query, colors, series)
        candidates, timings = retriever.retrieve_with_timings(signals, CANDIDATE_LIMIT)
        frozen_candidates = tuple(freeze_candidate(candidate) for candidate in candidates)
        row = CandidatePoolRow(
            case_id=case_id,
            split=cast(Literal["train", "dev"], split),
            query=query,
            signals=_freeze_signals(signals),
            retrieval_timings_ms=_validate_timings(timings),
            candidates=frozen_candidates,
        )
        rows.append(row)
        split_counts[split] += 1
    if split_counts != EXPECTED_TRAIN_DEV_COUNTS or len(rows) != 79:
        raise ValueError("candidate pool train/dev denominators differ from the frozen contract")
    return tuple(rows)


def _signals_payload(signals: FrozenSignals) -> dict[str, object]:
    return {
        "normalized_title": signals.normalized_title,
        "tokens": list(signals.tokens),
        "year": signals.year,
        "collector_number": signals.collector_number,
        "series_position": signals.series_position,
        "quantity": signals.quantity,
        "multipack_hint": signals.multipack_hint,
        "color_hints": list(signals.color_hints),
        "series_hints": list(signals.series_hints),
        "parse_warnings": list(signals.parse_warnings),
    }


def _candidate_payload(candidate: FrozenCandidate) -> dict[str, object]:
    return {
        "canonical_uuid": candidate.canonical_uuid,
        "canonical_id": candidate.canonical_id,
        "text": {
            "brand": candidate.text.brand,
            "casting": candidate.text.casting,
            "release_year": candidate.text.release_year,
            "series": candidate.text.series,
            "color": candidate.text.color,
            "collector_number": candidate.text.collector_number,
            "series_position": candidate.text.series_position,
            "edition": candidate.text.edition,
            "aliases": list(candidate.text.aliases),
            "identifiers": list(candidate.text.identifiers),
        },
        "source_ranks": dict(candidate.source_ranks),
        "source_scores": dict(candidate.source_scores),
        "structured_matches": list(candidate.structured_matches),
        "structured_conflicts": list(candidate.structured_conflicts),
        "rrf_rank": candidate.rrf_rank,
        "rrf_score": candidate.rrf_score,
    }


def candidate_pool_payload(
    rows: Sequence[CandidatePoolRow],
    protocol_sha256: str,
) -> dict[str, object]:
    _require_sha256(protocol_sha256, "protocol")
    split_counts = {split: sum(row.split == split for row in rows) for split in ("train", "dev")}
    payload: dict[str, object] = {
        "schema_version": POOL_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "protocol_sha256": protocol_sha256,
        "case_count": len(rows),
        "split_counts": split_counts,
        "candidate_limit": CANDIDATE_LIMIT,
        "rows": [
            {
                "case_id": row.case_id,
                "split": row.split,
                "query": row.query,
                "signals": _signals_payload(row.signals),
                "retrieval_timings_ms": dict(row.retrieval_timings_ms),
                "candidates": [_candidate_payload(candidate) for candidate in row.candidates],
            }
            for row in rows
        ],
    }
    validate_candidate_pool_document(payload)
    return payload


def _require_exact_keys(value: Mapping[str, object], expected: set[str], name: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{name} keys differ from the frozen schema")


def _string_tuple(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise TypeError(f"{name} must be a string array")
    return tuple(cast(list[str], value))


def _optional_string(value: object, name: str) -> str | None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"{name} must be a string or null")
    return value


def _parse_frozen_candidate(value: object) -> FrozenCandidate:
    if not isinstance(value, Mapping):
        raise TypeError("candidate pool candidate must be an object")
    row = cast(Mapping[str, object], value)
    _require_exact_keys(
        row,
        {
            "canonical_uuid",
            "canonical_id",
            "text",
            "source_ranks",
            "source_scores",
            "structured_matches",
            "structured_conflicts",
            "rrf_rank",
            "rrf_score",
        },
        "candidate",
    )
    text_value = row["text"]
    ranks_value = row["source_ranks"]
    scores_value = row["source_scores"]
    if not isinstance(text_value, Mapping):
        raise TypeError("candidate text must be an object")
    text = cast(Mapping[str, object], text_value)
    _require_exact_keys(
        text,
        {
            "brand",
            "casting",
            "release_year",
            "series",
            "color",
            "collector_number",
            "series_position",
            "edition",
            "aliases",
            "identifiers",
        },
        "candidate text",
    )
    if not isinstance(ranks_value, Mapping) or not isinstance(scores_value, Mapping):
        raise TypeError("candidate source ranks/scores must be objects")
    ranks = cast(Mapping[str, object], ranks_value)
    scores = cast(Mapping[str, object], scores_value)
    if not ranks or set(ranks) != set(scores) or set(ranks) - set(SOURCE_NAMES):
        raise ValueError("candidate source ranks/scores differ")
    if any(
        not isinstance(rank, int) or isinstance(rank, bool) or not 1 <= rank <= CANDIDATE_LIMIT
        for rank in ranks.values()
    ):
        raise TypeError("candidate source rank must be an integer between 1 and 25")
    if any(
        not isinstance(score, (int, float))
        or isinstance(score, bool)
        or not math.isfinite(float(score))
        for score in scores.values()
    ):
        raise TypeError("candidate source score must be finite numeric")
    canonical_uuid = row["canonical_uuid"]
    canonical_id = row["canonical_id"]
    brand = text["brand"]
    casting_name = text["casting"]
    if not all(
        isinstance(item, str) for item in (canonical_uuid, canonical_id, brand, casting_name)
    ):
        raise TypeError("candidate identity and required text fields must be strings")
    release_year = text["release_year"]
    if release_year is not None and (
        not isinstance(release_year, int) or isinstance(release_year, bool)
    ):
        raise TypeError("candidate release_year must be an integer or null")
    rrf_rank = row["rrf_rank"]
    rrf_score = row["rrf_score"]
    if not isinstance(rrf_rank, int) or isinstance(rrf_rank, bool):
        raise TypeError("candidate rrf_rank must be an integer")
    if not isinstance(rrf_score, (int, float)) or isinstance(rrf_score, bool):
        raise TypeError("candidate rrf_score must be numeric")
    expected_rrf_score = sum(1.0 / (RRF_K + cast(int, rank)) for rank in ranks.values())
    if not math.isclose(float(rrf_score), expected_rrf_score, rel_tol=0.0, abs_tol=1e-15):
        raise ValueError("candidate RRF score differs from its source ranks")
    return FrozenCandidate(
        canonical_uuid=cast(str, canonical_uuid),
        canonical_id=cast(str, canonical_id),
        text=CandidateTextFields(
            brand=cast(str, brand),
            casting=cast(str, casting_name),
            release_year=release_year,
            series=_optional_string(text["series"], "candidate series"),
            color=_optional_string(text["color"], "candidate color"),
            collector_number=_optional_string(
                text["collector_number"], "candidate collector_number"
            ),
            series_position=_optional_string(text["series_position"], "candidate series_position"),
            edition=_optional_string(text["edition"], "candidate edition"),
            aliases=_string_tuple(text["aliases"], "candidate aliases"),
            identifiers=_string_tuple(text["identifiers"], "candidate identifiers"),
        ),
        source_ranks=tuple(
            (name, int(cast(Any, ranks[name]))) for name in SOURCE_NAMES if name in ranks
        ),
        source_scores=tuple(
            (name, float(cast(Any, scores[name]))) for name in SOURCE_NAMES if name in scores
        ),
        structured_matches=_string_tuple(row["structured_matches"], "candidate structured_matches"),
        structured_conflicts=_string_tuple(
            row["structured_conflicts"], "candidate structured_conflicts"
        ),
        rrf_rank=rrf_rank,
        rrf_score=float(rrf_score),
    )


def _parse_signals(value: object) -> FrozenSignals:
    if not isinstance(value, Mapping):
        raise TypeError("candidate pool signals must be an object")
    row = cast(Mapping[str, object], value)
    _require_exact_keys(
        row,
        {
            "normalized_title",
            "tokens",
            "year",
            "collector_number",
            "series_position",
            "quantity",
            "multipack_hint",
            "color_hints",
            "series_hints",
            "parse_warnings",
        },
        "signals",
    )
    normalized_title = row["normalized_title"]
    year = row["year"]
    quantity = row["quantity"]
    multipack_hint = row["multipack_hint"]
    if not isinstance(normalized_title, str) or not isinstance(multipack_hint, bool):
        raise TypeError("candidate pool signal scalar types are invalid")
    for name, value_item in (("year", year), ("quantity", quantity)):
        if value_item is not None and (
            not isinstance(value_item, int) or isinstance(value_item, bool)
        ):
            raise TypeError(f"candidate pool signal {name} must be integer or null")
    return FrozenSignals(
        normalized_title=normalized_title,
        tokens=_string_tuple(row["tokens"], "signal tokens"),
        year=cast(int | None, year),
        collector_number=_optional_string(row["collector_number"], "signal collector_number"),
        series_position=_optional_string(row["series_position"], "signal series_position"),
        quantity=cast(int | None, quantity),
        multipack_hint=multipack_hint,
        color_hints=_string_tuple(row["color_hints"], "signal color_hints"),
        series_hints=_string_tuple(row["series_hints"], "signal series_hints"),
        parse_warnings=_string_tuple(row["parse_warnings"], "signal parse_warnings"),
    )


def validate_candidate_pool_document(payload: Mapping[str, object]) -> tuple[CandidatePoolRow, ...]:
    validate_candidate_pool_payload(payload)
    _require_exact_keys(
        payload,
        {
            "schema_version",
            "experiment_id",
            "protocol_sha256",
            "case_count",
            "split_counts",
            "candidate_limit",
            "rows",
        },
        "candidate pool",
    )
    if (
        payload["schema_version"] != POOL_SCHEMA
        or payload["experiment_id"] != EXPERIMENT_ID
        or payload["candidate_limit"] != CANDIDATE_LIMIT
        or payload["split_counts"] != EXPECTED_TRAIN_DEV_COUNTS
        or payload["case_count"] != 79
    ):
        raise ValueError("candidate pool header differs from the frozen contract")
    protocol_sha = payload["protocol_sha256"]
    if not isinstance(protocol_sha, str):
        raise TypeError("candidate pool protocol_sha256 must be a string")
    _require_sha256(protocol_sha, "candidate pool protocol")
    rows_value = payload["rows"]
    if not isinstance(rows_value, list) or len(rows_value) != 79:
        raise ValueError("candidate pool must contain exactly 79 train/dev rows")
    rows: list[CandidatePoolRow] = []
    seen: set[str] = set()
    for value in rows_value:
        if not isinstance(value, Mapping):
            raise TypeError("candidate pool row must be an object")
        row = cast(Mapping[str, object], value)
        _require_exact_keys(
            row,
            {
                "case_id",
                "split",
                "query",
                "signals",
                "retrieval_timings_ms",
                "candidates",
            },
            "candidate pool row",
        )
        case_id = row["case_id"]
        split = row["split"]
        query = row["query"]
        timings_value = row["retrieval_timings_ms"]
        candidates_value = row["candidates"]
        if (
            not isinstance(case_id, str)
            or not isinstance(query, str)
            or split not in EXPECTED_TRAIN_DEV_COUNTS
            or not isinstance(timings_value, Mapping)
            or not isinstance(candidates_value, list)
        ):
            raise TypeError("candidate pool row scalar/collection types are invalid")
        if case_id in seen:
            raise ValueError("candidate pool contains duplicate case_id")
        seen.add(case_id)
        timings_mapping = cast(Mapping[str, object], timings_value)
        if any(
            not isinstance(value_item, (int, float)) or isinstance(value_item, bool)
            for value_item in timings_mapping.values()
        ):
            raise TypeError("candidate pool timing must be numeric")
        timings = _validate_timings(
            {name: float(cast(Any, value_item)) for name, value_item in timings_mapping.items()}
        )
        rows.append(
            CandidatePoolRow(
                case_id=case_id,
                split=cast(Literal["train", "dev"], split),
                query=query,
                signals=_parse_signals(row["signals"]),
                retrieval_timings_ms=timings,
                candidates=tuple(
                    _parse_frozen_candidate(candidate) for candidate in candidates_value
                ),
            )
        )
    counts = {split: sum(row.split == split for row in rows) for split in ("train", "dev")}
    if counts != EXPECTED_TRAIN_DEV_COUNTS:
        raise ValueError("candidate pool row split counts differ from header")
    return tuple(rows)


def _validate_pool_projection(
    rows: Sequence[CandidatePoolRow],
    benchmark: Mapping[str, object],
) -> None:
    cases = benchmark.get("cases")
    if not isinstance(cases, list):  # pragma: no cover - benchmark validator owns this path
        raise TypeError("benchmark requires cases[]")
    expected: list[tuple[str, str, str]] = []
    for raw in cases:
        if not isinstance(raw, Mapping):  # pragma: no cover - validator owns this path
            raise TypeError("benchmark case must be an object")
        split = raw.get("split")
        if split == "test":
            continue
        case_id = raw.get("case_id")
        query = raw.get("query")
        if (
            split not in EXPECTED_TRAIN_DEV_COUNTS
            or not isinstance(case_id, str)
            or not isinstance(query, str)
        ):
            raise ValueError("benchmark Train/Dev projection is invalid")
        expected.append((case_id, split, query))
    actual = [(row.case_id, row.split, row.query) for row in rows]
    if actual != expected:
        raise ValueError("candidate pool differs from the ordered Train/Dev benchmark projection")


def _protocol_manifest(protocol_bytes: bytes, protocol: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema_version": PROTOCOL_MANIFEST_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "protocol_sha256": sha256_bytes(protocol_bytes),
        "source_sha256": protocol["source_sha256"],
        "test_collection_executed": False,
        "training_executed": False,
    }


def _pool_manifest(pool_bytes: bytes, protocol_sha256: str) -> dict[str, object]:
    return {
        "schema_version": POOL_MANIFEST_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "pool_sha256": sha256_bytes(pool_bytes),
        "protocol_sha256": protocol_sha256,
        "case_count": 79,
        "split_counts": EXPECTED_TRAIN_DEV_COUNTS,
        "retrieval_call_count": 79,
        "retrieval_error_count": 0,
        "label_blind": True,
        "test_collection_executed": False,
    }


def _artifact_bytes(
    sources: ProtocolSourcePaths,
    model_binding: PointwiseModelBinding,
    dependencies: Sequence[tuple[str, str]],
    retriever: CandidatePoolRetriever,
) -> dict[Path, bytes]:
    protocol, catalog, benchmark = build_protocol_payload(sources, model_binding, dependencies)
    protocol_bytes = canonical_json_bytes(protocol)
    protocol_sha = sha256_bytes(protocol_bytes)
    rows = collect_train_dev_pool(benchmark, catalog, retriever)
    pool = candidate_pool_payload(rows, protocol_sha)
    pool_bytes = canonical_json_bytes(pool)
    return {
        Path("protocol/protocol.json"): protocol_bytes,
        Path("protocol/protocol-manifest.json"): canonical_json_bytes(
            _protocol_manifest(protocol_bytes, protocol)
        ),
        Path("pool/train-dev-candidate-pool.json"): pool_bytes,
        Path("pool/train-dev-candidate-pool-manifest.json"): canonical_json_bytes(
            _pool_manifest(pool_bytes, protocol_sha)
        ),
    }


def _require_artifact_layout(directory: Path) -> None:
    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("neural reranker experiment directory is missing or unsafe")
    allowed_children = {"protocol", "pool", "models", "raw"}
    children = {item.name for item in directory.iterdir()}
    if not {"protocol", "pool"}.issubset(children) or children - allowed_children:
        raise ValueError("neural reranker experiment directory is partial or conflicting")
    expected = {
        "protocol": {"protocol.json", "protocol-manifest.json"},
        "pool": {"train-dev-candidate-pool.json", "train-dev-candidate-pool-manifest.json"},
    }
    for child, names in expected.items():
        child_path = directory / child
        if (
            not child_path.is_dir()
            or child_path.is_symlink()
            or {item.name for item in child_path.iterdir()} != names
            or any(item.is_symlink() for item in child_path.iterdir())
        ):
            raise ValueError(f"neural reranker {child} directory is partial or unsafe")


def check_frozen_train_dev(
    root: Path,
    sources: ProtocolSourcePaths,
    model_binding: PointwiseModelBinding,
    dependencies: Sequence[tuple[str, str]],
) -> tuple[CandidatePoolRow, ...]:
    directory = root / EXPERIMENT_DIRECTORY
    _require_artifact_layout(directory)
    expected_protocol, _catalog, benchmark = build_protocol_payload(
        sources, model_binding, dependencies
    )
    protocol_path = directory / "protocol/protocol.json"
    protocol_manifest_path = directory / "protocol/protocol-manifest.json"
    pool_path = directory / "pool/train-dev-candidate-pool.json"
    pool_manifest_path = directory / "pool/train-dev-candidate-pool-manifest.json"
    protocol = _read_object(protocol_path, "frozen protocol")
    if protocol != expected_protocol:
        raise ValueError("frozen protocol differs from current bound sources")
    protocol_bytes = canonical_json_bytes(protocol)
    if protocol_path.read_bytes() != protocol_bytes:
        raise ValueError("frozen protocol is not canonical JSON")
    expected_protocol_manifest = _protocol_manifest(protocol_bytes, protocol)
    protocol_manifest = _read_object(protocol_manifest_path, "protocol manifest")
    if (
        protocol_manifest != expected_protocol_manifest
        or protocol_manifest_path.read_bytes() != canonical_json_bytes(protocol_manifest)
    ):
        raise ValueError("protocol manifest differs from frozen protocol")
    pool = _read_object(pool_path, "train/dev candidate pool")
    rows = validate_candidate_pool_document(pool)
    _validate_pool_projection(rows, benchmark)
    protocol_sha = sha256_bytes(protocol_bytes)
    if pool.get("protocol_sha256") != protocol_sha:
        raise ValueError("candidate pool is bound to a different protocol")
    pool_bytes = canonical_json_bytes(pool)
    if pool_path.read_bytes() != pool_bytes:
        raise ValueError("candidate pool is not canonical JSON")
    expected_pool_manifest = _pool_manifest(pool_bytes, protocol_sha)
    pool_manifest = _read_object(pool_manifest_path, "candidate pool manifest")
    if (
        pool_manifest != expected_pool_manifest
        or pool_manifest_path.read_bytes() != canonical_json_bytes(pool_manifest)
    ):
        raise ValueError("candidate pool manifest differs from pool bytes")
    return rows


def freeze_protocol_and_train_dev_pool(
    root: Path,
    sources: ProtocolSourcePaths,
    model_binding: PointwiseModelBinding,
    dependencies: Sequence[tuple[str, str]],
    retriever: CandidatePoolRetriever,
) -> FreezeStatus:
    directory = root / EXPERIMENT_DIRECTORY
    if directory.exists():
        check_frozen_train_dev(root, sources, model_binding, dependencies)
        return "unchanged"
    outputs = _artifact_bytes(sources, model_binding, dependencies, retriever)
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{EXPERIMENT_ID}-", dir=directory.parent))
    try:
        for relative_path, content in outputs.items():
            destination = staging / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as handle:
                handle.write(content)
        _require_artifact_layout(staging)
        if directory.exists():
            raise FileExistsError("neural reranker experiment directory appeared during freeze")
        os.rename(staging, directory)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    check_frozen_train_dev(root, sources, model_binding, dependencies)
    return "created"


def _protocol_payload_without_benchmark_labels(
    sources: ProtocolSourcePaths,
    model_binding: PointwiseModelBinding,
    dependencies: Sequence[tuple[str, str]],
) -> dict[str, object]:
    """Reconstruct protocol bindings for fitting without parsing any benchmark label."""

    config = load_pointwise_model_config(sources.config)
    catalog = load_catalog(sources.catalog)
    return {
        "schema_version": PROTOCOL_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "status": "frozen_pre_test",
        "candidate_limit": CANDIDATE_LIMIT,
        "rrf_k": RRF_K,
        "retrieval": {
            "path": "canonical_sparse_dense_structured_rrf",
            "sparse_version": "token-index-v1",
            "dense_version": "hashing-v1",
            "dense_dimensions": 192,
            "structured_version": "structured-features-v1",
            "timing_names": list(RETRIEVAL_TIMING_NAMES),
            "reranker_enabled": False,
        },
        "benchmark_contract": FROZEN_BENCHMARK_CONTRACT,
        "train_dev_contract": {
            "split_counts": EXPECTED_TRAIN_DEV_COUNTS,
            "case_count": 79,
            "label_blind": True,
        },
        "catalog": {
            "version": catalog.version,
            "product_count": len(catalog.products),
            "semantic_checksum": catalog_checksum(catalog),
        },
        "pointwise_model": {
            "model_id": model_binding.model_id,
            "revision": model_binding.revision,
            "license": model_binding.license,
            "manifest_sha256": model_binding.manifest_sha256,
            "config_sha256": config.config_sha256,
        },
        "dependencies": _dependency_payload(dependencies),
        "source_sha256": _source_hashes(sources),
        "test_collection_executed": False,
        "training_executed": False,
    }


def _check_frozen_train_dev_for_fit(
    root: Path,
    sources: ProtocolSourcePaths,
    model_binding: PointwiseModelBinding,
    dependencies: Sequence[tuple[str, str]],
) -> tuple[CandidatePoolRow, ...]:
    """Validate the frozen phase by bytes/contracts, without invoking the Test-label validator."""

    directory = root / EXPERIMENT_DIRECTORY
    _require_artifact_layout(directory)
    expected_protocol = _protocol_payload_without_benchmark_labels(
        sources, model_binding, dependencies
    )
    protocol_path = directory / "protocol/protocol.json"
    protocol_manifest_path = directory / "protocol/protocol-manifest.json"
    pool_path = directory / "pool/train-dev-candidate-pool.json"
    pool_manifest_path = directory / "pool/train-dev-candidate-pool-manifest.json"
    protocol = _read_object(protocol_path, "frozen protocol")
    if protocol != expected_protocol:
        raise ValueError("frozen protocol differs from current bound sources")
    protocol_bytes = canonical_json_bytes(protocol)
    if protocol_path.read_bytes() != protocol_bytes:
        raise ValueError("frozen protocol is not canonical JSON")
    protocol_manifest = _read_object(protocol_manifest_path, "protocol manifest")
    if protocol_manifest != _protocol_manifest(
        protocol_bytes, protocol
    ) or protocol_manifest_path.read_bytes() != canonical_json_bytes(protocol_manifest):
        raise ValueError("protocol manifest differs from frozen protocol")
    pool = _read_object(pool_path, "train/dev candidate pool")
    rows = validate_candidate_pool_document(pool)
    protocol_sha = sha256_bytes(protocol_bytes)
    if pool.get("protocol_sha256") != protocol_sha:
        raise ValueError("candidate pool is bound to a different protocol")
    pool_bytes = canonical_json_bytes(pool)
    if pool_path.read_bytes() != pool_bytes:
        raise ValueError("candidate pool is not canonical JSON")
    pool_manifest = _read_object(pool_manifest_path, "candidate pool manifest")
    if pool_manifest != _pool_manifest(
        pool_bytes, protocol_sha
    ) or pool_manifest_path.read_bytes() != canonical_json_bytes(pool_manifest):
        raise ValueError("candidate pool manifest differs from pool bytes")
    return rows


def load_train_dev_labels(benchmark: Mapping[str, object]) -> tuple[TrainDevLabel, ...]:
    """Project only Train/Dev supervision; Test rows are skipped before label fields are read."""

    cases = benchmark.get("cases")
    if not isinstance(cases, list):
        raise TypeError("benchmark requires cases[]")
    labels: list[TrainDevLabel] = []
    split_counts = {"train": 0, "dev": 0}
    status_counts = {
        "train": {"matched": 0, "ambiguous": 0, "no_match": 0},
        "dev": {"matched": 0, "ambiguous": 0, "no_match": 0},
    }
    for raw in cases:
        if not isinstance(raw, Mapping):
            raise TypeError("benchmark case must be an object")
        split = raw.get("split")
        if split == "test":
            continue
        if split not in split_counts:
            raise ValueError("Train/Dev label projection contains an invalid split")
        case_id = raw.get("case_id")
        status = raw.get("expected_status")
        if not isinstance(case_id, str) or status not in status_counts[split]:
            raise ValueError("Train/Dev label projection contains an invalid case")
        target = raw.get("expected_canonical_uuid") if status == "matched" else None
        if status == "matched" and not isinstance(target, str):
            raise ValueError("matched Train/Dev case is missing its target UUID")
        labels.append(
            TrainDevLabel(
                case_id=case_id,
                split=cast(Literal["train", "dev"], split),
                expected_status=cast(str, status),
                expected_canonical_uuid=cast(str | None, target),
            )
        )
        split_counts[split] += 1
        status_counts[split][cast(str, status)] += 1
    if split_counts != EXPECTED_TRAIN_DEV_COUNTS or status_counts != {
        "train": {"matched": 36, "ambiguous": 12, "no_match": 10},
        "dev": {"matched": 12, "ambiguous": 4, "no_match": 5},
    }:
        raise ValueError("Train/Dev labels differ from the frozen benchmark contract")
    return tuple(labels)


def _experiment_input_hashes(root: Path) -> tuple[str, str]:
    directory = root / EXPERIMENT_DIRECTORY
    return (
        sha256_path(directory / "protocol/protocol.json"),
        sha256_path(directory / "pool/train-dev-candidate-pool.json"),
    )


def _reference_environment(dependencies: Sequence[tuple[str, str]]) -> dict[str, object]:
    resolved = _dependency_payload(dependencies)
    return {
        "device": "cpu",
        "dtype": "float32",
        "platform": "macOS ARM64 reference",
        "python": resolved.get("python", "unrecorded"),
    }


def _score_pointwise_rows(
    rows: Sequence[CandidatePoolRow],
    scorer: PointwiseScorer,
) -> tuple[dict[str, object], ...]:
    scored_rows: list[dict[str, object]] = []
    for row in rows:
        pairs = tuple(
            (row.query, render_candidate_text(candidate.text)) for candidate in row.candidates
        )
        scores = scorer.score_pairs(pairs)
        ranked = rank_scores(row.candidates, scores)
        ranks = {item.canonical_uuid: item.rank for item in ranked}
        scored_rows.append(
            {
                "case_id": row.case_id,
                "split": row.split,
                "candidates": [
                    {
                        "canonical_uuid": candidate.canonical_uuid,
                        "pointwise_logit": score,
                        "pointwise_rank": ranks[candidate.canonical_uuid],
                    }
                    for candidate, score in zip(row.candidates, scores, strict=True)
                ],
            }
        )
    return tuple(scored_rows)


def _pointwise_manifest_payload(
    rows: Sequence[CandidatePoolRow],
    scored_rows: Sequence[Mapping[str, object]],
    model_binding: PointwiseModelBinding,
    dependencies: Sequence[tuple[str, str]],
    protocol_sha256: str,
    pool_sha256: str,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": POINTWISE_MANIFEST_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "architecture": "cross-encoder",
        "model_id": model_binding.model_id,
        "revision": model_binding.revision,
        "license": model_binding.license,
        "model_manifest_sha256": model_binding.manifest_sha256,
        "protocol_sha256": protocol_sha256,
        "pool_sha256": pool_sha256,
        "input_schema": "query-plus-allowlisted-candidate-text-v1",
        "preprocessing_version": "candidate-text-v1",
        "frozen_weights": True,
        "score_tolerance": 1e-6,
        "dependencies": _dependency_payload(dependencies),
        "reference_environment": _reference_environment(dependencies),
        "case_count": len(rows),
        "split_counts": EXPECTED_TRAIN_DEV_COUNTS,
        "candidate_score_count": sum(len(row.candidates) for row in rows),
        "rows": [dict(item) for item in scored_rows],
        "test_labels_loaded": False,
        "test_scored": False,
    }
    validate_label_blind_payload(payload)
    return payload


def _validate_pointwise_manifest(
    payload: Mapping[str, object],
    rows: Sequence[CandidatePoolRow],
    model_binding: PointwiseModelBinding,
    dependencies: Sequence[tuple[str, str]],
    protocol_sha256: str,
    pool_sha256: str,
) -> tuple[tuple[float, ...], ...]:
    validate_label_blind_payload(payload)
    _require_exact_keys(
        payload,
        {
            "schema_version",
            "experiment_id",
            "architecture",
            "model_id",
            "revision",
            "license",
            "model_manifest_sha256",
            "protocol_sha256",
            "pool_sha256",
            "input_schema",
            "preprocessing_version",
            "frozen_weights",
            "score_tolerance",
            "dependencies",
            "reference_environment",
            "case_count",
            "split_counts",
            "candidate_score_count",
            "rows",
            "test_labels_loaded",
            "test_scored",
        },
        "pointwise manifest",
    )
    expected_header = {
        "schema_version": POINTWISE_MANIFEST_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "architecture": "cross-encoder",
        "model_id": model_binding.model_id,
        "revision": model_binding.revision,
        "license": model_binding.license,
        "model_manifest_sha256": model_binding.manifest_sha256,
        "protocol_sha256": protocol_sha256,
        "pool_sha256": pool_sha256,
        "input_schema": "query-plus-allowlisted-candidate-text-v1",
        "preprocessing_version": "candidate-text-v1",
        "frozen_weights": True,
        "score_tolerance": 1e-6,
        "dependencies": _dependency_payload(dependencies),
        "reference_environment": _reference_environment(dependencies),
        "case_count": 79,
        "split_counts": EXPECTED_TRAIN_DEV_COUNTS,
        "candidate_score_count": sum(len(row.candidates) for row in rows),
        "test_labels_loaded": False,
        "test_scored": False,
    }
    if any(payload.get(key) != value for key, value in expected_header.items()):
        raise ValueError("pointwise manifest header or binding drift")
    rows_value = payload["rows"]
    if not isinstance(rows_value, list) or len(rows_value) != len(rows):
        raise ValueError("pointwise manifest rows differ from the frozen pool")
    all_scores: list[tuple[float, ...]] = []
    for frozen_row, raw in zip(rows, rows_value, strict=True):
        if not isinstance(raw, Mapping):
            raise TypeError("pointwise manifest row must be an object")
        _require_exact_keys(raw, {"case_id", "split", "candidates"}, "pointwise row")
        candidates_value = raw["candidates"]
        if (
            raw["case_id"] != frozen_row.case_id
            or raw["split"] != frozen_row.split
            or not isinstance(candidates_value, list)
            or len(candidates_value) != len(frozen_row.candidates)
        ):
            raise ValueError("pointwise row differs from the frozen candidate pool")
        scores: list[float] = []
        declared_ranks: list[int] = []
        for candidate, scored in zip(frozen_row.candidates, candidates_value, strict=True):
            if not isinstance(scored, Mapping):
                raise TypeError("pointwise candidate score must be an object")
            _require_exact_keys(
                scored,
                {"canonical_uuid", "pointwise_logit", "pointwise_rank"},
                "pointwise candidate score",
            )
            score = scored["pointwise_logit"]
            rank = scored["pointwise_rank"]
            if (
                scored["canonical_uuid"] != candidate.canonical_uuid
                or not isinstance(score, (int, float))
                or isinstance(score, bool)
                or not math.isfinite(float(score))
                or not isinstance(rank, int)
                or isinstance(rank, bool)
            ):
                raise ValueError("pointwise candidate score is invalid or misaligned")
            scores.append(float(score))
            declared_ranks.append(rank)
        expected_ranks = {
            item.canonical_uuid: item.rank for item in rank_scores(frozen_row.candidates, scores)
        }
        if declared_ranks != [
            expected_ranks[candidate.canonical_uuid] for candidate in frozen_row.candidates
        ]:
            raise ValueError("pointwise candidate ranks differ from deterministic sorting")
        all_scores.append(tuple(scores))
    return tuple(all_scores)


def _label_checksum(labels: Sequence[TrainDevLabel]) -> str:
    return sha256_bytes(
        canonical_json_bytes(
            [
                {
                    "case_id": label.case_id,
                    "split": label.split,
                    "expected_status": label.expected_status,
                    "expected_canonical_uuid": label.expected_canonical_uuid,
                }
                for label in labels
            ]
        )
    )


def _eligibility_payload(value: EligibilitySummary) -> dict[str, int]:
    return {
        "total_cases": value.total_cases,
        "matched_cases": value.matched_cases,
        "eligible_cases": value.eligible_cases,
        "retrieval_misses": value.retrieval_misses,
        "excluded_non_matched": value.excluded_non_matched,
    }


def _build_listwise_examples(
    rows: Sequence[CandidatePoolRow],
    score_rows: Sequence[Sequence[float]],
    labels: Sequence[TrainDevLabel],
) -> tuple[
    tuple[ListwiseExample, ...],
    tuple[ListwiseExample, ...],
    dict[str, EligibilitySummary],
]:
    if len(rows) != len(score_rows) or len(rows) != len(labels):
        raise ValueError("Train/Dev pool, pointwise scores and labels differ in length")
    examples: dict[str, list[ListwiseExample]] = {"train": [], "dev": []}
    counters = {
        split: {
            "total_cases": 0,
            "matched_cases": 0,
            "eligible_cases": 0,
            "retrieval_misses": 0,
            "excluded_non_matched": 0,
        }
        for split in ("train", "dev")
    }
    for row, scores, label in zip(rows, score_rows, labels, strict=True):
        if row.case_id != label.case_id or row.split != label.split:
            raise ValueError("Train/Dev labels do not align with the frozen pool")
        counts = counters[row.split]
        counts["total_cases"] += 1
        if label.expected_status != "matched":
            counts["excluded_non_matched"] += 1
            continue
        counts["matched_cases"] += 1
        target_uuid = label.expected_canonical_uuid
        identities = [candidate.canonical_uuid for candidate in row.candidates]
        if target_uuid not in identities:
            counts["retrieval_misses"] += 1
            continue
        target_index = identities.index(target_uuid)
        features = tuple(
            candidate_feature_vector(candidate, score)
            for candidate, score in zip(row.candidates, scores, strict=True)
        )
        examples[row.split].append(ListwiseExample(features=features, target_index=target_index))
        counts["eligible_cases"] += 1
    summaries = {split: EligibilitySummary(**counters[split]) for split in ("train", "dev")}
    return tuple(examples["train"]), tuple(examples["dev"]), summaries


def _normalizer_payload_for_selection(normalizer: FeatureNormalizer) -> dict[str, object]:
    return {
        "feature_schema": list(normalizer.feature_schema),
        "normalized_indices": list(normalizer.normalized_indices),
        "means": list(normalizer.means),
        "standard_deviations": list(normalizer.standard_deviations),
        "fitted_split": normalizer.fitted_split,
    }


def _parse_selection_normalizer(value: object) -> FeatureNormalizer:
    if not isinstance(value, Mapping):
        raise TypeError("listwise selection normalizer must be an object")
    _require_exact_keys(
        value,
        {
            "feature_schema",
            "normalized_indices",
            "means",
            "standard_deviations",
            "fitted_split",
        },
        "listwise selection normalizer",
    )
    schema = value["feature_schema"]
    indices = value["normalized_indices"]
    means = value["means"]
    deviations = value["standard_deviations"]
    if not all(isinstance(item, list) for item in (schema, indices, means, deviations)):
        raise TypeError("listwise selection normalizer arrays are invalid")
    if any(not isinstance(item, str) for item in cast(list[object], schema)):
        raise TypeError("listwise selection feature schema is invalid")
    if any(
        not isinstance(item, int) or isinstance(item, bool) for item in cast(list[object], indices)
    ):
        raise TypeError("listwise selection normalized indices are invalid")
    if any(
        not isinstance(item, (int, float)) or isinstance(item, bool)
        for values in (means, deviations)
        for item in cast(list[object], values)
    ):
        raise TypeError("listwise selection statistics are invalid")
    fitted_split = value["fitted_split"]
    if not isinstance(fitted_split, str):
        raise TypeError("listwise selection fitted_split is invalid")
    return FeatureNormalizer(
        feature_schema=tuple(cast(list[str], schema)),
        normalized_indices=tuple(cast(list[int], indices)),
        means=tuple(float(item) for item in cast(list[int | float], means)),
        standard_deviations=tuple(float(item) for item in cast(list[int | float], deviations)),
        fitted_split=fitted_split,
    )


def _validate_training_result(
    result: ListwiseTrainingResult,
    train_examples: Sequence[ListwiseExample],
) -> None:
    expected_normalizer = fit_train_feature_normalizer(
        [row for example in train_examples for row in example.features]
    )
    if result.normalizer != expected_normalizer:
        raise ValueError("listwise normalizer was not fitted from eligible Train candidates only")
    selection = select_early_stopping_epoch(result.history)
    if result.selected_epoch != selection.selected_epoch or not math.isclose(
        result.selected_dev_mrr_at_10,
        selection.selected_dev_mrr_at_10,
        rel_tol=0.0,
        abs_tol=1e-15,
    ):
        raise ValueError("listwise selected epoch differs from deterministic Dev early stopping")


def _listwise_manifest_payload(
    result: ListwiseTrainingResult,
    checkpoint_manifest: Mapping[str, object],
    summaries: Mapping[str, EligibilitySummary],
    labels: Sequence[TrainDevLabel],
    dependencies: Sequence[tuple[str, str]],
    protocol_sha256: str,
    pool_sha256: str,
    pointwise_manifest_sha256: str,
) -> dict[str, object]:
    return {
        "schema_version": LISTWISE_MANIFEST_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "architecture": "candidate-set-reranker-v1",
        "architecture_parameters": {name: value for name, value in LISTWISE_ARCHITECTURE},
        "training_hyperparameters": {
            "optimizer": "AdamW",
            "learning_rate": LISTWISE_LEARNING_RATE,
            "weight_decay": LISTWISE_WEIGHT_DECAY,
            "batch_size": LISTWISE_BATCH_SIZE,
            "max_epochs": LISTWISE_MAX_EPOCHS,
            "patience": LISTWISE_PATIENCE,
            "loss": "masked_listwise_cross_entropy",
        },
        "seed": LISTWISE_SEED,
        "feature_schema": list(FEATURE_SCHEMA),
        "preprocessing_version": "candidate-features-v1",
        "dependencies": _dependency_payload(dependencies),
        "reference_environment": _reference_environment(dependencies),
        "protocol_sha256": protocol_sha256,
        "pool_sha256": pool_sha256,
        "pointwise_manifest_sha256": pointwise_manifest_sha256,
        "training_label_sha256": _label_checksum(labels),
        "eligibility": {
            split: _eligibility_payload(summaries[split]) for split in ("train", "dev")
        },
        "normalizer": _normalizer_payload_for_selection(result.normalizer),
        "selected_epoch": result.selected_epoch,
        "selected_dev_mrr_at_10": result.selected_dev_mrr_at_10,
        "history": [
            {
                "epoch": item.epoch,
                "train_loss": item.train_loss,
                "dev_mrr_at_10": item.dev_mrr_at_10,
            }
            for item in result.history
        ],
        "checkpoint": dict(checkpoint_manifest),
        "test_labels_loaded": False,
        "test_scored": False,
    }


def _require_models_layout(models: Path) -> None:
    expected = {
        "pointwise-manifest.json",
        "listwise-model.safetensors",
        "listwise-manifest.json",
    }
    if (
        not models.is_dir()
        or models.is_symlink()
        or {item.name for item in models.iterdir()} != expected
        or any(item.is_symlink() for item in models.iterdir())
    ):
        raise ValueError("neural reranker models directory is partial or unsafe")


def _validate_listwise_manifest(
    payload: Mapping[str, object],
    checkpoint_path: Path,
    backend: ListwiseCheckpointBackend,
    train_examples: Sequence[ListwiseExample],
    summaries: Mapping[str, EligibilitySummary],
    labels: Sequence[TrainDevLabel],
    dependencies: Sequence[tuple[str, str]],
    protocol_sha256: str,
    pool_sha256: str,
    pointwise_manifest_sha256: str,
) -> None:
    _require_exact_keys(
        payload,
        {
            "schema_version",
            "experiment_id",
            "architecture",
            "architecture_parameters",
            "training_hyperparameters",
            "seed",
            "feature_schema",
            "preprocessing_version",
            "dependencies",
            "reference_environment",
            "protocol_sha256",
            "pool_sha256",
            "pointwise_manifest_sha256",
            "training_label_sha256",
            "eligibility",
            "normalizer",
            "selected_epoch",
            "selected_dev_mrr_at_10",
            "history",
            "checkpoint",
            "test_labels_loaded",
            "test_scored",
        },
        "listwise manifest",
    )
    expected = {
        "schema_version": LISTWISE_MANIFEST_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "architecture": "candidate-set-reranker-v1",
        "architecture_parameters": {name: value for name, value in LISTWISE_ARCHITECTURE},
        "training_hyperparameters": {
            "optimizer": "AdamW",
            "learning_rate": LISTWISE_LEARNING_RATE,
            "weight_decay": LISTWISE_WEIGHT_DECAY,
            "batch_size": LISTWISE_BATCH_SIZE,
            "max_epochs": LISTWISE_MAX_EPOCHS,
            "patience": LISTWISE_PATIENCE,
            "loss": "masked_listwise_cross_entropy",
        },
        "seed": LISTWISE_SEED,
        "feature_schema": list(FEATURE_SCHEMA),
        "preprocessing_version": "candidate-features-v1",
        "dependencies": _dependency_payload(dependencies),
        "reference_environment": _reference_environment(dependencies),
        "protocol_sha256": protocol_sha256,
        "pool_sha256": pool_sha256,
        "pointwise_manifest_sha256": pointwise_manifest_sha256,
        "training_label_sha256": _label_checksum(labels),
        "eligibility": {
            split: _eligibility_payload(summaries[split]) for split in ("train", "dev")
        },
        "test_labels_loaded": False,
        "test_scored": False,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        raise ValueError("listwise manifest header, inputs or eligibility drift")
    history_value = payload["history"]
    if not isinstance(history_value, list):
        raise TypeError("listwise manifest history must be an array")
    history: list[TrainingEpoch] = []
    for raw in history_value:
        if not isinstance(raw, Mapping):
            raise TypeError("listwise history item must be an object")
        _require_exact_keys(raw, {"epoch", "train_loss", "dev_mrr_at_10"}, "history item")
        epoch = raw["epoch"]
        train_loss = raw["train_loss"]
        dev_mrr = raw["dev_mrr_at_10"]
        if (
            not isinstance(epoch, int)
            or isinstance(epoch, bool)
            or not isinstance(train_loss, (int, float))
            or isinstance(train_loss, bool)
            or not isinstance(dev_mrr, (int, float))
            or isinstance(dev_mrr, bool)
        ):
            raise TypeError("listwise history item types are invalid")
        history.append(
            TrainingEpoch(
                epoch=epoch,
                train_loss=float(train_loss),
                dev_mrr_at_10=float(dev_mrr),
            )
        )
    selection = select_early_stopping_epoch(history)
    if (
        payload["selected_epoch"] != selection.selected_epoch
        or payload["selected_dev_mrr_at_10"] != selection.selected_dev_mrr_at_10
    ):
        raise ValueError("listwise selected epoch differs from Dev history")
    expected_normalizer = fit_train_feature_normalizer(
        [row for example in train_examples for row in example.features]
    )
    if _parse_selection_normalizer(payload["normalizer"]) != expected_normalizer:
        raise ValueError("listwise normalizer differs from eligible Train candidates")
    checkpoint = payload["checkpoint"]
    if not isinstance(checkpoint, Mapping):
        raise TypeError("listwise checkpoint contract must be an object")
    checkpoint_sha = checkpoint.get("checkpoint_sha256")
    if not isinstance(checkpoint_sha, str) or checkpoint_sha != sha256_path(checkpoint_path):
        raise ValueError("listwise checkpoint hash drift")
    if checkpoint.get("selected_epoch") != selection.selected_epoch:
        raise ValueError("listwise checkpoint selected epoch drift")
    backend.validate(checkpoint_path, cast(Mapping[str, object], checkpoint))


def check_fitted_train_dev_models(
    root: Path,
    sources: ProtocolSourcePaths,
    model_binding: PointwiseModelBinding,
    dependencies: Sequence[tuple[str, str]],
    model_integrity_probe: Callable[[], str],
    checkpoint_backend: ListwiseCheckpointBackend,
) -> None:
    rows = _check_frozen_train_dev_for_fit(root, sources, model_binding, dependencies)
    if model_integrity_probe() != model_binding.manifest_sha256:
        raise ValueError("pointwise model bytes differ from the frozen manifest binding")
    models = root / EXPERIMENT_DIRECTORY / "models"
    _require_models_layout(models)
    protocol_sha, pool_sha = _experiment_input_hashes(root)
    pointwise_path = models / "pointwise-manifest.json"
    pointwise = _read_object(pointwise_path, "pointwise manifest")
    score_rows = _validate_pointwise_manifest(
        pointwise,
        rows,
        model_binding,
        dependencies,
        protocol_sha,
        pool_sha,
    )
    benchmark = _read_object(sources.benchmark, "benchmark")
    labels = load_train_dev_labels(benchmark)
    train_examples, _dev_examples, summaries = _build_listwise_examples(rows, score_rows, labels)
    listwise_path = models / "listwise-manifest.json"
    listwise = _read_object(listwise_path, "listwise manifest")
    if listwise_path.read_bytes() != canonical_json_bytes(listwise):
        raise ValueError("listwise manifest is not canonical JSON")
    _validate_listwise_manifest(
        listwise,
        models / "listwise-model.safetensors",
        checkpoint_backend,
        train_examples,
        summaries,
        labels,
        dependencies,
        protocol_sha,
        pool_sha,
        sha256_path(pointwise_path),
    )
    if pointwise_path.read_bytes() != canonical_json_bytes(pointwise):
        raise ValueError("pointwise manifest is not canonical JSON")


def fit_train_dev_models(
    root: Path,
    sources: ProtocolSourcePaths,
    model_binding: PointwiseModelBinding,
    dependencies: Sequence[tuple[str, str]],
    scorer: PointwiseScorer,
    model_integrity_probe: Callable[[], str],
    *,
    trainer: ListwiseTrainer = train_listwise_model,
    checkpoint_backend: ListwiseCheckpointBackend | None = None,
) -> FreezeStatus:
    """Fit only eligible Train lists, select on Dev, and exclusively publish model artifacts."""

    backend = checkpoint_backend or CoreListwiseCheckpointBackend()
    rows = _check_frozen_train_dev_for_fit(root, sources, model_binding, dependencies)
    models = root / EXPERIMENT_DIRECTORY / "models"
    if models.exists():
        check_fitted_train_dev_models(
            root,
            sources,
            model_binding,
            dependencies,
            model_integrity_probe,
            backend,
        )
        return "unchanged"
    before_model_hash = model_integrity_probe()
    if before_model_hash != model_binding.manifest_sha256:
        raise ValueError("pointwise model bytes differ from the frozen manifest binding")
    expected_version = f"{model_binding.model_id}@{model_binding.revision}"
    if scorer.version != expected_version:
        raise ValueError("pointwise scorer version differs from the frozen model binding")
    scored_rows = _score_pointwise_rows(rows, scorer)
    after_model_hash = model_integrity_probe()
    if after_model_hash != before_model_hash:
        raise ValueError("pointwise weights changed during frozen scoring")
    protocol_sha, pool_sha = _experiment_input_hashes(root)
    pointwise = _pointwise_manifest_payload(
        rows,
        scored_rows,
        model_binding,
        dependencies,
        protocol_sha,
        pool_sha,
    )
    score_rows = _validate_pointwise_manifest(
        pointwise,
        rows,
        model_binding,
        dependencies,
        protocol_sha,
        pool_sha,
    )
    labels = load_train_dev_labels(_read_object(sources.benchmark, "benchmark"))
    train_examples, dev_examples, summaries = _build_listwise_examples(rows, score_rows, labels)
    if not train_examples or not dev_examples:
        raise ValueError(
            "eligible matched Train and Dev examples are required for listwise fitting"
        )
    result = trainer(train_examples, dev_examples)
    _validate_training_result(result, train_examples)
    if model_integrity_probe() != before_model_hash:
        raise ValueError("pointwise weights changed during listwise fitting")
    staging = Path(
        tempfile.mkdtemp(
            prefix=f".{EXPERIMENT_ID}-models-",
            dir=(root / EXPERIMENT_DIRECTORY).parent,
        )
    )
    try:
        checkpoint_path = staging / "listwise-model.safetensors"
        checkpoint_manifest = backend.save(checkpoint_path, result)
        pointwise_bytes = canonical_json_bytes(pointwise)
        (staging / "pointwise-manifest.json").write_bytes(pointwise_bytes)
        listwise = _listwise_manifest_payload(
            result,
            checkpoint_manifest,
            summaries,
            labels,
            dependencies,
            protocol_sha,
            pool_sha,
            sha256_bytes(pointwise_bytes),
        )
        (staging / "listwise-manifest.json").write_bytes(canonical_json_bytes(listwise))
        _require_models_layout(staging)
        _validate_listwise_manifest(
            listwise,
            checkpoint_path,
            backend,
            train_examples,
            summaries,
            labels,
            dependencies,
            protocol_sha,
            pool_sha,
            sha256_bytes(pointwise_bytes),
        )
        if models.exists():
            raise FileExistsError("neural reranker models directory appeared during fitting")
        os.rename(staging, models)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    check_fitted_train_dev_models(
        root,
        sources,
        model_binding,
        dependencies,
        model_integrity_probe,
        backend,
    )
    return "created"


@dataclass(frozen=True, slots=True)
class TestLabel:
    case_id: str
    expected_status: str
    expected_canonical_uuid: str | None
    failure_category: str
    hard_negative: bool


def load_test_queries(benchmark: Mapping[str, object]) -> tuple[tuple[str, str], ...]:
    cases = benchmark.get("cases")
    if not isinstance(cases, list):
        raise TypeError("benchmark requires cases[]")
    queries: list[tuple[str, str]] = []
    for raw in cases:
        if not isinstance(raw, Mapping):
            raise TypeError("benchmark case must be an object")
        if raw.get("split") != "test":
            continue
        case_id = raw.get("case_id")
        query = raw.get("query")
        if not isinstance(case_id, str) or not isinstance(query, str):
            raise TypeError("Test query projection is invalid")
        queries.append((case_id, query))
    if len(queries) != 21 or len({case_id for case_id, _query in queries}) != 21:
        raise ValueError("Test query projection must contain exactly 21 unique cases")
    return tuple(queries)


def load_test_labels(benchmark: Mapping[str, object]) -> tuple[TestLabel, ...]:
    validate_benchmark_contract(benchmark)
    cases = benchmark["cases"]
    labels: list[TestLabel] = []
    for raw in cast(list[object], cases):
        if not isinstance(raw, Mapping) or raw.get("split") != "test":
            continue
        case_id = raw.get("case_id")
        status = raw.get("expected_status")
        category = raw.get("failure_category")
        hard_negative = raw.get("hard_negative")
        target = raw.get("expected_canonical_uuid") if status == "matched" else None
        if (
            not isinstance(case_id, str)
            or status not in {"matched", "ambiguous", "no_match"}
            or not isinstance(category, str)
            or not isinstance(hard_negative, bool)
            or (status == "matched" and not isinstance(target, str))
        ):
            raise ValueError("Test label is invalid")
        labels.append(
            TestLabel(
                case_id=case_id,
                expected_status=cast(str, status),
                expected_canonical_uuid=cast(str | None, target),
                failure_category=category,
                hard_negative=hard_negative,
            )
        )
    if len(labels) != 21 or sum(label.expected_status == "matched" for label in labels) != 12:
        raise ValueError("Test labels differ from the frozen 21/12 contract")
    return tuple(labels)


def _score_records(
    candidates: Sequence[FrozenCandidate],
    scores: Sequence[float],
) -> list[dict[str, object]]:
    ranked = rank_scores(candidates, scores)
    ranks = {item.canonical_uuid: item.rank for item in ranked}
    return [
        {
            "canonical_uuid": candidate.canonical_uuid,
            "score": float(score),
            "rank": ranks[candidate.canonical_uuid],
        }
        for candidate, score in zip(candidates, scores, strict=True)
    ]


def _run_invariance_preflight(
    row: CandidatePoolRow,
    pointwise: PointwiseScorer,
    listwise: ListwiseScorer,
) -> None:
    if len(row.candidates) < 2:
        raise ValueError("invariance preflight requires at least two frozen candidates")
    pairs = tuple(
        (row.query, render_candidate_text(candidate.text)) for candidate in row.candidates
    )
    forward = pointwise.score_pairs(pairs)
    reverse = pointwise.score_pairs(tuple(reversed(pairs)))
    if any(
        not math.isclose(left, right, rel_tol=0.0, abs_tol=1e-6)
        for left, right in zip(forward, reversed(reverse), strict=True)
    ):
        raise ValueError("pointwise batch-order invariance preflight failed")
    features = tuple(
        candidate_feature_vector(candidate, score)
        for candidate, score in zip(row.candidates, forward, strict=True)
    )
    list_forward = listwise.score_set(features)
    list_reverse = listwise.score_set(tuple(reversed(features)))
    if any(
        not math.isclose(left, right, rel_tol=0.0, abs_tol=1e-6)
        for left, right in zip(list_forward, reversed(list_reverse), strict=True)
    ):
        raise ValueError("listwise permutation invariance preflight failed")


def _warm_scorers(
    rows: Sequence[CandidatePoolRow],
    pointwise: PointwiseScorer,
    listwise: ListwiseScorer,
) -> None:
    for row in rows[:5]:
        pairs = tuple(
            (row.query, render_candidate_text(candidate.text)) for candidate in row.candidates
        )
        pointwise_scores = pointwise.score_pairs(pairs)
        features = tuple(
            candidate_feature_vector(candidate, score)
            for candidate, score in zip(row.candidates, pointwise_scores, strict=True)
        )
        listwise.score_set(features)


def _raw_manifest(
    raw_bytes: bytes,
    root: Path,
    test_query_source_sha256: str,
    error_count: int,
) -> dict[str, object]:
    directory = root / EXPERIMENT_DIRECTORY
    return {
        "schema_version": RAW_MANIFEST_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "raw_sha256": sha256_bytes(raw_bytes),
        "protocol_sha256": sha256_path(directory / "protocol/protocol.json"),
        "pool_sha256": sha256_path(directory / "pool/train-dev-candidate-pool.json"),
        "pointwise_manifest_sha256": sha256_path(directory / "models/pointwise-manifest.json"),
        "listwise_manifest_sha256": sha256_path(directory / "models/listwise-manifest.json"),
        "listwise_checkpoint_sha256": sha256_path(directory / "models/listwise-model.safetensors"),
        "test_query_source_sha256": test_query_source_sha256,
        "case_count": 21,
        "retrieval_call_count": 21,
        "retrieval_error_count": error_count,
        "label_blind": True,
        "test_collection_executed": True,
    }


def validate_raw_test_document(payload: Mapping[str, object]) -> tuple[Mapping[str, object], ...]:
    validate_raw_test_payload(payload)
    _require_exact_keys(
        payload,
        {
            "schema_version",
            "experiment_id",
            "case_count",
            "arms",
            "candidate_limit",
            "rows",
        },
        "raw Test document",
    )
    if (
        payload["schema_version"] != RAW_SCHEMA
        or payload["experiment_id"] != EXPERIMENT_ID
        or payload["case_count"] != 21
        or payload["arms"] != list(ARMS)
        or payload["candidate_limit"] != CANDIDATE_LIMIT
    ):
        raise ValueError("raw Test header differs from the frozen contract")
    rows = payload["rows"]
    if not isinstance(rows, list) or len(rows) != 21:
        raise ValueError("raw Test document must contain exactly 21 rows")
    seen: set[str] = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise TypeError("raw Test row must be an object")
        _require_exact_keys(
            raw,
            {"case_id", "query", "signals", "candidates", "arms", "timings_ms", "error"},
            "raw Test row",
        )
        case_id = raw["case_id"]
        query = raw["query"]
        if not isinstance(case_id, str) or not isinstance(query, str) or case_id in seen:
            raise ValueError("raw Test case identity is invalid or duplicated")
        seen.add(case_id)
        error = raw["error"]
        candidates = raw["candidates"]
        arms = raw["arms"]
        timings = raw["timings_ms"]
        if (
            not isinstance(candidates, list)
            or not isinstance(arms, Mapping)
            or not isinstance(timings, Mapping)
        ):
            raise TypeError("raw Test candidate/arm/timing collections are invalid")
        if set(arms) != set(ARMS):
            raise ValueError("raw Test row must contain exactly the three frozen arms")
        if error is not None:
            if not isinstance(error, Mapping) or set(error) != {"type", "message"}:
                raise ValueError("raw Test error record is invalid")
            if candidates or any(arms[arm] for arm in ARMS):
                raise ValueError("errored raw Test rows cannot contain partial candidate scores")
            continue
        frozen_candidates = tuple(_parse_frozen_candidate(candidate) for candidate in candidates)
        identities = [candidate.canonical_uuid for candidate in frozen_candidates]
        for arm in ARMS:
            records = arms[arm]
            if not isinstance(records, list) or len(records) != len(frozen_candidates):
                raise ValueError("raw Test arm candidate count differs from shared candidates")
            record_ids: list[str] = []
            declared_ranks: list[int] = []
            scores: list[float] = []
            for record in records:
                if not isinstance(record, Mapping) or set(record) != {
                    "canonical_uuid",
                    "score",
                    "rank",
                }:
                    raise ValueError("raw Test arm score record is invalid")
                identity = record["canonical_uuid"]
                score = record["score"]
                rank = record["rank"]
                if (
                    not isinstance(identity, str)
                    or not isinstance(score, (int, float))
                    or isinstance(score, bool)
                    or not math.isfinite(float(score))
                    or not isinstance(rank, int)
                    or isinstance(rank, bool)
                ):
                    raise ValueError("raw Test arm score value is invalid")
                record_ids.append(identity)
                scores.append(float(score))
                declared_ranks.append(rank)
            if record_ids != identities:
                raise ValueError("raw Test arms do not share byte-equivalent candidate order")
            expected_ranks = {
                item.canonical_uuid: item.rank for item in rank_scores(frozen_candidates, scores)
            }
            if declared_ranks != [expected_ranks[identity] for identity in identities]:
                raise ValueError("raw Test arm ranks differ from deterministic scores")
        required_timings = {
            "signal",
            "retrieval",
            "policy",
            "pointwise",
            "listwise_head",
        }
        if set(timings) != required_timings or any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(float(value))
            or float(value) < 0
            for value in timings.values()
        ):
            raise ValueError("raw Test timings are incomplete or invalid")
    return tuple(cast(list[Mapping[str, object]], rows))


def check_collected_test(
    root: Path,
    sources: ProtocolSourcePaths,
    model_binding: PointwiseModelBinding,
    dependencies: Sequence[tuple[str, str]],
    model_integrity_probe: Callable[[], str],
    checkpoint_backend: ListwiseCheckpointBackend,
) -> tuple[Mapping[str, object], ...]:
    check_fitted_train_dev_models(
        root,
        sources,
        model_binding,
        dependencies,
        model_integrity_probe,
        checkpoint_backend,
    )
    raw_dir = root / EXPERIMENT_DIRECTORY / "raw"
    expected_names = {"test-raw.json", "test-raw-manifest.json"}
    if (
        not raw_dir.is_dir()
        or raw_dir.is_symlink()
        or {item.name for item in raw_dir.iterdir()} != expected_names
        or any(item.is_symlink() for item in raw_dir.iterdir())
    ):
        raise ValueError("neural reranker raw directory is partial or unsafe")
    raw_path = raw_dir / "test-raw.json"
    payload = _read_object(raw_path, "raw Test artifact")
    rows = validate_raw_test_document(payload)
    raw_bytes = canonical_json_bytes(payload)
    if raw_path.read_bytes() != raw_bytes:
        raise ValueError("raw Test artifact is not canonical JSON")
    error_count = sum(row["error"] is not None for row in rows)
    expected_manifest = _raw_manifest(
        raw_bytes,
        root,
        sha256_path(sources.benchmark),
        error_count,
    )
    manifest_path = raw_dir / "test-raw-manifest.json"
    manifest = _read_object(manifest_path, "raw Test manifest")
    if manifest != expected_manifest or manifest_path.read_bytes() != canonical_json_bytes(
        manifest
    ):
        raise ValueError("raw Test manifest differs from immutable inputs or raw bytes")
    queries = load_test_queries(_read_object(sources.benchmark, "benchmark"))
    if [(row["case_id"], row["query"]) for row in rows] != list(queries):
        raise ValueError("raw Test rows differ from the ordered Test query projection")
    return rows


def collect_test_once(
    root: Path,
    sources: ProtocolSourcePaths,
    model_binding: PointwiseModelBinding,
    dependencies: Sequence[tuple[str, str]],
    model_integrity_probe: Callable[[], str],
    checkpoint_backend: ListwiseCheckpointBackend,
    retriever: CandidatePoolRetriever,
    pointwise: PointwiseScorer,
    listwise: ListwiseScorer,
    *,
    policy_timing_ms: float = 0.0,
    clock: Callable[[], float] = time.perf_counter,
) -> FreezeStatus:
    train_dev_rows = _check_frozen_train_dev_for_fit(root, sources, model_binding, dependencies)
    check_fitted_train_dev_models(
        root,
        sources,
        model_binding,
        dependencies,
        model_integrity_probe,
        checkpoint_backend,
    )
    raw_dir = root / EXPERIMENT_DIRECTORY / "raw"
    if raw_dir.exists():
        check_collected_test(
            root,
            sources,
            model_binding,
            dependencies,
            model_integrity_probe,
            checkpoint_backend,
        )
        return "unchanged"
    if not math.isfinite(policy_timing_ms) or policy_timing_ms < 0:
        raise ValueError("policy timing must be finite and nonnegative")
    before_hash = model_integrity_probe()
    _run_invariance_preflight(train_dev_rows[0], pointwise, listwise)
    _warm_scorers(train_dev_rows, pointwise, listwise)
    benchmark = _read_object(sources.benchmark, "benchmark")
    queries = load_test_queries(benchmark)
    catalog = load_catalog(sources.catalog)
    colors = frozenset(
        item.product.color for item in catalog.products if item.product.color is not None
    )
    series = frozenset(
        item.product.series for item in catalog.products if item.product.series is not None
    )
    raw_rows: list[dict[str, object]] = []
    for case_id, query in queries:
        empty_arms: dict[str, list[object]] = {arm: [] for arm in ARMS}
        try:
            started = clock()
            signals = extract_signals(query, colors, series)
            signal_ms = (clock() - started) * 1000.0
            started = clock()
            candidates, _retrieval_stage_timings = retriever.retrieve_with_timings(
                signals, CANDIDATE_LIMIT
            )
            retrieval_ms = (clock() - started) * 1000.0
            frozen = tuple(freeze_candidate(candidate) for candidate in candidates)
            pairs = tuple((query, render_candidate_text(candidate.text)) for candidate in frozen)
            started = clock()
            pointwise_scores = pointwise.score_pairs(pairs)
            pointwise_ms = (clock() - started) * 1000.0
            features = tuple(
                candidate_feature_vector(candidate, score)
                for candidate, score in zip(frozen, pointwise_scores, strict=True)
            )
            started = clock()
            listwise_scores = listwise.score_set(features)
            listwise_ms = (clock() - started) * 1000.0
            rrf_scores = tuple(candidate.rrf_score for candidate in frozen)
            raw_rows.append(
                {
                    "case_id": case_id,
                    "query": query,
                    "signals": _signals_payload(_freeze_signals(signals)),
                    "candidates": [_candidate_payload(candidate) for candidate in frozen],
                    "arms": {
                        "rrf": _score_records(frozen, rrf_scores),
                        "neural_pointwise": _score_records(frozen, pointwise_scores),
                        "neural_listwise": _score_records(frozen, listwise_scores),
                    },
                    "timings_ms": {
                        "signal": signal_ms,
                        "retrieval": retrieval_ms,
                        "policy": policy_timing_ms,
                        "pointwise": pointwise_ms,
                        "listwise_head": listwise_ms,
                    },
                    "error": None,
                }
            )
        except Exception as error:  # noqa: BLE001 - a formal Test error is persisted once
            raw_rows.append(
                {
                    "case_id": case_id,
                    "query": query,
                    "signals": None,
                    "candidates": [],
                    "arms": empty_arms,
                    "timings_ms": {},
                    "error": {"type": type(error).__name__, "message": str(error)},
                }
            )
    if model_integrity_probe() != before_hash:
        raise ValueError("pointwise weights changed during Test collection")
    payload: dict[str, object] = {
        "schema_version": RAW_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "case_count": 21,
        "arms": list(ARMS),
        "candidate_limit": CANDIDATE_LIMIT,
        "rows": raw_rows,
    }
    validate_raw_test_document(payload)
    raw_bytes = canonical_json_bytes(payload)
    manifest_bytes = canonical_json_bytes(
        _raw_manifest(
            raw_bytes,
            root,
            sha256_path(sources.benchmark),
            sum(row["error"] is not None for row in raw_rows),
        )
    )
    staging = Path(
        tempfile.mkdtemp(prefix=f".{EXPERIMENT_ID}-raw-", dir=(root / EXPERIMENT_DIRECTORY).parent)
    )
    try:
        (staging / "test-raw.json").write_bytes(raw_bytes)
        (staging / "test-raw-manifest.json").write_bytes(manifest_bytes)
        if raw_dir.exists():
            raise FileExistsError("neural reranker raw directory appeared during collection")
        os.rename(staging, raw_dir)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    check_collected_test(
        root,
        sources,
        model_binding,
        dependencies,
        model_integrity_probe,
        checkpoint_backend,
    )
    return "created"


def _metric_payload(metric: MetricValue) -> dict[str, int | float]:
    return {
        "numerator": metric.numerator,
        "denominator": metric.denominator,
        "value": metric.value,
    }


def _nearest_rank(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be in (0, 1]")
    ordered = sorted(float(value) for value in values)
    return ordered[math.ceil(len(ordered) * percentile) - 1]


def evaluate_arm_gates(
    baseline_metrics: Mapping[str, MetricValue],
    arm_metrics: Mapping[str, MetricValue],
    *,
    resolver_p95_ms: float,
    error_count: int,
) -> tuple[dict[str, object], ...]:
    checks = (
        (
            "top1_absolute_gain_at_least_0_05",
            arm_metrics["top1_accuracy"].value - baseline_metrics["top1_accuracy"].value,
            ">=",
            0.05,
        ),
        (
            "hard_negative_accuracy_not_lower",
            arm_metrics["hard_negative_accuracy"].value,
            ">=",
            baseline_metrics["hard_negative_accuracy"].value,
        ),
        (
            "mrr_at_10_not_lower",
            arm_metrics["mrr_at_10"].value,
            ">=",
            baseline_metrics["mrr_at_10"].value,
        ),
        (
            "recall_at_25_identical",
            arm_metrics["recall_at_25"].value,
            "=",
            baseline_metrics["recall_at_25"].value,
        ),
        ("resolver_p95_at_most_1500_ms", resolver_p95_ms, "<=", 1500.0),
        ("collection_errors_equal_zero", float(error_count), "=", 0.0),
    )
    result: list[dict[str, object]] = []
    for name, actual, operator, threshold in checks:
        if operator == ">=":
            passed = actual >= threshold
        elif operator == "<=":
            passed = actual <= threshold
        else:
            passed = math.isclose(actual, threshold, rel_tol=0.0, abs_tol=1e-15)
        result.append(
            {
                "name": name,
                "actual": actual,
                "operator": operator,
                "threshold": threshold,
                "passed": passed,
            }
        )
    return tuple(result)


def select_recommendation(
    arm_results: Mapping[str, Mapping[str, object]],
) -> str | None:
    candidates: list[tuple[str, Mapping[str, object]]] = []
    for arm in ("neural_pointwise", "neural_listwise"):
        result = arm_results.get(arm)
        if result is None:
            raise ValueError("recommendation requires both neural arm results")
        gates = result.get("gates")
        if not isinstance(gates, list):
            raise TypeError("recommendation arm gates must be a list")
        if all(isinstance(gate, Mapping) and gate.get("passed") is True for gate in gates):
            candidates.append((arm, result))
    if not candidates:
        return None

    def key(item: tuple[str, Mapping[str, object]]) -> tuple[float, float, float, float, int]:
        arm, result = item
        metrics = result.get("metrics")
        latency = result.get("latency_ms")
        if not isinstance(metrics, Mapping) or not isinstance(latency, Mapping):
            raise TypeError("recommendation result metrics/latency are invalid")

        def metric(name: str) -> float:
            value = metrics.get(name)
            if not isinstance(value, Mapping) or not isinstance(value.get("value"), (int, float)):
                raise TypeError("recommendation metric is invalid")
            return float(value["value"])

        p95 = latency.get("resolver_p95")
        if not isinstance(p95, (int, float)):
            raise TypeError("recommendation latency is invalid")
        simplicity = 1 if arm == "neural_pointwise" else 0
        return (
            metric("hard_negative_accuracy"),
            metric("top1_accuracy"),
            metric("mrr_at_10"),
            -float(p95),
            simplicity,
        )

    return max(candidates, key=key)[0]


def _arm_target_rank(raw_row: Mapping[str, object], arm: str, target: str) -> int | None:
    arms = cast(Mapping[str, object], raw_row["arms"])
    records = cast(list[Mapping[str, object]], arms[arm])
    for record in records:
        if record["canonical_uuid"] == target:
            return cast(int, record["rank"])
    return None


def _comparison_report(
    raw_rows: Sequence[Mapping[str, object]],
    labels: Sequence[TestLabel],
    root: Path,
) -> dict[str, object]:
    if [row["case_id"] for row in raw_rows] != [label.case_id for label in labels]:
        raise ValueError("raw Test rows and Test labels are not aligned")
    matched: list[ScoredCase] = []
    case_rows: list[dict[str, object]] = []
    for raw, label in zip(raw_rows, labels, strict=True):
        error = raw["error"]
        target_ranks: tuple[tuple[str, int | None], ...]
        if label.expected_status == "matched":
            target = cast(str, label.expected_canonical_uuid)
            target_ranks = (
                tuple((arm, _arm_target_rank(raw, arm, target)) for arm in ARMS)
                if error is None
                else tuple((arm, None) for arm in ARMS)
            )
            matched.append(
                ScoredCase(
                    case_id=label.case_id,
                    failure_category=label.failure_category,
                    hard_negative=label.hard_negative,
                    expected_canonical_uuid=target,
                    target_ranks=target_ranks,
                )
            )
        else:
            target_ranks = tuple((arm, None) for arm in ARMS)
        case_rows.append(
            {
                "case_id": label.case_id,
                "query": raw["query"],
                "expected_status": label.expected_status,
                "expected_canonical_uuid": label.expected_canonical_uuid,
                "failure_category": label.failure_category,
                "hard_negative": label.hard_negative,
                "target_ranks": dict(target_ranks),
                "shared_candidates": raw["candidates"],
                "arm_scores": raw["arms"],
                "timings_ms": raw["timings_ms"],
                "evidence_scope": (
                    "RRF/source ranks and structured evidence are shared; pointwise uses only "
                    "query/candidate text; listwise adds frozen generic candidate-set features."
                ),
                "error": error,
            }
        )
    if len(matched) != 12:
        raise ValueError("comparison requires exactly 12 matched Test labels")
    metric_objects = {arm: ranking_metrics(matched, arm) for arm in ARMS}
    error_count = sum(row["error"] is not None for row in raw_rows)
    latency: dict[str, dict[str, float]] = {}
    for arm in ARMS:
        samples: list[float] = []
        rerank_samples: list[float] = []
        for row in raw_rows:
            if row["error"] is not None:
                continue
            timings = cast(Mapping[str, float], row["timings_ms"])
            common = timings["signal"] + timings["retrieval"] + timings["policy"]
            rerank = 0.0
            if arm == "neural_pointwise":
                rerank = timings["pointwise"]
            elif arm == "neural_listwise":
                rerank = timings["pointwise"] + timings["listwise_head"]
            samples.append(common + rerank)
            rerank_samples.append(rerank)
        latency[arm] = {
            "sample_count": float(len(samples)),
            "rerank_p50": _nearest_rank(rerank_samples, 0.50),
            "rerank_p95": _nearest_rank(rerank_samples, 0.95),
            "resolver_p50": _nearest_rank(samples, 0.50),
            "resolver_p95": _nearest_rank(samples, 0.95),
        }
    arm_results: dict[str, dict[str, object]] = {}
    for arm in ARMS:
        metrics = {name: _metric_payload(value) for name, value in metric_objects[arm].items()}
        gates = (
            []
            if arm == "rrf"
            else list(
                evaluate_arm_gates(
                    metric_objects["rrf"],
                    metric_objects[arm],
                    resolver_p95_ms=latency[arm]["resolver_p95"],
                    error_count=error_count,
                )
            )
        )
        arm_results[arm] = {"metrics": metrics, "latency_ms": latency[arm], "gates": gates}
    winner = select_recommendation(arm_results)
    transitions = {
        arm: [
            {
                "case_id": item.case_id,
                "baseline_rank": item.baseline_rank,
                "compared_rank": item.compared_rank,
                "direction": item.direction,
            }
            for item in paired_rank_transitions(matched, arm)
        ]
        for arm in ("neural_pointwise", "neural_listwise")
    }
    by_category: dict[str, object] = {}
    for category in sorted({case.failure_category for case in matched}):
        subset = [case for case in matched if case.failure_category == category]
        by_category[category] = {
            arm: {
                name: _metric_payload(value) for name, value in ranking_metrics(subset, arm).items()
            }
            for arm in ARMS
        }
    directory = root / EXPERIMENT_DIRECTORY
    pointwise_model = _read_object(
        directory / "models/pointwise-manifest.json", "pointwise manifest"
    )
    listwise_model = _read_object(directory / "models/listwise-manifest.json", "listwise manifest")
    return {
        "schema_version": REPORT_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "dataset": "100-case synthetic/curated fixture benchmark",
        "test_case_count": 21,
        "matched_test_denominator": 12,
        "one_case_top1_increment": 1 / 12,
        "arms": arm_results,
        "winner": winner,
        "default_runtime_arm": "rrf",
        "score_semantics": "Raw ranking scores only; no neural score is a calibrated match probability.",
        "model_versions": {
            "pointwise": {
                "model_id": pointwise_model["model_id"],
                "revision": pointwise_model["revision"],
                "manifest_sha256": sha256_path(directory / "models/pointwise-manifest.json"),
            },
            "listwise": {
                "architecture": listwise_model["architecture"],
                "selected_epoch": listwise_model["selected_epoch"],
                "checkpoint_sha256": sha256_path(directory / "models/listwise-model.safetensors"),
            },
        },
        "collection_error_count": error_count,
        "cases": case_rows,
        "paired_transitions": transitions,
        "metrics_by_failure_category": by_category,
        "bindings": {
            "raw_sha256": sha256_path(directory / "raw/test-raw.json"),
            "pointwise_manifest_sha256": sha256_path(directory / "models/pointwise-manifest.json"),
            "listwise_manifest_sha256": sha256_path(directory / "models/listwise-manifest.json"),
        },
        "disclaimers": [
            "Shadow evaluation only; runtime, API, calibration, Dual RAG and PostgreSQL are unchanged.",
            "The 12 matched Test cases do not establish production accuracy or statistical generality.",
            "A null result is complete and must not be retuned against Test labels.",
        ],
    }


def _json_number(value: object) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError("report numeric field is invalid")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("report numeric field must be finite")
    return result


def render_comparison_markdown(report: Mapping[str, object]) -> str:
    winner = report["winner"] if report["winner"] is not None else "null"
    lines = [
        "# Neural reranker comparison v1",
        "",
        f"Winner: **{winner}**. Runtime default remains **RRF**.",
        "",
        (
            "Dataset: 100-case synthetic/curated fixture benchmark; Test has 21 cases and exactly "
            "12 matched ranking targets. One matched case changes Top-1 by 0.0833."
        ),
        "",
        "| Arm | Top-1 | MRR@10 | Hard-negative | Recall@25 | Resolver p95 ms |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    arms = cast(Mapping[str, Mapping[str, object]], report["arms"])
    for arm in ARMS:
        result = arms[arm]
        metrics = cast(Mapping[str, Mapping[str, object]], result["metrics"])
        latency = cast(Mapping[str, object], result["latency_ms"])
        lines.append(
            f"| {arm} | {_json_number(metrics['top1_accuracy']['value']):.6f} | "
            f"{_json_number(metrics['mrr_at_10']['value']):.6f} | "
            f"{_json_number(metrics['hard_negative_accuracy']['value']):.6f} | "
            f"{_json_number(metrics['recall_at_25']['value']):.6f} | "
            f"{_json_number(latency['resolver_p95']):.3f} |"
        )
    lines.extend(["", "## Limitations", ""])
    for disclaimer in cast(list[str], report["disclaimers"]):
        lines.append(f"- {disclaimer}")
    lines.extend(
        ["", "All metrics preserve raw numerators and denominators in comparison.json.", ""]
    )
    return "\n".join(lines)


def render_reranker_comparison_svg(report: Mapping[str, object]) -> str:
    arms = cast(Mapping[str, Mapping[str, object]], report["arms"])
    colors = {"rrf": "#64748b", "neural_pointwise": "#2563eb", "neural_listwise": "#7c3aed"}
    bars: list[str] = []
    for index, arm in enumerate(ARMS):
        metrics = cast(Mapping[str, Mapping[str, object]], arms[arm]["metrics"])
        value = _json_number(metrics["top1_accuracy"]["value"])
        width = value * 420
        y = 55 + index * 55
        bars.append(
            f'<g data-arm="{arm}" data-top1="{value:.12f}"><text x="10" y="{y + 18}">'
            f'{arm}</text><rect x="155" y="{y}" width="{width:.3f}" height="24" '
            f'fill="{colors[arm]}"/><text x="{165 + width:.3f}" y="{y + 18}">{value:.4f}</text></g>'
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="680" height="240" viewBox="0 0 680 240">'
        '<rect width="100%" height="100%" fill="white"/><text x="10" y="28" '
        'font-size="20">Matched Test Top-1 accuracy (n=12)</text>' + "".join(bars) + "</svg>\n"
    )


def render_accuracy_latency_svg(report: Mapping[str, object]) -> str:
    arms = cast(Mapping[str, Mapping[str, object]], report["arms"])
    points: list[str] = []
    for arm in ARMS:
        metrics = cast(Mapping[str, Mapping[str, object]], arms[arm]["metrics"])
        latency = cast(Mapping[str, object], arms[arm]["latency_ms"])
        accuracy = _json_number(metrics["top1_accuracy"]["value"])
        p95 = _json_number(latency["resolver_p95"])
        x = 70 + min(p95 / 1500.0, 1.0) * 500
        y = 190 - accuracy * 150
        points.append(
            f'<g data-arm="{arm}" data-top1="{accuracy:.12f}" data-p95-ms="{p95:.6f}">'
            f'<circle cx="{x:.3f}" cy="{y:.3f}" r="7"/><text x="{x + 10:.3f}" '
            f'y="{y + 4:.3f}">{arm}</text></g>'
        )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="680" height="240" viewBox="0 0 680 240">'
        '<rect width="100%" height="100%" fill="white"/><text x="10" y="24" '
        'font-size="20">Top-1 accuracy vs resolver p95 (1500 ms budget)</text>'
        '<line x1="70" y1="190" x2="590" y2="190" stroke="black"/>'
        '<line x1="70" y1="40" x2="70" y2="190" stroke="black"/>' + "".join(points) + "</svg>\n"
    )


def _report_files(report: Mapping[str, object]) -> dict[str, bytes]:
    report_bytes = canonical_json_bytes(report)
    markdown = render_comparison_markdown(report).encode("utf-8")
    comparison_svg = render_reranker_comparison_svg(report).encode("utf-8")
    latency_svg = render_accuracy_latency_svg(report).encode("utf-8")
    manifest = {
        "schema_version": REPORT_MANIFEST_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "comparison_sha256": sha256_bytes(report_bytes),
        "markdown_sha256": sha256_bytes(markdown),
        "reranker_comparison_svg_sha256": sha256_bytes(comparison_svg),
        "accuracy_latency_svg_sha256": sha256_bytes(latency_svg),
        "winner": report["winner"],
        "raw_sha256": cast(Mapping[str, object], report["bindings"])["raw_sha256"],
    }
    return {
        "comparison.json": report_bytes,
        "comparison-manifest.json": canonical_json_bytes(manifest),
        "comparison.md": markdown,
        "reranker-comparison.svg": comparison_svg,
        "accuracy-latency.svg": latency_svg,
    }


def check_scored_report(
    root: Path,
    sources: ProtocolSourcePaths,
    model_binding: PointwiseModelBinding,
    dependencies: Sequence[tuple[str, str]],
    model_integrity_probe: Callable[[], str],
    checkpoint_backend: ListwiseCheckpointBackend,
) -> Mapping[str, object]:
    raw_rows = check_collected_test(
        root,
        sources,
        model_binding,
        dependencies,
        model_integrity_probe,
        checkpoint_backend,
    )
    report_dir = root / REPORT_DIRECTORY
    expected_names = {
        "comparison.json",
        "comparison-manifest.json",
        "comparison.md",
        "reranker-comparison.svg",
        "accuracy-latency.svg",
    }
    if (
        not report_dir.is_dir()
        or report_dir.is_symlink()
        or {item.name for item in report_dir.iterdir()} != expected_names
        or any(item.is_symlink() for item in report_dir.iterdir())
    ):
        raise ValueError("neural reranker report directory is partial or unsafe")
    labels = load_test_labels(_read_object(sources.benchmark, "benchmark"))
    expected = _comparison_report(raw_rows, labels, root)
    files = _report_files(expected)
    for name, content in files.items():
        if (report_dir / name).read_bytes() != content:
            raise ValueError(f"neural reranker report file drift: {name}")
    return expected


def score_test_once(
    root: Path,
    sources: ProtocolSourcePaths,
    model_binding: PointwiseModelBinding,
    dependencies: Sequence[tuple[str, str]],
    model_integrity_probe: Callable[[], str],
    checkpoint_backend: ListwiseCheckpointBackend,
) -> FreezeStatus:
    raw_rows = check_collected_test(
        root,
        sources,
        model_binding,
        dependencies,
        model_integrity_probe,
        checkpoint_backend,
    )
    report_dir = root / REPORT_DIRECTORY
    if report_dir.exists():
        check_scored_report(
            root,
            sources,
            model_binding,
            dependencies,
            model_integrity_probe,
            checkpoint_backend,
        )
        return "unchanged"
    protected = {
        path: path.read_bytes()
        for path in (
            root / EXPERIMENT_DIRECTORY / "raw/test-raw.json",
            root / EXPERIMENT_DIRECTORY / "raw/test-raw-manifest.json",
            root / EXPERIMENT_DIRECTORY / "models/pointwise-manifest.json",
            root / EXPERIMENT_DIRECTORY / "models/listwise-manifest.json",
            root / EXPERIMENT_DIRECTORY / "models/listwise-model.safetensors",
        )
    }
    labels = load_test_labels(_read_object(sources.benchmark, "benchmark"))
    report = _comparison_report(raw_rows, labels, root)
    files = _report_files(report)
    report_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{EXPERIMENT_ID}-report-", dir=report_dir.parent))
    try:
        for name, content in files.items():
            (staging / name).write_bytes(content)
        if report_dir.exists():
            raise FileExistsError("neural reranker report directory appeared during scoring")
        os.rename(staging, report_dir)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    if any(path.read_bytes() != content for path, content in protected.items()):
        raise ValueError("scoring altered immutable model or raw Test bytes")
    check_scored_report(
        root,
        sources,
        model_binding,
        dependencies,
        model_integrity_probe,
        checkpoint_backend,
    )
    return "created"


@dataclass(slots=True)
class LocalListwiseScorer:
    version: str
    model: object
    normalizer: FeatureNormalizer
    torch_module: Any

    def score_set(self, features: Sequence[Sequence[float]]) -> tuple[float, ...]:
        if not features:
            return ()
        return score_listwise_features(
            self.model,
            features,
            self.normalizer,
            torch_module=self.torch_module,
        )

    @classmethod
    def load(cls, selection_manifest: Path, checkpoint: Path) -> LocalListwiseScorer:
        selection = _read_object(selection_manifest, "listwise selection manifest")
        normalizer = _parse_selection_normalizer(selection.get("normalizer"))
        torch = importlib.import_module("torch")
        safetensors = importlib.import_module("safetensors.torch")
        load_file = getattr(safetensors, "load_file", None)
        if not callable(load_file):
            raise TypeError("installed safetensors.torch API is incompatible")
        model = cast(Any, build_candidate_set_reranker(torch_module=torch))
        state = load_file(str(checkpoint), device="cpu")
        model.load_state_dict(state, strict=True)
        model.eval()
        return cls(
            version=f"candidate-set-reranker-v1@{sha256_path(checkpoint)}",
            model=model,
            normalizer=normalizer,
            torch_module=torch,
        )


def resolved_reranking_dependencies() -> tuple[tuple[str, str], ...]:
    packages = (
        ("product-variant-resolver", "product-variant-resolver"),
        ("sentence-transformers", "sentence-transformers"),
        ("torch", "torch"),
        ("safetensors", "safetensors"),
    )
    values = [("python", platform_python_version())]
    for logical_name, distribution in packages:
        try:
            version = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError as error:
            raise RuntimeError(
                "neural reranking dependencies are missing; install "
                "'product-variant-resolver[reranking]' with "
                "constraints/reranking-python312.txt"
            ) from error
        values.append((logical_name, version))
    return tuple(values)


def platform_python_version() -> str:
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _local_model_context(
    root: Path,
) -> tuple[PointwiseModelBinding, Callable[[], str], LocalPointwiseScorer]:
    config = load_pointwise_model_config(root / "config/neural-reranker-comparison-v1.json")
    model_directory = root / "model-cache/neural-reranker-comparison-v1/pointwise"
    validate_local_pointwise_model(config, model_directory)
    manifest_path = model_directory / "manifest.json"
    binding = PointwiseModelBinding(
        model_id=config.model_id,
        revision=config.revision,
        license=config.license,
        manifest_sha256=sha256_path(manifest_path),
    )

    def probe() -> str:
        validate_local_pointwise_model(config, model_directory)
        return sha256_path(manifest_path)

    scorer = LocalPointwiseScorer.load(config, model_directory)
    return binding, probe, scorer


def _cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pvr-compare-neural-rerankers",
        description="Run the immutable neural pointwise/listwise comparison phases",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    phases = parser.add_mutually_exclusive_group(required=True)
    phases.add_argument("--acquire-model", action="store_true")
    phases.add_argument("--freeze-protocol", action="store_true")
    phases.add_argument("--fit", action="store_true")
    phases.add_argument("--collect-test", action="store_true")
    phases.add_argument("--score", action="store_true")
    phases.add_argument("--check", action="store_true")
    parser.add_argument("--confirm-license", action="store_true")
    return parser


def _run_cli(args: argparse.Namespace) -> str:
    root = cast(Path, args.root).resolve()
    config_path = root / "config/neural-reranker-comparison-v1.json"
    if args.acquire_model:
        config = load_pointwise_model_config(config_path)
        return acquire_pointwise_model(
            config,
            root / "model-cache/neural-reranker-comparison-v1/pointwise",
            confirm_license=bool(args.confirm_license),
        )
    sources = default_protocol_sources(root)
    dependencies = resolved_reranking_dependencies()
    binding, probe, pointwise = _local_model_context(root)
    backend = CoreListwiseCheckpointBackend()
    if args.freeze_protocol:
        catalog = load_catalog(sources.catalog)
        return freeze_protocol_and_train_dev_pool(
            root,
            sources,
            binding,
            dependencies,
            build_offline_canonical_retriever(catalog),
        )
    if args.fit:
        return fit_train_dev_models(
            root,
            sources,
            binding,
            dependencies,
            pointwise,
            probe,
            checkpoint_backend=backend,
        )
    if args.collect_test:
        models = root / EXPERIMENT_DIRECTORY / "models"
        listwise = LocalListwiseScorer.load(
            models / "listwise-manifest.json",
            models / "listwise-model.safetensors",
        )
        catalog = load_catalog(sources.catalog)
        return collect_test_once(
            root,
            sources,
            binding,
            dependencies,
            probe,
            backend,
            build_offline_canonical_retriever(catalog),
            pointwise,
            listwise,
        )
    if args.score:
        return score_test_once(root, sources, binding, dependencies, probe, backend)
    report = root / REPORT_DIRECTORY
    raw = root / EXPERIMENT_DIRECTORY / "raw"
    models = root / EXPERIMENT_DIRECTORY / "models"
    if report.exists():
        check_scored_report(root, sources, binding, dependencies, probe, backend)
    elif raw.exists():
        check_collected_test(root, sources, binding, dependencies, probe, backend)
    elif models.exists():
        check_fitted_train_dev_models(root, sources, binding, dependencies, probe, backend)
    else:
        check_frozen_train_dev(root, sources, binding, dependencies)
    return "valid"


def main(argv: Sequence[str] | None = None) -> int:
    args = _cli_parser().parse_args(argv)
    status = _run_cli(args)
    print(status)
    return 0


if __name__ == "__main__":  # pragma: no cover - installed entry point owns execution
    raise SystemExit(main())
