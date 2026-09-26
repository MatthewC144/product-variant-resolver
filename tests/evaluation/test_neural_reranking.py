from __future__ import annotations

import copy
import json
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from uuid import UUID

import pytest

from product_variant_resolver import neural_reranking
from product_variant_resolver.neural_reranking import (
    ARMS,
    FEATURE_SCHEMA,
    LISTWISE_ARCHITECTURE,
    LISTWISE_INPUT_DIM,
    LISTWISE_LEARNING_RATE,
    LISTWISE_PATIENCE,
    LISTWISE_SEED,
    LISTWISE_WEIGHT_DECAY,
    NORMALIZED_FEATURE_INDICES,
    POINTWISE_LICENSE,
    POINTWISE_MODEL_ID,
    POINTWISE_REVISION,
    BenchmarkContract,
    CandidatePoolRow,
    CandidateTextFields,
    FrozenCandidate,
    FrozenSignals,
    ListwiseExample,
    ListwiseTrainingResult,
    LocalPointwiseScorer,
    ScoredCase,
    TrainingEpoch,
    acquire_pointwise_model,
    build_candidate_set_reranker,
    candidate_feature_vector,
    canonical_json_bytes,
    configure_torch_determinism,
    fit_train_feature_normalizer,
    load_pointwise_model_config,
    metrics_by_failure_category,
    paired_rank_transitions,
    rank_scores,
    ranking_metrics,
    render_candidate_text,
    save_listwise_checkpoint,
    score_listwise_features,
    select_early_stopping_epoch,
    sha256_bytes,
    train_listwise_model,
    validate_benchmark_contract,
    validate_candidate_pool_payload,
    validate_label_blind_payload,
    validate_listwise_checkpoint,
    validate_local_pointwise_model,
    validate_raw_test_payload,
)

ROOT = Path(__file__).resolve().parents[2]
MODEL_CONFIG = ROOT / "config/neural-reranker-comparison-v1.json"


def fake_snapshot_downloader(calls: list[dict[str, object]]):
    def download(
        *,
        model_id: str,
        revision: str,
        allowed_files: tuple[str, ...],
        cache_dir: Path,
    ) -> Path:
        calls.append(
            {
                "model_id": model_id,
                "revision": revision,
                "allowed_files": allowed_files,
                "cache_dir": cache_dir,
            }
        )
        snapshot = cache_dir / "snapshot"
        snapshot.mkdir()
        for index, name in enumerate(allowed_files):
            (snapshot / name).write_bytes(f"fixture-{index}-{name}".encode())
        return snapshot

    return download


def candidate(
    number: int,
    *,
    rrf_rank: int,
    rrf_score: float,
    matches: tuple[str, ...] = (),
    conflicts: tuple[str, ...] = (),
    source_ranks: tuple[tuple[str, int], ...] = (("sparse", 1), ("dense", 2)),
) -> FrozenCandidate:
    return FrozenCandidate(
        canonical_uuid=str(UUID(int=number)),
        canonical_id=f"hot-wheels-test-{number}",
        text=CandidateTextFields(
            brand="Hot Wheels",
            casting=f"Test Car {number}",
            release_year=2025,
            series="Mainline",
            color="Red",
            collector_number=str(number),
            series_position=f"{number}/250",
            edition="First Edition",
            aliases=(f"Car {number}", " HW Test "),
            identifiers=(f"HW-{number}",),
        ),
        source_ranks=source_ranks,
        source_scores=(("sparse", 4.5), ("dense", 0.8)),
        structured_matches=matches,
        structured_conflicts=conflicts,
        rrf_rank=rrf_rank,
        rrf_score=rrf_score,
    )


def scored_case(
    number: int,
    *,
    category: str,
    hard_negative: bool,
    rrf: int | None,
    pointwise: int | None,
    listwise: int | None,
) -> ScoredCase:
    return ScoredCase(
        case_id=f"case-{number:03d}",
        failure_category=category,
        hard_negative=hard_negative,
        expected_canonical_uuid=str(UUID(int=number)),
        target_ranks=tuple(zip(ARMS, (rrf, pointwise, listwise), strict=True)),
    )


