from __future__ import annotations

import copy
import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

import pytest

import product_variant_resolver.release_casting_review_knowledge as knowledge
from product_variant_resolver.release_casting_review_decisions import append_event
from product_variant_resolver.release_casting_review_knowledge import (
    DOCUMENT_FIELDS,
    SEARCHABLE_FIELDS,
    build_projection,
    build_public_manifest,
    publish_outputs,
    validate_projection,
)
from product_variant_resolver.release_casting_review_materialization import build_registry
from product_variant_resolver.release_staging import digest

ROOT = Path(__file__).resolve().parents[2]


def packet() -> dict[str, Any]:
    questions = []
    for ordinal in range(1, 6):
        questions.append(
            {
                "ordinal": ordinal,
                "review_cluster_id": f"local-cluster-{ordinal}",
                "observed_casting_labels": [f"Local Casting {ordinal}"],
                "normalized_key": {
                    "brand": "hot wheels",
                    "casting": f"local casting {ordinal}",
                },
                "source_observations": [
                    {
                        "source_record_id": f"local-source-{ordinal}",
                        "release_year": 2020 + ordinal,
                        "toy_number": f"LOCAL-{ordinal}",
                        "collector_number": str(ordinal),
                        "source_model_label": f"Local Casting {ordinal}",
                        "casting_name": f"Local Casting {ordinal}",
                        "variant_note": None,
                        "series": "Local Series",
                        "series_position": f"{ordinal}/5",
                    }
                ],
                "candidate_evidence": {"canonical_fixture": None, "human_draft": []},
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
        "packet_sha256": "b" * 64,
        "batch_id": "local-batch-" + "b" * 64,
        "questions": questions,
    }


def local_registry() -> dict[str, Any]:
    current_packet = packet()
    ledger = None
    for ordinal in range(1, 6):
        ledger = append_event(
            current_packet,
            ledger,
            question_ordinal=ordinal,
            decision="same_review_family",
            owner_response_verbatim="same_review_family",
            decided_at=f"2026-09-19T00:0{ordinal}:00Z",
        )
    assert ledger is not None
    return build_registry(current_packet, ledger)


def existing_inputs() -> tuple[dict[str, Any], dict[str, Any], str, str]:
    documents = []
    for ordinal in range(42):
        documents.append(
            {
                "knowledge_type": "review_family",
                "review_family_id": f"existing-family-{ordinal}",
                "review_family_uuid": str(
                    uuid.uuid5(uuid.NAMESPACE_URL, f"existing-family:{ordinal}")
                ),
                "identity_level": "casting_family_only",
                "identity_status": "family_accepted_variants_unreviewed",
                "brand": "Hot Wheels",
                "casting": f"Existing Casting {ordinal}",
                "aliases": [f"Existing Casting {ordinal}"],
                "source_record_ids": [f"existing-source-{ordinal}"],
            }
        )
    projection = {
        "schema_version": "pvr-review-family-knowledge-v1",
        "knowledge_version": "review-family-knowledge-fandom-2025-r790665-v1",
        "status": "debug_retrieval_only",
        "documents": documents,
    }
    projection_sha = hashlib.sha256(stable_json(projection).encode()).hexdigest()
    manifest = {
        "knowledge_version": "review-family-knowledge-fandom-2025-r790665-v1",
        "document_count": 42,
        "projection_sha256": projection_sha,
    }
    manifest_sha = hashlib.sha256(stable_json(manifest).encode()).hexdigest()
    return projection, manifest, projection_sha, manifest_sha


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def build_current(
    registry: dict[str, Any] | None = None,
    existing: dict[str, Any] | None = None,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    default_existing, default_manifest, projection_sha, manifest_sha = existing_inputs()
    selected_existing = existing if existing is not None else default_existing
    selected_manifest = manifest if manifest is not None else default_manifest
    if existing is not None:
        projection_sha = hashlib.sha256(stable_json(existing).encode()).hexdigest()
        selected_manifest = copy.deepcopy(selected_manifest)
        selected_manifest["projection_sha256"] = projection_sha
    if manifest is not None:
        manifest_sha = hashlib.sha256(stable_json(selected_manifest).encode()).hexdigest()
    return build_projection(
        registry if registry is not None else local_registry(),
        selected_existing,
        selected_manifest,
        existing_projection_sha256=projection_sha,
        existing_manifest_sha256=manifest_sha,
    )


def rehash_registry(registry: dict[str, Any]) -> None:
    for relationship in registry["relationships"]:
        body = {key: value for key, value in relationship.items() if key != "relationship_sha256"}
        relationship["relationship_sha256"] = digest(body)
    body = {key: value for key, value in registry.items() if key != "registry_sha256"}
    registry["registry_sha256"] = digest(body)


def test_projection_has_five_typed_offline_documents() -> None:
    projection = build_current()
    assert projection["status"] == "offline_evaluation_candidate_not_runtime"
    assert projection["eligible_for"] == ["offline_retrieval_evaluation"]
    assert len(projection["documents"]) == 5
    assert projection["summary"]["source_record_reference_count"] == 5
    assert projection["summary"]["existing_corpus_document_count"] == 42
    assert projection["summary"]["runtime_indexed_documents"] == 0
    assert all(item["knowledge_type"] == "review_family" for item in projection["documents"])


def test_document_fields_and_search_allowlist_are_narrow() -> None:
    projection = build_current()
    assert projection["searchable_fields"] == list(SEARCHABLE_FIELDS)
    assert projection["document_fields"] == list(DOCUMENT_FIELDS)
    for document in projection["documents"]:
        assert set(document) == set(DOCUMENT_FIELDS)
        assert document["identity_level"] == "casting_family_only"
        assert document["identity_status"] == "owner_confirmed_variants_unreviewed"
        assert "toy_number" not in document
        assert "variant_note" not in document
        assert "candidate_evidence" not in document


def test_ids_uuids_order_and_projection_are_deterministic() -> None:
    first = build_current()
    second = build_current(copy.deepcopy(local_registry()))
    assert first == second
    ids = [item["review_family_id"] for item in first["documents"]]
    uuids = [item["review_family_uuid"] for item in first["documents"]]
    assert ids == sorted(ids)
    assert len(ids) == len(set(ids)) == 5
    assert len(uuids) == len(set(uuids)) == 5
    for document in first["documents"]:
        expected = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"{knowledge.IDENTITY_NAMESPACE}:{document['review_family_id']}",
            )
        )
        assert document["review_family_uuid"] == expected


