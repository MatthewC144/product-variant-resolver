from __future__ import annotations

import json
import stat
from pathlib import Path
from typing import Any, cast

from product_variant_resolver.domain_ranker_v2_candidate_pools import LOCAL_POOLS_PATH
from product_variant_resolver.domain_ranker_v2_latency_repair import (
    AUTHORIZATION_PATH,
    LOCAL_ONNX_PATH,
    ONNX_MANIFEST_PATH,
    RESULT_PATH,
    _contains_public_row_level_data,
    build_authorization,
    build_result,
    check,
    compare_frozen_scores,
)

ROOT = Path(__file__).resolve().parents[2]


def load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


class FrozenScoreReplay:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.pending = [
            tuple(float(candidate["generic_pointwise_score"]) for candidate in row["candidates"])
            for row in rows
        ]

    def score_pairs(self, pairs: list[tuple[str, str]]) -> tuple[float, ...]:
        assert len(pairs) == 25
        return self.pending.pop(0)


def test_equivalence_protocol_accepts_identical_all_pool_ordering() -> None:
    local = load(ROOT / LOCAL_POOLS_PATH)
    rows = cast(list[dict[str, Any]], local["rows"])
    result = compare_frozen_scores(rows, cast(Any, FrozenScoreReplay(rows)))
    assert result == {
        "pair_count": 4500,
        "exactly_equal_logit_count": 4500,
        "maximum_absolute_logit_delta": 0.0,
        "maximum_allowed_absolute_logit_delta": 2e-05,
        "identical_top25_order_count": 180,
        "required_identical_top25_order_count": 180,
        "passed": True,
    }


def test_repair_result_keeps_200ms_gate_and_t4_separate() -> None:
    authorization = build_authorization(ROOT, "0" * 40)
    manifest = {"manifest_sha256": "a" * 64}
    equivalence = {
        "pair_count": 4500,
        "maximum_absolute_logit_delta": 0.0,
        "identical_top25_order_count": 180,
        "passed": True,
    }
    passed = build_result(authorization, manifest, equivalence, [199.0] * 90)
    failed = build_result(authorization, manifest, equivalence, [200.001] * 90)
    assert passed["latency"]["gate_passed"] is True
    assert passed["next_allowed_action"] == "DRV2-T4_requires_separate_owner_authorization"
    assert failed["latency"]["gate_passed"] is False
    assert failed["next_allowed_action"] == "stop_and_repair_generic_latency_before_DRV2-T4"


def test_t3r_authorization_prohibits_quantization_and_training() -> None:
    authorization = build_authorization(ROOT, "0" * 40)
    assert "quantize_or_change_model_weights" in authorization["prohibited_actions"]
    assert "hard_negative_mining_or_model_training" in authorization["prohibited_actions"]
    assert authorization["equivalence_protocol"]["required_identical_top25_order_count"] == 180


def test_materialized_t3r_artifacts_validate() -> None:
    result = check(ROOT)
    assert result["equivalence"]["identical_top25_order_count"] == 180
    assert result["latency"]["maximum_p95_ms"] == 200.0
    assert stat.S_IMODE((ROOT / LOCAL_ONNX_PATH).stat().st_mode) == 0o600


def test_materialized_t3r_public_files_are_aggregate_only() -> None:
    payloads = [load(ROOT / path) for path in (AUTHORIZATION_PATH, ONNX_MANIFEST_PATH, RESULT_PATH)]
    assert not any(_contains_public_row_level_data(payload) for payload in payloads)
    text = json.dumps(payloads, ensure_ascii=False).casefold()
    assert "drv2-q001" not in text
    assert "generic_pointwise_score" not in text