def test_render_candidate_text_is_stable_and_allowlisted() -> None:
    rendered = render_candidate_text(candidate(1, rrf_rank=1, rrf_score=0.03).text)

    assert rendered == (
        "brand=hot wheels | casting=test car 1 | year=2025 | series=mainline | "
        "color=red | collector=1 | series_position=1/250 | edition=first edition | "
        "aliases=car 1; hw test | identifiers=hw-1"
    )
    assert "canonical" not in rendered
    assert "uuid" not in rendered
    assert "provenance" not in rendered


def test_feature_vector_has_exact_declared_order_and_missing_rank_behavior() -> None:
    item = candidate(
        1,
        rrf_rank=2,
        rrf_score=0.031,
        matches=("year", "color"),
        conflicts=("series",),
        source_ranks=(("sparse", 4), ("structured", 2)),
    )

    vector = candidate_feature_vector(item, pointwise_logit=1.25)

    assert len(vector) == len(FEATURE_SCHEMA) == 21
    assert vector == pytest.approx(
        (
            1.25,
            0.031,
            0.5,
            1.0,
            0.0,
            1.0,
            0.25,
            0.0,
            0.5,
            1.0,
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            0.4,
            0.2,
        )
    )
    with pytest.raises(ValueError, match="finite"):
        candidate_feature_vector(item, pointwise_logit=math.nan)


def test_candidate_and_pool_contracts_reject_invalid_identity_and_rank_state() -> None:
    first = candidate(1, rrf_rank=1, rrf_score=0.03)
    second = candidate(2, rrf_rank=2, rrf_score=0.02)
    row = CandidatePoolRow(
        case_id="case-001",
        split="train",
        query="Hot Wheels Test Car",
        signals=FrozenSignals(normalized_title="hot wheels test car", tokens=("hot", "wheels")),
        retrieval_timings_ms=(("sparse", 1.0), ("dense", 2.0)),
        candidates=(first, second),
    )
    assert row.candidates == (first, second)

    with pytest.raises(ValueError, match="duplicate identities"):
        CandidatePoolRow(
            case_id="case-001",
            split="train",
            query="query",
            signals=row.signals,
            retrieval_timings_ms=(),
            candidates=(first, first),
        )
    with pytest.raises(ValueError, match="ordered and contiguous"):
        CandidatePoolRow(
            case_id="case-001",
            split="train",
            query="query",
            signals=row.signals,
            retrieval_timings_ms=(),
            candidates=(second,),
        )


def test_rank_scores_uses_score_then_rrf_then_uuid_without_using_uuid_as_feature() -> None:
    candidates = (
        candidate(3, rrf_rank=3, rrf_score=0.01),
        candidate(2, rrf_rank=1, rrf_score=0.03),
        candidate(1, rrf_rank=1, rrf_score=0.03),
    )

    ranked = rank_scores(candidates, (0.9, 0.5, 0.5))

    assert [item.canonical_uuid for item in ranked] == [
        str(UUID(int=3)),
        str(UUID(int=1)),
        str(UUID(int=2)),
    ]
    assert [item.rank for item in ranked] == [1, 2, 3]
    with pytest.raises(ValueError, match="counts differ"):
        rank_scores(candidates, (0.5,))


