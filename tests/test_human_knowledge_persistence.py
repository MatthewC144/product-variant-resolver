from __future__ import annotations

import copy
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

import pytest

from product_variant_resolver.human_knowledge_persistence import (
    PostgresHumanKnowledgeSnapshotRepository,
)
from product_variant_resolver.human_knowledge_snapshot import build_plan

ROOT = Path(__file__).resolve().parents[1]
DATABASE = "pvr_t49_2_0123456789ab"


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


class RecordingRepository(PostgresHumanKnowledgeSnapshotRepository):
    def __init__(self, engine: FakeEngine, *, stored: dict[str, Any] | None = None) -> None:
        super().__init__(engine, expected_database=DATABASE, allow_disposable_test=True)
        self.stored = stored
        self.statements: list[str] = []
        self.inserted: list[dict[str, Any]] = []
        self.header: dict[str, Any] | None = None
        self.fail_after: int | None = None

    def _guard_database(self, connection: Any) -> None:
        return None

    def _execute(self, connection: Any, statement: str,
                 parameters: dict[str, Any] | None = None) -> Any:
        self.statements.append(statement)
        if statement.startswith("INSERT INTO public.hk_snapshot"):
            import json
            self.header = json.loads((parameters or {})["plan_header"])
        return None

    def _read_plan(self, connection: Any, snapshot_id: str) -> dict[str, Any] | None:
        if self.stored is not None:
            return self.stored
        return {**self.header, "documents": self.inserted} if self.header else None

    def _insert_document(self, connection: Any, snapshot_id: str, ordinal: int,
                         entry: dict[str, Any]) -> None:
        self.inserted.append(copy.deepcopy(entry))
        if ordinal == self.fail_after:
            raise ValueError("simulated insertion failure")


@pytest.mark.parametrize("permission", [False, 1, None, "true"])
def test_constructor_requires_literal_explicit_permission(permission: Any) -> None:
    with pytest.raises(ValueError, match="authorization"):
        PostgresHumanKnowledgeSnapshotRepository(FakeEngine(), expected_database=DATABASE,
                                                allow_disposable_test=permission)


@pytest.mark.parametrize("database", ["pvr", "production", "pvr_t49_2_", "pvr_t49_2_../../pvr"])
def test_existing_or_unbounded_database_name_rejected(database: str) -> None:
    with pytest.raises(ValueError, match="new T49.2"):
        PostgresHumanKnowledgeSnapshotRepository(FakeEngine(), expected_database=database,
                                                allow_disposable_test=True)


def test_sqlite_is_not_substitute_for_postgres() -> None:
    engine = FakeEngine()
    engine.dialect = SimpleNamespace(name="sqlite")
    with pytest.raises(ValueError, match="PostgreSQL"):
        PostgresHumanKnowledgeSnapshotRepository(engine, expected_database=DATABASE,
                                                allow_disposable_test=True)


def test_invalid_plan_does_not_open_connection() -> None:
    engine = FakeEngine()
    repo = RecordingRepository(engine)
    plan = build_plan(ROOT)
    plan["documents"].pop()
    with pytest.raises(ValueError, match="pinned"):
        repo.import_snapshot(plan, root=ROOT)
    assert engine.begins == 0 and repo.statements == []


def test_insert_only_transaction_and_exact_parity() -> None:
    engine = FakeEngine()
    repo = RecordingRepository(engine)
    plan = build_plan(ROOT)
    assert repo.import_snapshot(plan, root=ROOT) == "inserted"
    assert repo.inserted == plan["documents"]
    assert len(repo.inserted) == 142
    assert engine.commits == 1 and engine.rollbacks == 0
    assert "SHARE ROW EXCLUSIVE" in repo.statements[0]
    assert all("product_variant" not in statement and "UPDATE " not in statement
               and "DELETE " not in statement for statement in repo.statements)


def test_equal_snapshot_is_verified_no_op() -> None:
    engine = FakeEngine()
    repo = RecordingRepository(engine, stored=build_plan(ROOT))
    assert repo.import_snapshot(build_plan(ROOT), root=ROOT) == "unchanged"
    assert repo.inserted == [] and repo.header is None
    assert engine.commits == 1


@pytest.mark.parametrize("mutation", ["type", "partial", "origin", "metadata"])
def test_stored_corruption_is_not_overwritten(mutation: str) -> None:
    stored = copy.deepcopy(build_plan(ROOT))
    if mutation == "type":
        stored["documents"][0]["knowledge_type"] = "canonical_variant"
    elif mutation == "partial":
        stored["documents"].pop()
    elif mutation == "origin":
        stored["documents"][0]["origin"] = {}
    else:
        stored["counts"]["postgresql_writes"] = False
    before = copy.deepcopy(stored)
    engine = FakeEngine()
    repo = RecordingRepository(engine, stored=stored)
    with pytest.raises(ValueError, match="pinned"):
        repo.import_snapshot(build_plan(ROOT), root=ROOT)
    assert repo.stored == before and repo.inserted == [] and repo.header is None
    assert engine.rollbacks == 1 and engine.commits == 0


def test_application_failure_aborts_context_without_claiming_real_sql() -> None:
    engine = FakeEngine()
    repo = RecordingRepository(engine)
    repo.fail_after = 70
    with pytest.raises(ValueError, match="simulated"):
        repo.import_snapshot(build_plan(ROOT), root=ROOT)
    assert len(repo.inserted) == 71
    assert engine.rollbacks == 1 and engine.commits == 0
    # This fake tests orchestration only. Real SQL rollback is proved by the separate Docker verifier.


def test_server_database_guard_rejects_wrong_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = PostgresHumanKnowledgeSnapshotRepository(FakeEngine(), expected_database=DATABASE,
                                                   allow_disposable_test=True)
    calls: list[str] = []

    def execute(connection: Any, statement: str) -> Any:
        calls.append(statement)
        return SimpleNamespace(scalar_one=lambda: "existing_user_database")

    monkeypatch.setattr(repo, "_execute", execute)
    with pytest.raises(ValueError, match="connected database"):
        repo._guard_database(object())
    assert calls == ["SELECT current_database()"]


def test_explicit_snapshot_selection_rejects_before_connecting() -> None:
    repo = PostgresHumanKnowledgeSnapshotRepository(FakeEngine(), expected_database=DATABASE,
                                                   allow_disposable_test=True)
    with pytest.raises(ValueError, match="matching snapshot"):
        repo.read_snapshot("latest", content_sha256="0" * 64, root=ROOT)


def test_url_requires_permission_before_optional_library_import() -> None:
    with pytest.raises(ValueError, match="authorization"):
        PostgresHumanKnowledgeSnapshotRepository.from_url("postgresql+psycopg://localhost/production",
                                                        expected_database=DATABASE)
