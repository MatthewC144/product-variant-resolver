from __future__ import annotations

import json
from pathlib import Path

from product_variant_resolver.domain_ranker_v2_governance import (
    AUTHORIZATION_PATH,
    GOVERNANCE_PATH,
    PROTOCOL_PATH,
    _contains_row_level_key,
    audit_source_capacity,
    check,
)

ROOT = Path(__file__).resolve().parents[2]


def load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_source_capacity_excludes_all_existing_positive_identities() -> None:
    assert audit_source_capacity(ROOT) == {
        "catalog_record_count": 1763,
        "positive_identity_denylist_count": 153,
        "combined_query_denylist_count": 173,
        "remaining_catalog_rows": 1610,
        "eligible_catalog_rows": 1041,
        "eligible_casting_families": 269,
        "minimum_family_release_count": 3,
        "authoring_capacity_passed": True,
    }


def test_materialized_governance_is_valid_and_training_stays_blocked() -> None:
    governance = check(ROOT)
    assert governance["status"] == "active_for_source_and_authoring_readiness_only"
    assert governance["permissions"]["pairwise_model_training"] is False
    assert governance["permissions"]["candidate_pool_scoring"] is False
    assert governance["permissions"]["future_local_owner_authored_query_materialization"] is True
    assert governance["next_allowed_action"] == "DRV2-T2_requires_separate_owner_authorization"


def test_public_governance_is_aggregate_only_and_has_no_source_urls() -> None:
    payloads = [load(ROOT / path) for path in (AUTHORIZATION_PATH, PROTOCOL_PATH, GOVERNANCE_PATH)]
    assert not any(_contains_row_level_key(payload) for payload in payloads)
    text = json.dumps(payloads, ensure_ascii=False).casefold()
    assert "http://" not in text
    assert "https://" not in text
    assert "/users/" not in text
    assert "query_text" not in text


def test_protocol_freezes_minima_and_disallows_t5_feedback() -> None:
    protocol = load(ROOT / PROTOCOL_PATH)
    assert protocol["required_query_count"] == 180
    assert protocol["minimum_partition_counts"] == {
        "ranker_train": 120,
        "ranker_validation": 30,
        "ranker_selection": 30,
    }
    assert protocol["resolver_output_access_during_authoring"] is False
    assert protocol["t5_error_or_prediction_access_during_authoring"] is False
    assert protocol["color_and_edition_label_authority"] is False
