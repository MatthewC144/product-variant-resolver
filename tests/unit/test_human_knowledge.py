from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from product_variant_resolver.human_knowledge import (
    HumanKnowledgeRetriever,
    load_human_knowledge_catalog,
)
from product_variant_resolver.retrieval import HashingEmbedding
from product_variant_resolver.signals import extract_signals


ROOT = Path(__file__).resolve().parents[2]


class HumanKnowledgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_human_knowledge_catalog(ROOT / "data/human_backed_catalog.json")
        cls.retriever = HumanKnowledgeRetriever(cls.catalog, HashingEmbedding())

    def test_catalog_loads_only_review_gated_variants(self) -> None:
        self.assertEqual(self.catalog.version, "human-backed-catalog-v1")
        self.assertEqual(len(self.catalog.documents), 100)
        self.assertTrue(
            all(item.identity_status == "needs_canonical_review" for item in self.catalog.documents)
        )

    def test_hybrid_retrieval_returns_matching_human_evidence(self) -> None:
        signals = extract_signals("Hot Wheels BMW M3 GT2 Neon Speeders")
        candidates = self.retriever.retrieve(signals, 3)
        self.assertEqual(candidates[0].document.casting, "BMW M3 GT2")
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

    def test_loader_rejects_a_variant_that_bypasses_canonical_review(self) -> None:
        source = ROOT / "data/human_backed_catalog.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["castings"][0]["provisional_variants"][0]["identity_status"] = "canonical"

        with tempfile.TemporaryDirectory() as directory:
            invalid_path = Path(directory) / "invalid-human-catalog.json"
            invalid_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid provisional variant"):
                load_human_knowledge_catalog(invalid_path)


if __name__ == "__main__":
    unittest.main()
