from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from product_variant_resolver.human_knowledge_snapshot import build_plan, canonical_bytes
from product_variant_resolver.human_knowledge_storage_profile import (
    FILE_MODE,
    MOCK_STATUS,
    POSTGRES_MODE,
    REQUIRED_RUNTIME_SOURCES,
    RUNTIME_STATUS,
    STORAGE_PROTOCOL,
    STORAGE_PROTOCOL_SHA256,
    HumanStorageHydration,
    StorageIntegrityError,
    load_profile,
)

ROOT = Path(__file__).resolve().parents[1]
DATABASE = "pvr_t49_2_0123456789ab"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def profile_payload(mode: str = FILE_MODE, *, status: str = MOCK_STATUS) -> dict[str, Any]:
    sources = {path: sha(ROOT / path) for path in sorted(REQUIRED_RUNTIME_SOURCES)}
    return {
        "schema_version": "pvr-human-storage-runtime-profile-v1",
        "artifact_version": "human-storage-profile-development-v1-0123456789ab",
        "status": status,
        "profile_version": "human-storage-hydration-development-v1",
        "mode": mode,
        "storage_protocol": {"file": STORAGE_PROTOCOL, "sha256": STORAGE_PROTOCOL_SHA256},
        "snapshot": {
            "id": "human-knowledge-plan-v1-f7830e460650e99ab5107ec0f049c96d2dcf322daa5c140c5847a53f969e144f",
            "content_sha256": "f7830e460650e99ab5107ec0f049c96d2dcf322daa5c140c5847a53f969e144f",
            "plan_file": "reports/human-knowledge-snapshot-v1/plan.json",
            "plan_byte_sha256": "d56391d19bf2d61acb422c05c9e9b8a21aaab81efe5c0185b0529a58d39a11a2",
            "documents": 142, "provisional_variant": 100, "review_family": 42,
        },
        "math": {
            "artifact_file": "config/human-knowledge-retrieval-v4.json",
            "artifact_sha256": "82c94a2629da6936bec3e4a2983e67c70d69e94cb94a9817375f891d59b1ae6b",
            "protocol_sha256": "31802be99f02698423c4526bbd8752e6f517fcbef8ca8080926d019f55083fde",
        },
        "source_sha256": sources,
        "actual_adapter_source_manifest_sha256": hashlib.sha256(canonical_bytes(sources)).hexdigest(),
        "database": ({"url_environment": "PVR_HUMAN_STORAGE_TEST_DATABASE_URL",
                      "expected_database": DATABASE} if mode == POSTGRES_MODE else None),
        "ready_for_real_outputs": status == RUNTIME_STATUS,
        "runtime_image_ids": (["sha256:" + "1" * 64, "sha256:" + "2" * 64]
                              if status == RUNTIME_STATUS else None),
        "human_authority": "debug_only_canonical_unchanged",
        "automatic_fallback": False,
    }