def test_metrics_keep_raw_denominators_categories_and_paired_transitions() -> None:
    cases = (
        scored_case(
            1,
            category="identifier_noise",
            hard_negative=True,
            rrf=2,
            pointwise=1,
            listwise=1,
        ),
        scored_case(
            2,
            category="marketplace_noise",
            hard_negative=False,
            rrf=1,
            pointwise=3,
            listwise=None,
        ),
        scored_case(
            3,
            category="marketplace_noise",
            hard_negative=False,
            rrf=None,
            pointwise=None,
            listwise=4,
        ),
    )

    metrics = ranking_metrics(cases, "neural_pointwise")
    assert metrics["top1_accuracy"].numerator == 1
    assert metrics["top1_accuracy"].denominator == 3
    assert metrics["top1_accuracy"].value == pytest.approx(1 / 3)
    assert metrics["mrr_at_10"].numerator == pytest.approx(1 + 1 / 3)
    assert metrics["hard_negative_accuracy"].value == 1
    assert metrics["recall_at_25"].value == pytest.approx(2 / 3)

    grouped = metrics_by_failure_category(cases, "neural_pointwise")
    assert list(grouped) == ["identifier_noise", "marketplace_noise"]
    assert grouped["marketplace_noise"]["top1_accuracy"].denominator == 2

    transitions = paired_rank_transitions(cases, "neural_pointwise")
    assert [item.direction for item in transitions] == ["improved", "regressed", "unchanged"]
    listwise = paired_rank_transitions(cases, "neural_listwise")
    assert [item.direction for item in listwise] == ["improved", "regressed", "improved"]


def test_recursive_blind_validators_reject_labels_results_and_pool_scores() -> None:
    label_blind = {
        "rows": [
            {
                "case_id": "case-001",
                "candidates": [{"canonical_uuid": str(UUID(int=1)), "rrf_score": 0.03}],
            }
        ]
    }
    validate_label_blind_payload(label_blind)
    validate_candidate_pool_payload(label_blind)
    validate_raw_test_payload({"rows": [{"pointwise_score": 0.5, "listwise_score": 0.6}]})

    for forbidden in (
        {"rows": [{"expected_canonical_uuid": str(UUID(int=1))}]},
        {"rows": [{"nested": {"failure_category": "identifier_noise"}}]},
        {"rows": [{"hard_negative": True}]},
        {"rows": [{"nested": {"winner": "neural_listwise"}}]},
        {"rows": [{"metrics": {"top1_accuracy": 1.0}}]},
    ):
        with pytest.raises(ValueError, match="forbidden"):
            validate_label_blind_payload(forbidden)

    with pytest.raises(ValueError, match="forbidden"):
        validate_candidate_pool_payload({"rows": [{"pointwise_logit": 0.5}]})
    with pytest.raises(ValueError, match="non-finite"):
        validate_raw_test_payload({"rows": [{"pointwise_score": math.inf}]})


def test_canonical_json_and_hash_are_order_independent_and_reject_nan() -> None:
    first = canonical_json_bytes({"b": [2, 3], "a": "車"})
    second = canonical_json_bytes({"a": "車", "b": [2, 3]})

    assert first == second == b'{"a":"\xe8\xbb\x8a","b":[2,3]}\n'
    assert sha256_bytes(first) == sha256_bytes(second)
    with pytest.raises(ValueError, match="JSON compliant"):
        canonical_json_bytes({"score": math.nan})


def test_committed_fixture_satisfies_exact_counts_and_family_isolation() -> None:
    payload = json.loads((ROOT / "data/benchmark.json").read_text(encoding="utf-8"))

    contract = validate_benchmark_contract(payload)

    assert isinstance(contract, BenchmarkContract)
    assert contract.total_count == 100
    assert dict(contract.split_counts) == {"train": 58, "dev": 21, "test": 21}
    assert dict(contract.hard_negative_counts) == {"train": 34, "dev": 13, "test": 13}
    assert dict(contract.matched_hard_negative_counts) == {
        "train": 12,
        "dev": 4,
        "test": 4,
    }
    assert contract.family_count > 0

    tampered = copy.deepcopy(payload)
    tampered["cases"][0]["split"] = "test"
    with pytest.raises(ValueError, match="leaks across splits|split counts"):
        validate_benchmark_contract(tampered)


def test_import_does_not_load_optional_neural_dependencies() -> None:
    assert "torch" not in sys.modules
    assert "sentence_transformers" not in sys.modules


