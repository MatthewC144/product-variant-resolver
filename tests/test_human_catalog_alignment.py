from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HumanCatalogAlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path = ROOT / "data" / "human_labeled_catalog_alignment.json"
        cls.alignment = json.loads(cls.path.read_text(encoding="utf-8"))
        cls.manifest = json.loads(
            (ROOT / "data" / "human_labeled_catalog_alignment_manifest.json").read_text(
                encoding="utf-8"
            )
        )

    def test_current_alignment_is_conservative_and_complete(self) -> None:
        rows = self.alignment["alignments"]
        self.assertEqual(len(rows), 101)
        self.assertEqual(len({row["case_id"] for row in rows}), 101)
        self.assertEqual(
            self.manifest["status_counts"],
            {"mapped": 0, "casting_family_only": 2, "unmapped": 99},
        )
        self.assertTrue(all(row["canonical_uuid"] is None for row in rows))
        self.assertTrue(all(row["canonical_id"] is None for row in rows))

    def test_family_only_rows_are_exact_toyota_supra_matches(self) -> None:
        family_only = [
            row for row in self.alignment["alignments"]
            if row["status"] == "casting_family_only"
        ]
        self.assertEqual(len(family_only), 2)
        self.assertTrue(
            all(row["matched_casting_family"] == "Toyota Supra" for row in family_only)
        )
        self.assertTrue(all(len(row["candidate_canonical_ids"]) == 12 for row in family_only))

    def test_unmapped_rows_do_not_receive_suggested_catalog_ids(self) -> None:
        unmapped = [
            row for row in self.alignment["alignments"] if row["status"] == "unmapped"
        ]
        self.assertEqual(len(unmapped), 99)
        self.assertTrue(all(not row["candidate_canonical_ids"] for row in unmapped))

    def test_manifest_freezes_all_inputs_and_output(self) -> None:
        self.assertEqual(
            self.manifest["alignment_sha256"],
            hashlib.sha256(self.path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.manifest["human_dataset_sha256"],
            hashlib.sha256((ROOT / "data" / "human_labeled_names.json").read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.manifest["catalog_sha256"],
            hashlib.sha256((ROOT / "data" / "catalog.json").read_bytes()).hexdigest(),
        )

    def test_alignment_builder_is_deterministic_in_memory(self) -> None:
        path = ROOT / "scripts" / "align_human_labeled_names.py"
        spec = importlib.util.spec_from_file_location("human_catalog_alignment", path)
        self.assertIsNotNone(spec)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        args = (ROOT / "data" / "human_labeled_names.json", ROOT / "data" / "catalog.json")
        self.assertEqual(module.build_alignment(*args), module.build_alignment(*args))


if __name__ == "__main__":
    unittest.main()
