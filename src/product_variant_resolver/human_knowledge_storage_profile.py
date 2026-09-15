"""Strict, fail-closed human-knowledge storage hydration for the T49.3 experiment."""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Protocol, cast

from .human_knowledge import HumanKnowledgeCatalog
from .human_knowledge_persistence import PostgresHumanKnowledgeSnapshotRepository
from .human_knowledge_snapshot import canonical_bytes, decode_document, validate_plan

PROFILE_SCHEMA = "pvr-human-storage-runtime-profile-v1"
PROFILE_VERSION = "human-storage-hydration-development-v1"
FILE_MODE = "file_snapshot_reference"
POSTGRES_MODE = "postgres_snapshot_experiment"
MOCK_STATUS = "private_mock_verified_no_real_outputs"
RUNTIME_STATUS = "source_and_runtime_frozen_for_authorized_isolated_run"
STORAGE_PROTOCOL = "data/evaluation/human-storage-profile-development-v1/freeze/protocol.json"
STORAGE_PROTOCOL_SHA256 = "d42ba490dccc8ab6b38f1087d39867d22e0e3e4990c40932da03c552ad2e6fd4"
MATH_PROTOCOL_SHA256 = "31802be99f02698423c4526bbd8752e6f517fcbef8ca8080926d019f55083fde"
SNAPSHOT_ID = "human-knowledge-plan-v1-f7830e460650e99ab5107ec0f049c96d2dcf322daa5c140c5847a53f969e144f"
SNAPSHOT_SHA256 = "f7830e460650e99ab5107ec0f049c96d2dcf322daa5c140c5847a53f969e144f"
PLAN = "reports/human-knowledge-snapshot-v1/plan.json"
PLAN_SHA256 = "d56391d19bf2d61acb422c05c9e9b8a21aaab81efe5c0185b0529a58d39a11a2"
MATH_ARTIFACT = "config/human-knowledge-retrieval-v4.json"
MATH_ARTIFACT_SHA256 = "82c94a2629da6936bec3e4a2983e67c70d69e94cb94a9817375f891d59b1ae6b"

REQUIRED_RUNTIME_SOURCES = frozenset({
    "src/product_variant_resolver/api.py",
    "src/product_variant_resolver/calibration.py",
    "src/product_variant_resolver/catalog.py",
    "src/product_variant_resolver/config.py",
    "src/product_variant_resolver/human_knowledge.py",
    "src/product_variant_resolver/human_knowledge_identity.py",
    "src/product_variant_resolver/human_knowledge_identity_artifact.py",
    "src/product_variant_resolver/human_knowledge_persistence.py",
    "src/product_variant_resolver/human_knowledge_snapshot.py",
    "src/product_variant_resolver/human_knowledge_storage_app.py",
    "src/product_variant_resolver/human_knowledge_storage_profile.py",
    "src/product_variant_resolver/identity.py",
    "src/product_variant_resolver/observability.py",
    "src/product_variant_resolver/policy.py",
    "src/product_variant_resolver/postgres_retrieval.py",
    "src/product_variant_resolver/rerank.py",
    "src/product_variant_resolver/retrieval.py",
    "src/product_variant_resolver/schemas.py",
    "src/product_variant_resolver/service.py",
    "src/product_variant_resolver/signals.py",
    "data/catalog.json",
    MATH_ARTIFACT,
    "data/evaluation/human-knowledge-identity-development-v1/protocol.json",
    "data/evaluation/human-knowledge-identity-development-v1/protocol-manifest.json",
    "reports/human-knowledge-identity-development-v1/selection.json",
    PLAN,
    "data/evaluation/family-retrieval-development-v1/development-pack.json",
    "data/evaluation/family-retrieval-development-v1/development-pack-manifest.json",
})


class StorageIntegrityError(RuntimeError):
    """Configured immutable human storage is unavailable or no longer exact."""


class SnapshotReader(Protocol):
    def read_snapshot(self, snapshot_id: str, *, content_sha256: str,
                      root: Path) -> dict[str, Any]: ...


RepositoryFactory = Callable[[str, str], SnapshotReader]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _object_sha(value: Any) -> str:
    return _sha(canonical_bytes(value))


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key rejected")
        result[key] = value
    return result


def _keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} fields differ")
    return value


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty string")
    return value


