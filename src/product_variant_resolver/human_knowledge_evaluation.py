"""Read-only evaluation for the frozen Human Knowledge RAG v2 holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol

from .human_knowledge import (
    HumanKnowledgeCandidate,
    HumanKnowledgeRetriever,
    HumanVariantKnowledgeDocument,
    ReviewFamilyKnowledgeDocument,
    load_human_knowledge_catalog,
)
from .retrieval import HashingEmbedding
from .schemas import ExtractedSignals
from .signals import extract_signals

ROOT = Path(__file__).resolve().parents[2]
EVALUATION_DIR = ROOT / "data" / "evaluation" / "family-retrieval-v1"
DEFAULT_BENCHMARK = EVALUATION_DIR / "benchmark.json"
DEFAULT_MANIFEST = EVALUATION_DIR / "benchmark-manifest.json"
DEFAULT_OUTPUT = ROOT / "reports" / "family-retrieval-v1" / "evaluation.json"

BENCHMARK_SCHEMA = "pvr-family-retrieval-benchmark-v1"
BENCHMARK_MANIFEST_SCHEMA = "pvr-family-retrieval-benchmark-manifest-v1"
BENCHMARK_VERSION = "family-retrieval-holdout-v1"
EVALUATION_SCHEMA = "pvr-family-retrieval-evaluation-v1"
EVALUATION_VERSION = "family-retrieval-evaluation-v1"

CASE_COUNTS = {
    "hold_control": 7,
    "merge_control": 4,
    "positive_family": 84,
    "unrelated_control": 10,
}
STYLE_COUNTS = {
    "held_identity": 7,
    "lexical_variation": 42,
    "marketplace_noise": 42,
    "merge_existing_family": 4,
    "no_overlap": 10,
}
POSITIVE_STYLES = ("lexical_variation", "marketplace_noise")
ELIGIBLE_FOR = ["human_knowledge_retrieval_evaluation"]
EXCLUDED_FROM = [
    "calibration_training",
    "canonical_candidate_ranking",
    "canonical_confidence",
    "canonical_variant_response",
    "postgresql_ingestion",
    "production_accuracy_claim",
    "query_rewriting",
    "release_variant_ground_truth",
    "retriever_tuning",
    "threshold_selection",
]
GATE_POLICY: tuple[tuple[str, str, float | int], ...] = (
    ("positive_recall_at_5", ">=", 0.85),
    ("positive_recall_at_1", ">=", 0.65),
    ("positive_mrr_at_5", ">=", 0.75),
    ("lexical_variation_recall_at_5", ">=", 0.75),
    ("marketplace_noise_recall_at_5", ">=", 0.75),
    ("family_coverage_at_5", ">=", 0.90),
    ("merge_control_recall_at_5", "=", 1.0),
    ("forbidden_family_hits", "=", 0),
    ("unrelated_non_empty_results", "=", 0),
)


class KnowledgeRetriever(Protocol):
    def retrieve(self, signals: ExtractedSignals, limit: int) -> list[HumanKnowledgeCandidate]: ...


def _load_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{label} could not be read as valid JSON") from error
    if not isinstance(payload, dict):
        raise TypeError(f"{label} root must be an object")
    return payload


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ValueError(f"{path.name}: could not read file for checksum") from error


def _stable_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _check_text(path: Path, expected: str) -> None:
    try:
        actual = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"{path.name}: existing output could not be read") from error
    if actual != expected:
        raise ValueError(f"{path.name}: output differs from reproducible evaluation")


def _validate_frozen_inputs(
    benchmark_path: Path,
    manifest_path: Path,
    benchmark: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> None:
    expected_benchmark_fields = {
        "benchmark_version",
        "cases",
        "decision_version",
        "eligible_for",
        "excluded_from",
        "query_pack_version",
        "schema_version",
        "split",
        "status",
        "system_under_test",
    }
    if set(benchmark) != expected_benchmark_fields:
        raise ValueError("benchmark fields differ from the frozen contract")
    if (
        benchmark.get("schema_version") != BENCHMARK_SCHEMA
        or benchmark.get("benchmark_version") != BENCHMARK_VERSION
        or benchmark.get("status") != "frozen_test_only"
        or benchmark.get("split") != "test"
        or benchmark.get("eligible_for") != ELIGIBLE_FOR
        or benchmark.get("excluded_from") != EXCLUDED_FROM
    ):
        raise ValueError("benchmark identity or usage boundary differs from contract")

    expected_manifest_fields = {
        "benchmark_file",
        "benchmark_sha256",
        "benchmark_version",
        "case_counts",
        "challenge_style_counts",
        "eligible_for",
        "excluded_from",
        "inputs",
        "positive_family_group_count",
        "schema_version",
        "single_token_family_ids",
        "split_counts",
        "status",
        "system_under_test",
    }
    if set(manifest) != expected_manifest_fields:
        raise ValueError("benchmark manifest fields differ from the frozen contract")
    if (
        manifest.get("schema_version") != BENCHMARK_MANIFEST_SCHEMA
        or manifest.get("benchmark_version") != BENCHMARK_VERSION
        or manifest.get("benchmark_file") != benchmark_path.name
        or manifest.get("benchmark_sha256") != _sha256(benchmark_path)
        or manifest.get("case_counts") != CASE_COUNTS
        or manifest.get("challenge_style_counts") != STYLE_COUNTS
        or manifest.get("split_counts") != {"dev": 0, "test": 105, "train": 0}
        or manifest.get("positive_family_group_count") != 42
        or manifest.get("status") != "frozen_test_only"
        or manifest.get("eligible_for") != ELIGIBLE_FOR
        or manifest.get("excluded_from") != EXCLUDED_FROM
    ):
        raise ValueError("benchmark manifest identity, counts, or checksum differs from contract")
    if benchmark.get("system_under_test") != manifest.get("system_under_test"):
        raise ValueError("benchmark and manifest system-under-test freezes differ")

    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict):
        raise TypeError("benchmark manifest inputs must be an object")
    evaluation_files = {"owner_decisions", "query_pack", "query_pack_manifest"}
    for name, reference in inputs.items():
        if not isinstance(reference, dict) or not isinstance(reference.get("file"), str):
            raise TypeError(f"benchmark manifest input {name} is invalid")
        path = (manifest_path.parent if name in evaluation_files else ROOT / "data") / reference[
            "file"
        ]
        if reference.get("sha256") != _sha256(path):
            raise ValueError(f"benchmark manifest input {name} checksum differs")

    sut = benchmark.get("system_under_test")
    if not isinstance(sut, dict):
        raise TypeError("benchmark system_under_test must be an object")
    expected_runtime = {
        "candidate_limit": 5,
        "dense_dimensions": 192,
        "dense_provider": HashingEmbedding.version,
        "human_catalog_version": "human-backed-catalog-v1",
        "normalizer_version": "identity.normalize_text-v1",
        "retriever_version": HumanKnowledgeRetriever.version,
        "review_family_knowledge_version": "review-family-knowledge-fandom-2025-r790665-v1",
        "rrf_k": 60,
    }
    for field, expected in expected_runtime.items():
        if sut.get(field) != expected:
            raise ValueError(f"frozen system-under-test {field} differs from runtime")
    source_paths = {
        "dense_source_sha256": ROOT / "src/product_variant_resolver/retrieval.py",
        "normalizer_source_sha256": ROOT / "src/product_variant_resolver/identity.py",
        "retriever_source_sha256": ROOT / "src/product_variant_resolver/human_knowledge.py",
        "human_catalog_sha256": ROOT / "data/human_backed_catalog.json",
        "review_family_knowledge_sha256": ROOT / "data/review_family_knowledge.json",
    }
    for field, path in source_paths.items():
        if sut.get(field) != _sha256(path):
            raise ValueError(f"frozen system-under-test {field} differs from runtime")

    cases = benchmark.get("cases")
    if not isinstance(cases, list) or len(cases) != 105:
        raise ValueError("benchmark must contain exactly 105 cases")
    ids: list[str] = []
    case_counts: Counter[str] = Counter()
    style_counts: Counter[str] = Counter()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise TypeError(f"case {index} must be an object")
        required = {
            "authored_at",
            "authored_by",
            "authoring_method",
            "case_id",
            "case_type",
            "casting_group_id",
            "challenge_style",
            "expected",
            "noise_tags",
            "query_text",
            "retriever_output_viewed",
            "review_reference",
            "split",
        }
        if set(case) != required:
            raise ValueError(f"case {index} fields differ from contract")
        case_id = case.get("case_id")
        query = case.get("query_text")
        if not isinstance(case_id, str) or not case_id or not isinstance(query, str) or not query:
            raise ValueError(f"case {index} identity or query is invalid")
        if case.get("split") != "test" or case.get("retriever_output_viewed") is not False:
            raise ValueError(f"{case_id}: evaluation boundary differs from contract")
        ids.append(case_id)
        case_counts[str(case.get("case_type"))] += 1
        style_counts[str(case.get("challenge_style"))] += 1
    if ids != sorted(ids) or len(ids) != len(set(ids)):
        raise ValueError("benchmark cases are duplicate or not deterministically ordered")
    if dict(case_counts) != CASE_COUNTS or dict(style_counts) != STYLE_COUNTS:
        raise ValueError("benchmark case composition differs from contract")


def _serialize_candidate(candidate: HumanKnowledgeCandidate) -> dict[str, Any]:
    document = candidate.document
    payload: dict[str, Any] = {
        "dense_rank": candidate.dense_rank,
        "dense_score": candidate.dense_score,
        "knowledge_id": document.knowledge_id,
        "knowledge_type": document.knowledge_type,
        "knowledge_uuid": str(document.knowledge_uuid),
        "matched_tokens": list(candidate.matched_tokens),
        "rrf_rank": candidate.rrf_rank,
        "rrf_score": candidate.rrf_score,
        "sparse_rank": candidate.sparse_rank,
        "sparse_score": candidate.sparse_score,
    }
    if isinstance(document, HumanVariantKnowledgeDocument):
        payload["casting_id"] = document.casting_id
        payload["provisional_variant_id"] = document.provisional_variant_id
    elif isinstance(document, ReviewFamilyKnowledgeDocument):
        payload["review_family_id"] = document.review_family_id
    else:  # pragma: no cover - the retriever's closed union prevents this
        raise TypeError("retriever returned an unsupported knowledge document")
    return payload


def _validate_expected(case_type: str, expected: Any, *, case_id: str) -> dict[str, Any]:
    if not isinstance(expected, dict):
        raise TypeError(f"{case_id}: expected label must be an object")
    fields = {
        "positive_family": {"knowledge_type", "review_family_id"},
        "merge_control": {"casting_id", "forbidden_review_family_id", "knowledge_type"},
        "hold_control": {"expected_materialized", "forbidden_review_family_id"},
        "unrelated_control": {"expected_candidate_count", "zero_token_overlap"},
    }
    if case_type not in fields or set(expected) != fields[case_type]:
        raise ValueError(f"{case_id}: expected label fields differ from contract")
    if case_type == "positive_family" and expected.get("knowledge_type") != "review_family":
        raise ValueError(f"{case_id}: positive expected type differs from contract")
    if case_type == "merge_control" and expected.get("knowledge_type") != "provisional_variant":
        raise ValueError(f"{case_id}: merge expected type differs from contract")
    if case_type == "hold_control" and expected.get("expected_materialized") is not False:
        raise ValueError(f"{case_id}: hold materialization expectation differs")
    if case_type == "unrelated_control" and expected != {
        "expected_candidate_count": 0,
        "zero_token_overlap": True,
    }:
        raise ValueError(f"{case_id}: unrelated expectation differs from contract")
    return dict(expected)


def _derive_case_outcome(
    case_type: str,
    expected: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
) -> tuple[int | None, list[int], str]:
    expected_rank: int | None = None
    forbidden_hits: list[int] = []
    if case_type == "positive_family":
        expected_rank = next(
            (
                item["rrf_rank"]
                for item in candidates
                if item["knowledge_type"] == "review_family"
                and item["review_family_id"] == expected["review_family_id"]
            ),
            None,
        )
    elif case_type == "merge_control":
        expected_rank = next(
            (
                item["rrf_rank"]
                for item in candidates
                if item["knowledge_type"] == "provisional_variant"
                and item["casting_id"] == expected["casting_id"]
            ),
            None,
        )
        forbidden_hits = [
            item["rrf_rank"]
            for item in candidates
            if item["knowledge_type"] == "review_family"
            and item["review_family_id"] == expected["forbidden_review_family_id"]
        ]
    elif case_type == "hold_control":
        forbidden_hits = [
            item["rrf_rank"]
            for item in candidates
            if item["knowledge_type"] == "review_family"
            and item["review_family_id"] == expected["forbidden_review_family_id"]
        ]

    if forbidden_hits:
        error_category = "forbidden_family_retrieved"
    elif case_type in {"positive_family", "merge_control"} and expected_rank is None:
        error_category = "no_candidates" if not candidates else "expected_identity_not_retrieved"
    elif case_type == "unrelated_control" and candidates:
        error_category = "unexpected_candidates"
    else:
        error_category = "none"
    return expected_rank, forbidden_hits, error_category


def evaluate_cases(
    cases: Sequence[Mapping[str, Any]],
    retriever: KnowledgeRetriever,
    *,
    candidate_limit: int = 5,
    signal_extractor: Callable[[str], ExtractedSignals] = extract_signals,
) -> list[dict[str, Any]]:
    """Retrieve first, then reveal and score each case's expected-label branch."""

    results: list[dict[str, Any]] = []
    for case in cases:
        case_id = case.get("case_id")
        case_type = case.get("case_type")
        group_id = case.get("casting_group_id")
        style = case.get("challenge_style")
        query_text = case.get("query_text")
        if (
            not isinstance(case_id, str)
            or not case_id
            or not isinstance(case_type, str)
            or not case_type
            or not isinstance(group_id, str)
            or not group_id
            or not isinstance(style, str)
            or not style
            or not isinstance(query_text, str)
            or not query_text
        ):
            raise ValueError("case metadata must contain non-empty strings")

        # This call intentionally occurs before any access to case["expected"].
        raw_candidates = retriever.retrieve(signal_extractor(query_text), candidate_limit)
        candidates = [_serialize_candidate(item) for item in raw_candidates]
        if [item["rrf_rank"] for item in candidates] != list(range(1, len(candidates) + 1)):
            raise ValueError(f"{case_id}: retriever returned unordered ranks")

        expected = _validate_expected(case_type, case.get("expected"), case_id=case_id)
        expected_rank, forbidden_hits, error_category = _derive_case_outcome(
            case_type, expected, candidates
        )

        results.append(
            {
                "candidate_count": len(candidates),
                "candidates": candidates,
                "case_id": case_id,
                "case_type": case_type,
                "casting_group_id": group_id,
                "challenge_style": style,
                "error_category": error_category,
                "expected": expected,
                "expected_rank": expected_rank,
                "forbidden_hit_ranks": forbidden_hits,
                "query_text": query_text,
            }
        )
    return results


