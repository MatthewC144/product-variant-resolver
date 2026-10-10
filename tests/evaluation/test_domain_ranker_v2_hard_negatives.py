from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from product_variant_resolver.domain_ranker_v2_hard_negatives import (
    AUTHORIZATION_PATH,
    LOCAL_TRIPLES_PATH,
    MANIFEST_PATH,
    _conflicting_fields,
    _parse_candidate,
    build_authorization,
    build_mining_artifacts,
    check,
)

ROOT = Path(__file__).resolve().parents[2]


def load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_train_only_mining_exceeds_exact_release_density_gate() -> None:
    authorization = build_authorization(ROOT, "0" * 40)
    local, manifest = build_mining_artifacts(ROOT, authorization)
    counts = manifest["aggregate_counts"]
    assert counts == {
        "train_pool_count": 120,
        "qualifying_train_query_count": 112,
        "ineligible_train_query_count": 8,
        "defensible_same_casting_sibling_count": 340,
        "pairwise_triple_count": 332,
        "ambiguous_same_casting_sibling_count": 19,
        "held_sibling_count": 27,
        "held_sibling_counts_by_reason": {
            "no_query_supported_exact_field_conflict": 19,
            "query_has_fewer_than_two_defensible_siblings": 8,
        },
        "qualifying_query_counts_by_template": {
            "casting_year_toy_collector": 43,
            "toy_casting_collector_year": 50,
            "year_series_position_casting_collector": 19,
        },
        "validation_label_read_count": 0,
        "selection_label_read_count": 0,
        "model_training_run_count": 0,
        "selection_quality_evaluation_count": 0,
    }
    triples = local["triples"]
    assert isinstance(triples, list)
    assert len(triples) == 332
    assert {triple["negative_category"] for triple in triples} == {
        "same_casting_wrong_exact_release"
    }
    assert all(triple["conflicting_query_fields"] for triple in triples)


def test_ambiguous_sibling_without_query_supported_conflict_is_held() -> None:
    target = {
        "release_year": 2026,
        "series": "Factory Fresh",
        "series_position": "4/5",
        "collector_number": "114",
        "toy_number": "JPD55",
    }
    candidate = _parse_candidate(
        "brand=hot wheels | casting=custom '66 toronado | year=2026 | "
        "series=factory fresh | color=<missing> | collector=114 | series_position=4/5 | "
        "edition=<missing> | aliases=custom '66 toronado | identifiers=114; jpd55"
    )
    assert (
        _conflicting_fields(
            target,
            candidate,
            ("release_year", "toy_number", "collector_number"),
        )
        == []
    )


def test_candidate_identifier_parser_fails_closed() -> None:
    with pytest.raises(ValueError, match="one toy and collector"):
        _parse_candidate(
            "brand=hot wheels | casting=x | year=2026 | series=y | color=<missing> | "
            "collector=001 | series_position=1/5 | edition=<missing> | aliases=x | "
            "identifiers=001"
        )


def test_t4_authorization_does_not_authorize_training_or_protected_partition_labels() -> None:
    authorization = build_authorization(ROOT, "0" * 40)
    assert "read_validation_or_selection_labels_for_mining" in authorization["prohibited_actions"]
    assert (
        "model_training_checkpoint_creation_or_selection_scoring"
        in authorization["prohibited_actions"]
    )
    assert authorization["mining_protocol"]["minimum_qualifying_query_count"] == 60


def test_materialized_t4_artifacts_replay_and_remain_private() -> None:
    manifest = check(ROOT)
    assert manifest["status"] == "pairwise_mining_ready"
    assert manifest["next_allowed_action"] == "DRV2-T5_requires_separate_owner_authorization"
    assert stat.S_IMODE((ROOT / LOCAL_TRIPLES_PATH).stat().st_mode) == 0o600
    for path in (AUTHORIZATION_PATH, MANIFEST_PATH):
        assert stat.S_IMODE((ROOT / path).stat().st_mode) == 0o644


def test_public_t4_files_are_aggregate_only() -> None:
    payloads = [load(ROOT / path) for path in (AUTHORIZATION_PATH, MANIFEST_PATH)]
    text = json.dumps(payloads, ensure_ascii=False).casefold()
    assert "drv2-q001" not in text
    assert "positive_text" not in text
    assert "negative_text" not in text
    assert "expected_full_identity" not in text
