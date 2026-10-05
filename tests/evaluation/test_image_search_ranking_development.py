from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, replace
from pathlib import Path

from product_variant_resolver.config import Settings
from product_variant_resolver.image_search_evaluation import load_image_search_dataset
from product_variant_resolver.image_search_ranking_development import (
    ARMS,
    RankingOutcome,
    compare_development_rankers,
    summarize_outcomes,
)

ROOT = Path(__file__).resolve().parents[2]
DATASET = ROOT / "data/evaluation/image-search-resolver-v1/dataset.json"


class _FlatPointwise:
    version = "flat-pointwise-test"

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[float, ...]:
        return tuple(0.0 for _ in pairs)


class _FlatListwise:
    version = "flat-listwise-test"

    def score_set(self, features: Sequence[Sequence[float]]) -> tuple[float, ...]:
        return tuple(0.0 for _ in features)


def _source_from_dataset(path: Path) -> None:
    dataset = load_image_search_dataset(DATASET)
    records = []
    for index, case in enumerate(dataset.records, start=1):
        identity = case.expected_full_identity
        records.append(
            {
                "source_record_id": f"test-source-{index:04d}",
                "release_year": identity.release_year,
                "brand": identity.brand,
                "toy_number": identity.toy_number,
                "collector_number": identity.collector_number,
                "source_model_label": identity.casting,
                "casting_name": identity.casting,
                "variant_note": identity.variant_note,
                "series": identity.series,
                "series_position": identity.series_position,
                "color": identity.color,
                "usage": "staging_only_not_evaluation_or_canonical",
                "canonical_uuid": None,
            }
        )
    path.write_text(
        json.dumps(
            {
                "schema_version": "pvr-local-release-staging-v1",
                "status": "review_only_local_staging_snapshot",
                "records": records,
            }
        ),
        encoding="utf-8",
    )


def test_summary_preserves_raw_counts_and_latency() -> None:
    summary = summarize_outcomes(
        [
            RankingOutcome(True, 1, 2.0),
            RankingOutcome(False, 5, 4.0),
            RankingOutcome(True, None, 9.0),
        ]
    )
    assert summary.sample_count == 3
    assert summary.casting_top1_correct == 2
    assert summary.exact_release_top1_correct == 1
    assert summary.exact_release_retrieved_at_10 == 2
    assert summary.exact_release_top1_accuracy == 1 / 3
    assert summary.exact_release_mrr_at_10 == (1 + 1 / 5) / 3
    assert summary.rerank_p50_latency_ms == 4.0
    assert summary.rerank_p95_latency_ms == 9.0


def test_comparison_scores_development_only_and_emits_no_rows(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    _source_from_dataset(source)
    settings = replace(
        Settings(),
        human_catalog_path=ROOT / "data/human_backed_catalog.json",
        review_family_knowledge_path=ROOT / "data/review_family_knowledge.json",
        review_family_knowledge_manifest_path=ROOT / "data/review_family_knowledge_manifest.json",
        candidate_limit=5,
    )
    report = compare_development_rankers(
        settings,
        root=ROOT,
        dataset_path=DATASET,
        source_path=source,
        source_expected_count=153,
        pointwise=_FlatPointwise(),
        listwise=_FlatListwise(),
    )
    payload = asdict(report)
    assert report.split == "development"
    assert report.sample_count == 100
    assert report.metadata["test_cases_scored"] == 0
    assert set(report.arms) == set(ARMS)
    assert "cases" not in payload
    assert "predictions" not in payload
