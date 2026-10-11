from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from product_variant_resolver.config import Settings
from product_variant_resolver.rerank import NeuralPointwiseReranker
from product_variant_resolver.serper_dual_source_evaluation import (
    DEVELOPMENT_BASELINE,
    FROZEN_SPLIT_SHA256,
    RAW_POINTWISE_DEVELOPMENT,
    RAW_POINTWISE_FINAL_TEST,
    SDSE_T4_OWNER_AUTHORIZATION,
    FrozenGroupedSplit,
    SerperDualSourceDataset,
    build_year_stratified_grouped_split,
    evaluate_four_development_arms,
    evaluate_frozen_raw_pointwise_final_test,
    evaluate_raw_pointwise_development,
    evaluate_raw_pointwise_final_test,
    load_frozen_development_baseline,
    load_frozen_grouped_split,
    load_frozen_raw_pointwise_development,
    load_frozen_raw_pointwise_final_test,
    load_sdse_t4_owner_authorization,
    load_serper_dual_source_dataset,
    split_year_counts,
)

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data/evaluation/serper-dual-source-query-v1/dataset.json"


def _write(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _source_record(
    *, source_id: str, toy_number: str, casting: str, collector_number: str
) -> dict[str, object]:
    return {
        "source_record_id": source_id,
        "release_year": 2025,
        "brand": "Hot Wheels",
        "toy_number": toy_number,
        "collector_number": collector_number,
        "source_model_label": casting,
        "casting_name": casting,
        "variant_note": None,
        "series": "HW Test",
        "series_position": f"{int(collector_number)}/10",
        "color": None,
        "usage": "staging_only_not_evaluation_or_canonical",
        "canonical_uuid": None,
    }


def _paired_dataset() -> SerperDualSourceDataset:
    records: list[dict[str, object]] = []
    for target_index, (casting, toy_number) in enumerate(
        (("Alpha", "AAA01"), ("Beta", "BBB02")),
        start=1,
    ):
        identity = {
            "brand": "Hot Wheels",
            "casting": casting,
            "release_year": 2025,
            "series": "HW Test",
            "collector_number": str(target_index),
            "series_position": f"{target_index}/10",
            "toy_number": toy_number,
        }
        for source_type, raw_suffix, cleaned_suffix in (
            ("image_search", "sealed image result", "image result"),
            ("shopping", "new shopping listing", "shopping listing"),
        ):
            records.append(
                {
                    "id": f"sds-{len(records) + 1:04d}",
                    "target_id": f"sds-target-{target_index:04d}",
                    "source_type": source_type,
                    "query_raw": f"Hot Wheels {casting} 2025 {toy_number} {raw_suffix}",
                    "query_cleaned": (
                        f"hot wheels {casting.casefold()} 2025 {toy_number.casefold()} "
                        f"{cleaned_suffix}"
                    ),
                    "expected_casting": casting,
                    "expected_full_identity": identity,
                }
            )
    return SerperDualSourceDataset.model_validate(
        {
            "dataset_version": "serper-dual-source-query-v1",
            "catalog_sha256": "a" * 64,
            "authority_scope": "frozen-community-catalog-relative-not-manufacturer-truth",
            "target_count": 2,
            "record_count": 4,
            "records": records,
        }
    )


class _FakePointwiseScorer:
    version = "fake-pointwise-v1"

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[float, ...]:
        return tuple(1.0 if "casting: alpha" in document.casefold() else 0.0 for _, document in pairs)


def test_frozen_dataset_has_exact_paired_contract() -> None:
    dataset = load_serper_dual_source_dataset(DATASET)
    assert dataset.target_count == 150
    assert dataset.record_count == 300
    assert len(dataset.target_pairs()) == 150
    assert all(
        pair[0].target_id == pair[1].target_id
        and pair[0].source_type == "image_search"
        and pair[1].source_type == "shopping"
        for pair in dataset.target_pairs()
    )


def test_frozen_split_is_grouped_disjoint_exhaustive_and_stable() -> None:
    dataset = load_serper_dual_source_dataset(DATASET)
    split = load_frozen_grouped_split(dataset, DATASET)
    development = set(split.development_target_ids)
    test = set(split.test_target_ids)
    assert len(development) == 100
    assert len(test) == 50
    assert not development & test
    assert len(development | test) == 150
    assert split.assignment_sha256 == FROZEN_SPLIT_SHA256
    assert split_year_counts(dataset, split) == {
        "development": {"2023": 26, "2024": 22, "2025": 30, "2026": 22},
        "test": {"2023": 13, "2024": 11, "2025": 15, "2026": 11},
    }


def test_split_changes_when_salt_changes_but_never_splits_a_pair() -> None:
    dataset = load_serper_dual_source_dataset(DATASET)
    first = build_year_stratified_grouped_split(
        dataset,
        development_target_count=100,
        salt="first",
        version="v1",
    )
    second = build_year_stratified_grouped_split(
        dataset,
        development_target_count=100,
        salt="second",
        version="v1",
    )
    assert first.assignment_sha256 != second.assignment_sha256
    assert len(set(first.development_target_ids) & set(first.test_target_ids)) == 0


def test_dataset_rejects_pair_identity_disagreement(tmp_path: Path) -> None:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    payload["records"][1]["expected_full_identity"]["series"] = "Changed Series"
    path = _write(tmp_path / "dataset.json", payload)
    with pytest.raises(ValueError, match="disagree on expected identity"):
        load_serper_dual_source_dataset(path)


def test_dataset_rejects_missing_source_pair(tmp_path: Path) -> None:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    payload["records"][1]["source_type"] = "image_search"
    path = _write(tmp_path / "dataset.json", payload)
    with pytest.raises(ValueError, match="one ordered record per source"):
        load_serper_dual_source_dataset(path)


def test_frozen_loader_rejects_byte_drift(tmp_path: Path) -> None:
    payload = json.loads(DATASET.read_text(encoding="utf-8"))
    payload["records"][0]["query_raw"] += " changed"
    path = _write(tmp_path / "dataset.json", payload)
    dataset = load_serper_dual_source_dataset(path)
    with pytest.raises(ValueError, match="dataset bytes differ"):
        load_frozen_grouped_split(dataset, path)


def test_dataset_directory_contains_only_final_dataset() -> None:
    assert sorted(path.name for path in DATASET.parent.iterdir()) == ["dataset.json"]


def test_four_arm_evaluator_scores_development_only_and_returns_aggregate() -> None:
    dataset = _paired_dataset()
    split = FrozenGroupedSplit(
        version="test-split-v1",
        development_target_ids=("sds-target-0001",),
        test_target_ids=("sds-target-0002",),
        assignment_sha256="b" * 64,
    )
    source_records = [
        _source_record(
            source_id="source-alpha",
            toy_number="AAA01",
            casting="Alpha",
            collector_number="1",
        ),
        _source_record(
            source_id="source-beta",
            toy_number="BBB02",
            casting="Beta",
            collector_number="2",
        ),
    ]
    settings = replace(
        Settings(),
        human_catalog_path=ROOT / "data/human_backed_catalog.json",
        review_family_knowledge_path=ROOT / "data/review_family_knowledge.json",
        review_family_knowledge_manifest_path=ROOT
        / "data/review_family_knowledge_manifest.json",
        candidate_limit=2,
    )
    report = evaluate_four_development_arms(
        settings,
        dataset,
        split,
        source_records,
        dataset_sha256="c" * 64,
    )
    assert report.status == "development_only_test_unopened"
    assert report.development_target_count == 1
    assert report.test_target_count == 1
    assert report.metadata["test_targets_scored"] == 0
    assert set(report.arms) == {
        "image_search_raw",
        "image_search_cleaned",
        "shopping_raw",
        "shopping_cleaned",
    }
    assert all(arm.sample_count == 1 for arm in report.arms.values())
    assert all(arm.casting_top1_accuracy == 1.0 for arm in report.arms.values())

    serialized = json.dumps(asdict(report), sort_keys=True)
    for forbidden in (
        "query_raw",
        "query_cleaned",
        "target_id",
        "expected_casting",
        "prediction",
    ):
        assert forbidden not in serialized


def test_four_arm_evaluator_rejects_split_overlap() -> None:
    dataset = _paired_dataset()
    split = FrozenGroupedSplit(
        version="test-split-v1",
        development_target_ids=("sds-target-0001",),
        test_target_ids=("sds-target-0001",),
        assignment_sha256="b" * 64,
    )
    with pytest.raises(ValueError, match="disjoint"):
        evaluate_four_development_arms(
            Settings(),
            dataset,
            split,
            [],
            dataset_sha256="c" * 64,
        )


def test_raw_pointwise_evaluator_uses_raw_development_only_and_same_candidates() -> None:
    dataset = _paired_dataset()
    split = FrozenGroupedSplit(
        version="test-split-v1",
        development_target_ids=("sds-target-0001",),
        test_target_ids=("sds-target-0002",),
        assignment_sha256="b" * 64,
    )
    source_records = [
        _source_record(
            source_id="source-alpha",
            toy_number="AAA01",
            casting="Alpha",
            collector_number="1",
        ),
        _source_record(
            source_id="source-beta",
            toy_number="BBB02",
            casting="Beta",
            collector_number="2",
        ),
    ]
    settings = replace(
        Settings(),
        human_catalog_path=ROOT / "data/human_backed_catalog.json",
        review_family_knowledge_path=ROOT / "data/review_family_knowledge.json",
        review_family_knowledge_manifest_path=ROOT
        / "data/review_family_knowledge_manifest.json",
        candidate_limit=2,
    )
    report = evaluate_raw_pointwise_development(
        settings,
        dataset,
        split,
        source_records,
        NeuralPointwiseReranker(_FakePointwiseScorer()),
        dataset_sha256="c" * 64,
    )
    assert report.status == "development_only_raw_pointwise_test_unopened"
    assert report.metadata["query_representation"] == "raw_only"
    assert report.metadata["cleaned_arms_scored"] == 0
    assert report.metadata["test_targets_scored"] == 0
    assert report.metadata["candidate_membership_changed_by_pointwise"] is False
    assert set(report.arms) == {
        "image_search_rrf",
        "image_search_neural_pointwise",
        "shopping_rrf",
        "shopping_neural_pointwise",
    }
    assert all(arm.sample_count == 1 for arm in report.arms.values())
    assert all(arm.casting_top1_accuracy == 1.0 for arm in report.arms.values())

    serialized = json.dumps(asdict(report), sort_keys=True)
    for forbidden in ("query_raw", "query_cleaned", "target_id", "prediction"):
        assert forbidden not in serialized


def test_raw_pointwise_evaluator_rejects_runtime_reranker_activation() -> None:
    dataset = _paired_dataset()
    split = FrozenGroupedSplit(
        version="test-split-v1",
        development_target_ids=("sds-target-0001",),
        test_target_ids=("sds-target-0002",),
        assignment_sha256="b" * 64,
    )
    with pytest.raises(ValueError, match="RRF runtime default"):
        evaluate_raw_pointwise_development(
            replace(Settings(), reranker_enabled=True),
            dataset,
            split,
            [],
            NeuralPointwiseReranker(_FakePointwiseScorer()),
            dataset_sha256="c" * 64,
        )


def test_raw_pointwise_final_evaluator_scores_test_partition_only() -> None:
    dataset = _paired_dataset()
    split = FrozenGroupedSplit(
        version="test-split-v1",
        development_target_ids=("sds-target-0001",),
        test_target_ids=("sds-target-0002",),
        assignment_sha256="b" * 64,
    )
    source_records = [
        _source_record(
            source_id="source-alpha",
            toy_number="AAA01",
            casting="Alpha",
            collector_number="1",
        ),
        _source_record(
            source_id="source-beta",
            toy_number="BBB02",
            casting="Beta",
            collector_number="2",
        ),
    ]
    settings = replace(
        Settings(),
        human_catalog_path=ROOT / "data/human_backed_catalog.json",
        review_family_knowledge_path=ROOT / "data/review_family_knowledge.json",
        review_family_knowledge_manifest_path=ROOT
        / "data/review_family_knowledge_manifest.json",
        candidate_limit=2,
    )
    report = evaluate_raw_pointwise_final_test(
        settings,
        dataset,
        split,
        source_records,
        NeuralPointwiseReranker(_FakePointwiseScorer()),
        dataset_sha256="c" * 64,
        owner_authorization_sha256="d" * 64,
    )
    assert report.status == "final_test_evaluated_once_aggregate_only"
    assert report.test_target_count == 1
    assert report.metadata["development_targets_scored_in_final_run"] == 0
    assert report.metadata["test_targets_scored"] == 1
    assert report.metadata["test_run_count"] == 1
    assert all(arm.sample_count == 1 for arm in report.arms.values())

    serialized = json.dumps(asdict(report), sort_keys=True)
    for forbidden in ("query_raw", "query_cleaned", "target_id", "prediction"):
        assert forbidden not in serialized


def test_sdse_t4_owner_authorization_is_frozen() -> None:
    authorization = load_sdse_t4_owner_authorization(ROOT / SDSE_T4_OWNER_AUTHORIZATION)
    assert authorization["decision"] == "execute_one_time_aggregate_final_test"
    assert authorization["bindings"]["test_target_count"] == 50


def test_frozen_final_evaluator_rejects_rerun_before_loading_data(
    tmp_path: Path,
) -> None:
    output = _write(tmp_path / "raw-pointwise-final-test.json", {})
    with pytest.raises(FileExistsError, match="rerun is prohibited"):
        evaluate_frozen_raw_pointwise_final_test(
            Settings(),
            root=ROOT,
            output_path=output,
        )


def test_frozen_development_baseline_is_traceable_and_test_closed() -> None:
    baseline = load_frozen_development_baseline(ROOT / DEVELOPMENT_BASELINE)
    assert baseline["status"] == "development_baseline_frozen_test_unopened"
    assert baseline["decision"]["development_leader"] == "shopping_raw"
    assert baseline["decision"]["primary_representation_by_source"] == {
        "image_search": "raw",
        "shopping": "raw",
    }
    assert baseline["arms"]["image_search_raw"]["metrics"][
        "casting_top1_accuracy"
    ] == 0.88
    assert baseline["arms"]["shopping_raw"]["metrics"][
        "exact_release_top1_accuracy"
    ] == 0.57
    assert baseline["guardrails"]["test_targets_scored"] == 0


def test_frozen_development_baseline_rejects_byte_drift(tmp_path: Path) -> None:
    payload = json.loads((ROOT / DEVELOPMENT_BASELINE).read_text(encoding="utf-8"))
    payload["arms"]["shopping_raw"]["metrics"]["exact_release_top1_accuracy"] = 0.58
    path = _write(tmp_path / "development-baseline.json", payload)
    with pytest.raises(ValueError, match="bytes differ"):
        load_frozen_development_baseline(path)


def test_frozen_raw_pointwise_result_is_traceable_and_test_closed() -> None:
    result = load_frozen_raw_pointwise_development(ROOT / RAW_POINTWISE_DEVELOPMENT)
    assert result["status"] == "development_pointwise_selected_test_unopened"
    assert result["decision"]["selected_development_ranker"] == "neural_pointwise"
    assert result["decision"]["selected_query_representation"] == "raw"
    assert result["arms"]["image_search_neural_pointwise"]["metrics"][
        "casting_top1_accuracy"
    ] == 0.98
    assert result["arms"]["shopping_neural_pointwise"]["metrics"][
        "exact_release_top1_accuracy"
    ] == 0.74
    assert result["guardrails"]["test_targets_scored"] == 0


def test_frozen_raw_pointwise_result_rejects_byte_drift(tmp_path: Path) -> None:
    payload = json.loads((ROOT / RAW_POINTWISE_DEVELOPMENT).read_text(encoding="utf-8"))
    payload["arms"]["shopping_neural_pointwise"]["metrics"][
        "exact_release_top1_accuracy"
    ] = 0.75
    path = _write(tmp_path / "raw-pointwise-development.json", payload)
    with pytest.raises(ValueError, match="bytes differ"):
        load_frozen_raw_pointwise_development(path)


def test_frozen_raw_pointwise_final_test_is_traceable_and_one_shot() -> None:
    result = load_frozen_raw_pointwise_final_test(ROOT / RAW_POINTWISE_FINAL_TEST)
    assert result["status"] == "final_test_evaluated_once_aggregate_only"
    assert result["combined_metrics"]["rrf"]["exact_release_top1_accuracy"] == 0.55
    assert result["combined_metrics"]["neural_pointwise"][
        "exact_release_top1_accuracy"
    ] == 0.64
    assert result["conclusion"]["selected_ranker_supported_on_final_test"] is True
    assert result["guardrails"]["completed_test_run_count"] == 1
    assert result["guardrails"]["rerun_allowed"] is False
    with pytest.raises(FileExistsError, match="rerun is prohibited"):
        evaluate_frozen_raw_pointwise_final_test(Settings(), root=ROOT)


def test_frozen_raw_pointwise_final_test_rejects_byte_drift(tmp_path: Path) -> None:
    payload = json.loads((ROOT / RAW_POINTWISE_FINAL_TEST).read_text(encoding="utf-8"))
    payload["combined_metrics"]["neural_pointwise"][
        "exact_release_top1_accuracy"
    ] = 0.65
    path = _write(tmp_path / "raw-pointwise-final-test.json", payload)
    with pytest.raises(ValueError, match="bytes differ"):
        load_frozen_raw_pointwise_final_test(path)
