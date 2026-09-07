"""Verify T09 against a migrated and ingested disposable PostgreSQL database."""

from __future__ import annotations

import json
import os
from pathlib import Path

import sqlalchemy as sa
from fastapi.testclient import TestClient

from product_variant_resolver.api import create_app
from product_variant_resolver.catalog import catalog_checksum, load_catalog
from product_variant_resolver.config import Settings
from product_variant_resolver.postgres_retrieval import SQLAlchemyPostgresRetrieverAdapter
from product_variant_resolver.retrieval import POSTGRES_FTS_SQL, PostgresSparseRetriever
from product_variant_resolver.signals import extract_signals


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def main() -> None:
    if os.getenv("PVR_ALLOW_DESTRUCTIVE_TEST_DATABASE") != "1":
        raise RuntimeError(
            "set PVR_ALLOW_DESTRUCTIVE_TEST_DATABASE=1 only for a disposable test database"
        )
    database_url = _required("PVR_DATABASE_URL")
    catalog_path = Path(_required("PVR_CATALOG_PATH"))
    benchmark_path = Path(_required("PVR_BENCHMARK_PATH"))
    human_catalog_path = Path(_required("PVR_HUMAN_CATALOG_PATH"))
    ui_path = Path(_required("PVR_UI_PATH"))
    catalog = load_catalog(catalog_path)
    adapter = SQLAlchemyPostgresRetrieverAdapter(database_url)
    state = adapter.verify_catalog(catalog)
    retriever = PostgresSparseRetriever(catalog, adapter)

    target = catalog.products[0]
    identifier = target.identifiers[0]
    identifier_results = retriever.retrieve(extract_signals(identifier), 5)
    assert identifier_results[0][0].canonical_uuid == target.canonical_uuid

    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    matched_test_cases = [
        case
        for case in benchmark["cases"]
        if case["split"] == "test" and case["expected_status"] == "matched"
    ]
    hits = 0
    for case in matched_test_cases:
        results = retriever.retrieve(extract_signals(case["query"]), 25)
        if any(str(product.canonical_uuid) == case["expected_canonical_uuid"] for product, _ in results):
            hits += 1
    recall_at_25 = hits / len(matched_test_cases)
    assert recall_at_25 >= 0.95, recall_at_25

    injection_results = retriever.retrieve(
        extract_signals("Nomad'); DROP TABLE product_variant; -- #101"),
        5,
    )
    assert injection_results
    with adapter.engine.connect() as connection:
        transaction = connection.begin()
        table_exists = connection.scalar(
            sa.text("SELECT to_regclass('public.product_variant')")
        )
        connection.execute(sa.text("SET LOCAL enable_seqscan=off"))
        plan = "\n".join(
            row[0]
            for row in connection.execute(
                sa.text("EXPLAIN " + POSTGRES_FTS_SQL),
                {"query": '"nomad"', "limit": 5},
            )
        )
        transaction.rollback()
    assert table_exists == "product_variant"
    assert "ix_product_search_document" in plan

    settings = Settings(
        catalog_path=catalog_path,
        human_catalog_path=human_catalog_path,
        benchmark_path=benchmark_path,
        ui_path=ui_path,
        database_url=database_url,
        backend="postgres",
    )
    client = TestClient(create_app(settings))
    health = client.get("/health")
    assert health.status_code == 200, health.text
    health_payload = health.json()
    assert health_payload["dependencies"]["sparse_index"]["version"] == (
        "postgres-fts-simple-v1"
    )
    assert health_payload["dependencies"]["database"]["version"].startswith("postgresql-")
    response = client.post(
        "/resolve",
        json={"title": "2022 Chevy Nomad Red #101", "debug": True},
    )
    assert response.status_code == 200, response.text
    assert response.json()["debug"]["model_versions"]["sparse"] == (
        "postgres-fts-simple-v1"
    )

    expected_checksum = catalog_checksum(catalog)
    with adapter.engine.begin() as connection:
        connection.execute(
            sa.text(
                "UPDATE index_metadata SET checksum=:checksum "
                "WHERE index_name=:index_name"
            ),
            {"checksum": "0" * 64, "index_name": "canonical_catalog"},
        )
    unavailable_client = TestClient(create_app(settings))
    assert unavailable_client.get("/health").status_code == 503
    with adapter.engine.begin() as connection:
        connection.execute(
            sa.text(
                "UPDATE index_metadata SET checksum=:checksum "
                "WHERE index_name=:index_name"
            ),
            {"checksum": expected_checksum, "index_name": "canonical_catalog"},
        )
    adapter.verify_catalog(catalog)

    print(
        json.dumps(
            {
                "status": "passed",
                "database_version": state.database_version,
                "catalog_version": state.catalog_version,
                "product_count": state.product_count,
                "search_document_count": state.search_document_count,
                "identifier_top1": True,
                "matched_test_cases": len(matched_test_cases),
                "recall_at_25": recall_at_25,
                "gin_index_plan_verified": True,
                "bound_injection_probe_safe": True,
                "api_postgres_backend_ready": True,
                "checksum_mismatch_fails_readiness": True,
            },
            indent=2,
            sort_keys=True,
        )
    )
    adapter.dispose()


if __name__ == "__main__":
    main()
