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
SCRIPT = ROOT / "scripts/build_family_retrieval_benchmark.py"
AUTHOR_SCRIPT = ROOT / "scripts/author_family_retrieval_query_pack.py"
REGISTRY = ROOT / "data/review_family_registry.json"
REGISTRY_MANIFEST = ROOT / "data/review_family_registry_manifest.json"
PROJECTION = ROOT / "data/review_family_knowledge.json"
PROJECTION_MANIFEST = ROOT / "data/review_family_knowledge_manifest.json"
HUMAN = ROOT / "data/human_backed_catalog.json"
HUMAN_MANIFEST = ROOT / "data/human_backed_catalog_manifest.json"
QUERY_PACK = ROOT / "data/evaluation/family-retrieval-v1/query-pack.json"
QUERY_PACK_MANIFEST = ROOT / "data/evaluation/family-retrieval-v1/query-pack-manifest.json"


def _load_module():
    spec = importlib.util.spec_from_file_location("family_retrieval_benchmark", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load family-retrieval benchmark builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _json_text(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


class FamilyRetrievalBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_module()
        cls.registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        cls.projection = json.loads(PROJECTION.read_text(encoding="utf-8"))
        cls.human = json.loads(HUMAN.read_text(encoding="utf-8"))
        cls.sut = cls.module._system_under_test(
            human_path=HUMAN,
            projection_path=PROJECTION,
        )

    def _query_pack(self) -> dict:
        timestamp = "2026-09-12T12:00:00Z"
        cases: list[dict] = []
        for index, family in enumerate(self.registry["new_families"]):
            family_id = family["review_family_id"]
            casting = family["display_name"]
            normalized_words = self.module._normalize(casting).split()
            lexical_words = [*normalized_words[:-1], f"{normalized_words[-1]}x"]
            common = {
                "authored_at": timestamp,
                "authored_by": "evaluation_query_author",
                "authoring_method": self.module.AUTHORING_POLICY["method"],
                "case_type": "positive_family",
                "casting_group_id": f"review:{family_id}",
                "retriever_output_viewed": False,
                "review_reference": {
                    "kind": "review_family",
                    "review_family_id": family_id,
                },
                "split": "test",
            }
            cases.append(
                {
                    **common,
                    "case_id": (
                        "fre-positive-"
                        f"{family_id.removeprefix('fandom-family-')}-marketplace"
                    ),
                    "challenge_style": "marketplace_noise",
                    "noise_tags": ["condition_noise", "marketplace_wrapper"],
                    "query_text": f"sellerwrap {casting} sealedcard item{index}",
                }
            )
            cases.append(
                {
                    **common,
                    "case_id": f"fre-positive-{family_id.removeprefix('fandom-family-')}-lexical",
                    "challenge_style": "lexical_variation",
                    "noise_tags": ["marketplace_wrapper", "misspelling"],
                    "query_text": f"listingwrap {' '.join(lexical_words)} looseitem{index}",
                }
            )

        for index, link in enumerate(self.registry["merge_links"]):
            family_id = link["source_family_review_id"]
            cases.append(
                {
                    "authored_at": timestamp,
                    "authored_by": "evaluation_query_author",
                    "authoring_method": self.module.AUTHORING_POLICY["method"],
                    "case_id": f"fre-merge-{family_id.removeprefix('fandom-family-')}",
                    "case_type": "merge_control",
                    "casting_group_id": f"merge:{family_id}",
                    "challenge_style": "merge_existing_family",
                    "noise_tags": ["marketplace_wrapper"],
                    "query_text": f"mergewrapper {link['display_name']} collectable{index}",
                    "retriever_output_viewed": False,
                    "review_reference": {
                        "kind": "merge_control",
                        "source_family_review_id": family_id,
                    },
                    "split": "test",
                }
            )

        for index, hold in enumerate(self.registry["hold_exclusions"]):
            family_id = hold["review_family_id"]
            cases.append(
                {
                    "authored_at": timestamp,
                    "authored_by": "evaluation_query_author",
                    "authoring_method": self.module.AUTHORING_POLICY["method"],
                    "case_id": f"fre-hold-{family_id.removeprefix('fandom-family-')}",
                    "case_type": "hold_control",
                    "casting_group_id": f"hold:{family_id}",
                    "challenge_style": "held_identity",
                    "noise_tags": ["identity_ambiguity"],
                    "query_text": f"holdwrapper {hold['display_name']} lineagequestion{index}",
                    "retriever_output_viewed": False,
                    "review_reference": {
                        "kind": "hold_control",
                        "review_family_id": family_id,
                    },
                    "split": "test",
                }
            )

        for index in range(10):
            control_id = f"zero-overlap-{index:02d}"
            cases.append(
                {
                    "authored_at": timestamp,
                    "authored_by": "evaluation_query_author",
                    "authoring_method": self.module.AUTHORING_POLICY["method"],
                    "case_id": f"fre-unrelated-{index:02d}",
                    "case_type": "unrelated_control",
                    "casting_group_id": f"unrelated:{control_id}",
                    "challenge_style": "no_overlap",
                    "noise_tags": ["no_overlap"],
                    "query_text": f"zxqvocabulary{index}plugh",
                    "retriever_output_viewed": False,
                    "review_reference": {
                        "control_id": control_id,
                        "kind": "unrelated_control",
                    },
                    "split": "test",
                }
            )

        return {
            "authorship_policy": copy.deepcopy(self.module.AUTHORING_POLICY),
            "benchmark_version": self.module.BENCHMARK_VERSION,
            "cases": sorted(cases, key=lambda item: item["case_id"]),
            "eligible_for": copy.deepcopy(self.module.ELIGIBLE_FOR),
            "excluded_from": copy.deepcopy(self.module.EXCLUDED_FROM),
            "expected_counts": copy.deepcopy(self.module.EXPECTED_CASE_COUNTS),
            "query_pack_version": self.module.QUERY_PACK_VERSION,
            "schema_version": self.module.QUERY_PACK_SCHEMA,
            "split": "test",
            "status": "pending_owner_review",
            "system_under_test": copy.deepcopy(self.sut),
        }

    def _decisions(self, query_pack: dict, query_pack_path: Path) -> dict:
        timestamp = "2026-09-12T13:00:00Z"
        merge_by_id = {
            item["source_family_review_id"]: item for item in self.registry["merge_links"]
        }
        decisions = []
        for case in query_pack["cases"]:
            reference = case["review_reference"]
            if case["case_type"] == "positive_family":
                expected = {
                    "knowledge_type": "review_family",
                    "review_family_id": reference["review_family_id"],
                }
            elif case["case_type"] == "merge_control":
                family_id = reference["source_family_review_id"]
                expected = {
                    "casting_id": merge_by_id[family_id]["target_casting_id"],
                    "forbidden_review_family_id": family_id,
                    "knowledge_type": "provisional_variant",
                }
            elif case["case_type"] == "hold_control":
                expected = {
                    "expected_materialized": False,
                    "forbidden_review_family_id": reference["review_family_id"],
                }
            else:
                expected = {"expected_candidate_count": 0, "zero_token_overlap": True}
            decisions.append(
                {
                    "case_id": case["case_id"],
                    "decided_at": timestamp,
                    "decided_by": "project_owner",
                    "decision": "approve",
                    "expected": expected,
                    "reason": "Synthetic fixture owner decision for contract validation.",
                }
            )
        return {
            "benchmark_version": self.module.BENCHMARK_VERSION,
            "decided_at": timestamp,
            "decided_by": "project_owner",
            "decision_version": self.module.DECISIONS_VERSION,
            "decisions": decisions,
            "query_pack_file": query_pack_path.name,
            "query_pack_sha256": hashlib.sha256(query_pack_path.read_bytes()).hexdigest(),
            "schema_version": self.module.DECISIONS_SCHEMA,
            "status": "approved_for_test_evaluation",
        }

    def _write_fixture(self, directory: str, *, query_pack: dict | None = None):
        temp = Path(directory)
        query_pack = copy.deepcopy(query_pack or self._query_pack())
        query_pack_path = temp / "query-pack.json"
        query_pack_path.write_text(_json_text(query_pack), encoding="utf-8")
        accounting = self.module.validate_query_pack(
            query_pack,
            registry=self.registry,
            projection=self.projection,
            human=self.human,
            system_under_test=self.sut,
        )
        query_manifest = self.module.expected_query_pack_manifest(
            query_pack_path, query_pack, accounting
        )
        query_manifest_path = temp / "query-pack-manifest.json"
        query_manifest_path.write_text(_json_text(query_manifest), encoding="utf-8")
        decisions_path = temp / "owner-decisions.json"
        decisions_path.write_text(
            _json_text(self._decisions(query_pack, query_pack_path)), encoding="utf-8"
        )
        return query_pack_path, query_manifest_path, decisions_path

    def _build(self, query_pack: Path, query_manifest: Path, decisions: Path):
        return self.module.build_benchmark(
            query_pack_path=query_pack,
            query_pack_manifest_path=query_manifest,
            decisions_path=decisions,
            registry_path=REGISTRY,
            registry_manifest_path=REGISTRY_MANIFEST,
            projection_path=PROJECTION,
            projection_manifest_path=PROJECTION_MANIFEST,
            human_path=HUMAN,
            human_manifest_path=HUMAN_MANIFEST,
        )

    def _cli_sources(self) -> list[str]:
        return [
            "--registry", str(REGISTRY),
            "--registry-manifest", str(REGISTRY_MANIFEST),
            "--projection", str(PROJECTION),
            "--projection-manifest", str(PROJECTION_MANIFEST),
            "--human-catalog", str(HUMAN),
            "--human-catalog-manifest", str(HUMAN_MANIFEST),
        ]

    def test_valid_contract_freezes_exact_composition_and_usage_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            query, query_manifest, decisions = self._write_fixture(directory)
            benchmark, manifest = self._build(query, query_manifest, decisions)

        self.assertEqual(len(benchmark["cases"]), 105)
        self.assertEqual(manifest["case_counts"], self.module.EXPECTED_CASE_COUNTS)
        self.assertEqual(manifest["challenge_style_counts"], self.module.EXPECTED_STYLE_COUNTS)
        self.assertEqual(manifest["positive_family_group_count"], 42)
        self.assertEqual(len(manifest["single_token_family_ids"]), 4)
        self.assertEqual(manifest["split_counts"], {"dev": 0, "test": 105, "train": 0})
        self.assertEqual(benchmark["status"], "frozen_test_only")
        self.assertIn("postgresql_ingestion", benchmark["excluded_from"])
        self.assertIn("retriever_tuning", benchmark["excluded_from"])
        self.assertEqual(benchmark["system_under_test"]["candidate_limit"], 5)
        self.assertEqual(benchmark["system_under_test"]["rrf_k"], 60)

    def test_actual_query_pack_is_complete_output_blind_and_checksum_frozen(self) -> None:
        query_pack = json.loads(QUERY_PACK.read_text(encoding="utf-8"))
        manifest = json.loads(QUERY_PACK_MANIFEST.read_text(encoding="utf-8"))
        accounting = self.module.validate_query_pack(
            query_pack,
            registry=self.registry,
            projection=self.projection,
            human=self.human,
            system_under_test=self.sut,
        )
        expected_manifest = self.module.expected_query_pack_manifest(
            QUERY_PACK, query_pack, accounting
        )
        self.assertEqual(manifest, expected_manifest)
        self.assertEqual(len(query_pack["cases"]), 105)
        self.assertTrue(
            all(item["retriever_output_viewed"] is False for item in query_pack["cases"])
        )
        forbidden_output_fields = {
            "candidates",
            "dense_rank",
            "dense_score",
            "expected",
            "retrieval_output",
            "rrf_rank",
            "rrf_score",
            "sparse_rank",
            "sparse_score",
        }
        self.assertTrue(
            all(not (set(item) & forbidden_output_fields) for item in query_pack["cases"])
        )

    def test_actual_query_pack_authoring_and_freeze_checks_are_non_mutating(self) -> None:
        before = {
            path: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (QUERY_PACK, QUERY_PACK_MANIFEST)
        }
        for command in (
            ["python3", str(AUTHOR_SCRIPT), "--check"],
            ["python3", str(SCRIPT), "--check-query-pack"],
        ):
            completed = subprocess.run(
                command,
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in before}
        self.assertEqual(before, after)

    def test_query_pack_freeze_and_benchmark_check_are_byte_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            query_pack = self._query_pack()
            query = temp / "query-pack.json"
            query.write_text(_json_text(query_pack), encoding="utf-8")
            query_manifest = temp / "query-pack-manifest.json"
            freeze = subprocess.run(
                [
                    "python3", str(SCRIPT), "--freeze-query-pack",
                    "--query-pack", str(query),
                    "--query-pack-manifest", str(query_manifest),
                    *self._cli_sources(),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(freeze.returncode, 0, freeze.stderr)
            check_pack = subprocess.run(
                [
                    "python3", str(SCRIPT), "--check-query-pack",
                    "--query-pack", str(query),
                    "--query-pack-manifest", str(query_manifest),
                    *self._cli_sources(),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(check_pack.returncode, 0, check_pack.stderr)
            decisions = temp / "owner-decisions.json"
            decisions.write_text(
                _json_text(self._decisions(query_pack, query)), encoding="utf-8"
            )
            benchmark, manifest = self._build(query, query_manifest, decisions)
            output = temp / "benchmark.json"
            output_manifest = temp / "benchmark-manifest.json"
            output.write_text(_json_text(benchmark), encoding="utf-8")
            output_manifest.write_text(_json_text(manifest), encoding="utf-8")
            before = {
                path: hashlib.sha256(path.read_bytes()).hexdigest()
                for path in (query_manifest, output, output_manifest)
            }
            check_benchmark = subprocess.run(
                [
                    "python3", str(SCRIPT), "--check",
                    "--query-pack", str(query),
                    "--query-pack-manifest", str(query_manifest),
                    "--owner-decisions", str(decisions),
                    "--output", str(output),
                    "--manifest", str(output_manifest),
                    *self._cli_sources(),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(check_benchmark.returncode, 0, check_benchmark.stderr)
            after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in before}
            self.assertEqual(before, after)

    def test_copied_queries_retained_lexical_phrases_and_overlap_fail_closed(self) -> None:
        pack = self._query_pack()
        pack["cases"][0]["query_text"] = self.projection["documents"][0]["casting"]
        with self.assertRaisesRegex(ValueError, "copies a prohibited"):
            self.module.validate_query_pack(
                pack,
                registry=self.registry,
                projection=self.projection,
                human=self.human,
                system_under_test=self.sut,
            )

        pack = self._query_pack()
        lexical = next(
            item for item in pack["cases"] if item["challenge_style"] == "lexical_variation"
        )
        family_id = lexical["review_reference"]["review_family_id"]
        casting = next(
            item["casting"]
            for item in self.projection["documents"]
            if item["review_family_id"] == family_id
        )
        lexical["query_text"] = f"wrapper {casting} altered"
        with self.assertRaisesRegex(ValueError, "retains the full casting phrase"):
            self.module.validate_query_pack(
                pack,
                registry=self.registry,
                projection=self.projection,
                human=self.human,
                system_under_test=self.sut,
            )

        pack = self._query_pack()
        unrelated = next(
            item for item in pack["cases"] if item["case_type"] == "unrelated_control"
        )
        unrelated["query_text"] = "hot zxqnonexistent"
        with self.assertRaisesRegex(ValueError, "overlaps human knowledge tokens"):
            self.module.validate_query_pack(
                pack,
                registry=self.registry,
                projection=self.projection,
                human=self.human,
                system_under_test=self.sut,
            )

    def test_viewed_output_non_test_use_and_changed_system_are_rejected(self) -> None:
        for mutate, message in (
            (lambda pack: pack["cases"][0].update({"retriever_output_viewed": True}), "unviewed"),
            (lambda pack: pack["cases"][0].update({"split": "dev"}), "test split"),
            (
                lambda pack: pack["excluded_from"].remove("postgresql_ingestion"),
                "excluded uses",
            ),
            (
                lambda pack: pack["system_under_test"].update({"rrf_k": 61}),
                "system-under-test",
            ),
        ):
            pack = self._query_pack()
            mutate(pack)
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                self.module.validate_query_pack(
                    pack,
                    registry=self.registry,
                    projection=self.projection,
                    human=self.human,
                    system_under_test=self.sut,
                )

    def test_partial_duplicate_changed_and_wrong_owner_labels_are_rejected(self) -> None:
        mutations = []
        mutations.append(lambda payload: payload["decisions"].pop())
        mutations.append(
            lambda payload: payload["decisions"].__setitem__(
                1, copy.deepcopy(payload["decisions"][0])
            )
        )
        mutations.append(lambda payload: payload.update({"query_pack_sha256": "0" * 64}))

        def wrong_label(payload):
            decision = next(
                item
                for item in payload["decisions"]
                if item["expected"].get("knowledge_type") == "review_family"
            )
            decision["expected"]["review_family_id"] = "fandom-family-0000000000000000"

        mutations.append(wrong_label)
        for mutate in mutations:
            with tempfile.TemporaryDirectory() as directory:
                query, query_manifest, decisions_path = self._write_fixture(directory)
                decisions = json.loads(decisions_path.read_text(encoding="utf-8"))
                mutate(decisions)
                decisions_path.write_text(_json_text(decisions), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self._build(query, query_manifest, decisions_path)

    def test_invalid_input_and_stale_check_do_not_overwrite_known_good_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            query, query_manifest, decisions = self._write_fixture(directory)
            output = temp / "benchmark.json"
            output_manifest = temp / "benchmark-manifest.json"
            output.write_text("known-good-benchmark\n", encoding="utf-8")
            output_manifest.write_text("known-good-manifest\n", encoding="utf-8")

            decision_payload = json.loads(decisions.read_text(encoding="utf-8"))
            decision_payload["status"] = "pending"
            decisions.write_text(_json_text(decision_payload), encoding="utf-8")
            failed_build = subprocess.run(
                [
                    "python3", str(SCRIPT),
                    "--query-pack", str(query),
                    "--query-pack-manifest", str(query_manifest),
                    "--owner-decisions", str(decisions),
                    "--output", str(output),
                    "--manifest", str(output_manifest),
                    *self._cli_sources(),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(failed_build.returncode, 0)
            self.assertEqual(output.read_text(), "known-good-benchmark\n")
            self.assertEqual(output_manifest.read_text(), "known-good-manifest\n")

            query, query_manifest, decisions = self._write_fixture(directory)
            stale_check = subprocess.run(
                [
                    "python3", str(SCRIPT), "--check",
                    "--query-pack", str(query),
                    "--query-pack-manifest", str(query_manifest),
                    "--owner-decisions", str(decisions),
                    "--output", str(output),
                    "--manifest", str(output_manifest),
                    *self._cli_sources(),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(stale_check.returncode, 0)
            self.assertEqual(output.read_text(), "known-good-benchmark\n")
            self.assertEqual(output_manifest.read_text(), "known-good-manifest\n")


if __name__ == "__main__":
    unittest.main()
