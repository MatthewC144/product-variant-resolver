from __future__ import annotations

import importlib.util
import json
import unittest
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FixtureDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))
        cls.benchmark = json.loads((ROOT / "data" / "benchmark.json").read_text(encoding="utf-8"))
        cls.manifest = json.loads((ROOT / "data" / "manifest.json").read_text(encoding="utf-8"))

    def test_catalog_minimums_and_identity_uniqueness(self) -> None:
        products = self.catalog["products"]
        self.assertGreaterEqual(len(products), 120)
        self.assertGreaterEqual(len({item["casting"] for item in products}), 8)
        self.assertGreaterEqual(len({item["near_duplicate_group"] for item in products}), 20)
        self.assertEqual(len({item["canonical_uuid"] for item in products}), len(products))
        self.assertEqual(len({item["canonical_id"] for item in products}), len(products))
        self.assertTrue(all(item["provenance"] for item in products))

    def test_benchmark_minimums_and_targets(self) -> None:
        cases = self.benchmark["cases"]
        counts = Counter(case["expected_status"] for case in cases)
        self.assertGreaterEqual(len(cases), 90)
        self.assertGreaterEqual(counts["matched"], 50)
        self.assertGreaterEqual(counts["ambiguous"], 20)
        self.assertGreaterEqual(counts["no_match"], 20)
        known_ids = {item["canonical_id"] for item in self.catalog["products"]}
        for case in cases:
            if case["expected_status"] == "matched":
                self.assertIn(case["expected_canonical_id"], known_ids)
            else:
                self.assertIsNone(case["expected_canonical_id"])
                self.assertIsNone(case["expected_canonical_uuid"])

    def test_casting_families_do_not_cross_splits(self) -> None:
        family_splits: dict[str, set[str]] = defaultdict(set)
        for case in self.benchmark["cases"]:
            family_splits[case["casting_family"]].add(case["split"])
        self.assertTrue(all(len(splits) == 1 for splits in family_splits.values()))

    def test_frozen_manifest_matches_data(self) -> None:
        import hashlib

        self.assertEqual(
            self.manifest["catalog_sha256"],
            hashlib.sha256((ROOT / "data" / "catalog.json").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.manifest["benchmark_sha256"],
            hashlib.sha256((ROOT / "data" / "benchmark.json").read_bytes()).hexdigest(),
        )
        self.assertEqual(self.manifest["product_count"], len(self.catalog["products"]))
        self.assertEqual(self.manifest["benchmark_case_count"], len(self.benchmark["cases"]))

    def test_generator_is_deterministic_in_memory(self) -> None:
        path = ROOT / "scripts" / "generate_fixture_data.py"
        spec = importlib.util.spec_from_file_location("fixture_generator", path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        self.assertEqual(module.build_catalog(), module.build_catalog())
        catalog = module.build_catalog()
        self.assertEqual(module.build_benchmark(catalog), module.build_benchmark(catalog))


if __name__ == "__main__":
    unittest.main()
