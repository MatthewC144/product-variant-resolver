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
    path = ROOT / "scripts" / "build_fandom_priority_two_research.py"
    spec = importlib.util.spec_from_file_location("fandom_priority_two_research", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load priority-two research builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FandomPriorityTwoResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.research_path = DIRECTORY / "priority-2-batch-01-research.json"
        cls.report_path = DIRECTORY / "priority-2-batch-01-research.md"
        cls.manifest_path = DIRECTORY / "priority-2-batch-01-research-manifest.json"
        cls.research = json.loads(cls.research_path.read_text(encoding="utf-8"))
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))
        cls.module = _load_module()

    def _build(self):
        return self.module.build_research(
            DIRECTORY / "adjudicated-queue.json",
            DIRECTORY / "adjudicated-queue-manifest.json",
            DIRECTORY / "priority-2-batch-01-source-notes.json",
        )

    def test_batch_is_first_ten_pending_priority_two_families(self) -> None:
        queue = json.loads((DIRECTORY / "adjudicated-queue.json").read_text())
        expected = [
            family["family_review_id"]
            for family in queue["families"]
            if family["priority"] == 2
            and family["reviewer_decision"]["status"] == "pending"
        ][:10]
        actual = [packet["family_review_id"] for packet in self.research["packets"]]
        self.assertEqual(actual, expected)

    def test_nine_creates_and_one_disambiguation_hold_are_proposed(self) -> None:
        summary = self.research["summary"]
        self.assertEqual(summary["researched_families"], 10)
        self.assertEqual(summary["represented_wiki_rows"], 19)
        self.assertEqual(summary["proposed_new_castings"], 9)
        self.assertEqual(summary["proposed_holds"], 1)
        held = [
            packet
            for packet in self.research["packets"]
            if packet["machine_recommendation"]["family_decision"] == "hold"
        ]
        self.assertEqual([packet["casting_name"] for packet in held], ["'55 Chevy"])
        self.assertEqual(
            held[0]["research_evidence"]["wiki_casting_page"]["page_classification"],
            "disambiguation",
        )

    def test_create_recommendations_have_independent_exact_name_evidence(self) -> None:
        for packet in self.research["packets"]:
            if packet["machine_recommendation"]["family_decision"] != "create_new_casting":
                continue
            evidence = packet["research_evidence"]
            self.assertEqual(
                evidence["wiki_casting_page"]["page_classification"],
                "single_casting",
            )
            self.assertGreaterEqual(evidence["independent_source_count"], 1)
            self.assertIn("hotwheels.fandom.com", evidence["distinct_source_hosts"])
            self.assertGreaterEqual(len(evidence["distinct_source_hosts"]), 2)
            self.assertTrue(
                all(
                    source["confirms_exact_casting_name"]
                    for source in evidence["independent_sources"]
                )
            )

    def test_research_does_not_complete_or_promote_decisions(self) -> None:
        for packet in self.research["packets"]:
            self.assertEqual(packet["reviewer_confirmation"]["status"], "pending")
            self.assertEqual(
                packet["machine_recommendation"]["variant_decision"], "hold"
            )
            self.assertFalse(packet["promotion_eligible"])
        self.assertEqual(self.research["summary"]["confirmed_reviewer_decisions"], 0)
        self.assertEqual(self.research["summary"]["promotion_eligible_families"], 0)

    def test_invalid_independent_source_fails_closed(self) -> None:
        notes_path = DIRECTORY / "priority-2-batch-01-source-notes.json"
        payload = json.loads(notes_path.read_text(encoding="utf-8"))
        payload["families"][0]["independent_sources"][0]["url"] = (
            "https://hotwheels.fandom.com/wiki/1988_Jeep_Wagoneer"
        )
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "source-notes.json"
            changed.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cannot use the Wiki host"):
                self.module.build_research(
                    DIRECTORY / "adjudicated-queue.json",
                    DIRECTORY / "adjudicated-queue-manifest.json",
                    changed,
                )

    def test_outputs_are_frozen_and_deterministically_reproducible(self) -> None:
        self.assertEqual(
            self.manifest["research_sha256"],
            hashlib.sha256(self.research_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.manifest["report_sha256"],
            hashlib.sha256(self.report_path.read_bytes()).hexdigest(),
        )
        expected = self.module.expected_outputs(*self._build())
        actual = (
            self.research_path.read_text(encoding="utf-8"),
            self.manifest_path.read_text(encoding="utf-8"),
            self.report_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
