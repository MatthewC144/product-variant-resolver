from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/build_family_retrieval_development.py"
OUTPUT_DIR = ROOT / "data/evaluation/family-retrieval-development-v1"
PACK = OUTPUT_DIR / "development-pack.json"
MANIFEST = OUTPUT_DIR / "development-pack-manifest.json"
REGISTRY = ROOT / "data/review_family_registry.json"
PROJECTION = ROOT / "data/review_family_knowledge.json"
HUMAN = ROOT / "data/human_backed_catalog.json"
V1_QUERY_PACK = ROOT / "data/evaluation/family-retrieval-v1/query-pack.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("family_retrieval_development", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load family-retrieval development builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FamilyRetrievalDevelopmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module()
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.projection = json.loads(PROJECTION.read_text(encoding="utf-8"))
        cls.human = json.loads(HUMAN.read_text(encoding="utf-8"))
        cls.v1 = json.loads(V1_QUERY_PACK.read_text(encoding="utf-8"))
        cls.pack = json.loads(PACK.read_text(encoding="utf-8"))
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_exact_development_composition_and_disclosure(self) -> None:
        cases = self.pack["cases"]
        self.assertEqual(len(cases), 199)
        self.assertEqual(
            Counter(case["case_type"] for case in cases), self.module.CASE_COUNTS
        )
        self.assertEqual(
            Counter(case["challenge_style"] for case in cases), self.module.STYLE_COUNTS
        )
        self.assertEqual(self.pack["split"], "dev")
        self.assertTrue(self.pack["authorship_policy"]["derived_from_indexed_identities"])
        self.assertFalse(self.pack["authorship_policy"]["final_accuracy_eligible"])
        self.assertFalse(self.pack["retrieval_executed"])
        self.assertFalse(self.pack["configuration_output_viewed"])
        self.assertIn("family_retrieval_final_evaluation", self.pack["excluded_from"])

    def test_every_family_has_all_four_declared_styles(self) -> None:
        styles: dict[str, set[str]] = defaultdict(set)
        for case in self.pack["cases"]:
            if case["case_type"] == "positive_family":
                styles[case["expected"]["review_family_id"]].add(case["challenge_style"])
        family_ids = {item["review_family_id"] for item in self.registry["new_families"]}
        self.assertEqual(set(styles), family_ids)
        self.assertTrue(
            all(value == set(self.module.POSITIVE_STYLES) for value in styles.values())
        )

    def test_queries_are_unique_and_do_not_reuse_v1(self) -> None:
        queries = [self.module._normalize(case["query_text"]) for case in self.pack["cases"]]
        v1_queries = {
            self.module._normalize(case["query_text"]) for case in self.v1["cases"]
        }
        self.assertEqual(len(queries), len(set(queries)))
        self.assertFalse(set(queries) & v1_queries)

    def test_negative_control_contracts(self) -> None:
        knowledge_tokens = self.module._knowledge_tokens(self.projection, self.human)
        identity_phrases = self.module._identity_phrases(
            self.registry, self.projection, self.human
        )
        opaque = [
            case
            for case in self.pack["cases"]
            if case["challenge_style"] == "opaque_no_overlap"
        ]
        generic = [
            case
            for case in self.pack["cases"]
            if case["challenge_style"] == "generic_no_identity"
        ]
        self.assertEqual(len(opaque), 10)
        self.assertEqual(len(generic), 10)
        for case in opaque:
            self.assertFalse(
                set(self.module._normalize(case["query_text"]).split()) & knowledge_tokens
            )
            self.assertEqual(
                case["expected"], {"expected_candidate_count": 0, "zero_token_overlap": True}
            )
        for case in generic:
            query = self.module._normalize(case["query_text"])
            self.assertFalse(
                any(f" {identity} " in f" {query} " for identity in identity_phrases)
            )
            self.assertEqual(
                case["expected"], {"expected_candidate_count": 0, "zero_token_overlap": False}
            )

    def test_selection_grid_is_frozen_to_exactly_21_candidates(self) -> None:
        contract = self.pack["selection_contract"]
        self.assertEqual(contract["character_score_floors"], [0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55])
        self.assertEqual(contract["character_rrf_weights"], [0.5, 1.0, 1.5])
        self.assertEqual(contract["configuration_count"], 21)
        self.assertEqual(contract["tie_break_order"][0], "positive_mrr_desc")

    def test_manifest_binds_pack_sources_builder_and_zero_output_state(self) -> None:
        self.assertEqual(
            self.manifest["development_sha256"], hashlib.sha256(PACK.read_bytes()).hexdigest()
        )
        references = {item["file"]: item for item in self.manifest["inputs"]}
        self.assertEqual(
            references["scripts/build_family_retrieval_development.py"]["sha256"],
            hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            references["data/evaluation/family-retrieval-v1/query-pack.json"]["use"],
            "non_reuse_validation_only",
        )
        self.assertEqual(self.manifest["split_counts"], {"dev": 199, "test": 0, "train": 0})
        self.assertTrue(self.manifest["derived_from_indexed_identity"])
        self.assertFalse(self.manifest["retrieval_executed"])
        self.assertFalse(self.manifest["configuration_output_viewed"])

    def test_checked_in_files_equal_a_fresh_deterministic_build(self) -> None:
        pack, manifest = self.module.build_development_pack()
        self.assertEqual(PACK.read_text(encoding="utf-8"), self.module._stable_json(pack))
        self.assertEqual(MANIFEST.read_text(encoding="utf-8"), self.module._stable_json(manifest))

    def test_cli_check_is_non_mutating(self) -> None:
        before = (PACK.read_bytes(), MANIFEST.read_bytes())
        result = subprocess.run(
            [str(ROOT / ".venv/bin/python"), str(SCRIPT), "--check"],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("199 dev cases", result.stdout)
        self.assertEqual(before, (PACK.read_bytes(), MANIFEST.read_bytes()))

    def test_v1_collision_is_rejected(self) -> None:
        changed = copy.deepcopy(self.pack)
        changed["cases"][0]["query_text"] = self.v1["cases"][0]["query_text"]
        with self.assertRaisesRegex(ValueError, "reuses a frozen v1 query"):
            self.module._validate_pack(
                changed,
                registry=self.registry,
                projection=self.projection,
                human=self.human,
                v1_query_pack=self.v1,
            )

    def test_invalid_source_cannot_overwrite_existing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            output = temporary / "output"
            output.mkdir()
            pack_path = output / "development-pack.json"
            manifest_path = output / "development-pack-manifest.json"
            pack_path.write_text("preserve-pack\n", encoding="utf-8")
            manifest_path.write_text("preserve-manifest\n", encoding="utf-8")
            changed_registry = copy.deepcopy(self.registry)
            changed_registry["new_families"].pop()
            changed_registry_path = temporary / "review_family_registry.json"
            changed_registry_path.write_text(
                self.module._stable_json(changed_registry), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "new_families count"):
                self.module.freeze(output, registry_path=changed_registry_path)
            self.assertEqual(pack_path.read_text(encoding="utf-8"), "preserve-pack\n")
            self.assertEqual(
                manifest_path.read_text(encoding="utf-8"), "preserve-manifest\n"
            )


if __name__ == "__main__":
    unittest.main()
