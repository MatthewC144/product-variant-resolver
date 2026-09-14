#!/usr/bin/env python3
"""Real SQL tests confined to a newly created, explicitly authorized T49.2 database."""
from __future__ import annotations

import copy
import json
import os
import platform
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from typing import Any

import alembic
import psycopg
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from product_variant_resolver.catalog import load_catalog  # noqa: E402
from product_variant_resolver.human_knowledge_persistence import (  # noqa: E402
    PostgresHumanKnowledgeSnapshotRepository,
)
from product_variant_resolver.human_knowledge_snapshot import (  # noqa: E402
    canonical_bytes,
    check_bundle,
    decode_document,
    digest,
)
from product_variant_resolver.ingestion import ingest_catalog  # noqa: E402
from product_variant_resolver.postgres_ingestion import PostgresCatalogRepository  # noqa: E402

CANONICAL_ORDER = {
    "product_variant": "canonical_uuid", "product_alias": "id", "identifier": "id",
    "provenance_record": "id", "index_metadata": "index_name",
    "product_search": "canonical_uuid", "product_embedding": "canonical_uuid",
}


def table_snapshot(engine: Any, orders: dict[str, str]) -> dict[str, Any]:
    with engine.connect() as connection:
        return {table: [[str(value) for value in row] for row in connection.execute(
            sa.text(f"SELECT * FROM public.{table} ORDER BY {order}")).all()]
            for table, order in orders.items()}


def human_snapshot(engine: Any) -> dict[str, Any]:
    return table_snapshot(engine, {"hk_snapshot": "snapshot_id",
        "hk_document": "snapshot_id, ordinal"})


def expect_rejected(action: Any) -> None:
    try:
        action()
    except ValueError:
        return
    raise AssertionError("invalid/colliding snapshot was accepted")


