from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from product_variant_resolver.release_casting_review import (
    STATUSES,
    build_public_manifest,
    build_review_queue,
    normalize_review_text,
)
from product_variant_resolver.release_staging import SOURCE_RIGHTS_STATE

ROOT = Path(__file__).resolve().parents[2]


def record(source_id: str, toy_number: str, casting: str, *, year: int = 2025) -> dict[str, Any]:
    return {
        "source_record_id": source_id,
        "brand": "Hot Wheels",
        "casting_name": casting,
        "release_year": year,
        "toy_number": toy_number,
        "review_status": "needs_canonical_review",
        "usage": "staging_only_not_evaluation_or_canonical",
        "canonical_uuid": None,
        "color": None,
    }


def inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    snapshot = {
        "batch_id": "local-release-staging-v1-" + "a" * 64,
        "content_sha256": "a" * 64,
        "source_rights_state": SOURCE_RIGHTS_STATE,
        "records": [
            record("r-1", "T-1", "Toyota Supra"),
            record("r-2", "T-2", "Bone Shaker"),
            record("r-3", "T-3", "Ford Escort RS2000"),
            record("r-4", "T-4", "Coupé Clip", year=2024),
            record("r-5", "T-5", "Coupe Clip"),
            record("r-6", "T-6", "Mystery Mobile"),
        ],
    }
    canonical = {
        "products": [
            {
                "brand": "Hot Wheels",
                "casting": "Toyota Supra",
                "canonical_id": "supra-red",
                "canonical_uuid": "10000000-0000-0000-0000-000000000001",
            },
            {
                "brand": "Hot Wheels",
                "casting": "Toyota Supra",
                "canonical_id": "supra-blue",
                "canonical_uuid": "10000000-0000-0000-0000-000000000002",
            },
            {
                "brand": "Hot Wheels",
                "casting": "Bone Shaker",
                "canonical_id": "bone-shaker-red",
                "canonical_uuid": "10000000-0000-0000-0000-000000000003",
            },
        ]
    }
    human = {
        "castings": [
            {
                "brand": "Hot Wheels",
                "casting": "Toyota Supra",
                "casting_id": "human-toyota-supra",
                "casting_uuid": "20000000-0000-0000-0000-000000000001",
            },
            {
                "brand": "Hot Wheels",
                "casting": "Ford Escort RS2000",
                "casting_id": "human-ford-escort-rs2000",
                "casting_uuid": "20000000-0000-0000-0000-000000000002",
            },
        ]
    }
    return snapshot, canonical, human


def test_exact_candidate_classes_remain_review_only() -> None:
    queue = build_review_queue(*inputs())
    summary = queue["summary"]
    assert summary["staged_observations"] == 6
    assert summary["raw_casting_labels"] == 6
    assert summary["normalized_review_clusters"] == 5
    assert summary["normalization_collision_clusters"] == 1
    assert summary["candidate_cluster_counts"] == {
        "exact_both_sources": 1,
        "exact_canonical_fixture_only": 1,
        "exact_human_draft_only": 1,
        "no_exact_candidate": 2,
    }
    assert summary["candidate_observation_counts"]["no_exact_candidate"] == 3
    assert summary["approved_casting_links"] == 0
    assert summary["canonical_promotions"] == 0
    assert all(item["promotion_eligible"] is False for item in queue["clusters"])
    assert all(item["canonical_uuid"] is None for item in queue["clusters"])


def test_fixture_variants_are_one_family_candidate_not_automatic_variant_matches() -> None:
    queue = build_review_queue(*inputs())
    supra = next(
        item for item in queue["clusters"] if item["normalized_key"]["casting"] == "toyota supra"
    )
    candidate = supra["canonical_fixture_candidate"]
    assert candidate["product_count"] == 2
    assert candidate["canonical_ids"] == ["supra-blue", "supra-red"]
    assert supra["promotion_decision"] == "hold_for_human_review"


