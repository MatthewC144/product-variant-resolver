from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import Settings
from .schemas import ResolveRequest
from .service import ResolverService
from .signals import extract_signals


def safe_divide(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def recall_at_k(ranks: list[int | None], k: int) -> float:
    return safe_divide(sum(rank is not None and rank <= k for rank in ranks), len(ranks))


def reciprocal_rank(ranks: list[int | None], k: int = 10) -> float:
    return safe_divide(sum(1.0 / rank for rank in ranks if rank is not None and rank <= k), len(ranks))


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return ordered[index]


def load_benchmark(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload.get("cases"), list):
        raise ValueError("benchmark must contain cases[]")
    for case in payload["cases"]:
        if case.get("split") not in {"train", "dev", "test"}:
            raise ValueError(f"invalid split for {case.get('case_id')}")
        if case.get("expected_status") == "matched" and not case.get("expected_canonical_uuid"):
            raise ValueError(f"matched case lacks target: {case.get('case_id')}")
    families: dict[str, str] = {}
    for case in payload["cases"]:
        family, split = case["casting_family"], case["split"]
        if family in families and families[family] != split:
            raise ValueError(f"casting family leaks across splits: {family}")
        families[family] = split
    return payload


@dataclass(frozen=True, slots=True)
class EvaluationReport:
    dataset_version: str
    catalog_version: str
    split: str
    sample_count: int
    matched_count: int
    recall_at_10: float
    recall_at_25: float
    recall_at_50: float
    top1_accuracy: float
    mrr_at_10: float
    hard_negative_accuracy: float
    precision: float
    coverage: float
    false_match_rate: float
    abstention_rate: float
    pipeline_p50_latency_ms: float
    pipeline_p95_latency_ms: float
    raw_counts: dict[str, int | float]
    pipeline_latency_samples_ms: list[float]
    ablations: dict[str, dict[str, float]]
    ablation_raw_ranks: dict[str, list[int | None]]
    metadata: dict[str, Any]


def evaluate(settings: Settings, split: str = "test") -> EvaluationReport:
    if split != "test":
        raise ValueError("frozen final runner evaluates test only; use training modules for train/dev")
    benchmark = load_benchmark(settings.benchmark_path)
    service = ResolverService.from_settings(settings)
    cases = [case for case in benchmark["cases"] if case["split"] == split]
    ranks: list[int | None] = []
    latencies: list[float] = []
    correct_top1 = hard_total = hard_correct = predicted_matches = correct_matches = false_matches = 0
    wrong_identity_matches = 0
    matched_count = 0
    stage_ranks: dict[str, list[int | None]] = {
        "sparse": [], "dense": [], "rrf": [], "reranker": [],
    }
    pipeline_warmup_requests = min(5, len(cases))
    for case in cases[:pipeline_warmup_requests]:
        service.resolve(ResolveRequest(title=case["query"]))
    for case in cases:
        started = time.perf_counter()
        response = service.resolve(ResolveRequest(title=case["query"], debug=True, debug_candidate_limit=25))
        latencies.append((time.perf_counter() - started) * 1000)
        expected = case.get("expected_canonical_uuid")
        if case["expected_status"] == "matched":
            matched_count += 1
            signals = extract_signals(
                case["query"], service.color_vocabulary, service.series_vocabulary,
            )
            experiment_candidates = service.retrieval.retrieve(
                signals, settings.candidate_limit,
            )
            target = next((item for item in experiment_candidates
                           if str(item.product.canonical_uuid) == str(expected)), None)
            sparse_rank = target.source_ranks.get("sparse") if target else None
            dense_rank = target.source_ranks.get("dense") if target else None
            rrf_rank = target.rrf_rank if target else None
            experiment_candidates = service.reranker.rerank(signals, experiment_candidates)
            reranker_rank = target.reranker_rank if target else None
            rank = reranker_rank if settings.reranker_enabled else rrf_rank
            ranks.append(rank)
            stage_ranks["sparse"].append(sparse_rank)
            stage_ranks["dense"].append(dense_rank)
            stage_ranks["rrf"].append(rrf_rank)
            stage_ranks["reranker"].append(reranker_rank)
            # Ranking is evaluated independently from the downstream abstention decision.
            is_correct = rank == 1
            correct_top1 += is_correct
            if case.get("hard_negative"):
                hard_total += 1
                hard_correct += is_correct
        if response.status.value == "matched":
            predicted_matches += 1
            if case["expected_status"] == "matched":
                if str(response.canonical_uuid) == str(expected):
                    correct_matches += 1
                else:
                    wrong_identity_matches += 1
            else:
                false_matches += 1
    nonmatches = sum(case["expected_status"] != "matched" for case in cases)
    retrieval_hits = {
        f"retrieved_at_{k}": sum(rank is not None and rank <= k for rank in ranks)
        for k in (10, 25, 50)
    }
    reciprocal_rank_sum = sum(
        1.0 / rank for rank in ranks if rank is not None and rank <= 10
    )
    return EvaluationReport(
        dataset_version=str(benchmark.get("dataset_version", "unknown")), catalog_version=service.catalog.version,
        split=split, sample_count=len(cases), matched_count=matched_count,
        recall_at_10=recall_at_k(ranks, 10), recall_at_25=recall_at_k(ranks, 25),
        recall_at_50=recall_at_k(ranks, 50), top1_accuracy=safe_divide(correct_top1, matched_count),
        mrr_at_10=reciprocal_rank(ranks), hard_negative_accuracy=safe_divide(hard_correct, hard_total),
        precision=safe_divide(correct_matches, predicted_matches), coverage=safe_divide(correct_matches, matched_count),
        false_match_rate=safe_divide(false_matches, nonmatches),
        abstention_rate=safe_divide(len(cases) - predicted_matches, len(cases)),
        pipeline_p50_latency_ms=statistics.median(latencies) if latencies else 0.0,
        pipeline_p95_latency_ms=percentile(latencies, 0.95),
        raw_counts={"test_cases": len(cases), "matched_cases": matched_count,
                    **retrieval_hits, "reciprocal_rank_sum_at_10": reciprocal_rank_sum,
                    "correct_top1": correct_top1, "hard_total": hard_total,
                    "hard_correct": hard_correct, "predicted_matches": predicted_matches,
                    "correct_matches": correct_matches,
                    "wrong_identity_matches": wrong_identity_matches,
                    "false_matches": false_matches,
                    "nonmatch_cases": nonmatches},
        pipeline_latency_samples_ms=latencies,
        ablations={stage: {
            "top1_accuracy": safe_divide(sum(rank == 1 for rank in values), matched_count),
            "recall_at_25": recall_at_k(values, 25),
            "mrr_at_10": reciprocal_rank(values),
        } for stage, values in stage_ranks.items()},
        ablation_raw_ranks=stage_ranks,
        metadata={"runtime": platform.python_version(), "machine": platform.machine(),
                  "processor": platform.processor(), "platform": platform.platform(),
                  "candidate_k": settings.candidate_limit,
                  "dense_model": settings.dense_provider,
                  "default_ranker": ("heuristic-v1" if settings.reranker_enabled else "rrf"),
                  "reranker": (settings.reranker_provider
                                 if settings.reranker_enabled else "disabled"),
                  "reranker_runtime_enabled": settings.reranker_enabled,
                  "reranker_ablation_model": "heuristic-v1",
                  "external_cross_encoder_evaluated": False,
                  "calibrator_artifact": service.calibrator.artifact.artifact_version,
                  "calibrator_model": service.calibrator.artifact.model_version,
                  "policy_version": service.policy.version,
                  "policy_thresholds": {
                      "match": service.policy.match_threshold,
                      "no_match": service.policy.no_match_threshold,
                      "margin": service.policy.margin_threshold,
                      "max_conflicts": service.policy.max_conflicts,
                  },
                  "benchmark_sha256": hashlib.sha256(settings.benchmark_path.read_bytes()).hexdigest(),
                  "catalog_sha256": hashlib.sha256(settings.catalog_path.read_bytes()).hexdigest(),
                  "split_strategy": benchmark.get("split_strategy", "unknown"),
                  "source_note": benchmark.get("source_note", "unknown"),
                  "pipeline_latency_method": (
                      "direct ResolverService wall clock with debug payload construction; sequential "
                      "warmed process; service startup/index build excluded"
                  ),
                  "pipeline_warmup_requests": pipeline_warmup_requests,
                  "disclaimer": (
                      f"{len(cases)} synthetic fixture test cases; results do not establish production "
                      "accuracy, marketplace coverage, or production readiness."
                  )},
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = evaluate(Settings.from_env())
    content = json.dumps(asdict(report), indent=2)
    if arguments.output:
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(content + "\n", encoding="utf-8")
    else:
        print(content)


if __name__ == "__main__":
    main()
