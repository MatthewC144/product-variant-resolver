"""T49.2 isolated-test persistence, not a production/runtime retrieval adapter."""
from __future__ import annotations

import copy
import importlib
import json
import re
from pathlib import Path
from typing import Any

from .human_knowledge_snapshot import canonical_bytes, validate_plan

STORAGE_VERSION = "human-knowledge-postgres-storage-v1"
PERSISTENCE_NAMESPACE = "human-knowledge-isolated-storage-test-v1"


def _sqlalchemy() -> Any:
    try:
        sa = importlib.import_module("sqlalchemy")
    except ImportError as error:
        raise RuntimeError("human snapshot storage requires the 'postgres' extra") from error
    return sa


class PostgresHumanKnowledgeSnapshotRepository:
    """Insert-only complete snapshots; all writes confined to explicitly disposable test DBs.

    Application immutability is enforced through exact reads and no update/delete/upsert path.
    Database uniqueness/FKs/checks do not prevent a privileged external SQL writer from corruption;
    the reader/importer fail closed on such corruption rather than silently repairing it.
    """

    def __init__(self, engine: Any, *, expected_database: str,
                 allow_disposable_test: bool = False) -> None:
        if allow_disposable_test is not True:
            raise ValueError("explicit disposable-test authorization is required")
        if not re.fullmatch(r"pvr_t49_2_[0-9a-f]{12}", expected_database):
            raise ValueError("expected_database must identify a new T49.2 disposable database")
        if engine.dialect.name != "postgresql":
            raise ValueError("PostgreSQL is required; SQLite is not equivalent evidence")
        self.engine = engine
        self.expected_database = expected_database

    @classmethod
    def from_url(cls, database_url: str, *, expected_database: str,
                 allow_disposable_test: bool = False) -> PostgresHumanKnowledgeSnapshotRepository:
        if allow_disposable_test is not True:
            raise ValueError("explicit disposable-test authorization is required")
        sa = _sqlalchemy()
        url = sa.engine.make_url(database_url)
        if (url.drivername != "postgresql+psycopg" or url.database != expected_database
                or not re.fullmatch(r"pvr_t49_2_[0-9a-f]{12}", expected_database)):
            raise ValueError("explicit matching PostgreSQL disposable-test URL required")
        engine = sa.create_engine(url, poolclass=sa.pool.NullPool)
        return cls(engine, expected_database=expected_database, allow_disposable_test=True)

    def _execute(self, connection: Any, statement: str,
                 parameters: dict[str, Any] | None = None) -> Any:
        return connection.execute(_sqlalchemy().text(statement), parameters or {})

    def _guard_database(self, connection: Any) -> None:
        actual = self._execute(connection, "SELECT current_database()").scalar_one()
        if actual != self.expected_database:
            raise ValueError("connected database differs from authorized disposable database")
        self._execute(connection, "SET LOCAL lock_timeout = '5s'")
        self._execute(connection, "SET LOCAL statement_timeout = '30s'")

    def _read_plan(self, connection: Any, snapshot_id: str) -> dict[str, Any] | None:
        row = self._execute(connection,
            "SELECT snapshot_id, storage_version, persistence_namespace, content_sha256, "
            "document_count, provisional_variant_count, review_family_count, plan_header "
            "FROM public.hk_snapshot WHERE snapshot_id = :snapshot_id",
            {"snapshot_id": snapshot_id}).mappings().first()
        if row is None:
            return None
        if (row["storage_version"] != STORAGE_VERSION
                or row["persistence_namespace"] != PERSISTENCE_NAMESPACE
                or (row["document_count"], row["provisional_variant_count"],
                    row["review_family_count"]) != (142, 100, 42)):
            raise ValueError("stored snapshot metadata differs from storage contract")
        header = row["plan_header"]
        if not isinstance(header, dict) or "documents" in header:
            raise ValueError("stored snapshot header is invalid")
        if (header.get("snapshot_id") != row["snapshot_id"]
                or header.get("content_sha256") != row["content_sha256"]):
            raise ValueError("stored snapshot identity/checksum collision")
        rows = self._execute(connection,
            "SELECT knowledge_uuid, knowledge_id, knowledge_type, ordinal, payload, "
            "payload_sha256, origin FROM public.hk_document WHERE snapshot_id = :snapshot_id "
            "ORDER BY ordinal", {"snapshot_id": snapshot_id}).mappings().all()
        if len(rows) != 142 or [item["ordinal"] for item in rows] != list(range(142)):
            raise ValueError("stored snapshot is partial or unordered")
        documents = [{"knowledge_uuid": str(item["knowledge_uuid"]),
                      "knowledge_id": item["knowledge_id"], "knowledge_type": item["knowledge_type"],
                      "payload": item["payload"], "payload_sha256": item["payload_sha256"],
                      "origin": item["origin"]} for item in rows]
        return {**header, "documents": documents}

    def _insert_document(self, connection: Any, snapshot_id: str, ordinal: int,
                         entry: dict[str, Any]) -> None:
        parameters = {**entry, "snapshot_id": snapshot_id, "ordinal": ordinal,
                      "payload": json.dumps(entry["payload"], ensure_ascii=False, allow_nan=False),
                      "origin": json.dumps(entry["origin"], ensure_ascii=False, allow_nan=False)}
        self._execute(connection,
            "INSERT INTO public.hk_document (snapshot_id, knowledge_uuid, knowledge_id, "
            "knowledge_type, ordinal, payload, payload_sha256, origin) VALUES "
            "(:snapshot_id, CAST(:knowledge_uuid AS uuid), :knowledge_id, :knowledge_type, "
            ":ordinal, CAST(:payload AS jsonb), :payload_sha256, CAST(:origin AS jsonb))", parameters)

    def import_snapshot(self, plan: dict[str, Any], *, root: Path) -> str:
        # Defensive copy + source validation before opening any connection/transaction.
        expected = copy.deepcopy(plan)
        validate_plan(expected, root)
        with self.engine.begin() as connection:
            self._guard_database(connection)
            # Tiny fixed142-doc lane: serialize imports/external table writers, not canonical reads.
            # This also closes the absent-row race for simultaneous first imports without upserts.
            self._execute(connection,
                "LOCK TABLE public.hk_snapshot, public.hk_document IN SHARE ROW EXCLUSIVE MODE")
            stored = self._read_plan(connection, expected["snapshot_id"])
            if stored is not None:
                validate_plan(stored, root)
                if canonical_bytes(stored) != canonical_bytes(expected):
                    raise ValueError("snapshot collision; overwriting is prohibited")
                return "unchanged"
            header = {key: value for key, value in expected.items() if key != "documents"}
            self._execute(connection,
                "INSERT INTO public.hk_snapshot (snapshot_id, storage_version, "
                "persistence_namespace, content_sha256, document_count, provisional_variant_count, "
                "review_family_count, plan_header) VALUES (:snapshot_id, :storage_version, "
                ":persistence_namespace, :content_sha256, 142, 100, 42, CAST(:plan_header AS jsonb))",
                {"snapshot_id": expected["snapshot_id"], "storage_version": STORAGE_VERSION,
                 "persistence_namespace": PERSISTENCE_NAMESPACE,
                 "content_sha256": expected["content_sha256"],
                 "plan_header": json.dumps(header, ensure_ascii=False, allow_nan=False)})
            for ordinal, entry in enumerate(expected["documents"]):
                self._insert_document(connection, expected["snapshot_id"], ordinal, entry)
            stored = self._read_plan(connection, expected["snapshot_id"])
            if stored is None or canonical_bytes(stored) != canonical_bytes(expected):
                raise ValueError("snapshot write/read parity failed; rolling back")
        return "inserted"

    def read_snapshot(self, snapshot_id: str, *, content_sha256: str, root: Path) -> dict[str, Any]:
        # Snapshot selection is explicit ID+hash, never latest/active/fallback selection.
        if (not re.fullmatch(r"[0-9a-f]{64}", content_sha256)
                or snapshot_id != "human-knowledge-plan-v1-" + content_sha256):
            raise ValueError("explicit matching snapshot ID and content checksum required")
        with self.engine.connect().execution_options(isolation_level="REPEATABLE READ") as connection:
            with connection.begin():
                self._execute(connection, "SET TRANSACTION READ ONLY")
                self._guard_database(connection)
                stored = self._read_plan(connection, snapshot_id)
                if stored is None:
                    raise ValueError("selected snapshot is missing")
                validate_plan(stored, root)
                return stored
