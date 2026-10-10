from __future__ import annotations

import json
import stat
from pathlib import Path

from product_variant_resolver.domain_ranker_v2_candidate_pools import (
    AUTHORIZATION_PATH,
    CANDIDATE_LIMIT,
    LATENCY_PATH,
    LOCAL_POOLS_PATH,
    MAXIMUM_P95_MS,
    POOL_MANIFEST_PATH,
    _contains_public_row_level_data,
    build_authorization,
    build_candidate_pools,
    build_latency_report,
    check,
)

ROOT = Path(__file__).resolve().parents[2]


class FakeScorer:
    version = "fake-generic-v1"

    def score_pairs(self, pairs: list[tuple[str, str]]) -> tuple[float, ...]:
        return tuple(float(index % CANDIDATE_LIMIT) for index, _ in enumerate(pairs))


def load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_query_only_top25_pools_have_no_target_injection_or_miss() -> None:
    authorization = build_authorization(ROOT, "0" * 40)
    local, public = build_candidate_pools(ROOT, authorization, scorer=FakeScorer())
    rows = local["rows"]
    assert isinstance(rows, list)
    assert len(rows) == 180
    assert all(len(row["candidates"]) == 25 for row in rows)
    assert public["aggregate_counts"] == {
        "pool_count": 180,
        "candidate_count": 4500,
        "ranker_train_pool_count": 120,
        "ranker_validation_pool_count": 30,
        "ranker_selection_pool_count": 30,
        "ranker_train_retrieval_miss_count": 0,
        "ranker_validation_retrieval_miss_count": 0,
        "ranker_selection_retrieval_miss_count": 0,
        "target_injection_count": 0,
        "hard_negative_labels_created": 0,
        "model_training_runs": 0,
        "selection_quality_evaluations": 0,
    }


def test_public_pool_manifest_is_aggregate_only() -> None:
    authorization = build_authorization(ROOT, "0" * 40)
    _, public = build_candidate_pools(ROOT, authorization, scorer=FakeScorer())
    assert not _contains_public_row_level_data(public)
    text = json.dumps(public, ensure_ascii=False).casefold()
    assert "drv2-q001" not in text
    assert "expected_full_identity" not in text


def test_latency_gate_passes_at_200ms_and_fails_above_it() -> None:
    authorization = build_authorization(ROOT, "0" * 40)
    _, pool_manifest = build_candidate_pools(ROOT, authorization, scorer=FakeScorer())
    environment = {"machine": "test"}
    passed = build_latency_report(
        authorization, pool_manifest, [MAXIMUM_P95_MS] * 90, environment
    )
    failed = build_latency_report(
        authorization, pool_manifest, [MAXIMUM_P95_MS + 0.001] * 90, environment
    )
    assert passed["metrics"]["gate_passed"] is True
    assert passed["next_allowed_action"] == "DRV2-T4_requires_separate_owner_authorization"
    assert failed["metrics"]["gate_passed"] is False
    assert failed["next_allowed_action"] == "stop_and_repair_generic_latency_before_DRV2-T4"


def test_materialized_t3_artifacts_validate_and_remain_private() -> None:
    result = check(ROOT)
    assert result["metrics"]["sample_count"] == 90
    assert result["metrics"]["maximum_p95_ms"] == 200.0
    assert stat.S_IMODE((ROOT / LOCAL_POOLS_PATH).stat().st_mode) == 0o600
    for path in (AUTHORIZATION_PATH, POOL_MANIFEST_PATH, LATENCY_PATH):
        assert stat.S_IMODE((ROOT / path).stat().st_mode) == 0o644


def test_materialized_public_t3_files_have_no_row_level_data() -> None:
    payloads = [load(ROOT / path) for path in (AUTHORIZATION_PATH, POOL_MANIFEST_PATH, LATENCY_PATH)]
    assert not any(_contains_public_row_level_data(payload) for payload in payloads)
