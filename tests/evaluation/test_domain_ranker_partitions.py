from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import product_variant_resolver.domain_ranker_partitions as partition_module
from product_variant_resolver.domain_ranker_partitions import (
    AUTHORIZATION_PATH,
    CANDIDATE_LIMIT,
    LOCAL_PARTITIONS_PATH,
    LOCAL_POOLS_PATH,
    POOL_MANIFEST_PATH,
    POSITIVE_DEVELOPMENT_COUNT,
    POSITIVE_TEST_COUNT,
    RANKER_SELECTION_MINIMUM,
    RANKER_TRAIN_MINIMUM,
    SPLIT_MANIFEST_PATH,
    _contains_public_row_level_data,
    _target_rrf_rank,
    _validate_digest,
    build_authorization,
    build_candidate_pools,
    build_partitions,
    check,
)

ROOT = Path(__file__).resolve().parents[2]


class DeterministicScorer:
    version = "deterministic-test-scorer-v1"

    def score_pairs(self, pairs: list[tuple[str, str]]) -> tuple[float, ...]:
        return tuple(
            int.from_bytes(hashlib.sha256(f"{query}\0{text}".encode()).digest()[:4], "big")
            / 2**32
            for query, text in pairs
        )


@pytest.fixture(scope="module")
def built() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    authorization = build_authorization(ROOT)
    local_partitions, split_manifest = build_partitions(ROOT, authorization)
    local_pools, pool_manifest = build_candidate_pools(
        ROOT,
        authorization,
        local_partitions,
        split_manifest,
        scorer=DeterministicScorer(),
    )
    return authorization, local_partitions, split_manifest, local_pools, pool_manifest


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_partitioning_is_deterministic_and_family_evidence_safe(
    built: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
) -> None:
    authorization, local_partitions, split_manifest, _local_pools, _pool_manifest = built

    repeated_local, repeated_manifest = build_partitions(ROOT, authorization)

    assert repeated_local == local_partitions
    assert repeated_manifest == split_manifest
    counts = split_manifest["aggregate_counts"]
    assert counts["admitted_positive_development"] == POSITIVE_DEVELOPMENT_COUNT
    assert counts["ranker_train"] == 70
    assert counts["ranker_selection"] == 30
    assert counts["ranker_train"] >= RANKER_TRAIN_MINIMUM
    assert counts["ranker_selection"] >= RANKER_SELECTION_MINIMUM
    assert counts["permanently_excluded_positive_test"] == POSITIVE_TEST_COUNT
    assert all(value == 0 for value in split_manifest["zero_overlap_audit"].values())


def test_candidate_pools_are_deterministic_top25_and_do_not_adapt_on_holdouts(
    built: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
) -> None:
    authorization, local_partitions, split_manifest, local_pools, pool_manifest = built

    repeated_local, repeated_manifest = build_candidate_pools(
        ROOT,
        authorization,
        local_partitions,
        split_manifest,
        scorer=DeterministicScorer(),
    )

    assert repeated_local == local_pools
    assert repeated_manifest == pool_manifest
    assert len(local_pools["rows"]) == POSITIVE_DEVELOPMENT_COUNT
    assert all(0 < len(row["candidates"]) <= CANDIDATE_LIMIT for row in local_pools["rows"])
    counts = pool_manifest["aggregate_counts"]
    assert counts["positive_test_scored"] == 0
    assert counts["negative_holdout_scored"] == 0
    assert counts["no_match_ranker_scored"] == 0
    assert counts["target_injection_count"] == 0
    assert pool_manifest["guardrails"] == {
        "expected_target_passed_to_retriever": False,
        "hard_negatives_mined": 0,
        "model_training_runs": 0,
        "model_selection_runs": 0,
        "calibration_fits": 0,
        "fresh_final_reads": 0,
        "runtime_default_changed": False,
    }


def test_missing_target_is_observed_as_retrieval_miss_not_injected() -> None:
    candidates = [
        SimpleNamespace(canonical_uuid="00000000-0000-0000-0000-000000000001", rrf_rank=1)
    ]

    assert _target_rrf_rank("00000000-0000-0000-0000-000000000002", candidates) is None
    assert len(candidates) == 1


