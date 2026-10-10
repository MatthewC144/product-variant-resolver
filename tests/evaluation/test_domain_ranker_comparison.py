from __future__ import annotations

from pathlib import Path

import pytest

from product_variant_resolver.domain_ranker_comparison import (
    AggregateMetrics,
    _casting,
    _nearest_rank_percentile,
    aggregate_metrics,
    comparison_protocol,
    evaluate_gate,
    select_winner,
)

ROOT = Path(__file__).resolve().parents[2]


def metric(**overrides: float) -> AggregateMetrics:
    values: dict[str, float] = {
        "exact_top1_count": 10,
        "exact_top1_rate": 1 / 3,
        "casting_top1_count": 20,
        "casting_top1_rate": 2 / 3,
        "mrr_at_10": 0.5,
        "recall_at_25_count": 30,
        "recall_at_25": 1.0,
        "same_family_hard_negative_correct": 10,
        "same_family_hard_negative_total": 20,
        "same_family_hard_negative_accuracy": 0.5,
        "cpu_latency_sample_count": 90,
        "cpu_latency_p50_ms": 40.0,
        "cpu_latency_p95_ms": 50.0,
    }
    values.update(overrides)
    return AggregateMetrics(**values)  # type: ignore[arg-type]


def test_protocol_freezes_selection_only_comparison_and_stop_gates() -> None:
    protocol = comparison_protocol()
    assert protocol["selection_query_count"] == 30
    assert protocol["candidates_per_query"] == 25
    assert protocol["latency"]["measurement_rounds"] == 3
    assert protocol["gates"]["minimum_exact_top1_case_delta"] == 3
    assert protocol["gates"]["minimum_mrr_at_10_delta"] == 0.02


def test_casting_parser_normalizes_only_the_named_rendered_field() -> None:
    assert _casting("brand=x | casting=  Nissan  Skyline  | year=2025") == "nissan skyline"
    with pytest.raises(ValueError, match="casting"):
        _casting("brand=x | year=2025")


def test_nearest_rank_percentile_is_explicit_and_deterministic() -> None:
    assert _nearest_rank_percentile([3.0, 1.0, 4.0, 2.0], 0.50) == 2.0
    assert _nearest_rank_percentile(list(range(1, 101)), 0.95) == 95


def test_aggregate_metrics_uses_uuid_tie_break_and_strict_hard_negative_win() -> None:
    pools = []
    scores = []
    for index in range(30):
        candidates = [
            {
                "canonical_uuid": "b",
                "rendered_text": "brand=x | casting=same | year=2025",
            },
            {
                "canonical_uuid": "a",
                "rendered_text": "brand=x | casting=same | year=2024",
            },
        ]
        candidates.extend(
            {
                "canonical_uuid": f"z{slot:02d}",
                "rendered_text": f"brand=x | casting=other {slot} | year=2025",
            }
            for slot in range(23)
        )
        pools.append({"case_id": f"c{index}", "target_uuid": "b", "candidates": candidates})
        scores.append([1.0, 1.0, *([0.0] * 23)])
    metrics, rows = aggregate_metrics(pools, scores, [1.0] * 90)
    assert metrics.exact_top1_count == 0
    assert metrics.casting_top1_count == 30
    assert metrics.same_family_hard_negative_total == 30
    assert metrics.same_family_hard_negative_correct == 0
    assert len(rows) == 30
    assert "case_id" not in rows[0]


def test_gate_is_all_or_nothing_and_failed_gate_returns_no_winner() -> None:
    generic = metric()
    passing = metric(
        exact_top1_count=13,
        exact_top1_rate=13 / 30,
        casting_top1_count=19,
        casting_top1_rate=19 / 30,
        mrr_at_10=0.53,
        same_family_hard_negative_correct=12,
        same_family_hard_negative_accuracy=0.6,
        cpu_latency_p95_ms=60.0,
    )
    passed = evaluate_gate(generic, passing, seed_direction_stable=True)
    failed = evaluate_gate(generic, passing, seed_direction_stable=False)
    assert passed["passed"] is True
    assert failed["passed"] is False
    assert (
        select_winner(
            {"generic": generic, "domain_seed_17": passing, "domain_seed_29": passing},
            {"domain_seed_17": failed, "domain_seed_29": failed},
        )
        is None
    )


def test_winner_tie_break_prefers_quality_then_latency_then_seed() -> None:
    generic = metric()
    seed17 = metric(exact_top1_count=13, mrr_at_10=0.55, cpu_latency_p95_ms=60.0)
    seed29 = metric(exact_top1_count=13, mrr_at_10=0.54, cpu_latency_p95_ms=40.0)
    gates = {"domain_seed_17": {"passed": True}, "domain_seed_29": {"passed": True}}
    assert (
        select_winner(
            {"generic": generic, "domain_seed_17": seed17, "domain_seed_29": seed29}, gates
        )
        == "domain_seed_17"
    )
