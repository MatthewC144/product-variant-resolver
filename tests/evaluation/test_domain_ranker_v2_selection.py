from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from product_variant_resolver.domain_ranker_comparison import AggregateMetrics
from product_variant_resolver.domain_ranker_v2_selection import (
    AUTHORIZATION_PATH,
    RESULT_PATH,
    build_authorization,
    check,
    compare_equivalence,
    comparison_protocol,
    evaluate_gate,
    select_winner,
)

ROOT = Path(__file__).resolve().parents[2]


def metric(**changes: Any) -> AggregateMetrics:
    baseline = AggregateMetrics(
        exact_top1_count=10,
        exact_top1_rate=10 / 30,
        casting_top1_count=20,
        casting_top1_rate=20 / 30,
        mrr_at_10=0.50,
        recall_at_25_count=30,
        recall_at_25=1.0,
        same_family_hard_negative_correct=10,
        same_family_hard_negative_total=20,
        same_family_hard_negative_accuracy=0.50,
        cpu_latency_sample_count=90,
        cpu_latency_p50_ms=80.0,
        cpu_latency_p95_ms=100.0,
    )
    return replace(baseline, **changes)


def test_protocol_freezes_quality_latency_two_seed_and_tie_gates() -> None:
    protocol = comparison_protocol()
    assert protocol["selection_query_count"] == 30
    assert protocol["gates"] == {
        "minimum_exact_top1_case_delta": 3,
        "minimum_mrr_at_10_delta": 0.02,
        "minimum_same_family_accuracy_delta": 0.10,
        "minimum_casting_top1_case_delta": -1,
        "minimum_recall_at_25_delta": 0.0,
        "maximum_latency_ratio": 1.25,
        "maximum_latency_p95_ms": 200.0,
        "two_seed_direction": "both_seeds_exact_top1_and_mrr_deltas_strictly_positive",
    }
    assert protocol["latency"]["runtime"] == "onnxruntime_cpu"
    assert protocol["winner_tie_break"][-1] == "seed_asc"


def test_gate_is_all_or_nothing_and_winner_tie_prefers_lower_seed() -> None:
    generic = metric()
    passing = metric(
        exact_top1_count=13,
        exact_top1_rate=13 / 30,
        casting_top1_count=19,
        casting_top1_rate=19 / 30,
        mrr_at_10=0.52,
        same_family_hard_negative_correct=12,
        same_family_hard_negative_accuracy=0.60,
        cpu_latency_p95_ms=125.0,
    )
    gate = evaluate_gate(generic, passing, seed_direction_stable=True)
    assert gate["passed"] is True
    failing = replace(passing, exact_top1_count=12, exact_top1_rate=12 / 30)
    assert evaluate_gate(generic, failing, seed_direction_stable=True)["passed"] is False
    metrics = {
        "generic": generic,
        "domain_seed_17": passing,
        "domain_seed_29": passing,
    }
    gates = {"domain_seed_17": gate, "domain_seed_29": gate}
    assert select_winner(metrics, gates) == "domain_seed_17"


def test_no_passing_checkpoint_produces_null_winner() -> None:
    generic = metric()
    domain = metric(exact_top1_count=12, mrr_at_10=0.53)
    failed = evaluate_gate(generic, domain, seed_direction_stable=True)
    metrics = {"generic": generic, "domain_seed_17": domain, "domain_seed_29": domain}
    gates = {"domain_seed_17": failed, "domain_seed_29": failed}
    assert select_winner(metrics, gates) is None


def test_equivalence_requires_all_thirty_identical_orders() -> None:
    pools = []
    left = []
    for row_index in range(30):
        candidates = [{"canonical_uuid": f"{row_index:02d}-{index:02d}"} for index in range(25)]
        pools.append({"candidates": candidates})
        left.append([float(25 - index) for index in range(25)])
    result = compare_equivalence(pools, left, left)
    assert result["pair_count"] == 750
    assert result["identical_top25_order_count"] == 30
    assert result["passed"] is True


def test_authorization_freezes_protocol_before_selection() -> None:
    authorization = build_authorization(ROOT, "0" * 40)
    assert authorization["decision"] == "execute_untouched_selection_once_under_frozen_protocol"
    assert (
        "score_exactly_30_frozen_selection_pools_once_for_quality"
        in authorization["authorized_actions"]
    )
    assert (
        "calibration_threshold_selection_or_fresh_final_evaluation"
        in authorization["prohibited_actions"]
    )


def test_materialized_t6_result_is_integral_aggregate_only_and_runtime_closed() -> None:
    result = check(ROOT)
    assert result["winner"] is None
    assert result["selected_checkpoint_sha256"] is None
    assert result["guardrails"]["selection_quality_evaluations"] == 1
    assert result["guardrails"]["runtime_activations"] == 0
    assert result["guardrails"]["public_row_level_records"] == 0
    assert result["next_allowed_action"] == "DRV2-T7_Lite_QA_requires_separate_owner_authorization"
    public_text = (ROOT / AUTHORIZATION_PATH).read_text() + (ROOT / RESULT_PATH).read_text()
    assert "drv2-q" not in public_text.casefold()
    assert '"query"' not in public_text
    assert '"target_uuid"' not in public_text
