from __future__ import annotations

import copy
import json
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from product_variant_resolver.catalog import Catalog, load_catalog
from product_variant_resolver.neural_reranker_comparison import (
    EXPERIMENT_DIRECTORY,
    POINTWISE_LICENSE,
    POINTWISE_MODEL_ID,
    POINTWISE_REVISION,
    REPORT_DIRECTORY,
    ListwiseCheckpointBackend,
    PointwiseModelBinding,
    ProtocolSourcePaths,
    build_offline_canonical_retriever,
    check_fitted_train_dev_models,
    check_frozen_train_dev,
    collect_test_once,
    evaluate_arm_gates,
    fit_train_dev_models,
    freeze_protocol_and_train_dev_pool,
    score_test_once,
    select_recommendation,
    validate_candidate_pool_document,
)
from product_variant_resolver.neural_reranking import (
    ListwiseExample,
    ListwiseTrainingResult,
    MetricValue,
    TrainingEpoch,
    fit_train_feature_normalizer,
    sha256_path,
    validate_candidate_pool_payload,
)
from product_variant_resolver.retrieval import (
    Candidate,
    DenseRetriever,
    SparseRetriever,
    StructuredRetriever,
)
from product_variant_resolver.schemas import ExtractedSignals
from product_variant_resolver.signals import extract_signals

ROOT = Path(__file__).resolve().parents[2]
DEPENDENCIES = (("python", "3.12-test"), ("product-variant-resolver", "0.1.0-test"))
MODEL_BINDING = PointwiseModelBinding(
    model_id=POINTWISE_MODEL_ID,
    revision=POINTWISE_REVISION,
    license=POINTWISE_LICENSE,
    manifest_sha256="a" * 64,
)


class RecordingRetriever:
    def __init__(self, catalog: Catalog, *, missing_timing: bool = False) -> None:
        self.catalog = catalog
        self.missing_timing = missing_timing
        self.calls: list[tuple[ExtractedSignals, int]] = []

    def retrieve_with_timings(
        self,
        signals: ExtractedSignals,
        limit: int,
    ) -> tuple[list[Candidate], dict[str, float]]:
        self.calls.append((signals, limit))
        first, second = self.catalog.products[:2]
        candidates = [
            Candidate(
                product=first,
                source_ranks={"sparse": 1, "dense": 2, "structured": 1},
                source_scores={"sparse": 4.0, "dense": 0.9, "structured": 5.0},
                matches=["year", "color"],
                rrf_score=(1 / 61) + (1 / 62) + (1 / 61),
                rrf_rank=1,
            ),
            Candidate(
                product=second,
                source_ranks={"sparse": 2, "dense": 1},
                source_scores={"sparse": 3.0, "dense": 0.8},
                conflicts=["color"],
                rrf_score=(1 / 62) + (1 / 61),
                rrf_rank=2,
            ),
        ]
        timings = {"sparse": 1.0, "dense": 2.0, "structured": 3.0, "fusion": 0.5}
        if self.missing_timing:
            del timings["fusion"]
        return candidates[:limit], timings


class TargetFixtureRetriever:
    def __init__(
        self,
        catalog: Catalog,
        query_targets: Mapping[str, str],
        missing_targets: frozenset[str],
    ) -> None:
        self.catalog = catalog
        self.query_targets = query_targets
        self.missing_targets = missing_targets
        self.calls: list[str] = []

    def retrieve_with_timings(
        self,
        signals: ExtractedSignals,
        limit: int,
    ) -> tuple[list[Candidate], dict[str, float]]:
        query = signals.normalized_title
        self.calls.append(query)
        target_uuid = self.query_targets.get(query)
        products = list(self.catalog.products[:2])
        if target_uuid is not None and query not in self.missing_targets:
            target = self.catalog.by_uuid[UUID(target_uuid)]
            fallback = next(
                product
                for product in self.catalog.products
                if product.canonical_uuid != target.canonical_uuid
            )
            products = [target, fallback]
        candidates = [
            Candidate(
                product=product,
                source_ranks={"sparse": rank, "dense": rank},
                source_scores={"sparse": 3.0 / rank, "dense": 1.0 / rank},
                matches=["year"] if rank == 1 else [],
                conflicts=["color"] if rank == 2 else [],
                rrf_score=2 / (60 + rank),
                rrf_rank=rank,
            )
            for rank, product in enumerate(products[:limit], start=1)
        ]
        return candidates, {"sparse": 1.0, "dense": 2.0, "structured": 3.0, "fusion": 0.5}


