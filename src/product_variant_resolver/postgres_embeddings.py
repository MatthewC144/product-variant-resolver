from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from .catalog import Catalog, load_catalog
from .embedding_artifacts import (
    VersionedEmbedding,
    build_embedding_rows,
    embedding_artifact_version,
    embedding_index_checksum,
)
from .postgres_retrieval import SQLAlchemyPostgresRetrieverAdapter
from .retrieval import HashingEmbedding


def materialize_embeddings(
    catalog: Catalog,
    database_url: str,
    model: VersionedEmbedding,
) -> dict[str, Any]:
    if model.dimensions != 192:
        raise ValueError("the current PostgreSQL schema requires 192 embedding dimensions")
    adapter = SQLAlchemyPostgresRetrieverAdapter(database_url)
    try:
        adapter.verify_catalog(catalog)
        rows = build_embedding_rows(catalog, model)
        index_checksum = embedding_index_checksum(rows)
        sa = adapter.sqlalchemy
        with adapter.engine.begin() as connection:
            stored_uuids = {
                row[0]
                for row in connection.execute(
                    sa.text("SELECT canonical_uuid FROM product_embedding FOR UPDATE")
                )
            }
            expected_uuids = {row.canonical_uuid for row in rows}
            if stored_uuids - expected_uuids:
                raise ValueError(
                    "database embeddings contain identities outside the canonical catalog"
                )
            for row in rows:
                connection.execute(
                    sa.text(
                        "INSERT INTO product_embedding "
                        "(canonical_uuid, embedding_version, embedding, checksum) "
                        "VALUES (:canonical_uuid, :embedding_version, "
                        "CAST(:embedding AS vector), :checksum) "
                        "ON CONFLICT (canonical_uuid) DO UPDATE SET "
                        "embedding_version=EXCLUDED.embedding_version, "
                        "embedding=EXCLUDED.embedding, checksum=EXCLUDED.checksum"
                    ),
                    {
                        "canonical_uuid": row.canonical_uuid,
                        "embedding_version": row.embedding_version,
                        "embedding": row.vector_literal,
                        "checksum": row.checksum,
                    },
                )
            connection.execute(
                sa.text(
                    "INSERT INTO index_metadata "
                    "(index_name, catalog_version, artifact_version, checksum) "
                    "VALUES (:index_name, :catalog_version, :artifact_version, :checksum) "
                    "ON CONFLICT (index_name) DO UPDATE SET "
                    "catalog_version=EXCLUDED.catalog_version, "
                    "artifact_version=EXCLUDED.artifact_version, "
                    "checksum=EXCLUDED.checksum, updated_at=now()"
                ),
                {
                    "index_name": "canonical_dense",
                    "catalog_version": catalog.version,
                    "artifact_version": embedding_artifact_version(model),
                    "checksum": index_checksum,
                },
            )
        state = adapter.verify_dense_index(catalog, model)
        return {
            "status": "complete",
            "catalog_version": state.catalog_version,
            "embedding_version": state.embedding_version,
            "embedding_count": state.embedding_count,
            "index_checksum": state.index_checksum,
        }
    finally:
        adapter.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize deterministic canonical embeddings in PostgreSQL"
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path(os.getenv("PVR_CATALOG_PATH", "data/catalog.json")),
    )
    parser.add_argument("--database-url", default=os.getenv("PVR_DATABASE_URL"))
    parser.add_argument(
        "--dimensions",
        type=int,
        default=int(os.getenv("PVR_DENSE_DIMENSIONS", "192")),
    )
    arguments = parser.parse_args()
    if not arguments.database_url:
        parser.error("--database-url or PVR_DATABASE_URL is required")
    result = materialize_embeddings(
        load_catalog(arguments.catalog),
        arguments.database_url,
        HashingEmbedding(arguments.dimensions),
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
