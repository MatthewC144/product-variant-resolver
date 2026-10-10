from __future__ import annotations

import json
from pathlib import Path

import pytest

from product_variant_resolver.domain_ranker_training import (
    EARLY_STOPPING_PATIENCE,
    PACKAGE_DIRECTORY,
    PACKAGE_FILES,
    TEXT_FILES,
    EpochMetric,
    _validate_exact_package_files,
    _validate_safetensors,
    check,
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


def test_real_safetensors_file_is_inspected_through_safe_open(tmp_path: Path) -> None:
    import torch
    from safetensors.torch import save_file

    checkpoint = tmp_path / "model.safetensors"
    save_file(
        {
            "classifier.weight": torch.zeros((1, 4), dtype=torch.float16),
            "classifier.bias": torch.zeros((1,), dtype=torch.float16),
        },
        checkpoint,
    )
    assert _validate_safetensors(checkpoint) == {
        "classifier.bias": [1],
        "classifier.weight": [1, 4],
    }


def test_published_checkpoint_package_passes_strict_offline_validation() -> None:
    manifest = check(ROOT)
    assert manifest["release_gate_passed"] is True
    assert manifest["training"]["generic_vs_domain_winner_selected"] is False
    assert manifest["guardrails"]["positive_test_rows_read_or_scored"] == 0
    assert manifest["guardrails"]["negative_holdout_rows_read_or_scored"] == 0
    assert manifest["guardrails"]["no_match_development_rows_read_or_scored"] == 0
    assert manifest["guardrails"]["runtime_default_changed"] is False
    assert all(
        b"\r" not in (ROOT / PACKAGE_DIRECTORY / name).read_bytes() for name in TEXT_FILES
    )


def test_checkpoint_allowlist_rejects_nested_unexpected_file(tmp_path: Path) -> None:
    for name in PACKAGE_FILES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"")
    _validate_exact_package_files(tmp_path)
    unexpected = tmp_path / "seed-17" / "optimizer.pt"
    unexpected.write_bytes(b"pickle-like state is forbidden")
    with pytest.raises(ValueError, match="allowlist mismatch"):
        _validate_exact_package_files(tmp_path)
