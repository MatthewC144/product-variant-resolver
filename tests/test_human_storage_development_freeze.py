from __future__ import annotations

import importlib.util
import json
import shutil
import socket
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "storage_freeze", ROOT / "scripts/freeze_human_storage_development.py")
assert spec and spec.loader
freeze = importlib.util.module_from_spec(spec)
spec.loader.exec_module(freeze)


@pytest.fixture
def local_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    real_git = freeze.git_bytes

    def local_git(root: Path, commit: str, relative: str) -> bytes:
        if relative == freeze.PRODUCER:
            return (ROOT / relative).read_bytes()  # Private producer mock, not committed-run evidence.
        return real_git(ROOT, commit, relative)

    monkeypatch.setattr(freeze, "git_bytes", local_git)
    bundle = freeze.build_bundle(ROOT, freeze.TASK_COMMIT)
    manifest = json.loads(bundle["manifest.json"])
    for relative in [*manifest["source_sha256"], freeze.PRODUCER]:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return tmp_path


def test_deterministic_input_only_freeze(local_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("network is forbidden")

    monkeypatch.setattr(socket, "socket", forbidden)
    bundle = freeze.build_bundle(local_root, freeze.TASK_COMMIT)
    assert bundle == freeze.build_bundle(local_root, freeze.TASK_COMMIT)
    protocol = json.loads(bundle["protocol.json"])
    assert protocol["owner_tasks_and_budgets_confirmed"] is True
    assert protocol["ready_for_real_outputs"] is False
    assert protocol["actual_adapter_source_manifest_sha256"] is None
    assert protocol["runtime_image_ids"] is None
    assert protocol["legacy_final_outputs_already_viewed"] is True
    assert protocol["new_storage_profile_retrieval_executed"] is False
    assert protocol["development"]["cases"] == 199
    assert protocol["snapshot"]["documents"] == 142
    assert protocol["fixed_mathematics"]["character_score_floor"] == 0.5
    assert protocol["cost"]["http_p95_max_ms"] == 250
    approval = json.loads(bundle["approval.json"])
    assert approval["new_isolated_sql_run_authorized"] is False
    assert not any("final-v2" in path for path in json.loads(bundle["manifest.json"])["source_sha256"])


def test_publish_check_and_refuse_overwrite(local_root: Path) -> None:
    freeze.publish_bundle(local_root, freeze.TASK_COMMIT)
    freeze.check_bundle(local_root)
    before = {p.name: p.read_bytes() for p in (local_root / freeze.OUTPUT).iterdir()}
    with pytest.raises(ValueError, match="refusing overwrite"):
        freeze.publish_bundle(local_root, freeze.TASK_COMMIT)
    assert before == {p.name: p.read_bytes() for p in (local_root / freeze.OUTPUT).iterdir()}


@pytest.mark.parametrize("relative", ["data/human_backed_catalog.json",
    "reports/human-knowledge-snapshot-v1/plan.json",
    "data/evaluation/family-retrieval-development-v1/development-pack.json",
    "src/product_variant_resolver/api.py"])
def test_input_drift_fails_before_output(local_root: Path, relative: str) -> None:
    path = local_root / relative
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        freeze.publish_bundle(local_root, freeze.TASK_COMMIT)
    assert not (local_root / freeze.OUTPUT).exists()


@pytest.mark.parametrize("name", ["protocol.json", "approval.json", "manifest.json",
                                 "declared-profile.json", "tasks.md"])
def test_bundle_tampering_rejected(local_root: Path, name: str) -> None:
    freeze.publish_bundle(local_root, freeze.TASK_COMMIT)
    path = local_root / freeze.OUTPUT / name
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="bundle mismatch"):
        freeze.check_bundle(local_root)


@pytest.mark.parametrize("action", ["missing", "extra", "symlink"])
def test_partial_extra_or_symlink_bundle_rejected(local_root: Path, action: str) -> None:
    freeze.publish_bundle(local_root, freeze.TASK_COMMIT)
    path = local_root / freeze.OUTPUT / "approval.json"
    if action == "missing":
        path.unlink()
    elif action == "extra":
        (path.parent / "extra").write_bytes(b"unexpected")
    else:
        raw = path.read_bytes()
        path.unlink()
        target = local_root / "outside.json"
        target.write_bytes(raw)
        path.symlink_to(target)
    with pytest.raises(ValueError):
        freeze.check_bundle(local_root)


def test_approval_hash_and_uncommitted_producer_rejected(
    local_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = freeze.git_bytes

    def changed_git(root: Path, commit: str, relative: str) -> bytes:
        return original(root, commit, relative) + b"changed"

    monkeypatch.setattr(freeze, "git_bytes", changed_git)
    with pytest.raises(ValueError, match="specification hash mismatch"):
        freeze.build_bundle(local_root, freeze.TASK_COMMIT)
    monkeypatch.setattr(freeze, "git_bytes", original)
    path = local_root / freeze.PRODUCER
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="producer must match committed"):
        freeze.build_bundle(local_root, freeze.TASK_COMMIT)


def test_invalid_commit_rejected_without_git(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("git must not run for invalid commit")

    monkeypatch.setattr(subprocess, "run", forbidden)
    with pytest.raises(ValueError, match="invalid committed"):
        freeze.git_bytes(ROOT, "--bad", "irrelevant")
