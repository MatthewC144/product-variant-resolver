#!/usr/bin/env python3
"""Real-SQL verifier for one explicitly disposable release-staging database."""

from __future__ import annotations

import json
import os
import platform
import re
import sys
from pathlib import Path
from typing import Any

import alembic
import psycopg
import sqlalchemy as sa
from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from product_variant_resolver.postgres_release_staging import (
    PostgresReleaseStagingRepository,
)
from product_variant_resolver.release_staging import (
    canonical_bytes,
    check_bundle,
)

PROTECTED_TABLES = (
    "product_variant",
    "product_alias",
    "identifier",
    "provenance_record",
    "index_metadata",
    "product_search",
    "product_embedding",
    "hk_snapshot",
    "hk_document",
)


def table_counts(connection: Any) -> dict[str, int]:
    return {
        table: int(connection.execute(sa.text(f"SELECT count(*) FROM public.{table}")).scalar_one())
        for table in PROTECTED_TABLES
    }


def verify() -> dict[str, Any]:
    if os.getenv("PVR_LRS_ALLOW_DISPOSABLE_DATABASE") != "1":
        raise RuntimeError("explicit disposable release-staging database authorization is required")
    database = os.environ["PVR_LRS_EXPECTED_DATABASE"]
    if not re.fullmatch(r"pvr_lrs_[0-9a-f]{12}", database):
        raise ValueError("expected database must be a new pvr_lrs_<12 hex> disposable database")
    url = os.environ["PVR_LRS_DATABASE_URL"]
    parsed_url = sa.engine.make_url(url)
    if parsed_url.drivername != "postgresql+psycopg" or parsed_url.database != database:
        raise ValueError("database URL must select the exact authorized disposable database")
    repository = PostgresReleaseStagingRepository.from_url(url)
    engine = repository.engine
    with engine.connect() as connection:
        if connection.execute(sa.text("SELECT current_database()")).scalar_one() != database:
            raise ValueError("server database differs from the authorized disposable database")
        existing_tables = connection.execute(
            sa.text(
                "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' "
                "AND table_type = 'BASE TABLE'"
            )
        ).scalar_one()
        if existing_tables != 0:
            raise ValueError("verifier requires a genuinely empty disposable database")
        server = connection.execute(sa.text("SELECT version()")).scalar_one()

    configuration = Config(str(ROOT / "alembic.ini"))
    configuration.set_main_option("script_location", str(ROOT / "migrations"))
    configuration.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    if os.getenv("PVR_DATABASE_URL"):
        raise RuntimeError("legacy database URL must not be present in this isolated verifier")
    command.upgrade(configuration, "0002")
    with engine.connect() as connection:
        protected_before = table_counts(connection)
    command.upgrade(configuration, "0003")
    with engine.connect() as connection:
        protected_after_upgrade = table_counts(connection)
    assert protected_after_upgrade == protected_before
    command.downgrade(configuration, "0002")
    with engine.connect() as connection:
        assert table_counts(connection) == protected_before
        assert connection.execute(
            sa.text(
                "SELECT to_regclass('public.release_source_batch'), "
                "to_regclass('public.release_source_record')"
            )
        ).one() == (None, None)
    command.upgrade(configuration, "0003")
    snapshot = check_bundle(ROOT / "data/external/hot-wheels-wiki/local-export-2023-2026", ROOT)

    class FailingRepository(PostgresReleaseStagingRepository):
        visible_records = 0

        def _insert_record(
            self, connection: Any, batch_id: str, ordinal: int, record: dict[str, Any]
        ) -> None:
            super()._insert_record(connection, batch_id, ordinal, record)
            if ordinal == 880:
                self.visible_records = int(
                    connection.execute(
                        sa.text("SELECT count(*) FROM public.release_source_record")
                    ).scalar_one()
                )
                super()._insert_record(connection, batch_id, ordinal, record)

    failing = FailingRepository(engine)
    try:
        failing.import_snapshot(snapshot, root=ROOT)
    except sa.exc.IntegrityError:
        pass
    else:
        raise AssertionError("SQL uniqueness fault did not abort the release staging import")
    with engine.connect() as connection:
        assert (
            connection.execute(
                sa.text("SELECT count(*) FROM public.release_source_batch")
            ).scalar_one()
            == 0
        )
        assert (
            connection.execute(
                sa.text("SELECT count(*) FROM public.release_source_record")
            ).scalar_one()
            == 0
        )
        assert table_counts(connection) == protected_before

    assert repository.import_snapshot(snapshot, root=ROOT) == "inserted"
    assert repository.import_snapshot(snapshot, root=ROOT) == "unchanged"
    with engine.connect() as connection:
        counts = {
            "batches": int(
                connection.execute(
                    sa.text("SELECT count(*) FROM public.release_source_batch")
                ).scalar_one()
            ),
            "staged_observations": int(
                connection.execute(
                    sa.text("SELECT count(*) FROM public.release_source_record")
                ).scalar_one()
            ),
            "unique_source_record_ids": int(
                connection.execute(
                    sa.text(
                        "SELECT count(DISTINCT source_record_id) FROM public.release_source_record"
                    )
                ).scalar_one()
            ),
            "unique_toy_numbers": int(
                connection.execute(
                    sa.text("SELECT count(DISTINCT toy_number) FROM public.release_source_record")
                ).scalar_one()
            ),
            "unique_casting_names": int(
                connection.execute(
                    sa.text("SELECT count(DISTINCT casting_name) FROM public.release_source_record")
                ).scalar_one()
            ),
            "unknown_colors": int(
                connection.execute(
                    sa.text("SELECT count(*) FROM public.release_source_record WHERE color IS NULL")
                ).scalar_one()
            ),
            "canonical_links": int(
                connection.execute(
                    sa.text(
                        "SELECT count(*) FROM public.release_source_record WHERE canonical_uuid IS NOT NULL"
                    )
                ).scalar_one()
            ),
        }
        restored = repository._read_snapshot(connection, snapshot["batch_id"])
        protected_after = table_counts(connection)
        revision = connection.execute(
            sa.text("SELECT version_num FROM public.alembic_version")
        ).scalar_one()
    assert counts == {
        "batches": 1,
        "staged_observations": 1763,
        "unique_source_record_ids": 1763,
        "unique_toy_numbers": 1763,
        "unique_casting_names": 678,
        "unknown_colors": 1763,
        "canonical_links": 0,
    }
    assert restored is not None and canonical_bytes(restored) == canonical_bytes(snapshot)
    assert protected_after == protected_before
    engine.dispose()
    return {
        "verdict": "PASS",
        "database": database,
        "postgresql_server": server,
        "python": platform.python_version(),
        "dependency_versions": {
            "sqlalchemy": sa.__version__,
            "alembic": alembic.__version__,
            "psycopg": psycopg.__version__,
        },
        "migration_revision": revision,
        "batch_id": snapshot["batch_id"],
        "content_sha256": snapshot["content_sha256"],
        "counts": counts,
        "protected_table_counts_before": protected_before,
        "protected_table_counts_after": protected_after,
        "gates": {
            "additive_upgrade_and_downgrade_preserve_protected_tables": True,
            "genuine_mid_import_sql_fault_full_rollback": True,
            "records_visible_before_fault": failing.visible_records,
            "first_import_inserted": True,
            "identical_repeat_verified_noop": True,
            "exact_snapshot_readback": True,
            "all_colors_null": True,
            "no_canonical_links": True,
        },
    }


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False, sort_keys=True, indent=2))