def _ratio(numerator: float, denominator: int) -> float:
    if denominator <= 0:
        raise ValueError("metric denominator must be positive")
    return numerator / denominator


def summarize_results(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    positives = [item for item in results if item["case_type"] == "positive_family"]
    merge = [item for item in results if item["case_type"] == "merge_control"]
    holds = [item for item in results if item["case_type"] == "hold_control"]
    unrelated = [item for item in results if item["case_type"] == "unrelated_control"]
    if not positives or not merge or not holds or not unrelated:
        raise ValueError("all benchmark case types require non-zero denominators")

    positive_hits_1 = sum(item["expected_rank"] == 1 for item in positives)
    positive_hits_5 = sum(
        isinstance(item["expected_rank"], int) and item["expected_rank"] <= 5 for item in positives
    )
    reciprocal_rank_sum = sum(
        1 / item["expected_rank"]
        for item in positives
        if isinstance(item["expected_rank"], int) and item["expected_rank"] <= 5
    )
    style_raw: dict[str, dict[str, int]] = {}
    style_metrics: dict[str, float] = {}
    for style in POSITIVE_STYLES:
        subset = [item for item in positives if item["challenge_style"] == style]
        if not subset:
            raise ValueError(f"positive style {style} requires a non-zero denominator")
        hits = sum(
            isinstance(item["expected_rank"], int) and item["expected_rank"] <= 5 for item in subset
        )
        style_raw[style] = {"hits_at_5": hits, "total": len(subset)}
        style_metrics[style] = _ratio(hits, len(subset))

    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for item in positives:
        groups[str(item["casting_group_id"])].append(item)
    covered = sum(
        any(isinstance(item["expected_rank"], int) and item["expected_rank"] <= 5 for item in items)
        for items in groups.values()
    )
    merge_hits = sum(
        isinstance(item["expected_rank"], int) and item["expected_rank"] <= 5 for item in merge
    )
    forbidden_cases = sum(bool(item["forbidden_hit_ranks"]) for item in (*merge, *holds))
    forbidden_candidates = sum(len(item["forbidden_hit_ranks"]) for item in (*merge, *holds))
    unrelated_nonempty = sum(item["candidate_count"] > 0 for item in unrelated)

    raw_counts = {
        "family_coverage": {"covered_at_5": covered, "total": len(groups)},
        "merge_control": {"hits_at_5": merge_hits, "total": len(merge)},
        "positive": {
            "hits_at_1": positive_hits_1,
            "hits_at_5": positive_hits_5,
            "reciprocal_rank_sum_at_5": reciprocal_rank_sum,
            "total": len(positives),
        },
        "positive_styles": style_raw,
        "safety_controls": {
            "forbidden_family_hit_candidates": forbidden_candidates,
            "forbidden_family_hit_cases": forbidden_cases,
            "hold_control_total": len(holds),
            "unrelated_non_empty_results": unrelated_nonempty,
            "unrelated_total": len(unrelated),
        },
    }
    metrics: dict[str, float | int] = {
        "family_coverage_at_5": _ratio(covered, len(groups)),
        "forbidden_family_hits": forbidden_candidates,
        "lexical_variation_recall_at_5": style_metrics["lexical_variation"],
        "marketplace_noise_recall_at_5": style_metrics["marketplace_noise"],
        "merge_control_recall_at_5": _ratio(merge_hits, len(merge)),
        "positive_mrr_at_5": _ratio(reciprocal_rank_sum, len(positives)),
        "positive_recall_at_1": _ratio(positive_hits_1, len(positives)),
        "positive_recall_at_5": _ratio(positive_hits_5, len(positives)),
        "unrelated_non_empty_results": unrelated_nonempty,
    }
    gates: dict[str, dict[str, Any]] = {}
    for name, operator, threshold in GATE_POLICY:
        actual = metrics[name]
        passed = actual >= threshold if operator == ">=" else actual == threshold
        gates[name] = {
            "actual": actual,
            "operator": operator,
            "passed": passed,
            "threshold": threshold,
        }
    return {
        "error_category_counts": dict(
            sorted(Counter(str(item["error_category"]) for item in results).items())
        ),
        "gates": gates,
        "metrics": metrics,
        "raw_counts": raw_counts,
        "verdict": "PASS" if all(item["passed"] for item in gates.values()) else "FAIL",
    }


def build_evaluation(
    benchmark_path: Path = DEFAULT_BENCHMARK,
    manifest_path: Path = DEFAULT_MANIFEST,
    *,
    retriever: KnowledgeRetriever | None = None,
) -> dict[str, Any]:
    benchmark = _load_object(benchmark_path, label="benchmark")
    manifest = _load_object(manifest_path, label="benchmark manifest")
    _validate_frozen_inputs(benchmark_path, manifest_path, benchmark, manifest)

    if retriever is None:
        catalog = load_human_knowledge_catalog(
            ROOT / "data/human_backed_catalog.json",
            ROOT / "data/review_family_knowledge.json",
            ROOT / "data/review_family_knowledge_manifest.json",
        )
        retriever = HumanKnowledgeRetriever(catalog, HashingEmbedding(192))
    results = evaluate_cases(benchmark["cases"], retriever, candidate_limit=5)
    summary = summarize_results(results)
    return {
        "ai_eval_record": "docs/evidence/ai-evals/family-retrieval-holdout-v1.md",
        "benchmark": {
            "benchmark_sha256": _sha256(benchmark_path),
            "benchmark_version": BENCHMARK_VERSION,
            "case_count": len(results),
            "manifest_sha256": _sha256(manifest_path),
            "split": "test",
            "status": "frozen_test_only",
        },
        "cases": results,
        "eligible_for": ["human_knowledge_retrieval_quality_evidence"],
        "error_category_counts": summary["error_category_counts"],
        "evaluation_version": EVALUATION_VERSION,
        "excluded_from": EXCLUDED_FROM,
        "gate_policy": {
            name: {"operator": operator, "threshold": threshold}
            for name, operator, threshold in GATE_POLICY
        },
        "gates": summary["gates"],
        "limitations": [
            "synthetic_challenge_queries_not_live_marketplace_traffic",
            "casting_family_retrieval_not_release_variant_resolution",
            "small_42_family_domain_with_wide_uncertainty",
            "no_postgresql_pgvector_or_production_latency_measurement",
            "v1_holdout_becomes_development_known_after_this_report",
        ],
        "metrics": summary["metrics"],
        "query_preprocessor": {
            "source_file": "signals.py",
            "source_sha256": _sha256(ROOT / "src/product_variant_resolver/signals.py"),
            "version": "signals.extract_signals-v1",
        },
        "raw_counts": summary["raw_counts"],
        "schema_version": EVALUATION_SCHEMA,
        "system_under_test": benchmark["system_under_test"],
        "test_only_no_tuning": True,
        "tuning_policy": {
            "same_set_tuning_allowed": False,
            "changed_retriever_requires_new_holdout": True,
        },
        "verdict": summary["verdict"],
    }


def validate_evaluation_report(payload: Mapping[str, Any]) -> None:
    expected_fields = {
        "ai_eval_record",
        "benchmark",
        "cases",
        "eligible_for",
        "error_category_counts",
        "evaluation_version",
        "excluded_from",
        "gate_policy",
        "gates",
        "limitations",
        "metrics",
        "query_preprocessor",
        "raw_counts",
        "schema_version",
        "system_under_test",
        "test_only_no_tuning",
        "tuning_policy",
        "verdict",
    }
    if set(payload) != expected_fields:
        raise ValueError("evaluation fields differ from contract")
    if (
        payload.get("schema_version") != EVALUATION_SCHEMA
        or payload.get("evaluation_version") != EVALUATION_VERSION
        or payload.get("ai_eval_record") != "docs/evidence/ai-evals/family-retrieval-holdout-v1.md"
        or payload.get("eligible_for") != ["human_knowledge_retrieval_quality_evidence"]
        or payload.get("excluded_from") != EXCLUDED_FROM
        or payload.get("gate_policy")
        != {
            name: {"operator": operator, "threshold": threshold}
            for name, operator, threshold in GATE_POLICY
        }
        or payload.get("test_only_no_tuning") is not True
        or payload.get("tuning_policy")
        != {
            "same_set_tuning_allowed": False,
            "changed_retriever_requires_new_holdout": True,
        }
        or not isinstance(payload.get("limitations"), list)
        or not payload.get("limitations")
        or payload.get("verdict") not in {"PASS", "FAIL"}
    ):
        raise ValueError("evaluation identity or verdict differs from contract")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != 105:
        raise ValueError("evaluation must contain 105 raw case results")
    case_ids: list[str] = []
    for index, item in enumerate(cases):
        expected_case_fields = {
            "candidate_count",
            "candidates",
            "case_id",
            "case_type",
            "casting_group_id",
            "challenge_style",
            "error_category",
            "expected",
            "expected_rank",
            "forbidden_hit_ranks",
            "query_text",
        }
        if not isinstance(item, dict) or set(item) != expected_case_fields:
            raise ValueError(f"evaluation case {index} fields differ from contract")
        candidates = item.get("candidates")
        if not isinstance(candidates, list) or len(candidates) > 5:
            raise ValueError(f"evaluation case {index} candidates differ from K=5 contract")
        if item.get("candidate_count") != len(candidates):
            raise ValueError(f"evaluation case {index} candidate count differs from raw candidates")
        if [
            candidate.get("rrf_rank") for candidate in candidates if isinstance(candidate, dict)
        ] != list(range(1, len(candidates) + 1)):
            raise ValueError(f"evaluation case {index} candidate ranks are not ordered")
        case_id = item.get("case_id")
        case_type = item.get("case_type")
        if not isinstance(case_id, str) or not isinstance(case_type, str):
            raise TypeError(f"evaluation case {index} identity fields are invalid")
        expected = _validate_expected(case_type, item.get("expected"), case_id=case_id)
        derived = _derive_case_outcome(case_type, expected, candidates)
        recorded = (
            item.get("expected_rank"),
            item.get("forbidden_hit_ranks"),
            item.get("error_category"),
        )
        if recorded != derived:
            raise ValueError(f"{case_id}: recorded outcome differs from raw candidates")
        case_ids.append(case_id)
    if case_ids != sorted(case_ids) or len(case_ids) != len(set(case_ids)):
        raise ValueError("evaluation cases are duplicate or not deterministically ordered")
    recomputed = summarize_results(cases)
    for field in ("raw_counts", "metrics", "gates", "error_category_counts", "verdict"):
        if payload.get(field) != recomputed[field]:
            raise ValueError(f"evaluation {field} cannot be recomputed from raw cases")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, default=DEFAULT_BENCHMARK)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    try:
        evaluation = build_evaluation(arguments.benchmark, arguments.manifest)
        validate_evaluation_report(evaluation)
        text = _stable_json(evaluation)
        if arguments.check:
            _check_text(arguments.output, text)
            print("family retrieval evaluation is reproducible")
        else:
            _atomic_write(arguments.output, text)
            print(f"wrote {len(evaluation['cases'])} cases; verdict={evaluation['verdict']}")
        return 0
    except (OSError, TypeError, ValueError) as error:
        print(f"family retrieval evaluation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