def test_pointwise_config_pins_model_revision_license_and_offline_runtime(tmp_path: Path) -> None:
    config = load_pointwise_model_config(MODEL_CONFIG)

    assert config.model_id == POINTWISE_MODEL_ID
    assert config.revision == POINTWISE_REVISION
    assert config.license == POINTWISE_LICENSE
    assert config.local_files_only is True
    assert config.trust_remote_code is False
    assert config.device == "cpu"
    assert config.dtype == "float32"
    assert config.num_labels == 1
    assert config.max_length == 128
    assert config.allowed_files == config.required_files
    assert "model.safetensors" in config.required_files
    assert all(
        not name.endswith((".bin", ".pkl", ".pickle", ".pt", ".pth"))
        for name in config.allowed_files
    )

    payload = json.loads(MODEL_CONFIG.read_text(encoding="utf-8"))
    mutations = (
        ("revision", "main", "immutable revision"),
        ("license", "unknown", "Apache-2.0"),
        ("trust_remote_code", True, "trust_remote_code"),
        ("local_files_only", False, "local_files_only"),
    )
    for key, value, message in mutations:
        tampered = copy.deepcopy(payload)
        tampered["pointwise"][key] = value
        path = tmp_path / f"{key}.json"
        path.write_text(json.dumps(tampered), encoding="utf-8")
        with pytest.raises(ValueError, match=message):
            load_pointwise_model_config(path)


def test_fake_acquisition_binds_provenance_hashes_and_is_idempotent(tmp_path: Path) -> None:
    config = load_pointwise_model_config(MODEL_CONFIG)
    destination = tmp_path / "pointwise"
    calls: list[dict[str, object]] = []

    status = acquire_pointwise_model(
        config,
        destination,
        confirm_license=True,
        downloader=fake_snapshot_downloader(calls),
    )

    assert status == "created"
    assert len(calls) == 1
    assert calls[0]["model_id"] == POINTWISE_MODEL_ID
    assert calls[0]["revision"] == POINTWISE_REVISION
    manifest = validate_local_pointwise_model(config, destination)
    assert manifest.model_id == POINTWISE_MODEL_ID
    assert manifest.revision == POINTWISE_REVISION
    assert manifest.license == POINTWISE_LICENSE
    assert manifest.config_sha256 == config.config_sha256
    assert tuple(item.path for item in manifest.files) == config.required_files
    assert all(len(item.sha256) == 64 and item.size > 0 for item in manifest.files)

    def should_not_download(**_kwargs: object) -> Path:
        raise AssertionError("valid existing model must not redownload")

    assert (
        acquire_pointwise_model(
            config,
            destination,
            confirm_license=True,
            downloader=should_not_download,
        )
        == "unchanged"
    )


def test_acquisition_requires_license_and_rejects_unexpected_pickle(tmp_path: Path) -> None:
    config = load_pointwise_model_config(MODEL_CONFIG)
    calls: list[dict[str, object]] = []
    destination = tmp_path / "pointwise"

    with pytest.raises(ValueError, match="license confirmation"):
        acquire_pointwise_model(
            config,
            destination,
            confirm_license=False,
            downloader=fake_snapshot_downloader(calls),
        )
    assert calls == []
    assert not destination.exists()

    valid_downloader = fake_snapshot_downloader(calls)

    def unsafe_downloader(**kwargs: object) -> Path:
        snapshot = valid_downloader(**kwargs)  # type: ignore[arg-type]
        (snapshot / "pytorch_model.bin").write_bytes(b"pickle-like-fixture")
        return snapshot

    with pytest.raises(ValueError, match="allowlist"):
        acquire_pointwise_model(
            config,
            destination,
            confirm_license=True,
            downloader=unsafe_downloader,
        )
    assert not destination.exists()


def test_local_model_validation_rejects_missing_hash_and_tampered_bytes(tmp_path: Path) -> None:
    config = load_pointwise_model_config(MODEL_CONFIG)
    destination = tmp_path / "pointwise"
    acquire_pointwise_model(
        config,
        destination,
        confirm_license=True,
        downloader=fake_snapshot_downloader([]),
    )
    manifest_path = destination / "manifest.json"
    original = manifest_path.read_bytes()
    payload = json.loads(original)
    del payload["files"][0]["sha256"]
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="file record"):
        validate_local_pointwise_model(config, destination)

    manifest_path.write_bytes(original)
    (destination / config.required_files[0]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="hashes or sizes"):
        validate_local_pointwise_model(config, destination)


