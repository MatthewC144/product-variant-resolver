"""T3 orchestration/contract fixtures use EMPTY FAKE retrieval, never a quality winner."""
from copy import deepcopy
from pathlib import Path

import pytest

from product_variant_resolver import human_knowledge_identity_selection as module
from product_variant_resolver.human_knowledge_identity import IdentityRetrievalWork
from product_variant_resolver.human_knowledge_identity_artifact import (
    validate_identity_selection_report,
)
from product_variant_resolver.human_knowledge_selection import choose, grid, load_object


@pytest.fixture(scope="module")
def empty_fake_report():
    protocol = module.load_identity_protocol()
    calls, parameters = [], []
    class FakeRetriever:
        def __init__(self, catalog, embedding, config):
            audit = protocol["audit_summary"]["real" if len(catalog.documents) == 142 else "synthetic"]
            self.character_index_metadata = {"document_count": audit["document_count"],
                "form_count": audit["form_count"], "posting_entry_count": audit["form_posting_entry_count"],
                "posting_count": audit["gram_posting_key_count"]}
            parameters.append({"character_score_floor": config.character_score_floor,
                "character_rrf_weight": config.character_rrf_weight})
        def retrieve_with_work(self, signal, limit):
            calls.append((signal.normalized_title, limit))
            return [], IdentityRetrievalWork()
    original_read_bytes = Path.read_bytes
    original_read_text = Path.read_text
    def reject_final(path):
        if "family-retrieval-v1" in str(path):
            raise AssertionError("final v1 must not be read during selection")
    def read_bytes(path):
        reject_final(path)
        return original_read_bytes(path)
    def read_text(path, *args, **kwargs):
        reject_final(path)
        return original_read_text(path, *args, **kwargs)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module, "HumanKnowledgeIdentityRetriever", FakeRetriever)
        patch.setattr(Path, "read_bytes", read_bytes)
        patch.setattr(Path, "read_text", read_text)
        payload = module.evaluate()
        assert validate_identity_selection_report(payload) is None
    return payload, calls, parameters


def test_exact_grid_raw_counts_warmups_and_no_final_reads(empty_fake_report):
    report, calls, parameters = empty_fake_report
    assert parameters == [parameter for parameter in grid() for _ in range(2)]
    assert len(calls) == 21 * (199 + 120 + 6)
    assert all(limit == 5 for _, limit in calls)
    assert sum(len(entry["cases"]) for entry in report["configurations"]) == 4179
    assert sum(len(entry["scale_cases"]) for entry in report["configurations"]) == 2520
    assert report["verdict"] == "FAIL" and report["winner"] is None
    for entry in report["configurations"]:
        assert entry["metrics"]["raw_counts"]["positive"]["total"] == 168
        assert all(style["total"] == 42 for style in entry["metrics"]["raw_counts"]["positive_styles"].values())
        assert entry["scale_hits"] == {"exact_identity": 0, "single_edit": 0, "contextual_identity": 0}
        assert all(f"synthetic_correctness_failed:{key}" in entry["rejection_reasons"] for key in entry["scale_hits"])
        assert entry["scale_subgroups"]["original_dev_20"]["latency"]["sample_count"] == 20


@pytest.mark.parametrize("mutation", ["grid", "case", "sample", "subgroup", "work", "target", "metric", "winner", "runtime", "source"])
def test_raw_report_tampering_rejects_without_retrieval(empty_fake_report, mutation):
    report = deepcopy(empty_fake_report[0])
    entry = report["configurations"][0]
    if mutation == "grid":
        report["configurations"].pop()
    elif mutation == "case":
        entry["cases"].pop()
    elif mutation == "sample":
        entry["cost"]["real_142"]["samples_ms"].pop()
    elif mutation == "subgroup":
        entry["scale_subgroups"]["original_dev_20"]["latency"]["p95_ms"] += 1
    elif mutation == "work":
        entry["work_summary"]["real_142"]["sample_count"] -= 1
    elif mutation == "target":
        entry["scale_cases"][20]["target_knowledge_uuid"] = "changed"
    elif mutation == "metric":
        entry["metrics"]["recall_at_5"] = 1
    elif mutation == "winner":
        report["winner"] = entry["configuration"]
    elif mutation == "runtime":
        report["runtime"]["candidate_k"] = 25
    else:
        report["sources"][next(iter(report["sources"]))] = "0" * 64
    with pytest.raises(ValueError):
        validate_identity_selection_report(report)


