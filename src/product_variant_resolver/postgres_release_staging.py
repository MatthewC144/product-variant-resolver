"""Transactional PostgreSQL persistence for review-only release staging snapshots."""

from __future__ import annotations

import argparse
import importlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .release_staging import canonical_bytes, check_bundle, validate_snapshot


def _sqlalchemy() -> Any:
    try:
        return importlib.import_module("sqlalchemy")
    except ImportError as error:
        raise RuntimeError(
            "release staging PostgreSQL import requires the 'postgres' extra"
        ) from error


def _timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("collected_at must include timezone")
    return parsed


def _timestamp_text(value: Any) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("stored collected_at is not timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class PostgresReleaseStagingRepository:
    """Insert-only immutable batches isolated from canonical and human-knowledge tables."""

    def __init__(self, engine: Any) -> None:
        if engine.dialect.name != "postgresql":
            raise ValueError("PostgreSQL is required")
        self.engine = engine

    @classmethod
    def from_url(cls, database_url: str) -> PostgresReleaseStagingRepository:
        sa = _sqlalchemy()
        url = sa.engine.make_url(database_url)
        if url.drivername != "postgresql+psycopg" or not url.database:
            raise ValueError("an explicit postgresql+psycopg database URL is required")
        return cls(sa.create_engine(url, poolclass=sa.pool.NullPool))

    def _execute(
        self, connection: Any, statement: str, parameters: dict[str, Any] | None = None
    ) -> Any:
        return connection.execute(_sqlalchemy().text(statement), parameters or {})

    def _read_snapshot(self, connection: Any, batch_id: str) -> dict[str, Any] | None:
        batch = (
            self._execute(
                connection,
                "SELECT batch_id, schema_version, import_version, content_sha256, status, "
                "source_rights_state, files, counts FROM public.release_source_batch "
                "WHERE batch_id = :batch_id",
                {"batch_id": batch_id},
            )
            .mappings()
            .first()
        )
        if batch is None:
            return None
        rows = (
            self._execute(
                connection,
                "SELECT source_record_id, ordinal, release_year, brand, toy_number, "
                "collector_number, source_model_label, casting_name, variant_note, series, "
                "series_position, color, source_page_title, source_page_url, source_table, "
                "source_row, parse_status, parse_error, collected_at, raw_fields, input_filename, "
                "input_sha256, review_status, usage, canonical_uuid "
                "FROM public.release_source_record WHERE batch_id = :batch_id ORDER BY ordinal",
                {"batch_id": batch_id},
            )
            .mappings()
            .all()
        )
        records = []
        for row in rows:
            records.append(
                {
                    "source_record_id": row["source_record_id"],
                    "release_year": row["release_year"],
                    "brand": row["brand"],
                    "toy_number": row["toy_number"],
                    "collector_number": row["collector_number"],
                    "source_model_label": row["source_model_label"],
                    "casting_name": row["casting_name"],
                    "variant_note": row["variant_note"],
                    "series": row["series"],
                    "series_position": row["series_position"],
                    "color": row["color"],
                    "source_page_title": row["source_page_title"],
                    "source_page_url": row["source_page_url"],
                    "source_table": row["source_table"],
                    "source_row": row["source_row"],
                    "parse_status": row["parse_status"],
                    "parse_error": row["parse_error"],
                    "collected_at": _timestamp_text(row["collected_at"]),
                    "raw_fields": row["raw_fields"],
                    "input_filename": row["input_filename"],
                    "input_sha256": row["input_sha256"],
                    "review_status": row["review_status"],
                    "usage": row["usage"],
                    "canonical_uuid": str(row["canonical_uuid"]) if row["canonical_uuid"] else None,
                }
            )
        return {
            "schema_version": batch["schema_version"],
            "import_version": batch["import_version"],
            "status": batch["status"],
            "source_rights_state": batch["source_rights_state"],
            "files": batch["files"],
            "counts": batch["counts"],
            "records": records,
            "content_sha256": batch["content_sha256"],
            "batch_id": batch["batch_id"],
        }

    def _insert_record(
        self, connection: Any, batch_id: str, ordinal: int, record: dict[str, Any]
    ) -> None:
        parameters = {
            **record,
            "batch_id": batch_id,
            "ordinal": ordinal,
            "collected_at": _timestamp(record["collected_at"]),
            "raw_fields": json.dumps(record["raw_fields"], ensure_ascii=False, allow_nan=False),
        }
        self._execute(
            connection,
            "INSERT INTO public.release_source_record (batch_id, source_record_id, ordinal, "
            "release_year, brand, toy_number, collector_number, source_model_label, casting_name, "
            "variant_note, series, series_position, color, source_page_title, source_page_url, "
            "source_table, source_row, parse_status, parse_error, collected_at, raw_fields, "
            "input_filename, input_sha256, review_status, usage, canonical_uuid) VALUES "
            "(:batch_id, :source_record_id, :ordinal, :release_year, :brand, :toy_number, "
            ":collector_number, :source_model_label, :casting_name, :variant_note, :series, "
            ":series_position, :color, :source_page_title, :source_page_url, :source_table, "
            ":source_row, :parse_status, :parse_error, :collected_at, CAST(:raw_fields AS jsonb), "
            ":input_filename, :input_sha256, :review_status, :usage, CAST(:canonical_uuid AS uuid))",
            parameters,
        )

    def import_snapshot(self, snapshot: dict[str, Any], *, root: Path) -> str:
        validate_snapshot(snapshot, root)
        with self.engine.begin() as connection:
            self._execute(
                connection,
                "LOCK TABLE public.release_source_batch, public.release_source_record "
                "IN SHARE ROW EXCLUSIVE MODE",
            )
            stored = self._read_snapshot(connection, snapshot["batch_id"])
            if stored is not None:
                if stored["content_sha256"] != snapshot["content_sha256"]:
                    raise ValueError("release staging batch ID collision")
                validate_snapshot(stored, root)
                if canonical_bytes(stored) != canonical_bytes(snapshot):
                    raise ValueError(
                        "stored release staging batch differs; overwrite is prohibited"
                    )
                return "unchanged"
            header = {key: value for key, value in snapshot.items() if key != "records"}
            self._execute(
                connection,
                "INSERT INTO public.release_source_batch (batch_id, schema_version, "
                "import_version, content_sha256, status, source_rights_state, files, counts) "
                "VALUES (:batch_id, :schema_version, :import_version, :content_sha256, :status, "
                ":source_rights_state, CAST(:files AS jsonb), CAST(:counts AS jsonb))",
                {
                    **header,
                    "files": json.dumps(header["files"], ensure_ascii=False, allow_nan=False),
                    "counts": json.dumps(header["counts"], ensure_ascii=False, allow_nan=False),
                },
            )
            for ordinal, record in enumerate(snapshot["records"]):
                self._insert_record(connection, snapshot["batch_id"], ordinal, record)
            stored = self._read_snapshot(connection, snapshot["batch_id"])
            if stored is None or canonical_bytes(stored) != canonical_bytes(snapshot):
                raise ValueError("release staging write/read parity failed; rolling back")
        return "inserted"


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a validated release staging bundle")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--bundle",
        type=Path,
        default=Path("data/external/hot-wheels-wiki/local-export-2023-2026"),
    )
    parser.add_argument("--database-url", default=os.getenv("PVR_RELEASE_STAGING_DATABASE_URL"))
    arguments = parser.parse_args()
    if not arguments.database_url:
        parser.error("--database-url or PVR_RELEASE_STAGING_DATABASE_URL is required")
    root = arguments.root.resolve()
    bundle = arguments.bundle if arguments.bundle.is_absolute() else root / arguments.bundle
    snapshot = check_bundle(bundle, root)
    repository = PostgresReleaseStagingRepository.from_url(arguments.database_url)
    try:
        status = repository.import_snapshot(snapshot, root=root)
    finally:
        repository.engine.dispose()
    print(
        json.dumps(
            {
                "status": status,
                "batch_id": snapshot["batch_id"],
                "staged_observations": snapshot["counts"]["staged_observations"],
                "canonical_products": 0,
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
