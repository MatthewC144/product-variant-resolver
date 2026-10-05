from __future__ import annotations

import json
from pathlib import Path

import pytest

from product_variant_resolver.pointwise_no_match_readiness import (
    FIT_COUNT,
    OUTPUT,
    SELECTION_COUNT,
    build_readiness,
    check,
    classify_candidates,
)

ROOT = Path(__file__).resolve().parents[2]


def test_actual_readiness_is_reproducible_and_aggregate_only() -> None:
    payload = check(ROOT, require_local_inputs=True)
    assert payload == build_readiness(ROOT)
    assert payload["audit"]["exact_family_absent_count"] == 52
    assert payload["prospective_split"]["fit_count"] == FIT_COUNT
    assert payload["prospective_split"]["selection_count"] == SELECTION_COUNT
    assert payload["permission"]["permission_changed"] is False
    assert payload["guardrails"]["final_test_cases_read"] == 0
    assert payload["guardrails"]["neural_model_loaded"] is False


def test_candidate_rule_requires_confirmed_query_and_exact_family_absence() -> None:
    source = [{"parse_status": "parsed", "brand": "Hot Wheels", "casting_name": "Known Car"}]
    human = [
        {
            "case_id": "present",
            "initial_name": "real known listing",
            "human_label_confidence": "confirmed",
            "human_label_brand": "HOT WHEELS",
            "human_label_casting": "Known Car",
        },
        {
            "case_id": "absent",
            "initial_name": "real absent listing",
            "human_label_confidence": "confirmed",
            "human_label_brand": "Hot Wheels",
            "human_label_casting": "Absent Car",
        },
        {
            "case_id": "other-brand",
            "initial_name": "real matchbox listing",
            "human_label_confidence": "confirmed",
            "human_label_brand": "Matchbox",
            "human_label_casting": "Known Car",
        },
        {
            "case_id": "missing-query",
            "initial_name": None,
            "human_label_confidence": "confirmed",
            "human_label_brand": "Hot Wheels",
            "human_label_casting": "Absent Two",
        },
    ]
    candidates, counts = classify_candidates(human, source)
    assert [candidate.case_id for candidate in candidates] == ["absent", "other-brand"]
    assert counts["exact_family_present_count"] == 1
    assert counts["same_brand_absent_count"] == 1
    assert counts["other_brand_absent_count"] == 1
    assert counts["missing_query_count"] == 1


def test_check_rejects_row_level_output(tmp_path: Path) -> None:
    destination = tmp_path / OUTPUT
    destination.parent.mkdir(parents=True)
    payload = json.loads((ROOT / OUTPUT).read_text(encoding="utf-8"))
    payload["cases"] = [{"case_id": "forbidden"}]
    destination.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="row-level"):
        check(tmp_path)