def test_expected_target_is_not_a_retriever_input_and_cannot_change_candidate_sequence(
    built: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization, local_partitions, split_manifest, _local_pools, _pool_manifest = built
    original_service = partition_module.CandidateRetrievalService
    captured_inputs: list[tuple[dict[str, Any], int]] = []

    class RetrievalSpy(original_service):  # type: ignore[misc, valid-type]
        def retrieve(self, signals: Any, limit: int) -> Any:
            signal_payload = signals.model_dump(mode="json")
            assert isinstance(signal_payload, dict)
            captured_inputs.append((signal_payload, limit))
            return super().retrieve(signals, limit)

    monkeypatch.setattr(partition_module, "CandidateRetrievalService", RetrievalSpy)
    first_local, _first_manifest = partition_module.build_candidate_pools(
        ROOT,
        authorization,
        local_partitions,
        split_manifest,
        scorer=DeterministicScorer(),
    )
    first_inputs = copy.deepcopy(captured_inputs)
    first_sequences = [
        [candidate["canonical_uuid"] for candidate in row["candidates"]]
        for row in first_local["rows"]
    ]

    changed_partitions = copy.deepcopy(local_partitions)
    changed_partitions["members"][0]["target_uuid"] = (
        "00000000-0000-0000-0000-000000000000"
    )
    monkeypatch.setattr(
        partition_module,
        "build_partitions",
        lambda _root, _authorization: (changed_partitions, split_manifest),
    )
    captured_inputs.clear()
    changed_local, _changed_manifest = partition_module.build_candidate_pools(
        ROOT,
        authorization,
        changed_partitions,
        split_manifest,
        scorer=DeterministicScorer(),
    )
    changed_sequences = [
        [candidate["canonical_uuid"] for candidate in row["candidates"]]
        for row in changed_local["rows"]
    ]

    assert captured_inputs == first_inputs
    assert changed_sequences == first_sequences
    assert len(captured_inputs) == POSITIVE_DEVELOPMENT_COUNT
    assert all(limit == CANDIDATE_LIMIT for _signals, limit in captured_inputs)
    assert all(
        not ({"target", "target_uuid", "expected", "expected_uuid"} & set(signals))
        for signals, _limit in captured_inputs
    )
    assert first_local["rows"][0]["target_uuid"] != changed_local["rows"][0]["target_uuid"]


def test_public_manifests_are_aggregate_only_and_local_artifacts_are_default_denied(
    built: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
) -> None:
    authorization, _local_partitions, split_manifest, _local_pools, pool_manifest = built

    assert not _contains_public_row_level_data(authorization)
    assert not _contains_public_row_level_data(split_manifest)
    assert not _contains_public_row_level_data(pool_manifest)
    serialized = json.dumps(
        [authorization, split_manifest, pool_manifest], ensure_ascii=False
    )
    assert "isr-" not in serialized
    assert "/Users/" not in serialized
    assert "http://" not in serialized
    assert "https://" not in serialized
    assert subprocess.run(
        ["git", "check-ignore", "-q", str(LOCAL_PARTITIONS_PATH)],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    assert subprocess.run(
        ["git", "check-ignore", "-q", str(LOCAL_POOLS_PATH)],
        cwd=ROOT,
        check=False,
    ).returncode == 0
    for public_path in (AUTHORIZATION_PATH, SPLIT_MANIFEST_PATH, POOL_MANIFEST_PATH):
        assert subprocess.run(
            ["git", "check-ignore", "-q", str(public_path)],
            cwd=ROOT,
            check=False,
        ).returncode == 1


def test_calibration_shortfall_is_explicit_without_reusing_ranker_members(
    built: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
) -> None:
    _authorization, _local_partitions, split_manifest, _local_pools, pool_manifest = built

    readiness = split_manifest["calibration_readiness"]
    assert readiness["catalog_present_family_disjoint_examples_available"] == 0
    assert readiness["exact_correctness_calibration_ready"] is False
    assert readiness["ranker_pool_work_may_continue_to_t3"] is True
    assert pool_manifest["retrieval"]["gate_passed"] is True


@pytest.mark.parametrize(
    ("index", "field", "name"),
    [
        (0, "authorization_sha256", "authorization"),
        (2, "manifest_sha256", "split manifest"),
        (4, "manifest_sha256", "pool manifest"),
    ],
)
def test_public_artifact_tamper_fails_closed(
    built: tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]],
    index: int,
    field: str,
    name: str,
) -> None:
    payload = copy.deepcopy(built[index])
    payload["status"] = "tampered"

    with pytest.raises(ValueError, match="checksum is stale"):
        _validate_digest(payload, field, name)


def test_materialized_artifacts_match_strict_checker() -> None:
    manifest = check(ROOT, require_local_artifacts=True)
    split_manifest = _load(ROOT / SPLIT_MANIFEST_PATH)

    assert manifest == _load(ROOT / POOL_MANIFEST_PATH)
    assert split_manifest["aggregate_counts"]["ranker_train"] == 70
    assert split_manifest["aggregate_counts"]["ranker_selection"] == 30
    assert manifest["guardrails"]["hard_negatives_mined"] == 0
    assert manifest["guardrails"]["model_training_runs"] == 0
    assert manifest["guardrails"]["runtime_default_changed"] is False
