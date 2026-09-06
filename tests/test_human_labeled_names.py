from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HumanLabeledNameDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.dataset_path = ROOT / "data" / "human_labeled_names.json"
        cls.dataset = json.loads(cls.dataset_path.read_text(encoding="utf-8"))
        cls.manifest = json.loads(
            (ROOT / "data" / "human_labeled_names_manifest.json").read_text(
                encoding="utf-8"
            )
        )

    def test_dataset_has_reviewed_name_pairs(self) -> None:
        records = self.dataset["records"]
        self.assertEqual(len(records), 101)
        self.assertEqual(len({record["case_id"] for record in records}), len(records))
        for record in records:
            self.assertTrue(record["human_label_name"])
            self.assertTrue(record["human_label_casting"])
            self.assertTrue(record["human_label_pricing_keyword"])
            self.assertEqual(record["human_label_confidence"], "confirmed")
            self.assertNotIn("frame_path", record)

    def test_missing_initial_outputs_are_explicit_failures(self) -> None:
        records = self.dataset["records"]
        paired = [record for record in records if record["initial_name"] is not None]
        missing = [record for record in records if record["initial_name"] is None]
        self.assertEqual(len(paired), 91)
        self.assertEqual(len(missing), 10)
        self.assertTrue(
            all(record["initial_output_status"] == "candidate" for record in paired)
        )
        self.assertTrue(
            all(record["initial_output_status"] == "no_candidate" for record in missing)
        )

    def test_manifest_matches_frozen_dataset(self) -> None:
        digest = hashlib.sha256(self.dataset_path.read_bytes()).hexdigest()
        self.assertEqual(self.manifest["dataset_sha256"], digest)
        self.assertEqual(self.manifest["record_count"], 101)
        self.assertEqual(self.manifest["paired_initial_name_count"], 91)
        self.assertEqual(self.manifest["missing_initial_name_count"], 10)
        self.assertEqual(self.manifest["excluded_source_row_count"], 4)

    def test_dataset_is_not_used_as_canonical_ground_truth_yet(self) -> None:
        self.assertIn("canonical_resolution_accuracy", self.dataset["excluded_from"])
        self.assertIn("calibration_training", self.dataset["excluded_from"])
        self.assertIn("threshold_selection", self.dataset["excluded_from"])


if __name__ == "__main__":
    unittest.main()
