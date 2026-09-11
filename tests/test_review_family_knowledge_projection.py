from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "review_family_registry.json"
REGISTRY_MANIFEST = ROOT / "data" / "review_family_registry_manifest.json"
PROJECTION = ROOT / "data" / "review_family_knowledge.json"
PROJECTION_MANIFEST = ROOT / "data" / "review_family_knowledge_manifest.json"


def _load_module():
    path = ROOT / "scripts" / "build_review_family_knowledge.py"
    spec = importlib.util.spec_from_file_location("review_family_knowledge", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load review-family knowledge builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _json_text(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


class ReviewFamilyKnowledgeProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module()
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.registry_manifest = json.loads(REGISTRY_MANIFEST.read_text(encoding="utf-8"))
        cls.projection = json.loads(PROJECTION.read_text(encoding="utf-8"))
        cls.manifest = json.loads(PROJECTION_MANIFEST.read_text(encoding="utf-8"))

    def _mutated_inputs(self, directory: str, mutator):
        registry = copy.deepcopy(self.registry)
        mutator(registry)
        registry_path = Path(directory) / REGISTRY.name
        registry_path.write_text(_json_text(registry), encoding="utf-8")
        manifest = copy.deepcopy(self.registry_manifest)
        manifest["registry_sha256"] = hashlib.sha256(registry_path.read_bytes()).hexdigest()
        manifest_path = Path(directory) / REGISTRY_MANIFEST.name
        manifest_path.write_text(_json_text(manifest), encoding="utf-8")
        return registry_path, manifest_path

    def test_projection_contains_only_42_accepted_family_documents(self) -> None:
        documents = self.projection["documents"]
        expected_ids = {item["review_family_id"] for item in self.registry["new_families"]}
        merge_ids = {item["source_family_review_id"] for item in self.registry["merge_links"]}
        hold_ids = {item["review_family_id"] for item in self.registry["hold_exclusions"]}
        actual_ids = {item["review_family_id"] for item in documents}

        self.assertEqual(self.projection["schema_version"], "pvr-review-family-knowledge-v1")
        self.assertEqual(
            self.projection["knowledge_version"],
            "review-family-knowledge-fandom-2025-r790665-v1",
        )
        self.assertEqual(self.projection["status"], "debug_retrieval_only")
        self.assertEqual(self.projection["searchable_fields"], ["brand", "casting", "aliases"])
        self.assertEqual(len(documents), 42)
        self.assertEqual(actual_ids, expected_ids)
        self.assertTrue(actual_ids.isdisjoint(merge_ids | hold_ids))
        self.assertEqual(len({item["review_family_uuid"] for item in documents}), 42)
        self.assertTrue(all(item["knowledge_type"] == "review_family" for item in documents))
        self.assertTrue(
            all(
                item["identity_status"] == "family_accepted_variants_unreviewed"
                for item in documents
            )
        )

    def test_document_schema_is_allowlisted_and_release_details_are_not_copied(self) -> None:
        allowed_fields = {
            "knowledge_type",
            "review_family_id",
            "review_family_uuid",
            "identity_level",
            "identity_status",
            "brand",
            "casting",
            "aliases",
            "source_record_ids",
        }
        accepted_source_ids = {
            reference["source_record_id"]
            for family in self.registry["new_families"]
            for reference in family["held_release_references"]
        }
        projected_source_ids = {
            source_id
            for document in self.projection["documents"]
            for source_id in document["source_record_ids"]
        }
        self.assertEqual(projected_source_ids, accepted_source_ids)
        self.assertEqual(len(projected_source_ids), 79)
        for document in self.projection["documents"]:
            self.assertEqual(set(document), allowed_fields)
            self.assertEqual(document["aliases"], [document["casting"]])
            for forbidden in (
                "decision",
                "evidence_references",
                "held_release_references",
                "toy_number",
                "collector_number",
                "series",
                "variant_note",
            ):
                self.assertNotIn(forbidden, document)

    def test_manifest_freezes_inputs_output_accounting_and_usage_boundaries(self) -> None:
        self.assertEqual(
            self.manifest["schema_version"],
            "pvr-review-family-knowledge-manifest-v1",
        )
        self.assertEqual(
            self.manifest["knowledge_version"],
            self.projection["knowledge_version"],
        )
        self.assertEqual(self.manifest["projection_file"], PROJECTION.name)
        self.assertEqual(
            self.manifest["projection_sha256"],
            hashlib.sha256(PROJECTION.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.manifest["inputs"]["review_family_registry"]["sha256"],
            hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            self.manifest["inputs"]["review_family_registry_manifest"]["sha256"],
            hashlib.sha256(REGISTRY_MANIFEST.read_bytes()).hexdigest(),
        )
        self.assertEqual(self.manifest["document_count"], 42)
        self.assertEqual(self.manifest["accepted_source_record_count"], 79)
        self.assertEqual(self.manifest["skipped_merge_link_count"], 4)
        self.assertEqual(self.manifest["skipped_merge_source_record_count"], 9)
        self.assertEqual(self.manifest["skipped_hold_exclusion_count"], 7)
        self.assertEqual(self.manifest["skipped_hold_source_record_count"], 12)
        self.assertEqual(self.manifest["source_held_release_reference_count"], 100)
        for field in (
            "provisional_variant_document_count",
            "canonical_promotion_count",
            "postgresql_row_count",
        ):
            self.assertEqual(self.manifest[field], 0)
        self.assertEqual(
            self.manifest["eligible_for"], ["human_knowledge_debug_retrieval"]
        )
        self.assertIn("canonical_candidate_ranking", self.manifest["excluded_from"])
        self.assertIn("postgresql_ingestion", self.manifest["excluded_from"])

    def test_outputs_are_byte_reproducible_and_check_mode_is_non_mutating(self) -> None:
        expected = self.module.expected_outputs(
            *self.module.build_projection(REGISTRY, REGISTRY_MANIFEST)
        )
        actual = (
            PROJECTION.read_text(encoding="utf-8"),
            PROJECTION_MANIFEST.read_text(encoding="utf-8"),
        )
        self.assertEqual(expected, actual)
        before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (PROJECTION, PROJECTION_MANIFEST)
        }
        completed = subprocess.run(
            ["python3", "scripts/build_review_family_knowledge.py", "--check"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in before}
        self.assertEqual(before, after)

    def test_invalid_checksum_counts_uuid_and_usage_widening_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry_path, manifest_path = self._mutated_inputs(
                directory,
                lambda payload: payload["eligible_for"].append("canonical_retrieval"),
            )
            with self.assertRaisesRegex(ValueError, "eligibility boundary"):
                self.module.build_projection(registry_path, manifest_path)

        with tempfile.TemporaryDirectory() as directory:
            registry_path, manifest_path = self._mutated_inputs(
                directory,
                lambda payload: payload["new_families"].pop(),
            )
            with self.assertRaisesRegex(ValueError, "count differs"):
                self.module.build_projection(registry_path, manifest_path)

        def duplicate_uuid(payload):
            payload["new_families"][1]["review_family_uuid"] = payload["new_families"][0][
                "review_family_uuid"
            ]

        with tempfile.TemporaryDirectory() as directory:
            registry_path, manifest_path = self._mutated_inputs(directory, duplicate_uuid)
            with self.assertRaisesRegex(ValueError, "not source-stable"):
                self.module.build_projection(registry_path, manifest_path)

        with tempfile.TemporaryDirectory() as directory:
            registry_path, manifest_path = self._mutated_inputs(
                directory,
                lambda payload: payload["new_families"][0]["aliases"].append(
                    "unreviewed widened alias"
                ),
            )
            with self.assertRaisesRegex(ValueError, "frozen v1 contract"):
                self.module.build_projection(registry_path, manifest_path)

        with tempfile.TemporaryDirectory() as directory:
            registry_path = Path(directory) / REGISTRY.name
            registry_path.write_bytes(REGISTRY.read_bytes())
            manifest_path = Path(directory) / REGISTRY_MANIFEST.name
            manifest = copy.deepcopy(self.registry_manifest)
            manifest["registry_sha256"] = "0" * 64
            manifest_path.write_text(_json_text(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum differs"):
                self.module.build_projection(registry_path, manifest_path)

    def test_invalid_input_and_stale_check_never_overwrite_existing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            registry_path, manifest_path = self._mutated_inputs(
                directory,
                lambda payload: payload["excluded_from"].remove("runtime_retrieval"),
            )
            output_path = temp / PROJECTION.name
            output_manifest_path = temp / PROJECTION_MANIFEST.name
            output_path.write_text("known-good-projection\n", encoding="utf-8")
            output_manifest_path.write_text("known-good-manifest\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    "python3",
                    "scripts/build_review_family_knowledge.py",
                    "--registry",
                    str(registry_path),
                    "--registry-manifest",
                    str(manifest_path),
                    "--output",
                    str(output_path),
                    "--manifest",
                    str(output_manifest_path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(output_path.read_text(), "known-good-projection\n")
            self.assertEqual(output_manifest_path.read_text(), "known-good-manifest\n")

            completed = subprocess.run(
                [
                    "python3",
                    "scripts/build_review_family_knowledge.py",
                    "--check",
                    "--registry",
                    str(REGISTRY),
                    "--registry-manifest",
                    str(REGISTRY_MANIFEST),
                    "--output",
                    str(output_path),
                    "--manifest",
                    str(output_manifest_path),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(output_path.read_text(), "known-good-projection\n")
            self.assertEqual(output_manifest_path.read_text(), "known-good-manifest\n")


if __name__ == "__main__":
    unittest.main()
