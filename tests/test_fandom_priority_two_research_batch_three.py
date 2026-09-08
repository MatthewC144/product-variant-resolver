from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"


def _load_module():
    path = ROOT / "scripts" / "build_fandom_priority_two_research.py"
    spec = importlib.util.spec_from_file_location(
        "fandom_priority_two_research_batch_three", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load priority-two research builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FandomPriorityTwoResearchBatchThreeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.research_path = DIRECTORY / "priority-2-batch-03-research.json"
        cls.report_path = DIRECTORY / "priority-2-batch-03-research.md"
        cls.manifest_path = DIRECTORY / "priority-2-batch-03-research-manifest.json"
        cls.research = json.loads(cls.research_path.read_text(encoding="utf-8"))
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))
        cls.module = _load_module()

    def _build(self):
        return self.module.build_research(
            DIRECTORY / "priority-2-batch-02-adjudicated-queue.json",
            DIRECTORY / "priority-2-batch-02-adjudicated-queue-manifest.json",
            DIRECTORY / "priority-2-batch-03-source-notes.json",
            batch_version="fandom-2025-priority-two-research-batch-03-v1",
            batch_label="03",
        )

    def test_batch_is_next_ten_pending_families_after_batch_two_decisions(self) -> None:
        queue = json.loads(
            (DIRECTORY / "priority-2-batch-02-adjudicated-queue.json").read_text()
        )
        expected = [
            family["family_review_id"]
            for family in queue["families"]
            if family["priority"] == 2
            and family["reviewer_decision"]["status"] == "pending"
        ][:10]
        actual = [packet["family_review_id"] for packet in self.research["packets"]]
        self.assertEqual(actual, expected)
        self.assertNotIn("fandom-family-1555c05ceeb491cb", actual)

    def test_all_ten_families_receive_create_recommendations(self) -> None:
        summary = self.research["summary"]
        self.assertEqual(summary["researched_families"], 10)
        self.assertEqual(summary["represented_wiki_rows"], 18)
        self.assertEqual(summary["proposed_new_castings"], 10)
        self.assertEqual(summary["proposed_holds"], 0)

    def test_create_recommendations_have_two_distinct_source_hosts(self) -> None:
        for packet in self.research["packets"]:
            evidence = packet["research_evidence"]
            self.assertEqual(
                evidence["wiki_casting_page"]["page_classification"],
                "single_casting",
            )
            self.assertGreaterEqual(evidence["independent_source_count"], 1)
            self.assertIn("hotwheels.fandom.com", evidence["distinct_source_hosts"])
            self.assertGreaterEqual(len(evidence["distinct_source_hosts"]), 2)

    def test_related_but_differently_named_castings_keep_their_distinction(self) -> None:
        packets = {packet["casting_name"]: packet for packet in self.research["packets"]}
        fiat_related = packets["Fiat 500e"]["research_evidence"][
            "wiki_casting_page"
        ]["related_casting_pages"]
        hirohata_related = packets["Hirohata Merc"]["research_evidence"][
            "wiki_casting_page"
        ]["related_casting_pages"]
        self.assertIn("different casting lineage", fiat_related[0]["distinction"])
        self.assertIn("'51 Merc", hirohata_related[0]["distinction"])
        self.assertEqual(
            packets["Hirohata Merc"]["machine_recommendation"]["family_decision"],
            "create_new_casting",
        )

    def test_every_recommendation_remains_unreviewed_and_non_promotable(self) -> None:
        for packet in self.research["packets"]:
            self.assertEqual(packet["reviewer_confirmation"]["status"], "pending")
            self.assertEqual(
                packet["machine_recommendation"]["variant_decision"], "hold"
            )
            self.assertFalse(packet["promotion_eligible"])
        self.assertEqual(self.research["summary"]["confirmed_reviewer_decisions"], 0)
        self.assertEqual(self.research["summary"]["promotion_eligible_families"], 0)

    def test_outputs_are_frozen_and_deterministically_reproducible(self) -> None:
        self.assertEqual(
            self.manifest["research_sha256"],
            hashlib.sha256(self.research_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.manifest["report_sha256"],
            hashlib.sha256(self.report_path.read_bytes()).hexdigest(),
        )
        expected = self.module.expected_outputs(
            *self._build(),
            research_file_name="priority-2-batch-03-research.json",
            report_file_name="priority-2-batch-03-research.md",
        )
        actual = (
            self.research_path.read_text(encoding="utf-8"),
            self.manifest_path.read_text(encoding="utf-8"),
            self.report_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
