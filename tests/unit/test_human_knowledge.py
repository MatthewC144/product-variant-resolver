from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from product_variant_resolver.human_knowledge import (
    HumanKnowledgeRetriever,
    HumanVariantKnowledgeDocument,
    ReviewFamilyKnowledgeDocument,
    load_human_knowledge_catalog,
)
from product_variant_resolver.retrieval import HashingEmbedding
from product_variant_resolver.signals import extract_signals


ROOT = Path(__file__).resolve().parents[2]
HUMAN_CATALOG = ROOT / "data/human_backed_catalog.json"
FAMILY_PROJECTION = ROOT / "data/review_family_knowledge.json"
FAMILY_MANIFEST = ROOT / "data/review_family_knowledge_manifest.json"


class HumanKnowledgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_human_knowledge_catalog(
            HUMAN_CATALOG, FAMILY_PROJECTION, FAMILY_MANIFEST
        )
        cls.retriever = HumanKnowledgeRetriever(cls.catalog, HashingEmbedding())

    def test_catalog_loads_typed_review_gated_documents(self) -> None:
        self.assertEqual(self.catalog.version, "human-backed-catalog-v1")
        self.assertEqual(
            self.catalog.review_family_version,
            "review-family-knowledge-fandom-2025-r790665-v1",
        )
        self.assertEqual(len(self.catalog.documents), 142)
        self.assertEqual(self.catalog.variant_document_count, 100)
        self.assertEqual(self.catalog.review_family_document_count, 42)
        self.assertTrue(
            all(
                item.identity_status == "needs_canonical_review"
                for item in self.catalog.documents
                if isinstance(item, HumanVariantKnowledgeDocument)
            )
        )
        self.assertTrue(
            all(
                item.identity_status == "family_accepted_variants_unreviewed"
                for item in self.catalog.documents
                if isinstance(item, ReviewFamilyKnowledgeDocument)
            )
        )
        self.assertEqual(
            len({item.knowledge_id for item in self.catalog.documents}), 142
        )
        self.assertEqual(
            len({item.knowledge_uuid for item in self.catalog.documents}), 142
        )

    def test_hybrid_retrieval_returns_matching_human_evidence(self) -> None:
        signals = extract_signals("Hot Wheels BMW M3 GT2 Neon Speeders")
        candidates = self.retriever.retrieve(signals, 3)
        self.assertEqual(candidates[0].document.casting, "BMW M3 GT2")
        self.assertEqual(candidates[0].document.knowledge_type, "provisional_variant")
        self.assertIsInstance(candidates[0].document, HumanVariantKnowledgeDocument)
        self.assertEqual(candidates[0].document.variant_label, "Neon Speeders")
        self.assertEqual(candidates[0].sparse_rank, 1)
        self.assertEqual(candidates[0].dense_rank, 1)
        self.assertIn("m3", candidates[0].matched_tokens)
        self.assertIn("gt2", candidates[0].matched_tokens)

    def test_no_shared_tokens_returns_no_suggestion(self) -> None:
        signals = extract_signals("qzxv completely unknown")
        self.assertEqual(self.retriever.retrieve(signals, 5), [])

    def test_limit_is_enforced(self) -> None:
        signals = extract_signals("Hot Wheels")
        self.assertEqual(len(self.retriever.retrieve(signals, 2)), 2)
        with self.assertRaisesRegex(ValueError, "between 1 and 25"):
            self.retriever.retrieve(signals, 26)

    def test_all_42_family_names_retrieve_the_expected_document_within_top_five(self) -> None:
        family_documents = [
            item
            for item in self.catalog.documents
            if isinstance(item, ReviewFamilyKnowledgeDocument)
        ]
        self.assertEqual(len(family_documents), 42)
        worst_rank = 0
        for document in family_documents:
            candidates = self.retriever.retrieve(
                extract_signals(f"{document.brand} {document.casting}"), 5
            )
            matching = next(
                item
                for item in candidates
                if item.document.knowledge_id == document.review_family_id
            )
            worst_rank = max(worst_rank, matching.rrf_rank)
        self.assertLessEqual(worst_rank, 5)

    def test_family_searchable_text_uses_only_approved_name_fields(self) -> None:
        family = next(
            item
            for item in self.catalog.documents
            if isinstance(item, ReviewFamilyKnowledgeDocument)
        )
        self.assertEqual(
            family.searchable_text,
            " ".join((family.brand, family.casting, *family.aliases)),
        )
        self.assertFalse(
            set(family.source_record_ids) & set(family.searchable_text.split())
        )

    def test_merge_and_hold_families_create_no_review_family_document(self) -> None:
        registry = json.loads(
            (ROOT / "data/review_family_registry.json").read_text(encoding="utf-8")
        )
        projected_ids = {
            item.review_family_id
            for item in self.catalog.documents
            if isinstance(item, ReviewFamilyKnowledgeDocument)
        }
        merge_ids = {item["source_family_review_id"] for item in registry["merge_links"]}
        hold_ids = {item["review_family_id"] for item in registry["hold_exclusions"]}
        self.assertTrue(projected_ids.isdisjoint(merge_ids | hold_ids))
        for merge in registry["merge_links"]:
            candidates = self.retriever.retrieve(
                extract_signals(f"{merge['brand']} {merge['display_name']}"), 5
            )
            self.assertTrue(
                any(
                    isinstance(item.document, HumanVariantKnowledgeDocument)
                    and item.document.casting == merge["target_casting"]
                    for item in candidates
                )
            )
        for hold in registry["hold_exclusions"]:
            candidates = self.retriever.retrieve(
                extract_signals(f"{hold['brand']} {hold['display_name']}"), 5
            )
            self.assertFalse(
                any(
                    isinstance(item.document, ReviewFamilyKnowledgeDocument)
                    and item.document.casting == hold["display_name"]
                    for item in candidates
                )
            )

    def test_loader_rejects_a_variant_that_bypasses_canonical_review(self) -> None:
        source = HUMAN_CATALOG
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["castings"][0]["provisional_variants"][0]["identity_status"] = "canonical"

        with tempfile.TemporaryDirectory() as directory:
            invalid_path = Path(directory) / "invalid-human-catalog.json"
            invalid_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid provisional variant"):
                load_human_knowledge_catalog(
                    invalid_path, FAMILY_PROJECTION, FAMILY_MANIFEST
                )

    def test_family_loader_rejects_checksum_field_scope_and_count_changes(self) -> None:
        source_projection = json.loads(FAMILY_PROJECTION.read_text(encoding="utf-8"))
        source_manifest = json.loads(FAMILY_MANIFEST.read_text(encoding="utf-8"))

        mutations = (
            (
                lambda payload: payload["documents"][0].update(
                    {"decision_reason": "must never become searchable"}
                ),
                "fields differ",
            ),
            (
                lambda payload: payload["eligible_for"].append("canonical_retrieval"),
                "eligibility boundary",
            ),
            (lambda payload: payload["documents"].pop(), "exactly 42"),
        )
        for mutate, expected_error in mutations:
            with self.subTest(expected_error=expected_error):
                with tempfile.TemporaryDirectory() as directory:
                    projection = json.loads(json.dumps(source_projection))
                    mutate(projection)
                    projection_path = Path(directory) / FAMILY_PROJECTION.name
                    projection_path.write_text(json.dumps(projection), encoding="utf-8")
                    manifest = json.loads(json.dumps(source_manifest))
                    manifest["projection_sha256"] = hashlib.sha256(
                        projection_path.read_bytes()
                    ).hexdigest()
                    manifest_path = Path(directory) / FAMILY_MANIFEST.name
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, expected_error):
                        load_human_knowledge_catalog(
                            HUMAN_CATALOG, projection_path, manifest_path
                        )

        with tempfile.TemporaryDirectory() as directory:
            projection_path = Path(directory) / FAMILY_PROJECTION.name
            projection_path.write_bytes(FAMILY_PROJECTION.read_bytes())
            manifest_path = Path(directory) / FAMILY_MANIFEST.name
            manifest_path.write_bytes(FAMILY_MANIFEST.read_bytes())
            projection_path.write_text(
                FAMILY_PROJECTION.read_text(encoding="utf-8") + " ",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "checksum differs"):
                load_human_knowledge_catalog(
                    HUMAN_CATALOG, projection_path, manifest_path
                )


if __name__ == "__main__":
    unittest.main()
