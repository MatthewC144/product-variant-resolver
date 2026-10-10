"""DRSP-T5 aggregate-only generic/domain ranker comparison."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
import re
import stat
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

from .domain_ranker_partitions import LOCAL_POOLS_PATH, POOL_MANIFEST_PATH
from .domain_ranker_training import (
    BASE_MODEL_DIRECTORY,
    PACKAGE_DIRECTORY,
    SEEDS,
    load_selection_pools,
)

VERSION = "domain-ranker-selection-v1"
SCHEMA_AUTHORIZATION = "pvr-drsp-t5-owner-authorization-v1"
SCHEMA_RESULT = "pvr-drsp-t5-ranker-selection-v1"
SCHEMA_PRIVATE = "pvr-drsp-t5-private-diagnostics-v1"

AUTHORIZATION_PATH = Path("config/domain-ranker-selection-authorization-v1.json")
RESULT_PATH = Path("config/domain-ranker-selection-v1.json")
PRIVATE_PATH = Path(
    "artifacts/domain-ranker-selective-prediction-development-v1/local-t5/diagnostics.json"
)
T4_MANIFEST_PATH = PACKAGE_DIRECTORY / "manifest.json"
T4_AUTHORIZATION_PATH = PACKAGE_DIRECTORY / "owner-authorization.json"

FROZEN_T2_POOL_MANIFEST_SHA256 = "ec27f7608865bef5983ae90a780b8779fa6a715bc8253d9dfa4ce046f79e4ac3"
FROZEN_T2_PRIVATE_POOLS_SHA256 = "a54172a409e759dff89175aefc6a82a7de4c8828b5a7da5c119072bb8d9fa9a1"
FROZEN_T4_MANIFEST_FILE_SHA256 = "64f51dac2440db4bddc5aeb0672ab25bdf8069e590a464deb8e0b2cec8bb36af"
FROZEN_T4_MANIFEST_CONTENT_SHA256 = (
    "3ab623d01f1de0514af33b2f0bface9ca2acde17432174aaac27eb0f014404da"
)
FROZEN_T4_AUTHORIZATION_FILE_SHA256 = (
    "5fd9feac60decc2e18871d2d973e987140beb86be2cc67e24f90ff0a387a79a3"
)
FROZEN_T4_PACKAGE_SHA256 = "1cc26cc8aea072d02cb5fd25909b0adfcdbdfd2a7f642433945cf00211b002e1"
FROZEN_GENERIC_WEIGHTS_SHA256 = "821d1aa69520101d6e0737f78a042ae25b19e5cb9160701909d10434f4aeb0ae"
FROZEN_SEED_WEIGHTS = {
    17: "652f1e900bfeefd1536603e2d7e3b9c783df7b93273eb0a83a3bb0dce4360417",
    29: "315df109e64798108cb06fb249cb43f85f625e8224f34b51559b8d4c74cecb2d",
}
OWNER_STATEMENT_SHA256 = "37e6c4a73e7b5f0bafa28453bc8756ef3d45f87162d0d1f802d1ff4bc2b26389"

MAX_LENGTH = 128
WARMUP_RUNS = 3
MEASUREMENT_ROUNDS = 3
CANDIDATES_PER_QUERY = 25
SELECTION_QUERY_COUNT = 30


@dataclass(frozen=True, slots=True)
class AggregateMetrics:
    exact_top1_count: int
    exact_top1_rate: float
    casting_top1_count: int
    casting_top1_rate: float
    mrr_at_10: float
    recall_at_25_count: int
    recall_at_25: float
    same_family_hard_negative_correct: int
    same_family_hard_negative_total: int
    same_family_hard_negative_accuracy: float
    cpu_latency_sample_count: int
    cpu_latency_p50_ms: float
    cpu_latency_p95_ms: float


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _content_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _file_sha256(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{path}: required regular file is absent or unsafe")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_file(path: Path, expected: str, label: str) -> None:
    if _file_sha256(path) != expected:
        raise ValueError(f"{label} differs from the frozen SHA-256 binding")


def _load_object(path: Path) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        payload = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicates)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: could not read strict JSON") from error
    if not isinstance(payload, dict):
        raise TypeError(f"{path}: JSON root must be an object")
    return payload


def _validate_content_digest(payload: Mapping[str, Any], field: str, label: str) -> None:
    body = {key: value for key, value in payload.items() if key != field}
    if payload.get(field) != _content_sha256(body):
        raise ValueError(f"{label} checksum is stale")


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _current_git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    )
    commit = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("could not resolve the comparison code commit")
    return commit


def comparison_protocol() -> dict[str, Any]:
    return {
        "arms": ["generic", "domain_seed_17", "domain_seed_29"],
        "selection_query_count": SELECTION_QUERY_COUNT,
        "candidates_per_query": CANDIDATES_PER_QUERY,
        "ranking_tie_break": "score_desc_then_canonical_uuid_asc",
        "same_family_pair_rule": "target_score_strictly_greater_than_negative_score",
        "latency": {
            "device": "cpu",
            "torch_threads": 1,
            "batch_size": CANDIDATES_PER_QUERY,
            "warmup_runs": WARMUP_RUNS,
            "measurement_rounds": MEASUREMENT_ROUNDS,
            "p95_method": "nearest_rank",
        },
        "gates": {
            "minimum_exact_top1_case_delta": 3,
            "minimum_mrr_at_10_delta": 0.02,
            "minimum_same_family_accuracy_delta": 0.10,
            "minimum_casting_top1_case_delta": -1,
            "minimum_recall_at_25_delta": 0.0,
            "maximum_latency_ratio": 1.25,
            "maximum_latency_p95_ms": 200.0,
            "two_seed_direction": "both_seeds_exact_top1_and_mrr_deltas_strictly_positive",
        },
        "winner_tie_break": [
            "exact_top1_count_desc",
            "mrr_at_10_desc",
            "same_family_hard_negative_accuracy_desc",
            "cpu_latency_p95_ms_asc",
            "seed_asc",
        ],
    }


def _casting(rendered_text: object) -> str:
    text = _string(rendered_text, "candidate rendered text")
    fields: dict[str, str] = {}
    for part in text.split("|"):
        key, separator, value = part.strip().partition("=")
        if separator:
            fields[key.strip().casefold()] = value.strip().casefold()
    casting = fields.get("casting")
    if not casting or casting == "<missing>":
        raise ValueError("candidate casting is missing from rendered text")
    return " ".join(casting.split())


def _nearest_rank_percentile(values: Sequence[float], probability: float) -> float:
    if not values or not 0.0 < probability <= 1.0:
        raise ValueError("percentile needs values and a probability in (0, 1]")
    ordered = sorted(values)
    return ordered[math.ceil(probability * len(ordered)) - 1]


def aggregate_metrics(
    pools: Sequence[Mapping[str, Any]],
    score_rows: Sequence[Sequence[float]],
    latency_ms: Sequence[float],
) -> tuple[AggregateMetrics, list[dict[str, Any]]]:
    if len(pools) != SELECTION_QUERY_COUNT or len(score_rows) != len(pools):
        raise ValueError("T5 requires exactly 30 aligned selection pools")
    exact_top1 = casting_top1 = recall_count = hard_correct = hard_total = 0
    reciprocal_sum = 0.0
    private_rows: list[dict[str, Any]] = []
    for pool, scores in zip(pools, score_rows, strict=True):
        candidates = pool.get("candidates")
        if not isinstance(candidates, list) or len(candidates) != CANDIDATES_PER_QUERY:
            raise ValueError("T5 selection pools must each contain 25 candidates")
        if len(scores) != len(candidates):
            raise ValueError("candidate and score rows differ")
        target_uuid = _string(pool.get("target_uuid"), "target UUID")
        candidate_by_uuid: dict[str, Mapping[str, Any]] = {}
        ranked: list[tuple[float, str]] = []
        for candidate, raw_score in zip(candidates, scores, strict=True):
            if not isinstance(candidate, dict):
                raise TypeError("candidate must be an object")
            uuid = _string(candidate.get("canonical_uuid"), "candidate UUID")
            score = float(raw_score)
            if not math.isfinite(score):
                raise ValueError("ranker score is non-finite")
            candidate_by_uuid[uuid] = candidate
            ranked.append((score, uuid))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        if target_uuid not in candidate_by_uuid:
            raise ValueError("selection target is absent from its frozen pool")
        recall_count += 1
        rank = next(index for index, (_, uuid) in enumerate(ranked, 1) if uuid == target_uuid)
        top_uuid = ranked[0][1]
        target_casting = _casting(candidate_by_uuid[target_uuid].get("rendered_text"))
        top_casting = _casting(candidate_by_uuid[top_uuid].get("rendered_text"))
        exact = top_uuid == target_uuid
        casting = top_casting == target_casting
        exact_top1 += int(exact)
        casting_top1 += int(casting)
        if rank <= 10:
            reciprocal_sum += 1.0 / rank
        score_by_uuid = {uuid: score for score, uuid in ranked}
        row_hard_correct = row_hard_total = 0
        for uuid, candidate in candidate_by_uuid.items():
            if uuid == target_uuid or _casting(candidate.get("rendered_text")) != target_casting:
                continue
            row_hard_total += 1
            row_hard_correct += int(score_by_uuid[target_uuid] > score_by_uuid[uuid])
        hard_correct += row_hard_correct
        hard_total += row_hard_total
        case_id = _string(pool.get("case_id"), "case ID")
        private_rows.append(
            {
                "case_id_sha256": hashlib.sha256(case_id.encode()).hexdigest(),
                "target_rank": rank,
                "exact_top1": exact,
                "casting_top1": casting,
                "same_family_correct": row_hard_correct,
                "same_family_total": row_hard_total,
            }
        )
    if hard_total == 0:
        raise ValueError("same-family hard-negative gate is not evaluable")
    if len(latency_ms) != SELECTION_QUERY_COUNT * MEASUREMENT_ROUNDS:
        raise ValueError("latency samples differ from the frozen 90-sample protocol")
    metrics = AggregateMetrics(
        exact_top1_count=exact_top1,
        exact_top1_rate=exact_top1 / len(pools),
        casting_top1_count=casting_top1,
        casting_top1_rate=casting_top1 / len(pools),
        mrr_at_10=reciprocal_sum / len(pools),
        recall_at_25_count=recall_count,
        recall_at_25=recall_count / len(pools),
        same_family_hard_negative_correct=hard_correct,
        same_family_hard_negative_total=hard_total,
        same_family_hard_negative_accuracy=hard_correct / hard_total,
        cpu_latency_sample_count=len(latency_ms),
        cpu_latency_p50_ms=_nearest_rank_percentile(latency_ms, 0.50),
        cpu_latency_p95_ms=_nearest_rank_percentile(latency_ms, 0.95),
    )
    return metrics, private_rows


def evaluate_gate(
    generic: AggregateMetrics,
    domain: AggregateMetrics,
    *,
    seed_direction_stable: bool,
) -> dict[str, Any]:
    deltas = {
        "exact_top1_case_delta": domain.exact_top1_count - generic.exact_top1_count,
        "mrr_at_10_delta": domain.mrr_at_10 - generic.mrr_at_10,
        "same_family_accuracy_delta": (
            domain.same_family_hard_negative_accuracy - generic.same_family_hard_negative_accuracy
        ),
        "casting_top1_case_delta": domain.casting_top1_count - generic.casting_top1_count,
        "recall_at_25_delta": domain.recall_at_25 - generic.recall_at_25,
        "latency_p95_ratio": domain.cpu_latency_p95_ms / generic.cpu_latency_p95_ms,
    }
    checks = {
        "exact_top1_improves_by_at_least_3_cases": deltas["exact_top1_case_delta"] >= 3,
        "mrr_at_10_improves_by_at_least_0_02": deltas["mrr_at_10_delta"] >= 0.02 - 1e-12,
        "same_family_accuracy_improves_by_at_least_0_10": (
            deltas["same_family_accuracy_delta"] >= 0.10 - 1e-12
        ),
        "casting_top1_regresses_by_no_more_than_1_case": (deltas["casting_top1_case_delta"] >= -1),
        "recall_at_25_does_not_fall": deltas["recall_at_25_delta"] >= 0.0,
        "cpu_p95_at_most_1_25x_generic": deltas["latency_p95_ratio"] <= 1.25,
        "cpu_p95_at_most_200_ms": domain.cpu_latency_p95_ms <= 200.0,
        "two_seed_improvement_direction_is_stable": seed_direction_stable,
    }
    return {"deltas": deltas, "checks": checks, "passed": all(checks.values())}


def select_winner(
    metrics: Mapping[str, AggregateMetrics], gates: Mapping[str, Mapping[str, Any]]
) -> str | None:
    eligible = [name for name in ("domain_seed_17", "domain_seed_29") if gates[name]["passed"]]
    if not eligible:
        return None

    def order(name: str) -> tuple[float, float, float, float, int]:
        value = metrics[name]
        seed = int(name.rsplit("_", 1)[1])
        return (
            -float(value.exact_top1_count),
            -value.mrr_at_10,
            -value.same_family_hard_negative_accuracy,
            value.cpu_latency_p95_ms,
            seed,
        )

    return min(eligible, key=order)


def _load_dependencies() -> tuple[Any, Any, Any]:
    try:
        torch = importlib.import_module("torch")
        transformers = importlib.import_module("transformers")
    except ImportError as error:
        raise RuntimeError("DRSP-T5 requires the pinned reranking environment") from error
    tokenizer_class = getattr(transformers, "AutoTokenizer", None)
    model_class = getattr(transformers, "AutoModelForSequenceClassification", None)
    if tokenizer_class is None or model_class is None:
        raise RuntimeError("installed transformers API is incompatible")
    return torch, tokenizer_class, model_class


def _score_arm(
    model: Any,
    tokenizer: Any,
    pools: Sequence[dict[str, Any]],
    torch: Any,
) -> tuple[list[list[float]], list[float]]:
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    torch.set_num_threads(1)
    model.eval()

    def score_pool(pool: Mapping[str, Any]) -> list[float]:
        query = _string(pool.get("query"), "selection query")
        candidates = cast(list[dict[str, Any]], pool["candidates"])
        encoded = tokenizer(
            [query] * len(candidates),
            [_string(candidate.get("rendered_text"), "candidate text") for candidate in candidates],
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        )
        with torch.no_grad():
            logits = model(**encoded).logits.reshape(-1)
        values = [float(value) for value in logits.detach().cpu().tolist()]
        if len(values) != len(candidates) or not all(math.isfinite(value) for value in values):
            raise ValueError("ranker returned an invalid score vector")
        return values

    for _ in range(WARMUP_RUNS):
        score_pool(pools[0])
    first_scores: list[list[float]] = []
    latency_ms: list[float] = []
    for round_index in range(MEASUREMENT_ROUNDS):
        for pool in pools:
            started = time.perf_counter_ns()
            values = score_pool(pool)
            latency_ms.append((time.perf_counter_ns() - started) / 1_000_000.0)
            if round_index == 0:
                first_scores.append(values)
    return first_scores, latency_ms


def _validate_inputs(root: Path) -> dict[str, Any]:
    _require_file(root / POOL_MANIFEST_PATH, FROZEN_T2_POOL_MANIFEST_SHA256, "T2 manifest")
    _require_file(root / LOCAL_POOLS_PATH, FROZEN_T2_PRIVATE_POOLS_SHA256, "T2 private pools")
    _require_file(root / T4_MANIFEST_PATH, FROZEN_T4_MANIFEST_FILE_SHA256, "T4 manifest")
    _require_file(
        root / T4_AUTHORIZATION_PATH,
        FROZEN_T4_AUTHORIZATION_FILE_SHA256,
        "T4 authorization",
    )
    _require_file(
        root / BASE_MODEL_DIRECTORY / "model.safetensors",
        FROZEN_GENERIC_WEIGHTS_SHA256,
        "generic weights",
    )
    for seed, expected in FROZEN_SEED_WEIGHTS.items():
        _require_file(
            root / PACKAGE_DIRECTORY / f"seed-{seed}/model.safetensors",
            expected,
            f"domain seed {seed} weights",
        )
    manifest = _load_object(root / T4_MANIFEST_PATH)
    _validate_content_digest(manifest, "manifest_sha256", "T4 manifest")
    if (
        manifest.get("manifest_sha256") != FROZEN_T4_MANIFEST_CONTENT_SHA256
        or manifest.get("package_sha256") != FROZEN_T4_PACKAGE_SHA256
        or manifest.get("release_gate_passed") is not True
        or manifest.get("next_allowed_action") != "DRSP-T5_requires_separate_owner_authorization"
    ):
        raise ValueError("T4 is not the frozen released parent of T5")
    return manifest


def build_authorization(root: Path, code_commit: str) -> dict[str, Any]:
    _validate_inputs(root)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_AUTHORIZATION,
        "gate": "DRSP-T5",
        "authorization_date": "2026-10-09",
        "authorized_by": "project_owner",
        "owner_statement_sha256": OWNER_STATEMENT_SHA256,
        "decision": "compare_generic_and_two_domain_rankers_on_frozen_selection_only",
        "authorized_actions": [
            "score_the_frozen_30_query_t2_ranker_selection_pools",
            "publish_aggregate_quality_latency_and_gate_results",
            "freeze_one_domain_winner_or_winner_null",
        ],
        "prohibited_actions": [
            "calibration_fit_or_threshold_selection",
            "positive_test_or_negative_holdout_read_or_scoring",
            "no_match_development_read_or_scoring",
            "fresh_final_evaluation",
            "runtime_change_or_activation",
            "public_row_level_queries_predictions_or_scores",
        ],
        "bindings": {
            "t2_pool_manifest_file_sha256": FROZEN_T2_POOL_MANIFEST_SHA256,
            "t2_private_pool_file_sha256": FROZEN_T2_PRIVATE_POOLS_SHA256,
            "t4_manifest_file_sha256": FROZEN_T4_MANIFEST_FILE_SHA256,
            "t4_manifest_content_sha256": FROZEN_T4_MANIFEST_CONTENT_SHA256,
            "t4_package_sha256": FROZEN_T4_PACKAGE_SHA256,
            "generic_weights_sha256": FROZEN_GENERIC_WEIGHTS_SHA256,
            "seed_weights_sha256": {str(key): value for key, value in FROZEN_SEED_WEIGHTS.items()},
            "comparison_code_commit": code_commit,
            "comparison_module_sha256": _file_sha256(
                root / "src/product_variant_resolver/domain_ranker_comparison.py"
            ),
        },
        "protocol": comparison_protocol(),
        "rights_state": "owner_attested_not_independently_verified",
        "authority_scope": "frozen_third_party_catalog_relative_not_manufacturer_or_global_truth",
    }
    return {**body, "authorization_sha256": _content_sha256(body)}


def _generic_ordering_matches_frozen(
    pools: Sequence[Mapping[str, Any]], scores: Sequence[Sequence[float]]
) -> bool:
    for pool, score_row in zip(pools, scores, strict=True):
        candidates = cast(list[dict[str, Any]], pool["candidates"])
        ranked = sorted(
            zip(score_row, candidates, strict=True),
            key=lambda item: (-float(item[0]), _string(item[1].get("canonical_uuid"), "UUID")),
        )
        for rank, (_, candidate) in enumerate(ranked, 1):
            if candidate.get("generic_pointwise_rank") != rank:
                return False
    return True


def execute(root: Path) -> dict[str, Any]:
    _validate_inputs(root)
    pools = load_selection_pools(root)
    authorization = build_authorization(root, _current_git_commit(root))
    torch, tokenizer_class, model_class = _load_dependencies()
    tokenizer = tokenizer_class.from_pretrained(
        root / PACKAGE_DIRECTORY, local_files_only=True, trust_remote_code=False
    )
    model_paths = {
        "generic": root / BASE_MODEL_DIRECTORY,
        "domain_seed_17": root / PACKAGE_DIRECTORY / "seed-17",
        "domain_seed_29": root / PACKAGE_DIRECTORY / "seed-29",
    }
    metrics: dict[str, AggregateMetrics] = {}
    private_rows: dict[str, list[dict[str, Any]]] = {}
    raw_scores: dict[str, list[list[float]]] = {}
    private_latencies: dict[str, list[float]] = {}
    for name, model_path in model_paths.items():
        model = model_class.from_pretrained(
            model_path,
            local_files_only=True,
            trust_remote_code=False,
            use_safetensors=True,
            dtype=torch.float32,
        )
        scores, latencies = _score_arm(model, tokenizer, pools, torch)
        arm_metrics, rows = aggregate_metrics(pools, scores, latencies)
        metrics[name] = arm_metrics
        private_rows[name] = rows
        raw_scores[name] = scores
        private_latencies[name] = latencies
        del model
    if not _generic_ordering_matches_frozen(pools, raw_scores["generic"]):
        raise ValueError("rescored generic ordering differs from the frozen T2 ordering")

    generic = metrics["generic"]
    seed_direction_stable = all(
        metrics[f"domain_seed_{seed}"].exact_top1_count > generic.exact_top1_count
        and metrics[f"domain_seed_{seed}"].mrr_at_10 > generic.mrr_at_10
        for seed in SEEDS
    )
    gates = {
        name: evaluate_gate(generic, metrics[name], seed_direction_stable=seed_direction_stable)
        for name in ("domain_seed_17", "domain_seed_29")
    }
    winner = select_winner(metrics, gates)
    private_body: dict[str, Any] = {
        "schema_version": SCHEMA_PRIVATE,
        "version": VERSION,
        "authorization_sha256": authorization["authorization_sha256"],
        "arms": {
            name: {"rows": private_rows[name], "latency_ms": private_latencies[name]}
            for name in model_paths
        },
    }
    private = {**private_body, "content_sha256": _content_sha256(private_body)}
    private_path = root / PRIVATE_PATH
    private_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    private_path.write_bytes(_canonical_bytes(private))
    private_path.chmod(stat.S_IRUSR | stat.S_IWUSR)

    (root / AUTHORIZATION_PATH).write_bytes(_canonical_bytes(authorization))
    result_body: dict[str, Any] = {
        "schema_version": SCHEMA_RESULT,
        "version": VERSION,
        "status": "winner_selected" if winner is not None else "ranker_gate_failed",
        "authorization_sha256": authorization["authorization_sha256"],
        "authorization_file_sha256": _file_sha256(root / AUTHORIZATION_PATH),
        "input_bindings": cast(Mapping[str, Any], authorization["bindings"]),
        "protocol": comparison_protocol(),
        "generic_ordering_matches_frozen_t2": True,
        "metrics": {name: asdict(value) for name, value in metrics.items()},
        "gates": gates,
        "winner": winner,
        "selected_checkpoint_sha256": (
            None if winner is None else FROZEN_SEED_WEIGHTS[int(winner.rsplit("_", 1)[1])]
        ),
        "guardrails": {
            "ranker_selection_rows_scored": SELECTION_QUERY_COUNT,
            "positive_test_rows_read_or_scored": 0,
            "negative_holdout_rows_read_or_scored": 0,
            "no_match_development_rows_read_or_scored": 0,
            "calibration_fits": 0,
            "fresh_final_evaluations": 0,
            "runtime_default_changed": False,
            "runtime_activations": 0,
            "public_row_level_records": 0,
        },
        "rights_state": "owner_attested_not_independently_verified",
        "limitations": [
            "selection_partition_was_already_used_for_t4_early_stopping",
            "small_catalog_relative_development_comparison",
            "not_manufacturer_or_global_truth",
            "not_calibrated_or_final_evaluated",
            "runtime_not_activated",
        ],
        "next_allowed_action": (
            "DRSP-T6_requires_separate_owner_authorization_and_new_admissible_calibration_positives"
            if winner is not None
            else "stop_ranker_gate_failed_no_DRSP-T6"
        ),
    }
    result = {**result_body, "result_sha256": _content_sha256(result_body)}
    (root / RESULT_PATH).write_bytes(_canonical_bytes(result))
    return result


def check(root: Path) -> dict[str, Any]:
    _validate_inputs(root)
    authorization = _load_object(root / AUTHORIZATION_PATH)
    _validate_content_digest(authorization, "authorization_sha256", "T5 authorization")
    result = _load_object(root / RESULT_PATH)
    _validate_content_digest(result, "result_sha256", "T5 result")
    if result.get("authorization_sha256") != authorization.get("authorization_sha256"):
        raise ValueError("T5 result is not bound to its authorization")
    if result.get("authorization_file_sha256") != _file_sha256(root / AUTHORIZATION_PATH):
        raise ValueError("T5 authorization file hash differs")
    guardrails = result.get("guardrails")
    expected = {
        "positive_test_rows_read_or_scored": 0,
        "negative_holdout_rows_read_or_scored": 0,
        "no_match_development_rows_read_or_scored": 0,
        "calibration_fits": 0,
        "fresh_final_evaluations": 0,
        "runtime_activations": 0,
        "public_row_level_records": 0,
    }
    if not isinstance(guardrails, dict) or any(
        guardrails.get(key) != value for key, value in expected.items()
    ):
        raise ValueError("T5 guardrail evidence is invalid")
    winner = result.get("winner")
    if winner is not None and winner not in {"domain_seed_17", "domain_seed_29"}:
        raise ValueError("T5 winner is invalid")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute or validate the frozen DRSP-T5 comparison"
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = check(args.root.resolve()) if args.check else execute(args.root.resolve())
    print(
        json.dumps(
            {
                "status": "valid" if args.check else result["status"],
                "winner": result["winner"],
                "result_sha256": result["result_sha256"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
