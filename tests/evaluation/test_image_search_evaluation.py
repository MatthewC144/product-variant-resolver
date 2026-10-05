from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from product_variant_resolver.config import Settings
from product_variant_resolver.image_search_evaluation import (
    FROZEN_SPLIT_SHA256,
    bind_dataset_to_source,
    build_deterministic_split,
    build_evaluation_catalog,
    evaluate_image_search_dataset,
    load_frozen_split,
    load_image_search_dataset,
    load_source_records,
)

ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _record(*, source_id: str, toy: str, casting: str, collector: str) -> dict[str, object]:
    return {
        "source_record_id": source_id,
        "release_year": 2025,
        "brand": "Hot Wheels",
        "toy_number": toy,
        "collector_number": collector,
        "source_model_label": casting,
        "casting_name": casting,
        "variant_note": None,
        "series": "HW Test",
        "series_position": f"{int(collector)}/10",
        "color": None,
        "usage": "staging_only_not_evaluation_or_canonical",
        "canonical_uuid": None,
    }


def _source(records: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema_version": "pvr-local-release-staging-v1",
        "status": "review_only_local_staging_snapshot",
        "records": records,
    }


def _case(case_id: str, *, query: str, toy: str, casting: str, collector: str) -> dict[str, object]:
    return {
        "id": case_id,
        "query": query,
        "expected_casting": casting,
        "expected_full_identity": {
            "brand": "Hot Wheels",
            "casting": casting,
            "release_year": 2025,
            "series": "HW Test",
            "collector_number": collector,
            "series_position": f"{int(collector)}/10",
            "toy_number": toy,
        },
    }


def _dataset(cases: list[dict[str, object]]) -> dict[str, object]:
    return {"dataset_version": "image-search-resolver-v1", "records": cases}


def test_dataset_and_source_bind_exact_release_fields(tmp_path: Path) -> None:
    dataset_path = _write(
        tmp_path / "dataset.json",
        _dataset(
            [
                _case(
                    "isr-0001",
                    query="Hot Wheels Alpha AAA01",
                    toy="AAA01",
                    casting="Alpha",
                    collector="1",
                )
            ]
        ),
    )
    source_path = _write(
        tmp_path / "source.json",
        _source([_record(source_id="source-alpha", toy="AAA01", casting="Alpha", collector="1")]),
    )
    dataset = load_image_search_dataset(dataset_path)
    source = load_source_records(source_path, expected_count=1)
    bindings = bind_dataset_to_source(dataset, source)
    assert bindings[0].case_id == "isr-0001"
    assert bindings[0].toy_number == "AAA01"
    assert (
        bindings[0].evaluation_uuid == build_evaluation_catalog(source).products[0].canonical_uuid
    )


def test_dataset_rejects_noncontiguous_ids_and_duplicate_queries(tmp_path: Path) -> None:
    cases = [
        _case("isr-0001", query="same query", toy="AAA01", casting="Alpha", collector="1"),
        _case("isr-0003", query="same query", toy="BBB02", casting="Beta", collector="2"),
    ]
    path = _write(tmp_path / "dataset.json", _dataset(cases))
    with pytest.raises(ValueError, match="contiguous|unique"):
        load_image_search_dataset(path)


def test_binding_rejects_source_identity_drift(tmp_path: Path) -> None:
    dataset_path = _write(
        tmp_path / "dataset.json",
        _dataset([_case("isr-0001", query="Alpha", toy="AAA01", casting="Alpha", collector="1")]),
    )
    source_path = _write(
        tmp_path / "source.json",
        _source([_record(source_id="source-alpha", toy="AAA01", casting="Changed", collector="1")]),
    )
    with pytest.raises(ValueError, match="source mismatch for casting"):
        bind_dataset_to_source(
            load_image_search_dataset(dataset_path),
            load_source_records(source_path, expected_count=1),
        )


def test_source_rejects_canonical_promotion(tmp_path: Path) -> None:
    record = _record(source_id="source-alpha", toy="AAA01", casting="Alpha", collector="1")
    record["canonical_uuid"] = "13ab2640-7372-4d77-8fbb-11407d07a07e"
    path = _write(tmp_path / "source.json", _source([record]))
    with pytest.raises(ValueError, match="authority boundary"):
        load_source_records(path, expected_count=1)


def test_frozen_split_is_disjoint_exhaustive_and_stable() -> None:
    dataset = load_image_search_dataset(
        ROOT / "data/evaluation/image-search-resolver-v1/dataset.json"
    )
    split = load_frozen_split(
        dataset, ROOT / "data/evaluation/image-search-resolver-v1/dataset.json"
    )
    assert len(split.development_case_ids) == 100
    assert len(split.test_case_ids) == 53
    assert not set(split.development_case_ids) & set(split.test_case_ids)
    assert len(set(split.development_case_ids) | set(split.test_case_ids)) == 153
    assert split.assignment_sha256 == FROZEN_SPLIT_SHA256


def test_split_changes_when_salt_changes(tmp_path: Path) -> None:
    cases = [
        _case(
            f"isr-{index:04d}",
            query=f"query {index}",
            toy=f"T{index}",
            casting=f"Car {index}",
            collector=str(index),
        )
        for index in range(1, 7)
    ]
    dataset = load_image_search_dataset(_write(tmp_path / "dataset.json", _dataset(cases)))
    first = build_deterministic_split(dataset, development_count=4, salt="one", version="v1")
    second = build_deterministic_split(dataset, development_count=4, salt="two", version="v1")
    assert first.assignment_sha256 != second.assignment_sha256


def test_evaluation_emits_aggregate_only_metrics(tmp_path: Path) -> None:
    records = [
        _record(source_id="source-alpha", toy="AAA01", casting="Alpha", collector="1"),
        _record(source_id="source-beta", toy="BBB02", casting="Beta", collector="2"),
    ]
    cases = [
        _case(
            "isr-0001",
            query="Hot Wheels Alpha 2025 HW Test 1/10 AAA01",
            toy="AAA01",
            casting="Alpha",
            collector="1",
        ),
        _case(
            "isr-0002",
            query="Hot Wheels Beta 2025 HW Test 2/10 BBB02",
            toy="BBB02",
            casting="Beta",
            collector="2",
        ),
    ]
    dataset_path = _write(tmp_path / "dataset.json", _dataset(cases))
    source_path = _write(tmp_path / "source.json", _source(records))
    settings = replace(
        Settings(),
        human_catalog_path=ROOT / "data/human_backed_catalog.json",
        review_family_knowledge_path=ROOT / "data/review_family_knowledge.json",
        review_family_knowledge_manifest_path=ROOT / "data/review_family_knowledge_manifest.json",
        candidate_limit=2,
    )
    report = evaluate_image_search_dataset(
        settings,
        dataset_path=dataset_path,
        source_path=source_path,
        source_expected_count=2,
        split="all",
    )
    assert report.split == "all"
    assert report.sample_count == 2
    assert report.candidate_count == 2
    assert report.source_binding_count == 2
    assert report.casting_top1_accuracy == 1.0
    assert report.exact_release_top1_accuracy == 1.0
    assert report.metadata["row_level_output_persisted"] is False
    assert "cases" not in report.raw_counts
