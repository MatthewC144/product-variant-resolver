from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def _load_planner() -> ModuleType:
    path = ROOT / "scripts/plan_release_field_evidence_review.py"
    spec = importlib.util.spec_from_file_location("plan_release_field_evidence_review", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PLANNER = _load_planner()
DEFAULT_OUTPUT = PLANNER.DEFAULT_OUTPUT
NORMALIZED_PATH = PLANNER.NORMALIZED_PATH
QUEUE_PATH = PLANNER.QUEUE_PATH
REVIEW_PATH = PLANNER.REVIEW_PATH
build_plan = PLANNER.build_plan
check = PLANNER.check
publish = PLANNER.publish


class ReleaseFieldEvidenceReviewPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = build_plan()

    def test_exact_source_membership_and_separate_observation_identity(self) -> None:
        records = self.plan["records"]
        self.assertEqual(len(records), 100)
        self.assertEqual(len({record["source_record_id"] for record in records}), 100)
        self.assertEqual(len({record["observation_id"] for record in records}), 100)
        self.assertTrue(
            all(record["source_record_id"] != record["observation_id"] for record in records)
        )

    def test_unknown_release_fields_are_not_inferred(self) -> None:
        for record in self.plan["records"]:
            fields = record["field_evidence"]
            for name in (
                "color",
                "wheel_type",
                "tampo_description",
                "edition",
                "packaging_variant",
            ):
                self.assertIsNone(fields[name]["raw_value"])
                self.assertEqual(fields[name]["state"], "unknown")
        self.assertEqual(self.plan["counts"]["variant_note_observed"], 45)

    def test_all_releases_remain_held_and_noncanonical(self) -> None:
        self.assertEqual(self.plan["authority"]["held_release_count"], 100)
        self.assertEqual(self.plan["authority"]["variant_equivalence_count"], 0)
        for record in self.plan["records"]:
            state = record["release_review"]
            self.assertEqual(state["status"], "held_pending_field_review")
            self.assertFalse(state["promotion_eligible"])
            self.assertIsNone(state["variant_equivalence_id"])
            self.assertIsNone(state["canonical_uuid"])
            self.assertIsNone(state["owner_field_decision_id"])

    def test_batch_is_unique_bounded_and_covers_decision_contexts(self) -> None:
        batch = self.plan["first_review_batch"]
        families = batch["families"]
        family_ids = [family["family_review_id"] for family in families]
        self.assertEqual(len(family_ids), len(set(family_ids)))
        self.assertLessEqual(batch["family_count"], 5)
        self.assertGreaterEqual(batch["family_count"], 1)
        self.assertLessEqual(batch["source_row_count"], 15)
        self.assertEqual(
            {family["family_decision"] for family in families},
            {"hold", "merge_existing_family", "create_new_casting"},
        )

    def test_batch_contains_complete_families(self) -> None:
        full_counts: dict[str, int] = {}
        for record in self.plan["records"]:
            family_id = record["family_review_id"]
            full_counts[family_id] = full_counts.get(family_id, 0) + 1
        for family in self.plan["first_review_batch"]["families"]:
            self.assertEqual(family["source_row_count"], full_counts[family["family_review_id"]])
            self.assertEqual(len(family["source_record_ids"]), family["source_row_count"])

    def test_committed_output_recomputes_exactly(self) -> None:
        checked = check(DEFAULT_OUTPUT)
        self.assertEqual(checked["plan_version"], "release-field-evidence-review-plan-v1")

    def test_publication_is_exclusive_and_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "plan"
            publish(output)
            with self.assertRaisesRegex(ValueError, "already exists"):
                publish(output)
            (output / "plan.md").write_text("changed")
            with self.assertRaisesRegex(ValueError, "plan.md drift"):
                check(output)

    def test_source_membership_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            temporary_root = Path(temporary)
            for relative in (NORMALIZED_PATH, REVIEW_PATH, QUEUE_PATH):
                target = temporary_root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
            normalized_path = temporary_root / NORMALIZED_PATH
            normalized = json.loads(normalized_path.read_text())
            normalized["records"].pop()
            normalized_path.write_text(json.dumps(normalized))
            with self.assertRaisesRegex(ValueError, "exactly 100"):
                build_plan(temporary_root)

    def test_planner_has_no_network_or_database_client(self) -> None:
        source = (ROOT / "scripts/plan_release_field_evidence_review.py").read_text()
        for forbidden in ("requests", "httpx", "urllib", "sqlalchemy", "psycopg", "docker"):
            self.assertNotIn(f"import {forbidden}", source)


if __name__ == "__main__":
    unittest.main()
