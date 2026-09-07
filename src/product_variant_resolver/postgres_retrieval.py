from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from .catalog import Catalog, catalog_checksum
from .embedding_artifacts import (
    VersionedEmbedding,
    build_embedding_rows,
    embedding_artifact_version,
    embedding_index_checksum,
)


def _sqlalchemy() -> Any:
    try:
        import sqlalchemy as sa
    except ImportError as error:
        raise RuntimeError(
            "PostgreSQL retrieval requires the 'postgres' project extra"
        ) from error
    return sa


@dataclass(frozen=True, slots=True)
class PostgresCatalogState:
    database_version: str
    catalog_version: str
    catalog_checksum: str
    product_count: int
    search_document_count: int


@dataclass(frozen=True, slots=True)
class PostgresDenseIndexState:
    catalog_version: str
    embedding_version: str
    index_checksum: str
    embedding_count: int


class SQLAlchemyPostgresRetrieverAdapter:
    """Execute fixed retrieval statements and validate the installed catalog snapshot."""

    def __init__(self, database_url: str) -> None:
        sa = _sqlalchemy()
        self.sqlalchemy = sa
        self.engine = sa.create_engine(database_url, pool_pre_ping=True)

    def verify_catalog(self, catalog: Catalog) -> PostgresCatalogState:
        sa = _sqlalchemy()
        with self.engine.connect() as connection:
            row = connection.execute(
                sa.text(
                    "SELECT current_setting('server_version') AS database_version, "
                    "metadata.catalog_version, metadata.checksum, "
                    "(SELECT count(*) FROM product_variant) AS product_count, "
                    "(SELECT count(*) FROM product_search) AS search_document_count "
                    "FROM index_metadata AS metadata "
                    "WHERE metadata.index_name=:index_name"
                ),
                {"index_name": "canonical_catalog"},
            ).mappings().first()
        if row is None:
            raise RuntimeError("canonical catalog metadata is missing")
        expected_checksum = catalog_checksum(catalog)
        expected_count = len(catalog.products)
        if row["catalog_version"] != catalog.version:
            raise RuntimeError("PostgreSQL catalog version does not match the loaded catalog")
        if row["checksum"] != expected_checksum:
            raise RuntimeError("PostgreSQL catalog checksum does not match the loaded catalog")
        if row["product_count"] != expected_count:
            raise RuntimeError("PostgreSQL product count does not match the loaded catalog")
        if row["search_document_count"] != expected_count:
            raise RuntimeError("PostgreSQL search-document count is incomplete")
        return PostgresCatalogState(
            database_version=f"postgresql-{row['database_version']}",
            catalog_version=row["catalog_version"],
            catalog_checksum=row["checksum"],
            product_count=row["product_count"],
            search_document_count=row["search_document_count"],
        )

    def verify_dense_index(
        self, catalog: Catalog, model: VersionedEmbedding
    ) -> PostgresDenseIndexState:
        expected_rows = build_embedding_rows(catalog, model)
        expected_version = embedding_artifact_version(model)
        expected_checksum = embedding_index_checksum(expected_rows)
        sa = self.sqlalchemy
        with self.engine.connect() as connection:
            metadata = connection.execute(
                sa.text(
                    "SELECT catalog_version, artifact_version, checksum "
                    "FROM index_metadata WHERE index_name=:index_name"
                ),
                {"index_name": "canonical_dense"},
            ).mappings().first()
            stored_rows = connection.execute(
                sa.text(
                    "SELECT canonical_uuid, embedding_version, checksum "
                    "FROM product_embedding ORDER BY canonical_uuid"
                )
            ).mappings().all()
        if metadata is None:
            raise RuntimeError("canonical dense-index metadata is missing")
        if metadata["catalog_version"] != catalog.version:
            raise RuntimeError("PostgreSQL dense catalog version does not match")
        if metadata["artifact_version"] != expected_version:
            raise RuntimeError("PostgreSQL embedding version does not match")
        if metadata["checksum"] != expected_checksum:
            raise RuntimeError("PostgreSQL dense-index checksum does not match")
        stored = {
            row["canonical_uuid"]: (row["embedding_version"], row["checksum"])
            for row in stored_rows
        }
        expected = {
            row.canonical_uuid: (row.embedding_version, row.checksum)
            for row in expected_rows
        }
        if stored != expected:
            raise RuntimeError("PostgreSQL embedding rows are incomplete or stale")
        return PostgresDenseIndexState(
            catalog_version=metadata["catalog_version"],
            embedding_version=metadata["artifact_version"],
            index_checksum=metadata["checksum"],
            embedding_count=len(stored_rows),
        )

    def execute_ranked(
        self, statement: str, parameters: dict[str, object]
    ) -> list[tuple[UUID, float]]:
        sa = _sqlalchemy()
        with self.engine.connect() as connection:
            rows = connection.execute(sa.text(statement), parameters)
            return [(row[0], float(row[1])) for row in rows]

    def dispose(self) -> None:
        self.engine.dispose()
