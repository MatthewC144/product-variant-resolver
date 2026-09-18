from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from product_variant_resolver.release_casting_review_batch import (
    SELECTED_CLUSTER_IDS,
    build_owner_batch,
    build_public_manifest,
    render_private_report,
)

ROOT = Path(__file__).resolve().parents[2]


def source_record(source_id: str, label: str, number: int) -> dict[str, Any]:
    return {
        "source_record_id": source_id,
        "release_year": 2023 + number % 3,
        "toy_number": f"T-{number}",
        "collector_number": f"{number:03d}",
        "source_model_label": label,
        "casting_name": label,
        "variant_note": "2nd Color" if number == 2 else None,
        "series": "Synthetic Series",
        "series_position": "1/5",
        "color": None,
    }


def cluster(
    cluster_id: str,
    source_id: str,
    label: str,
    *,
    match_status: str,
    collision: bool = False,
) -> dict[str, Any]:
    canonical = None
    human: list[dict[str, Any]] = []
    if match_status in {"exact_both_sources", "exact_canonical_fixture_only"}:
        canonical = {
            "brand": ["Hot Wheels"],
            "casting": [label],
            "product_count": 2,
            "canonical_ids": [f"synthetic-{cluster_id}-1", f"synthetic-{cluster_id}-2"],
            "canonical_uuids": [],
            "authority": "synthetic_fixture_not_real_catalog_truth",
        }
    if match_status == "exact_both_sources":
        human = [
            {
                "brand": "Hot Wheels",
                "casting": label,
                "casting_id": f"human-{cluster_id}",
                "casting_uuid": "20000000-0000-0000-0000-000000000001",
                "authority": "human_backed_draft_not_canonical_truth",
            }
        ]
    labels = [label, f"{label} Alt"] if collision else [label]
    return {
        "review_cluster_id": cluster_id,
        "normalized_key": {"brand": "hot wheels", "casting": label.casefold()},
        "observed_casting_labels": labels,
        "normalization_collision": collision,
        "source_record_ids": [source_id],
        "match_status": match_status,
        "canonical_fixture_candidate": canonical,
        "human_draft_candidates": human,
        "promotion_decision": "hold_for_human_review",
        "promotion_eligible": False,
        "canonical_uuid": None,
    }


def inputs() -> tuple[dict[str, Any], dict[str, Any], tuple[str, ...]]:
    selected = ("q-1", "q-2", "q-3", "q-4", "q-5")
    queue = {
        "status": "human_review_required",
        "source_batch_id": "source-batch-1",
        "clusters": [
            cluster("q-1", "r-1", "Alpha", match_status="exact_both_sources"),
            cluster("q-2", "r-2", "Beta", match_status="no_exact_candidate", collision=True),
            cluster("q-3", "r-3", "Gamma", match_status="no_exact_candidate", collision=True),
            cluster("q-4", "r-4", "Delta", match_status="exact_canonical_fixture_only"),
            cluster("q-5", "r-5", "Epsilon", match_status="exact_canonical_fixture_only"),
        ],
    }
    snapshot = {
        "batch_id": "source-batch-1",
        "records": [
            source_record("r-1", "Alpha", 1),
            source_record("r-2", "Beta", 2),
            source_record("r-3", "Gamma", 3),
            source_record("r-4", "Delta", 4),
            source_record("r-5", "Epsilon", 5),
        ],
    }
    return queue, snapshot, selected


def test_batch_has_five_unanswered_questions_and_fixed_decision_semantics() -> None:
    queue, snapshot, selected = inputs()
    packet = build_owner_batch(queue, snapshot, selected_ids=selected)
    assert packet["summary"] == {
        "selected_review_clusters": 5,
        "selected_source_observations": 5,
        "selection_kind_counts": {
            "cross_source_exact_candidate": 1,
            "normalization_collision": 2,
            "synthetic_fixture_name_candidate": 2,
        },
        "pending_owner_decisions": 5,
        "recorded_owner_decisions": 0,
        "approved_casting_links": 0,
        "canonical_promotions": 0,
        "reviewed_colors": 0,
        "postgresql_writes": 0,
        "network_requests": 0,
    }
    assert all(item["decision"] is None for item in packet["questions"])
    assert all(item["decision_status"] == "pending_owner" for item in packet["questions"])
    assert all(
        item["allowed_decisions"] == ["same_review_family", "keep_separate", "unknown"]
        for item in packet["questions"]
    )


