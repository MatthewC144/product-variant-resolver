from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"
BATCH_ID = "fandom-priority-2-batch-05-owner-decisions-v1"


def _load_module():
    path = ROOT / "scripts" / "apply_fandom_priority_two_decisions.py"
    spec = importlib.util.spec_from_file_location(
        "fandom_priority_two_decisions_batch_five", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load priority-two decision applier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FandomPriorityTwoDecisionBatchFiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result_path = DIRECTORY / "priority-2-batch-05-adjudicated-queue.json"
        cls.report_path = DIRECTORY / "priority-2-batch-05-adjudication-result.md"
        cls.manifest_path = (
            DIRECTORY / "priority-2-batch-05-adjudicated-queue-manifest.json"
        )
        cls.result = json.loads(cls.result_path.read_text(encoding="utf-8"))
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))
        cls.module = _load_module()

    def _build(self, decisions_path: Path | None = None):
        return self.module.apply_priority_two_decisions(
            DIRECTORY / "priority-2-batch-04-adjudicated-queue.json",
            DIRECTORY / "priority-2-batch-04-adjudicated-queue-manifest.json",
            DIRECTORY / "priority-2-batch-05-research.json",
            DIRECTORY / "priority-2-batch-05-research-manifest.json",
            decisions_path or DIRECTORY / "priority-2-batch-05-decisions.json",
            result_version="fandom-2025-priority-two-batch-05-adjudicated-v1",
            batch_label="05",
        )

    def test_queue_is_fully_adjudicated_with_all_variants_held(self) -> None:
        summary = self.result["summary"]
        self.assertEqual(self.result["status"], "adjudicated")
        self.assertEqual(summary["completed_decisions"], 53)
        self.assertEqual(summary["pending_decisions"], 0)
        self.assertEqual(summary["accepted_family_merges"], 4)
        self.assertEqual(summary["accepted_new_casting_families"], 42)
        self.assertEqual(summary["held_family_decisions"], 7)
        self.assertEqual(summary["held_release_variants"], 100)
        self.assertEqual(summary["promotion_eligible_families"], 0)

    def test_batch_accepts_exactly_six_creations_and_three_holds(self) -> None:
        current = [
            family
            for family in self.result["families"]
            if family["reviewer_decision"].get("decision_batch_id") == BATCH_ID
        ]
        self.assertEqual(len(current), 9)
        decisions = {
            family["casting_name"]: family["reviewer_decision"]["decision"]
            for family in current
        }
        self.assertEqual(
            sum(value == "create_new_casting" for value in decisions.values()), 6
        )
        self.assertEqual(
            {name for name, value in decisions.items() if value == "hold"},
            {
                "Nissan Skyline GT-R (BNR32)",
                "Power Wheels Dune Racer",
                "Standard Kart",
            },
        )
        self.assertEqual(sum(family["source_row_count"] for family in current), 13)

    def test_final_decisions_are_attributable_family_only_and_variant_held(self) -> None:
        for family in self.result["families"]:
            decision = family["reviewer_decision"]
            self.assertEqual(decision["status"], "completed")
            self.assertEqual(decision["scope"], "casting_family_only")
            self.assertEqual(decision["variant_decision"], "hold")
            self.assertFalse(family["promotion_eligible"])
            if decision.get("decision_batch_id") != BATCH_ID:
                continue
            self.assertEqual(decision["decided_by"], "project_owner")
            self.assertIsNone(decision["target_family_id"])
            self.assertTrue(decision["reason"])
            self.assertIn(
                "priority-2-batch-05-research.json#" + family["family_review_id"],
                decision["evidence_references"],
            )
            self.assertGreaterEqual(len(decision["evidence_references"]), 3)

    def test_all_prior_decisions_and_six_history_events_are_preserved(self) -> None:
        prior_batch_ids = {
            "fandom-2025-priority-1-owner-confirmation-v1": 4,
            "fandom-priority-2-batch-01-owner-decisions-v1": 10,
            "fandom-priority-2-batch-02-owner-decisions-v1": 10,
            "fandom-priority-2-batch-03-owner-decisions-v1": 10,
            "fandom-priority-2-batch-04-owner-decisions-v1": 10,
        }
        for batch_id, expected_count in prior_batch_ids.items():
            actual = [
                family
                for family in self.result["families"]
                if family["reviewer_decision"].get("decision_batch_id") == batch_id
            ]
            self.assertEqual(len(actual), expected_count)
        self.assertEqual(len(self.result["decision_batches"]), 6)
        self.assertEqual(self.result["decision_batches"][-1]["batch_id"], BATCH_ID)

    def test_changed_incomplete_duplicate_and_widened_batches_fail_closed(self) -> None:
        source = DIRECTORY / "priority-2-batch-05-decisions.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["decisions"][0]["decision"] = "create_new_casting"
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "decisions.json"
            changed.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "differs from the approved"):
                self._build(changed)

        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["decisions"].pop()
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "decisions.json"
            changed.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "every research packet"):
                self._build(changed)

        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["batch_id"] = "fandom-priority-2-batch-04-owner-decisions-v1"
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "decisions.json"
            changed.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "already exists"):
                self._build(changed)

        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["decisions"][0]["variant_decision"] = "create"
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "decisions.json"
            changed.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "release variants must remain held"):
                self._build(changed)

    def test_outputs_are_frozen_and_deterministically_reproducible(self) -> None:
        self.assertEqual(
            self.manifest["result_sha256"],
            hashlib.sha256(self.result_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.manifest["report_sha256"],
            hashlib.sha256(self.report_path.read_bytes()).hexdigest(),
        )
        expected = self.module.expected_outputs(
            *self._build(),
            result_file_name="priority-2-batch-05-adjudicated-queue.json",
            report_file_name="priority-2-batch-05-adjudication-result.md",
        )
        actual = (
            self.result_path.read_text(encoding="utf-8"),
            self.manifest_path.read_text(encoding="utf-8"),
            self.report_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
