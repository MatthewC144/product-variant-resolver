from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HumanBackedCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path = ROOT / "data" / "human_backed_catalog.json"
        cls.catalog = json.loads(cls.path.read_text(encoding="utf-8"))
        cls.manifest = json.loads(
            (ROOT / "data" / "human_backed_catalog_manifest.json").read_text(
                encoding="utf-8"
            )
        )

    def test_catalog_counts_and_source_coverage(self) -> None:
        castings = self.catalog["castings"]
        variants = [variant for casting in castings for variant in casting["provisional_variants"]]
        source_ids = {
            case_id
            for casting in castings
            for case_id in casting["source_case_ids"]
        }
        self.assertEqual(len(castings), 97)
        self.assertEqual(len(variants), 100)
        self.assertEqual(len(source_ids), 101)
        self.assertEqual(self.manifest["merged_duplicate_record_count"], 1)

    def test_ids_are_unique_and_all_variants_require_review(self) -> None:
        castings = self.catalog["castings"]
        variants = [variant for casting in castings for variant in casting["provisional_variants"]]
        self.assertEqual(len({item["casting_uuid"] for item in castings}), 97)
        self.assertEqual(len({item["casting_id"] for item in castings}), 97)
        self.assertEqual(len({item["provisional_variant_uuid"] for item in variants}), 100)
        self.assertEqual(len({item["provisional_variant_id"] for item in variants}), 100)
        self.assertTrue(
            all(item["identity_status"] == "needs_canonical_review" for item in variants)
        )
        hot_wheels = [item for item in castings if item["brand"].casefold() == "hot wheels"]
        self.assertTrue(hot_wheels)
        self.assertTrue(all(item["brand"] == "Hot Wheels" for item in hot_wheels))

    def test_duplicate_chevelle_labels_merge_without_losing_sources(self) -> None:
        chevelle = next(
            item for item in self.catalog["castings"]
            if item["casting"] == "1970 Chevrolet Chevelle SS"
        )
        self.assertEqual(len(chevelle["provisional_variants"]), 1)
        variant = chevelle["provisional_variants"][0]
        self.assertEqual(len(variant["source_case_ids"]), 2)
        self.assertEqual(len(variant["human_label_names"]), 2)
        self.assertEqual(len(variant["pricing_keywords"]), 2)

    def test_similar_castings_are_not_fuzzy_merged(self) -> None:
        names = {item["casting"] for item in self.catalog["castings"]}
        self.assertIn("Dodge Challenger", names)
        self.assertIn("18 Dodge Challenger SRT Demon", names)
        self.assertIn("ICE CHARGER", names)
        self.assertIn("Nissan Skyline GTR (R34)", names)
        self.assertIn("Nissan Skyline RS", names)

    def test_catalog_is_not_canonical_variant_ground_truth(self) -> None:
        self.assertEqual(self.catalog["status"], "human_review_draft")
        self.assertIn("canonical_variant_response", self.catalog["excluded_from"])
        self.assertIn("calibration_training", self.catalog["excluded_from"])

    def test_manifest_freezes_source_and_catalog(self) -> None:
        self.assertEqual(
            self.manifest["catalog_sha256"],
            hashlib.sha256(self.path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.manifest["source_dataset_sha256"],
            hashlib.sha256((ROOT / "data" / "human_labeled_names.json").read_bytes()).hexdigest(),
        )

    def test_builder_is_deterministic_in_memory(self) -> None:
        path = ROOT / "scripts" / "build_human_backed_catalog.py"
        spec = importlib.util.spec_from_file_location("human_backed_catalog", path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        source = ROOT / "data" / "human_labeled_names.json"
        self.assertEqual(module.build_catalog(source), module.build_catalog(source))


if __name__ == "__main__":
    unittest.main()
