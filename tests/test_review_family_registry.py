from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025"
QUEUE = PILOT / "priority-2-batch-05-adjudicated-queue.json"
QUEUE_MANIFEST = PILOT / "priority-2-batch-05-adjudicated-queue-manifest.json"
STAGING = PILOT / "normalized.json"
STAGING_MANIFEST = PILOT / "manifest.json"
HUMAN = ROOT / "data" / "human_backed_catalog.json"
HUMAN_MANIFEST = ROOT / "data" / "human_backed_catalog_manifest.json"
REGISTRY = ROOT / "data" / "review_family_registry.json"
REGISTRY_MANIFEST = ROOT / "data" / "review_family_registry_manifest.json"
REPORT = ROOT / "reports" / "review-family-materialization.md"


def _load_module():
    path = ROOT / "scripts" / "build_review_family_registry.py"
    spec = importlib.util.spec_from_file_location("review_family_registry", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load review-family registry builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _json_text(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


class ReviewFamilyRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module()
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.manifest = json.loads(REGISTRY_MANIFEST.read_text(encoding="utf-8"))
        cls.human = json.loads(HUMAN.read_text(encoding="utf-8"))

    def _build(
        self,
        *,
        queue: Path = QUEUE,
        queue_manifest: Path = QUEUE_MANIFEST,
        human: Path = HUMAN,
        human_manifest: Path = HUMAN_MANIFEST,
    ):
        return self.module.build_registry(
            queue,
            queue_manifest,
            STAGING,
            STAGING_MANIFEST,
            human,
            human_manifest,
        )

    def _mutated_queue(self, directory: str, mutator, *, sync_manifest: bool = True):
        queue = json.loads(QUEUE.read_text(encoding="utf-8"))
        mutator(queue)
        queue_path = Path(directory) / QUEUE.name
        queue_path.write_text(_json_text(queue), encoding="utf-8")
        manifest = json.loads(QUEUE_MANIFEST.read_text(encoding="utf-8"))
        if sync_manifest:
            manifest["result_sha256"] = hashlib.sha256(queue_path.read_bytes()).hexdigest()
        manifest_path = Path(directory) / QUEUE_MANIFEST.name
        manifest_path.write_text(_json_text(manifest), encoding="utf-8")
        return queue_path, manifest_path

    def test_registry_has_exact_family_and_zero_promotion_contract(self) -> None:
        self.assertEqual(self.registry["status"], "review_family_only")
        self.assertEqual(len(self.registry["new_families"]), 42)
        self.assertEqual(len(self.registry["merge_links"]), 4)
        self.assertEqual(len(self.registry["hold_exclusions"]), 7)
        self.assertEqual(self.manifest["new_family_source_row_count"], 79)
        self.assertEqual(self.manifest["merge_source_row_count"], 9)
        self.assertEqual(self.manifest["hold_source_row_count"], 12)
        self.assertEqual(self.manifest["held_release_reference_count"], 100)
        for field in (
            "provisional_variant_count",
            "canonical_promotion_count",
            "runtime_indexed_family_count",
            "postgresql_row_count",
        ):
            self.assertEqual(self.manifest[field], 0)
        self.assertIn("runtime_retrieval", self.registry["excluded_from"])
        self.assertIn("postgresql_ingestion", self.registry["excluded_from"])

    def test_new_family_ids_are_source_stable_and_aliases_are_conservative(self) -> None:
        namespace = "product-variant-resolver:review-family:fandom-hot-wheels-wiki"
        ids: set[str] = set()
        uuids: set[str] = set()
        for family in self.registry["new_families"]:
            family_id = family["review_family_id"]
            expected_uuid = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"{namespace}:{family_id}")
            )
            self.assertEqual(family["review_family_uuid"], expected_uuid)
            self.assertEqual(family["aliases"], [family["display_name"]])
            self.assertEqual(family["identity_level"], "casting_family_only")
            self.assertEqual(
                family["identity_status"], "family_accepted_variants_unreviewed"
            )
            ids.add(family_id)
            uuids.add(expected_uuid)
        self.assertEqual(len(ids), 42)
        self.assertEqual(len(uuids), 42)

    def test_merge_links_reuse_exact_existing_human_identities(self) -> None:
        existing = {item["casting_id"]: item for item in self.human["castings"]}
        self.assertEqual(
            {item["target_casting_id"] for item in self.registry["merge_links"]},
            {
                "human-hot-wheels-67-chevy-c10",
                "human-hot-wheels-purple-passion",
                "human-hot-wheels-subaru-brz",
                "human-hot-wheels-tesla-model-s-plaid",
            },
        )
        for link in self.registry["merge_links"]:
            target = existing[link["target_casting_id"]]
            self.assertEqual(link["target_casting_uuid"], target["casting_uuid"])
            self.assertNotIn("review_family_uuid", link)

    def test_named_holds_are_auditable_and_not_retrieval_eligible(self) -> None:
        holds = self.registry["hold_exclusions"]
        self.assertEqual(
            {item["display_name"] for item in holds},
            {
                "'55 Chevy",
                "Batman and Robin Batmobile",
                "Mazda MX-5 Miata",
                "Nissan Skyline 2000GT-R LBWK",
                "Nissan Skyline GT-R (BNR32)",
                "Power Wheels Dune Racer",
                "Standard Kart",
            },
        )
        for hold in holds:
            self.assertFalse(hold["retrieval_eligible"])
            self.assertEqual(hold["identity_status"], "held_not_materialized")
            self.assertTrue(hold["decision"]["reason"])
            self.assertTrue(hold["decision"]["evidence_references"])

    def test_all_source_rows_occur_once_and_remain_release_held(self) -> None:
        records = [
            reference
            for section in ("new_families", "merge_links", "hold_exclusions")
            for item in self.registry[section]
            for reference in item["held_release_references"]
        ]
        self.assertEqual(len(records), 100)
        self.assertEqual(len({item["source_record_id"] for item in records}), 100)
        self.assertTrue(
            all(item["review_status"] == "held_for_variant_review" for item in records)
        )
        serialized = _json_text(self.registry)
        self.assertNotIn('"provisional_variants"', serialized)
        self.assertNotIn('"canonical_uuid"', serialized)

    def test_provenance_is_complete_for_every_accepted_family(self) -> None:
        self.assertEqual(self.registry["source"]["revision_id"], 790665)
        self.assertEqual(self.registry["source"]["license"], "CC-BY-SA")
        for section in ("new_families", "merge_links"):
            for item in self.registry[section]:
                decision = item["decision"]
                self.assertTrue(decision["decision_batch_id"])
                self.assertEqual(decision["decided_by"], "project_owner")
                self.assertTrue(decision["decided_at"].endswith("Z"))
                self.assertTrue(decision["reason"])
                self.assertGreaterEqual(len(decision["evidence_references"]), 3)

    def test_outputs_are_frozen_reproducible_and_check_mode_is_non_mutating(self) -> None:
        self.assertEqual(
            self.manifest["registry_sha256"], hashlib.sha256(REGISTRY.read_bytes()).hexdigest()
        )
        self.assertEqual(
            self.manifest["report_sha256"], hashlib.sha256(REPORT.read_bytes()).hexdigest()
        )
        expected = self.module.expected_outputs(*self._build())
        actual = (
            REGISTRY.read_text(encoding="utf-8"),
            REGISTRY_MANIFEST.read_text(encoding="utf-8"),
            REPORT.read_text(encoding="utf-8"),
        )
        self.assertEqual(expected, actual)
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in (
            REGISTRY,
            REGISTRY_MANIFEST,
            REPORT,
        )}
        completed = subprocess.run(
            ["python3", "scripts/build_review_family_registry.py", "--check"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in before}
        self.assertEqual(before, after)

    def test_changed_checksum_partial_queue_and_widened_variant_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            queue_path, manifest_path = self._mutated_queue(
                directory,
                lambda payload: payload.update({"status": "partially_adjudicated"}),
                sync_manifest=False,
            )
            with self.assertRaisesRegex(ValueError, "checksum differs"):
                self._build(queue=queue_path, queue_manifest=manifest_path)

        with tempfile.TemporaryDirectory() as directory:
            queue_path, manifest_path = self._mutated_queue(
                directory,
                lambda payload: payload.update({"status": "partially_adjudicated"}),
            )
            with self.assertRaisesRegex(ValueError, "not fully adjudicated"):
                self._build(queue=queue_path, queue_manifest=manifest_path)

        def unsupported(payload):
            payload["families"][0]["reviewer_decision"]["decision"] = "reject"

        with tempfile.TemporaryDirectory() as directory:
            queue_path, manifest_path = self._mutated_queue(directory, unsupported)
            with self.assertRaisesRegex(ValueError, "decision is not permitted"):
                self._build(queue=queue_path, queue_manifest=manifest_path)

        def widen(payload):
            payload["families"][0]["reviewer_decision"]["variant_decision"] = "create"

        with tempfile.TemporaryDirectory() as directory:
            queue_path, manifest_path = self._mutated_queue(directory, widen)
            with self.assertRaisesRegex(ValueError, "release variants must remain held"):
                self._build(queue=queue_path, queue_manifest=manifest_path)

    def test_duplicate_rows_unknown_targets_and_human_collisions_fail_closed(self) -> None:
        def duplicate_row(payload):
            family = payload["families"][0]
            family["source_rows"].append(copy.deepcopy(family["source_rows"][0]))
            family["source_row_count"] += 1

        with tempfile.TemporaryDirectory() as directory:
            queue_path, manifest_path = self._mutated_queue(directory, duplicate_row)
            with self.assertRaisesRegex(ValueError, "assigned to more than one family"):
                self._build(queue=queue_path, queue_manifest=manifest_path)

        def unknown_target(payload):
            family = next(
                item
                for item in payload["families"]
                if item["reviewer_decision"]["decision"] == "merge_existing_family"
            )
            family["reviewer_decision"]["target_family_id"] = "human-missing"

        with tempfile.TemporaryDirectory() as directory:
            queue_path, manifest_path = self._mutated_queue(directory, unknown_target)
            with self.assertRaisesRegex(ValueError, "absent from human catalog"):
                self._build(queue=queue_path, queue_manifest=manifest_path)

        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            human = json.loads(HUMAN.read_text(encoding="utf-8"))
            template = copy.deepcopy(human["castings"][0])
            template.update(
                {
                    "brand": "Hot Wheels",
                    "casting": "1988 Jeep Wagoneer",
                    "casting_id": "human-hot-wheels-1988-jeep-wagoneer",
                    "casting_uuid": "11111111-1111-5111-8111-111111111111",
                }
            )
            human["castings"].append(template)
            human_path = temp / HUMAN.name
            human_path.write_text(_json_text(human), encoding="utf-8")
            manifest = json.loads(HUMAN_MANIFEST.read_text(encoding="utf-8"))
            manifest["casting_count"] += 1
            manifest["catalog_sha256"] = hashlib.sha256(human_path.read_bytes()).hexdigest()
            manifest_path = temp / HUMAN_MANIFEST.name
            manifest_path.write_text(_json_text(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "collides with human catalog"):
                self._build(human=human_path, human_manifest=manifest_path)


if __name__ == "__main__":
    unittest.main()
