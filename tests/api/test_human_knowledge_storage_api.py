from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from product_variant_resolver.api import create_app as create_default_app
from product_variant_resolver.config import Settings
from product_variant_resolver.human_knowledge_snapshot import build_plan, canonical_bytes
from product_variant_resolver.human_knowledge_storage_app import (
    HumanStorageResolverService,
    create_app,
)
from product_variant_resolver.human_knowledge_storage_profile import (
    FILE_MODE,
    MOCK_STATUS,
    REQUIRED_RUNTIME_SOURCES,
    STORAGE_PROTOCOL,
    STORAGE_PROTOCOL_SHA256,
)

ROOT = Path(__file__).resolve().parents[2]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def profile_path(tmp_path: Path) -> Path:
    sources = {path: sha(ROOT / path) for path in sorted(REQUIRED_RUNTIME_SOURCES)}
    payload = {
        "schema_version": "pvr-human-storage-runtime-profile-v1",
        "artifact_version": "human-storage-profile-development-v1-0123456789ab",
        "status": MOCK_STATUS, "profile_version": "human-storage-hydration-development-v1",
        "mode": FILE_MODE,
        "storage_protocol": {"file": STORAGE_PROTOCOL, "sha256": STORAGE_PROTOCOL_SHA256},
        "snapshot": {"id": "human-knowledge-plan-v1-f7830e460650e99ab5107ec0f049c96d2dcf322daa5c140c5847a53f969e144f",
            "content_sha256": "f7830e460650e99ab5107ec0f049c96d2dcf322daa5c140c5847a53f969e144f",
            "plan_file": "reports/human-knowledge-snapshot-v1/plan.json",
            "plan_byte_sha256": "d56391d19bf2d61acb422c05c9e9b8a21aaab81efe5c0185b0529a58d39a11a2",
            "documents": 142, "provisional_variant": 100, "review_family": 42},
        "math": {"artifact_file": "config/human-knowledge-retrieval-v4.json",
            "artifact_sha256": "82c94a2629da6936bec3e4a2983e67c70d69e94cb94a9817375f891d59b1ae6b",
            "protocol_sha256": "31802be99f02698423c4526bbd8752e6f517fcbef8ca8080926d019f55083fde"},
        "source_sha256": sources,
        "actual_adapter_source_manifest_sha256": hashlib.sha256(canonical_bytes(sources)).hexdigest(),
        "database": None, "ready_for_real_outputs": False, "runtime_image_ids": None,
        "human_authority": "debug_only_canonical_unchanged", "automatic_fallback": False,
    }
    path = tmp_path / "private-profile.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.fixture
def clients(tmp_path: Path):
    settings = Settings(catalog_path=ROOT / "data/catalog.json", ui_path=ROOT / "ui")
    experimental_app = create_app(settings, profile_path=profile_path(tmp_path), root=ROOT,
                                  allow_private_mock=True)
    return TestClient(create_default_app(settings)), TestClient(experimental_app), experimental_app


@pytest.mark.parametrize("title", ["2022 Chevy Nomad Red #101", "Chevy Nomad",
                                    "red toy boxed", "unrelated qzxv"])
def test_nondebug_canonical_response_is_byte_equivalent(clients: Any, title: str) -> None:
    default, experimental, _app = clients
    expected = default.post("/resolve", json={"title": title}, headers={"x-request-id": "same"})
    actual = experimental.post("/resolve", json={"title": title}, headers={"x-request-id": "same"})
    assert expected.status_code == actual.status_code == 200
    assert expected.content == actual.content


def test_valid_debug_request_reports_storage_without_changing_math(clients: Any) -> None:
    _default, experimental, _app = clients
    response = experimental.post("/resolve", json={"title": "2022 Chevy Nomad Red #101", "debug": True,
                                                    "debug_candidate_limit": 5})
    assert response.status_code == 200
    debug = response.json()["debug"]
    assert debug["model_versions"]["human_knowledge"] == "human-knowledge-hybrid-v4"
    assert debug["model_versions"]["human_knowledge_storage"].startswith(
        "human-storage-profile-development-v1-")
    assert len(debug["model_versions"]["human_knowledge_storage_sha256"]) == 64
    assert debug["timings_ms"]["human_storage_integrity"] >= 0
    assert debug["human_knowledge_retrieval_artifact_sha256"] == sha(
        ROOT / "config/human-knowledge-retrieval-v4.json")
    assert response.json()["canonical_uuid"] is not None


