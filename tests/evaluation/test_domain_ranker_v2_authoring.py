from __future__ import annotations

import json
import re
import stat
from pathlib import Path

import pytest

from product_variant_resolver.domain_ranker_v2_authoring import (
    AUTHORIZATION_T2_PATH,
    LOCAL_QUERY_PACK_PATH,
    PARTITION_COUNTS,
    QUERY_MANIFEST_PATH,
    SPLIT_MANIFEST_PATH,
    _contains_public_row_level_key,
    build_query_pack,
    check,
)

ROOT = Path(__file__).resolve().parents[2]


def load(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_t2_pack_is_deterministic_and_exactly_180_rows() -> None:
    first = build_query_pack(ROOT)
    second = build_query_pack(ROOT)
    assert first == second
    records = first["records"]
    assert isinstance(records, list)
    assert len(records) == 180
    assert len({row["query"] for row in records}) == 180
    assert len({json.dumps(row["expected_full_identity"], sort_keys=True) for row in records}) == 180
    assert len({row["family_group_sha256"] for row in records}) == 180


def test_t2_partitions_are_family_disjoint_and_have_frozen_counts() -> None:
    records = build_query_pack(ROOT)["records"]
    assert isinstance(records, list)
    groups = {
        partition: {row["family_group_sha256"] for row in records if row["partition"] == partition}
        for partition in PARTITION_COUNTS
    }
    assert {name: len(values) for name, values in groups.items()} == PARTITION_COUNTS
    assert groups["ranker_train"].isdisjoint(groups["ranker_validation"])
    assert groups["ranker_train"].isdisjoint(groups["ranker_selection"])
    assert groups["ranker_validation"].isdisjoint(groups["ranker_selection"])


def test_t2_rows_contain_only_authorized_identity_fields() -> None:
    records = build_query_pack(ROOT)["records"]
    assert isinstance(records, list)
    for row in records:
        assert set(row["expected_full_identity"]) == {
            "brand",
            "casting",
            "release_year",
            "series",
            "collector_number",
            "series_position",
            "toy_number",
        }
        text = json.dumps(row, ensure_ascii=False).casefold()
        assert "http://" not in text and "https://" not in text
        assert "color" not in row["expected_full_identity"]
        assert "edition" not in row["expected_full_identity"]


def test_public_t2_artifacts_are_aggregate_only() -> None:
    payloads = [
        load(ROOT / path)
        for path in (AUTHORIZATION_T2_PATH, QUERY_MANIFEST_PATH, SPLIT_MANIFEST_PATH)
    ]
    assert not any(_contains_public_row_level_key(payload) for payload in payloads)
    text = json.dumps(payloads, ensure_ascii=False).casefold()
    assert "http://" not in text and "https://" not in text
    assert re.search(r"drv2-q\d{3}", text) is None


def test_t2_check_proves_zero_leakage_and_keeps_t3_gated() -> None:
    manifest = check(ROOT)
    assert manifest["partition_counts"] == dict(sorted(PARTITION_COUNTS.items()))
    assert manifest["cross_partition_overlap_counts"] == {
        "normalized_query": 0,
        "exact_identity": 0,
        "casting_family": 0,
    }
    assert manifest["exact_density_readiness"][
        "train_queries_with_at_least_two_same_family_siblings"
    ] == 120
    assert manifest["exact_density_readiness"]["candidate_labels_created"] == 0
    assert manifest["next_allowed_action"] == "DRV2-T3_requires_separate_owner_authorization"


def test_private_pack_is_mode_0600() -> None:
    assert stat.S_IMODE((ROOT / LOCAL_QUERY_PACK_PATH).stat().st_mode) == 0o600


def test_t2_detects_private_pack_tampering(tmp_path: Path) -> None:
    target = tmp_path / "query-pack.json"
    target.write_bytes((ROOT / LOCAL_QUERY_PACK_PATH).read_bytes())
    payload = load(target)
    payload["status"] = "tampered"
    target.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="checksum is stale"):
        from product_variant_resolver.domain_ranker_v2_governance import _validate_digest

        _validate_digest(payload, "query_pack_sha256", "local v2 query pack")