def write_profile(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "profile.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_strict_file_profile_and_exact_hydration(tmp_path: Path) -> None:
    path = write_profile(tmp_path, profile_payload())
    profile = load_profile(path, root=ROOT, allow_private_mock=True)
    storage = HumanStorageHydration(profile)
    assert len(storage.catalog.documents) == 142
    assert sum(item.knowledge_type == "provisional_variant"
               for item in storage.catalog.documents) == 100
    assert sum(item.knowledge_type == "review_family"
               for item in storage.catalog.documents) == 42
    assert storage.probe() >= 0
    assert profile.mode == FILE_MODE and profile.ready_for_real_outputs is False


@pytest.mark.parametrize("mutation", ["extra", "mode", "protocol", "snapshot", "math",
                                      "source", "manifest", "fallback"])
def test_profile_drift_or_unknown_fields_fail_closed(tmp_path: Path, mutation: str) -> None:
    payload = profile_payload()
    if mutation == "extra":
        payload["unexpected"] = True
    elif mutation == "mode":
        payload["mode"] = "latest"
    elif mutation == "protocol":
        payload["storage_protocol"]["sha256"] = "0" * 64
    elif mutation == "snapshot":
        payload["snapshot"]["documents"] = 141
    elif mutation == "math":
        payload["math"]["protocol_sha256"] = "0" * 64
    elif mutation == "source":
        payload["source_sha256"].pop("src/product_variant_resolver/api.py")
    elif mutation == "manifest":
        payload["actual_adapter_source_manifest_sha256"] = "0" * 64
    else:
        payload["automatic_fallback"] = True
    with pytest.raises(ValueError):
        load_profile(write_profile(tmp_path, payload), root=ROOT, allow_private_mock=True)


def test_private_mock_requires_literal_opt_in_and_cannot_be_runtime_ready(tmp_path: Path) -> None:
    path = write_profile(tmp_path, profile_payload())
    with pytest.raises(ValueError, match="private mock"):
        load_profile(path, root=ROOT)
    payload = profile_payload()
    payload["ready_for_real_outputs"] = True
    with pytest.raises(ValueError, match="private mock"):
        load_profile(write_profile(tmp_path, payload), root=ROOT, allow_private_mock=True)


@pytest.mark.parametrize("images", [None, [], ["sha256:" + "1" * 64], ["latest", "latest"]])
def test_runtime_profile_requires_two_content_addressed_images(
    tmp_path: Path, images: Any,
) -> None:
    payload = profile_payload(status=RUNTIME_STATUS)
    payload["runtime_image_ids"] = images
    with pytest.raises(ValueError, match="two frozen"):
        load_profile(write_profile(tmp_path, payload), root=ROOT)


def test_valid_runtime_shape_loads_without_running_retrieval(tmp_path: Path) -> None:
    profile = load_profile(write_profile(tmp_path, profile_payload(status=RUNTIME_STATUS)), root=ROOT)
    assert profile.ready_for_real_outputs is True


class FakeRepository:
    def __init__(self, plans: list[dict[str, Any] | Exception]) -> None:
        self.plans = plans
        self.calls: list[tuple[str, str, Path]] = []

    def read_snapshot(self, snapshot_id: str, *, content_sha256: str,
                      root: Path) -> dict[str, Any]:
        self.calls.append((snapshot_id, content_sha256, root))
        item = self.plans[min(len(self.calls) - 1, len(self.plans) - 1)]
        if isinstance(item, Exception):
            raise item
        return copy.deepcopy(item)


def test_postgres_profile_uses_explicit_env_and_full_reader_each_probe(tmp_path: Path) -> None:
    url = "postgresql+psycopg://reader:secret@internal/" + DATABASE
    profile = load_profile(write_profile(tmp_path, profile_payload(POSTGRES_MODE)), root=ROOT,
        environ={"PVR_HUMAN_STORAGE_TEST_DATABASE_URL": url}, allow_private_mock=True)
    repository = FakeRepository([build_plan(ROOT)])
    captured: list[tuple[str, str]] = []

    def factory(value: str, expected: str) -> FakeRepository:
        captured.append((value, expected))
        return repository

    storage = HumanStorageHydration(profile,
        environ={"PVR_HUMAN_STORAGE_TEST_DATABASE_URL": url}, repository_factory=factory)
    storage.probe()
    storage.probe()
    assert captured == [(url, DATABASE)]
    assert len(repository.calls) == 3  # startup plus one complete read per request probe
    assert all(call[0].endswith(call[1]) for call in repository.calls)


def test_postgres_startup_failure_has_no_file_fallback(tmp_path: Path) -> None:
    url = "postgresql+psycopg://reader:secret@internal/" + DATABASE
    profile = load_profile(write_profile(tmp_path, profile_payload(POSTGRES_MODE)), root=ROOT,
        environ={"PVR_HUMAN_STORAGE_TEST_DATABASE_URL": url}, allow_private_mock=True)
    repository = FakeRepository([RuntimeError("database unavailable")])
    with pytest.raises(StorageIntegrityError):
        HumanStorageHydration(profile,
            environ={"PVR_HUMAN_STORAGE_TEST_DATABASE_URL": url},
            repository_factory=lambda _url, _database: repository)
    assert len(repository.calls) == 1


def test_postgres_missing_url_or_wrong_database_rejected_before_repository(tmp_path: Path) -> None:
    payload = profile_payload(POSTGRES_MODE)
    path = write_profile(tmp_path, payload)
    with pytest.raises(ValueError, match="URL is unavailable"):
        load_profile(path, root=ROOT, environ={}, allow_private_mock=True)
    payload["database"]["expected_database"] = "production"
    with pytest.raises(ValueError, match="disposable"):
        load_profile(write_profile(tmp_path, payload), root=ROOT,
            environ={"PVR_HUMAN_STORAGE_TEST_DATABASE_URL": "secret"}, allow_private_mock=True)


def test_explicit_empty_environment_never_inherits_process_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PVR_HUMAN_STORAGE_TEST_DATABASE_URL", "process-secret")
    with pytest.raises(ValueError, match="URL is unavailable"):
        load_profile(write_profile(tmp_path, profile_payload(POSTGRES_MODE)), root=ROOT,
                     environ={}, allow_private_mock=True)


def test_duplicate_json_keys_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version":"one","schema_version":"two"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        load_profile(path, root=ROOT, allow_private_mock=True)


@pytest.mark.parametrize("fault", [RuntimeError("disconnected"), ValueError("partial")])
def test_runtime_fault_latches_without_retry_or_fallback(tmp_path: Path, fault: Exception) -> None:
    url = "postgresql+psycopg://reader:secret@internal/" + DATABASE
    profile = load_profile(write_profile(tmp_path, profile_payload(POSTGRES_MODE)), root=ROOT,
        environ={"PVR_HUMAN_STORAGE_TEST_DATABASE_URL": url}, allow_private_mock=True)
    repository = FakeRepository([build_plan(ROOT), fault, build_plan(ROOT)])
    storage = HumanStorageHydration(profile,
        environ={"PVR_HUMAN_STORAGE_TEST_DATABASE_URL": url},
        repository_factory=lambda _url, _database: repository)
    with pytest.raises(StorageIntegrityError):
        storage.probe()
    with pytest.raises(StorageIntegrityError, match="latched"):
        storage.probe()
    assert len(repository.calls) == 2  # restored third value is never retried until restart


def test_changed_complete_snapshot_latches(tmp_path: Path) -> None:
    profile = load_profile(write_profile(tmp_path, profile_payload()), root=ROOT,
                           allow_private_mock=True)
    storage = HumanStorageHydration(profile)
    changed = copy.deepcopy(build_plan(ROOT))
    changed["documents"][0]["origin"] = {"changed": True}
    storage._read_selected = lambda: changed  # type: ignore[method-assign]
    with pytest.raises(StorageIntegrityError, match="changed"):
        storage.probe()
    with pytest.raises(StorageIntegrityError, match="latched"):
        storage.probe()


def test_profile_path_is_bounded_and_symlink_rejected(tmp_path: Path) -> None:
    payload = profile_payload()
    payload["source_sha256"]["../outside"] = "0" * 64
    payload["actual_adapter_source_manifest_sha256"] = hashlib.sha256(
        canonical_bytes(payload["source_sha256"])).hexdigest()
    with pytest.raises(ValueError, match="contained"):
        load_profile(write_profile(tmp_path, payload), root=ROOT, allow_private_mock=True)
    target = write_profile(tmp_path, profile_payload())
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="regular"):
        load_profile(link, root=ROOT, allow_private_mock=True)
