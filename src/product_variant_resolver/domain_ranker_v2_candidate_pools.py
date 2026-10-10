"""DRV2-T3 query-only Top-25 pools and generic CPU latency readiness."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import platform
import stat
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol
from uuid import NAMESPACE_URL, uuid5

from .domain_ranker_v2_authoring import (
    LOCAL_QUERY_PACK_PATH,
    QUERY_MANIFEST_PATH,
    SPLIT_MANIFEST_PATH,
    T1_GOVERNANCE_CONTENT_SHA256,
)
from .domain_ranker_v2_authoring import (
    check as check_t2,
)
from .domain_ranker_v2_governance import (
    CATALOG_PATH,
    CATALOG_SHA256,
    _canonical_bytes,
    _content_sha256,
    _file_sha256,
    _identity_key,
    _load_object,
    _require_file,
    _string,
    _validate_digest,
)
from .image_search_evaluation import build_evaluation_catalog, load_source_records
from .neural_reranker_comparison import freeze_candidate
from .neural_reranking import (
    POINTWISE_MODEL_ID,
    POINTWISE_REVISION,
    LocalPointwiseScorer,
    load_pointwise_model_config,
    rank_scores,
    render_candidate_text,
    validate_local_pointwise_model,
)
from .retrieval import (
    CandidateRetrievalService,
    DenseRetriever,
    HashingEmbedding,
    SparseRetriever,
    StructuredRetriever,
)
from .signals import extract_signals

SCHEMA_AUTHORIZATION = "pvr-drv2-t3-owner-authorization-v1"
SCHEMA_LOCAL_POOLS = "pvr-drv2-local-candidate-pools-v1"
SCHEMA_POOL_MANIFEST = "pvr-drv2-candidate-pool-manifest-v1"
SCHEMA_LATENCY = "pvr-drv2-generic-latency-readiness-v1"

DIRECTORY = Path("data/evaluation/domain-ranker-v2-remediation")
LOCAL_DIRECTORY = DIRECTORY / "local-t3"
LOCAL_POOLS_PATH = LOCAL_DIRECTORY / "candidate-pools.json"
AUTHORIZATION_PATH = DIRECTORY / "t3-owner-authorization.json"
POOL_MANIFEST_PATH = DIRECTORY / "candidate-pool-manifest.json"
LATENCY_PATH = DIRECTORY / "latency-readiness.json"

POINTWISE_CONFIG_PATH = Path("config/neural-reranker-comparison-v1.json")
POINTWISE_MODEL_PATH = Path("model-cache/neural-reranker-comparison-v1/pointwise")

T2_AUTHORIZATION_FILE_SHA256 = (
    "5187cdc24108b4d95579bf9bd1416dddb208a4b6ddf026b33ea94cf05d171457"
)
T2_QUERY_MANIFEST_FILE_SHA256 = (
    "ae03f68aa75f4646bfdc546cb93b3a0c2948e3cac1e87fa73f808f3a570d19f4"
)
T2_SPLIT_MANIFEST_FILE_SHA256 = (
    "52004c3534d34377bbc335a22b452a87a318211fe5536d4e95f5d814ea2b3ffc"
)
T2_QUERY_PACK_FILE_SHA256 = (
    "8f52043d615c1422018e5abe01670ba867c1908a6b268ce85754c71a9528d1fa"
)
T2_QUERY_PACK_CONTENT_SHA256 = (
    "149d7d867b9e270ffb805906aec64685d6823f11efcd68a59e9e74ba60134e6f"
)
POINTWISE_CONFIG_SHA256 = "3a88163cc7abc84468024f5e6410e0ca489a80a710b67b4c2474c4b4f7d7fad6"
POINTWISE_MANIFEST_SHA256 = (
    "32f889bb415ef5a56760a299da0635e8e1704d46fe0b11ded06c563de896feb8"
)
POINTWISE_WEIGHTS_SHA256 = (
    "821d1aa69520101d6e0737f78a042ae25b19e5cb9160701909d10434f4aeb0ae"
)
OWNER_STATEMENT_SHA256 = "d1c87988a770d3c14093392eadd15ce1b7dce06f600fe541681bfa0aa57d2920"

CANDIDATE_LIMIT = 25
DENSE_DIMENSIONS = 192
RRF_K = 60
MAX_LENGTH = 128
TORCH_THREADS = 1
WARMUP_RUNS = 3
MEASUREMENT_ROUNDS = 3
VALIDATION_QUERY_COUNT = 30
MAXIMUM_P95_MS = 200.0

_PUBLIC_FORBIDDEN_KEYS = {
    "candidate",
    "candidates",
    "case_id",
    "expected_full_identity",
    "prediction",
    "query",
    "records",
    "rows",
    "score",
    "scores",
    "target_uuid",
}


class PointwiseScorer(Protocol):
    version: str

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[float, ...]: ...


def _contains_public_row_level_data(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            key in _PUBLIC_FORBIDDEN_KEYS or _contains_public_row_level_data(child)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(_contains_public_row_level_data(child) for child in value)
    return False


def _write(path: Path, payload: object, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(payload))
    path.chmod(mode)


def _validate_t2_chain(root: Path) -> dict[str, Any]:
    for path, digest, label in (
        (DIRECTORY / "t2-owner-authorization.json", T2_AUTHORIZATION_FILE_SHA256, "T2 authorization"),
        (QUERY_MANIFEST_PATH, T2_QUERY_MANIFEST_FILE_SHA256, "T2 query manifest"),
        (SPLIT_MANIFEST_PATH, T2_SPLIT_MANIFEST_FILE_SHA256, "T2 split manifest"),
        (LOCAL_QUERY_PACK_PATH, T2_QUERY_PACK_FILE_SHA256, "T2 local query pack"),
    ):
        _require_file(root / path, digest, label)
    split = check_t2(root)
    if (
        split.get("query_pack_sha256") != T2_QUERY_PACK_CONTENT_SHA256
        or split.get("next_allowed_action") != "DRV2-T3_requires_separate_owner_authorization"
    ):
        raise ValueError("T2 does not authorize the separate T3 owner Gate")
    return split


def build_authorization(root: Path, code_commit: str) -> dict[str, Any]:
    _validate_t2_chain(root)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_AUTHORIZATION,
        "gate": "DRV2-T3",
        "authorization_date": "2026-10-09",
        "authorized_by": "project_owner",
        "owner_statement_sha256": OWNER_STATEMENT_SHA256,
        "decision": "freeze_query_only_top25_pools_and_generic_cpu_latency_readiness_only",
        "authorized_actions": [
            "retrieve_and_freeze_query_only_top25_candidate_pools",
            "score_frozen_pools_once_with_pinned_generic_cross_encoder",
            "measure_generic_cpu_latency_on_validation_only",
            "publish_aggregate_pool_and_latency_manifests_only",
        ],
        "prohibited_actions": [
            "inject_expected_identity_into_retrieval",
            "inspect_selection_quality_metrics",
            "hard_negative_mining_or_labeling",
            "model_training_or_checkpoint_creation",
            "calibration_final_evaluation_or_runtime_activation",
            "public_row_level_queries_candidates_scores_or_membership",
        ],
        "bindings": {
            "t1_governance_content_sha256": T1_GOVERNANCE_CONTENT_SHA256,
            "t2_query_pack_file_sha256": T2_QUERY_PACK_FILE_SHA256,
            "t2_query_pack_content_sha256": T2_QUERY_PACK_CONTENT_SHA256,
            "t2_query_manifest_file_sha256": T2_QUERY_MANIFEST_FILE_SHA256,
            "t2_split_manifest_file_sha256": T2_SPLIT_MANIFEST_FILE_SHA256,
            "catalog_file_sha256": CATALOG_SHA256,
            "generic_model_config_sha256": POINTWISE_CONFIG_SHA256,
            "generic_model_manifest_sha256": POINTWISE_MANIFEST_SHA256,
            "generic_model_weights_sha256": POINTWISE_WEIGHTS_SHA256,
            "implementation_commit": code_commit,
            "implementation_module_sha256": _file_sha256(
                root / "src/product_variant_resolver/domain_ranker_v2_candidate_pools.py"
            ),
        },
        "latency_protocol": {
            "partition": "ranker_validation",
            "query_count": VALIDATION_QUERY_COUNT,
            "candidates_per_query": CANDIDATE_LIMIT,
            "device": "cpu",
            "torch_threads": TORCH_THREADS,
            "batch_size": CANDIDATE_LIMIT,
            "max_length": MAX_LENGTH,
            "warmup_runs": WARMUP_RUNS,
            "measurement_rounds": MEASUREMENT_ROUNDS,
            "sample_count": VALIDATION_QUERY_COUNT * MEASUREMENT_ROUNDS,
            "p95_method": "nearest_rank",
            "maximum_p95_ms": MAXIMUM_P95_MS,
        },
    }
    result = {**body, "authorization_sha256": _content_sha256(body)}
    if _contains_public_row_level_data(result):
        raise ValueError("T3 authorization contains row-level material")
    return result


def _target_uuid(
    expected: Mapping[str, Any], source_by_identity: Mapping[tuple[str, ...], Mapping[str, Any]]
) -> str:
    source = source_by_identity.get(_identity_key(expected, catalog=False))
    if source is None:
        raise ValueError("T3 expected identity is absent from the frozen catalog")
    source_id = _string(source.get("source_record_id"), "source record id")
    return str(uuid5(NAMESPACE_URL, f"pvr:image-search-evaluation:{source_id}"))


def _load_default_scorer(root: Path) -> PointwiseScorer:
    _require_file(root / POINTWISE_CONFIG_PATH, POINTWISE_CONFIG_SHA256, "pointwise config")
    model_path = root / POINTWISE_MODEL_PATH
    _require_file(model_path / "manifest.json", POINTWISE_MANIFEST_SHA256, "pointwise manifest")
    _require_file(model_path / "model.safetensors", POINTWISE_WEIGHTS_SHA256, "pointwise weights")
    config = load_pointwise_model_config(root / POINTWISE_CONFIG_PATH)
    validate_local_pointwise_model(config, model_path)
    return LocalPointwiseScorer.load(config, model_path, batch_size=CANDIDATE_LIMIT)


def build_candidate_pools(
    root: Path,
    authorization: Mapping[str, Any],
    *,
    scorer: PointwiseScorer,
) -> tuple[dict[str, Any], dict[str, Any]]:
    query_pack = _load_object(root / LOCAL_QUERY_PACK_PATH)
    _validate_digest(query_pack, "query_pack_sha256", "T2 local query pack")
    records = query_pack.get("records")
    if not isinstance(records, list) or len(records) != 180:
        raise ValueError("T2 query pack must contain exactly 180 rows")

    source_records = load_source_records(root / CATALOG_PATH)
    source_by_identity: dict[tuple[str, ...], Mapping[str, Any]] = {}
    for source in source_records:
        key = _identity_key(source, catalog=True)
        if key in source_by_identity:
            raise ValueError("catalog contains duplicate exact identity keys")
        source_by_identity[key] = source
    catalog = build_evaluation_catalog(source_records)
    structured = StructuredRetriever(catalog)
    retrieval = CandidateRetrievalService(
        [
            SparseRetriever(catalog),
            DenseRetriever(catalog, HashingEmbedding(DENSE_DIMENSIONS)),
            structured,
        ],
        structured,
    )
    color_vocabulary = {item.product.color for item in catalog.products if item.product.color}
    series_vocabulary = {item.product.series for item in catalog.products if item.product.series}

    pending: list[tuple[dict[str, Any], str, tuple[Any, ...], tuple[str, ...]]] = []
    all_pairs: list[tuple[str, str]] = []
    for raw in records:
        if not isinstance(raw, dict) or not isinstance(raw.get("expected_full_identity"), dict):
            raise TypeError("T2 query row is malformed")
        query = _string(raw.get("query"), "query")
        signals = extract_signals(query, color_vocabulary, series_vocabulary)
        retrieved = retrieval.retrieve(signals, CANDIDATE_LIMIT)
        if len(retrieved) != CANDIDATE_LIMIT:
            raise ValueError("query-only retrieval did not produce exactly Top-25")
        frozen = tuple(freeze_candidate(candidate) for candidate in retrieved)
        rendered = tuple(render_candidate_text(candidate.text) for candidate in frozen)
        all_pairs.extend((query, text) for text in rendered)
        pending.append((raw, _target_uuid(raw["expected_full_identity"], source_by_identity), frozen, rendered))

    scores = scorer.score_pairs(all_pairs)
    if len(scores) != len(all_pairs) or any(not math.isfinite(score) for score in scores):
        raise ValueError("generic scorer returned invalid T3 scores")
    score_offset = 0
    rows: list[dict[str, Any]] = []
    per_partition: Counter[str] = Counter()
    retrieval_misses: Counter[str] = Counter()
    for raw, target_uuid, frozen, rendered in pending:
        row_scores = tuple(scores[score_offset : score_offset + CANDIDATE_LIMIT])
        score_offset += CANDIDATE_LIMIT
        ranked = rank_scores(frozen, row_scores)
        rank_by_uuid = {item.canonical_uuid: item.rank for item in ranked}
        score_by_uuid = {
            candidate.canonical_uuid: score
            for candidate, score in zip(frozen, row_scores, strict=True)
        }
        partition = _string(raw.get("partition"), "partition")
        if partition not in {"ranker_train", "ranker_validation", "ranker_selection"}:
            raise ValueError("T3 query partition is invalid")
        per_partition[partition] += 1
        if target_uuid not in rank_by_uuid:
            retrieval_misses[partition] += 1
        rows.append(
            {
                "case_id": raw["case_id"],
                "partition": partition,
                "query": raw["query"],
                "target_uuid": target_uuid,
                "target_retrieved": target_uuid in rank_by_uuid,
                "candidates": [
                    {
                        "canonical_uuid": candidate.canonical_uuid,
                        "canonical_id": candidate.canonical_id,
                        "rendered_text": text,
                        "rrf_rank": candidate.rrf_rank,
                        "rrf_score": candidate.rrf_score,
                        "source_ranks": dict(candidate.source_ranks),
                        "source_scores": dict(candidate.source_scores),
                        "structured_matches": list(candidate.structured_matches),
                        "structured_conflicts": list(candidate.structured_conflicts),
                        "generic_pointwise_score": score_by_uuid[candidate.canonical_uuid],
                        "generic_pointwise_rank": rank_by_uuid[candidate.canonical_uuid],
                    }
                    for candidate, text in zip(frozen, rendered, strict=True)
                ],
                "retrieval_output_sha256": _content_sha256(
                    tuple(candidate.canonical_uuid for candidate in frozen)
                ),
            }
        )
    if score_offset != len(scores):
        raise ValueError("generic score cursor did not consume every score")
    local_body: dict[str, Any] = {
        "schema_version": SCHEMA_LOCAL_POOLS,
        "status": "frozen_local_only",
        "authorization_sha256": authorization["authorization_sha256"],
        "query_pack_sha256": T2_QUERY_PACK_CONTENT_SHA256,
        "candidate_limit": CANDIDATE_LIMIT,
        "retrieval": {
            "sparse": "token-index-v1",
            "dense": f"hashing-v1:{DENSE_DIMENSIONS}",
            "structured": "structured-v1",
            "fusion": f"rrf:k={RRF_K}",
            "target_injection_allowed": False,
        },
        "generic_model": {
            "model_id": POINTWISE_MODEL_ID,
            "revision": POINTWISE_REVISION,
            "scorer_version": scorer.version,
            "score_semantics": "ranking_relevance_logit_not_probability_or_confidence",
        },
        "rows": rows,
    }
    local = {**local_body, "content_sha256": _content_sha256(local_body)}
    public_body: dict[str, Any] = {
        "schema_version": SCHEMA_POOL_MANIFEST,
        "status": "frozen_query_only_top25_pools",
        "authorization_sha256": authorization["authorization_sha256"],
        "query_pack_sha256": T2_QUERY_PACK_CONTENT_SHA256,
        "bindings": {
            "catalog_file_sha256": CATALOG_SHA256,
            "generic_model_id": POINTWISE_MODEL_ID,
            "generic_model_revision": POINTWISE_REVISION,
            "generic_model_config_sha256": POINTWISE_CONFIG_SHA256,
            "generic_model_manifest_sha256": POINTWISE_MANIFEST_SHA256,
            "generic_model_weights_sha256": POINTWISE_WEIGHTS_SHA256,
            "retrieval_module_sha256": _file_sha256(root / "src/product_variant_resolver/retrieval.py"),
            "signals_module_sha256": _file_sha256(root / "src/product_variant_resolver/signals.py"),
            "renderer_module_sha256": _file_sha256(
                root / "src/product_variant_resolver/neural_reranking.py"
            ),
        },
        "aggregate_counts": {
            "pool_count": len(rows),
            "candidate_count": len(rows) * CANDIDATE_LIMIT,
            "ranker_train_pool_count": per_partition["ranker_train"],
            "ranker_validation_pool_count": per_partition["ranker_validation"],
            "ranker_selection_pool_count": per_partition["ranker_selection"],
            "ranker_train_retrieval_miss_count": retrieval_misses["ranker_train"],
            "ranker_validation_retrieval_miss_count": retrieval_misses["ranker_validation"],
            "ranker_selection_retrieval_miss_count": retrieval_misses["ranker_selection"],
            "target_injection_count": 0,
            "hard_negative_labels_created": 0,
            "model_training_runs": 0,
            "selection_quality_evaluations": 0,
        },
        "private_pool_artifact_sha256": _content_sha256(local),
        "row_level_publication": False,
    }
    public = {**public_body, "manifest_sha256": _content_sha256(public_body)}
    if _contains_public_row_level_data(public):
        raise ValueError("T3 candidate-pool manifest contains row-level material")
    return local, public


def _nearest_rank(values: Sequence[float], probability: float) -> float:
    if not values or not 0.0 < probability <= 1.0:
        raise ValueError("percentile input is invalid")
    ordered = sorted(values)
    return ordered[math.ceil(probability * len(ordered)) - 1]


def runtime_environment() -> dict[str, Any]:
    torch = importlib.import_module("torch")
    transformers = importlib.import_module("transformers")
    sentence_transformers = importlib.import_module("sentence_transformers")
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "torch": _string(getattr(torch, "__version__", None), "torch version"),
        "transformers": _string(
            getattr(transformers, "__version__", None), "transformers version"
        ),
        "sentence_transformers": _string(
            getattr(sentence_transformers, "__version__", None),
            "sentence-transformers version",
        ),
        "executable_architecture_bits": 64 if sys.maxsize > 2**32 else 32,
    }


def build_latency_report(
    authorization: Mapping[str, Any],
    pool_manifest: Mapping[str, Any],
    latency_ms: Sequence[float],
    environment: Mapping[str, Any],
) -> dict[str, Any]:
    expected_samples = VALIDATION_QUERY_COUNT * MEASUREMENT_ROUNDS
    if len(latency_ms) != expected_samples or any(
        not math.isfinite(value) or value <= 0 for value in latency_ms
    ):
        raise ValueError("latency samples differ from the frozen 90-sample protocol")
    p50 = _nearest_rank(latency_ms, 0.50)
    p95 = _nearest_rank(latency_ms, 0.95)
    passed = p95 <= MAXIMUM_P95_MS
    body: dict[str, Any] = {
        "schema_version": SCHEMA_LATENCY,
        "status": "latency_ready" if passed else "latency_gate_failed",
        "authorization_sha256": authorization["authorization_sha256"],
        "candidate_pool_manifest_sha256": pool_manifest["manifest_sha256"],
        "protocol": authorization["latency_protocol"],
        "environment": dict(environment),
        "metrics": {
            "sample_count": len(latency_ms),
            "cpu_latency_p50_ms": p50,
            "cpu_latency_p95_ms": p95,
            "maximum_p95_ms": MAXIMUM_P95_MS,
            "gate_passed": passed,
        },
        "guardrails": {
            "hard_negative_labels_created": 0,
            "model_training_runs": 0,
            "selection_quality_evaluations": 0,
            "runtime_default_changed": False,
        },
        "next_allowed_action": (
            "DRV2-T4_requires_separate_owner_authorization"
            if passed
            else "stop_and_repair_generic_latency_before_DRV2-T4"
        ),
    }
    result = {**body, "readiness_sha256": _content_sha256(body)}
    if _contains_public_row_level_data(result):
        raise ValueError("T3 latency report contains row-level material")
    return result


def benchmark_validation_latency(
    local_pools: Mapping[str, Any],
    scorer: PointwiseScorer,
    *,
    clock_ns: Callable[[], int] = time.perf_counter_ns,
) -> list[float]:
    rows = local_pools.get("rows")
    if not isinstance(rows, list):
        raise TypeError("local pools are malformed")
    validation = [row for row in rows if isinstance(row, dict) and row.get("partition") == "ranker_validation"]
    if len(validation) != VALIDATION_QUERY_COUNT:
        raise ValueError("latency protocol requires exactly 30 validation pools")

    def pairs(row: Mapping[str, Any]) -> list[tuple[str, str]]:
        query = _string(row.get("query"), "validation query")
        candidates = row.get("candidates")
        if not isinstance(candidates, list) or len(candidates) != CANDIDATE_LIMIT:
            raise ValueError("validation pool must contain 25 candidates")
        return [
            (query, _string(candidate.get("rendered_text"), "candidate text"))
            for candidate in candidates
            if isinstance(candidate, dict)
        ]

    for _ in range(WARMUP_RUNS):
        scorer.score_pairs(pairs(validation[0]))
    samples: list[float] = []
    for _ in range(MEASUREMENT_ROUNDS):
        for row in validation:
            started = clock_ns()
            values = scorer.score_pairs(pairs(row))
            elapsed = (clock_ns() - started) / 1_000_000.0
            if len(values) != CANDIDATE_LIMIT:
                raise ValueError("generic latency scorer returned incomplete values")
            samples.append(elapsed)
    return samples


def materialize(root: Path, code_commit: str, *, scorer: PointwiseScorer | None = None) -> dict[str, Any]:
    output_paths = (AUTHORIZATION_PATH, POOL_MANIFEST_PATH, LATENCY_PATH, LOCAL_POOLS_PATH)
    if any((root / path).exists() for path in output_paths):
        raise FileExistsError("DRV2-T3 artifacts already exist")
    authorization = build_authorization(root, code_commit)
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    torch = importlib.import_module("torch")
    torch.set_num_threads(TORCH_THREADS)
    active_scorer = scorer if scorer is not None else _load_default_scorer(root)
    local_pools, pool_manifest = build_candidate_pools(root, authorization, scorer=active_scorer)
    latency_ms = benchmark_validation_latency(local_pools, active_scorer)
    latency = build_latency_report(authorization, pool_manifest, latency_ms, runtime_environment())
    _write(root / LOCAL_POOLS_PATH, local_pools, 0o600)
    _write(root / AUTHORIZATION_PATH, authorization, 0o644)
    _write(root / POOL_MANIFEST_PATH, pool_manifest, 0o644)
    _write(root / LATENCY_PATH, latency, 0o644)
    return latency


def check(root: Path) -> dict[str, Any]:
    _validate_t2_chain(root)
    authorization = _load_object(root / AUTHORIZATION_PATH)
    pool_manifest = _load_object(root / POOL_MANIFEST_PATH)
    latency = _load_object(root / LATENCY_PATH)
    local_pools = _load_object(root / LOCAL_POOLS_PATH)
    _validate_digest(authorization, "authorization_sha256", "T3 authorization")
    _validate_digest(pool_manifest, "manifest_sha256", "T3 pool manifest")
    _validate_digest(latency, "readiness_sha256", "T3 latency readiness")
    _validate_digest(local_pools, "content_sha256", "T3 local pools")
    if any(_contains_public_row_level_data(value) for value in (authorization, pool_manifest, latency)):
        raise ValueError("T3 public artifact contains row-level material")
    if pool_manifest.get("private_pool_artifact_sha256") != _content_sha256(local_pools):
        raise ValueError("T3 private pool binding changed")
    rows = local_pools.get("rows")
    if not isinstance(rows, list) or len(rows) != 180:
        raise ValueError("T3 local pool count changed")
    if stat.S_IMODE((root / LOCAL_POOLS_PATH).stat().st_mode) != 0o600:
        raise ValueError("T3 local pools must use mode 0600")
    for path in (AUTHORIZATION_PATH, POOL_MANIFEST_PATH, LATENCY_PATH):
        if stat.S_IMODE((root / path).stat().st_mode) != 0o644:
            raise ValueError("T3 public artifacts must use mode 0644")
    expected_next = (
        "DRV2-T4_requires_separate_owner_authorization"
        if latency.get("metrics", {}).get("gate_passed") is True
        else "stop_and_repair_generic_latency_before_DRV2-T4"
    )
    if latency.get("next_allowed_action") != expected_next:
        raise ValueError("T3 next action differs from latency Gate")
    return latency


def _current_commit(root: Path) -> str:
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    )
    commit = result.stdout.strip()
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise ValueError("could not resolve T3 implementation commit")
    return commit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize or check DRV2-T3 candidate pools")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--acknowledge-owner-authorization", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.run:
        if not args.acknowledge_owner_authorization:
            parser.error("--run requires --acknowledge-owner-authorization")
        result = materialize(root, _current_commit(root))
    elif args.check:
        result = check(root)
    else:
        parser.error("choose --run or --check")
    print(
        json.dumps(
            {
                "status": result["status"],
                "generic_cpu_p95_ms": result["metrics"]["cpu_latency_p95_ms"],
                "next_allowed_action": result["next_allowed_action"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
