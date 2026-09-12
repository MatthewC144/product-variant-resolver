from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from uuid import UUID

from product_variant_resolver.human_knowledge import (
    HumanKnowledgeCandidate,
    ReviewFamilyKnowledgeDocument,
)
from product_variant_resolver.human_knowledge_evaluation import (
    DEFAULT_BENCHMARK,
    DEFAULT_MANIFEST,
    build_evaluation,
    evaluate_cases,
    summarize_results,
    validate_evaluation_report,
)

ROOT = Path(__file__).resolve().parents[2]
EVALUATION_OUTPUT = ROOT / "reports/family-retrieval-v1/evaluation.json"
MARKDOWN_OUTPUT = ROOT / "reports/family-retrieval-v1/evaluation.md"
REPORT_SCRIPT = ROOT / "scripts/generate_family_retrieval_report.py"


def _family_candidate(family_id: str, rank: int = 1) -> HumanKnowledgeCandidate:
    document = ReviewFamilyKnowledgeDocument(
        review_family_uuid=UUID(int=int(family_id[-4:], 16)),
        review_family_id=family_id,
        brand="Hot Wheels",
        casting="Test Family",
        aliases=("Test Family",),
        source_record_ids=("fandom-row-0000000000000000",),
        identity_status="family_accepted_variants_unreviewed",
    )
    return HumanKnowledgeCandidate(
        document=document,
        sparse_rank=rank,
        sparse_score=1.0,
        dense_rank=rank,
        dense_score=1.0,
        rrf_rank=rank,
        rrf_score=2 / (60 + rank),
        matched_tokens=("test",),
    )


def _case_result(
    case_id: str,
    case_type: str,
    style: str,
    *,
    rank: int | None = None,
    group: str | None = None,
    candidate_count: int = 0,
    forbidden_hits: list[int] | None = None,
    error: str = "none",
) -> dict[str, Any]:
    return {
        "candidate_count": candidate_count,
        "candidates": [],
        "case_id": case_id,
        "case_type": case_type,
        "casting_group_id": group or case_id,
        "challenge_style": style,
        "error_category": error,
        "expected": {},
        "expected_rank": rank,
        "forbidden_hit_ranks": forbidden_hits or [],
        "query_text": "test query",
    }