class FakePointwiseScorer:
    version = f"{POINTWISE_MODEL_ID}@{POINTWISE_REVISION}"

    def __init__(self, state: dict[str, str], *, mutate_weights: bool = False) -> None:
        self.state = state
        self.mutate_weights = mutate_weights
        self.calls: list[tuple[tuple[str, str], ...]] = []

    def score_pairs(self, pairs: Any) -> tuple[float, ...]:
        frozen_pairs = tuple(pairs)
        self.calls.append(frozen_pairs)
        if self.mutate_weights:
            self.state["hash"] = "b" * 64
        return tuple(
            (sum(candidate.encode("utf-8")) % 997) / 100.0 for _query, candidate in frozen_pairs
        )


class RecordingTrainer:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[ListwiseExample, ...], tuple[ListwiseExample, ...]]] = []

    def __call__(
        self,
        train_examples: Any,
        dev_examples: Any,
    ) -> ListwiseTrainingResult:
        train = tuple(train_examples)
        dev = tuple(dev_examples)
        self.calls.append((train, dev))
        normalizer = fit_train_feature_normalizer(
            [row for example in train for row in example.features]
        )
        history = (
            TrainingEpoch(epoch=1, train_loss=1.0, dev_mrr_at_10=0.5),
            TrainingEpoch(epoch=2, train_loss=0.8, dev_mrr_at_10=0.75),
            TrainingEpoch(epoch=3, train_loss=0.7, dev_mrr_at_10=0.75),
        )
        return ListwiseTrainingResult(
            model=object(),
            normalizer=normalizer,
            history=history,
            selected_epoch=2,
            selected_dev_mrr_at_10=0.75,
        )


class FakeCheckpointBackend(ListwiseCheckpointBackend):
    def __init__(self) -> None:
        self.save_calls = 0
        self.validate_calls = 0

    def save(
        self,
        checkpoint_path: Path,
        result: ListwiseTrainingResult,
    ) -> Mapping[str, object]:
        self.save_calls += 1
        checkpoint_path.write_bytes(b"synthetic-safetensors-checkpoint-v1")
        return {
            "schema_version": 1,
            "selected_epoch": result.selected_epoch,
            "checkpoint_sha256": sha256_path(checkpoint_path),
        }

    def validate(
        self,
        checkpoint_path: Path,
        manifest: Mapping[str, object],
    ) -> None:
        self.validate_calls += 1
        if manifest.get("checkpoint_sha256") != sha256_path(checkpoint_path):
            raise ValueError("fake checkpoint hash drift")


class FakeListwiseScorer:
    version = "candidate-set-reranker-v1@synthetic"

    def __init__(self) -> None:
        self.calls: list[tuple[tuple[float, ...], ...]] = []

    def score_set(self, features: Any) -> tuple[float, ...]:
        rows = tuple(tuple(float(value) for value in row) for row in features)
        self.calls.append(rows)
        return tuple(row[0] + row[1] + sum(row[9:14]) * 0.1 for row in rows)


class FixedClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        self.value += 0.001
        return self.value


class FailingOnceRetriever(RecordingRetriever):
    def __init__(self, catalog: Catalog, *, fail_call: int) -> None:
        super().__init__(catalog)
        self.fail_call = fail_call

    def retrieve_with_timings(
        self,
        signals: ExtractedSignals,
        limit: int,
    ) -> tuple[list[Candidate], dict[str, float]]:
        if len(self.calls) + 1 == self.fail_call:
            self.calls.append((signals, limit))
            raise RuntimeError("synthetic retrieval failure")
        return super().retrieve_with_timings(signals, limit)


