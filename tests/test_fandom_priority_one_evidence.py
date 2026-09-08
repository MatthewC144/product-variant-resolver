from __future__ import annotations

import hashlib
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECTORY = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"


def _load_module():
    path = ROOT / "scripts" / "build_fandom_priority_one_evidence.py"
    spec = importlib.util.spec_from_file_location("fandom_priority_one_evidence", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Fandom priority-one evidence builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FandomPriorityOneEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.packet_path = DIRECTORY / "priority-1-evidence.json"
        cls.report_path = DIRECTORY / "priority-1-evidence.md"
        cls.manifest_path = DIRECTORY / "priority-1-evidence-manifest.json"
        cls.payload = json.loads(cls.packet_path.read_text(encoding="utf-8"))
        cls.manifest = json.loads(cls.manifest_path.read_text(encoding="utf-8"))

    def test_four_packets_cover_nine_priority_one_wiki_rows(self) -> None:
        packets = self.payload["packets"]
        rows = [row for packet in packets for row in packet["wiki_evidence"]["source_rows"]]
        self.assertEqual(len(packets), 4)
        self.assertEqual(len(rows), 9)
        self.assertEqual(len({row["source_record_id"] for row in rows}), 9)
        self.assertEqual(
            {packet["casting_name"] for packet in packets},
            {"'67 Chevy C10", "Purple Passion", "Subaru BRZ", "Tesla Model S Plaid"},
        )

    def test_each_packet_has_one_exact_human_family_target(self) -> None:
        for packet in self.payload["packets"]:
            self.assertEqual(
                packet["family_name_match"], "exact_normalized_brand_and_casting"
            )
            self.assertTrue(packet["target_human_casting_id"].startswith("human-hot-wheels-"))
            self.assertTrue(packet["human_evidence"]["source_case_ids"])
            self.assertTrue(packet["human_evidence"]["variants"])

    def test_family_merge_is_recommended_but_every_variant_is_held(self) -> None:
        for packet in self.payload["packets"]:
            recommendation = packet["machine_recommendation"]
            self.assertEqual(recommendation["family_decision"], "merge_existing_family")
            self.assertEqual(recommendation["scope"], "casting_family_only")
            self.assertEqual(recommendation["variant_decision"], "hold")
            self.assertFalse(packet["comparison"]["variant_identity_verified"])
            self.assertFalse(packet["promotion_eligible"])

    def test_subaru_zamac_is_visible_as_evidence_not_variant_confirmation(self) -> None:
        subaru = next(
            packet for packet in self.payload["packets"] if packet["casting_name"] == "Subaru BRZ"
        )
        self.assertEqual(subaru["comparison"]["shared_explicit_variant_tokens"], ["zamac"])
        self.assertFalse(subaru["comparison"]["series_labels_exact"])
        self.assertEqual(subaru["reviewer_confirmation"]["status"], "pending")
        self.assertIsNone(subaru["reviewer_confirmation"]["accept_family_recommendation"])

    def test_outputs_are_frozen_and_deterministically_reproducible(self) -> None:
        self.assertEqual(
            self.manifest["packet_sha256"],
            hashlib.sha256(self.packet_path.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.manifest["report_sha256"],
            hashlib.sha256(self.report_path.read_bytes()).hexdigest(),
        )
        module = _load_module()
        built = module.build_packets(
            DIRECTORY / "adjudication-queue.json",
            DIRECTORY / "adjudication-queue-manifest.json",
            ROOT / "data" / "human_backed_catalog.json",
        )
        expected = module.expected_outputs(*built)
        actual = (
            self.packet_path.read_text(encoding="utf-8"),
            self.manifest_path.read_text(encoding="utf-8"),
            self.report_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()