def safe_project_path(root: Path, relative: Any) -> Path:
    text = _string(relative, "project path")
    candidate = Path(text)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("project path must be relative and contained")
    path = root / candidate
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("symlinked project path rejected")
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise ValueError("project path is missing") from error
    if not resolved.is_file() or not resolved.is_relative_to(root.resolve()):
        raise ValueError("project path must be a contained file")
    return resolved


@dataclass(frozen=True, slots=True)
class HumanStorageProfile:
    artifact_version: str
    artifact_sha256: str
    mode: str
    root: Path
    plan_path: Path
    math_artifact_path: Path
    source_sha256: dict[str, str]
    database_url_environment: str | None
    expected_database: str | None
    ready_for_real_outputs: bool


def load_profile(path: Path, *, root: Path, environ: Mapping[str, str] | None = None,
                 allow_private_mock: bool = False) -> HumanStorageProfile:
    if allow_private_mock is not True and allow_private_mock is not False:
        raise ValueError("private mock permission must be a literal boolean")
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1_000_000:
        raise ValueError("profile must be a regular JSON file no larger than 1 MB")
    try:
        raw = path.read_bytes()
        data = json.loads(raw, object_pairs_hook=_no_duplicate_keys)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("profile JSON is unavailable or malformed") from error
    profile = _keys(data, {"schema_version", "artifact_version", "status", "profile_version",
        "mode", "storage_protocol", "snapshot", "math", "source_sha256",
        "actual_adapter_source_manifest_sha256", "database", "ready_for_real_outputs",
        "runtime_image_ids", "human_authority", "automatic_fallback"}, "profile")
    if (profile["schema_version"] != PROFILE_SCHEMA or profile["profile_version"] != PROFILE_VERSION
            or profile["human_authority"] != "debug_only_canonical_unchanged"
            or profile["automatic_fallback"] is not False):
        raise ValueError("profile identity or authority differs")
    artifact_version = _string(profile["artifact_version"], "artifact version")
    if not re.fullmatch(r"human-storage-profile-development-v1-[0-9a-f]{12}", artifact_version):
        raise ValueError("profile artifact version differs")
    mode = profile["mode"]
    if mode not in {FILE_MODE, POSTGRES_MODE}:
        raise ValueError("unknown storage mode")
    protocol = _keys(profile["storage_protocol"], {"file", "sha256"}, "storage protocol")
    if protocol != {"file": STORAGE_PROTOCOL, "sha256": STORAGE_PROTOCOL_SHA256}:
        raise ValueError("storage protocol binding differs")
    snapshot = _keys(profile["snapshot"], {"id", "content_sha256", "plan_file",
        "plan_byte_sha256", "documents", "provisional_variant", "review_family"}, "snapshot")
    if snapshot != {"id": SNAPSHOT_ID, "content_sha256": SNAPSHOT_SHA256, "plan_file": PLAN,
            "plan_byte_sha256": PLAN_SHA256, "documents": 142,
            "provisional_variant": 100, "review_family": 42}:
        raise ValueError("snapshot binding differs")
    math = _keys(profile["math"], {"artifact_file", "artifact_sha256",
        "protocol_sha256"}, "math")
    if math != {"artifact_file": MATH_ARTIFACT, "artifact_sha256": MATH_ARTIFACT_SHA256,
                 "protocol_sha256": MATH_PROTOCOL_SHA256}:
        raise ValueError("mathematical artifact binding differs")
    sources = profile["source_sha256"]
    if (not isinstance(sources, dict) or not REQUIRED_RUNTIME_SOURCES.issubset(sources)
            or any(not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
                   for key, value in sources.items())):
        raise ValueError("runtime source manifest is incomplete or malformed")
    if profile["actual_adapter_source_manifest_sha256"] != _object_sha(sources):
        raise ValueError("runtime source manifest checksum differs")
    for relative, expected in sources.items():
        if _sha(safe_project_path(root, relative).read_bytes()) != expected:
            raise ValueError(f"runtime source differs: {relative}")
    if _sha(safe_project_path(root, STORAGE_PROTOCOL).read_bytes()) != STORAGE_PROTOCOL_SHA256:
        raise ValueError("storage protocol bytes differ")
    plan_path = safe_project_path(root, PLAN)
    if _sha(plan_path.read_bytes()) != PLAN_SHA256:
        raise ValueError("snapshot plan bytes differ")
    math_path = safe_project_path(root, MATH_ARTIFACT)
    if _sha(math_path.read_bytes()) != MATH_ARTIFACT_SHA256:
        raise ValueError("math artifact bytes differ")
    ready = profile["ready_for_real_outputs"]
    images = profile["runtime_image_ids"]
    status = profile["status"]
    if status == MOCK_STATUS:
        if allow_private_mock is not True or ready is not False or images is not None:
            raise ValueError("private mock profile cannot produce real outputs")
    elif status == RUNTIME_STATUS:
        if (ready is not True or not isinstance(images, list) or len(images) != 2
                or any(not isinstance(item, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", item)
                       for item in images)):
            raise ValueError("runtime profile lacks two frozen image IDs")
    else:
        raise ValueError("profile status differs")
    database = profile["database"]
    url_environment = expected_database = None
    if mode == FILE_MODE:
        if database is not None:
            raise ValueError("file profile must not carry database configuration")
    else:
        database = _keys(database, {"url_environment", "expected_database"}, "database")
        url_environment = _string(database["url_environment"], "database URL environment")
        expected_database = _string(database["expected_database"], "expected database")
        if (url_environment != "PVR_HUMAN_STORAGE_TEST_DATABASE_URL"
                or not re.fullmatch(r"pvr_t49_2_[0-9a-f]{12}", expected_database)):
            raise ValueError("database binding is not the authorized disposable pattern")
        value = (os.environ if environ is None else environ).get(url_environment, "")
        if not value:
            raise ValueError("configured human storage database URL is unavailable")
    return HumanStorageProfile(artifact_version, _sha(raw), mode, root.resolve(), plan_path,
        math_path, dict(sources), url_environment, expected_database, ready)


def default_repository_factory(database_url: str, expected_database: str) -> SnapshotReader:
    return cast(SnapshotReader, PostgresHumanKnowledgeSnapshotRepository.from_url(database_url,
        expected_database=expected_database, allow_disposable_test=True))


class HumanStorageHydration:
    """A verified startup catalog plus a live complete-snapshot integrity gate."""

    def __init__(self, profile: HumanStorageProfile, *,
                 environ: Mapping[str, str] | None = None,
                 repository_factory: RepositoryFactory = default_repository_factory) -> None:
        self.profile = profile
        self._environ = os.environ if environ is None else environ
        self._repository: SnapshotReader | None = None
        if profile.mode == POSTGRES_MODE:
            assert profile.database_url_environment and profile.expected_database
            database_url = self._environ.get(profile.database_url_environment, "")
            self._repository = repository_factory(database_url, profile.expected_database)
        self._expected = self._read_selected()
        self.catalog = self._catalog(self._expected)
        self._failed = False
        self._lock = threading.Lock()

    def _read_selected(self) -> dict[str, Any]:
        try:
            if self.profile.mode == FILE_MODE:
                if _sha(self.profile.plan_path.read_bytes()) != PLAN_SHA256:
                    raise ValueError("snapshot plan bytes differ")
                plan = cast(dict[str, Any], json.loads(self.profile.plan_path.read_bytes()))
                validate_plan(plan, self.profile.root)
            else:
                assert self._repository is not None
                plan = self._repository.read_snapshot(SNAPSHOT_ID,
                    content_sha256=SNAPSHOT_SHA256, root=self.profile.root)
            if (plan.get("snapshot_id") != SNAPSHOT_ID
                    or plan.get("content_sha256") != SNAPSHOT_SHA256
                    or len(plan.get("documents", [])) != 142):
                raise ValueError("selected snapshot differs")
            return plan
        except Exception as error:
            raise StorageIntegrityError("selected human storage failed integrity validation") from error

    @staticmethod
    def _catalog(plan: dict[str, Any]) -> HumanKnowledgeCatalog:
        documents = [decode_document(entry) for entry in plan["documents"]]
        human = plan["source_contracts"]["human"]
        family = plan["source_contracts"]["family"]
        return HumanKnowledgeCatalog(human["catalog_version"], family["knowledge_version"], documents)

    def probe(self) -> float:
        with self._lock:
            if self._failed:
                raise StorageIntegrityError("human storage is latched unavailable until restart")
            started = perf_counter_ns()
            try:
                current = self._read_selected()
                if canonical_bytes(current) != canonical_bytes(self._expected):
                    raise StorageIntegrityError("selected snapshot changed after startup")
            except Exception as error:
                self._failed = True
                if isinstance(error, StorageIntegrityError):
                    raise
                raise StorageIntegrityError("human storage integrity probe failed") from error
            return round((perf_counter_ns() - started) / 1_000_000, 4)
