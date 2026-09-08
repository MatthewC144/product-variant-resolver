from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"
BATCH_ID = "fandom-priority-2-batch-02-owner-decisions-v1"


def _load_module():
    path = ROOT / "scripts" / "apply_fandom_priority_two_decisions.py"
    spec = importlib.util.spec_from_file_location(
        "fandom_priority_two_decisions_batch_two", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load priority-two decision applier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FandomPriorityTwoDecisionBatchTwoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result_path = DIRECTORY / "priority-2-batch-02-adjudicated-queue.json"
        cls.report_path = DIRECTORY / "priority-2-batch-02-adjudication-result.md"
        cls.manifest_path = (
            DIRECTORY / "priority-2-batch-02-adjudicated-queue-manifest.json"
        )
        cls.result = json.loads(cls.result_path.read_text(encoding="utf-8"))
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))
        cls.module = _load_module()

    def _build(self, decisions_path: Path | None = None):
        return self.module.apply_priority_two_decisions(
            DIRECTORY / "priority-2-batch-01-adjudicated-queue.json",
            DIRECTORY / "priority-2-batch-01-adjudicated-queue-manifest.json",
            DIRECTORY / "priority-2-batch-02-research.json",
            DIRECTORY / "priority-2-batch-02-research-manifest.json",
            decisions_path or DIRECTORY / "priority-2-batch-02-decisions.json",
            result_version="fandom-2025-priority-two-batch-02-adjudicated-v1",
            batch_label="02",
        )

    def test_cumulative_queue_has_twenty_four_completed_and_29_pending(self) -> None:
        summary = self.result["summary"]
        self.assertEqual(summary["completed_decisions"], 24)
        self.assertEqual(summary["pending_decisions"], 29)
        self.assertEqual(summary["accepted_family_merges"], 4)
        self.assertEqual(summary["accepted_new_casting_families"], 18)
        self.assertEqual(summary["held_family_decisions"], 2)
        self.assertEqual(summary["held_release_variants"], 46)
        self.assertEqual(summary["promotion_eligible_families"], 0)

    def test_batch_accepts_nine_creations_and_holds_batman(self) -> None:
        current = [
            family
            for family in self.result["families"]
            if family["reviewer_decision"].get("decision_batch_id") == BATCH_ID
        ]
        self.assertEqual(len(current), 10)
        creates = [
            family
            for family in current
            if family["reviewer_decision"]["decision"] == "create_new_casting"
        ]
        holds = [
            family
            for family in current
            if family["reviewer_decision"]["decision"] == "hold"
        ]
        self.assertEqual(len(creates), 9)
        self.assertEqual(
            [family["casting_name"] for family in holds],
            ["Batman and Robin Batmobile"],
        )

    def test_new_decisions_are_attributable_family_only_and_variant_held(self) -> None:
        for family in self.result["families"]:
            decision = family["reviewer_decision"]
            if decision.get("decision_batch_id") != BATCH_ID:
                continue
            self.assertEqual(decision["status"], "completed")
            self.assertEqual(decision["decided_by"], "project_owner")
            self.assertEqual(decision["scope"], "casting_family_only")
            self.assertEqual(decision["variant_decision"], "hold")
            self.assertIsNone(decision["target_family_id"])
            self.assertTrue(decision["reason"])
            self.assertTrue(decision["evidence_references"])
            self.assertFalse(family["promotion_eligible"])

    def test_all_prior_decisions_and_batch_history_are_preserved(self) -> None:
        priority_one = [
            family
            for family in self.result["families"]
            if family["reviewer_decision"].get("decision_batch_id")
            == "fandom-2025-priority-1-owner-confirmation-v1"
        ]
        priority_two_batch_one = [
            family
            for family in self.result["families"]
            if family["reviewer_decision"].get("decision_batch_id")
            == "fandom-priority-2-batch-01-owner-decisions-v1"
        ]
        self.assertEqual(len(priority_one), 4)
        self.assertEqual(len(priority_two_batch_one), 10)
        self.assertEqual(len(self.result["decision_batches"]), 3)
        self.assertEqual(self.result["decision_batches"][-1]["batch_id"], BATCH_ID)

    def test_changed_outcome_and_incomplete_batch_fail_closed(self) -> None:
        source = DIRECTORY / "priority-2-batch-02-decisions.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["decisions"][0]["decision"] = "hold"
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
        payload["batch_id"] = "fandom-priority-2-batch-01-owner-decisions-v1"
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "decisions.json"
            changed.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "already exists"):
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
            result_file_name="priority-2-batch-02-adjudicated-queue.json",
            report_file_name="priority-2-batch-02-adjudication-result.md",
        )
        actual = (
            self.result_path.read_text(encoding="utf-8"),
            self.manifest_path.read_text(encoding="utf-8"),
            self.report_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
