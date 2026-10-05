from __future__ import annotations

import json
from pathlib import Path

import pytest

from product_variant_resolver.pointwise_no_match_governance import (
    AUTHORIZATION_PATH,
    _validate_authorization,
    build_authorization,
    build_overlay,
    check,
)

ROOT = Path(__file__).resolve().parents[2]


def test_materialized_owner_authorization_and_overlay_are_exact() -> None:
    authorization = build_authorization(ROOT)
    overlay = check(ROOT)
    assert json.loads((ROOT / AUTHORIZATION_PATH).read_text()) == authorization
    assert overlay == build_overlay(ROOT, authorization)
    assert overlay["permissions"]["pointwise_development_calibration_fit"] is True
    assert overlay["permissions"]["pointwise_development_threshold_selection"] is True
    assert overlay["permissions"]["runtime_activation"] is False
    assert overlay["guardrails"]["final_test_cases_read"] == 0


def test_authorization_rejects_changed_owner_scope() -> None:
    authorization = build_authorization(ROOT)
    authorization["allowed_actions"].append("runtime_activation")
    with pytest.raises(ValueError, match="stale, generic, or out of scope"):
        _validate_authorization(authorization, ROOT)


def test_overlay_keeps_original_dataset_contract_unchanged() -> None:
    source = json.loads((ROOT / "data/human_labeled_names.json").read_text())
    overlay = check(ROOT)
    assert "calibration_training" in source["excluded_from"]
    assert "threshold_selection" in source["excluded_from"]
    assert overlay["scope"]["source_contract_overwritten"] is False
    assert overlay["scope"]["source_wide_permission_promotion"] is False
