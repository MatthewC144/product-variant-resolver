from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"


def _load_module():
    path = ROOT / "scripts" / "apply_fandom_priority_two_decisions.py"
    spec = importlib.util.spec_from_file_location("fandom_priority_two_decisions", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load priority-two decision applier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FandomPriorityTwoDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result_path = DIRECTORY / "priority-2-batch-01-adjudicated-queue.json"
        cls.report_path = DIRECTORY / "priority-2-batch-01-adjudication-result.md"
        cls.manifest_path = (
            DIRECTORY / "priority-2-batch-01-adjudicated-queue-manifest.json"
        )
        cls.result = json.loads(cls.result_path.read_text(encoding="utf-8"))
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))
        cls.module = _load_module()

    def _build(self):
        return self.module.apply_priority_two_decisions(
            DIRECTORY / "adjudicated-queue.json",
            DIRECTORY / "adjudicated-queue-manifest.json",
            DIRECTORY / "priority-2-batch-01-research.json",
            DIRECTORY / "priority-2-batch-01-research-manifest.json",
            DIRECTORY / "priority-2-batch-01-decisions.json",
        )

    def test_cumulative_queue_has_fourteen_completed_and_39_pending(self) -> None:
        summary = self.result["summary"]
        self.assertEqual(summary["completed_decisions"], 14)
        self.assertEqual(summary["pending_decisions"], 39)
        self.assertEqual(summary["accepted_family_merges"], 4)
        self.assertEqual(summary["accepted_new_casting_families"], 9)
        self.assertEqual(summary["held_family_decisions"], 1)
        self.assertEqual(summary["held_release_variants"], 28)
        self.assertEqual(summary["promotion_eligible_families"], 0)

    def test_batch_accepts_nine_creations_and_holds_55_chevy(self) -> None:
        current = [
            family
            for family in self.result["families"]
            if family["reviewer_decision"].get("decision_batch_id")
            == "fandom-priority-2-batch-01-owner-decisions-v1"
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
        self.assertEqual([family["casting_name"] for family in holds], ["'55 Chevy"])

    def test_all_new_decisions_are_attributable_family_only_and_variant_held(self) -> None:
        for family in self.result["families"]:
            decision = family["reviewer_decision"]
            if decision.get("decision_batch_id") != (
                "fandom-priority-2-batch-01-owner-decisions-v1"
            ):
                continue
            self.assertEqual(decision["status"], "completed")
            self.assertEqual(decision["decided_by"], "project_owner")
            self.assertEqual(decision["scope"], "casting_family_only")
            self.assertEqual(decision["variant_decision"], "hold")
            self.assertIsNone(decision["target_family_id"])
            self.assertTrue(decision["reason"])
            self.assertTrue(decision["evidence_references"])
            self.assertFalse(family["promotion_eligible"])

    def test_wrong_decision_and_incomplete_batch_fail_closed(self) -> None:
        decisions_path = DIRECTORY / "priority-2-batch-01-decisions.json"
        payload = json.loads(decisions_path.read_text(encoding="utf-8"))
        payload["decisions"][0]["decision"] = "hold"
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "decisions.json"
            changed.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "differs from the approved"):
                self.module.apply_priority_two_decisions(
                    DIRECTORY / "adjudicated-queue.json",
                    DIRECTORY / "adjudicated-queue-manifest.json",
                    DIRECTORY / "priority-2-batch-01-research.json",
                    DIRECTORY / "priority-2-batch-01-research-manifest.json",
                    changed,
                )
        payload = json.loads(decisions_path.read_text(encoding="utf-8"))
        payload["decisions"].pop()
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "decisions.json"
            changed.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "every research packet"):
                self.module.apply_priority_two_decisions(
                    DIRECTORY / "adjudicated-queue.json",
                    DIRECTORY / "adjudicated-queue-manifest.json",
                    DIRECTORY / "priority-2-batch-01-research.json",
                    DIRECTORY / "priority-2-batch-01-research-manifest.json",
                    changed,
                )

    def test_prior_priority_one_decisions_and_history_are_preserved(self) -> None:
        prior = [
            family
            for family in self.result["families"]
            if family["reviewer_decision"].get("decision_batch_id")
            == "fandom-2025-priority-1-owner-confirmation-v1"
        ]
        self.assertEqual(len(prior), 4)
        self.assertTrue(
            all(
                family["reviewer_decision"]["decision"] == "merge_existing_family"
                for family in prior
            )
        )
        self.assertEqual(len(self.result["decision_batches"]), 2)

    def test_outputs_are_frozen_and_deterministically_reproducible(self) -> None:
        self.assertEqual(
            self.manifest["result_sha256"],
            hashlib.sha256(self.result_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.manifest["report_sha256"],
            hashlib.sha256(self.report_path.read_bytes()).hexdigest(),
        )
        expected = self.module.expected_outputs(*self._build())
        actual = (
            self.result_path.read_text(encoding="utf-8"),
            self.manifest_path.read_text(encoding="utf-8"),
            self.report_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