def copy_protocol_sources(tmp_path: Path) -> ProtocolSourcePaths:
    inputs = tmp_path / "inputs"
    config = inputs / "config.json"
    benchmark = inputs / "benchmark.json"
    catalog = inputs / "catalog.json"
    implementation = inputs / "implementation"
    implementation.mkdir(parents=True)
    shutil.copyfile(ROOT / "config/neural-reranker-comparison-v1.json", config)
    shutil.copyfile(ROOT / "data/benchmark.json", benchmark)
    shutil.copyfile(ROOT / "data/catalog.json", catalog)
    neural_source = implementation / "neural_reranking.py"
    comparison_source = implementation / "neural_reranker_comparison.py"
    shutil.copyfile(ROOT / "src/product_variant_resolver/neural_reranking.py", neural_source)
    shutil.copyfile(
        ROOT / "src/product_variant_resolver/neural_reranker_comparison.py",
        comparison_source,
    )
    return ProtocolSourcePaths(
        config=config,
        benchmark=benchmark,
        catalog=catalog,
        implementation_files=(
            ("src/product_variant_resolver/neural_reranking.py", neural_source),
            ("src/product_variant_resolver/neural_reranker_comparison.py", comparison_source),
        ),
    )


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def freeze_fixture(
    tmp_path: Path,
) -> tuple[ProtocolSourcePaths, RecordingRetriever, Path]:
    sources = copy_protocol_sources(tmp_path)
    retriever = RecordingRetriever(load_catalog(sources.catalog))
    assert (
        freeze_protocol_and_train_dev_pool(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            retriever,
        )
        == "created"
    )
    return sources, retriever, tmp_path / EXPERIMENT_DIRECTORY


def freeze_fit_fixture(
    tmp_path: Path,
) -> tuple[ProtocolSourcePaths, TargetFixtureRetriever, Path]:
    sources = copy_protocol_sources(tmp_path)
    catalog = load_catalog(sources.catalog)
    benchmark = load_json(sources.benchmark)
    cases = benchmark["cases"]
    assert isinstance(cases, list)
    colors = frozenset(
        product.product.color for product in catalog.products if product.product.color is not None
    )
    series = frozenset(
        product.product.series for product in catalog.products if product.product.series is not None
    )
    targets: dict[str, str] = {}
    matched_queries: dict[str, list[str]] = {"train": [], "dev": []}
    for case in cases:
        assert isinstance(case, dict)
        split = case["split"]
        if split not in matched_queries or case["expected_status"] != "matched":
            continue
        normalized = extract_signals(str(case["query"]), colors, series).normalized_title
        targets[normalized] = str(case["expected_canonical_uuid"])
        matched_queries[str(split)].append(normalized)
    missing = frozenset((matched_queries["train"][-1], matched_queries["dev"][-1]))
    retriever = TargetFixtureRetriever(catalog, targets, missing)
    assert (
        freeze_protocol_and_train_dev_pool(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            retriever,
        )
        == "created"
    )
    return sources, retriever, tmp_path / EXPERIMENT_DIRECTORY


def fitted_fixture(
    tmp_path: Path,
) -> tuple[ProtocolSourcePaths, dict[str, str], FakeCheckpointBackend, Path]:
    sources, _retriever, experiment = freeze_fit_fixture(tmp_path)
    state = {"hash": "a" * 64}
    backend = FakeCheckpointBackend()
    assert (
        fit_train_dev_models(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            FakePointwiseScorer(state),
            lambda: state["hash"],
            trainer=RecordingTrainer(),
            checkpoint_backend=backend,
        )
        == "created"
    )
    return sources, state, backend, experiment


def test_freeze_collects_each_train_dev_query_once_and_is_label_blind(tmp_path: Path) -> None:
    sources, retriever, experiment = freeze_fixture(tmp_path)

    assert len(retriever.calls) == 79
    assert all(limit == 25 for _signals, limit in retriever.calls)
    pool_path = experiment / "pool/train-dev-candidate-pool.json"
    pool_bytes = pool_path.read_bytes()
    pool = load_json(pool_path)
    validate_candidate_pool_payload(pool)
    rows = validate_candidate_pool_document(pool)
    assert len(rows) == 79
    assert {split: sum(row.split == split for row in rows) for split in ("train", "dev")} == {
        "train": 58,
        "dev": 21,
    }
    expected_ids = tuple(
        str(product.canonical_uuid) for product in load_catalog(sources.catalog).products[:2]
    )
    for row in rows:
        assert tuple(candidate.canonical_uuid for candidate in row.candidates) == expected_ids
        assert row.candidates[0].source_ranks == (
            ("sparse", 1),
            ("dense", 2),
            ("structured", 1),
        )
        assert row.candidates[1].source_ranks == (("sparse", 2), ("dense", 1))
        assert tuple(name for name, _value in row.retrieval_timings_ms) == (
            "sparse",
            "dense",
            "structured",
            "fusion",
        )
    manifest = load_json(experiment / "pool/train-dev-candidate-pool-manifest.json")
    assert manifest["retrieval_call_count"] == 79
    assert manifest["label_blind"] is True

    assert (
        freeze_protocol_and_train_dev_pool(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            retriever,
        )
        == "unchanged"
    )
    assert len(retriever.calls) == 79
    assert pool_path.read_bytes() == pool_bytes