def test_health_and_each_valid_resolve_run_integrity_gate(
    clients: Any, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _default, experimental, app = clients
    service = app.state.service
    assert isinstance(service, HumanStorageResolverService)
    calls = 0
    original = service.storage.probe

    def counted_probe() -> float:
        nonlocal calls
        calls += 1
        return original()

    monkeypatch.setattr(service.storage, "probe", counted_probe)
    health = experimental.get("/health")
    assert health.status_code == 200
    dependency = health.json()["dependencies"]["human_knowledge_storage"]
    assert dependency == {"ready": True,
        "version": service.storage_profile.artifact_version,
        "detail": "file_snapshot_reference; immutable142 snapshot; complete integrity gate"}
    assert experimental.post("/resolve", json={"title": "Chevy Nomad"}).status_code == 200
    assert calls == 2


@pytest.mark.parametrize("request_case", [
    {"content": b"{", "headers": {"content-type": "application/json"}, "status": 400},
    {"content": b"{}", "headers": {"content-type": "text/plain"}, "status": 415},
    {"json": {"title": "   "}, "status": 422},
    {"json": {"title": "x" * 501}, "status": 422},
])
def test_invalid_http_never_probes_storage(clients: Any, monkeypatch: pytest.MonkeyPatch,
                                           request_case: dict[str, Any]) -> None:
    _default, experimental, app = clients
    service = app.state.service
    assert isinstance(service, HumanStorageResolverService)
    calls = 0

    def probe() -> float:
        nonlocal calls
        calls += 1
        return 0

    monkeypatch.setattr(service.storage, "probe", probe)
    case = dict(request_case)
    status = case.pop("status")
    response = experimental.post("/resolve", **case)
    assert response.status_code == status and calls == 0


def test_debug_disabled_is_422_before_probe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(catalog_path=ROOT / "data/catalog.json", ui_path=ROOT / "ui",
                        debug_enabled=False)
    app = create_app(settings, profile_path=profile_path(tmp_path), root=ROOT,
                     allow_private_mock=True)
    service = app.state.service
    assert isinstance(service, HumanStorageResolverService)
    calls = 0

    def probe() -> float:
        nonlocal calls
        calls += 1
        return 0

    monkeypatch.setattr(service.storage, "probe", probe)
    response = TestClient(app).post("/resolve", json={"title": "Chevy Nomad", "debug": True})
    assert response.status_code == 422 and calls == 0


@pytest.mark.parametrize("endpoint", ["health", "resolve"])
def test_runtime_integrity_failure_is_sticky_503_without_identity(
    clients: Any, monkeypatch: pytest.MonkeyPatch, endpoint: str,
) -> None:
    _default, experimental, app = clients
    service = app.state.service
    assert isinstance(service, HumanStorageResolverService)
    good = copy.deepcopy(build_plan(ROOT))
    calls = 0

    def fail_then_restore() -> dict[str, Any]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("simulated backend loss")
        return good

    monkeypatch.setattr(service.storage, "_read_selected", fail_then_restore)
    first = (experimental.get("/health") if endpoint == "health" else
             experimental.post("/resolve", json={"title": "Chevy Nomad"}))
    assert first.status_code == 503
    if endpoint == "health":
        dependency = first.json()["dependencies"]["human_knowledge_storage"]
        assert dependency["ready"] is False
        assert dependency["version"] == service.storage_profile.artifact_version
    if endpoint == "resolve":
        assert "canonical_uuid" not in first.json() and first.json()["error"]["code"] == "dependency_unavailable"
    assert app.state.service is None
    assert experimental.get("/health").status_code == 503
    later = experimental.post("/resolve", json={"title": "Chevy Nomad"})
    assert later.status_code == 503 and "canonical_uuid" not in later.json()
    assert calls == 1  # backend restoration is not retried inside this process


def test_startup_profile_failure_is_notready_without_default_fallback(tmp_path: Path) -> None:
    path = profile_path(tmp_path)
    payload = json.loads(path.read_text())
    payload["snapshot"]["documents"] = 141
    path.write_text(json.dumps(payload))
    app = create_app(Settings(catalog_path=ROOT / "data/catalog.json", ui_path=ROOT / "ui"),
                     profile_path=path, root=ROOT, allow_private_mock=True)
    client = TestClient(app)
    assert client.get("/health").status_code == 503
    dependency = client.get("/health").json()["dependencies"]["human_knowledge_storage"]
    assert dependency == {"ready": False, "version": None,
                          "detail": "configured human storage is unavailable"}
    response = client.post("/resolve", json={"title": "Chevy Nomad"})
    assert response.status_code == 503 and "canonical_uuid" not in response.json()


@pytest.mark.parametrize("change", ["postgres", "v3", "v4"])
def test_canonical_or_legacy_environment_switches_conflict(tmp_path: Path, change: str) -> None:
    settings = Settings(catalog_path=ROOT / "data/catalog.json", ui_path=ROOT / "ui")
    if change == "postgres":
        settings = replace(settings, backend="postgres")
    elif change == "v3":
        settings = replace(settings, human_knowledge_retrieval_artifact_path=Path("v3.json"))
    else:
        settings = replace(settings, human_knowledge_identity_artifact_path=Path("v4.json"))
    app = create_app(settings, profile_path=profile_path(tmp_path), root=ROOT,
                     allow_private_mock=True)
    assert TestClient(app).get("/health").status_code == 503


def test_explicit_module_without_profile_is_notready() -> None:
    app = create_app(Settings(catalog_path=ROOT / "data/catalog.json", ui_path=ROOT / "ui"),
                     environ={})
    client = TestClient(app)
    assert client.get("/health").status_code == 503
    assert client.post("/resolve", json={"title": "Chevy Nomad"}).status_code == 503