def test_normalized_identity_collision_with_existing_corpus_is_rejected() -> None:
    existing, manifest, _, _ = existing_inputs()
    existing["documents"][0]["casting"] = "Local Casting 1"
    existing["documents"][0]["aliases"] = ["Local Casting 1"]
    with pytest.raises(ValueError, match="normalized review-family identity collides"):
        build_current(existing=existing, manifest=manifest)


def test_id_and_uuid_collisions_with_existing_corpus_are_rejected() -> None:
    registry = local_registry()
    projection = build_current(registry)
    existing, manifest, _, _ = existing_inputs()
    existing["documents"][0]["review_family_id"] = projection["documents"][0]["review_family_id"]
    with pytest.raises(ValueError, match="knowledge ID collides"):
        build_current(registry, existing, manifest)

    existing, manifest, _, _ = existing_inputs()
    existing["documents"][0]["review_family_uuid"] = projection["documents"][0][
        "review_family_uuid"
    ]
    with pytest.raises(ValueError, match="knowledge UUID collides"):
        build_current(registry, existing, manifest)


def test_duplicate_source_assignment_is_rejected() -> None:
    registry = local_registry()
    registry["relationships"][1]["source_references"][0]["source_record_id"] = registry[
        "relationships"
    ][0]["source_references"][0]["source_record_id"]
    rehash_registry(registry)
    with pytest.raises(ValueError, match="assigned to more than one knowledge document"):
        build_current(registry)


def test_registry_tamper_and_projection_tamper_are_rejected() -> None:
    registry = local_registry()
    registry["summary"]["canonical_promotions"] = 1
    with pytest.raises(ValueError, match="checksum differs"):
        build_current(registry)

    registry = local_registry()
    projection = build_current(registry)
    projection["summary"]["runtime_indexed_documents"] = 1
    existing, manifest, projection_sha, manifest_sha = existing_inputs()
    with pytest.raises(ValueError, match="differs from deterministic"):
        validate_projection(
            registry,
            existing,
            manifest,
            projection,
            existing_projection_sha256=projection_sha,
            existing_manifest_sha256=manifest_sha,
        )