@pytest.mark.parametrize("partial_child", ["protocol", "pool"])
def test_freeze_rejects_partial_existing_state_without_retrieval(
    tmp_path: Path,
    partial_child: str,
) -> None:
    sources = copy_protocol_sources(tmp_path)
    retriever = RecordingRetriever(load_catalog(sources.catalog))
    partial = tmp_path / EXPERIMENT_DIRECTORY / partial_child
    partial.mkdir(parents=True)

    with pytest.raises(ValueError, match="partial|missing"):
        freeze_protocol_and_train_dev_pool(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            retriever,
        )

    assert retriever.calls == []


def test_check_rejects_tampered_pool_and_freeze_never_overwrites_it(tmp_path: Path) -> None:
    sources, retriever, experiment = freeze_fixture(tmp_path)
    pool_path = experiment / "pool/train-dev-candidate-pool.json"
    tampered = load_json(pool_path)
    rows = tampered["rows"]
    assert isinstance(rows, list)
    first = rows[0]
    assert isinstance(first, dict)
    first["query"] = "tampered query"
    tampered_bytes = json.dumps(tampered, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    pool_path.write_bytes(tampered_bytes)

    with pytest.raises(ValueError, match="benchmark projection"):
        check_frozen_train_dev(tmp_path, sources, MODEL_BINDING, DEPENDENCIES)
    with pytest.raises(ValueError, match="benchmark projection"):
        freeze_protocol_and_train_dev_pool(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            retriever,
        )

    assert pool_path.read_bytes() == tampered_bytes
    assert len(retriever.calls) == 79


def test_check_rejects_source_drift_after_freeze(tmp_path: Path) -> None:
    sources, _retriever, _experiment = freeze_fixture(tmp_path)
    implementation_path = sources.implementation_files[1][1]
    implementation_path.write_text(
        implementation_path.read_text(encoding="utf-8") + "\n# drift\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="bound sources"):
        check_frozen_train_dev(tmp_path, sources, MODEL_BINDING, DEPENDENCIES)


def test_family_leak_and_incomplete_timings_fail_before_publication(tmp_path: Path) -> None:
    sources = copy_protocol_sources(tmp_path)
    benchmark = load_json(sources.benchmark)
    cases = benchmark["cases"]
    assert isinstance(cases, list)
    train_case = next(
        case for case in cases if isinstance(case, Mapping) and case.get("split") == "train"
    )
    dev_case = next(
        case for case in cases if isinstance(case, Mapping) and case.get("split") == "dev"
    )
    assert isinstance(train_case, dict) and isinstance(dev_case, dict)
    dev_case["casting_family"] = train_case["casting_family"]
    sources.benchmark.write_text(json.dumps(benchmark), encoding="utf-8")
    retriever = RecordingRetriever(load_catalog(sources.catalog))

    with pytest.raises(ValueError, match="leaks across splits"):
        freeze_protocol_and_train_dev_pool(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            retriever,
        )
    assert retriever.calls == []
    assert not (tmp_path / EXPERIMENT_DIRECTORY).exists()

    clean_root = tmp_path / "clean"
    clean_sources = copy_protocol_sources(clean_root)
    incomplete = RecordingRetriever(load_catalog(clean_sources.catalog), missing_timing=True)
    with pytest.raises(ValueError, match="timings"):
        freeze_protocol_and_train_dev_pool(
            clean_root,
            clean_sources,
            MODEL_BINDING,
            DEPENDENCIES,
            incomplete,
        )
    assert len(incomplete.calls) == 1
    assert not (clean_root / EXPERIMENT_DIRECTORY).exists()


def test_candidate_pool_parser_rejects_labels_and_malformed_retrieval_evidence(
    tmp_path: Path,
) -> None:
    _sources, _retriever, experiment = freeze_fixture(tmp_path)
    original = load_json(experiment / "pool/train-dev-candidate-pool.json")
    with_label = copy.deepcopy(original)
    rows = with_label["rows"]
    assert isinstance(rows, list) and isinstance(rows[0], dict)
    rows[0]["expected_status"] = "matched"
    with pytest.raises(ValueError, match="forbidden"):
        validate_candidate_pool_document(with_label)

    malformed = copy.deepcopy(original)
    malformed_rows = malformed["rows"]
    assert isinstance(malformed_rows, list) and isinstance(malformed_rows[0], dict)
    candidates = malformed_rows[0]["candidates"]
    assert isinstance(candidates, list) and isinstance(candidates[0], dict)
    source_ranks = candidates[0]["source_ranks"]
    assert isinstance(source_ranks, dict)
    source_ranks["sparse"] = "1"
    with pytest.raises(TypeError, match="source rank"):
        validate_candidate_pool_document(malformed)

    inconsistent_rrf = copy.deepcopy(original)
    inconsistent_rows = inconsistent_rrf["rows"]
    assert isinstance(inconsistent_rows, list) and isinstance(inconsistent_rows[0], dict)
    inconsistent_candidates = inconsistent_rows[0]["candidates"]
    assert isinstance(inconsistent_candidates, list) and isinstance(
        inconsistent_candidates[0], dict
    )
    inconsistent_candidates[0]["rrf_score"] = 0.0
    with pytest.raises(ValueError, match="RRF score"):
        validate_candidate_pool_document(inconsistent_rrf)


def test_offline_builder_reuses_the_three_canonical_retrievers(tmp_path: Path) -> None:
    sources = copy_protocol_sources(tmp_path)
    service = build_offline_canonical_retriever(load_catalog(sources.catalog))

    assert tuple(type(retriever) for retriever in service.retrievers) == (
        SparseRetriever,
        DenseRetriever,
        StructuredRetriever,
    )
    assert service.structured is service.retrievers[2]


def test_fit_uses_only_eligible_train_and_dev_selects_without_test_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources, _retriever, experiment = freeze_fit_fixture(tmp_path)
    state = {"hash": "a" * 64}
    scorer = FakePointwiseScorer(state)
    trainer = RecordingTrainer()
    backend = FakeCheckpointBackend()

    def forbidden_test_loader(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("fit must never invoke the Test-label loader")

    monkeypatch.setattr(
        "product_variant_resolver.neural_reranker_comparison.load_test_labels",
        forbidden_test_loader,
        raising=False,
    )
    monkeypatch.setattr(
        "product_variant_resolver.neural_reranker_comparison.validate_benchmark_contract",
        forbidden_test_loader,
    )
    assert (
        fit_train_dev_models(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            scorer,
            lambda: state["hash"],
            trainer=trainer,
            checkpoint_backend=backend,
        )
        == "created"
    )

    assert len(scorer.calls) == 79
    assert len(trainer.calls) == 1
    train_examples, dev_examples = trainer.calls[0]
    assert len(train_examples) == 35
    assert len(dev_examples) == 11
    assert all(len(example.features) == 2 for example in (*train_examples, *dev_examples))
    assert state["hash"] == "a" * 64
    pointwise_path = experiment / "models/pointwise-manifest.json"
    listwise_path = experiment / "models/listwise-manifest.json"
    pointwise = load_json(pointwise_path)
    listwise = load_json(listwise_path)
    assert pointwise["frozen_weights"] is True
    assert pointwise["case_count"] == 79
    assert pointwise["test_labels_loaded"] is False
    assert listwise["test_labels_loaded"] is False
    assert listwise["selected_epoch"] == 2
    assert listwise["eligibility"] == {
        "train": {
            "total_cases": 58,
            "matched_cases": 36,
            "eligible_cases": 35,
            "retrieval_misses": 1,
            "excluded_non_matched": 22,
        },
        "dev": {
            "total_cases": 21,
            "matched_cases": 12,
            "eligible_cases": 11,
            "retrieval_misses": 1,
            "excluded_non_matched": 9,
        },
    }
    serialized = pointwise_path.read_text(encoding="utf-8") + listwise_path.read_text(
        encoding="utf-8"
    )
    assert "expected_canonical_uuid" not in serialized
    assert "casting_family" not in serialized

    score_call_count = len(scorer.calls)
    trainer_call_count = len(trainer.calls)
    save_call_count = backend.save_calls
    assert (
        fit_train_dev_models(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            scorer,
            lambda: state["hash"],
            trainer=trainer,
            checkpoint_backend=backend,
        )
        == "unchanged"
    )
    assert len(scorer.calls) == score_call_count
    assert len(trainer.calls) == trainer_call_count
    assert backend.save_calls == save_call_count


def test_fit_rejects_pointwise_weight_mutation_before_model_publication(tmp_path: Path) -> None:
    sources, _retriever, experiment = freeze_fit_fixture(tmp_path)
    state = {"hash": "a" * 64}
    scorer = FakePointwiseScorer(state, mutate_weights=True)

    with pytest.raises(ValueError, match="weights changed"):
        fit_train_dev_models(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            scorer,
            lambda: state["hash"],
            trainer=RecordingTrainer(),
            checkpoint_backend=FakeCheckpointBackend(),
        )

    assert not (experiment / "models").exists()


def test_fitted_models_reject_every_upstream_drift_without_overwrite(tmp_path: Path) -> None:
    sources, _retriever, experiment = freeze_fit_fixture(tmp_path)
    state = {"hash": "a" * 64}
    backend = FakeCheckpointBackend()
    assert (
        fit_train_dev_models(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            FakePointwiseScorer(state),
            lambda: state["hash"],
            trainer=RecordingTrainer(),
            checkpoint_backend=backend,
        )
        == "created"
    )
    checkpoint = experiment / "models/listwise-model.safetensors"
    checkpoint_bytes = checkpoint.read_bytes()

    with pytest.raises(ValueError, match="bound sources"):
        check_fitted_train_dev_models(
            tmp_path,
            sources,
            MODEL_BINDING,
            (("python", "3.13-drift"), ("product-variant-resolver", "0.1.0-test")),
            lambda: state["hash"],
            backend,
        )
    with pytest.raises(ValueError, match="pointwise model bytes"):
        check_fitted_train_dev_models(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            lambda: "b" * 64,
            backend,
        )

    pool_path = experiment / "pool/train-dev-candidate-pool.json"
    pool_bytes = pool_path.read_bytes()
    pool_path.write_bytes(pool_bytes + b" ")
    with pytest.raises(ValueError, match="canonical JSON"):
        check_fitted_train_dev_models(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            lambda: state["hash"],
            backend,
        )
    pool_path.write_bytes(pool_bytes)

    config_bytes = sources.config.read_bytes()
    sources.config.write_bytes(config_bytes + b"\n")
    with pytest.raises(ValueError, match="bound sources"):
        check_fitted_train_dev_models(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            lambda: state["hash"],
            backend,
        )
    sources.config.write_bytes(config_bytes)
    assert checkpoint.read_bytes() == checkpoint_bytes

    tampered_checkpoint = b"tampered-listwise-checkpoint"
    checkpoint.write_bytes(tampered_checkpoint)
    with pytest.raises(ValueError, match="checkpoint hash drift"):
        check_fitted_train_dev_models(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            lambda: state["hash"],
            backend,
        )
    assert checkpoint.read_bytes() == tampered_checkpoint


def test_fit_rejects_partial_models_directory_without_scoring(tmp_path: Path) -> None:
    sources, _retriever, experiment = freeze_fit_fixture(tmp_path)
    models = experiment / "models"
    models.mkdir()
    (models / "pointwise-manifest.json").write_text("{}", encoding="utf-8")
    state = {"hash": "a" * 64}
    scorer = FakePointwiseScorer(state)

    with pytest.raises(ValueError, match="partial"):
        fit_train_dev_models(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            scorer,
            lambda: state["hash"],
            trainer=RecordingTrainer(),
            checkpoint_backend=FakeCheckpointBackend(),
        )

    assert scorer.calls == []


def test_synthetic_test_collection_and_scoring_are_immutable_and_honest(tmp_path: Path) -> None:
    sources, state, backend, experiment = fitted_fixture(tmp_path)
    test_retriever = RecordingRetriever(load_catalog(sources.catalog))
    pointwise = FakePointwiseScorer(state)
    listwise = FakeListwiseScorer()
    assert (
        collect_test_once(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            lambda: state["hash"],
            backend,
            test_retriever,
            pointwise,
            listwise,
            policy_timing_ms=0.25,
            clock=FixedClock(),
        )
        == "created"
    )
    assert len(test_retriever.calls) == 21
    raw_path = experiment / "raw/test-raw.json"
    raw_bytes = raw_path.read_bytes()
    raw = load_json(raw_path)
    serialized_raw = raw_path.read_text(encoding="utf-8")
    for forbidden in (
        "expected_status",
        "expected_canonical_uuid",
        "winner",
        "accuracy",
        "metrics",
    ):
        assert forbidden not in serialized_raw
    rows = raw["rows"]
    assert isinstance(rows, list) and len(rows) == 21
    for row in rows:
        assert isinstance(row, dict)
        candidates = row["candidates"]
        arms = row["arms"]
        assert isinstance(candidates, list) and isinstance(arms, dict)
        identities = [candidate["canonical_uuid"] for candidate in candidates]
        assert all(
            [record["canonical_uuid"] for record in arms[arm]] == identities
            for arm in ("rrf", "neural_pointwise", "neural_listwise")
        )

    pointwise_calls = len(pointwise.calls)
    listwise_calls = len(listwise.calls)
    assert (
        collect_test_once(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            lambda: state["hash"],
            backend,
            test_retriever,
            pointwise,
            listwise,
            clock=FixedClock(),
        )
        == "unchanged"
    )
    assert len(test_retriever.calls) == 21
    assert len(pointwise.calls) == pointwise_calls
    assert len(listwise.calls) == listwise_calls

    protected = {
        path: path.read_bytes()
        for path in (
            raw_path,
            experiment / "raw/test-raw-manifest.json",
            experiment / "models/pointwise-manifest.json",
            experiment / "models/listwise-manifest.json",
            experiment / "models/listwise-model.safetensors",
        )
    }
    assert (
        score_test_once(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            lambda: state["hash"],
            backend,
        )
        == "created"
    )
    assert all(path.read_bytes() == content for path, content in protected.items())
    report_dir = tmp_path / REPORT_DIRECTORY
    report = load_json(report_dir / "comparison.json")
    assert report["winner"] is None
    assert report["matched_test_denominator"] == 12
    assert report["one_case_top1_increment"] == pytest.approx(1 / 12)
    markdown = (report_dir / "comparison.md").read_text(encoding="utf-8")
    assert "12 matched ranking targets" in markdown
    assert "production accuracy" in markdown
    top1 = report["arms"]["rrf"]["metrics"]["top1_accuracy"]["value"]
    assert f'data-top1="{top1:.12f}"' in (report_dir / "reranker-comparison.svg").read_text(
        encoding="utf-8"
    )
    assert (
        score_test_once(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            lambda: state["hash"],
            backend,
        )
        == "unchanged"
    )
    assert raw_path.read_bytes() == raw_bytes

    chart = report_dir / "accuracy-latency.svg"
    chart.write_text("<svg>tampered</svg>\n", encoding="utf-8")
    with pytest.raises(ValueError, match="report file drift"):
        score_test_once(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            lambda: state["hash"],
            backend,
        )
    assert chart.read_text(encoding="utf-8") == "<svg>tampered</svg>\n"


def test_test_collection_persists_one_error_without_retry_and_cannot_win(tmp_path: Path) -> None:
    sources, state, backend, experiment = fitted_fixture(tmp_path)
    retriever = FailingOnceRetriever(load_catalog(sources.catalog), fail_call=7)
    assert (
        collect_test_once(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            lambda: state["hash"],
            backend,
            retriever,
            FakePointwiseScorer(state),
            FakeListwiseScorer(),
            clock=FixedClock(),
        )
        == "created"
    )
    assert len(retriever.calls) == 21
    manifest = load_json(experiment / "raw/test-raw-manifest.json")
    assert manifest["retrieval_call_count"] == 21
    assert manifest["retrieval_error_count"] == 1
    raw = load_json(experiment / "raw/test-raw.json")
    errored = [row for row in raw["rows"] if row["error"] is not None]
    assert len(errored) == 1
    assert errored[0]["candidates"] == []

    assert (
        score_test_once(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            lambda: state["hash"],
            backend,
        )
        == "created"
    )
    report = load_json(tmp_path / REPORT_DIRECTORY / "comparison.json")
    assert report["winner"] is None
    for arm in ("neural_pointwise", "neural_listwise"):
        gates = {gate["name"]: gate for gate in report["arms"][arm]["gates"]}
        assert gates["collection_errors_equal_zero"]["passed"] is False


def test_test_collection_rejects_partial_raw_phase_without_retrieval(tmp_path: Path) -> None:
    sources, state, backend, experiment = fitted_fixture(tmp_path)
    raw_dir = experiment / "raw"
    raw_dir.mkdir()
    (raw_dir / "test-raw.json").write_text("{}", encoding="utf-8")
    retriever = RecordingRetriever(load_catalog(sources.catalog))

    with pytest.raises(ValueError, match="partial"):
        collect_test_once(
            tmp_path,
            sources,
            MODEL_BINDING,
            DEPENDENCIES,
            lambda: state["hash"],
            backend,
            retriever,
            FakePointwiseScorer(state),
            FakeListwiseScorer(),
            clock=FixedClock(),
        )

    assert retriever.calls == []


@pytest.mark.parametrize(
    ("metric_name", "arm_value", "latency", "errors"),
    [
        ("top1_accuracy", 0.54, 100.0, 0),
        ("hard_negative_accuracy", 0.49, 100.0, 0),
        ("mrr_at_10", 0.59, 100.0, 0),
        ("recall_at_25", 0.99, 100.0, 0),
        ("top1_accuracy", 0.60, 1500.01, 0),
        ("top1_accuracy", 0.60, 100.0, 1),
    ],
)
def test_each_predeclared_gate_failure_forces_null_recommendation(
    metric_name: str,
    arm_value: float,
    latency: float,
    errors: int,
) -> None:
    baseline = {
        "top1_accuracy": MetricValue(6, 12, 0.5),
        "hard_negative_accuracy": MetricValue(2, 4, 0.5),
        "mrr_at_10": MetricValue(7.2, 12, 0.6),
        "recall_at_10": MetricValue(10, 12, 10 / 12),
        "recall_at_25": MetricValue(12, 12, 1.0),
    }
    arm = dict(baseline)
    arm.update(
        {
            "top1_accuracy": MetricValue(7.2, 12, 0.6),
            "hard_negative_accuracy": MetricValue(2.4, 4, 0.6),
            "mrr_at_10": MetricValue(7.8, 12, 0.65),
        }
    )
    original = arm[metric_name]
    arm[metric_name] = MetricValue(original.numerator, original.denominator, arm_value)
    gates = list(
        evaluate_arm_gates(
            baseline,
            arm,
            resolver_p95_ms=latency,
            error_count=errors,
        )
    )
    arm_payload = {
        "metrics": {name: {"value": value.value} for name, value in arm.items()},
        "latency_ms": {"resolver_p95": latency},
        "gates": gates,
    }
    assert (
        select_recommendation({"neural_pointwise": arm_payload, "neural_listwise": arm_payload})
        is None
    )


def test_recommendation_tie_break_is_deterministic_and_prefers_simpler_arm() -> None:
    def result(hard: float, top1: float, mrr: float, p95: float) -> dict[str, object]:
        return {
            "metrics": {
                "hard_negative_accuracy": {"value": hard},
                "top1_accuracy": {"value": top1},
                "mrr_at_10": {"value": mrr},
            },
            "latency_ms": {"resolver_p95": p95},
            "gates": [{"passed": True}],
        }

    assert (
        select_recommendation(
            {
                "neural_pointwise": result(0.75, 0.67, 0.70, 200),
                "neural_listwise": result(0.75, 0.67, 0.70, 200),
            }
        )
        == "neural_pointwise"
    )
    assert (
        select_recommendation(
            {
                "neural_pointwise": result(0.75, 0.67, 0.70, 200),
                "neural_listwise": result(0.80, 0.67, 0.70, 300),
            }
        )
        == "neural_listwise"
    )


def test_installed_cli_help_lists_exactly_six_mutually_exclusive_phases() -> None:
    executable = ROOT / ".venv/bin/pvr-compare-neural-rerankers"
    completed = subprocess.run(
        [str(executable), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    phases = {
        "--acquire-model",
        "--freeze-protocol",
        "--fit",
        "--collect-test",
        "--score",
        "--check",
    }
    listed = {
        line.strip().split()[0]
        for line in completed.stdout.splitlines()
        if line.startswith("  --") and line.strip().split()[0] in phases
    }
    assert listed == phases
    assert "(--acquire-model | --freeze-protocol | --fit | --collect-test | --score | --check)" in (
        " ".join(completed.stdout.split())
    )
