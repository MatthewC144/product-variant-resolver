from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"


def _load_module():
    path = ROOT / "scripts" / "build_fandom_adjudication_queue.py"
    spec = importlib.util.spec_from_file_location("fandom_adjudication_queue", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Fandom adjudication queue builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FandomAdjudicationQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.queue_path = DIRECTORY / "adjudication-queue.json"
        cls.worksheet_path = DIRECTORY / "adjudication-queue.md"
        cls.manifest_path = DIRECTORY / "adjudication-queue-manifest.json"
        cls.queue = json.loads(cls.queue_path.read_text(encoding="utf-8"))
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))

    def test_queue_groups_every_source_row_exactly_once(self) -> None:
        families = self.queue["families"]
        rows = [row for family in families for row in family["source_rows"]]
        self.assertEqual(len(families), 53)
        self.assertEqual(len(rows), 100)
        self.assertEqual(len({row["source_record_id"] for row in rows}), 100)
        self.assertEqual({row["source_row"] for row in rows}, set(range(1, 101)))
        self.assertEqual(len({item["family_review_id"] for item in families}), 53)

    def test_existing_candidates_are_prioritized_without_becoming_decisions(self) -> None:
        priority_one = [item for item in self.queue["families"] if item["priority"] == 1]
        self.assertEqual(len(priority_one), 4)
        self.assertEqual(
            {item["casting_name"] for item in priority_one},
            {"'67 Chevy C10", "Purple Passion", "Subaru BRZ", "Tesla Model S Plaid"},
        )
        self.assertTrue(
            all(item["pre_review"]["human_casting_candidate_ids"] for item in priority_one)
        )
        self.assertTrue(
            all(
                item["pre_review"]["suggested_action"]
                == "merge_existing_family_candidate"
                for item in priority_one
            )
        )

    def test_all_decisions_are_pending_and_not_promotion_eligible(self) -> None:
        families = self.queue["families"]
        self.assertTrue(
            all(item["reviewer_decision"]["status"] == "pending" for item in families)
        )
        self.assertTrue(
            all(item["reviewer_decision"]["decision"] is None for item in families)
        )
        self.assertTrue(all(item["promotion_eligible"] is False for item in families))
        self.assertEqual(self.queue["summary"]["completed_decisions"], 0)
        self.assertEqual(self.queue["summary"]["promotion_eligible_families"], 0)

    def test_decision_contract_requires_actor_reason_time_and_evidence(self) -> None:
        contract = self.queue["decision_contract"]
        self.assertEqual(
            contract["allowed_decisions"],
            ["merge_existing_family", "create_new_casting", "hold", "reject"],
        )
        self.assertEqual(
            contract["completed_decision_requires"],
            ["decided_by", "decided_at", "reason", "evidence_references"],
        )
        self.assertIn("independent source confirmation", contract["create_new_casting"])
        self.assertFalse(contract["pending_items_are_promotion_eligible"])

    def test_manifest_and_worksheet_are_frozen_and_reproducible(self) -> None:
        self.assertEqual(
            self.manifest["queue_sha256"],
            hashlib.sha256(self.queue_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.manifest["worksheet_sha256"],
            hashlib.sha256(self.worksheet_path.read_bytes()).hexdigest(),
        )
        module = _load_module()
        built = module.build_queue(
            DIRECTORY / "review.json", DIRECTORY / "review-manifest.json"
        )
        expected = module.expected_outputs(*built)
        actual = (
            self.queue_path.read_text(encoding="utf-8"),
            self.manifest_path.read_text(encoding="utf-8"),
            self.worksheet_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
