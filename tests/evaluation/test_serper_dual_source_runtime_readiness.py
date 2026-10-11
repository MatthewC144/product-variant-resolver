from __future__ import annotations

import json
from pathlib import Path

import pytest

from product_variant_resolver.serper_dual_source_runtime_readiness import (
    FRESH_NO_MATCH_HOLDOUT_TARGETS,
    FRESH_POSITIVE_HOLDOUT_TARGETS,
    NEW_NO_MATCH_DEVELOPMENT_TARGETS,
    OUTPUT,
    build_readiness,
    check,
)

ROOT = Path(__file__).resolve().parents[2]


def test_frozen_readiness_is_reproducible_and_fail_closed() -> None:
    payload = check(ROOT)
    assert payload == build_readiness(ROOT)
    assert payload["status"] == "blocked_missing_source_matched_policy_data"
    assert payload["legacy_policy_evidence"]["runtime_eligible"] is False
    assert payload["guardrails"]["runtime_activation_authorized"] is False
    assert payload["guardrails"]["final_observations_scored"] == 0


def test_next_dataset_contract_is_minimal_grouped_and_fresh() -> None:
    contract = build_readiness(ROOT)["next_dataset_contract"]
    assert contract["new_no_match_development_target_count"] == (
        NEW_NO_MATCH_DEVELOPMENT_TARGETS
    )
    assert contract["fresh_positive_holdout_target_count"] == (
        FRESH_POSITIVE_HOLDOUT_TARGETS
    )
    assert contract["fresh_no_match_holdout_target_count"] == (
        FRESH_NO_MATCH_HOLDOUT_TARGETS
    )
    assert contract["new_identity_count"] == 80
    assert contract["new_source_observation_count"] == 160
    assert contract["source_types"] == ["image_search", "shopping"]
    assert contract["group_by_identity_before_split"] is True
    assert contract["existing_50_target_ranking_final_may_be_reused"] is False


def test_missing_evidence_does_not_silently_reuse_legacy_policy() -> None:
    payload = build_readiness(ROOT)
    assert payload["legacy_policy_evidence"]["dual_source_transfer_validated"] is False
    assert payload["missing_evidence"]["dual_source_no_match_development_target_count"] == 0
    assert payload["missing_evidence"]["fresh_policy_evaluation"] is False
    assert payload["next_allowed_action"] == (
        "collect_and_freeze_the_minimal_dual_source_policy_dataset"
    )


def test_build_rejects_frozen_dataset_drift(tmp_path: Path) -> None:
    dataset = ROOT / "data/evaluation/serper-dual-source-query-v1/dataset.json"
    relative = dataset.relative_to(ROOT)
    copied = tmp_path / relative
    copied.parent.mkdir(parents=True)
    copied.write_bytes(dataset.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="dataset differs"):
        build_readiness(tmp_path)


def test_check_rejects_row_level_fields(tmp_path: Path) -> None:
    destination = tmp_path / OUTPUT
    destination.parent.mkdir(parents=True)
    payload = json.loads((ROOT / OUTPUT).read_text(encoding="utf-8"))
    payload["query_raw"] = "forbidden"
    destination.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="row-level"):
        check(tmp_path)
