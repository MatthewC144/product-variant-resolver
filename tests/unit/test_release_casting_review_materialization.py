from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

import product_variant_resolver.release_casting_review_materialization as materialization
from product_variant_resolver.release_casting_review_decisions import append_event
from product_variant_resolver.release_casting_review_materialization import (
    build_public_manifest,
    build_registry,
    publish_outputs,
    validate_registry,
)

ROOT = Path(__file__).resolve().parents[2]


def packet() -> dict[str, Any]:
    questions = []
    for ordinal in range(1, 6):
        questions.append(
            {
                "ordinal": ordinal,
                "review_cluster_id": f"cluster-{ordinal}",
                "selection_kind": "test_candidate",
                "observed_casting_labels": [f"Casting {ordinal}"],
                "normalized_key": {
                    "brand": "hot wheels",
                    "casting": f"casting {ordinal}",
                },
                "source_observations": [
                    {
                        "source_record_id": f"source-{ordinal}",
                        "release_year": 2020 + ordinal,
                        "toy_number": f"TEST-{ordinal}",
                        "collector_number": str(ordinal),
                        "source_model_label": f"Casting {ordinal}",
                        "casting_name": f"Casting {ordinal}",
                        "variant_note": None,
                        "series": "Test Series",
                        "series_position": f"{ordinal}/5",
                    }
                ],
                "candidate_evidence": {
                    "canonical_fixture": {"canonical_ids": [f"fixture-{ordinal}"]},
                    "human_draft": [],
                },
                "allowed_decisions": [
                    "same_review_family",
                    "keep_separate",
                    "unknown",
                ],
                "canonical_uuid": None,
                "color_decision": None,
            }
        )
    return {
        "schema_version": "test-packet-v1",
        "packet_version": "test-packet-01",
        "packet_sha256": "a" * 64,
        "batch_id": "batch-01-" + "a" * 64,
        "questions": questions,
    }


def ledger_for(
    current_packet: dict[str, Any],
    decisions: tuple[str, ...] = ("same_review_family",) * 5,
) -> dict[str, Any]:
    ledger = None
    for ordinal, decision in enumerate(decisions, start=1):
        ledger = append_event(
            current_packet,
            ledger,
            question_ordinal=ordinal,
            decision=decision,
            owner_response_verbatim=decision,
            decided_at=f"2026-09-18T00:0{ordinal}:00Z",
        )
    assert ledger is not None
    return ledger


def test_complete_ledger_materializes_review_relationships_only() -> None:
    current_packet = packet()
    registry = build_registry(current_packet, ledger_for(current_packet))
    assert registry["status"] == "complete_review_layer_only"
    assert len(registry["relationships"]) == 5
    assert registry["decision_exclusions"] == []
    assert registry["summary"]["held_source_references"] == 5
    assert registry["summary"]["canonical_promotions"] == 0
    assert registry["summary"]["postgresql_writes"] == 0
    assert registry["summary"]["runtime_indexed_relationships"] == 0


def test_relationship_ids_and_registry_are_deterministic() -> None:
    current_packet = packet()
    ledger = ledger_for(current_packet)
    first = build_registry(current_packet, ledger)
    second = build_registry(copy.deepcopy(current_packet), copy.deepcopy(ledger))
    assert first == second
    ids = [item["relationship_id"] for item in first["relationships"]]
    assert len(ids) == len(set(ids)) == 5
    assert all(item.startswith("local-review-family-") for item in ids)


def test_release_references_remain_distinct_held_and_unenriched() -> None:
    current_packet = packet()
    registry = build_registry(current_packet, ledger_for(current_packet))
    references = [
        reference
        for relationship in registry["relationships"]
        for reference in relationship["source_references"]
    ]
    assert len({item["source_record_id"] for item in references}) == 5
    assert all(item["release_variant_status"] == "held_for_variant_review" for item in references)
    assert all(item["canonical_uuid"] is None and item["color"] is None for item in references)
    for relationship in registry["relationships"]:
        assert relationship["candidate_evidence_status"] == "context_only_not_selected"
        assert relationship["canonical_uuid"] is None
        assert relationship["color_decision"] is None


def test_nonaffirmative_decisions_become_exclusions_not_relationships() -> None:
    current_packet = packet()
    decisions = (
        "same_review_family",
        "keep_separate",
        "unknown",
        "same_review_family",
        "keep_separate",
    )
    registry = build_registry(current_packet, ledger_for(current_packet, decisions))
    assert len(registry["relationships"]) == 2
    assert len(registry["decision_exclusions"]) == 3
    assert {item["exclusion_status"] for item in registry["decision_exclusions"]} == {
        "owner_rejected_relationship",
        "owner_relationship_unresolved",
    }
    assert all(item["materialized"] is False for item in registry["decision_exclusions"])


def test_incomplete_ledger_is_rejected() -> None:
    current_packet = packet()
    first = append_event(
        current_packet,
        None,
        question_ordinal=1,
        decision="same_review_family",
        owner_response_verbatim="same_review_family",
        decided_at="2026-09-18T00:01:00Z",
    )
    with pytest.raises(ValueError, match="must be complete"):
        build_registry(current_packet, first)


