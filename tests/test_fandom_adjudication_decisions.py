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
    path = ROOT / "scripts" / "apply_fandom_adjudication_decisions.py"
    spec = importlib.util.spec_from_file_location("fandom_adjudication_decisions", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Fandom adjudication decision applier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FandomAdjudicationDecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result_path = DIRECTORY / "adjudicated-queue.json"
        cls.report_path = DIRECTORY / "adjudication-result.md"
        cls.manifest_path = DIRECTORY / "adjudicated-queue-manifest.json"
        cls.result = json.loads(cls.result_path.read_text(encoding="utf-8"))
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))
        cls.module = _load_module()

    def _build(self):
        return self.module.apply_decisions(
            DIRECTORY / "adjudication-queue.json",
            DIRECTORY / "adjudication-queue-manifest.json",
            DIRECTORY / "priority-1-evidence.json",
            DIRECTORY / "priority-1-evidence-manifest.json",
            DIRECTORY / "priority-1-decisions.json",
        )

    def test_four_family_merges_are_completed_and_49_remain_pending(self) -> None:
        summary = self.result["summary"]
        self.assertEqual(summary["completed_decisions"], 4)
        self.assertEqual(summary["accepted_family_merges"], 4)
        self.assertEqual(summary["pending_decisions"], 49)
        self.assertEqual(summary["held_release_variants"], 9)
        self.assertEqual(summary["promotion_eligible_families"], 0)

    def test_completed_decisions_are_attributable_family_only_and_variant_held(self) -> None:
        completed = [
            family
            for family in self.result["families"]
            if family["reviewer_decision"]["status"] == "completed"
        ]
        self.assertEqual(len(completed), 4)
        for family in completed:
            decision = family["reviewer_decision"]
            self.assertEqual(decision["decision"], "merge_existing_family")
            self.assertEqual(decision["scope"], "casting_family_only")
            self.assertEqual(decision["variant_decision"], "hold")
            self.assertEqual(decision["decided_by"], "project_owner")
            self.assertTrue(decision["reason"])
            self.assertTrue(decision["evidence_references"])
            self.assertFalse(family["promotion_eligible"])

    def test_merge_targets_are_exact_human_candidates(self) -> None:
        for family in self.result["families"]:
            decision = family["reviewer_decision"]
            if decision["status"] != "completed":
                continue
            self.assertIn(
                decision["target_family_id"],
                family["pre_review"]["human_casting_candidate_ids"],
            )

    def test_invalid_merge_target_fails_closed(self) -> None:
        decisions_path = DIRECTORY / "priority-1-decisions.json"
        payload = json.loads(decisions_path.read_text(encoding="utf-8"))
        payload["decisions"][0]["target_family_id"] = "human-hot-wheels-wrong-target"
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "decisions.json"
            changed.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not an exact"):
                self.module.apply_decisions(
                    DIRECTORY / "adjudication-queue.json",
                    DIRECTORY / "adjudication-queue-manifest.json",
                    DIRECTORY / "priority-1-evidence.json",
                    DIRECTORY / "priority-1-evidence-manifest.json",
                    changed,
                )

    def test_outputs_are_frozen_and_deterministically_reproducible(self) -> None:
        self.assertEqual(
            self.manifest["result_sha256"],
            hashlib.sha256(self.result_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.manifest["report_sha256"],
            hashlib.sha256(self.report_path.read_bytes()).hexdigest(),
        )
        built = self._build()
        expected = self.module.expected_outputs(*built)
        actual = (
            self.result_path.read_text(encoding="utf-8"),
            self.manifest_path.read_text(encoding="utf-8"),
            self.report_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
