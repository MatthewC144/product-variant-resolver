from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"


def _load_module():
    path = ROOT / "scripts" / "review_fandom_catalog_pilot.py"
    spec = importlib.util.spec_from_file_location("fandom_catalog_review", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Fandom review builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FandomCatalogReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.review_path = DIRECTORY / "review.json"
        cls.manifest_path = DIRECTORY / "review-manifest.json"
        cls.review = json.loads(cls.review_path.read_text(encoding="utf-8"))
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))

    def test_all_staging_rows_are_reviewed_but_held(self) -> None:
        rows = self.review["reviews"]
        self.assertEqual(len(rows), 100)
        self.assertEqual(len({row["source_record_id"] for row in rows}), 100)
        self.assertEqual([row["source_row"] for row in rows], list(range(1, 101)))
        self.assertTrue(all(row["promotion_eligible"] is False for row in rows))
        self.assertTrue(
            all(row["promotion_decision"] == "hold_for_human_review" for row in rows)
        )
        self.assertTrue(all(row["canonical_uuid"] is None for row in rows))
        self.assertTrue(all(row["canonical_id"] is None for row in rows))

    def test_current_exact_match_counts_are_frozen(self) -> None:
        self.assertEqual(
            self.manifest["row_match_status_counts"],
            {
                "exact_human_casting_family": 9,
                "no_exact_casting_family": 91,
            },
        )
        self.assertEqual(
            self.manifest["family_match_status_counts"],
            {
                "exact_human_casting_family": 4,
                "no_exact_casting_family": 49,
            },
        )
        self.assertEqual(self.manifest["unique_staging_casting_family_count"], 53)

    def test_exact_human_candidates_are_explanatory_not_promotions(self) -> None:
        matched = [
            row
            for row in self.review["reviews"]
            if row["match_status"] == "exact_human_casting_family"
        ]
        self.assertEqual(
            {row["casting_name"] for row in matched},
            {"'67 Chevy C10", "Purple Passion", "Subaru BRZ", "Tesla Model S Plaid"},
        )
        self.assertTrue(all(row["human_casting_candidate_ids"] for row in matched))
        self.assertTrue(all(row["human_variant_candidate_ids"] for row in matched))
        self.assertTrue(all(not row["canonical_family_candidate_ids"] for row in matched))

    def test_policy_disables_fuzzy_identifier_only_and_automatic_promotion(self) -> None:
        policy = self.review["policy"]
        self.assertFalse(policy["fuzzy_matching"])
        self.assertFalse(policy["identifier_only_matching"])
        self.assertFalse(policy["automatic_promotion"])
        self.assertEqual(self.manifest["canonical_promotion_count"], 0)

    def test_manifest_freezes_inputs_output_and_deterministic_build(self) -> None:
        self.assertEqual(
            self.manifest["review_sha256"],
            hashlib.sha256(self.review_path.read_bytes()).hexdigest(),
        )
        module = _load_module()
        paths = (
            DIRECTORY / "normalized.json",
            ROOT / "data" / "catalog.json",
            ROOT / "data" / "human_backed_catalog.json",
        )
        first = module.build_review(*paths)
        second = module.build_review(*paths)
        self.assertEqual(first, second)
        review_text, manifest_text = module.expected_outputs(*first)
        self.assertEqual(review_text, self.review_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest_text, self.manifest_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