def test_missing_optional_dependency_fails_before_project_artifact_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = load_pointwise_model_config(MODEL_CONFIG)
    destination = tmp_path / "not-created" / "pointwise"

    def missing_import(_name: str) -> object:
        raise ImportError("fixture missing dependency")

    monkeypatch.setattr(neural_reranking.importlib, "import_module", missing_import)
    with pytest.raises(RuntimeError, match=r"product-variant-resolver\[reranking\]"):
        acquire_pointwise_model(config, destination, confirm_license=True)
    assert not destination.parent.exists()


def test_offline_pointwise_loader_uses_secure_v341_arguments_and_one_batch(
    tmp_path: Path,
) -> None:
    config = load_pointwise_model_config(MODEL_CONFIG)
    destination = tmp_path / "pointwise"
    acquire_pointwise_model(
        config,
        destination,
        confirm_license=True,
        downloader=fake_snapshot_downloader([]),
    )
    factory_calls: list[tuple[str, dict[str, object]]] = []

    class FakeModel:
        def __init__(self) -> None:
            self.calls: list[tuple[tuple[tuple[str, str], ...], dict[str, object]]] = []

        def predict(
            self,
            sentences: Sequence[tuple[str, str]],
            *,
            batch_size: int,
            show_progress_bar: bool,
            convert_to_numpy: bool,
        ) -> object:
            pairs = tuple(sentences)
            self.calls.append(
                (
                    pairs,
                    {
                        "batch_size": batch_size,
                        "show_progress_bar": show_progress_bar,
                        "convert_to_numpy": convert_to_numpy,
                    },
                )
            )
            return [len(query) * 1000 + len(candidate) for query, candidate in pairs]

    fake_model = FakeModel()

    def factory(model_name: str, **kwargs: object) -> FakeModel:
        factory_calls.append((model_name, kwargs))
        return fake_model

    scorer = LocalPointwiseScorer.load(
        config,
        destination,
        factory=factory,
        torch_dtype="fixture-float32",
        batch_size=25,
    )
    pairs = (("query-a", "candidate-one"), ("longer-query", "candidate-two"))
    first = scorer.score_pairs(pairs)
    second_pairs = tuple(reversed(pairs))
    second = scorer.score_pairs(second_pairs)

    assert len(factory_calls) == 1
    model_name, kwargs = factory_calls[0]
    assert model_name == str(destination)
    assert kwargs["local_files_only"] is True
    assert kwargs["trust_remote_code"] is False
    assert kwargs["device"] == "cpu"
    assert kwargs["num_labels"] == 1
    assert kwargs["max_length"] == 128
    assert kwargs["automodel_args"] == {
        "torch_dtype": "fixture-float32",
        "use_safetensors": True,
    }
    assert "tokenizer_args" not in kwargs
    assert "config_args" not in kwargs
    assert len(fake_model.calls) == 2
    assert all(call[1]["batch_size"] == 25 for call in fake_model.calls)
    assert dict(zip(pairs, first, strict=True)) == dict(zip(second_pairs, second, strict=True))


def test_pointwise_scorer_rejects_wrong_count_and_nonfinite_values() -> None:
    class InvalidModel:
        def __init__(self, result: object) -> None:
            self.result = result

        def predict(
            self,
            _sentences: Sequence[tuple[str, str]],
            *,
            batch_size: int,
            show_progress_bar: bool,
            convert_to_numpy: bool,
        ) -> object:
            del batch_size, show_progress_bar, convert_to_numpy
            return self.result

    pairs = (("query", "candidate"),)
    with pytest.raises(ValueError, match="wrong score count"):
        LocalPointwiseScorer("fixture", InvalidModel([])).score_pairs(pairs)
    with pytest.raises(ValueError, match="finite"):
        LocalPointwiseScorer("fixture", InvalidModel([math.nan])).score_pairs(pairs)