def test_duplicate_source_assignment_is_rejected() -> None:
    current_packet = packet()
    current_packet["questions"][1]["source_observations"][0]["source_record_id"] = "source-1"
    with pytest.raises(ValueError, match="more than one review relationship"):
        build_registry(current_packet, ledger_for(current_packet))


def test_duplicate_review_cluster_is_rejected() -> None:
    current_packet = packet()
    current_packet["questions"][1]["review_cluster_id"] = "cluster-1"
    with pytest.raises(ValueError, match="review cluster is assigned more than once"):
        build_registry(current_packet, ledger_for(current_packet))


def test_tampered_ledger_and_registry_are_rejected() -> None:
    current_packet = packet()
    ledger = ledger_for(current_packet)
    tampered_ledger = copy.deepcopy(ledger)
    tampered_ledger["summary"]["canonical_promotions"] = 1
    with pytest.raises(ValueError, match="summary, status, or checksum"):
        build_registry(current_packet, tampered_ledger)

    registry = build_registry(current_packet, ledger)
    registry["summary"]["canonical_promotions"] = 1
    with pytest.raises(ValueError, match="differs from deterministic"):
        validate_registry(current_packet, ledger, registry)


def test_public_manifest_contains_aggregates_but_no_private_identity() -> None:
    current_packet = packet()
    registry = build_registry(current_packet, ledger_for(current_packet))
    manifest = build_public_manifest(registry)
    text = json.dumps(manifest, sort_keys=True)
    assert manifest["summary"]["materialized_review_relationships"] == 5
    assert "relationships" not in manifest
    assert "Casting 1" not in text
    assert "cluster-1" not in text
    assert "source-1" not in text
    assert "TEST-1" not in text
    assert "owner_response_verbatim" not in text


def test_publication_is_idempotent_and_conflicts_fail_without_overwrite(tmp_path: Path) -> None:
    (tmp_path / "data/external/hot-wheels-wiki").mkdir(parents=True)
    (tmp_path / "reports").mkdir()
    current_packet = packet()
    registry = build_registry(current_packet, ledger_for(current_packet))
    manifest = build_public_manifest(registry)
    assert publish_outputs(tmp_path, registry, manifest) == "created"
    private_path = (
        tmp_path
        / "data/external/hot-wheels-wiki/local-release-casting-review-family-materialization-v1/registry.json"
    )
    before = private_path.read_bytes()
    assert publish_outputs(tmp_path, registry, manifest) == "unchanged"
    report = tmp_path / "reports/local-release-casting-review-family-materialization-v1/report.md"
    report.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="differs from deterministic"):
        publish_outputs(tmp_path, registry, manifest)
    assert private_path.read_bytes() == before


def test_partial_publication_pair_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "data/external/hot-wheels-wiki").mkdir(parents=True)
    (tmp_path / "reports").mkdir()
    current_packet = packet()
    registry = build_registry(current_packet, ledger_for(current_packet))
    manifest = build_public_manifest(registry)
    private_directory, _ = materialization._paths(tmp_path)
    private_directory.mkdir()
    (private_directory / "registry.json").write_text("partial\n", encoding="utf-8")
    with pytest.raises(ValueError, match="partial materialization exists"):
        publish_outputs(tmp_path, registry, manifest)
    assert (private_directory / "registry.json").read_text(encoding="utf-8") == "partial\n"


def test_first_publication_failure_rolls_back_created_private_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "data/external/hot-wheels-wiki").mkdir(parents=True)
    (tmp_path / "reports").mkdir()
    current_packet = packet()
    registry = build_registry(current_packet, ledger_for(current_packet))
    manifest = build_public_manifest(registry)
    original = materialization._write_directory
    calls = 0

    def fail_second_write(directory: Path, outputs: dict[str, str]) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated public write failure")
        original(directory, outputs)

    monkeypatch.setattr(materialization, "_write_directory", fail_second_write)
    with pytest.raises(RuntimeError, match="simulated"):
        publish_outputs(tmp_path, registry, manifest)
    private_directory, public_directory = materialization._paths(tmp_path)
    assert not private_directory.exists()
    assert not public_directory.exists()


def test_current_private_and_public_materialization_when_present() -> None:
    private_path = (
        ROOT
        / "data/external/hot-wheels-wiki/local-release-casting-review-family-materialization-v1/registry.json"
    )
    public_path = (
        ROOT / "reports/local-release-casting-review-family-materialization-v1/manifest.json"
    )
    if not private_path.is_file() or not public_path.is_file():
        pytest.skip("local materialization is created after the complete decision ledger")
    registry = json.loads(private_path.read_text(encoding="utf-8"))
    manifest = json.loads(public_path.read_text(encoding="utf-8"))
    assert registry["status"] == "complete_review_layer_only"
    assert len(registry["relationships"]) == 5
    assert registry["summary"]["held_source_references"] == 18
    assert manifest["private_registry_sha256"] == registry["registry_sha256"]
    assert manifest["summary"]["materialized_review_relationships"] == 5
    assert manifest["summary"]["canonical_promotions"] == 0
