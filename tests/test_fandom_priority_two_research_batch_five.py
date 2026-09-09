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
        "fandom_priority_two_research_batch_five", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load priority-two research builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FandomPriorityTwoResearchBatchFiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.queue = json.loads(
            (DIRECTORY / "priority-2-batch-04-adjudicated-queue.json").read_text(
                encoding="utf-8"
            )
        )
        cls.research_path = DIRECTORY / "priority-2-batch-05-research.json"
        cls.report_path = DIRECTORY / "priority-2-batch-05-research.md"
        cls.manifest_path = DIRECTORY / "priority-2-batch-05-research-manifest.json"
        cls.research = json.loads(cls.research_path.read_text(encoding="utf-8"))
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))
        cls.module = _load_module()

    def _build(self):
        return self.module.build_research(
            DIRECTORY / "priority-2-batch-04-adjudicated-queue.json",
            DIRECTORY / "priority-2-batch-04-adjudicated-queue-manifest.json",
            DIRECTORY / "priority-2-batch-05-source-notes.json",
            batch_version="fandom-2025-priority-two-research-batch-05-v1",
            batch_label="05",
            batch_size=9,
        )

    def test_selects_exactly_the_nine_remaining_pending_families(self) -> None:
        expected = [
            family["family_review_id"]
            for family in self.queue["families"]
            if family["priority"] == 2
            and family["reviewer_decision"]["status"] == "pending"
        ]
        actual = [packet["family_review_id"] for packet in self.research["packets"]]
        self.assertEqual(len(expected), 9)
        self.assertEqual(actual, expected)
        self.assertEqual(self.research["summary"]["represented_wiki_rows"], 13)
        self.assertEqual(
            self.research["selection_rule"],
            "first 9 pending priority-2 families in adjudicated queue order",
        )

    def test_recommends_six_creations_and_three_named_holds(self) -> None:
        decisions = {
            packet["casting_name"]: packet["machine_recommendation"]["family_decision"]
            for packet in self.research["packets"]
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

    def test_power_wheels_release_name_is_not_a_new_casting(self) -> None:
        packet = next(
            item
            for item in self.research["packets"]
            if item["casting_name"] == "Power Wheels Dune Racer"
        )
        wiki = packet["research_evidence"]["wiki_casting_page"]
        self.assertEqual(wiki["page_classification"], "renamed_existing_casting")
        self.assertEqual(wiki["url"], "https://hotwheels.fandom.com/wiki/Bogzilla")
        self.assertIn("FJV61", wiki["observed_claim"])
        self.assertIn("duplicate family", packet["machine_recommendation"]["reason"])

    def test_same_name_multi_tool_cases_are_held(self) -> None:
        packets = {item["casting_name"]: item for item in self.research["packets"]}
        standard = packets["Standard Kart"]["research_evidence"]["wiki_casting_page"]
        self.assertEqual(standard["page_classification"], "multi_casting_page")
        self.assertIn("GBG26", standard["observed_claim"])
        self.assertIn("GRX17", standard["observed_claim"])

        nissan = packets["Nissan Skyline GT-R (BNR32)"]["research_evidence"]
        self.assertEqual(
            nissan["wiki_casting_page"]["page_classification"],
            "homonymous_castings",
        )
        related = nissan["wiki_casting_page"]["related_casting_pages"]
        self.assertEqual(len(related), 1)
        self.assertIn("JJY54", related[0]["distinction"])
        self.assertIn("RLC", related[0]["url"])

    def test_creation_recommendations_have_two_hosts_and_keep_lineage_context(self) -> None:
        packets = {item["casting_name"]: item for item in self.research["packets"]}
        for packet in packets.values():
            if packet["machine_recommendation"]["family_decision"] != "create_new_casting":
                continue
            evidence = packet["research_evidence"]
            self.assertEqual(
                evidence["wiki_casting_page"]["page_classification"], "single_casting"
            )
            self.assertGreaterEqual(evidence["independent_source_count"], 1)
            self.assertGreaterEqual(len(evidence["distinct_source_hosts"]), 2)

        self.assertIn(
            "retools",
            packets["The Vanster"]["research_evidence"]["wiki_casting_page"][
                "observed_claim"
            ],
        )
        self.assertTrue(
            packets["Twin Mill Gen-E"]["research_evidence"]["wiki_casting_page"][
                "related_casting_pages"
            ]
        )
        self.assertTrue(
            packets["X-34 Landspeeder"]["research_evidence"]["wiki_casting_page"][
                "related_casting_pages"
            ]
        )

    def test_outputs_are_pending_frozen_and_deterministically_reproducible(self) -> None:
        for packet in self.research["packets"]:
            self.assertEqual(packet["reviewer_confirmation"]["status"], "pending")
            self.assertEqual(
                packet["machine_recommendation"]["variant_decision"], "hold"
            )
            self.assertFalse(packet["promotion_eligible"])
        self.assertEqual(self.research["summary"]["confirmed_reviewer_decisions"], 0)
        self.assertEqual(self.research["summary"]["promotion_eligible_families"], 0)
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
            research_file_name="priority-2-batch-05-research.json",
            report_file_name="priority-2-batch-05-research.md",
        )
        actual = (
            self.research_path.read_text(encoding="utf-8"),
            self.manifest_path.read_text(encoding="utf-8"),
            self.report_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
