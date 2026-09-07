from __future__ import annotations

import unittest
from pathlib import Path

from product_variant_resolver.catalog import Catalog, load_catalog
from product_variant_resolver.embedding_artifacts import (
    build_embedding_rows,
    embedding_artifact_version,
    embedding_index_checksum,
)
from product_variant_resolver.postgres_embeddings import materialize_embeddings
from product_variant_resolver.retrieval import HashingEmbedding


ROOT = Path(__file__).resolve().parents[2]


class EmbeddingArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog(ROOT / "data/catalog.json")
        cls.model = HashingEmbedding(192)

    def test_artifact_is_versioned_complete_and_repeatable(self) -> None:
        first = build_embedding_rows(self.catalog, self.model)
        repeated = build_embedding_rows(self.catalog, self.model)
        reordered = build_embedding_rows(
            Catalog(self.catalog.version, list(reversed(self.catalog.products))),
            self.model,
        )

        self.assertEqual(first, repeated)
        self.assertEqual(first, reordered)
        self.assertEqual(len(first), len(self.catalog.products))
        self.assertEqual(len({row.canonical_uuid for row in first}), len(first))
        self.assertTrue(all(len(row.checksum) == 64 for row in first))
        self.assertEqual(
            embedding_artifact_version(self.model),
            "hashing-v1-d192-catalog-searchable-text-v1",
        )
        self.assertEqual(
            embedding_index_checksum(first),
            embedding_index_checksum(repeated),
        )

    def test_catalog_text_change_changes_row_and_index_checksums(self) -> None:
        original_rows = build_embedding_rows(self.catalog, self.model)
        first = self.catalog.products[0]
        changed_product = type(first)(
            canonical_uuid=first.canonical_uuid,
            canonical_id=first.canonical_id,
            product=first.product.model_copy(update={"color": "Dense Checksum Test"}),
            aliases=first.aliases,
            identifiers=first.identifiers,
            provenance=first.provenance,
            alias_records=first.alias_records,
            identifier_records=first.identifier_records,
        )
        changed_catalog = Catalog(
            self.catalog.version,
            [changed_product, *self.catalog.products[1:]],
        )
        changed_rows = build_embedding_rows(changed_catalog, self.model)
        original_by_uuid = {row.canonical_uuid: row for row in original_rows}
        changed_by_uuid = {row.canonical_uuid: row for row in changed_rows}

        self.assertNotEqual(
            original_by_uuid[first.canonical_uuid].checksum,
            changed_by_uuid[first.canonical_uuid].checksum,
        )
        self.assertNotEqual(
            embedding_index_checksum(original_rows),
            embedding_index_checksum(changed_rows),
        )

    def test_materializer_rejects_dimensions_that_do_not_match_schema(self) -> None:
        with self.assertRaisesRegex(ValueError, "requires 192"):
            materialize_embeddings(
                self.catalog,
                "postgresql+psycopg://unused",
                HashingEmbedding(64),
            )


if __name__ == "__main__":
    unittest.main()
