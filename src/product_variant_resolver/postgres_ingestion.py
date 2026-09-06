from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from .catalog import CatalogProduct, load_catalog
from .identity import fingerprint, normalize_text
from .ingestion import ingest_catalog


INGESTION_VERSION = "postgres-catalog-ingestion-v1"


def _sqlalchemy() -> Any:
    try:
        import sqlalchemy as sa
    except ImportError as error:
        raise RuntimeError(
            "PostgreSQL ingestion requires the 'postgres' project extra"
        ) from error
    return sa


def _timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError("provenance retrieved_at must be an ISO-8601 timestamp")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class PostgresCatalogRepository:
    """SQLAlchemy-backed catalog repository with one transaction per catalog import."""

    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self._connection: Any | None = None
        self._transaction: Any | None = None
        self._seen_uuids: set[Any] = set()

    @classmethod
    def from_url(cls, database_url: str) -> "PostgresCatalogRepository":
        sa = _sqlalchemy()
        return cls(sa.create_engine(database_url, pool_pre_ping=True))

    def begin(self) -> None:
        if self._connection is not None:
            raise RuntimeError("transaction already active")
        self._connection = self.engine.connect()
        self._transaction = self._connection.begin()
        self._seen_uuids.clear()

    def _execute(self, statement: str, parameters: dict[str, Any] | None = None) -> Any:
        if self._connection is None:
            raise RuntimeError("no transaction")
        return self._connection.execute(_sqlalchemy().text(statement), parameters or {})

    def upsert(self, product: CatalogProduct) -> None:
        product_values = {
            "canonical_uuid": product.canonical_uuid,
            "canonical_id": product.canonical_id,
            "natural_key_fingerprint": fingerprint(product.product.model_dump()),
            **product.product.model_dump(),
        }
        conflict = self._execute(
            "SELECT canonical_uuid, canonical_id, natural_key_fingerprint "
            "FROM product_variant "
            "WHERE canonical_uuid = :canonical_uuid "
            "OR canonical_id = :canonical_id "
            "OR natural_key_fingerprint = :natural_key_fingerprint "
            "FOR UPDATE",
            product_values,
        ).mappings().all()
        for row in conflict:
            if row["canonical_uuid"] != product.canonical_uuid:
                raise ValueError(
                    "catalog identity collision for canonical_id or natural-key fingerprint"
                )
            if row["canonical_id"] != product.canonical_id:
                raise ValueError("immutable canonical_id changed")

        existing = self._execute(
            "SELECT canonical_uuid, canonical_id, natural_key_fingerprint, brand, casting, "
            "release_year, series, color, collector_number, series_position, rarity_tier, edition "
            "FROM product_variant WHERE canonical_uuid = :canonical_uuid",
            product_values,
        ).mappings().first()
        comparable_fields = tuple(product_values)
        changed = existing is None or any(
            existing[field] != product_values[field] for field in comparable_fields
        )
        if existing is None:
            self._execute(
                "INSERT INTO product_variant "
                "(canonical_uuid, canonical_id, natural_key_fingerprint, brand, casting, "
                "release_year, series, color, collector_number, series_position, rarity_tier, "
                "edition) VALUES (:canonical_uuid, :canonical_id, :natural_key_fingerprint, "
                ":brand, :casting, "
                ":release_year, :series, :color, :collector_number, :series_position, "
                ":rarity_tier, :edition)",
                product_values,
            )
        elif changed:
            self._execute(
                "UPDATE product_variant SET natural_key_fingerprint=:natural_key_fingerprint, "
                "brand=:brand, casting=:casting, release_year=:release_year, series=:series, "
                "color=:color, collector_number=:collector_number, "
                "series_position=:series_position, rarity_tier=:rarity_tier, edition=:edition, "
                "updated_at=now() WHERE canonical_uuid=:canonical_uuid",
                product_values,
            )

        self._sync_aliases(product)
        self._sync_identifiers(product)
        self._sync_provenance(product)
        self._sync_search_document(product)
        self._seen_uuids.add(product.canonical_uuid)

    def _sync_aliases(self, product: CatalogProduct) -> None:
        records = product.alias_records or tuple(
            {
                "alias_text": value,
                "alias_type": "catalog_alias",
                "source_id": f"catalog://{product.canonical_id}",
            }
            for value in product.aliases
        )
        desired: dict[str, dict[str, Any]] = {}
        for record in records:
            normalized = normalize_text(record["alias_text"])
            if not normalized:
                raise ValueError("catalog alias normalizes to an empty string")
            if normalized in desired:
                raise ValueError("duplicate normalized alias within one product")
            desired[normalized] = {
                "canonical_uuid": product.canonical_uuid,
                "alias_text": record["alias_text"],
                "normalized_alias": normalized,
                "alias_type": record["alias_type"],
                "source_id": record["source_id"],
            }
        existing = {
            row["normalized_alias"]: row
            for row in self._execute(
                "SELECT id, alias_text, normalized_alias, alias_type, source_id "
                "FROM product_alias WHERE canonical_uuid=:canonical_uuid FOR UPDATE",
                {"canonical_uuid": product.canonical_uuid},
            ).mappings()
        }
        for normalized, values in desired.items():
            row = existing.get(normalized)
            if row is None:
                self._execute(
                    "INSERT INTO product_alias "
                    "(canonical_uuid, alias_text, normalized_alias, alias_type, source_id) "
                    "VALUES (:canonical_uuid, :alias_text, :normalized_alias, :alias_type, "
                    ":source_id)",
                    values,
                )
            elif any(
                row[field] != values[field]
                for field in ("alias_text", "alias_type", "source_id")
            ):
                self._execute(
                    "UPDATE product_alias SET alias_text=:alias_text, alias_type=:alias_type, "
                    "source_id=:source_id WHERE id=:id",
                    {**values, "id": row["id"]},
                )
        for normalized, row in existing.items():
            if normalized not in desired:
                self._execute("DELETE FROM product_alias WHERE id=:id", {"id": row["id"]})

    def _sync_identifiers(self, product: CatalogProduct) -> None:
        records = product.identifier_records or tuple(
            {
                "identifier_type": "catalog_identifier",
                "identifier_value": value,
                "source_id": f"catalog://{product.canonical_id}",
            }
            for value in product.identifiers
        )
        desired: dict[tuple[str, str], dict[str, Any]] = {}
        for record in records:
            normalized = normalize_text(record["identifier_value"])
            key = (record["identifier_type"], normalized)
            if not normalized:
                raise ValueError("catalog identifier normalizes to an empty string")
            if key in desired:
                raise ValueError("duplicate normalized identifier within one product")
            desired[key] = {
                "canonical_uuid": product.canonical_uuid,
                "identifier_type": record["identifier_type"],
                "identifier_value": record["identifier_value"],
                "normalized_value": normalized,
                "source_id": record["source_id"],
            }
        existing = {
            (row["identifier_type"], row["normalized_value"]): row
            for row in self._execute(
                "SELECT id, canonical_uuid, identifier_type, identifier_value, normalized_value, "
                "source_id FROM identifier WHERE canonical_uuid=:canonical_uuid FOR UPDATE",
                {"canonical_uuid": product.canonical_uuid},
            ).mappings()
        }
        for key, values in desired.items():
            owner = self._execute(
                "SELECT id, canonical_uuid, identifier_value, source_id FROM identifier "
                "WHERE identifier_type=:identifier_type AND normalized_value=:normalized_value "
                "FOR UPDATE",
                values,
            ).mappings().first()
            if owner is not None and owner["canonical_uuid"] != product.canonical_uuid:
                raise ValueError("identifier already belongs to a different canonical product")
            if owner is None:
                self._execute(
                    "INSERT INTO identifier "
                    "(canonical_uuid, identifier_type, identifier_value, normalized_value, "
                    "source_id) "
                    "VALUES (:canonical_uuid, :identifier_type, :identifier_value, "
                    ":normalized_value, :source_id)",
                    values,
                )
            elif any(owner[field] != values[field] for field in ("identifier_value", "source_id")):
                self._execute(
                    "UPDATE identifier SET identifier_value=:identifier_value, "
                    "source_id=:source_id "
                    "WHERE id=:id",
                    {**values, "id": owner["id"]},
                )
        for key, row in existing.items():
            if key not in desired:
                self._execute("DELETE FROM identifier WHERE id=:id", {"id": row["id"]})

    def _sync_provenance(self, product: CatalogProduct) -> None:
        fields = (
            "field_name", "value_snapshot", "source_name", "source_reference",
            "retrieved_at", "license_note", "confidence_note",
        )
        desired = [
            {
                "canonical_uuid": product.canonical_uuid,
                "field_name": record.get("field_name"),
                "value_snapshot": record.get("value_snapshot"),
                "source_name": record["source_name"],
                "source_reference": record["source_reference"],
                "retrieved_at": _timestamp(record["retrieved_at"]),
                "license_note": record["license_note"],
                "confidence_note": record["confidence_note"],
            }
            for record in product.provenance
        ]
        existing = self._execute(
            "SELECT field_name, value_snapshot, source_name, source_reference, retrieved_at, "
            "license_note, confidence_note FROM provenance_record "
            "WHERE canonical_uuid=:canonical_uuid ORDER BY id FOR UPDATE",
            {"canonical_uuid": product.canonical_uuid},
        ).mappings().all()
        existing_values = [tuple(row[field] for field in fields) for row in existing]
        desired_values = [tuple(row[field] for field in fields) for row in desired]
        if existing_values == desired_values:
            return
        self._execute(
            "DELETE FROM provenance_record WHERE canonical_uuid=:canonical_uuid",
            {"canonical_uuid": product.canonical_uuid},
        )
        for values in desired:
            self._execute(
                "INSERT INTO provenance_record "
                "(canonical_uuid, field_name, value_snapshot, source_name, source_reference, "
                "retrieved_at, license_note, confidence_note) VALUES "
                "(:canonical_uuid, :field_name, :value_snapshot, :source_name, :source_reference, "
                ":retrieved_at, :license_note, :confidence_note)",
                values,
            )

    def _sync_search_document(self, product: CatalogProduct) -> None:
        values = {
            "canonical_uuid": product.canonical_uuid,
            "search_text": product.searchable_text,
        }
        existing = self._execute(
            "SELECT search_text FROM product_search "
            "WHERE canonical_uuid=:canonical_uuid FOR UPDATE",
            values,
        ).scalar_one_or_none()
        if existing is None:
            self._execute(
                "INSERT INTO product_search (canonical_uuid, search_text, search_document) "
                "VALUES (:canonical_uuid, :search_text, to_tsvector('simple', :search_text))",
                values,
            )
        elif existing != product.searchable_text:
            self._execute(
                "UPDATE product_search SET search_text=:search_text, "
                "search_document=to_tsvector('simple', :search_text) "
                "WHERE canonical_uuid=:canonical_uuid",
                values,
            )

    def set_version(self, version: str, checksum: str) -> None:
        stored_uuids = {
            row[0]
            for row in self._execute("SELECT canonical_uuid FROM product_variant")
        }
        if stored_uuids != self._seen_uuids:
            raise ValueError(
                "database catalog differs from incoming full snapshot; "
                "automatic product deletion is disabled"
            )
        values = {
            "index_name": "canonical_catalog",
            "catalog_version": version,
            "artifact_version": INGESTION_VERSION,
            "checksum": checksum,
        }
        existing = self._execute(
            "SELECT catalog_version, artifact_version, checksum FROM index_metadata "
            "WHERE index_name=:index_name FOR UPDATE",
            values,
        ).mappings().first()
        metadata_fields = ("catalog_version", "artifact_version", "checksum")
        expected = tuple(values[field] for field in metadata_fields)
        if existing is None:
            self._execute(
                "INSERT INTO index_metadata "
                "(index_name, catalog_version, artifact_version, checksum) "
                "VALUES (:index_name, :catalog_version, :artifact_version, :checksum)",
                values,
            )
        elif tuple(existing[field] for field in metadata_fields) != expected:
            self._execute(
                "UPDATE index_metadata SET catalog_version=:catalog_version, "
                "artifact_version=:artifact_version, checksum=:checksum, updated_at=now() "
                "WHERE index_name=:index_name",
                values,
            )

    def commit(self) -> None:
        if self._transaction is None or self._connection is None:
            raise RuntimeError("no transaction")
        try:
            self._transaction.commit()
        finally:
            self._close()

    def rollback(self) -> None:
        if self._transaction is not None:
            try:
                self._transaction.rollback()
            finally:
                self._close()

    def _close(self) -> None:
        if self._connection is not None:
            self._connection.close()
        self._transaction = None
        self._connection = None


def ingest_file(catalog_path: Path, database_url: str) -> dict[str, Any]:
    catalog = load_catalog(catalog_path)
    repository = PostgresCatalogRepository.from_url(database_url)
    try:
        ingest_catalog(catalog, repository)
    finally:
        repository.engine.dispose()
    return {
        "status": "complete",
        "catalog_version": catalog.version,
        "product_count": len(catalog.products),
        "ingestion_version": INGESTION_VERSION,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a canonical catalog into PostgreSQL")
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(os.getenv("PVR_CATALOG_PATH", "data/catalog.json")),
    )
    parser.add_argument("--database-url", default=os.getenv("PVR_DATABASE_URL"))
    arguments = parser.parse_args()
    if not arguments.database_url:
        parser.error("--database-url or PVR_DATABASE_URL is required")
    result = ingest_file(arguments.catalog, arguments.database_url)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
