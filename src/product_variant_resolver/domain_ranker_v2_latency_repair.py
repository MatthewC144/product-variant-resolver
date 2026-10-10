"""DRV2-T3R float32 ONNX export, equivalence, and latency recheck."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import stat
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .domain_ranker_v2_candidate_pools import (
    CANDIDATE_LIMIT,
    LOCAL_POOLS_PATH,
    MAXIMUM_P95_MS,
    MEASUREMENT_ROUNDS,
    POINTWISE_CONFIG_PATH,
    POINTWISE_CONFIG_SHA256,
    POINTWISE_MANIFEST_SHA256,
    POINTWISE_MODEL_PATH,
    POINTWISE_WEIGHTS_SHA256,
    TORCH_THREADS,
    VALIDATION_QUERY_COUNT,
    WARMUP_RUNS,
    _contains_public_row_level_data,
    benchmark_validation_latency,
)
from .domain_ranker_v2_candidate_pools import (
    LATENCY_PATH as T3_LATENCY_PATH,
)
from .domain_ranker_v2_candidate_pools import (
    POOL_MANIFEST_PATH as T3_POOL_MANIFEST_PATH,
)
from .domain_ranker_v2_candidate_pools import (
    check as check_t3,
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

SCHEMA_AUTHORIZATION = "pvr-drv2-t3r-owner-authorization-v1"
SCHEMA_ONNX_MANIFEST = "pvr-drv2-float32-onnx-manifest-v1"
SCHEMA_REPAIR_RESULT = "pvr-drv2-latency-repair-result-v1"

DIRECTORY = Path("data/evaluation/domain-ranker-v2-remediation")
LOCAL_DIRECTORY = DIRECTORY / "local-t3r"
LOCAL_ONNX_PATH = LOCAL_DIRECTORY / "generic-pointwise-float32.onnx"
AUTHORIZATION_PATH = DIRECTORY / "t3r-owner-authorization.json"
ONNX_MANIFEST_PATH = DIRECTORY / "onnx-manifest.json"
RESULT_PATH = DIRECTORY / "latency-repair.json"

T3_AUTHORIZATION_FILE_SHA256 = (
    "4e68a561d5191acc5c6aeacd75b0a666a66a0ed47a107b519038768ec48e6e81"
)
T3_POOL_MANIFEST_FILE_SHA256 = (
    "2b7d36595dfad3451b575488b48f016e6acf3aace000cf532a909e74e69d99f3"
)
T3_LATENCY_FILE_SHA256 = "296a273fad6f1f5fc10df391c22f839ded5d251beb6bafcb21b1e917a443e883"
T3_LOCAL_POOLS_FILE_SHA256 = (
    "0c889bfc06755a49ba779f2df64a4e4d87d3de676bf47063fcfcdec454022b24"
)
T3_AUTHORIZATION_CONTENT_SHA256 = (
    "ef8a7215f336443f58162b0f66138a5e449bda3245e2af5a43e88d2f045195c3"
)
T3_POOL_MANIFEST_CONTENT_SHA256 = (
    "da419555a6e364063a288a7ece691a330f849d361b7735809e616af4d4310777"
)
T3_LATENCY_CONTENT_SHA256 = (
    "7b396578d36e8c6a76fd79e447770713014716aa911661f4055898f2f0c76d86"
)
OWNER_STATEMENT_SHA256 = "37e6c4a73e7b5f0bafa28453bc8756ef3d45f87162d0d1f802d1ff4bc2b26389"

ONNX_OPSET = 17
MAX_ABSOLUTE_LOGIT_DELTA = 2e-5
EXPECTED_PAIR_COUNT = 4_500
EXPECTED_POOL_COUNT = 180


class OnnxPointwiseScorer:
    version = "generic-minilm-float32-onnxruntime-v1"

    def __init__(self, tokenizer: Any, session: Any) -> None:
        self.tokenizer = tokenizer
        self.session = session

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[float, ...]:
        if not pairs:
            return ()
        numpy = importlib.import_module("numpy")
        queries, candidates = zip(*pairs, strict=True)
        encoded = self.tokenizer(
            list(queries),
            list(candidates),
            padding=True,
            truncation=True,
            max_length=128,
            return_tensors="np",
        )
        inputs = {
            key: numpy.asarray(encoded[key], dtype=numpy.int64)
            for key in ("input_ids", "attention_mask", "token_type_ids")
        }
        raw = self.session.run(["logits"], inputs)[0].reshape(-1).tolist()
        values = tuple(float(value) for value in raw)
        if len(values) != len(pairs) or any(not math.isfinite(value) for value in values):
            raise ValueError("ONNX scorer returned invalid logits")
        return values


def _write(path: Path, payload: object, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(payload))
    path.chmod(mode)


def _validate_t3_chain(root: Path) -> dict[str, Any]:
    for path, digest, label in (
        (DIRECTORY / "t3-owner-authorization.json", T3_AUTHORIZATION_FILE_SHA256, "T3 authorization"),
        (T3_POOL_MANIFEST_PATH, T3_POOL_MANIFEST_FILE_SHA256, "T3 pool manifest"),
        (T3_LATENCY_PATH, T3_LATENCY_FILE_SHA256, "T3 latency result"),
        (LOCAL_POOLS_PATH, T3_LOCAL_POOLS_FILE_SHA256, "T3 local pools"),
    ):
        _require_file(root / path, digest, label)
    latency = check_t3(root)
    if (
        latency.get("readiness_sha256") != T3_LATENCY_CONTENT_SHA256
        or latency.get("status") != "latency_gate_failed"
        or latency.get("next_allowed_action") != "stop_and_repair_generic_latency_before_DRV2-T4"
    ):
        raise ValueError("T3 does not permit a latency-only repair")
    return latency


def build_authorization(root: Path, code_commit: str) -> dict[str, Any]:
    _validate_t3_chain(root)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_AUTHORIZATION,
        "gate": "DRV2-T3R",
        "authorization_date": "2026-10-10",
        "authorized_by": "project_owner",
        "owner_statement_sha256": OWNER_STATEMENT_SHA256,
        "decision": "export_float32_onnx_and_rerun_equivalent_generic_latency_only",
        "authorized_actions": [
            "export_pinned_generic_safetensors_to_float32_onnx_opset17",
            "verify_all_4500_logits_with_max_absolute_delta_at_most_2e_5",
            "require_identical_top25_order_for_all_180_pools",
            "rerun_identical_90_sample_validation_latency_protocol",
            "publish_aggregate_equivalence_and_latency_results_only",
        ],
        "prohibited_actions": [
            "quantize_or_change_model_weights",
            "change_tokenizer_queries_candidates_or_top25_membership",
            "change_200ms_budget_or_measurement_protocol",
            "inspect_selection_quality_metrics",
            "hard_negative_mining_or_model_training",
            "calibration_final_evaluation_or_runtime_activation",
            "publish_onnx_graph_or_row_level_scores_predictions_or_membership",
        ],
        "bindings": {
            "t3_authorization_content_sha256": T3_AUTHORIZATION_CONTENT_SHA256,
            "t3_pool_manifest_content_sha256": T3_POOL_MANIFEST_CONTENT_SHA256,
            "t3_latency_content_sha256": T3_LATENCY_CONTENT_SHA256,
            "t3_local_pools_file_sha256": T3_LOCAL_POOLS_FILE_SHA256,
            "generic_config_sha256": POINTWISE_CONFIG_SHA256,
            "generic_manifest_sha256": POINTWISE_MANIFEST_SHA256,
            "generic_weights_sha256": POINTWISE_WEIGHTS_SHA256,
            "implementation_commit": code_commit,
            "implementation_module_sha256": _file_sha256(
                root / "src/product_variant_resolver/domain_ranker_v2_latency_repair.py"
            ),
        },
        "equivalence_protocol": {
            "pair_count": EXPECTED_PAIR_COUNT,
            "pool_count": EXPECTED_POOL_COUNT,
            "maximum_absolute_logit_delta": MAX_ABSOLUTE_LOGIT_DELTA,
            "required_identical_top25_order_count": EXPECTED_POOL_COUNT,
            "tie_break": "score_desc_then_canonical_uuid_asc",
        },
        "latency_protocol": {
            "partition": "ranker_validation",
            "query_count": VALIDATION_QUERY_COUNT,
            "candidates_per_query": CANDIDATE_LIMIT,
            "device": "cpu",
            "intra_op_threads": TORCH_THREADS,
            "inter_op_threads": 1,
            "execution_mode": "sequential",
            "graph_optimization": "all",
            "batch_size": CANDIDATE_LIMIT,
            "max_length": 128,
            "warmup_runs": WARMUP_RUNS,
            "measurement_rounds": MEASUREMENT_ROUNDS,
            "sample_count": VALIDATION_QUERY_COUNT * MEASUREMENT_ROUNDS,
            "p95_method": "nearest_rank",
            "maximum_p95_ms": MAXIMUM_P95_MS,
        },
    }
    result = {**body, "authorization_sha256": _content_sha256(body)}
    if _contains_public_row_level_data(result):
        raise ValueError("T3R authorization contains row-level material")
    return result


def export_float32_onnx(root: Path, destination: Path) -> None:
    torch = importlib.import_module("torch")
    transformers = importlib.import_module("transformers")
    tokenizer = transformers.AutoTokenizer.from_pretrained(
        root / POINTWISE_MODEL_PATH, local_files_only=True, trust_remote_code=False
    )
    model = transformers.AutoModelForSequenceClassification.from_pretrained(
        root / POINTWISE_MODEL_PATH,
        local_files_only=True,
        trust_remote_code=False,
        use_safetensors=True,
        dtype=torch.float32,
    ).eval()

    class LogitWrapper(torch.nn.Module):  # type: ignore[name-defined,misc]
        def __init__(self, wrapped: Any) -> None:
            super().__init__()
            self.wrapped = wrapped

        def forward(
            self, input_ids: Any, attention_mask: Any, token_type_ids: Any
        ) -> Any:
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
        max_length=128,
        return_tensors="pt",
    )
    input_names = ("input_ids", "attention_mask", "token_type_ids")
    dynamic_axes = {name: {0: "batch", 1: "sequence"} for name in input_names}
    dynamic_axes["logits"] = {0: "batch"}
    torch.onnx.export(
        LogitWrapper(model),
        tuple(encoded[name] for name in input_names),
        destination,
        input_names=list(input_names),
        output_names=["logits"],
        dynamic_axes=dynamic_axes,
        opset_version=ONNX_OPSET,
        do_constant_folding=True,
        dynamo=False,
    )
    if not destination.is_file() or destination.stat().st_size <= 0:
        raise ValueError("float32 ONNX export failed")


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
        root / POINTWISE_MODEL_PATH, local_files_only=True, trust_remote_code=False
    )
    return OnnxPointwiseScorer(tokenizer, session)


def compare_frozen_scores(
    rows: Sequence[Mapping[str, Any]], scorer: OnnxPointwiseScorer
) -> dict[str, Any]:
    max_delta = 0.0
    identical_logits = 0
    identical_orders = 0
    pair_count = 0
    for row in rows:
        query = _string(row.get("query"), "pool query")
        candidates = row.get("candidates")
        if not isinstance(candidates, list) or len(candidates) != CANDIDATE_LIMIT:
            raise ValueError("T3R requires unchanged Top-25 pools")
        pairs = [
            (query, _string(candidate.get("rendered_text"), "candidate text"))
            for candidate in candidates
            if isinstance(candidate, dict)
        ]
        new_scores = scorer.score_pairs(pairs)
        old_scores = tuple(float(candidate["generic_pointwise_score"]) for candidate in candidates)
        deltas = [abs(new - old) for new, old in zip(new_scores, old_scores, strict=True)]
        max_delta = max(max_delta, max(deltas))
        identical_logits += sum(new == old for new, old in zip(new_scores, old_scores, strict=True))
        pair_count += len(new_scores)
        uuids = [_string(candidate.get("canonical_uuid"), "candidate UUID") for candidate in candidates]
        old_order = sorted(range(CANDIDATE_LIMIT), key=lambda i: (-old_scores[i], uuids[i]))
        new_order = sorted(range(CANDIDATE_LIMIT), key=lambda i: (-new_scores[i], uuids[i]))
        identical_orders += int(old_order == new_order)
    result = {
        "pair_count": pair_count,
        "exactly_equal_logit_count": identical_logits,
        "maximum_absolute_logit_delta": max_delta,
        "maximum_allowed_absolute_logit_delta": MAX_ABSOLUTE_LOGIT_DELTA,
        "identical_top25_order_count": identical_orders,
        "required_identical_top25_order_count": EXPECTED_POOL_COUNT,
        "passed": (
            pair_count == EXPECTED_PAIR_COUNT
            and max_delta <= MAX_ABSOLUTE_LOGIT_DELTA
            and identical_orders == EXPECTED_POOL_COUNT
        ),
    }
    return result


def _nearest_rank(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered or not 0 < probability <= 1:
        raise ValueError("percentile input is invalid")
    return ordered[math.ceil(probability * len(ordered)) - 1]


def build_result(
    authorization: Mapping[str, Any],
    onnx_manifest: Mapping[str, Any],
    equivalence: Mapping[str, Any],
    latency_ms: Sequence[float],
) -> dict[str, Any]:
    if equivalence.get("passed") is not True:
        raise ValueError("ONNX equivalence Gate failed")
    expected = VALIDATION_QUERY_COUNT * MEASUREMENT_ROUNDS
    if len(latency_ms) != expected or any(value <= 0 or not math.isfinite(value) for value in latency_ms):
        raise ValueError("T3R latency samples are invalid")
    p50 = _nearest_rank(latency_ms, 0.50)
    p95 = _nearest_rank(latency_ms, 0.95)
    passed = p95 <= MAXIMUM_P95_MS
    baseline_p95 = 217.699834
    body: dict[str, Any] = {
        "schema_version": SCHEMA_REPAIR_RESULT,
        "status": "latency_repair_passed" if passed else "latency_repair_failed",
        "authorization_sha256": authorization["authorization_sha256"],
        "onnx_manifest_sha256": onnx_manifest["manifest_sha256"],
        "equivalence": dict(equivalence),
        "latency": {
            "sample_count": len(latency_ms),
            "cpu_latency_p50_ms": p50,
            "cpu_latency_p95_ms": p95,
            "baseline_t3_cpu_latency_p95_ms": baseline_p95,
            "p95_improvement_ms": baseline_p95 - p95,
            "p95_improvement_ratio": (baseline_p95 - p95) / baseline_p95,
            "maximum_p95_ms": MAXIMUM_P95_MS,
            "gate_passed": passed,
        },
        "guardrails": {
            "model_weights_changed": False,
            "quantization_used": False,
            "top25_membership_changed": False,
            "selection_quality_evaluations": 0,
            "hard_negative_labels_created": 0,
            "model_training_runs": 0,
            "runtime_default_changed": False,
        },
        "next_allowed_action": (
            "DRV2-T4_requires_separate_owner_authorization"
            if passed
            else "stop_and_repair_generic_latency_before_DRV2-T4"
        ),
    }
    result = {**body, "result_sha256": _content_sha256(body)}
    if _contains_public_row_level_data(result):
        raise ValueError("T3R result contains row-level material")
    return result


def _package_version(name: str) -> str:
    module = importlib.import_module(name)
    return _string(getattr(module, "__version__", None), f"{name} version")


def materialize(root: Path, code_commit: str) -> dict[str, Any]:
    outputs = (AUTHORIZATION_PATH, ONNX_MANIFEST_PATH, RESULT_PATH, LOCAL_ONNX_PATH)
    if any((root / path).exists() for path in outputs):
        raise FileExistsError("DRV2-T3R artifacts already exist")
    _require_file(root / POINTWISE_CONFIG_PATH, POINTWISE_CONFIG_SHA256, "generic config")
    _require_file(
        root / POINTWISE_MODEL_PATH / "manifest.json", POINTWISE_MANIFEST_SHA256, "generic manifest"
    )
    _require_file(
        root / POINTWISE_MODEL_PATH / "model.safetensors", POINTWISE_WEIGHTS_SHA256, "generic weights"
    )
    authorization = build_authorization(root, code_commit)
    parent = root / DIRECTORY
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".t3r-", dir=parent) as temporary:
        staged_model = Path(temporary) / "generic-pointwise-float32.onnx"
        export_float32_onnx(root, staged_model)
        scorer = _load_onnx_scorer(root, staged_model)
        local_pools = _load_object(root / LOCAL_POOLS_PATH)
        rows = local_pools.get("rows")
        if not isinstance(rows, list) or len(rows) != EXPECTED_POOL_COUNT:
            raise ValueError("T3 local pool population changed")
        equivalence = compare_frozen_scores(rows, scorer)
        if equivalence["passed"] is not True:
            raise ValueError("float32 ONNX does not preserve frozen generic ordering")
        samples = benchmark_validation_latency(local_pools, scorer)
        onnxruntime = importlib.import_module("onnxruntime")
        manifest_body: dict[str, Any] = {
            "schema_version": SCHEMA_ONNX_MANIFEST,
            "status": "local_only_reproducible_float32_graph",
            "authorization_sha256": authorization["authorization_sha256"],
            "source": {
                "model_config_sha256": POINTWISE_CONFIG_SHA256,
                "model_manifest_sha256": POINTWISE_MANIFEST_SHA256,
                "model_weights_sha256": POINTWISE_WEIGHTS_SHA256,
            },
            "artifact": {
                "file_sha256": _file_sha256(staged_model),
                "size_bytes": staged_model.stat().st_size,
                "opset": ONNX_OPSET,
                "dtype": "float32",
                "input_names": ["input_ids", "attention_mask", "token_type_ids"],
                "output_names": ["logits"],
                "row_level_publication": False,
            },
            "runtime": {
                "onnx": _package_version("onnx"),
                "onnxruntime": _string(
                    getattr(onnxruntime, "__version__", None), "onnxruntime version"
                ),
                "provider": "CPUExecutionProvider",
                "intra_op_threads": 1,
                "inter_op_threads": 1,
                "execution_mode": "sequential",
                "graph_optimization": "all",
            },
        }
        onnx_manifest = {**manifest_body, "manifest_sha256": _content_sha256(manifest_body)}
        result = build_result(authorization, onnx_manifest, equivalence, samples)
        final_model = root / LOCAL_ONNX_PATH
        final_model.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staged_model, final_model)
        final_model.chmod(0o600)
    _write(root / AUTHORIZATION_PATH, authorization, 0o644)
    _write(root / ONNX_MANIFEST_PATH, onnx_manifest, 0o644)
    _write(root / RESULT_PATH, result, 0o644)
    return result


def check(root: Path) -> dict[str, Any]:
    _validate_t3_chain(root)
    authorization = _load_object(root / AUTHORIZATION_PATH)
    manifest = _load_object(root / ONNX_MANIFEST_PATH)
    result = _load_object(root / RESULT_PATH)
    _validate_digest(authorization, "authorization_sha256", "T3R authorization")
    _validate_digest(manifest, "manifest_sha256", "T3R ONNX manifest")
    _validate_digest(result, "result_sha256", "T3R result")
    if any(_contains_public_row_level_data(value) for value in (authorization, manifest, result)):
        raise ValueError("T3R public artifact contains row-level material")
    model = root / LOCAL_ONNX_PATH
    artifact = manifest.get("artifact")
    if not isinstance(artifact, dict):
        raise TypeError("T3R ONNX manifest artifact is malformed")
    if (
        _file_sha256(model) != artifact.get("file_sha256")
        or model.stat().st_size != artifact.get("size_bytes")
        or stat.S_IMODE(model.stat().st_mode) != 0o600
    ):
        raise ValueError("T3R local ONNX artifact differs from its manifest")
    for path in (AUTHORIZATION_PATH, ONNX_MANIFEST_PATH, RESULT_PATH):
        if stat.S_IMODE((root / path).stat().st_mode) != 0o644:
            raise ValueError("T3R public artifacts must use mode 0644")
    expected_next = (
        "DRV2-T4_requires_separate_owner_authorization"
        if result.get("latency", {}).get("gate_passed") is True
        else "stop_and_repair_generic_latency_before_DRV2-T4"
    )
    if result.get("next_allowed_action") != expected_next:
        raise ValueError("T3R next action differs from the latency Gate")
    return result


def _current_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    )
    commit = result.stdout.strip()
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise ValueError("could not resolve T3R implementation commit")
    return commit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Execute or check DRV2-T3R latency repair")
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
                "onnx_cpu_p95_ms": result["latency"]["cpu_latency_p95_ms"],
                "identical_top25_orders": result["equivalence"][
                    "identical_top25_order_count"
                ],
                "next_allowed_action": result["next_allowed_action"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
