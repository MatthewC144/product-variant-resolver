"""Ephemeral v4 wiring checks. No selected artifact or development report is created."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from product_variant_resolver.api import create_app
from product_variant_resolver.config import Settings
from product_variant_resolver.human_knowledge_identity import HumanKnowledgeV4Config, IdentityLimits
from product_variant_resolver.schemas import ResolveRequest
from product_variant_resolver.service import ResolverService

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def services():
    settings = Settings(catalog_path=ROOT / "data/catalog.json", ui_path=ROOT / "ui")
    base = ResolverService.from_settings(settings)
    v4 = ResolverService(settings, base.catalog, base.human_catalog,
        human_knowledge_v4_config=HumanKnowledgeV4Config(.35, 1))
    return base, v4


@pytest.mark.parametrize("query", ["2022 Chevy Nomad Red #101", "red toy boxed", "unrelated qzxv", "Chevy Nomad"])
def test_debug_off_canonical_response_unchanged(services, query):
    base, v4 = services
    request = ResolveRequest(title=query)
    assert base.resolve(request).model_dump(mode="json") == v4.resolve(request).model_dump(mode="json")


def test_api_local_work_metadata_and_health(services):
    base, v4 = services
    client = TestClient(create_app(base.settings, service_factory=lambda _: v4))
    health = client.get("/health")
    assert health.status_code == 200
    detail = health.json()["dependencies"]["human_knowledge_index"]
    assert detail["version"] == "human-knowledge-hybrid-v4"
    assert "identity-core-policy-v1" in detail["detail"] and "dense_union=50" in detail["detail"]
    populated = client.post("/resolve", json={"title": "Chevy Nomad", "debug": True}).json()["debug"]
    assert populated["human_knowledge_character_index"]["form_count"] == 284
    assert populated["human_knowledge_character_index"]["posting_entry_count"] == 8051
    assert populated["human_knowledge_identity_work"]["posting_entries_visited"] > 0
    empty = client.post("/resolve", json={"title": "red toy boxed", "debug": True}).json()["debug"]
    assert empty["human_knowledge_candidates"] == []
    assert empty["human_knowledge_identity_work"]["abstention_reason"] == "noise_only"
    assert empty["human_knowledge_identity_work"]["posting_entries_visited"] == 0
    assert "human_knowledge_identity_work" not in base.resolve(ResolveRequest(title="Chevy Nomad", debug=True)).model_dump(mode="json")["debug"]


def test_parallel_requests_do_not_overwrite_query_work(services):
    _, service = services
    queries = ["Chevy Nomad", "red toy boxed", "Toyota Supra", "red toy boxed"] * 3
    def resolve(query):
        return service.resolve(ResolveRequest(title=query, debug=True)).debug.human_knowledge_identity_work.model_dump()
    expected = [resolve(query) for query in queries]
    with ThreadPoolExecutor(max_workers=4) as pool:
        actual = list(pool.map(resolve, queries))
    assert actual == expected


def test_posting_abort_preserves_canonical_and_dependency_error_is_503(services, monkeypatch):
    base, _ = services
    service = ResolverService(base.settings, base.catalog, base.human_catalog,
        human_knowledge_v4_config=HumanKnowledgeV4Config(.35, 1,
            limits=replace(IdentityLimits(), posting_entries_per_query=1)))
    request = ResolveRequest(title="Chevy Nomad")
    assert service.resolve(request) == base.resolve(request)
    client = TestClient(create_app(base.settings, service_factory=lambda _: service))
    def fail(*args, **kwargs):
        raise RuntimeError("index unavailable")
    monkeypatch.setattr(service.human_knowledge, "retrieve_with_work", fail)
    assert client.post("/resolve", json={"title": "Chevy Nomad"}).status_code == 503


@pytest.mark.parametrize("kind", ["missing", "invalid", "conflicting"])
def test_bad_opt_in_not_ready_without_v2_fallback(tmp_path, kind):
    artifact = tmp_path / "artifact.json"
    if kind == "invalid":
        artifact.write_text("{}")
    settings = Settings(human_knowledge_identity_artifact_path=artifact,
        human_knowledge_retrieval_artifact_path=artifact if kind == "conflicting" else None)
    client = TestClient(create_app(settings))
    assert client.get("/health").status_code == 503
    assert client.post("/resolve", json={"title": "Chevy Nomad"}).status_code == 503


def test_environment_opt_in_and_conflict(monkeypatch):
    monkeypatch.setenv("PVR_HUMAN_KNOWLEDGE_IDENTITY_ARTIFACT", "/tmp/v4.json")
    monkeypatch.delenv("PVR_HUMAN_KNOWLEDGE_RETRIEVAL_ARTIFACT", raising=False)
    assert Settings.from_env().human_knowledge_identity_artifact_path == Path("/tmp/v4.json")
    monkeypatch.setenv("PVR_HUMAN_KNOWLEDGE_RETRIEVAL_ARTIFACT", "/tmp/v3.json")
    with pytest.raises(ValueError, match="cannot be configured together"):
        Settings.from_env()
