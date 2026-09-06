"""Verify T07 against an empty, migrated, disposable PostgreSQL database.

This script writes catalog rows and deliberately triggers a rollback. It refuses to
run unless the caller explicitly marks the database as disposable.
"""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy.pool import NullPool

from product_variant_resolver.catalog import Catalog, load_catalog
from product_variant_resolver.ingestion import ingest_catalog
from product_variant_resolver.postgres_ingestion import PostgresCatalogRepository


TABLE_ORDER = {
    "product_variant": "canonical_uuid",
    "product_alias": "id",
    "identifier": "id",
    "provenance_record": "id",
    "index_metadata": "index_name",
    "product_search": "canonical_uuid",
    "product_embedding": "canonical_uuid",
}


def _required_environment(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _snapshot(engine: sa.Engine) -> dict[str, list[tuple[Any, ...]]]:
    snapshot: dict[str, list[tuple[Any, ...]]] = {}
    with engine.connect() as connection:
        for table, order_column in TABLE_ORDER.items():
            rows = connection.execute(
                sa.text(f"SELECT * FROM {table} ORDER BY {order_column}")
            ).all()
            snapshot[table] = [tuple(str(value) for value in row) for row in rows]
    return snapshot


def _assert_empty(engine: sa.Engine) -> None:
    snapshot = _snapshot(engine)
    populated = {table: len(rows) for table, rows in snapshot.items() if rows}
    if populated:
        raise AssertionError(
            "ingestion verification requires empty application tables; found "
            + json.dumps(populated, sort_keys=True)
        )


def main() -> None:
    if os.getenv("PVR_ALLOW_DESTRUCTIVE_TEST_DATABASE") != "1":
        raise RuntimeError(
            "set PVR_ALLOW_DESTRUCTIVE_TEST_DATABASE=1 only for a disposable test database"
        )
    database_url = _required_environment("PVR_DATABASE_URL")
    catalog_path = Path(_required_environment("PVR_CATALOG_PATH"))
    engine = sa.create_engine(database_url, poolclass=NullPool)
    catalog = load_catalog(catalog_path)
    _assert_empty(engine)

    ingest_catalog(catalog, PostgresCatalogRepository(engine))
    first = _snapshot(engine)
    ingest_catalog(catalog, PostgresCatalogRepository(engine))
    repeated = _snapshot(engine)
    assert repeated == first, "repeated ingestion changed stored rows"

    changed_product = replace(
        catalog.products[0],
        product=catalog.products[0].product.model_copy(update={"color": "Rollback Test"}),
    )
    colliding_product = replace(
        catalog.products[1], canonical_id=catalog.products[0].canonical_id
    )
    invalid_catalog = Catalog(
        "transaction-rollback-test",
        [changed_product, colliding_product, *catalog.products[2:]],
    )
    try:
        ingest_catalog(invalid_catalog, PostgresCatalogRepository(engine))
    except ValueError:
        pass
    else:
        raise AssertionError("colliding catalog unexpectedly committed")
    after_failure = _snapshot(engine)
    assert after_failure == first, "failed ingestion was not fully rolled back"

    incomplete_catalog = Catalog("incomplete-snapshot-test", list(catalog.products[:-1]))
    try:
        ingest_catalog(incomplete_catalog, PostgresCatalogRepository(engine))
    except ValueError:
        pass
    else:
        raise AssertionError("incomplete full catalog unexpectedly replaced metadata")
    assert _snapshot(engine) == first, "incomplete catalog attempt was not rolled back"

    counts = {table: len(rows) for table, rows in first.items()}
    assert counts == {
        "product_variant": 120,
        "product_alias": 240,
        "identifier": 120,
        "provenance_record": 120,
        "index_metadata": 1,
        "product_search": 120,
        "product_embedding": 0,
    }, counts
    print(
        json.dumps(
            {
                "status": "passed",
                "first_ingestion": counts,
                "repeated_ingestion_identical": True,
                "collision_rolled_back": True,
                "implicit_deletion_refused": True,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
