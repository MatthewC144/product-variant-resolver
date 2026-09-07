"""Verify T10 against a migrated and ingested disposable PostgreSQL database."""

from __future__ import annotations

import json
import os
from pathlib import Path

import sqlalchemy as sa
from fastapi.testclient import TestClient

from product_variant_resolver.api import create_app
from product_variant_resolver.catalog import load_catalog
from product_variant_resolver.config import Settings
from product_variant_resolver.postgres_embeddings import materialize_embeddings
from product_variant_resolver.postgres_retrieval import SQLAlchemyPostgresRetrieverAdapter
from product_variant_resolver.retrieval import HashingEmbedding, PostgresDenseRetriever
from product_variant_resolver.signals import extract_signals


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required")
    return value


def _snapshot(database_url: str) -> list[tuple[str, ...]]:
    engine = sa.create_engine(database_url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                sa.text(
                    "SELECT canonical_uuid::text, embedding_version, embedding::text, checksum "
                    "FROM product_embedding ORDER BY canonical_uuid"
                )
            )
            return [tuple(str(value) for value in row) for row in rows]
    finally:
        engine.dispose()


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
    model = HashingEmbedding(192)

    first_result = materialize_embeddings(catalog, database_url, model)
    first_snapshot = _snapshot(database_url)
    repeated_result = materialize_embeddings(catalog, database_url, model)
    repeated_snapshot = _snapshot(database_url)
    assert repeated_snapshot == first_snapshot
    assert repeated_result == first_result

    adapter = SQLAlchemyPostgresRetrieverAdapter(database_url)
    state = adapter.verify_dense_index(catalog, model)
    retriever = PostgresDenseRetriever(catalog, adapter, model)

    target = next(product for product in catalog.products if product.aliases)
    alias_results = retriever.retrieve(extract_signals(target.aliases[-1]), 25)
    assert any(
        product.canonical_uuid == target.canonical_uuid
        for product, _score in alias_results
    )

    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    matched_test_cases = [
        case
        for case in benchmark["cases"]
        if case["split"] == "test" and case["expected_status"] == "matched"
    ]
    hits = 0
    for case in matched_test_cases:
        results = retriever.retrieve(extract_signals(case["query"]), 25)
        if any(
            str(product.canonical_uuid) == case["expected_canonical_uuid"]
            for product, _score in results
        ):
            hits += 1
    recall_at_25 = hits / len(matched_test_cases)
    assert recall_at_25 >= 0.95, recall_at_25

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
    dense_version = health.json()["dependencies"]["dense_index"]["version"]
    assert dense_version == (
        "postgres-exact-hashing-v1-d192-catalog-searchable-text-v1"
    )
    response = client.post(
        "/resolve",
        json={"title": "2022 Chevy Nomad Red #101", "debug": True},
    )
    assert response.status_code == 200, response.text
    assert response.json()["debug"]["model_versions"]["dense"] == dense_version
    observed_statuses: dict[str, str] = {}
    for expected_status in ("matched", "ambiguous", "no_match"):
        case = next(
            item
            for item in benchmark["cases"]
            if item["split"] == "test" and item["expected_status"] == expected_status
        )
        status_response = client.post("/resolve", json={"title": case["query"]})
        assert status_response.status_code == 200, status_response.text
        observed_statuses[expected_status] = status_response.json()["status"]
    assert observed_statuses == {
        "matched": "matched",
        "ambiguous": "ambiguous",
        "no_match": "no_match",
    }

    with adapter.engine.begin() as connection:
        connection.execute(
            sa.text(
                "DELETE FROM product_embedding WHERE canonical_uuid=:canonical_uuid"
            ),
            {"canonical_uuid": catalog.products[0].canonical_uuid},
        )
    unavailable_client = TestClient(create_app(settings))
    assert unavailable_client.get("/health").status_code == 503
    materialize_embeddings(catalog, database_url, model)
    adapter.verify_dense_index(catalog, model)

    print(
        json.dumps(
            {
                "status": "passed",
                "embedding_version": state.embedding_version,
                "embedding_count": state.embedding_count,
                "repeated_materialization_identical": True,
                "catalog_alias_retrieved": True,
                "matched_test_cases": len(matched_test_cases),
                "recall_at_25": recall_at_25,
                "api_postgres_dense_ready": True,
                "api_three_state_policy_verified": True,
                "missing_embedding_fails_readiness": True,
                "exact_pgvector_operator": "<=>",
            },
            indent=2,
            sort_keys=True,
        )
    )
    adapter.dispose()


if __name__ == "__main__":
    main()