def verify() -> dict[str, Any]:
    if os.getenv("PVR_T49_2_ALLOW_DISPOSABLE_DATABASE") != "1":
        raise RuntimeError("explicit T49.2 disposable database authorization is required")
    database = os.environ["PVR_T49_2_EXPECTED_DATABASE"]
    url = os.environ["PVR_T49_2_DATABASE_URL"]  # no PVR_DATABASE_URL / .env / production fallback
    repo = PostgresHumanKnowledgeSnapshotRepository.from_url(url, expected_database=database,
        allow_disposable_test=True)
    engine = repo.engine
    with engine.connect() as connection:
        repo._guard_database(connection)
        if connection.execute(sa.text("SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'")).scalar_one() != 0:
            raise AssertionError("verifier requires a genuinely empty new database")
        server = connection.execute(sa.text("SELECT version()")).scalar_one()
    plan = check_bundle(ROOT / "reports/human-knowledge-snapshot-v1", ROOT)
    configuration = Config(str(ROOT / "alembic.ini"))
    configuration.set_main_option("script_location", str(ROOT / "migrations"))
    configuration.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    # Prevent old migration env from selecting a caller/production URL instead of this explicit URL.
    if os.getenv("PVR_DATABASE_URL"):
        raise RuntimeError("legacy database URL must not be present in the isolated runner")
    command.upgrade(configuration, "0001")
    ingest_catalog(load_catalog(ROOT / "data/catalog.json"), PostgresCatalogRepository(engine))
    canonical_before = table_snapshot(engine, CANONICAL_ORDER)
    assert len(canonical_before["product_variant"]) == 120
    command.upgrade(configuration, "0002")
    assert table_snapshot(engine, CANONICAL_ORDER) == canonical_before
    command.downgrade(configuration, "0001")
    assert table_snapshot(engine, CANONICAL_ORDER) == canonical_before
    with engine.connect() as connection:
        assert connection.execute(sa.text("SELECT to_regclass('public.hk_snapshot'), "
            "to_regclass('public.hk_document')")).one() == (None, None)
    command.upgrade(configuration, "0002")
    empty = human_snapshot(engine)
    assert empty == {"hk_snapshot": [], "hk_document": []}

    class FailingRepository(PostgresHumanKnowledgeSnapshotRepository):
        visible_documents = 0

        def _insert_document(self, connection: Any, snapshot_id: str, ordinal: int,
                             entry: dict[str, Any]) -> None:
            super()._insert_document(connection, snapshot_id, ordinal, entry)
            if ordinal == 70:
                self.visible_documents = connection.execute(sa.text(
                    "SELECT count(*) FROM public.hk_document")).scalar_one()
                # Genuine SQL unique violation after header and71docs are already written.
                super()._insert_document(connection, snapshot_id, ordinal, entry)

    failing = FailingRepository(engine, expected_database=database, allow_disposable_test=True)
    try:
        failing.import_snapshot(plan, root=ROOT)
    except sa.exc.IntegrityError:
        pass
    else:
        raise AssertionError("SQL uniqueness fault did not abort the import")
    assert failing.visible_documents == 71
    assert human_snapshot(engine) == empty
    assert table_snapshot(engine, CANONICAL_ORDER) == canonical_before
    barrier = Barrier(2)

    def concurrent_import() -> str:
        barrier.wait(timeout=5)
        return repo.import_snapshot(plan, root=ROOT)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(concurrent_import) for _ in range(2)]
        statuses = sorted(future.result(timeout=60) for future in futures)
    assert statuses == ["inserted", "unchanged"]
    first = human_snapshot(engine)
    assert len(first["hk_snapshot"]) == 1 and len(first["hk_document"]) == 142
    assert repo.import_snapshot(plan, root=ROOT) == "unchanged"
    assert human_snapshot(engine) == first  # includes imported_at, every UUID, ordinal, JSON field
    read = lambda: repo.read_snapshot(plan["snapshot_id"], content_sha256=plan["content_sha256"], root=ROOT)
    restored = read()
    assert canonical_bytes(restored) == canonical_bytes(plan)
    assert [decode_document(e) for e in restored["documents"]] == [
        decode_document(e) for e in plan["documents"]]
    expect_rejected(lambda: repo.read_snapshot(plan["snapshot_id"], content_sha256="0" * 64, root=ROOT))
    expect_rejected(lambda: repo.read_snapshot("human-knowledge-plan-v1-" + "0" * 64,
        content_sha256="0" * 64, root=ROOT))

    invalid_cases = {}
    for name in ("partial", "duplicate", "changed_payload", "held_family"):
        invalid = copy.deepcopy(plan)
        if name == "partial":
            invalid["documents"].pop()
        elif name == "duplicate":
            invalid["documents"][-1] = copy.deepcopy(invalid["documents"][0])
        elif name == "changed_payload":
            invalid["documents"][0]["payload"]["casting"] = "not the approved casting"
            invalid["documents"][0]["payload_sha256"] = digest(invalid["documents"][0]["payload"])
        else:
            invalid["documents"][-1]["knowledge_id"] = "fandom-family-089ff8645b5f2de7"
        expect_rejected(lambda: repo.import_snapshot(invalid, root=ROOT))
        assert human_snapshot(engine) == first
        invalid_cases[name] = True

    # Controlled privileged corruption ONLY in this new test DB: prove no repair/overwrite.
    header = {k: v for k, v in plan.items() if k != "documents"}
    corrupt_header = copy.deepcopy(header)
    corrupt_header["counts"]["postgresql_writes"] = False
    with engine.begin() as connection:
        connection.execute(sa.text("UPDATE public.hk_snapshot SET plan_header = CAST(:header AS jsonb) "
            "WHERE snapshot_id = :id"), {"header": json.dumps(corrupt_header), "id": plan["snapshot_id"]})
    corrupt = human_snapshot(engine)
    expect_rejected(lambda: repo.import_snapshot(plan, root=ROOT))
    expect_rejected(read)
    assert human_snapshot(engine) == corrupt
    with engine.begin() as connection:
        connection.execute(sa.text("UPDATE public.hk_snapshot SET plan_header = CAST(:header AS jsonb) "
            "WHERE snapshot_id = :id"), {"header": json.dumps(header), "id": plan["snapshot_id"]})
        connection.execute(sa.text("DELETE FROM public.hk_document WHERE snapshot_id = :id AND ordinal = 141"),
                           {"id": plan["snapshot_id"]})
    partial = human_snapshot(engine)
    expect_rejected(lambda: repo.import_snapshot(plan, root=ROOT))
    expect_rejected(read)
    assert human_snapshot(engine) == partial
    with engine.begin() as connection:
        repo._insert_document(connection, plan["snapshot_id"], 141, plan["documents"][141])
    assert human_snapshot(engine) == first
    assert canonical_bytes(read()) == canonical_bytes(plan)
    assert table_snapshot(engine, CANONICAL_ORDER) == canonical_before
    with engine.connect() as connection:
        types = dict(connection.execute(sa.text("SELECT knowledge_type, count(*) "
            "FROM public.hk_document GROUP BY knowledge_type")).all())
        assert types == {"provisional_variant": 100, "review_family": 42}
        assert connection.execute(sa.text("SELECT version_num FROM public.alembic_version")).scalar_one() == "0002"
    canonical_after = table_snapshot(engine, CANONICAL_ORDER)
    engine.dispose()
    return {"verdict": "PASS", "database": database, "postgresql_server": server,
        "python": platform.python_version(), "platform": platform.platform(), "uid": os.geteuid(),
        "dependency_versions": {"sqlalchemy": sa.__version__, "alembic": alembic.__version__,
                                "psycopg": psycopg.__version__},
        "snapshot_id": plan["snapshot_id"], "content_sha256": plan["content_sha256"],
        "counts": {"snapshots": 1, "documents": 142, **types},
        "canonical_fixture_counts": {k: len(v) for k, v in canonical_before.items()},
        "canonical_before_sha256": digest(canonical_before),
        "canonical_after_sha256": digest(canonical_after),
        "gates": {"additive_upgrade_preserves_canonical": True,
            "new_tables_downgrade_upgrade_preserves_canonical": True,
            "sql_fault_visible_documents_before_abort": failing.visible_documents,
            "genuine_sql_fault_full_rollback": True, "exact_typed_and_raw_roundtrip": True,
            "simultaneous_first_import_one_insert_one_verified_noop": True,
            "repeat_all_rows_and_import_timestamp_identical": True,
            "invalid_input_no_overwrite": invalid_cases,
            "stored_corruption_read_and_import_fail_closed": True,
            "stored_partial_read_and_import_fail_closed": True,
            "all_seven_canonical_tables_unchanged": True,
            "explicit_id_hash_missing_selection_rejected": True},
        "scope": "isolated SQL correctness only; no production DB, retrieval, crash-durability or real3k claim"}


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, sort_keys=True, indent=2))
