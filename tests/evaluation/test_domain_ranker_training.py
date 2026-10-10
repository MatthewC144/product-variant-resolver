from __future__ import annotations

import json
from pathlib import Path

import pytest

from product_variant_resolver.domain_ranker_training import (
    EARLY_STOPPING_PATIENCE,
    EpochMetric,
    load_selection_pools,
    load_training_examples,
    mrr_at_10_from_scores,
    select_early_stopping,
    training_recipe,
)

ROOT = Path(__file__).resolve().parents[2]


def test_recipe_is_the_single_frozen_two_seed_binary_recipe() -> None:
    recipe = training_recipe()
    assert recipe["seeds"] == [17, 29]
    assert recipe["objective"] == "binary_relevance_bce_with_logits"
    assert recipe["max_epochs"] == 4
    assert recipe["early_stopping_patience"] == EARLY_STOPPING_PATIENCE == 2
    assert recipe["device"] == "cpu"
    assert recipe["published_checkpoint_dtype"] == "float16"


def test_frozen_t3_pairs_project_to_balanced_training_examples() -> None:
    examples = load_training_examples(ROOT)
    assert len(examples) == 690
    assert sum(example.label == 1.0 for example in examples) == 345
    assert sum(example.label == 0.0 for example in examples) == 345
    assert all(example.query and example.candidate for example in examples)


def test_only_thirty_ranker_selection_pools_are_loaded() -> None:
    pools = load_selection_pools(ROOT)
    assert len(pools) == 30
    assert {pool["partition"] for pool in pools} == {"ranker_selection"}
    assert {len(pool["candidates"]) for pool in pools} == {25}


def test_mrr_at_10_uses_stable_score_then_uuid_ranking() -> None:
    pools = (
        {
            "target_uuid": "b",
            "candidates": [
                {"canonical_uuid": "b"},
                {"canonical_uuid": "a"},
                {"canonical_uuid": "c"},
            ],
        },
        {
            "target_uuid": "z",
            "candidates": [
                {"canonical_uuid": "x"},
                {"canonical_uuid": "z"},
            ],
        },
    )
    assert mrr_at_10_from_scores(pools, ((1.0, 1.0, 0.0), (2.0, 1.0))) == pytest.approx(
        0.5
    )


def test_early_stopping_ties_keep_earliest_epoch() -> None:
    history = (
        EpochMetric(1, 0.5, 0.4),
        EpochMetric(2, 0.4, 0.5),
        EpochMetric(3, 0.3, 0.5),
        EpochMetric(4, 0.2, 0.49),
    )
    assert select_early_stopping(history) == (2, 4, 0.5)


def test_early_stopping_rejects_noncontiguous_history() -> None:
    with pytest.raises(ValueError, match="contiguous"):
        select_early_stopping((EpochMetric(2, 0.5, 0.4),))


def test_t3_public_manifest_is_still_the_authorized_input() -> None:
    path = (
        ROOT
        / "data/evaluation/domain-ranker-selective-prediction-development-v1"
        / "public-hard-negative-pairs-v1/manifest.json"
    )
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["files_sha256"]["pairs.jsonl"] == (
        "50f88e73889b31e8f314e93b2cca9e4871934662b5218c6659a72fe06c0ca2ba"
    )
    assert manifest["release_gate_passed"] is True
    assert manifest["guardrails"]["model_training_runs"] == 0