def feature_row(pointwise: float, rrf: float, marker: float = 0.0) -> tuple[float, ...]:
    return (pointwise, rrf, marker, *((0.0,) * (len(FEATURE_SCHEMA) - 3)))


def test_train_normalizer_only_transforms_two_approved_fields() -> None:
    train_rows = (
        feature_row(1.0, 0.1, 11.0),
        feature_row(2.0, 0.2, 12.0),
        feature_row(3.0, 0.3, 13.0),
    )

    normalizer = fit_train_feature_normalizer(train_rows)
    transformed = normalizer.transform(feature_row(2.0, 0.2, 99.0))

    assert normalizer.feature_schema == FEATURE_SCHEMA
    assert normalizer.normalized_indices == NORMALIZED_FEATURE_INDICES == (0, 1)
    assert normalizer.means == pytest.approx((2.0, 0.2))
    assert normalizer.standard_deviations == pytest.approx((math.sqrt(2 / 3), math.sqrt(0.02 / 3)))
    assert transformed[:2] == pytest.approx((0.0, 0.0))
    assert transformed[2:] == feature_row(2.0, 0.2, 99.0)[2:]

    # Dev/Test-sized values can be transformed but have no API path into fitting.
    dev_or_test = normalizer.transform(feature_row(1_000_000.0, 10_000.0, 7.0))
    assert normalizer.means == pytest.approx((2.0, 0.2))
    assert dev_or_test[2] == 7.0

    constant = fit_train_feature_normalizer((feature_row(1.0, 0.5),) * 2)
    assert constant.standard_deviations == (1.0, 1.0)
    with pytest.raises(ValueError, match="21-field"):
        normalizer.transform((1.0, 2.0))


def test_listwise_examples_and_early_stopping_are_deterministic_and_tie_early() -> None:
    example = ListwiseExample(
        features=(feature_row(1.0, 0.2), feature_row(0.0, 0.1)),
        target_index=0,
    )
    assert example.target_index == 0
    with pytest.raises(ValueError, match="target_index"):
        ListwiseExample(features=example.features, target_index=2)

    metrics = [0.4, 0.6, *([0.6] * LISTWISE_PATIENCE)]
    history = tuple(
        TrainingEpoch(epoch=index, train_loss=1.0 / index, dev_mrr_at_10=metric)
        for index, metric in enumerate(metrics, start=1)
    )

    first = select_early_stopping_epoch(history)
    second = select_early_stopping_epoch(history)

    assert first == second
    assert first.selected_epoch == 2
    assert first.selected_dev_mrr_at_10 == 0.6
    assert first.stop_epoch == 2 + LISTWISE_PATIENCE
    with pytest.raises(ValueError, match="contiguous"):
        select_early_stopping_epoch((TrainingEpoch(2, 1.0, 0.5),))


def test_listwise_architecture_contract_has_no_position_channel() -> None:
    architecture = dict(LISTWISE_ARCHITECTURE)

    assert architecture == {
        "input_dim": 21,
        "hidden_dim": 32,
        "attention_heads": 4,
        "feedforward_dim": 64,
        "encoder_layers": 1,
        "dropout": 0.0,
        "positional_embeddings": False,
    }
    assert LISTWISE_INPUT_DIM == len(FEATURE_SCHEMA)
    assert LISTWISE_SEED == 20260924