def test_no_winner_preserves_existing_and_missing_artifacts(empty_fake_report, tmp_path, monkeypatch):
    report = empty_fake_report[0]
    monkeypatch.setattr(module, "load_object", lambda _: report)
    existing = tmp_path / "existing.json"
    existing.write_text("original")
    before = existing.stat().st_mtime_ns
    assert module.freeze(tmp_path / "selection.json", existing) is False
    assert existing.read_text() == "original" and existing.stat().st_mtime_ns == before
    missing = tmp_path / "missing-directory" / "artifact.json"
    assert module.freeze(tmp_path / "selection.json", missing) is False
    assert not missing.parent.exists()


def test_exclusive_atomic_publication_preserves_files_and_rejects_bad_bytes(tmp_path):
    output = tmp_path / "output.json"
    module.publish_new(output, {"ok": True})
    with pytest.raises(FileExistsError):
        module.publish_new(output, {"ok": False})
    assert load_object(output) == {"ok": True}
    invalid = tmp_path / "invalid.json"
    def reject(path):
        raise ValueError("invalid artifact")
    with pytest.raises(ValueError):
        module.publish_new(invalid, {}, reject)
    assert not invalid.exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == ["output.json"]


def test_survivor_tie_break_and_safety_not_nearest_winner():
    entries = [{"configuration": parameter, "metrics": {"mrr_at_5": .9, "recall_at_1": .8},
        "rejection_reasons": []} for parameter in grid()]
    assert choose(entries) == {"character_score_floor": .55, "character_rrf_weight": .5}
    for entry in entries:
        entry["rejection_reasons"] = ["unrelated_nonempty"]
    assert choose(entries) is None


def test_frozen_genuine_report_replays_without_retrieval(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("checking frozen evidence must not run retrieval")
    monkeypatch.setattr(module.HumanKnowledgeIdentityRetriever, "retrieve_with_work", forbidden)
    payload = load_object(module.REPORT)
    assert validate_identity_selection_report(payload) == payload["winner"]
    assert len(payload["configurations"]) == 21
    assert payload["verdict"] == "PASS"


def test_genuine_runtime_opt_in_and_canonical_equality():
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from product_variant_resolver.api import create_app
    from product_variant_resolver.config import Settings
    from product_variant_resolver.schemas import ResolveRequest
    from product_variant_resolver.service import ResolverService
    settings = Settings()
    base = ResolverService.from_settings(settings)
    selected = ResolverService.from_settings(replace(settings,
        human_knowledge_identity_artifact_path=module.ROOT / "config/human-knowledge-retrieval-v4.json"))
    assert selected.human_knowledge.version == "human-knowledge-hybrid-v4"
    assert selected.human_knowledge.config.character_score_floor == .5
    assert selected.human_knowledge.artifact_sha256 == module.sha(module.ROOT / "config/human-knowledge-retrieval-v4.json")
    request = ResolveRequest(title="2022 Chevy Nomad Red #101")
    assert selected.resolve(request) == base.resolve(request)
    assert base.human_knowledge.version == "human-knowledge-hybrid-v2"
    client = TestClient(create_app(selected.settings))
    health = client.get("/health")
    assert health.status_code == 200
    assert selected.human_knowledge.artifact_sha256 in health.json()["dependencies"]["human_knowledge_index"]["detail"]
    response = client.post("/resolve", json={"title": request.title, "debug": True})
    assert response.status_code == 200
    debug = response.json()["debug"]
    assert debug["human_knowledge_retrieval_artifact_sha256"] == selected.human_knowledge.artifact_sha256
    assert debug["human_knowledge_identity_work"]["posting_entries_visited"] > 0


def test_genuine_winner_does_not_overwrite_existing_artifact(tmp_path):
    output = tmp_path / "existing.json"
    output.write_text("original")
    before = output.stat().st_mtime_ns
    with pytest.raises(ValueError, match="exists"):
        module.freeze(module.REPORT, output)
    assert output.read_text() == "original" and output.stat().st_mtime_ns == before


def test_container_public_evidence_is_readable_for_non_root():
    assert "RUN chmod -R a+rX /app/data /app/config /app/reports /app/scripts" in (module.ROOT / "Dockerfile").read_text()
