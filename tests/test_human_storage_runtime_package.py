from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_freezer() -> ModuleType:
    path = ROOT / "scripts/freeze_human_storage_runtime_package.py"
    spec = importlib.util.spec_from_file_location("freeze_human_storage_runtime_package", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_compose_package_is_explicit_and_default_remains_original() -> None:
    compose = (ROOT / "docker-compose.human-storage.yml").read_text()
    assert 'profiles: ["human-storage"]' in compose
    assert "product_variant_resolver.human_knowledge_storage_app:app" in compose
    assert "PVR_HUMAN_STORAGE_PROFILE_PATH: /runtime/profile.json" in compose
    assert "create_host_path: false" in compose
    assert "127.0.0.1:${PVR_HUMAN_STORAGE_PORT:-8001}:8000" in compose
    assert "PVR_HUMAN_STORAGE_TEST_DATABASE_URL" not in compose
    dockerfile = (ROOT / "Dockerfile.human-storage").read_text()
    assert 'CMD ["uvicorn", "product_variant_resolver.api:app"' in dockerfile


def test_docker_context_contains_only_required_storage_evidence() -> None:
    ignore = (ROOT / "Dockerfile.human-storage.dockerignore").read_text()
    dockerfile = (ROOT / "Dockerfile.human-storage").read_text()
    for name in (
        "manifest.json",
        "normalized.json",
        "priority-2-batch-05-adjudicated-queue-manifest.json",
        "priority-2-batch-05-adjudicated-queue.json",
    ):
        assert f"!data/external/hot-wheels-wiki/pilot-2025/{name}" in ignore
    assert ignore.startswith("**\n") and "!reports/**" not in ignore
    assert "!reports/human-knowledge-identity-development-v1/selection.json" in ignore
    assert "!reports/human-knowledge-snapshot-v1/plan.json" in ignore
    assert "!reports/family-retrieval-development-v1/selection.json" in ignore
    assert "!reports/family-retrieval-development-v1/selection.md" in ignore
    assert "COPY scripts/build_human_knowledge_identity_protocol.py" in dockerfile
    assert "COPY scripts/freeze_human_storage_runtime_sources.py" in dockerfile


def test_package_profile_binds_exact_image_without_changing_source_math() -> None:
    module = load_freezer()
    image_id = "sha256:" + "a" * 64
    profile_raw, manifest_raw, _readme = module.package_payloads(image_id, "b" * 40)
    profile = json.loads(profile_raw)
    manifest = json.loads(manifest_raw)
    base = json.loads(module.BASE.read_bytes())
    assert profile["runtime_image_ids"][1] == image_id
    assert profile["source_sha256"] == base["source_sha256"]
    assert profile["math"] == base["math"]
    assert manifest["image"]["id"] == image_id
    assert manifest["constraints"]["default_api_unchanged"] is True
    assert manifest["constraints"]["database_used"] is False


@pytest.mark.parametrize("image_id", ["latest", "sha256:short", "sha256:" + "g" * 64])
def test_package_rejects_non_content_addressed_image(image_id: str) -> None:
    with pytest.raises(ValueError, match="content-addressed"):
        load_freezer().package_payloads(image_id, "b" * 40)


def test_runtime_verifier_uses_owned_compose_cleanup_and_exclusive_output() -> None:
    source = (ROOT / "scripts/verify_human_storage_runtime_package.py").read_text()
    assert "com.docker.compose.project=" in source
    assert '"down", "--remove-orphans"' in source
    assert "path.exists() or path.is_symlink()" in source
    assert '"--no-build"' in source
    assert "docker volume" not in source and '"--volumes"' not in source
