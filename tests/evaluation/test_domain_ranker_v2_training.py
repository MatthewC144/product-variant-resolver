from __future__ import annotations

import json
from pathlib import Path

import pytest

from product_variant_resolver.domain_ranker_v2_training import (
    EARLY_STOPPING_PATIENCE,
    MANIFEST_PATH,
    PACKAGE_DIRECTORY,
    EpochMetric,
    build_authorization,
    check,
    load_pairwise_triples,
    load_validation_pools,
    pairwise_ranknet_loss,
    select_early_stopping,
    training_recipe,
)

ROOT = Path(__file__).resolve().parents[2]


def test_recipe_is_one_fixed_two_seed_pairwise_hypothesis() -> None:
    recipe = training_recipe()
    assert recipe["objective"] == "pairwise_logistic_ranknet_softplus"
    assert recipe["seeds"] == [17, 29]
    assert recipe["learning_rate"] == 1e-5
    assert recipe["max_epochs"] == 4
    assert recipe["early_stopping_patience"] == EARLY_STOPPING_PATIENCE == 2
    assert recipe["early_stopping_partition"] == "ranker_validation"
    assert recipe["selection_partition_access"] == "prohibited_until_DRV2-T6"


def test_frozen_t4_triples_are_exactly_the_training_input() -> None:
    triples = load_pairwise_triples(ROOT)
    assert len(triples) == 332
    assert len({triple.triple_id for triple in triples}) == 332
    assert len({triple.case_id for triple in triples}) == 112
    assert all(triple.query and triple.positive and triple.negative for triple in triples)


def test_only_thirty_validation_pools_are_loaded() -> None:
    pools = load_validation_pools(ROOT)
    assert len(pools) == 30
    assert {pool["partition"] for pool in pools} == {"ranker_validation"}
    assert {len(pool["candidates"]) for pool in pools} == {25}


def test_pairwise_loss_rewards_larger_positive_margin() -> None:
    torch = pytest.importorskip("torch")
    bad = pairwise_ranknet_loss(torch.tensor([0.0]), torch.tensor([1.0]), torch)
    tied = pairwise_ranknet_loss(torch.tensor([0.0]), torch.tensor([0.0]), torch)
    good = pairwise_ranknet_loss(torch.tensor([1.0]), torch.tensor([0.0]), torch)
    assert float(bad) > float(tied) > float(good)


def test_early_stopping_ties_keep_the_earliest_epoch() -> None:
    history = (
        EpochMetric(1, 0.8, 0.7),
        EpochMetric(2, 0.6, 0.8),
        EpochMetric(3, 0.5, 0.8),
        EpochMetric(4, 0.4, 0.79),
    )
    assert select_early_stopping(history) == (2, 4, 0.8)


def test_t5_authorization_prohibits_selection_and_runtime() -> None:
    authorization = build_authorization(ROOT, "0" * 40)
    assert "read_or_score_ranker_selection_partition" in authorization["prohibited_actions"]
    assert (
        "calibration_final_evaluation_or_runtime_activation" in authorization["prohibited_actions"]
    )


@pytest.mark.skipif(
    not (ROOT / MANIFEST_PATH).exists(), reason="T5 checkpoint package has not been materialized"
)
def test_materialized_public_checkpoint_package_is_safe_and_selection_blind() -> None:
    manifest = check(ROOT)
    assert manifest["training"]["generic_vs_domain_winner_selected"] is False
    assert manifest["guardrails"]["selection_rows_read_or_scored"] == 0
    assert manifest["guardrails"]["runtime_activations"] == 0
    assert manifest["next_allowed_action"] == "DRV2-T6_requires_separate_owner_authorization"
    assert (
        ROOT / PACKAGE_DIRECTORY / "seed-17/model.safetensors"
    ).stat().st_size < 50 * 1024 * 1024
    assert (
        ROOT / PACKAGE_DIRECTORY / "seed-29/model.safetensors"
    ).stat().st_size < 50 * 1024 * 1024
    payload = json.loads((ROOT / MANIFEST_PATH).read_text(encoding="utf-8"))
    text = json.dumps(payload, ensure_ascii=False).casefold()
    assert "drv2-q" not in text
    assert "positive_text" not in text
    assert "negative_text" not in text
