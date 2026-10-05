from __future__ import annotations

import json
from pathlib import Path

import pytest

from product_variant_resolver.pointwise_policy_holdout_readiness import (
    EXPECTED_SOURCE_INVENTORY,
    MINIMUM_UNTOUCHED_NO_MATCH_COUNT,
    OUTPUT,
    build_readiness,
    check,
)

ROOT = Path(__file__).resolve().parents[2]


def test_actual_holdout_readiness_is_reproducible_and_fail_closed() -> None:
    payload = check(ROOT)
    assert payload == build_readiness(ROOT, EXPECTED_SOURCE_INVENTORY)
    audit = payload["independence_audit"]
    assert payload["status"] == "holdout_not_ready"
    assert audit["eligible_untouched_labeled_no_match_count"] == 0
    assert audit["shortfall_count"] == MINIMUM_UNTOUCHED_NO_MATCH_COUNT
    assert payload["frozen_policy"]["runtime_eligible"] is False
    assert payload["guardrails"]["final_test_cases_read"] == 0
    assert payload["guardrails"]["policy_evaluation_performed"] is False


def test_inventory_proves_other_local_rows_are_not_new_labeled_queries() -> None:
    by_id = {item["source_id"]: item for item in EXPECTED_SOURCE_INVENTORY}
    assert by_id["human_labeling_queue"]["untracked_case_count"] == 4
    assert by_id["human_labeling_queue"]["untracked_human_answer_count"] == 0
    assert by_id["resolver_comparison_rows"]["untracked_case_count"] == 0
    assert by_id["candidate_evidence_rows"]["untracked_case_count"] == 0
    assert sum(item["eligible_untouched_labeled_no_match_count"] for item in by_id.values()) == 0


def test_build_rejects_unreviewed_inventory_change() -> None:
    changed = json.loads(json.dumps(EXPECTED_SOURCE_INVENTORY))
    changed[0]["untracked_human_answer_count"] = 1
    with pytest.raises(ValueError, match="frozen aggregate"):
        build_readiness(ROOT, changed)


def test_check_rejects_row_level_data(tmp_path: Path) -> None:
    destination = tmp_path / OUTPUT
    destination.parent.mkdir(parents=True)
    payload = json.loads((ROOT / OUTPUT).read_text(encoding="utf-8"))
    payload["case_ids"] = ["forbidden"]
    destination.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="row-level"):
        check(tmp_path)
