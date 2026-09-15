from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "runtime_source_freeze", ROOT / "scripts/freeze_human_storage_runtime_sources.py")
assert spec and spec.loader
freeze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(freeze)


@pytest.fixture
def local_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    def local_git(root: Path, commit: str, relative: str) -> bytes:
        return (ROOT / relative).read_bytes()

    monkeypatch.setattr(freeze, "git_bytes", local_git)
    files = freeze.build_bundle(ROOT, "0" * 40)
    manifest = json.loads(files["manifest.json"])
    for relative in manifest["source_sha256"]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return tmp_path


def test_deterministic_pending_runtime_contract(local_root: Path) -> None:
    bundle = freeze.build_bundle(local_root, "0" * 40)
    assert bundle == freeze.build_bundle(local_root, "0" * 40)
    manifest = json.loads(bundle["manifest.json"])
    binding = json.loads(bundle["protocol-binding.json"])
    template = json.loads(bundle["profile-template.json"])
    assert manifest["source_count"] >= 42
    assert manifest["real_sql_executed"] is False
    assert manifest["runtime_image_ids"] is None
    assert binding["actual_adapter_source_manifest_sha256"] == manifest[
        "actual_adapter_source_manifest_sha256"]
    assert binding["ready_for_real_outputs"] is False
    assert binding["new_storage_profile_outputs_viewed"] is False
    assert template["not_a_runnable_profile"] is True
    assert template["math"]["protocol_sha256"] != binding["declared_profile_sha256"]


def test_publish_check_and_refuse_overwrite(local_root: Path) -> None:
    freeze.publish(local_root, "0" * 40)
    freeze.check(local_root)
    before = {path.name: path.read_bytes() for path in (local_root / freeze.OUTPUT).iterdir()}
    with pytest.raises(ValueError, match="refusing overwrite"):
        freeze.publish(local_root, "0" * 40)
    assert before == {path.name: path.read_bytes() for path in (local_root / freeze.OUTPUT).iterdir()}


@pytest.mark.parametrize("relative", [
    "src/product_variant_resolver/human_knowledge_storage_profile.py",
    "src/product_variant_resolver/human_knowledge_storage_app.py",
    "data/human_backed_catalog.json",
    "reports/human-knowledge-snapshot-v1/plan.json",
])
def test_runtime_or_data_source_drift_rejected_before_output(
    local_root: Path, relative: str,
) -> None:
    path = local_root / relative
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError):
        freeze.publish(local_root, "0" * 40)
    assert not (local_root / freeze.OUTPUT).exists()


@pytest.mark.parametrize("name", ["manifest.json", "profile-template.json",
                                  "protocol-binding.json", "report.md"])
def test_frozen_member_change_rejected(local_root: Path, name: str) -> None:
    freeze.publish(local_root, "0" * 40)
    path = local_root / freeze.OUTPUT / name
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="differs"):
        freeze.check(local_root)


def test_partial_extra_and_symlink_rejected(local_root: Path) -> None:
    freeze.publish(local_root, "0" * 40)
    member = local_root / freeze.OUTPUT / "report.md"
    member.unlink()
    with pytest.raises(ValueError, match="partial"):
        freeze.check(local_root)
    member.write_bytes(b"wrong")
    (local_root / freeze.OUTPUT / "extra").write_bytes(b"extra")
    with pytest.raises(ValueError, match="partial"):
        freeze.check(local_root)


def test_changed_or_invalid_committed_producer_rejected(
    local_root: Path,
) -> None:
    producer = local_root / freeze.PRODUCER
    producer.write_bytes(producer.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="must match committed"):
        freeze.build_bundle(local_root, "0" * 40)


def test_invalid_commit_rejected() -> None:
    with pytest.raises(ValueError, match="invalid committed"):
        freeze.git_bytes(ROOT, "--bad", freeze.PRODUCER)