def test_existing_projection_checksum_mismatch_is_rejected() -> None:
    existing, manifest, projection_sha, manifest_sha = existing_inputs()
    manifest["projection_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="checksum differs from manifest"):
        build_projection(
            local_registry(),
            existing,
            manifest,
            existing_projection_sha256=projection_sha,
            existing_manifest_sha256=manifest_sha,
        )


def test_public_manifest_contains_no_private_document_identity() -> None:
    projection = build_current()
    manifest = build_public_manifest(projection)
    text = json.dumps(manifest, sort_keys=True)
    assert manifest["summary"]["document_count"] == 5
    assert "documents" not in manifest
    assert "Local Casting" not in text
    assert "local-review-family" not in text
    assert "local-source" not in text


def test_publication_is_idempotent_and_conflicts_fail_without_overwrite(tmp_path: Path) -> None:
    (tmp_path / "data/external/hot-wheels-wiki").mkdir(parents=True)
    (tmp_path / "reports").mkdir()
    projection = build_current()
    manifest = build_public_manifest(projection)
    assert publish_outputs(tmp_path, projection, manifest) == "created"
    private_path = (
        tmp_path
        / "data/external/hot-wheels-wiki/local-release-casting-review-family-knowledge-v1/projection.json"
    )
    before = private_path.read_bytes()
    assert publish_outputs(tmp_path, projection, manifest) == "unchanged"
    report = tmp_path / "reports/local-release-casting-review-family-knowledge-v1/report.md"
    report.write_text("tampered\n", encoding="utf-8")
    with pytest.raises(ValueError, match="differs from deterministic"):
        publish_outputs(tmp_path, projection, manifest)
    assert private_path.read_bytes() == before


def test_partial_projection_pair_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "data/external/hot-wheels-wiki").mkdir(parents=True)
    (tmp_path / "reports").mkdir()
    projection = build_current()
    manifest = build_public_manifest(projection)
    private_directory, _ = knowledge._paths(tmp_path)
    private_directory.mkdir()
    (private_directory / "projection.json").write_text("partial\n", encoding="utf-8")
    with pytest.raises(ValueError, match="partial knowledge projection exists"):
        publish_outputs(tmp_path, projection, manifest)


def test_failed_second_write_rolls_back_new_private_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "data/external/hot-wheels-wiki").mkdir(parents=True)
    (tmp_path / "reports").mkdir()
    projection = build_current()
    manifest = build_public_manifest(projection)
    original = knowledge._write_directory
    calls = 0

    def fail_second_write(directory: Path, outputs: dict[str, str]) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated public projection write failure")
        original(directory, outputs)

    monkeypatch.setattr(knowledge, "_write_directory", fail_second_write)
    with pytest.raises(RuntimeError, match="simulated"):
        publish_outputs(tmp_path, projection, manifest)
    private_directory, public_directory = knowledge._paths(tmp_path)
    assert not private_directory.exists()
    assert not public_directory.exists()


def test_current_private_and_public_projection_when_present() -> None:
    private_path = (
        ROOT
        / "data/external/hot-wheels-wiki/local-release-casting-review-family-knowledge-v1/projection.json"
    )
    public_path = ROOT / "reports/local-release-casting-review-family-knowledge-v1/manifest.json"
    if not private_path.is_file() or not public_path.is_file():
        pytest.skip("local knowledge projection is created after implementation")
    projection = json.loads(private_path.read_text(encoding="utf-8"))
    manifest = json.loads(public_path.read_text(encoding="utf-8"))
    assert len(projection["documents"]) == 5
    assert projection["summary"]["source_record_reference_count"] == 18
    assert projection["summary"]["normalized_identity_collisions"] == 0
    assert manifest["private_projection_sha256"] == projection["projection_sha256"]
    assert manifest["summary"]["runtime_indexed_documents"] == 0
