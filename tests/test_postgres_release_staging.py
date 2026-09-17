from __future__ import annotations

import copy
import json
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from product_variant_resolver.postgres_release_staging import PostgresReleaseStagingRepository
from product_variant_resolver.release_staging import build_snapshot
from tests.release_staging_test_support import write_exact_synthetic_inputs

ROOT = Path(__file__).resolve().parents[1]


class FakeEngine:
    dialect = SimpleNamespace(name="postgresql")

    def __init__(self) -> None:
        self.begins = self.commits = self.rollbacks = 0

    @contextmanager
    def begin(self) -> Iterator[object]:
        self.begins += 1
        try:
            yield object()
            self.commits += 1
        except Exception:
            self.rollbacks += 1
            raise


class RecordingRepository(PostgresReleaseStagingRepository):
    def __init__(self, engine: FakeEngine, stored: dict[str, Any] | None = None) -> None:
        super().__init__(engine)
        self.stored = stored
        self.header: dict[str, Any] | None = None
        self.inserted: list[dict[str, Any]] = []
        self.statements: list[str] = []
        self.fail_after: int | None = None

    def _execute(
        self, connection: Any, statement: str, parameters: dict[str, Any] | None = None
    ) -> Any:
        self.statements.append(statement)
        if statement.startswith("INSERT INTO public.release_source_batch"):
            assert parameters is not None
            import json

            self.header = {
                **parameters,
                "files": json.loads(parameters["files"]),
                "counts": json.loads(parameters["counts"]),
            }
        return None

    def _read_snapshot(self, connection: Any, batch_id: str) -> dict[str, Any] | None:
        if self.stored is not None:
            return self.stored
        if self.header is None:
            return None
        return {**self.header, "records": self.inserted}

    def _insert_record(
        self, connection: Any, batch_id: str, ordinal: int, record: dict[str, Any]
    ) -> None:
        self.inserted.append(copy.deepcopy(record))
        if ordinal == self.fail_after:
            raise ValueError("simulated record insertion failure")


@pytest.fixture(scope="module")
def synthetic_root(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("release-staging-postgres")
    write_exact_synthetic_inputs(root)
    return root


@pytest.fixture(scope="module")
def snapshot(synthetic_root: Path) -> dict[str, Any]:
    return build_snapshot(synthetic_root)


def test_committed_public_manifest_has_consistent_batch_and_counts() -> None:
    path = ROOT / "reports/local-release-staging-v1/manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    assert manifest["batch_id"] == "local-release-staging-v1-" + manifest["content_sha256"]
    assert manifest["public_scope"] == "summary_and_checksums_only_no_source_rows"
    assert manifest["counts"]["staged_observations"] == 1763
    assert manifest["counts"]["unknown_colors"] == 1763
    assert [item["row_count"] for item in manifest["files"]] == [445, 441, 440, 437]
    assert all(len(item["sha256"]) == 64 for item in manifest["files"])


def test_sqlite_is_rejected() -> None:
    engine = FakeEngine()
    engine.dialect = SimpleNamespace(name="sqlite")
    with pytest.raises(ValueError, match="PostgreSQL"):
        PostgresReleaseStagingRepository(engine)


def test_invalid_snapshot_fails_before_transaction(
    snapshot: dict[str, Any],
    synthetic_root: Path,
) -> None:
    engine = FakeEngine()
    repository = RecordingRepository(engine)
    invalid = copy.deepcopy(snapshot)
    invalid["records"].pop()
    with pytest.raises(ValueError, match="complete local inputs"):
        repository.import_snapshot(invalid, root=synthetic_root)
    assert engine.begins == 0 and repository.statements == []


def test_first_import_is_one_transaction_and_isolated(
    snapshot: dict[str, Any],
    synthetic_root: Path,
) -> None:
    engine = FakeEngine()
    repository = RecordingRepository(engine)
    assert repository.import_snapshot(snapshot, root=synthetic_root) == "inserted"
    assert repository.inserted == snapshot["records"]
    assert len(repository.inserted) == 1763
    assert engine.commits == 1 and engine.rollbacks == 0
    sql = " ".join(repository.statements)
    assert "LOCK TABLE public.release_source_batch" in sql
    assert all(name not in sql for name in ("product_variant", "product_alias", "hk_"))


def test_identical_import_is_verified_no_op(
    snapshot: dict[str, Any],
    synthetic_root: Path,
) -> None:
    engine = FakeEngine()
    repository = RecordingRepository(engine, stored=copy.deepcopy(snapshot))
    assert repository.import_snapshot(snapshot, root=synthetic_root) == "unchanged"
    assert repository.inserted == [] and repository.header is None
    assert engine.commits == 1 and engine.rollbacks == 0


def test_batch_collision_rolls_back(snapshot: dict[str, Any], synthetic_root: Path) -> None:
    stored = copy.deepcopy(snapshot)
    stored["content_sha256"] = "0" * 64
    engine = FakeEngine()
    repository = RecordingRepository(engine, stored=stored)
    with pytest.raises(ValueError, match="collision"):
        repository.import_snapshot(snapshot, root=synthetic_root)
    assert engine.rollbacks == 1 and engine.commits == 0


def test_mid_import_failure_aborts_transaction(
    snapshot: dict[str, Any],
    synthetic_root: Path,
) -> None:
    engine = FakeEngine()
    repository = RecordingRepository(engine)
    repository.fail_after = 880
    with pytest.raises(ValueError, match="simulated"):
        repository.import_snapshot(snapshot, root=synthetic_root)
    assert engine.rollbacks == 1 and engine.commits == 0
    assert len(repository.inserted) == 881