def test_listwise_builder_wires_exact_layers_without_importing_torch() -> None:
    calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    class Module:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def to(self, **kwargs: object) -> Module:
            calls.append(("to", (), kwargs))
            return self

    def layer(name: str) -> type[Module]:
        class Layer(Module):
            def __init__(self, *args: object, **kwargs: object) -> None:
                super().__init__()
                calls.append((name, args, kwargs))

        return Layer

    fake_nn = SimpleNamespace(
        Module=Module,
        Sequential=layer("Sequential"),
        Linear=layer("Linear"),
        GELU=layer("GELU"),
        LayerNorm=layer("LayerNorm"),
        TransformerEncoderLayer=layer("TransformerEncoderLayer"),
        TransformerEncoder=layer("TransformerEncoder"),
    )
    fake_torch = SimpleNamespace(nn=fake_nn, float32="float32")

    model = build_candidate_set_reranker(torch_module=fake_torch)

    assert isinstance(model, Module)
    assert [call for call in calls if call[0] == "Linear"] == [
        ("Linear", (21, 32), {}),
        ("Linear", (32, 1), {}),
    ]
    encoder_layer = next(call for call in calls if call[0] == "TransformerEncoderLayer")
    assert encoder_layer[2] == {
        "d_model": 32,
        "nhead": 4,
        "dim_feedforward": 64,
        "dropout": 0.0,
        "batch_first": True,
        "device": "cpu",
        "dtype": "float32",
    }
    encoder = next(call for call in calls if call[0] == "TransformerEncoder")
    assert encoder[2] == {"num_layers": 1, "enable_nested_tensor": False}
    assert not any("position" in name.lower() for name, _args, _kwargs in calls)
    assert calls[-1] == ("to", (), {"device": "cpu", "dtype": "float32"})


def test_listwise_missing_optional_dependency_is_actionable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def missing_import(name: str) -> object:
        if name in {"torch", "safetensors.torch"}:
            raise ImportError(f"fixture missing {name}")
        return importlib.import_module(name)

    import importlib

    monkeypatch.setattr(neural_reranking.importlib, "import_module", missing_import)
    with pytest.raises(RuntimeError, match=r"product-variant-resolver\[reranking\]"):
        build_candidate_set_reranker()


def test_listwise_checkpoint_binds_schema_hash_shapes_and_normalizer(tmp_path: Path) -> None:
    class FakeTensor:
        def __init__(self, shape: tuple[int, ...]) -> None:
            self.shape = shape

        def detach(self) -> FakeTensor:
            return self

        def cpu(self) -> FakeTensor:
            return self

        def contiguous(self) -> FakeTensor:
            return self

    class FakeModel:
        def state_dict(self) -> dict[str, FakeTensor]:
            return {
                "candidate_encoder.0.weight": FakeTensor((32, 21)),
                "score_head.weight": FakeTensor((1, 32)),
            }

    class FakeSafeTensors:
        def __init__(self) -> None:
            self.state: Mapping[str, object] = {}

        def save_file(
            self,
            tensors: Mapping[str, object],
            filename: str,
            metadata: Mapping[str, str] | None = None,
        ) -> None:
            self.state = dict(tensors)
            payload = {
                "metadata": dict(metadata or {}),
                "shapes": {
                    name: list(cast(FakeTensor, tensor).shape) for name, tensor in tensors.items()
                },
            }
            Path(filename).write_bytes(canonical_json_bytes(payload))

        def load_file(self, filename: str, device: str = "cpu") -> Mapping[str, object]:
            assert Path(filename).is_file()
            assert device == "cpu"
            return self.state

    normalizer = fit_train_feature_normalizer((feature_row(1.0, 0.1), feature_row(3.0, 0.3)))
    result = ListwiseTrainingResult(
        model=FakeModel(),
        normalizer=normalizer,
        history=(TrainingEpoch(1, 0.5, 1.0),),
        selected_epoch=1,
        selected_dev_mrr_at_10=1.0,
    )
    checkpoint = tmp_path / "listwise-model.safetensors"
    adapter = FakeSafeTensors()

    manifest_path = save_listwise_checkpoint(checkpoint, result, adapter=adapter)
    manifest = validate_listwise_checkpoint(checkpoint, adapter=adapter)

    assert manifest_path.name == "listwise-model.manifest.json"
    assert manifest.feature_schema == FEATURE_SCHEMA
    assert manifest.architecture == LISTWISE_ARCHITECTURE
    assert manifest.seed == LISTWISE_SEED
    assert manifest.selected_epoch == 1
    assert manifest.normalizer == normalizer
    assert dict(manifest.tensor_shapes) == {
        "candidate_encoder.0.weight": (32, 21),
        "score_head.weight": (1, 32),
    }
    assert len(manifest.checkpoint_sha256) == 64

    original_manifest = manifest_path.read_bytes()
    payload = json.loads(original_manifest)
    payload["feature_schema"][0] = "drifted"
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="feature schema drift"):
        validate_listwise_checkpoint(checkpoint, adapter=adapter)

    manifest_path.write_bytes(original_manifest)
    checkpoint.write_bytes(checkpoint.read_bytes() + b"tamper")
    with pytest.raises(ValueError, match="file hash drift"):
        validate_listwise_checkpoint(checkpoint, adapter=adapter)


