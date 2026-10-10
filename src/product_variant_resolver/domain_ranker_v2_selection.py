"""DRV2-T6 one-shot untouched generic/domain ranker selection."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import stat
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from .domain_ranker_comparison import (
    AggregateMetrics,
    aggregate_metrics,
    evaluate_gate,
    select_winner,
)
from .domain_ranker_v2_candidate_pools import (
    CANDIDATE_LIMIT,
    LOCAL_POOLS_PATH,
    _contains_public_row_level_data,
)
from .domain_ranker_v2_governance import (
    _canonical_bytes,
    _content_sha256,
    _file_sha256,
    _load_object,
    _require_file,
    _string,
    _validate_digest,
)
from .domain_ranker_v2_latency_repair import (
    LOCAL_ONNX_PATH as GENERIC_ONNX_PATH,
)
from .domain_ranker_v2_latency_repair import OnnxPointwiseScorer
from .domain_ranker_v2_training import (
    MANIFEST_PATH as T5_MANIFEST_PATH,
)
from .domain_ranker_v2_training import PACKAGE_DIRECTORY, SEEDS
from .domain_ranker_v2_training import check as check_t5

SCHEMA_AUTHORIZATION = "pvr-drv2-t6-owner-authorization-v1"
SCHEMA_RESULT = "pvr-drv2-t6-ranker-selection-v1"
SCHEMA_PRIVATE = "pvr-drv2-t6-private-diagnostics-v1"
VERSION = "domain-ranker-v2-remediation-selection-v1"

DIRECTORY = Path("data/evaluation/domain-ranker-v2-remediation")
LOCAL_DIRECTORY = DIRECTORY / "local-t6"
AUTHORIZATION_PATH = DIRECTORY / "t6-owner-authorization.json"
RESULT_PATH = DIRECTORY / "ranker-selection.json"
PRIVATE_PATH = LOCAL_DIRECTORY / "diagnostics.json"

T5_MANIFEST_FILE_SHA256 = "86b1fa8408a4a8d4a638cc0ab917f92e752cdd507f38c7ab564f99ee2b47c605"
T5_MANIFEST_CONTENT_SHA256 = "70df0fb9cb4700e4d34619471c8a582343093d0569a95b3af94d214d859cf5ee"
T5_PACKAGE_SHA256 = "28977b447a3ec7b7fa970d7c5eec8ce3b0a2c5f33b4c50c3dbd6dfca7dbb7663"
T3_LOCAL_POOLS_FILE_SHA256 = "0c889bfc06755a49ba779f2df64a4e4d87d3de676bf47063fcfcdec454022b24"
GENERIC_ONNX_FILE_SHA256 = "2c668e0e1bb772e0a9ba4b14e08875ec750a58e39b3ca9790e166eb927fbc42f"
SEED_WEIGHTS_SHA256 = {
    17: "5a4f2ea21b93a864f1e1ddb54523f68a0ae2766db555535c0f35721588b6e297",
    29: "83db9ab75c1c431ce2c6f3e4c717bae821c187a060f0864e45204ee8a4056e99",
}
OWNER_STATEMENT_SHA256 = "37e6c4a73e7b5f0bafa28453bc8756ef3d45f87162d0d1f802d1ff4bc2b26389"

SELECTION_QUERY_COUNT = 30
WARMUP_RUNS = 3
MEASUREMENT_ROUNDS = 3
MAX_LENGTH = 128
ONNX_OPSET = 17
MAX_ABSOLUTE_LOGIT_DELTA = 2e-5


def comparison_protocol() -> dict[str, Any]:
    """Return the immutable T6 decision protocol frozen before selection scoring."""
    return {
        "arms": ["generic", "domain_seed_17", "domain_seed_29"],
        "selection_query_count": SELECTION_QUERY_COUNT,
        "candidates_per_query": CANDIDATE_LIMIT,
        "ranking_tie_break": "score_desc_then_canonical_uuid_asc",
        "same_family_pair_rule": "target_score_strictly_greater_than_negative_score",
        "inference_equivalence": {
            "domain_checkpoint_source_dtype": "float16_safetensors",
            "comparison_dtype": "float32_onnx",
            "onnx_opset": ONNX_OPSET,
            "maximum_absolute_logit_delta": MAX_ABSOLUTE_LOGIT_DELTA,
            "required_identical_top25_order_count_per_domain_arm": SELECTION_QUERY_COUNT,
            "generic_required_to_match_frozen_top25_order": True,
        },
        "latency": {
            "runtime": "onnxruntime_cpu",
            "provider": "CPUExecutionProvider",
            "intra_op_threads": 1,
            "inter_op_threads": 1,
            "execution_mode": "sequential",
            "graph_optimization": "all",
            "batch_size": CANDIDATE_LIMIT,
            "warmup_runs": WARMUP_RUNS,
            "measurement_rounds": MEASUREMENT_ROUNDS,
            "sample_count_per_arm": SELECTION_QUERY_COUNT * MEASUREMENT_ROUNDS,
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
        "failure_rule": "winner_null_and_no_calibration_final_evaluation_or_runtime_activation",
    }


def _validate_parent_chain(root: Path) -> dict[str, Any]:
    for path, digest, label in (
        (T5_MANIFEST_PATH, T5_MANIFEST_FILE_SHA256, "T5 manifest"),
        (LOCAL_POOLS_PATH, T3_LOCAL_POOLS_FILE_SHA256, "T3 local pools"),
        (GENERIC_ONNX_PATH, GENERIC_ONNX_FILE_SHA256, "generic ONNX graph"),
    ):
        _require_file(root / path, digest, label)
    for seed, digest in SEED_WEIGHTS_SHA256.items():
        _require_file(
            root / PACKAGE_DIRECTORY / f"seed-{seed}/model.safetensors",
            digest,
            f"seed {seed} checkpoint",
        )
    manifest = check_t5(root)
    if (
        manifest.get("manifest_sha256") != T5_MANIFEST_CONTENT_SHA256
        or manifest.get("package_sha256") != T5_PACKAGE_SHA256
        or manifest.get("release_gate_passed") is not True
        or manifest.get("next_allowed_action") != "DRV2-T6_requires_separate_owner_authorization"
    ):
        raise ValueError("T5 does not authorize the separate T6 owner Gate")
    return manifest


def build_authorization(root: Path, code_commit: str) -> dict[str, Any]:
    _validate_parent_chain(root)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_AUTHORIZATION,
        "gate": "DRV2-T6",
        "authorization_date": "2026-10-10",
        "authorized_by": "project_owner",
        "owner_statement_sha256": OWNER_STATEMENT_SHA256,
        "decision": "execute_untouched_selection_once_under_frozen_protocol",
        "authorized_actions": [
            "export_each_frozen_domain_checkpoint_to_local_float32_onnx",
            "verify_domain_pytorch_onnx_logit_and_top25_order_equivalence",
            "score_exactly_30_frozen_selection_pools_once_for_quality",
            "measure_all_three_arms_under_identical_onnx_cpu_latency_protocol",
            "publish_aggregate_metrics_gates_and_winner_or_null",
        ],
        "prohibited_actions": [
            "change_metrics_gates_tie_rules_or_checkpoints_after_selection_is_visible",
            "change_selection_membership_targets_or_top25_candidates",
            "calibration_threshold_selection_or_fresh_final_evaluation",
            "runtime_activation_or_fastapi_default_change",
            "positive_test_negative_holdout_or_no_match_development_access",
            "publish_row_level_queries_targets_candidates_scores_or_predictions",
        ],
        "bindings": {
            "t5_manifest_file_sha256": T5_MANIFEST_FILE_SHA256,
            "t5_manifest_content_sha256": T5_MANIFEST_CONTENT_SHA256,
            "t5_package_sha256": T5_PACKAGE_SHA256,
            "t3_local_pools_file_sha256": T3_LOCAL_POOLS_FILE_SHA256,
            "generic_onnx_file_sha256": GENERIC_ONNX_FILE_SHA256,
            "seed_weights_sha256": {
                str(seed): digest for seed, digest in SEED_WEIGHTS_SHA256.items()
            },
            "implementation_commit": code_commit,
            "implementation_module_sha256": _file_sha256(
                root / "src/product_variant_resolver/domain_ranker_v2_selection.py"
            ),
        },
        "protocol": comparison_protocol(),
        "rights_state": "owner_attested_not_independently_verified",
        "authority_scope": "frozen_community_catalog_relative_not_manufacturer_or_global_truth",
    }
    result = {**body, "authorization_sha256": _content_sha256(body)}
    if _contains_public_row_level_data(result):
        raise ValueError("T6 authorization contains row-level material")
    return result


def _load_selection_pools(root: Path) -> list[dict[str, Any]]:
    payload = _load_object(root / LOCAL_POOLS_PATH)
    _validate_digest(payload, "content_sha256", "T3 local pools")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise TypeError("T3 local pools are malformed")
    selection = [
        cast(dict[str, Any], row)
        for row in rows
        if isinstance(row, dict) and row.get("partition") == "ranker_selection"
    ]
    if len(selection) != SELECTION_QUERY_COUNT:
        raise ValueError("T6 requires exactly 30 untouched selection pools")
    if any(len(cast(list[Any], row.get("candidates"))) != CANDIDATE_LIMIT for row in selection):
        raise ValueError("T6 selection pools must retain exactly 25 candidates")
    return selection


def _load_onnx_scorer(root: Path, model_path: Path) -> OnnxPointwiseScorer:
    onnxruntime = importlib.import_module("onnxruntime")
    transformers = importlib.import_module("transformers")
    options = onnxruntime.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    options.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
    options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_ENABLE_ALL
    session = onnxruntime.InferenceSession(
        str(model_path), session_options=options, providers=["CPUExecutionProvider"]
    )
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        root / PACKAGE_DIRECTORY, local_files_only=True, trust_remote_code=False
    )
    return OnnxPointwiseScorer(tokenizer, session)


def _export_domain_onnx(root: Path, seed: int, destination: Path) -> None:
    torch = importlib.import_module("torch")
    transformers = importlib.import_module("transformers")
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        root / PACKAGE_DIRECTORY, local_files_only=True, trust_remote_code=False
    )
    model = transformers.AutoModelForSequenceClassification.from_pretrained(
        root / PACKAGE_DIRECTORY / f"seed-{seed}",
        local_files_only=True,
        trust_remote_code=False,
        use_safetensors=True,
        dtype=torch.float32,
    ).eval()

    class LogitWrapper(torch.nn.Module):  # type: ignore[name-defined,misc]
        def __init__(self, wrapped: Any) -> None:
            super().__init__()
            self.wrapped = wrapped

        def forward(self, input_ids: Any, attention_mask: Any, token_type_ids: Any) -> Any:
            return self.wrapped(
                input_ids=input_ids,
                attention_mask=attention_mask,
                token_type_ids=token_type_ids,
            ).logits

    encoded = tokenizer(
        ["2025 HYY52 Aston Martin DB4GT High-Speed Edition 107"] * CANDIDATE_LIMIT,
        [
            (
                "brand=Hot Wheels | casting=Aston Martin DB4GT High-Speed Edition | "
                "year=2025 | series=HW Dream Garage | collector_number=107 | "
                "series_position=3/5 | toy_number=HYY52"
            )
        ]
        * CANDIDATE_LIMIT,
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    )
    names = ("input_ids", "attention_mask", "token_type_ids")
    dynamic_axes = {name: {0: "batch", 1: "sequence"} for name in names}
    dynamic_axes["logits"] = {0: "batch"}
    torch.onnx.export(
        LogitWrapper(model),
        tuple(encoded[name] for name in names),
        destination,
        input_names=list(names),
        output_names=["logits"],
        dynamic_axes=dynamic_axes,
        opset_version=ONNX_OPSET,
        do_constant_folding=True,
        dynamo=False,
    )
    if not destination.is_file() or destination.stat().st_size <= 0:
        raise ValueError(f"seed {seed} ONNX export failed")


def _pairs(pool: Mapping[str, Any]) -> list[tuple[str, str]]:
    query = _string(pool.get("query"), "selection query")
    candidates = pool.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != CANDIDATE_LIMIT:
        raise ValueError("selection pool must contain 25 candidates")
    return [
        (query, _string(candidate.get("rendered_text"), "candidate text"))
        for candidate in candidates
        if isinstance(candidate, dict)
    ]


def _score_onnx_arm(
    pools: Sequence[Mapping[str, Any]], scorer: OnnxPointwiseScorer
) -> tuple[list[list[float]], list[float]]:
    for _ in range(WARMUP_RUNS):
        scorer.score_pairs(_pairs(pools[0]))
    score_rows: list[list[float]] = []
    latency_ms: list[float] = []
    for round_index in range(MEASUREMENT_ROUNDS):
        for pool in pools:
            started = time.perf_counter_ns()
            values = list(scorer.score_pairs(_pairs(pool)))
            latency_ms.append((time.perf_counter_ns() - started) / 1_000_000.0)
            if round_index == 0:
                score_rows.append(values)
    return score_rows, latency_ms


def _score_pytorch_once(
    root: Path, seed: int, pools: Sequence[Mapping[str, Any]]
) -> list[list[float]]:
    torch = importlib.import_module("torch")
    transformers = importlib.import_module("transformers")
    torch.set_num_threads(1)
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        root / PACKAGE_DIRECTORY, local_files_only=True, trust_remote_code=False
    )
    model = transformers.AutoModelForSequenceClassification.from_pretrained(
        root / PACKAGE_DIRECTORY / f"seed-{seed}",
        local_files_only=True,
        trust_remote_code=False,
        use_safetensors=True,
        dtype=torch.float32,
    ).eval()
    rows: list[list[float]] = []
    for pool in pools:
        pairs = _pairs(pool)
        queries, candidates = zip(*pairs, strict=True)
        encoded = tokenizer(
            list(queries),
            list(candidates),
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        )
        with torch.no_grad():
            logits = model(**encoded).logits.reshape(-1).detach().cpu().tolist()
        values = [float(value) for value in logits]
        if len(values) != CANDIDATE_LIMIT or any(not math.isfinite(value) for value in values):
            raise ValueError("PyTorch equivalence scorer returned invalid logits")
        rows.append(values)
    return rows


def compare_equivalence(
    pools: Sequence[Mapping[str, Any]],
    pytorch_rows: Sequence[Sequence[float]],
    onnx_rows: Sequence[Sequence[float]],
) -> dict[str, Any]:
    if (
        len(pools) != SELECTION_QUERY_COUNT
        or len(pytorch_rows) != len(pools)
        or len(onnx_rows) != len(pools)
    ):
        raise ValueError("equivalence rows are not aligned")
    max_delta = 0.0
    identical_orders = 0
    for pool, left, right in zip(pools, pytorch_rows, onnx_rows, strict=True):
        if len(left) != CANDIDATE_LIMIT or len(right) != CANDIDATE_LIMIT:
            raise ValueError("equivalence score vector is incomplete")
        max_delta = max(
            max_delta,
            max(abs(float(a) - float(b)) for a, b in zip(left, right, strict=True)),
        )
        candidates = cast(list[dict[str, Any]], pool["candidates"])
        uuids = [
            _string(candidate.get("canonical_uuid"), "candidate UUID") for candidate in candidates
        ]
        left_order = sorted(range(CANDIDATE_LIMIT), key=lambda i: (-float(left[i]), uuids[i]))
        right_order = sorted(range(CANDIDATE_LIMIT), key=lambda i: (-float(right[i]), uuids[i]))
        identical_orders += int(left_order == right_order)
    passed = max_delta <= MAX_ABSOLUTE_LOGIT_DELTA and identical_orders == SELECTION_QUERY_COUNT
    return {
        "pair_count": SELECTION_QUERY_COUNT * CANDIDATE_LIMIT,
        "maximum_absolute_logit_delta": max_delta,
        "maximum_allowed_absolute_logit_delta": MAX_ABSOLUTE_LOGIT_DELTA,
        "identical_top25_order_count": identical_orders,
        "required_identical_top25_order_count": SELECTION_QUERY_COUNT,
        "passed": passed,
    }


def _generic_ordering_matches_frozen(
    pools: Sequence[Mapping[str, Any]], scores: Sequence[Sequence[float]]
) -> bool:
    for pool, row in zip(pools, scores, strict=True):
        candidates = cast(list[dict[str, Any]], pool["candidates"])
        ranked = sorted(
            zip(row, candidates, strict=True),
            key=lambda item: (-float(item[0]), _string(item[1].get("canonical_uuid"), "UUID")),
        )
        if any(
            candidate.get("generic_pointwise_rank") != rank
            for rank, (_, candidate) in enumerate(ranked, 1)
        ):
            return False
    return True


def _write(path: Path, payload: object, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(payload))
    path.chmod(mode)


def execute(root: Path, code_commit: str) -> dict[str, Any]:
    outputs = (
        AUTHORIZATION_PATH,
        RESULT_PATH,
        PRIVATE_PATH,
        *(LOCAL_DIRECTORY / f"seed-{seed}-float32.onnx" for seed in SEEDS),
    )
    if any((root / path).exists() for path in outputs):
        raise FileExistsError("DRV2-T6 is one-shot and its artifacts already exist")
    authorization = build_authorization(root, code_commit)
    pools = _load_selection_pools(root)
    os.environ["TOKENIZERS_PARALLELISM"] = "false"

    scorers: dict[str, OnnxPointwiseScorer] = {
        "generic": _load_onnx_scorer(root, root / GENERIC_ONNX_PATH)
    }
    export_metadata: dict[str, Any] = {}
    equivalence: dict[str, Any] = {}
    directory = root / DIRECTORY
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".t6-", dir=directory) as temporary:
        temporary_directory = Path(temporary)
        for seed in SEEDS:
            arm = f"domain_seed_{seed}"
            staged = temporary_directory / f"seed-{seed}-float32.onnx"
            _export_domain_onnx(root, seed, staged)
            scorer = _load_onnx_scorer(root, staged)
            pytorch_rows = _score_pytorch_once(root, seed, pools)
            onnx_rows = [list(scorer.score_pairs(_pairs(pool))) for pool in pools]
            equivalence[arm] = compare_equivalence(pools, pytorch_rows, onnx_rows)
            if equivalence[arm]["passed"] is not True:
                raise ValueError(f"{arm} ONNX equivalence Gate failed")
            export_metadata[arm] = {
                "file_sha256": _file_sha256(staged),
                "size_bytes": staged.stat().st_size,
                "opset": ONNX_OPSET,
                "dtype": "float32",
            }
            final = root / LOCAL_DIRECTORY / staged.name
            final.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged, final)
            final.chmod(0o600)
            scorers[arm] = _load_onnx_scorer(root, final)

    metrics: dict[str, AggregateMetrics] = {}
    private_rows: dict[str, list[dict[str, Any]]] = {}
    latency_samples: dict[str, list[float]] = {}
    raw_scores: dict[str, list[list[float]]] = {}
    for arm in ("generic", "domain_seed_17", "domain_seed_29"):
        scores, latencies = _score_onnx_arm(pools, scorers[arm])
        arm_metrics, rows = aggregate_metrics(pools, scores, latencies)
        metrics[arm] = arm_metrics
        private_rows[arm] = rows
        latency_samples[arm] = latencies
        raw_scores[arm] = scores
    if not _generic_ordering_matches_frozen(pools, raw_scores["generic"]):
        raise ValueError("generic ONNX ordering differs from the frozen T3 ordering")

    generic = metrics["generic"]
    stable = all(
        metrics[f"domain_seed_{seed}"].exact_top1_count > generic.exact_top1_count
        and metrics[f"domain_seed_{seed}"].mrr_at_10 > generic.mrr_at_10
        for seed in SEEDS
    )
    gates = {
        arm: evaluate_gate(generic, metrics[arm], seed_direction_stable=stable)
        for arm in ("domain_seed_17", "domain_seed_29")
    }
    winner = select_winner(metrics, gates)

    private_body: dict[str, Any] = {
        "schema_version": SCHEMA_PRIVATE,
        "version": VERSION,
        "authorization_sha256": authorization["authorization_sha256"],
        "onnx_exports": export_metadata,
        "equivalence": equivalence,
        "arms": {
            arm: {"rows": private_rows[arm], "latency_ms": latency_samples[arm]} for arm in metrics
        },
    }
    private = {**private_body, "content_sha256": _content_sha256(private_body)}
    _write(root / PRIVATE_PATH, private, 0o600)
    _write(root / AUTHORIZATION_PATH, authorization, 0o644)

    result_body: dict[str, Any] = {
        "schema_version": SCHEMA_RESULT,
        "version": VERSION,
        "status": "winner_selected" if winner is not None else "ranker_gate_failed",
        "authorization_sha256": authorization["authorization_sha256"],
        "authorization_file_sha256": _file_sha256(root / AUTHORIZATION_PATH),
        "private_diagnostics_file_sha256": _file_sha256(root / PRIVATE_PATH),
        "input_bindings": authorization["bindings"],
        "protocol": comparison_protocol(),
        "generic_ordering_matches_frozen_t3": True,
        "inference_equivalence": equivalence,
        "metrics": {arm: asdict(value) for arm, value in metrics.items()},
        "gates": gates,
        "winner": winner,
        "selected_checkpoint_sha256": (
            None if winner is None else SEED_WEIGHTS_SHA256[int(winner.rsplit("_", 1)[1])]
        ),
        "guardrails": {
            "ranker_selection_rows_scored": SELECTION_QUERY_COUNT,
            "selection_quality_evaluations": 1,
            "positive_test_rows_read_or_scored": 0,
            "negative_holdout_rows_read_or_scored": 0,
            "no_match_development_rows_read_or_scored": 0,
            "calibration_fits": 0,
            "fresh_final_evaluations": 0,
            "runtime_default_changed": False,
            "runtime_activations": 0,
            "public_row_level_records": 0,
        },
        "limitations": [
            "small_catalog_relative_selection_comparison",
            "not_manufacturer_or_global_truth",
            "not_calibrated_or_final_evaluated",
            "runtime_not_activated",
        ],
        "next_allowed_action": "DRV2-T7_Lite_QA_requires_separate_owner_authorization",
    }
    result = {**result_body, "result_sha256": _content_sha256(result_body)}
    if _contains_public_row_level_data(result):
        raise ValueError("T6 result contains row-level material")
    _write(root / RESULT_PATH, result, 0o644)
    return result


def check(root: Path) -> dict[str, Any]:
    _validate_parent_chain(root)
    authorization = _load_object(root / AUTHORIZATION_PATH)
    result = _load_object(root / RESULT_PATH)
    private = _load_object(root / PRIVATE_PATH)
    _validate_digest(authorization, "authorization_sha256", "T6 authorization")
    _validate_digest(result, "result_sha256", "T6 result")
    _validate_digest(private, "content_sha256", "T6 private diagnostics")
    if result.get("authorization_sha256") != authorization.get("authorization_sha256"):
        raise ValueError("T6 result is not bound to its authorization")
    if result.get("private_diagnostics_file_sha256") != _file_sha256(root / PRIVATE_PATH):
        raise ValueError("T6 private diagnostics binding changed")
    if any(_contains_public_row_level_data(value) for value in (authorization, result)):
        raise ValueError("T6 public artifact contains row-level material")
    if stat.S_IMODE((root / PRIVATE_PATH).stat().st_mode) != 0o600:
        raise ValueError("T6 private diagnostics must use mode 0600")
    exports = private.get("onnx_exports")
    if not isinstance(exports, dict):
        raise TypeError("T6 private ONNX metadata is malformed")
    for seed in SEEDS:
        arm = f"domain_seed_{seed}"
        metadata = exports.get(arm)
        if not isinstance(metadata, dict):
            raise TypeError(f"T6 {arm} ONNX metadata is malformed")
        path = root / LOCAL_DIRECTORY / f"seed-{seed}-float32.onnx"
        if (
            _file_sha256(path) != metadata.get("file_sha256")
            or path.stat().st_size != metadata.get("size_bytes")
            or stat.S_IMODE(path.stat().st_mode) != 0o600
        ):
            raise ValueError(f"T6 {arm} local ONNX artifact differs from diagnostics")
    winner = result.get("winner")
    if winner not in {None, "domain_seed_17", "domain_seed_29"}:
        raise ValueError("T6 winner is invalid")
    expected_hash = None if winner is None else SEED_WEIGHTS_SHA256[int(winner.rsplit("_", 1)[1])]
    if result.get("selected_checkpoint_sha256") != expected_hash:
        raise ValueError("T6 winner checkpoint binding differs")
    if result.get("next_allowed_action") != "DRV2-T7_Lite_QA_requires_separate_owner_authorization":
        raise ValueError("T6 next action is invalid")
    return result


def _current_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    )
    commit = result.stdout.strip()
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise ValueError("could not resolve T6 implementation commit")
    return commit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute or check DRV2-T6 untouched selection")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--acknowledge-owner-authorization", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.run:
        if not args.acknowledge_owner_authorization:
            parser.error("--run requires --acknowledge-owner-authorization")
        result = execute(root, _current_commit(root))
    elif args.check:
        result = check(root)
    else:
        parser.error("choose --run or --check")
    print(
        json.dumps(
            {
                "status": result["status"],
                "winner": result["winner"],
                "result_sha256": result["result_sha256"],
                "next_allowed_action": result["next_allowed_action"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