class _GuardedCase(dict[str, Any]):
    def __init__(self, retrieval_state: dict[str, bool], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.retrieval_state = retrieval_state

    def get(self, key: str, default: Any = None) -> Any:
        if key == "expected" and not self.retrieval_state["called"]:
            raise AssertionError("expected label was accessed before retrieval")
        return super().get(key, default)


class _GuardRetriever:
    def __init__(self, retrieval_state: dict[str, bool]) -> None:
        self.retrieval_state = retrieval_state

    def retrieve(self, signals: Any, limit: int) -> list[HumanKnowledgeCandidate]:
        self.retrieval_state["called"] = True
        return []


class _SequenceRetriever:
    def __init__(self, responses: list[list[HumanKnowledgeCandidate]]) -> None:
        self.responses = iter(responses)

    def retrieve(self, signals: Any, limit: int) -> list[HumanKnowledgeCandidate]:
        return next(self.responses)


class HumanKnowledgeEvaluationTests(unittest.TestCase):
    def test_expected_label_is_not_accessed_until_after_retrieval(self) -> None:
        state = {"called": False}
        case = _GuardedCase(
            state,
            case_id="positive-1",
            case_type="positive_family",
            casting_group_id="family-1",
            challenge_style="lexical_variation",
            query_text="mispelled family",
            expected={
                "knowledge_type": "review_family",
                "review_family_id": "fandom-family-0000000000000001",
            },
        )
        result = evaluate_cases([case], _GuardRetriever(state))
        self.assertTrue(state["called"])
        self.assertEqual(result[0]["error_category"], "no_candidates")

    def test_metrics_are_formula_derived_and_gate_failures_remain_failures(self) -> None:
        results = [
            _case_result("p1", "positive_family", "lexical_variation", rank=1, group="family-1"),
            _case_result("p2", "positive_family", "marketplace_noise", rank=5, group="family-2"),
            _case_result("m1", "merge_control", "merge_existing_family", rank=5),
            _case_result("h1", "hold_control", "held_identity"),
            _case_result("u1", "unrelated_control", "no_overlap"),
        ]
        summary = summarize_results(results)
        self.assertEqual(summary["metrics"]["positive_recall_at_5"], 1.0)
        self.assertEqual(summary["metrics"]["positive_recall_at_1"], 0.5)
        self.assertEqual(summary["metrics"]["positive_mrr_at_5"], 0.6)
        self.assertEqual(summary["raw_counts"]["positive"]["hits_at_5"], 2)
        self.assertFalse(summary["gates"]["positive_recall_at_1"]["passed"])
        self.assertEqual(summary["verdict"], "FAIL")

    def test_case_error_categories_are_explicit(self) -> None:
        wanted = "fandom-family-0000000000000001"
        other = "fandom-family-0000000000000002"
        forbidden = "fandom-family-0000000000000003"
        cases = [
            {
                "case_id": "p-empty",
                "case_type": "positive_family",
                "casting_group_id": "g1",
                "challenge_style": "lexical_variation",
                "query_text": "empty",
                "expected": {"knowledge_type": "review_family", "review_family_id": wanted},
            },
            {
                "case_id": "p-wrong",
                "case_type": "positive_family",
                "casting_group_id": "g2",
                "challenge_style": "marketplace_noise",
                "query_text": "wrong",
                "expected": {"knowledge_type": "review_family", "review_family_id": wanted},
            },
            {
                "case_id": "h-forbidden",
                "case_type": "hold_control",
                "casting_group_id": "g3",
                "challenge_style": "held_identity",
                "query_text": "forbidden",
                "expected": {
                    "expected_materialized": False,
                    "forbidden_review_family_id": forbidden,
                },
            },
            {
                "case_id": "u-nonempty",
                "case_type": "unrelated_control",
                "casting_group_id": "g4",
                "challenge_style": "no_overlap",
                "query_text": "unexpected",
                "expected": {"expected_candidate_count": 0, "zero_token_overlap": True},
            },
        ]
        retriever = _SequenceRetriever(
            [
                [],
                [_family_candidate(other)],
                [_family_candidate(forbidden)],
                [_family_candidate(other)],
            ]
        )
        results = evaluate_cases(cases, retriever)
        self.assertEqual(
            [item["error_category"] for item in results],
            [
                "no_candidates",
                "expected_identity_not_retrieved",
                "forbidden_family_retrieved",
                "unexpected_candidates",
            ],
        )

    def test_actual_frozen_evaluation_is_recomputable_and_truthful(self) -> None:
        evaluation = build_evaluation(DEFAULT_BENCHMARK, DEFAULT_MANIFEST)
        validate_evaluation_report(evaluation)
        self.assertEqual(evaluation["verdict"], "FAIL")
        self.assertEqual(evaluation["raw_counts"]["positive"]["hits_at_5"], 73)
        self.assertEqual(evaluation["raw_counts"]["positive"]["total"], 84)
        self.assertEqual(
            evaluation["raw_counts"]["positive_styles"]["lexical_variation"],
            {"hits_at_5": 31, "total": 42},
        )
        self.assertFalse(evaluation["gates"]["lexical_variation_recall_at_5"]["passed"])
        self.assertTrue(
            all(
                gate["passed"]
                for name, gate in evaluation["gates"].items()
                if name != "lexical_variation_recall_at_5"
            )
        )
        self.assertEqual(
            evaluation,
            json.loads(EVALUATION_OUTPUT.read_text(encoding="utf-8")),
        )

    def test_invalid_frozen_input_cannot_overwrite_existing_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            benchmark = json.loads(DEFAULT_BENCHMARK.read_text(encoding="utf-8"))
            benchmark["status"] = "tunable"
            benchmark_path = temporary / "benchmark.json"
            benchmark_path.write_text(json.dumps(benchmark), encoding="utf-8")
            manifest_path = temporary / "benchmark-manifest.json"
            manifest_path.write_bytes(DEFAULT_MANIFEST.read_bytes())
            output = temporary / "evaluation.json"
            output.write_text("known-good\n", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "product_variant_resolver.human_knowledge_evaluation",
                    "--benchmark",
                    str(benchmark_path),
                    "--manifest",
                    str(manifest_path),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "known-good\n")

    def test_json_and_markdown_reports_are_byte_reproducible(self) -> None:
        check_json = subprocess.run(
            [
                sys.executable,
                "-m",
                "product_variant_resolver.human_knowledge_evaluation",
                "--check",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(check_json.returncode, 0, check_json.stderr)
        check_markdown = subprocess.run(
            [
                sys.executable,
                str(REPORT_SCRIPT),
                "--evaluation",
                str(EVALUATION_OUTPUT),
                "--output",
                str(MARKDOWN_OUTPUT),
                "--check",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(check_markdown.returncode, 0, check_markdown.stderr)
        self.assertIn("Verdict: **FAIL**", MARKDOWN_OUTPUT.read_text(encoding="utf-8"))

    def test_markdown_renderer_rejects_non_recomputable_metrics(self) -> None:
        spec = importlib.util.spec_from_file_location("family_report", REPORT_SCRIPT)
        if spec is None or spec.loader is None:
            self.fail("could not load Markdown report generator")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        payload = json.loads(EVALUATION_OUTPUT.read_text(encoding="utf-8"))
        payload["metrics"]["positive_recall_at_5"] = 1.0
        with self.assertRaisesRegex(ValueError, "cannot be recomputed"):
            module.render_markdown(payload)


if __name__ == "__main__":
    unittest.main()