def test_private_report_explains_that_same_family_is_not_variant_approval() -> None:
    queue, snapshot, selected = inputs()
    report = render_private_report(build_owner_batch(queue, snapshot, selected_ids=selected))
    assert "does not approve a release variant, color, or canonical product" in report
    assert "Alpha" in report
    assert "2nd Color" in report


def test_batch_is_deterministic_for_identical_inputs() -> None:
    queue, snapshot, selected = inputs()
    first = build_owner_batch(queue, snapshot, selected_ids=selected)
    assert (
        build_owner_batch(copy.deepcopy(queue), copy.deepcopy(snapshot), selected_ids=selected)
        == first
    )


def test_selected_cluster_cannot_bypass_hold_boundary() -> None:
    queue, snapshot, selected = inputs()
    queue["clusters"][0]["promotion_eligible"] = True
    with pytest.raises(ValueError, match="promotion eligible"):
        build_owner_batch(queue, snapshot, selected_ids=selected)


def test_source_color_is_rejected_even_when_other_evidence_is_valid() -> None:
    queue, snapshot, selected = inputs()
    snapshot["records"][0]["color"] = "Red"
    with pytest.raises(ValueError, match="cannot accept or infer source color"):
        build_owner_batch(queue, snapshot, selected_ids=selected)


def test_missing_source_record_is_rejected() -> None:
    queue, snapshot, selected = inputs()
    snapshot["records"] = snapshot["records"][1:]
    with pytest.raises(ValueError, match="absent from staging"):
        build_owner_batch(queue, snapshot, selected_ids=selected)


def test_public_manifest_has_no_private_labels_or_rows() -> None:
    queue, snapshot, selected = inputs()
    manifest = build_public_manifest(build_owner_batch(queue, snapshot, selected_ids=selected))
    text = json.dumps(manifest, sort_keys=True)
    assert manifest["public_scope"].endswith("no_labels_toy_numbers_or_source_rows")
    assert "questions" not in manifest
    assert "Alpha" not in text
    assert "T-1" not in text
    assert manifest["summary"]["pending_owner_decisions"] == 5


def test_current_private_queue_builds_exact_batch_01_when_present() -> None:
    queue_path = ROOT / "data/external/hot-wheels-wiki/local-release-casting-review-v1/queue.json"
    snapshot_path = ROOT / "data/external/hot-wheels-wiki/local-export-2023-2026/normalized.json"
    if not queue_path.is_file() or not snapshot_path.is_file():
        pytest.skip("private owner review inputs are local and unpublished")
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    packet = build_owner_batch(queue, snapshot)
    assert [item["review_cluster_id"] for item in packet["questions"]] == list(SELECTED_CLUSTER_IDS)
    assert packet["summary"]["selected_source_observations"] == 18
    assert packet["summary"]["selection_kind_counts"] == {
        "cross_source_exact_candidate": 1,
        "normalization_collision": 2,
        "synthetic_fixture_name_candidate": 2,
    }
    assert packet["summary"]["recorded_owner_decisions"] == 0


def test_committed_public_manifest_freezes_pending_batch_without_labels() -> None:
    path = ROOT / "reports/local-release-casting-review-batch-01/manifest.json"
    if not path.is_file():
        pytest.skip("public batch aggregate is created after the first local packet build")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["summary"]["selected_review_clusters"] == 5
    assert manifest["summary"]["selected_source_observations"] == 18
    assert manifest["summary"]["pending_owner_decisions"] == 5
    assert manifest["summary"]["canonical_promotions"] == 0
    assert "questions" not in manifest
