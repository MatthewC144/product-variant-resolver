from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import tempfile
import unittest
import uuid
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
        expected_bytes = (json.dumps(catalog, indent=2, sort_keys=True) + "\n").encode()
        self.assertEqual(expected_bytes, (ROOT / "data" / "catalog.json").read_bytes())

    def test_generator_refuses_to_overwrite_applied_catalog_v2(self) -> None:
        path = ROOT / "scripts" / "generate_fixture_data.py"
        spec = importlib.util.spec_from_file_location("fixture_generator_guard", path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            catalog_path = Path(directory) / "catalog.json"
            catalog_path.write_text(
                json.dumps(
                    {
                        **module.build_catalog(),
                        "catalog_version": "catalog-v2",
                        "catalog_lineage": {"parent_product_count": 120},
                    }
                ),
                encoding="utf-8",
            )
            before = catalog_path.read_bytes()

            with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
                module.assert_safe_catalog_overwrite(catalog_path, module.build_catalog())

            self.assertEqual(catalog_path.read_bytes(), before)

    def test_validator_accepts_immutable_fixture_parent_lineage(self) -> None:
        path = ROOT / "scripts" / "validate_fixture_data.py"
        spec = importlib.util.spec_from_file_location("fixture_validator_lineage", path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        parent_products = self.catalog["products"]
        ordered_digest = module.content_sha256(
            [module.content_sha256(product) for product in parent_products]
        )
        catalog_v2 = {
            **self.catalog,
            "catalog_version": "catalog-v2",
            "source_note": (
                "Catalog contains 120 synthetic regression rows plus 20 owner-approved "
                "community-snapshot catalog rows; catalog inclusion is not exact authority."
            ),
            "products": [*parent_products, {"canonical_uuid": "appended"}],
            "catalog_lineage": {
                "schema_version": "pvr-catalog-lineage-v1",
                "parent_catalog_version": "fixture-v1",
                "parent_dataset_version": "fixture-v1",
                "parent_raw_catalog_sha256": self.manifest["catalog_sha256"],
                "parent_product_count": 120,
                "parent_ordered_product_sha256": ordered_digest,
                "application_version": "canonical-catalog-application-car-t4a-v1",
                "appended_product_count": 1,
            },
        }
        child_manifest = {
            **self.manifest,
            "catalog_version": "catalog-v2",
            "parent_catalog_version": "fixture-v1",
            "parent_catalog_sha256": self.manifest["catalog_sha256"],
            "parent_product_count": 120,
            "catalog_application_version": "canonical-catalog-application-car-t4a-v1",
            "product_count": 121,
        }
        errors: list[str] = []

        restored, digest = module.fixture_parent(catalog_v2, child_manifest, errors)

        self.assertEqual(errors, [])
        self.assertEqual(restored, parent_products)
        self.assertEqual(digest, self.manifest["catalog_sha256"])

    def test_full_validator_uses_fixture_parent_for_catalog_v2_history(self) -> None:
        path = ROOT / "scripts" / "validate_fixture_data.py"
        spec = importlib.util.spec_from_file_location("fixture_validator_catalog_v2", path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        parent_products = self.catalog["products"]
        appended = [
            {
                "aliases": [],
                "brand": "Hot Wheels",
                "canonical_id": f"catalog-v2-test-{index}",
                "canonical_uuid": str(uuid.UUID(int=10_000 + index)),
                "casting": f"Catalog V2 Test {index}",
                "collector_number": str(index),
                "color": None,
                "edition": None,
                "identifiers": [
                    {
                        "identifier_type": "toy_number",
                        "identifier_value": f"TEST{index:02d}",
                        "source_id": f"test://{index}",
                    }
                ],
                "near_duplicate_group": f"catalog-v2-test-{index}",
                "provenance": [{"source_name": "test_community_snapshot"}],
                "rarity_tier": None,
                "release_key": f"release-2025-test{index:02d}",
                "release_year": 2025,
                "series": "Test",
                "series_position": f"{index}/20",
            }
            for index in range(1, 21)
        ]
        child = {
            "catalog_lineage": {
                "schema_version": "pvr-catalog-lineage-v1",
                "parent_catalog_version": "fixture-v1",
                "parent_dataset_version": "fixture-v1",
                "parent_raw_catalog_sha256": self.manifest["catalog_sha256"],
                "parent_product_count": 120,
                "parent_ordered_product_sha256": module.content_sha256(
                    [module.content_sha256(product) for product in parent_products]
                ),
                "application_version": "canonical-catalog-application-car-t4a-v1",
                "appended_product_count": 20,
            },
            "catalog_version": "catalog-v2",
            "dataset_version": "fixture-v1",
            "products": [*parent_products, *appended],
            "source_note": (
                "Catalog contains 120 synthetic regression rows plus 20 owner-approved "
                "community-snapshot catalog rows; catalog inclusion is not exact authority."
            ),
        }
        child_bytes = (json.dumps(child, indent=2, sort_keys=True) + "\n").encode()
        child_manifest = {
            **self.manifest,
            "catalog_application_version": "canonical-catalog-application-car-t4a-v1",
            "catalog_sha256": hashlib.sha256(child_bytes).hexdigest(),
            "catalog_version": "catalog-v2",
            "parent_catalog_sha256": self.manifest["catalog_sha256"],
            "parent_catalog_version": "fixture-v1",
            "parent_product_count": 120,
            "product_count": 140,
        }
        with tempfile.TemporaryDirectory() as directory:
            isolated_root = Path(directory)
            shutil.copytree(ROOT / "data", isolated_root / "data")
            (isolated_root / "data/catalog.json").write_bytes(child_bytes)
            (isolated_root / "data/manifest.json").write_text(
                json.dumps(child_manifest, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            module.ROOT = isolated_root

            self.assertEqual(module.validate(), [])


if __name__ == "__main__":
    unittest.main()