def test_optional_torch_network_is_permutation_equivariant_and_padding_safe() -> None:
    torch = pytest.importorskip("torch", reason="reranking extra is installed only at NRC-T7")
    configure_torch_determinism(torch)
    model = build_candidate_set_reranker(torch_module=torch)
    model.eval()
    features = torch.randn(1, 4, LISTWISE_INPUT_DIM, dtype=torch.float32)
    mask = torch.zeros((1, 4), dtype=torch.bool)
    permutation = torch.tensor([2, 0, 3, 1], dtype=torch.long)

    with torch.no_grad():
        original = model(features, mask)[0]
        permuted = model(features[:, permutation], mask[:, permutation])[0]
        padded_features = torch.cat(
            (features, torch.randn(1, 3, LISTWISE_INPUT_DIM, dtype=torch.float32) * 1000), dim=1
        )
        padded_mask = torch.tensor([[False, False, False, False, True, True, True]])
        padded = model(padded_features, padded_mask)[0, :4]

    assert torch.allclose(permuted, original[permutation], atol=1e-6, rtol=0)
    assert torch.allclose(padded, original, atol=1e-6, rtol=0)


def test_optional_torch_step_reduces_loss_and_seed_repeats_selection() -> None:
    torch = pytest.importorskip("torch", reason="reranking extra is installed only at NRC-T7")
    configure_torch_determinism(torch)
    model = build_candidate_set_reranker(torch_module=torch)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=LISTWISE_LEARNING_RATE, weight_decay=LISTWISE_WEIGHT_DECAY
    )
    features = torch.zeros((1, 2, LISTWISE_INPUT_DIM), dtype=torch.float32)
    features[0, 0, 0] = 5.0
    features[0, 1, 0] = -5.0
    mask = torch.zeros((1, 2), dtype=torch.bool)
    target = torch.tensor([0], dtype=torch.long)
    model.train()
    before = torch.nn.functional.cross_entropy(model(features, mask), target)
    optimizer.zero_grad(set_to_none=True)
    before.backward()
    optimizer.step()
    after = torch.nn.functional.cross_entropy(model(features, mask), target)
    assert float(after.item()) < float(before.detach().item())

    train = (
        ListwiseExample((feature_row(3.0, 0.3), feature_row(-2.0, 0.1)), 0),
        ListwiseExample((feature_row(-1.0, 0.1), feature_row(2.0, 0.3)), 1),
    )
    dev = (ListwiseExample((feature_row(4.0, 0.4), feature_row(-3.0, 0.1)), 0),)
    first = train_listwise_model(train, dev, torch_module=torch)
    second = train_listwise_model(train, dev, torch_module=torch)
    assert first.selected_epoch == second.selected_epoch
    assert first.selected_dev_mrr_at_10 == second.selected_dev_mrr_at_10
    first_scores = score_listwise_features(
        first.model, dev[0].features, first.normalizer, torch_module=torch
    )
    second_scores = score_listwise_features(
        second.model, dev[0].features, second.normalizer, torch_module=torch
    )
    assert first_scores == pytest.approx(second_scores, abs=1e-7, rel=0)