def test_normalization_collision_preserves_raw_labels() -> None:
    queue = build_review_queue(*inputs())
    clip = next(
        item for item in queue["clusters"] if item["normalized_key"]["casting"] == "coupe clip"
    )
    assert normalize_review_text("Coupé Clip") == "coupe clip"
    assert clip["normalization_collision"] is True
    assert clip["observed_casting_labels"] == ["Coupe Clip", "Coupé Clip"]
    assert clip["source_record_ids"] == ["r-4", "r-5"]
    assert clip["review_priority"] == 4


def test_queue_is_deterministic_when_inputs_are_reordered() -> None:
    snapshot, canonical, human = inputs()
    first = build_review_queue(snapshot, canonical, human)
    snapshot["records"].reverse()
    canonical["products"].reverse()
    human["castings"].reverse()
    assert build_review_queue(snapshot, canonical, human) == first


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("review_status", "approved", "needs_canonical_review"),
        ("usage", "runtime", "non-staging usage"),
        ("canonical_uuid", "10000000-0000-0000-0000-000000000001", "canonical UUID"),
        ("color", "Red", "cannot infer or accept color"),
    ],
)
def test_changed_staging_authority_fails_closed(field: str, value: str, message: str) -> None:
    snapshot, canonical, human = inputs()
    snapshot["records"][0][field] = value
    with pytest.raises(ValueError, match=message):
        build_review_queue(snapshot, canonical, human)


def test_public_manifest_contains_counts_and_hashes_but_no_private_queue() -> None:
    snapshot, canonical, human = inputs()
    queue = build_review_queue(snapshot, canonical, human)
    manifest = build_public_manifest(
        queue,
        snapshot,
        canonical_sha256="b" * 64,
        human_sha256="c" * 64,
    )
    text = json.dumps(manifest, ensure_ascii=False, sort_keys=True)
    assert manifest["public_scope"].endswith("no_source_rows_or_casting_labels")
    assert len(manifest["private_queue_sha256"]) == 64
    assert "clusters" not in manifest
    assert "Toyota Supra" not in text
    assert "r-1" not in text
    assert set(manifest["summary"]["candidate_cluster_counts"]) == set(STATUSES)


def test_owner_snapshot_has_expected_review_aggregate_when_present() -> None:
    staging = ROOT / "data/external/hot-wheels-wiki/local-export-2023-2026/normalized.json"
    if not staging.is_file():
        pytest.skip("owner-supplied normalized snapshot is local and unpublished")
    snapshot = json.loads(staging.read_text(encoding="utf-8"))
    canonical = json.loads((ROOT / "data/catalog.json").read_text(encoding="utf-8"))
    human = json.loads((ROOT / "data/human_backed_catalog.json").read_text(encoding="utf-8"))
    summary = build_review_queue(snapshot, canonical, human)["summary"]
    assert summary == {
        "staged_observations": 1763,
        "raw_casting_labels": 678,
        "normalized_review_clusters": 676,
        "normalization_collision_clusters": 2,
        "candidate_cluster_counts": {
            "exact_both_sources": 1,
            "exact_canonical_fixture_only": 2,
            "exact_human_draft_only": 40,
            "no_exact_candidate": 633,
        },
        "candidate_observation_counts": {
            "exact_both_sources": 1,
            "exact_canonical_fixture_only": 8,
            "exact_human_draft_only": 126,
            "no_exact_candidate": 1628,
        },
        "unresolved_review_clusters": 676,
        "approved_casting_links": 0,
        "canonical_promotions": 0,
        "reviewed_colors": 0,
        "network_requests": 0,
    }


def test_committed_public_manifest_is_privacy_bounded() -> None:
    path = ROOT / "reports/local-release-casting-review-v1/manifest.json"
    if not path.is_file():
        pytest.skip("public aggregate is created after the first local queue build")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["summary"]["normalized_review_clusters"] == 676
    assert manifest["summary"]["canonical_promotions"] == 0
    assert set(manifest) == {
        "schema_version",
        "review_version",
        "status",
        "public_scope",
        "source_rights_state",
        "source_batch_id",
        "source_content_sha256",
        "canonical_catalog_sha256",
        "human_catalog_sha256",
        "private_queue_sha256",
        "summary",
    }
