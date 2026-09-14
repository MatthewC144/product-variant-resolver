"""Fail-closed artifact tests; mock winner is never a selected development result."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from uuid import UUID

import pytest

from product_variant_resolver import human_knowledge_identity_artifact as module
from product_variant_resolver.human_knowledge import (
    HumanKnowledgeCatalog,
    ReviewFamilyKnowledgeDocument,
)
from product_variant_resolver.human_knowledge_identity import (
    HumanKnowledgeIdentityRetriever,
    HumanKnowledgeV4Config,
    IdentityRetrievalWork,
)
from product_variant_resolver.retrieval import HashingEmbedding
from product_variant_resolver.signals import extract_signals


def test_real_frozen_protocol_loads_with_all_historical_bindings():
    protocol = module.load_identity_protocol()
    assert protocol["audit_summary"]["real"]["form_count"] == 284


def test_modified_protocol_and_missing_sources_reject(tmp_path):
    with pytest.raises(FileNotFoundError):
        module.load_identity_protocol(tmp_path)


@pytest.mark.parametrize("name", ["../outside.json", "/tmp/outside.json"])
def test_evidence_path_escape_rejected(tmp_path, name):
    with pytest.raises(ValueError):
        module.safe_path(tmp_path, name)


@pytest.fixture
def mock_artifact_contract(monkeypatch, tmp_path):
    """Isolate parsing from expensive report recomputation; not performance/quality proof."""
    protocol = module.load_identity_protocol()
    floor_weight = {"character_score_floor": .35, "character_rrf_weight": 1.0}
    sources = {name: "a"*64 for name in module.RUNTIME_SOURCES}
    entry = {"configuration": floor_weight, "metrics": {}, "scale_hits": {}, "rejection_reasons": []}
    artifact = {
        "schema_version": module.ARTIFACT_SCHEMA,
        "artifact_version": "human-knowledge-retrieval-v4-unit-fixture",
        "retriever_version": module.VERSION, "status": "selected_development_configuration",
        "configuration": {**floor_weight, "dense_dimensions": 192, "dense_rrf_weight": 1.0,
            "sparse_rrf_weight": 1.0, "rrf_k": 60, "selection_candidate_limit": 5, "source_candidate_limit": 25},
        "identity_policy": protocol["identity_policy"], "limits": protocol["limits"],
        "protocol_sha256": module.PROTOCOL_SHA256, "protocol_manifest_sha256": module.MANIFEST_SHA256,
        "sources": sources, "selection_evidence": {"file": str(module.REPORT_DIRECTORY / "selection.json"),
            "sha256": "a"*64, "configuration_summaries": [entry]},
        "eligible_for": ["human_knowledge_debug_retrieval"], "excluded_from": protocol["excluded_from"],
    }
    report = {"configurations": [entry], "sources": sources}
    inputs = {name: "a"*64 for name in (
        "data/human_backed_catalog.json", "data/review_family_knowledge.json",
        "data/evaluation/family-retrieval-development-v1/development-pack.json",
        "data/evaluation/family-retrieval-development-v1/development-pack-manifest.json")}
    monkeypatch.setattr(module, "load_identity_protocol", lambda _: protocol)
    monkeypatch.setattr(module, "sha", lambda _: "a"*64)
    def load(path):
        if path.name == "artifact.json":
            return artifact
        if path.name == "selection.json":
            return report
        return {"input_sha256": inputs}
    monkeypatch.setattr(module, "load_object", load)
    monkeypatch.setattr(module, "validate_identity_selection_report", lambda *args: floor_weight)
    def call():
        return module.load_human_knowledge_v4_config(tmp_path / "artifact.json", root=tmp_path,
            human_catalog_path=Path("human"), review_family_path=Path("family"),
            development_pack_path=Path("pack"), development_manifest_path=Path("manifest"), dense_dimensions=192)
    return artifact, report, call


def test_mock_qualified_contract_can_construct_config(mock_artifact_contract):
    _, _, call = mock_artifact_contract
    assert call().character_score_floor == .35


@pytest.mark.parametrize("field,value", [("limits", {}), ("identity_policy", {}),
    ("protocol_sha256", "stale"), ("eligible_for", ["canonical"]), ("selection_evidence", None),
    ("status", "failed"), ("sources", {})])
def test_strict_artifact_rejects_mutations(mock_artifact_contract, field, value):
    artifact, _, call = mock_artifact_contract
    artifact[field] = value
    with pytest.raises(ValueError):
        call()


@pytest.mark.parametrize("field,value", [("character_score_floor", .36), ("character_rrf_weight", True),
    ("dense_dimensions", 64), ("source_candidate_limit", 26), ("rrf_k", 61)])
def test_fixed_grid_and_budget_parameters_not_runtime_tunable(mock_artifact_contract, field, value):
    artifact, _, call = mock_artifact_contract
    artifact["configuration"][field] = value
    with pytest.raises(ValueError):
        call()


def test_no_winner_cannot_enable_v4(mock_artifact_contract, monkeypatch):
    _, _, call = mock_artifact_contract
    monkeypatch.setattr(module, "validate_identity_selection_report", lambda *args: None)
    with pytest.raises(ValueError, match="no qualified"):
        call()


def test_missing_or_stale_raw_report_cannot_enable(mock_artifact_contract, monkeypatch):
    artifact, _, call = mock_artifact_contract
    artifact["selection_evidence"]["sha256"] = "b"*64
    with pytest.raises(ValueError, match="checksum"):
        call()
    artifact["selection_evidence"]["sha256"] = "a"*64
    def reject(*args):
        raise ValueError("raw report invalid")
    monkeypatch.setattr(module, "validate_identity_selection_report", reject)
    with pytest.raises(ValueError, match="raw report"):
        call()


@pytest.mark.parametrize("mutation", ["negative", "over_cap", "partial", "uncovered"])
def test_raw_work_contract_rejects_invalid_counters(mutation):
    row = {"work": asdict(IdentityRetrievalWork()), "candidates": []}
    if mutation == "negative":
        row["work"]["scored_forms"] = -1
    elif mutation == "over_cap":
        row["work"]["posting_entries_visited"] = 1_000_001
    elif mutation == "partial":
        row["work"].update(abstention_reason="posting_limit", dense_union=1)
    else:
        row["candidates"] = [{}]
    with pytest.raises(ValueError):
        module._check_work(deepcopy(row))


def test_raw_selection_requires_exact_grid_before_any_evaluation():
    payload = {"schema_version": "pvr-human-knowledge-identity-selection-v1",
        "protocol_sha256": module.PROTOCOL_SHA256, "protocol_manifest_sha256": module.MANIFEST_SHA256,
        "configurations": [], "sources": {}}
    with pytest.raises(ValueError, match="grid"):
        module.validate_identity_selection_report(payload)


@pytest.mark.parametrize("mutation", [None, "fusion", "admission", "rank", "identity"])
def test_actual_candidate_evidence_recomputes_and_tampering_rejects(mutation):
    document = ReviewFamilyKnowledgeDocument(UUID(int=1), "family-1", "Test", "Alpha Coupe", (), (),
        "family_accepted_variants_unreviewed")
    service = HumanKnowledgeIdentityRetriever(HumanKnowledgeCatalog("test", "test", [document]),
        HashingEmbedding(), HumanKnowledgeV4Config(.35, 1))
    candidates, work = service.retrieve_with_work(extract_signals("Alpha Coupe"), 5)
    candidate = candidates[0]
    serialized = asdict(candidate)
    serialized.pop("document")
    serialized.update(knowledge_uuid=str(document.knowledge_uuid), knowledge_id=document.knowledge_id,
        knowledge_type=document.knowledge_type, casting_id=None)
    row = {"candidates": [serialized], "work": work.as_dict()}
    if mutation == "fusion":
        serialized["rrf_score"] += .1
    elif mutation == "admission":
        serialized["character_score"] = .1
    elif mutation == "rank":
        serialized["dense_rank"] = 51
    elif mutation == "identity":
        serialized["knowledge_id"] = "wrong"
    if mutation:
        with pytest.raises(ValueError):
            module._check_candidates(row, {str(document.knowledge_uuid): document},
                {"character_score_floor": .35, "character_rrf_weight": 1})
    else:
        module._check_candidates(row, {str(document.knowledge_uuid): document},
            {"character_score_floor": .35, "character_rrf_weight": 1})


def test_runtime_evidence_dependencies_are_in_container_context():
    root = module.ROOT
    dockerfile = (root / "Dockerfile").read_text()
    ignore = (root / ".dockerignore").read_text()
    assert "COPY reports/ ./reports/" in dockerfile
    assert "COPY scripts/build_human_knowledge_identity_protocol.py" in dockerfile
    assert "!scripts/build_human_knowledge_identity_protocol.py" in ignore
