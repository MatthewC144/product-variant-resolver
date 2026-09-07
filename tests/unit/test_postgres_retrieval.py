from __future__ import annotations

import unittest
from pathlib import Path
from uuid import UUID

from product_variant_resolver.catalog import load_catalog
from product_variant_resolver.retrieval import (
    PGVECTOR_EXACT_SQL,
    POSTGRES_FTS_SQL,
    HashingEmbedding,
    PostgresDenseRetriever,
    PostgresSparseRetriever,
)
from product_variant_resolver.signals import extract_signals


ROOT = Path(__file__).resolve().parents[2]


class RecordingAdapter:
    def __init__(self, rows: list[tuple[UUID, float]]) -> None:
        self.rows = rows
        self.statement = ""
        self.parameters: dict[str, object] = {}

    def execute_ranked(
        self, statement: str, parameters: dict[str, object]
    ) -> list[tuple[UUID, float]]:
        self.statement = statement
        self.parameters = parameters
        return self.rows


class PostgresSparseRetrieverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog(ROOT / "data/catalog.json")

    def test_query_text_and_limit_are_bound_parameters(self) -> None:
        target = self.catalog.products[0]
        adapter = RecordingAdapter([(target.canonical_uuid, 0.75)])
        retriever = PostgresSparseRetriever(self.catalog, adapter)

        result = retriever.retrieve(
            extract_signals("Nomad'); DROP TABLE product_variant; -- #101"),
            5,
        )

        self.assertEqual(result, [(target, 0.75)])
        self.assertEqual(adapter.statement, POSTGRES_FTS_SQL)
        self.assertIn(":query", adapter.statement)
        self.assertIn(":limit", adapter.statement)
        self.assertNotIn("DROP TABLE", adapter.statement)
        self.assertEqual(adapter.parameters["limit"], 5)
        self.assertIn("drop", str(adapter.parameters["query"]))

    def test_unknown_database_identity_fails_closed(self) -> None:
        retriever = PostgresSparseRetriever(
            self.catalog,
            RecordingAdapter([(UUID(int=0), 1.0)]),
        )
        with self.assertRaisesRegex(RuntimeError, "absent from the loaded catalog"):
            retriever.retrieve(extract_signals("Nomad"), 5)

    def test_empty_query_and_invalid_limit_are_rejected_without_sql(self) -> None:
        adapter = RecordingAdapter([])
        retriever = PostgresSparseRetriever(self.catalog, adapter)
        self.assertEqual(retriever.retrieve(extract_signals("!!!"), 5), [])
        self.assertEqual(adapter.statement, "")
        with self.assertRaisesRegex(ValueError, "between 1 and 25"):
            retriever.retrieve(extract_signals("Nomad"), 26)


class PostgresDenseRetrieverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog(ROOT / "data/catalog.json")

    def test_vector_version_and_limit_are_bound_parameters(self) -> None:
        target = self.catalog.products[0]
        adapter = RecordingAdapter([(target.canonical_uuid, 0.9)])
        retriever = PostgresDenseRetriever(
            self.catalog,
            adapter,
            HashingEmbedding(192),
        )

        result = retriever.retrieve(extract_signals("Chevy Nomad"), 5)

        self.assertEqual(result, [(target, 0.9)])
        self.assertEqual(adapter.statement, PGVECTOR_EXACT_SQL)
        self.assertIn(":embedding", adapter.statement)
        self.assertIn(":embedding_version", adapter.statement)
        self.assertIn(":limit", adapter.statement)
        self.assertEqual(adapter.parameters["limit"], 5)
        self.assertEqual(
            adapter.parameters["embedding_version"],
            "hashing-v1-d192-catalog-searchable-text-v1",
        )
        self.assertTrue(str(adapter.parameters["embedding"]).startswith("["))

    def test_empty_query_and_invalid_limit_avoid_database_work(self) -> None:
        adapter = RecordingAdapter([])
        retriever = PostgresDenseRetriever(
            self.catalog,
            adapter,
            HashingEmbedding(192),
        )
        self.assertEqual(retriever.retrieve(extract_signals("!!!"), 5), [])
        self.assertEqual(adapter.statement, "")
        with self.assertRaisesRegex(ValueError, "between 1 and 25"):
            retriever.retrieve(extract_signals("Nomad"), 26)

    def test_unknown_database_identity_fails_closed(self) -> None:
        retriever = PostgresDenseRetriever(
            self.catalog,
            RecordingAdapter([(UUID(int=0), 1.0)]),
            HashingEmbedding(192),
        )
        with self.assertRaisesRegex(RuntimeError, "absent from the loaded catalog"):
            retriever.retrieve(extract_signals("Nomad"), 5)


if __name__ == "__main__":
    unittest.main()
